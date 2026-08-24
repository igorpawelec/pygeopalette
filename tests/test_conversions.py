"""
tests/test_conversions.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for pygeopalette color space conversions.
Uses synthetic 10×10 uint8 arrays — no rasterio needed.
"""

import numpy as np
import pytest

from pygeopalette import (
    available_spaces,
    convertbands,
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
    rgb_to_ycbcr,
    rgb_to_jzczhz,
    lab_to_rgb,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def rgb_bands():
    """Synthetic 10×10 RGB bands (uint8)."""
    rng = np.random.default_rng(42)
    R = rng.integers(0, 256, (10, 10), dtype=np.uint8)
    G = rng.integers(0, 256, (10, 10), dtype=np.uint8)
    B = rng.integers(0, 256, (10, 10), dtype=np.uint8)
    return R, G, B


@pytest.fixture
def white_pixel():
    """Single white pixel as 1×1 arrays."""
    return (
        np.array([[255]], dtype=np.uint8),
        np.array([[255]], dtype=np.uint8),
        np.array([[255]], dtype=np.uint8),
    )


@pytest.fixture
def black_pixel():
    """Single black pixel as 1×1 arrays."""
    return (
        np.array([[0]], dtype=np.uint8),
        np.array([[0]], dtype=np.uint8),
        np.array([[0]], dtype=np.uint8),
    )


# ── Basic shape / dtype tests ─────────────────────────────────────────────

@pytest.mark.parametrize("space", available_spaces())
def test_convertbands_shape_dtype(rgb_bands, space):
    """Every space returns float32 arrays with correct shape."""
    R, G, B = rgb_bands
    comps, names = convertbands(R, G, B, space)
    assert len(comps) == len(names)
    for c in comps:
        assert c.shape == (10, 10)
        assert c.dtype == np.float32


def test_available_spaces_count():
    """All registered spaces are exposed."""
    # not a hardcoded count: that only ever catches the person who adds
    # a space and forgets this line, which is not what it is for
    spaces = available_spaces()
    assert len(spaces) >= 13
    assert spaces == sorted(spaces), 'available_spaces() must be sorted'
    assert len(set(spaces)) == len(spaces), 'duplicate space name'


def test_unknown_space_raises(rgb_bands):
    with pytest.raises(ValueError, match="Unknown space"):
        convertbands(*rgb_bands, "nonexistent")


# ── Per-space sanity checks ───────────────────────────────────────────────

def test_hsl_white(white_pixel):
    H, S, L = rgb_to_hsl(*white_pixel)
    assert L[0, 0] == pytest.approx(1.0, abs=0.01)


def test_hsv_white(white_pixel):
    H, S, V = rgb_to_hsv(*white_pixel)
    assert V[0, 0] == pytest.approx(1.0, abs=0.01)
    assert S[0, 0] == pytest.approx(0.0, abs=0.01)


def test_hsi_black(black_pixel):
    H, S, I = rgb_to_hsi(*black_pixel)
    assert I[0, 0] == pytest.approx(0.0, abs=1.0)


def test_lab_white(white_pixel):
    L, a, b = rgb_to_lab(*white_pixel)
    assert L[0, 0] == pytest.approx(100.0, abs=1.0)


def test_lab_black(black_pixel):
    L, a, b = rgb_to_lab(*black_pixel)
    assert L[0, 0] == pytest.approx(0.0, abs=1.0)


def test_dlab_returns_six(rgb_bands):
    result = rgb_to_dlab(*rgb_bands)
    assert len(result) == 6


def test_oklab_range(rgb_bands):
    L, a, b = rgb_to_oklab(*rgb_bands)
    assert L.min() >= -0.1
    assert L.max() <= 1.5


def test_luv_black(black_pixel):
    L, u, v = rgb_to_luv(*black_pixel)
    assert L[0, 0] == pytest.approx(0.0, abs=0.1)


def test_lchab_hue_range(rgb_bands):
    L, C, H = rgb_to_lchab(*rgb_bands)
    assert H.min() >= 0.0
    assert H.max() <= 360.0


def test_lchuv_hue_range(rgb_bands):
    L, C, H = rgb_to_lchuv(*rgb_bands)
    assert H.min() >= 0.0
    assert H.max() <= 360.0


def test_xyY_chromaticity(white_pixel):
    x, y, Y = rgb_to_xyY(*white_pixel)
    # x + y should be < 1 for any real color
    assert (x[0, 0] + y[0, 0]) <= 1.01


def test_jch_range(rgb_bands):
    J, C, H = rgb_to_jch(*rgb_bands)
    assert J.min() >= 0.0
    assert H.max() <= 360.0


def test_ycbcr_range(rgb_bands):
    Y, Cb, Cr = rgb_to_ycbcr(*rgb_bands)
    assert Y.min() >= 15.0
    assert Y.max() <= 240.0


def test_jzczhz_hue_range():
    az = np.array([[0.1, -0.1]], dtype=np.float32)
    bz = np.array([[0.05, 0.05]], dtype=np.float32)
    Jz = np.array([[0.5, 0.5]], dtype=np.float32)
    _, Cz, hz = rgb_to_jzczhz(Jz, az, bz)
    assert hz.min() >= 0.0
    assert hz.max() < 360.0


# ── Round-trip: RGB → LAB → RGB ──────────────────────────────────────────

def test_lab_roundtrip(rgb_bands):
    """Round-trip RGB→LAB→RGB.  Uses simplified (no-gamma) matrix,
    so we only check that the inverse is directionally correct."""
    R, G, B = rgb_bands
    L, a, b = rgb_to_lab(R, G, B)
    R2, G2, B2 = lab_to_rgb(L, a, b)
    # The forward path skips sRGB gamma, so roundtrip is approximate.
    # Check correlation rather than exact match.
    Rn = R.astype(np.float32) / 255.0
    corr = np.corrcoef(np.clip(R2, 0, 1).ravel(), Rn.ravel())[0, 1]
    assert corr > 0.90, f"Roundtrip correlation too low: {corr:.3f}"
