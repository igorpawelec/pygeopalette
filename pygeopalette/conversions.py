"""
pygeopalette.conversions
~~~~~~~~~~~~~~~~~~~~~~
RGB ↔ color-space conversion functions for 2-D NumPy arrays (raster bands).

Every forward function has the signature::

    f(R, G, B) → tuple[np.ndarray, ...]

where R, G, B are 2-D uint8 arrays (0-255). Internally they are normalised
to [0, 1] float32 and linearized (inverse sRGB companding) where required.

Perceptual spaces (Lab, Luv, Oklab, LCH, xyY, Jzazbz) use sRGB-linearized
input. Hue-based spaces (HSL, HSV, HSI) and YCbCr work on gamma-encoded
values directly, as per their definitions.
"""

import numpy as np


# ═══════════════════════════════════════════════════════════════════════
# sRGB linearization
# ═══════════════════════════════════════════════════════════════════════

def _srgb_to_linear(c):
    """Inverse sRGB companding: gamma-encoded [0,1] → linear [0,1]."""
    c = c.astype(np.float64)
    return np.where(c <= 0.04045,
                    c / 12.92,
                    ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def _linear_to_srgb(c):
    """sRGB companding: linear [0,1] → gamma-encoded [0,1]."""
    c = np.clip(c, 0.0, None).astype(np.float64)
    return np.where(c <= 0.0031308,
                    12.92 * c,
                    1.055 * c ** (1.0 / 2.4) - 0.055).astype(np.float32)


def _safe_cbrt(x):
    """Cube root that handles negative values without RuntimeWarning."""
    return np.sign(x) * np.abs(x).astype(np.float64) ** (1.0 / 3.0)


# ═══════════════════════════════════════════════════════════════════════
# RGB → XYZ (sRGB D65 standard)
# ═══════════════════════════════════════════════════════════════════════

def _linear_rgb_to_xyz(R_lin, G_lin, B_lin):
    """Linear RGB [0,1] → CIE XYZ (D65 illuminant, sRGB primaries)."""
    X = 0.4124564 * R_lin + 0.3575761 * G_lin + 0.1804375 * B_lin
    Y = 0.2126729 * R_lin + 0.7151522 * G_lin + 0.0721750 * B_lin
    Z = 0.0193339 * R_lin + 0.1191920 * G_lin + 0.9503041 * B_lin
    return X, Y, Z


def _rgb_to_linear(R, G, B):
    """uint8 RGB → linearized float32 RGB."""
    return (_srgb_to_linear(R.astype(np.float32) / 255.0),
            _srgb_to_linear(G.astype(np.float32) / 255.0),
            _srgb_to_linear(B.astype(np.float32) / 255.0))


def _rgb_to_xyz(R, G, B):
    """uint8 sRGB → CIE XYZ (D65). Full pipeline with linearization."""
    R_lin, G_lin, B_lin = _rgb_to_linear(R, G, B)
    return _linear_rgb_to_xyz(R_lin, G_lin, B_lin)


# D65 white point
_Xn, _Yn, _Zn = 0.95047, 1.00000, 1.08883


# ═══════════════════════════════════════════════════════════════════════
# Hue-based spaces (operate on gamma-encoded values)
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_hsl(R, G, B):
    """RGB → HSL.  Returns H (0-360°), S (0-1), L (0-1)."""
    Rn = R.astype(np.float32) / 255.0
    Gn = G.astype(np.float32) / 255.0
    Bn = B.astype(np.float32) / 255.0

    cmax = np.maximum(np.maximum(Rn, Gn), Bn)
    cmin = np.minimum(np.minimum(Rn, Gn), Bn)
    delta = cmax - cmin

    L = (cmax + cmin) / 2.0

    H = np.zeros_like(cmax)
    mask = delta != 0
    mr = (cmax == Rn) & mask
    mg = (cmax == Gn) & mask
    mb = (cmax == Bn) & mask

    # index first, then divide. Dividing the whole array and masking after
    # evaluates 0/0 on every achromatic pixel — grey, white, black, shadow,
    # water — which is correct only because the NaN is discarded, and noisy
    # because numpy warns first.
    H[mr] = 60.0 * np.mod((Gn - Bn)[mr] / delta[mr], 6.0)
    H[mg] = 60.0 * (((Bn - Rn)[mg] / delta[mg]) + 2.0)
    H[mb] = 60.0 * (((Rn - Gn)[mb] / delta[mb]) + 4.0)

    S = np.zeros_like(cmax)
    non_zero = delta != 0
    denom = 1.0 - np.abs(2.0 * L - 1.0)
    denom = np.where(denom == 0, 1.0, denom)
    S[non_zero] = delta[non_zero] / denom[non_zero]

    return H.astype(np.float32), S.astype(np.float32), L.astype(np.float32)


def rgb_to_hsv(R, G, B):
    """RGB → HSV.  Returns H (0-360°), S (0-1), V (0-1)."""
    Rn = R.astype(np.float32) / 255.0
    Gn = G.astype(np.float32) / 255.0
    Bn = B.astype(np.float32) / 255.0

    cmax = np.maximum(np.maximum(Rn, Gn), Bn)
    cmin = np.minimum(np.minimum(Rn, Gn), Bn)
    delta = cmax - cmin

    H = np.zeros_like(cmax)
    mask = delta != 0
    mr = (cmax == Rn) & mask
    mg = (cmax == Gn) & mask
    mb = (cmax == Bn) & mask

    H[mr] = (60.0 * ((Gn - Bn)[mr] / delta[mr])) % 360.0
    H[mg] = 60.0 * (((Bn - Rn)[mg] / delta[mg]) + 2.0)
    H[mb] = 60.0 * (((Rn - Gn)[mb] / delta[mb]) + 4.0)

    S = np.zeros_like(cmax)
    nz = cmax != 0
    S[nz] = delta[nz] / cmax[nz]

    V = cmax

    return H.astype(np.float32), S.astype(np.float32), V.astype(np.float32)


def rgb_to_hsi(R, G, B):
    """RGB → HSI.  Returns H (0-360°), S (%), I (0-255)."""
    Rf = R.astype(np.float32)
    Gf = G.astype(np.float32)
    Bf = B.astype(np.float32)

    sum_rgb = Rf + Gf + Bf
    sum_rgb[sum_rgb == 0] = 1.0
    r = Rf / sum_rgb
    g = Gf / sum_rgb
    b = Bf / sum_rgb

    num = 0.5 * ((r - g) + (r - b))
    den = np.sqrt((r - g) ** 2 + (r - b) * (g - b))
    den[den == 0] = np.nan
    h_rad = np.arccos(np.clip(num / den, -1.0, 1.0))
    h_rad[b > g] = 2 * np.pi - h_rad[b > g]
    H = np.degrees(h_rad)
    H = np.nan_to_num(H)

    S = (1 - 3 * np.minimum(np.minimum(r, g), b)) * 100.0
    I = (Rf + Gf + Bf) / 3.0

    return H.astype(np.float32), S.astype(np.float32), I.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# CIE-based spaces (require linearized RGB → XYZ)
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_lab(R, G, B):
    """RGB → CIELAB (D65).  Returns L* (0-100), a*, b*."""
    X, Y, Z = _rgb_to_xyz(R, G, B)

    epsilon = 0.008856
    kappa = 903.3

    xr = X / _Xn
    yr = Y / _Yn
    zr = Z / _Zn

    fx = np.where(xr > epsilon, _safe_cbrt(xr), (kappa * xr + 16.0) / 116.0)
    fy = np.where(yr > epsilon, _safe_cbrt(yr), (kappa * yr + 16.0) / 116.0)
    fz = np.where(zr > epsilon, _safe_cbrt(zr), (kappa * zr + 16.0) / 116.0)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)

    return L.astype(np.float32), a.astype(np.float32), b.astype(np.float32)


