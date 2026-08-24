"""Check every conversion against an independent implementation.

The maths here is standard and published, so it can be validated rather
than trusted. These tests exist because three real errors survived a full
unit-test suite that only ever checked shapes, dtypes and ranges:

  * Jzazbz skipped the b/g pre-scaling of Safdar et al. eq. 8-9 and used
    d_0 where the curve constant d = -0.56 belongs, leaving Jz out by ~80%
    of its own range;
  * DIN99 dropped the 0.7 factor DIN 6176 applies to f, leaving a99/b99
    out by several units;
  * nothing compared any output to a reference at all.

Skipped when the reference libraries are absent, so the suite still runs
on a bare install:

    pip install colour-science scikit-image
"""
import numpy as np
import pytest

colour = pytest.importorskip("colour", reason="needs colour-science")
skc = pytest.importorskip("skimage.color", reason="needs scikit-image")

import pygeopalette as gp


@pytest.fixture(scope="module")
def sample():
    rng = np.random.default_rng(7)
    N = 48
    R = rng.integers(0, 256, (N, N), dtype=np.uint8)
    G = rng.integers(0, 256, (N, N), dtype=np.uint8)
    B = rng.integers(0, 256, (N, N), dtype=np.uint8)
    rgb01 = np.stack([R, G, B], -1).astype(np.float64) / 255.0
    return R, G, B, rgb01, colour.sRGB_to_XYZ(rgb01)


def _close(got, ref, tol):
    d = np.abs(np.asarray(got, dtype=np.float64) - np.asarray(ref, dtype=np.float64))
    assert d.max() < tol, f"max|diff| = {d.max():.6g}, tolerance {tol}"


# tolerances are set by the module's float32 storage, not by taste: the PQ
# curve in Jzazbz carries an exponent of 134, which turns a float32 input
# error of ~1e-7 into ~1e-5 on the output.

def test_lab(sample):
    R, G, B, rgb01, _ = sample
    c, _ = gp.convertbands(R, G, B, "lab")
    ref = skc.rgb2lab(rgb01)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-2)


def test_luv(sample):
    R, G, B, rgb01, _ = sample
    c, _ = gp.convertbands(R, G, B, "luv")
    ref = skc.rgb2luv(rgb01)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-2)


def test_hsv(sample):
    R, G, B, rgb01, _ = sample
    c, _ = gp.convertbands(R, G, B, "hsv")
    ref = skc.rgb2hsv(rgb01)
    _close(c[0], ref[..., 0] * 360.0, 1e-2)
    _close(c[1], ref[..., 1], 1e-4)
    _close(c[2], ref[..., 2], 1e-4)


def test_hsl(sample):
    R, G, B, rgb01, _ = sample
    c, _ = gp.convertbands(R, G, B, "hsl")
    ref = colour.RGB_to_HSL(rgb01)
    _close(c[0], ref[..., 0] * 360.0, 1e-2)
    _close(c[1], ref[..., 1], 1e-4)
    _close(c[2], ref[..., 2], 1e-4)


def test_xyY(sample):
    R, G, B, _, XYZ = sample
    c, _ = gp.convertbands(R, G, B, "xyY")
    ref = colour.XYZ_to_xyY(XYZ)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-3)


def test_oklab(sample):
    R, G, B, _, XYZ = sample
    c, _ = gp.convertbands(R, G, B, "oklab")
    ref = colour.XYZ_to_Oklab(XYZ)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-3)


def test_ycbcr_is_studio_swing(sample):
    R, G, B, rgb01, _ = sample
    c, _ = gp.convertbands(R, G, B, "ycbcr")
    ref = colour.RGB_to_YCbCr(rgb01, K=colour.WEIGHTS_YCBCR["ITU-R BT.601"],
                              out_legal=True, out_int=False, out_bits=8)
    for i in range(3):
        _close(c[i], ref[..., i] * 255.0, 1e-2)


