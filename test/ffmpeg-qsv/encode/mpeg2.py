###
### Copyright (C) 2018-2019 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

from ....lib import *
from ..util import *
from .encoder import EncoderTest

spec      = load_test_spec("mpeg2", "encode")
spec_r2r  = load_test_spec("mpeg2", "encode", "r2r")

class MPEG2EncoderTest(EncoderTest):
  def before(self):
    vars(self).update(
      codec     = "mpeg2",
      ffencoder = "mpeg2_qsv",
      ffdecoder = "mpeg2_qsv",
    )
    super(MPEG2EncoderTest, self).before()

  def get_file_ext(self):
    return "m2v"

class cqp(MPEG2EncoderTest):
  def init(self, tspec, case, gop, bframes, qp, quality):
    self.caps = platform.get_caps("encode", "mpeg2")
    vars(self).update(tspec[case].copy())
    vars(self).update(
      bframes = bframes,
      case    = case,
      gop     = gop,
      mqp     = mapRangeInt(qp, [0, 100], [1, 51]),
      qp      = qp,
      quality = quality,
      rcmode  = "cqp",
    )

  @slash.requires(*platform.have_caps("encode", "mpeg2"))
  @slash.requires(*have_ffmpeg_encoder("mpeg2_qsv"))
  @slash.requires(*have_ffmpeg_decoder("mpeg2_qsv"))
  @slash.parametrize(*gen_mpeg2_cqp_parameters(spec))
  def test(self, case, gop, bframes, qp, quality):
    self.init(spec, case, gop, bframes, qp, quality)
    self.encode()

  @slash.requires(*platform.have_caps("encode", "mpeg2"))
  @slash.requires(*have_ffmpeg_encoder("mpeg2_qsv"))
  @slash.requires(*have_ffmpeg_decoder("mpeg2_qsv"))
  @slash.parametrize(*gen_mpeg2_cqp_parameters(spec_r2r))
  def test_r2r(self, case, gop, bframes, qp, quality):
    self.init(spec_r2r, case, gop, bframes, qp, quality)
    vars(self).setdefault("r2r", 5)
    self.encode()