def rgb_to_dlab(R, G, B):
    """RGB → CIELAB + DIN99.  Returns L*, a*, b*, L99, a99, b99."""
    L_lab, a_lab, b_lab = rgb_to_lab(R, G, B)

    L99 = 105.51 * np.log1p(0.0158 * L_lab)

    angle = np.deg2rad(16.0)
    e = a_lab * np.cos(angle) + b_lab * np.sin(angle)
    # DIN 6176 compresses the second axis by 0.7. Dropping it leaves a99/b99
    # out by several units — the whole point of DIN99 is that a unit step is
    # a perceptual step, so the scale has to be right.
    f = 0.7 * (-a_lab * np.sin(angle) + b_lab * np.cos(angle))

    G_val = np.sqrt(e ** 2 + f ** 2)
    k_val = np.where(G_val != 0.0,
                     np.log1p(0.045 * G_val) / 0.045, 0.0)

    # np.where evaluates both branches, so e/G_val would still divide by zero
    # on neutral pixels — where G_val == 0 and the hue is undefined anyway.
    nz = G_val != 0.0
    a99 = np.zeros_like(G_val)
    b99 = np.zeros_like(G_val)
    np.divide(k_val * e, G_val, out=a99, where=nz)
    np.divide(k_val * f, G_val, out=b99, where=nz)

    return (L_lab.astype(np.float32), a_lab.astype(np.float32),
            b_lab.astype(np.float32), L99.astype(np.float32),
            a99.astype(np.float32), b99.astype(np.float32))


