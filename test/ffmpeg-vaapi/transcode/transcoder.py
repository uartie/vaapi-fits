###
### Copyright (C) 2018-2019 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

from ....lib import *
from ..util import *
import os

@slash.requires(have_ffmpeg)
@slash.requires(have_ffmpeg_vaapi_accel)
@platform_tags(ALL_PLATFORMS)
class TranscoderTest(slash.Test):
  requirements = dict(
    # ffmpeg-vaapi HW decoders are built-in
    decode = {
      "avc" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_decoder("h264"), "h264"),
        hw = (AVC_DECODE_PLATFORMS, (True, True), None),
      ),
      "hevc-8" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_decoder("hevc"), "hevc"),
        hw = (HEVC_DECODE_8BIT_PLATFORMS, (True, True), None),
      ),
      "mpeg2" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_decoder("mpeg2video"), "mpeg2video"),
        hw = (MPEG2_DECODE_PLATFORMS, (True, True), None),
      ),
      "mjpeg" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_decoder("mjpeg"), "mjpeg"),
        hw = (JPEG_DECODE_PLATFORMS, (True, True), None),
      ),
      "vc1" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_decoder("vc1"), "vc1"),
        hw = (VC1_DECODE_PLATFORMS, (True, True), None),
      ),
    },
    encode = {
      "avc" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_encoder("libx264"), "libx264"),
        hw = (AVC_ENCODE_PLATFORMS, have_ffmpeg_encoder("h264_vaapi"), "h264_vaapi"),
      ),
      "hevc-8" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_encoder("libx265"), "libx265"),
        hw = (HEVC_ENCODE_8BIT_PLATFORMS, have_ffmpeg_encoder("hevc_vaapi"), "hevc_vaapi"),
      ),
      "mpeg2" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_encoder("mpeg2video"), "mpeg2video"),
        hw = (MPEG2_ENCODE_PLATFORMS, have_ffmpeg_encoder("mpeg2_vaapi"), "mpeg2_vaapi"),
      ),
      "mjpeg" : dict(
        sw = (ALL_PLATFORMS, have_ffmpeg_encoder("mjpeg"), "mjpeg"),
        hw = (JPEG_ENCODE_PLATFORMS, have_ffmpeg_encoder("mjpeg_vaapi"), "mjpeg_vaapi"),
      ),
    }
  )

  # hevc implies hevc 8 bit
  requirements["encode"]["hevc"] = requirements["encode"]["hevc-8"]
  requirements["decode"]["hevc"] = requirements["decode"]["hevc-8"]

  def before(self):
    self.refctx = []
 
  def get_requirements_data(self, ttype, codec, mode):
    return  self.requirements[ttype].get(
      codec, {}).get(
        mode, ([], (False, "{}:{}:{}".format(ttype, codec, mode)), None))

  def get_decoder(self, codec, mode):
    _, _, decoder = self.get_requirements_data("decode", codec, mode)
    assert decoder is not None, "failed to find a suitable decoder: {}:{}".format(codec, mode)
    return decoder.format(**vars(self))

  def get_encoder(self, codec, mode):
    _, _, encoder = self.get_requirements_data("encode", codec, mode)
    assert encoder is not None, "failed to find a suitable encoder: {}:{}".format(codec, mode)
    return encoder.format(**vars(self))

  def get_file_ext(self, codec):
    return {
      "avc"     : "h264",
      "hevc"    : "h265",
      "hevc-8"  : "h265",
      "mpeg2"   : "m2v",
      "mjpeg"   : "mjpeg",
    }.get(codec, "???")

  def validate_spec(self):
    from slash.utils.pattern_matching import Matcher

    assert len(self.outputs), "Invalid test case specification, outputs data empty"
    assert self.mode in ["sw", "hw"], "Invalid test case specification as mode type not valid"

    # generate platform list based on test runtime parameters
    iplats, ireq, _ =  self.get_requirements_data("decode", self.codec, self.mode)
    platforms = set(iplats)
    requires = [ireq,]

    for output in self.outputs:
      codec = output["codec"]
      mode  = output["mode"]
      assert mode in ["sw", "hw"], "Invalid test case specification as output mode type not valid"
      oplats, oreq, _ = self.get_requirements_data("encode", codec, mode)
      platforms &= set(oplats)
      requires.append(oreq)

    # create matchers based on command-line filters
    matchers = [Matcher(s) for s in slash.config.root.run.filter_strings]

    # check if user supplied any platform tag on command line
    pmatch = any(map(lambda p: any([m.matches(p) for m in matchers]), ALL_PLATFORMS))

    # if user supplied a platform tag, check if this test can support it via the
    # test param-based required platforms
    if pmatch and not any(map(lambda p: any([m.matches(p) for m in matchers]), platforms)):
      slash.skip_test("unsupported platform")

    # check required
    if not all([t for t,m in requires]):
      slash.skip_test(
        "One or more software requirements not met: {}".format(
          str([m for t,m in requires if not t])))

  def gen_input_opts(self):
    opts = ""

    if "hw" == self.mode:
      opts += " -hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -hwaccel_output_format vaapi"
    else:
      decoder = self.get_decoder(self.codec, self.mode)
      opts += " -vaapi_device /dev/dri/renderD128 -c:v {}".format(decoder)

    opts += " -i {source}"

    return opts.format(**vars(self))

  def gen_output_opts(self):
    self.goutputs = dict()

    opts = "-an"

    for n, output in enumerate(self.outputs):
      codec = output["codec"]
      mode = output["mode"]
      encoder = self.get_encoder(codec, mode)
      ext = self.get_file_ext(codec)

      for channel in xrange(output.get("channels", 1)):
        if "sw" == mode and "hw" == self.mode:
          opts += " -vf 'hwdownload,format=nv12'"
        elif "hw" == mode and "sw" == self.mode:
          opts += " -vf 'format=nv12,hwupload'"

        opts += " -c:v {}".format(encoder)
        opts += " -vframes {frames}"

        ofile = get_media()._test_artifact(
          "{}_{}_{}.{}".format(self.case, n, channel, ext))
        opts += " -y {}".format(ofile)

        self.goutputs.setdefault(n, list()).append(ofile)

    # dump decoded source to yuv for reference comparison
    self.srcyuv = get_media()._test_artifact(
      "src_{case}.yuv".format(**vars(self)))
    if "hw" == self.mode:
      opts += " -vf 'hwdownload,format=nv12'"
    opts += " -pix_fmt yuv420p -f rawvideo"
    opts += " -vframes {frames} -y {srcyuv}"

    return opts.format(**vars(self))

  def check_output(self):
    m = re.search(
      "not supported for hardware decode", self.output, re.MULTILINE)
    assert m is None, "Failed to use hardware decode"

    m = re.search(
      "hwaccel initialisation returned error", self.output, re.MULTILINE)
    assert m is None, "Failed to use hardware decode"

  def transcode(self):
    self.validate_spec()
    iopts = self.gen_input_opts()
    oopts = self.gen_output_opts()

    get_media().test_call_timeout = vars(self).get("call_timeout", 0)
    self.output = call("ffmpeg -v verbose {} {}".format(iopts, oopts))

    self.check_output()

    for n, output in enumerate(self.outputs):
      for channel in xrange(output.get("channels", 1)):
        encoded = self.goutputs[n][channel]
        yuv = get_media()._test_artifact(
          "{}_{}_{}.yuv".format(self.case, n, channel))
        call(
          "ffmpeg -i {} -pix_fmt yuv420p -vframes {}"
          " -y {}".format(encoded, self.frames, yuv))
        self.check_metrics(yuv, refctx = [(n, channel)])
        # delete yuv file after each iteration
        get_media()._purge_test_artifact(yuv)

  def check_metrics(self, yuv, refctx):
    get_media().baseline.check_psnr(
      psnr = calculate_psnr(
        self.srcyuv, yuv,
        self.width, self.height,
        self.frames),
      context = self.refctx + refctx,
    )
