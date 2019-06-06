###
### Copyright (C) 2018-2019 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

from ....lib import *
from ..util import *

@slash.requires(have_ffmpeg)
@slash.requires(have_ffmpeg_qsv_accel)
@slash.requires(*have_ffmpeg_filter("vpp_qsv"))
@slash.requires(using_compatible_driver)
class DeinterlaceTest(slash.Test):
  _default_methods_ = [
    "bob",
    "advanced",
  ]

  _default_modes_ = [
    dict(method = m, rate = "frame") for m in _default_methods_
  ]

  def before(self):
    # default metric
    self.metric = dict(type = "md5")
    self.refctx = []

  @timefn("ffmpeg")
  def call_ffmpeg(self):
    call(
      "ffmpeg -init_hw_device qsv=qsv:hw -hwaccel qsv -filter_hw_device qsv"
      " -v verbose {ffdecoder} -i {source}"
      " -vf 'format=nv12|qsv,hwupload=extra_hw_frames=16"
      ",vpp_qsv=deinterlace={method},hwdownload,format=nv12'"
      " -pix_fmt {mformat} -f rawvideo -vsync passthrough -an -vframes {frames}"
      " -y {decoded}".format(**vars(self)))

  def get_name_tmpl(self):
    name = "{case}_di_{method}_{rate}_{width}x{height}_{format}"
    if vars(self).get("r2r", None) is not None:
      name += "_r2r"
    return name

  def deinterlace(self):
    self.mformat = mapformat(self.format)
    self.mmethod = map_deinterlace_method(self.method)

    # This is fixed in vpp_qsv deinterlace.  It always outputs at frame
    # rate (one frame of output for each field-pair).
    if "frame" != self.rate:
      slash.skip_test("{rate} rate not supported".format(**vars(self)))

    if self.mformat is None:
      slash.skip_test("{format} format not supported".format(**vars(self)))

    if self.mmethod is None:
      slash.skip_test("{method} method not supported".format(**vars(self)))

    name = self.get_name_tmpl().format(**vars(self))
    self.decoded = get_media()._test_artifact("{}.yuv".format(name))
    self.ffdecoder = self.ffdecoder.format(**vars(self))
    self.call_ffmpeg()

    if vars(self).get("r2r", None) is not None:
      assert self.r2r > 1, "invalid r2r value"
      md5ref = md5(self.decoded)
      get_media()._set_test_details(md5_ref = md5ref)
      for i in xrange(1, self.r2r):
        self.decoded = get_media()._test_artifact("{}_{}.yuv".format(name, i))
        self.call_ffmpeg()
        result = md5(self.decoded)
        get_media()._set_test_details(**{"md5_{:03}".format(i) : result})
        assert result == md5ref, "r2r md5 mismatch"
        # Delete the decoded file after each iteration to conserve space
        get_media()._purge_test_artifact(self.decoded)
    else:
      self.check_metrics()

  def check_metrics(self):
    check_filesize(
      self.decoded, self.width, self.height, self.frames, self.format)
    if vars(self).get("reference", None) is not None:
      self.reference = format_value(self.reference, **vars(self))
    check_metric(**vars(self))

spec_raw = load_test_spec("vpp", "deinterlace")
spec_raw_r2r = load_test_spec("vpp", "deinterlace", "r2r")
class raw(DeinterlaceTest):
  def before(self):
    self.tff = 1
    self.rate = "frame"
    self.ffdecoder = "-f rawvideo -pix_fmt {mformat} -s:v {width}x{height} -top {tff}"
    super(raw, self).before()

  @platform_tags(VPP_PLATFORMS)
  @slash.parametrize(
    *gen_vpp_deinterlace_parameters(
      spec_raw, DeinterlaceTest._default_methods_))
  def test(self, case, method):
    vars(self).update(spec_raw[case].copy())
    vars(self).update(case = case, method = method)
    self.deinterlace()

  @platform_tags(VPP_PLATFORMS)
  @slash.parametrize(
    *gen_vpp_deinterlace_parameters(
      spec_raw_r2r, DeinterlaceTest._default_methods_))
  def test_r2r(self, case, method):
    vars(self).setdefault("r2r", 5)
    vars(self).update(spec_raw_r2r[case].copy())
    vars(self).update(case = case, method = method)
    self.deinterlace()

spec_avc = load_test_spec("vpp", "deinterlace", "avc")
class avc(DeinterlaceTest):
  def before(self):
    self.ffdecoder = "-c:v h264_qsv"
    super(avc, self).before()

  @platform_tags(set(AVC_DECODE_PLATFORMS) & set(VPP_PLATFORMS))
  @slash.requires(*have_ffmpeg_decoder("h264_qsv"))
  @slash.parametrize(
    *gen_vpp_deinterlace_parameters2(
      spec_avc, DeinterlaceTest._default_modes_))
  def test(self, case, method, rate):
    vars(self).update(spec_avc[case].copy())
    vars(self).update(case = case, method = method, rate = rate)
    self.deinterlace()

spec_mpeg2 = load_test_spec("vpp", "deinterlace", "mpeg2")
class mpeg2(DeinterlaceTest):
  def before(self):
    self.ffdecoder = "-c:v mpeg2_qsv"
    super(mpeg2, self).before()

  @platform_tags(set(MPEG2_DECODE_PLATFORMS) & set(VPP_PLATFORMS))
  @slash.requires(*have_ffmpeg_decoder("mpeg2_qsv"))
  @slash.parametrize(
    *gen_vpp_deinterlace_parameters2(
      spec_mpeg2, DeinterlaceTest._default_modes_))
  def test(self, case, method, rate):
    vars(self).update(spec_mpeg2[case].copy())
    vars(self).update(case = case, method = method, rate = rate)
    self.deinterlace()

spec_vc1 = load_test_spec("vpp", "deinterlace", "vc1")
class vc1(DeinterlaceTest):
  def before(self):
    self.ffdecoder = "-c:v vc1_qsv"
    super(vc1, self).before()

  @platform_tags(set(VC1_DECODE_PLATFORMS) & set(VPP_PLATFORMS))
  @slash.requires(*have_ffmpeg_decoder("vc1_qsv"))
  @slash.parametrize(
    *gen_vpp_deinterlace_parameters2(
      spec_vc1, DeinterlaceTest._default_modes_))
  def test(self, case, method, rate):
    vars(self).update(spec_vc1[case].copy())
    vars(self).update(case = case, method = method, rate = rate)
    self.deinterlace()