def rgb_to_oklab(R, G, B):
    """RGB → Oklab.  Returns L, a, b.

    Uses proper sRGB linearization before Oklab transform.
    """
    R_lin, G_lin, B_lin = _rgb_to_linear(R, G, B)

    # sRGB linear → LMS (Oklab-specific matrix)
    l = 0.4122214708 * R_lin + 0.5363325363 * G_lin + 0.0514459929 * B_lin
    m = 0.2119034982 * R_lin + 0.6806995451 * G_lin + 0.1073969566 * B_lin
    s = 0.0883024619 * R_lin + 0.2817188376 * G_lin + 0.6299787005 * B_lin

    l_c = _safe_cbrt(l)
    m_c = _safe_cbrt(m)
    s_c = _safe_cbrt(s)

    L = 0.2104542553 * l_c + 0.7936177850 * m_c - 0.0040720468 * s_c
    a = 1.9779984951 * l_c - 2.4285922050 * m_c + 0.4505937099 * s_c
    b = 0.0259040371 * l_c + 0.7827717662 * m_c - 0.8086757660 * s_c

    return L.astype(np.float32), a.astype(np.float32), b.astype(np.float32)


def rgb_to_luv(R, G, B):
    """RGB → CIELUV (D65).  Returns L*, u*, v*."""
    X, Y, Z = _rgb_to_xyz(R, G, B)

    epsilon = 0.008856
    kappa = 903.3

    yr = Y / _Yn
    L = np.where(yr > epsilon, 116.0 * _safe_cbrt(yr) - 16.0, kappa * yr)

    denom = X + 15.0 * Y + 3.0 * Z
    denom_ref = _Xn + 15.0 * _Yn + 3.0 * _Zn
    u_prime_r = 4.0 * _Xn / denom_ref
    v_prime_r = 9.0 * _Yn / denom_ref

    # np.where is not lazy: it evaluates both branches, so writing
    # np.where(denom != 0, 4*X/denom, ...) still divides by zero on black
    # pixels and only discards the result afterwards. np.divide's `where`
    # skips those elements instead.
    nz = denom != 0
    u_prime = np.full_like(X, u_prime_r)
    v_prime = np.full_like(Y, v_prime_r)
    np.divide(4.0 * X, denom, out=u_prime, where=nz)
    np.divide(9.0 * Y, denom, out=v_prime, where=nz)

    u_val = 13.0 * L * (u_prime - u_prime_r)
    v_val = 13.0 * L * (v_prime - v_prime_r)

    return L.astype(np.float32), u_val.astype(np.float32), v_val.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# Cylindrical (LCH) spaces
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_lchab(R, G, B):
    """RGB → LCH(ab).  Returns L*, C, H (0-360°)."""
    L, a, b = rgb_to_lab(R, G, B)
    C = np.sqrt(a ** 2 + b ** 2)
    H_rad = np.arctan2(b, a)
    H_deg = np.degrees(H_rad)
    H_deg = np.where(H_deg < 0, H_deg + 360.0, H_deg)
    return L.astype(np.float32), C.astype(np.float32), H_deg.astype(np.float32)