def test_ycbcr_endpoints():
    """Black lands on 16 and white on 235: studio range, not full range."""
    z = np.zeros((2, 2), dtype=np.uint8)
    f = np.full((2, 2), 255, dtype=np.uint8)
    (Y, Cb, Cr), _ = gp.convertbands(z, z, z, "ycbcr")
    assert Y[0, 0] == pytest.approx(16.0, abs=1e-3)
    (Y, Cb, Cr), _ = gp.convertbands(f, f, f, "ycbcr")
    assert Y[0, 0] == pytest.approx(235.0, abs=1e-3)


def test_jzazbz(sample):
    """Guards both the b/g pre-scaling and the d = -0.56 curve constant."""
    R, G, B, _, XYZ = sample
    c, _ = gp.convertbands(R, G, B, "jzazbz")
    # the module assumes an SDR peak of 203 cd/m2, per ITU-R BT.2408
    ref = colour.XYZ_to_Jzazbz(XYZ * 203.0)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-4)


def test_jzczhz_matches_the_cartesian_form(sample):
    R, G, B, _, XYZ = sample
    ref = colour.XYZ_to_Jzazbz(XYZ * 203.0)
    Cz = np.hypot(ref[..., 1], ref[..., 2])
    c, _ = gp.convertbands(R, G, B, "jzczhz")
    _close(c[0], ref[..., 0], 1e-4)
    _close(c[1], Cz, 1e-4)
    # hue is left out: it is ill-conditioned as Cz -> 0, where it means
    # nothing anyway. test_jzczhz_hue_where_chroma_exists covers it.


def test_jzczhz_hue_where_chroma_exists(sample):
    R, G, B, _, XYZ = sample
    ref = colour.XYZ_to_Jzazbz(XYZ * 203.0)
    Cz = np.hypot(ref[..., 1], ref[..., 2])
    hz = np.degrees(np.arctan2(ref[..., 2], ref[..., 1])) % 360.0
    c, _ = gp.convertbands(R, G, B, "jzczhz")
    m = Cz > 0.05                       # away from neutral
    d = np.abs(c[2].astype(np.float64) - hz)
    d = np.minimum(d, 360.0 - d)        # angular wrap
    assert d[m].max() < 0.1


def test_din99(sample):
    """Guards the 0.7 factor DIN 6176 applies to f."""
    R, G, B, _, XYZ = sample
    c, _ = gp.convertbands(R, G, B, "dlab")
    ref = colour.Lab_to_DIN99(colour.XYZ_to_Lab(XYZ))
    for i in range(3):
        _close(c[i + 3], ref[..., i], 1e-2)


def test_dlab_first_three_channels_are_plain_lab(sample):
    R, G, B, rgb01, _ = sample
    c, names = gp.convertbands(R, G, B, "dlab")
    assert names[:3] == ["L", "a", "b"]
    ref = skc.rgb2lab(rgb01)
    for i in range(3):
        _close(c[i], ref[..., i], 1e-2)


@pytest.mark.parametrize("space", ["lab", "oklab", "hsv", "hsl"])
def test_round_trip(space):
    """The inverse returns [0,1] floats while the forward takes 0-255 uint8."""
    rng = np.random.default_rng(2)
    R = rng.integers(0, 256, (32, 32), dtype=np.uint8)
    G = rng.integers(0, 256, (32, 32), dtype=np.uint8)
    B = rng.integers(0, 256, (32, 32), dtype=np.uint8)
    fwd = getattr(gp, f"rgb_to_{space}")
    inv = getattr(gp, f"{space}_to_rgb")
    R2, G2, B2 = inv(*fwd(R, G, B))
    for orig, back in ((R, R2), (G, G2), (B, B2)):
        _close(back * 255.0, orig.astype(np.float64), 0.05)


@pytest.mark.parametrize("rgb", [(0, 0, 0), (255, 255, 255), (128, 128, 128),
                                 (255, 0, 0), (0, 255, 255)])
def test_no_runtime_warnings_on_edge_colours(rgb):
    """Achromatic pixels divide by zero unless the code indexes first.

    Grey, white, black and shadow are everywhere in a raster; a conversion
    that warns on them buries the caller in noise.
    """
    a = np.full((4, 4), rgb[0], dtype=np.uint8)
    b = np.full((4, 4), rgb[1], dtype=np.uint8)
    c = np.full((4, 4), rgb[2], dtype=np.uint8)
    with np.errstate(all="raise"):
        for space in gp.available_spaces():
            gp.convertbands(a, b, c, space)


