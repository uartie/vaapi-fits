###
### Copyright (C) 2018-2019 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

from ....lib import *
from ..util import *
from .decoder import DecoderTest

spec = load_test_spec("vp9", "decode", "8bit")

class default(DecoderTest):
  def before(self):
    # default metric
    self.metric = dict(type = "ssim", miny = 1.0, minu = 1.0, minv = 1.0)
    super(default, self).before()

  @platform_tags(VP9_DECODE_8BIT_PLATFORMS)
  @slash.requires(*have_ffmpeg_decoder("vp9_qsv"))
  @slash.parametrize(("case"), sorted(spec.keys()))
  def test(self, case):
    vars(self).update(spec[case].copy())
    vars(self).update(
      case      = case,
      ffdecoder = "vp9_qsv",
      hwformat  = "nv12",
    )
    self.decode()

  def check_output(self):
    m = re.search("No support for codec vp9", self.output, re.MULTILINE)
    assert m is None, "Failed to use hardware decode"
    super(default, self).check_output()