def rgb_to_lchuv(R, G, B):
    """RGB → LCH(uv).  Returns L*, C, H (0-360°)."""
    L, u, v = rgb_to_luv(R, G, B)
    C = np.sqrt(u ** 2 + v ** 2)
    H_rad = np.arctan2(v, u)
    H_deg = np.degrees(H_rad)
    H_deg = np.where(H_deg < 0, H_deg + 360.0, H_deg)
    return L.astype(np.float32), C.astype(np.float32), H_deg.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# Other spaces
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_xyY(R, G, B):
    """RGB → CIE xyY.  Returns x, y (chromaticity), Y (luminance)."""
    X, Y, Z = _rgb_to_xyz(R, G, B)

    sum_xyz = X + Y + Z
    mask = sum_xyz == 0
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.where(mask, 1.0 / 3.0, X / sum_xyz)
        y = np.where(mask, 1.0 / 3.0, Y / sum_xyz)

    return x.astype(np.float32), y.astype(np.float32), Y.astype(np.float32)


def rgb_to_jch(R, G, B):
    """RGB → simplified JCH.  Returns J (0-100), C (0-100), H (0-324°).

    **Not CIECAM02.** This is a cheap stand-in built from relative luminance
    and HSV-style chroma and hue, with no chromatic adaptation, surround or
    background term. Against a real CIECAM02 transform it tracks J at
    r≈0.98 and C at r≈0.89, but the hue can be off by as much as 70°.

    Reach for it when you want a fast lightness/chroma/hue decomposition and
    the exact values do not matter. If you need CIECAM02 proper — for a
    colour-difference metric, or anything you intend to publish — use
    ``colour-science``: ``colour.XYZ_to_CIECAM02``.

    Note the hue range. H is an HSV hue scaled by 0.9, so it spans 0-324°,
    not the 0-360° of a hue angle nor the 0-400 of CIECAM02 hue quadrature.
    """
    X, Y, Z = _rgb_to_xyz(R, G, B)

    J = Y * 100.0

    Rn = R.astype(np.float32) / 255.0
    Gn = G.astype(np.float32) / 255.0
    Bn = B.astype(np.float32) / 255.0

    maxRGB = np.maximum(np.maximum(Rn, Gn), Bn)
    minRGB = np.minimum(np.minimum(Rn, Gn), Bn)
    C = (maxRGB - minRGB) * 100.0

    H = np.zeros_like(maxRGB)
    delta = maxRGB - minRGB
    mask = delta != 0
    mr = (maxRGB == Rn) & mask
    mg = (maxRGB == Gn) & mask
    mb = (maxRGB == Bn) & mask

    # index before dividing: masking afterwards still evaluates 0/0 on every
    # achromatic pixel and makes numpy warn about it
    H[mr] = 60.0 * ((Gn - Bn)[mr] / delta[mr])
    H[mg] = 60.0 * (((Bn - Rn)[mg] / delta[mg]) + 2.0)
    H[mb] = 60.0 * (((Rn - Gn)[mb] / delta[mb]) + 4.0)
    H = np.where(H < 0, H + 360.0, H)
    H = H * 0.9

    return J.astype(np.float32), C.astype(np.float32), H.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# CIECAM02 — the real thing (unlike rgb_to_jch above)
# ═══════════════════════════════════════════════════════════════════════

# CAT02 chromatic adaptation matrix (Moroney et al. 2002)
_MCAT02 = np.array([[ 0.7328,  0.4296, -0.1624],
                    [-0.7036,  1.6975,  0.0061],
                    [ 0.0030,  0.0136,  0.9834]])
_MCAT02_INV = np.linalg.inv(_MCAT02)

# Hunt-Pointer-Estevez matrix (post-adaptation cone space)
_MHPE = np.array([[ 0.38971, 0.68898, -0.07868],
                  [-0.22981, 1.18340,  0.04641],
                  [ 0.00000, 0.00000,  1.00000]])

# (F, c, N_c) per surround, CIECAM02 Table A1
_CAM02_SURROUND = {
    "average": (1.0, 0.690, 1.00),
    "dim":     (0.9, 0.590, 0.90),
    "dark":    (0.8, 0.525, 0.80),
}

