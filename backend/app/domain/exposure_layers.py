from enum import Enum


class ExposureLayer(str, Enum):
    SURFACE = "surface"
    DEEP = "deep"
    CONSTRAINED_DARK = "constrained_dark"
