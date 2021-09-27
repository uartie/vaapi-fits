###
### Copyright (C) 2021 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

import re
import slash

from ...lib.common import timefn, get_media, call
from ...lib.ffmpeg.util import have_ffmpeg, map_best_hw_format, mapformat
from ...lib.parameters import format_value
from ...lib.util import skip_test_if_missing_features
from ...lib.metrics import md5, check_metric

@slash.requires(have_ffmpeg)
class BaseDecoderTest(slash.Test):
  def before(self):
    super().before()
    self.refctx = []
    self.renderDevice = get_media().render_device

  @timefn("ffmpeg")
  def call_ffmpeg(self):
    return call(
      (
        "ffmpeg -hwaccel {hwaccel} -init_hw_device {hwaccel}=hw:{renderDevice}"
        " -hwaccel_output_format {hwformat} -hwaccel_flags allow_profile_mismatch"
        " -v verbose"
      ).format(**vars(self)) + (
        " -c:v {ffdecoder}" if hasattr(self, "ffdecoder") else ""
      ).format(**vars(self)) + (
        " -i {source}"
        " -pix_fmt {mformat} -f rawvideo -vsync passthrough -autoscale 0"
        " -vframes {frames} -y {decoded}"
      ).format(**vars(self))
    )

  def gen_name(self):
    name = "{case}_{width}x{height}_{format}"
    if vars(self).get("r2r", None) is not None:
      name += "_r2r"
    return name

  def validate_caps(self):
    self.hwformat = map_best_hw_format(self.format, self.caps["fmts"])
    self.mformat = mapformat(self.format)

    if None in [self.hwformat, self.mformat]:
      slash.skip_test("{format} format not supported".format(**vars(self)))

    maxw, maxh = self.caps["maxres"]
    if self.width > maxw or self.height > maxh:
      slash.skip_test(
        format_value(
          "{platform}.{driver}.{width}x{height} not supported", **vars(self)))

    skip_test_if_missing_features(self)

  def decode(self):
    self.validate_caps()

    get_media().test_call_timeout = vars(self).get("call_timeout", 0)

    name = self.gen_name().format(**vars(self))
    self.decoded = get_media()._test_artifact("{}.yuv".format(name))
    self.output = self.call_ffmpeg()

    if vars(self).get("r2r", None) is not None:
      assert type(self.r2r) is int and self.r2r > 1, "invalid r2r value"
      md5ref = md5(self.decoded)
      get_media()._set_test_details(md5_ref = md5ref)
      for i in range(1, self.r2r):
        self.decoded = get_media()._test_artifact("{}_{}.yuv".format(name, i))
        self.call_ffmpeg()
        result = md5(self.decoded)
        get_media()._set_test_details(**{"md5_{:03}".format(i) : result})
        assert result == md5ref, "r2r md5 mismatch"
        # delete decoded file after each iteration
        get_media()._purge_test_artifact(self.decoded)
    else:
      self.check_output()
      self.check_metrics()

  def check_output(self):
    m = re.search(
      "hwaccel initialisation returned error", self.output, re.MULTILINE)
    assert m is None, "Failed to use hardware decode"

  def check_metrics(self):
    check_metric(**vars(self))