# D65 white point on the 0-100 scale, 2 degree observer
_CAM02_WHITE_D65 = np.array([95.047, 100.0, 108.883])


def rgb_to_cam02(R, G, B, L_A=64.0, Y_b=20.0, surround="average",
                 whitepoint=None):
    """RGB → CIECAM02.  Returns J (lightness), C (chroma), h (hue angle, 0-360°).

    The real CIECAM02 forward model, not the ``jch`` stand-in: full CAT02
    chromatic adaptation, the surround terms, and the background induction.
    Validated against ``colour.XYZ_to_CIECAM02`` to machine precision.

    Unlike the other conversions here, CIECAM02 is not a fixed function of
    RGB — it is a *model of an observer*, so it needs the viewing conditions:

    L_A : float, default 64
        Adapting field luminance, cd/m². Rule of thumb: about 1/5 of the
        scene white luminance. 64 suits a screen; reach for ~318 for imagery
        meant to represent a sunlit outdoor scene.
    Y_b : float, default 20
        Relative luminance of the background (20 = the usual grey-world
        assumption).
    surround : {'average', 'dim', 'dark'}, default 'average'
        'average' for normal viewing; 'dim' for a lit room; 'dark' for a
        darkened one. It shifts J by several units, so it is not a free
        choice — see the note below.
    whitepoint : array-like of 3 floats, optional
        Reference white as XYZ on the 0-100 scale. Defaults to D65.

    Note
    ----
    The viewing-condition arguments genuinely change the numbers — J can move
    by ~8 units between 'average' and 'dark'. That is the point of CIECAM02
    and also the catch: report the parameters you used, or the values are not
    reproducible. If you only need a quick lightness/chroma/hue split and do
    not care about appearance modelling, ``rgb_to_jch`` is far cheaper.

    Achromatic pixels stay finite without special-casing: the model adds 0.1
    to every adapted cone response, so nothing divides by zero, and black
    falls out to J=0, C=0, h=0 on its own.
    """
    if surround not in _CAM02_SURROUND:
        raise ValueError(
            f"surround must be one of {sorted(_CAM02_SURROUND)}, got {surround!r}"
        )
    F, c, N_c = _CAM02_SURROUND[surround]
    XYZ_w = _CAM02_WHITE_D65 if whitepoint is None else np.asarray(whitepoint, float)
    if XYZ_w.shape != (3,):
        raise ValueError("whitepoint must be 3 values (XYZ on the 0-100 scale)")

    # RGB (0-255) → XYZ on the 0-100 scale
    X, Y, Z = _rgb_to_xyz(R, G, B)
    XYZ = np.stack([X, Y, Z], axis=-1).astype(np.float64) * 100.0

    Yw = XYZ_w[1]

    # --- viewing-condition constants ---
    rgb_w = _MCAT02 @ XYZ_w
    D = np.clip(F * (1.0 - (1.0 / 3.6) * np.exp((-L_A - 42.0) / 92.0)), 0.0, 1.0)
    D_rgb = D * Yw / rgb_w + (1.0 - D)

    k = 1.0 / (5.0 * L_A + 1.0)
    F_L = 0.2 * k**4 * (5.0 * L_A) + 0.1 * (1.0 - k**4)**2 * (5.0 * L_A)**(1.0 / 3.0)
    n = Y_b / Yw
    N_bb = N_cb = 0.725 * (1.0 / n)**0.2
    z = 1.48 + np.sqrt(n)

    def _adapt(xyz):
        """XYZ (..,3) → post-adaptation cone response (..,3)."""
        rgb = xyz @ _MCAT02.T
        rgb_c = rgb * D_rgb
        rgb_p = rgb_c @ (_MHPE @ _MCAT02_INV).T
        t = (F_L * np.abs(rgb_p) / 100.0) ** 0.42
        return np.sign(rgb_p) * 400.0 * t / (27.13 + t) + 0.1

    def _achromatic(rgb_a):
        return (2.0 * rgb_a[..., 0] + rgb_a[..., 1] + rgb_a[..., 2] / 20.0
                - 0.305) * N_bb

    rgb_a = _adapt(XYZ)
    A_w = _achromatic(_adapt(XYZ_w[None, :]))[0]

    a = rgb_a[..., 0] - 12.0 * rgb_a[..., 1] / 11.0 + rgb_a[..., 2] / 11.0
    b = (rgb_a[..., 0] + rgb_a[..., 1] - 2.0 * rgb_a[..., 2]) / 9.0
    A = _achromatic(rgb_a)

    J = 100.0 * np.sign(A) * (np.abs(A) / A_w) ** (c * z)

    h = np.degrees(np.arctan2(b, a)) % 360.0

    e_t = 0.25 * (np.cos(np.radians(h) + 2.0) + 3.8)
    # The +0.1 added to every cone response in _adapt means this sum is at
    # least 0.305 for any pixel, black included — so no zero-division guard
    # is needed here, and chroma falls out to 0 on its own when a=b=0.
    denom = rgb_a[..., 0] + rgb_a[..., 1] + 21.0 * rgb_a[..., 2] / 20.0
    t = (50000.0 / 13.0) * N_c * N_cb * e_t * np.sqrt(a**2 + b**2) / denom

    C = t**0.9 * np.sqrt(np.clip(J, 0.0, None) / 100.0) * (1.64 - 0.29**n)**0.73

    return J.astype(np.float32), C.astype(np.float32), h.astype(np.float32)


