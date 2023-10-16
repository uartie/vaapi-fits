###
### Copyright (C) 2023 Intel Corporation
###
### SPDX-License-Identifier: BSD-3-Clause
###

import enum

@enum.unique
class Profile(str, enum.Enum):
  NONE                  = "none"
  HIGH                  = "high"
  MAIN                  = "main"
  BASELINE              = "baseline"
  CONSTRAINED_BASELINE  = "constrained-baseline"
  MULTIVIEW_HIGH        = "multiview-high"
  STEREO_HIGH           = "stereo-high"
  SCC                   = "scc"
  SCC_444               = "scc-444"
  MAIN_444              = "main444"
  MAIN_10               = "main10"
  MAIN_10_444           = "main444-10"
  MAIN_12               = "main-12"
  PROFILE0              = "profile0"
  PROFILE1              = "profile1"
  PROFILE2              = "profile2"
  PROFILE3              = "profile3"

  def __str__(self):
    return self.value