# ── CIECAM02 (rgb_to_cam02) ───────────────────────────────────────────

def _cam_reference(R, G, B, L_A, Y_b, sur):
    """colour-science CIECAM02 on the SAME XYZ and white the package uses.

    rgb_to_cam02 builds XYZ from pygeopalette's own sRGB->XYZ matrix, which
    differs from colour's in the last two decimals. Feeding colour that same
    XYZ isolates the appearance model from the RGB->XYZ step; otherwise a
    correct CIECAM02 looks wrong by ~5e-3 for reasons that have nothing to do
    with it.
    """
    from pygeopalette.conversions import _rgb_to_xyz, _CAM02_WHITE_D65
    XYZ = np.stack(_rgb_to_xyz(R, G, B), -1) * 100.0
    return colour.XYZ_to_CIECAM02(
        XYZ, _CAM02_WHITE_D65, L_A=L_A, Y_b=Y_b,
        surround=colour.VIEWING_CONDITIONS_CIECAM02[sur.capitalize()])


@pytest.mark.parametrize("sur,L_A,Y_b", [("average", 64, 20),
                                         ("dim", 100, 20),
                                         ("dark", 318, 25)])
def test_cam02_matches_colour_science(sample, sur, L_A, Y_b):
    """Full CIECAM02 forward, every surround. Guards the N_c constants too:
    N_c feeds chroma directly, so a wrong one shows up here as a C mismatch
    for that surround only."""
    R, G, B, _, _ = sample
    J, C, h = gp.rgb_to_cam02(R, G, B, L_A=L_A, Y_b=Y_b, surround=sur)
    ref = _cam_reference(R, G, B, L_A, Y_b, sur)
    _close(J, ref.J, 1e-3)
    _close(C, np.asarray(ref.C), 1e-3)
    dh = np.abs(h.astype(np.float64) - np.asarray(ref.h))
    dh = np.minimum(dh, 360.0 - dh)
    assert dh.max() < 1e-2, f"hue max diff {dh.max()}"


def test_cam02_viewing_conditions_actually_matter(sample):
    """If the surround argument did nothing, it would be a fake parameter."""
    R, G, B, _, _ = sample
    J_avg = gp.rgb_to_cam02(R, G, B, surround="average")[0]
    J_dark = gp.rgb_to_cam02(R, G, B, surround="dark")[0]
    assert np.abs(J_avg.astype(float) - J_dark.astype(float)).max() > 1.0


@pytest.mark.parametrize("rgb", [(0, 0, 0), (255, 255, 255), (128, 128, 128),
                                 (1, 1, 1)])
def test_cam02_achromatic_is_finite_and_matches(rgb):
    """Black/grey/white push CIECAM02 to divide by a sum of cone responses
    that approaches zero. Output must stay finite (not NaN), and must still
    match the reference — black lands on J=0/C=0, grey and white on a small
    non-zero chroma because D65 is not exactly on the sRGB grey axis."""
    a = np.full((4, 4), rgb[0], dtype=np.uint8)
    b = np.full((4, 4), rgb[1], dtype=np.uint8)
    c = np.full((4, 4), rgb[2], dtype=np.uint8)
    with np.errstate(all="raise"):
        J, C, h = gp.rgb_to_cam02(a, b, c)
    for arr in (J, C, h):
        assert np.isfinite(arr).all()
    ref = _cam_reference(a, b, c, 64.0, 20.0, "average")
    _close(J, ref.J, 1e-3)
    _close(C, np.asarray(ref.C), 1e-3)


def test_cam02_rejects_bad_arguments(sample):
    R, G, B, _, _ = sample
    for bad in ("Average", "bright", ""):
        with pytest.raises(ValueError):
            gp.rgb_to_cam02(R, G, B, surround=bad)
    with pytest.raises(ValueError):
        gp.rgb_to_cam02(R, G, B, whitepoint=[95.0, 100.0])  # needs 3