def rgb_to_ycbcr(R, G, B):
    """RGB → YCbCr, BT.601 **studio swing**.  Returns Y (16-235), Cb/Cr (16-240).

    Studio range, not full range: black maps to Y=16 and white to Y=235,
    matching the ITU-R BT.601 broadcast convention. If you need the full
    0-255 swing, scale afterwards:

        Y_full = (Y - 16) * 255 / 219
    """
    Rf = R.astype(np.float32)
    Gf = G.astype(np.float32)
    Bf = B.astype(np.float32)

    Y = 16.0 + (65.481 * Rf + 128.553 * Gf + 24.966 * Bf) / 255.0
    Cb = 128.0 + (-37.797 * Rf - 74.203 * Gf + 112.0 * Bf) / 255.0
    Cr = 128.0 + (112.0 * Rf - 93.786 * Gf - 18.214 * Bf) / 255.0

    return Y.astype(np.float32), Cb.astype(np.float32), Cr.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# Jzazbz / JzCzHz (Perceptual Quantizer based, HDR-ready)
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_jzazbz(R, G, B):
    """RGB → Jzazbz.  Returns Jz, az, bz.

    Based on Safdar et al. (2017) "Perceptually uniform color space
    for image signals including high dynamic range and wide gamut".
    """
    X, Y, Z = _rgb_to_xyz(R, G, B)
    X = X.astype(np.float64)
    Y = Y.astype(np.float64)
    Z = Z.astype(np.float64)

    # Absolute luminance (assume SDR peak ~203 cd/m²)
    X_abs = X * 203.0
    Y_abs = Y * 203.0
    Z_abs = Z * 203.0

    # Pre-scaling of X and Y before the LMS matrix, per Safdar et al. eq. 8-9.
    # Without it Jz is out by ~80% of its own range; the LMS matrix below is
    # defined against these primed values, not against raw XYZ.
    b = 1.15
    g = 0.66
    X_p = b * X_abs - (b - 1.0) * Z_abs
    Y_p = g * Y_abs - (g - 1.0) * X_abs

    # XYZ' → LMS (modified Hunt-Pointer-Estevez)
    Lp = 0.41478972 * X_p + 0.579999 * Y_p + 0.01464800 * Z_abs
    Mp = -0.20151000 * X_p + 1.120649 * Y_p + 0.05310080 * Z_abs
    Sp = -0.01660080 * X_p + 0.264800 * Y_p + 0.66847990 * Z_abs

    # PQ transfer function (Perceptual Quantizer)
    c1 = 3424.0 / 4096.0
    c2 = 2413.0 / 128.0
    c3 = 2392.0 / 128.0
    n = 2610.0 / 16384.0
    p = 1.7 * 2523.0 / 32.0

    def _pq(x):
        x = np.clip(x / 10000.0, 0.0, None)
        xn = x ** n
        return ((c1 + c2 * xn) / (1.0 + c3 * xn)) ** p

    Lp_pq = _pq(Lp)
    Mp_pq = _pq(Mp)
    Sp_pq = _pq(Sp)

    # Izazbz
    Iz = 0.5 * Lp_pq + 0.5 * Mp_pq
    az = 3.524000 * Lp_pq - 4.066708 * Mp_pq + 0.542708 * Sp_pq
    bz = 0.199076 * Lp_pq + 1.096799 * Mp_pq - 1.295875 * Sp_pq

    # Jz. Two constants, not one: d shapes the curve, d_0 only offsets it.
    # Using d_0 in place of d collapses this to Jz ≈ Iz, since d_0 ≈ 1.6e-11.
    d = -0.56
    d_0 = 1.6295499532821566e-11
    Jz = ((1.0 + d) * Iz) / (1.0 + d * Iz) - d_0

    return Jz.astype(np.float32), az.astype(np.float32), bz.astype(np.float32)


