"""
geopalette — Color space conversions for geospatial raster data.
"""

__version__ = "0.6.2"
__author__ = "Igor Pawelec"

from .conversions import (
    rgb_to_hsl,
    rgb_to_hsv,
    rgb_to_hsi,
    rgb_to_lab,
    rgb_to_dlab,
    rgb_to_oklab,
    rgb_to_luv,
    rgb_to_lchab,
    rgb_to_lchuv,
    rgb_to_xyY,
    rgb_to_jch,
    rgb_to_cam02,
    rgb_to_ycbcr,
    rgb_to_jzazbz,
    rgb_to_jzczhz,
    lab_to_rgb,
    oklab_to_rgb,
    hsv_to_rgb,
    hsl_to_rgb,
    available_spaces,
    convertbands,
)


# Declared explicitly rather than left to a `# noqa: F401` comment: pyflakes
# does not read noqa (that is flake8), so without __all__ every re-export
# below reads as an unused import and any pyflakes-based lint fails.
__all__ = [
    "rgb_to_hsl",
    "rgb_to_hsv",
    "rgb_to_hsi",
    "rgb_to_lab",
    "rgb_to_dlab",
    "rgb_to_oklab",
    "rgb_to_luv",
    "rgb_to_lchab",
    "rgb_to_lchuv",
    "rgb_to_xyY",
    "rgb_to_jch",
    "rgb_to_cam02",
    "rgb_to_ycbcr",
    "rgb_to_jzazbz",
    "rgb_to_jzczhz",
    "lab_to_rgb",
    "oklab_to_rgb",
    "hsv_to_rgb",
    "hsl_to_rgb",
    "available_spaces",
    "convertbands",
]