def rgb_to_jzczhz(R, G, B):
    """RGB → JzCzHz (cylindrical Jzazbz).  Returns Jz, Cz, hz (0-360°)."""
    Jz, az, bz = rgb_to_jzazbz(R, G, B)
    Cz = np.sqrt(az ** 2 + bz ** 2)
    hz = np.degrees(np.arctan2(bz, az))
    hz = np.where(hz < 0, hz + 360.0, hz)
    return Jz.astype(np.float32), Cz.astype(np.float32), hz.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# Inverse conversions
# ═══════════════════════════════════════════════════════════════════════

def lab_to_rgb(L, a, b):
    """CIELAB → sRGB [0, 1].  Returns R, G, B as float32."""
    epsilon = 0.008856
    kappa = 903.3

    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0

    X = np.where(fx ** 3 > epsilon, fx ** 3,
                 (116.0 * fx - 16.0) / kappa) * _Xn
    Y = np.where(L > kappa * epsilon, fy ** 3, L / kappa) * _Yn
    Z = np.where(fz ** 3 > epsilon, fz ** 3,
                 (116.0 * fz - 16.0) / kappa) * _Zn

    # XYZ → linear sRGB (inverse of D65 matrix)
    r_lin =  3.2404542 * X - 1.5371385 * Y - 0.4985314 * Z
    g_lin = -0.9692660 * X + 1.8760108 * Y + 0.0415560 * Z
    b_lin =  0.0556434 * X - 0.2040259 * Y + 1.0572252 * Z

    R_out = _linear_to_srgb(r_lin)
    G_out = _linear_to_srgb(g_lin)
    B_out = _linear_to_srgb(b_lin)

    return R_out.astype(np.float32), G_out.astype(np.float32), B_out.astype(np.float32)


def oklab_to_rgb(L, a, b):
    """Oklab → sRGB [0, 1].  Returns R, G, B as float32."""
    l_c = L + 0.3963377774 * a + 0.2158037573 * b
    m_c = L - 0.1055613458 * a - 0.0638541728 * b
    s_c = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_c ** 3
    m = m_c ** 3
    s = s_c ** 3

    R_lin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    G_lin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    B_lin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return (_linear_to_srgb(R_lin).astype(np.float32),
            _linear_to_srgb(G_lin).astype(np.float32),
            _linear_to_srgb(B_lin).astype(np.float32))


def hsv_to_rgb(H, S, V):
    """HSV → RGB [0, 1].  H in [0, 360], S and V in [0, 1].  Returns R, G, B float32."""
    H = H.astype(np.float32)
    S = S.astype(np.float32)
    V = V.astype(np.float32)

    C = V * S
    Hp = H / 60.0
    X = C * (1.0 - np.abs(np.mod(Hp, 2.0) - 1.0))
    m = V - C

    R = np.zeros_like(H)
    G = np.zeros_like(H)
    B = np.zeros_like(H)

    mask0 = (Hp >= 0) & (Hp < 1); R[mask0] = C[mask0]; G[mask0] = X[mask0]
    mask1 = (Hp >= 1) & (Hp < 2); R[mask1] = X[mask1]; G[mask1] = C[mask1]
    mask2 = (Hp >= 2) & (Hp < 3); G[mask2] = C[mask2]; B[mask2] = X[mask2]
    mask3 = (Hp >= 3) & (Hp < 4); G[mask3] = X[mask3]; B[mask3] = C[mask3]
    mask4 = (Hp >= 4) & (Hp < 5); R[mask4] = X[mask4]; B[mask4] = C[mask4]
    mask5 = (Hp >= 5) & (Hp < 6); R[mask5] = C[mask5]; B[mask5] = X[mask5]

    return ((R + m).astype(np.float32),
            (G + m).astype(np.float32),
            (B + m).astype(np.float32))


def hsl_to_rgb(H, S, L):
    """HSL → RGB [0, 1].  H in [0, 360], S and L in [0, 1].  Returns R, G, B float32."""
    H = H.astype(np.float32)
    S = S.astype(np.float32)
    L = L.astype(np.float32)

    C = (1.0 - np.abs(2.0 * L - 1.0)) * S
    Hp = H / 60.0
    X = C * (1.0 - np.abs(np.mod(Hp, 2.0) - 1.0))
    m = L - C / 2.0

    R = np.zeros_like(H)
    G = np.zeros_like(H)
    B = np.zeros_like(H)

    mask0 = (Hp >= 0) & (Hp < 1); R[mask0] = C[mask0]; G[mask0] = X[mask0]
    mask1 = (Hp >= 1) & (Hp < 2); R[mask1] = X[mask1]; G[mask1] = C[mask1]
    mask2 = (Hp >= 2) & (Hp < 3); G[mask2] = C[mask2]; B[mask2] = X[mask2]
    mask3 = (Hp >= 3) & (Hp < 4); G[mask3] = X[mask3]; B[mask3] = C[mask3]
    mask4 = (Hp >= 4) & (Hp < 5); R[mask4] = X[mask4]; B[mask4] = C[mask4]
    mask5 = (Hp >= 5) & (Hp < 6); R[mask5] = C[mask5]; B[mask5] = X[mask5]

    return ((R + m).astype(np.float32),
            (G + m).astype(np.float32),
            (B + m).astype(np.float32))


# ═══════════════════════════════════════════════════════════════════════
# Registry & dispatcher
# ═══════════════════════════════════════════════════════════════════════

_CONVERSIONS = {
    "dlab":   (rgb_to_dlab,   ["L", "a", "b", "L99", "a99", "b99"]),
    "hsl":    (rgb_to_hsl,    ["H", "S", "L"]),
    "hsi":    (rgb_to_hsi,    ["H", "S", "I"]),
    "hsv":    (rgb_to_hsv,    ["H", "S", "V"]),
    "jch":    (rgb_to_jch,    ["J", "C", "H"]),
    "cam02":  (rgb_to_cam02,  ["J", "C", "h"]),
    "jzazbz": (rgb_to_jzazbz, ["Jz", "az", "bz"]),
    "jzczhz": (rgb_to_jzczhz, ["Jz", "Cz", "hz"]),
    "lab":    (rgb_to_lab,    ["L", "a", "b"]),
    "lchab":  (rgb_to_lchab,  ["L", "C", "Hab"]),
    "lchuv":  (rgb_to_lchuv,  ["L", "C", "Huv"]),
    "luv":    (rgb_to_luv,    ["L", "u", "v"]),
    "oklab":  (rgb_to_oklab,  ["L", "a", "b"]),
    "xyY":    (rgb_to_xyY,    ["x", "y_ch", "Y_lum"]),
    "ycbcr":  (rgb_to_ycbcr,  ["Y", "Cb", "Cr"]),
}


def available_spaces():
    """Return sorted list of supported color space names."""
    return sorted(_CONVERSIONS.keys())


def convertbands(R, G, B, space):
    """Convert RGB bands to the chosen color space.

    Parameters
    ----------
    R, G, B : numpy.ndarray
        2-D arrays (uint8 or float).  Each function normalises internally.
    space : str
        Target color space (see ``available_spaces()``).

    Returns
    -------
    comps : tuple of numpy.ndarray
        Component arrays (float32).
    names : list of str
        Component names.
    """
    try:
        func, names = _CONVERSIONS[space]
    except KeyError:
        raise ValueError(
            f"Unknown space '{space}'. Available: {available_spaces()}"
        )
    comps = func(R, G, B)
    return comps, names
