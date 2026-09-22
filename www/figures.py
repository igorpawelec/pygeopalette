"""The README figures, generated from test_data so they can be remade.

    python www/figures.py            # from the repository root; no install needed

Writes two figures and prints the numbers the README captions quote:
  www/spaces.png       a 30 x 30 m window of the scene in RGB and in seven
                       colour spaces, each space's three components shown as
                       the red, green and blue channels;
  www/separation.png   why a colour space matters: how well each axis tells
                       the 36 digitised dead trees from the living canopy,
                       measured as an AUC over every component of every space
                       and every RGB band, with the best of each drawn.
One scene, test_data/SNP_21_2020_1.tif: a 100 x 100 m circular sample plot in
a spruce stand at 0.25 m, with 36 standing dead trees digitised as points.
Every component is stretched for display only; the numbers use the raw values.
"""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import rasterio  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from scipy.stats import gaussian_kde, rankdata  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from pygeopalette import available_spaces, convertbands  # noqa: E402

RGB = os.path.join(ROOT, "test_data", "SNP_21_2020_1.tif")
PTS = os.path.join(ROOT, "test_data", "dead_trees_test.shp")
BLUES = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
         "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP = LinearSegmentedColormap.from_list("mag", BLUES)
BLUE, ORANGE, INK, MUTED, LINE = "#2a78d6", "#eb6834", "#1f1f1f", "#6b6b6b", "#e4e4e4"
WINDOW = (120, 90, 120)                                  # row0, col0, size: the same 30 m window as the adaptels figures
GRID = [("rgb", "RGB"), ("lab", "CIELAB  L*, a*, b*"), ("oklab", "Oklab  L, a, b"), ("lchab", "LCH(ab)  L*, C, H"),
        ("luv", "CIELUV  L*, u*, v*"), ("hsv", "HSV  H, S, V"), ("ycbcr", "YCbCr  Y, Cb, Cr"), ("jzazbz", "Jzazbz  Jz, az, bz")]
PRETTY = {"lab a": "CIELAB a*", "lab b": "CIELAB b*", "lab L": "CIELAB L*", "oklab a": "Oklab a", "dlab a": "DIN99 a",
          "RGB R": "RGB red", "RGB G": "RGB green", "RGB B": "RGB blue"}
DIVERGING = LinearSegmentedColormap.from_list("ab", ["#2a78d6", "#f0efec", "#e34948"])   # green <- 0 -> red, grey at zero
DEAD_R, LIVING_R = 4, 8                                  # px: within 1 m of a point is a dead crown; beyond 2 m of every point is living


def read_points(path, transform):
    import fiona
    with fiona.open(path) as src:
        xy = np.array([f["geometry"]["coordinates"] for f in src])
    inv = ~transform
    cols, rows = inv * (xy[:, 0], xy[:, 1])
    return np.column_stack([np.floor(rows), np.floor(cols)]).astype(np.int64)


def stretch(a, valid, lo=1.0, hi=99.0):
    """Percentile stretch of the valid pixels to [0, 1], for display only."""
    v = a[valid & np.isfinite(a)]
    p, q = np.percentile(v, [lo, hi])
    return np.clip((a - p) / max(q - p, 1e-9), 0, 1)


def composite(comps, valid):
    out = np.ones(comps[0].shape + (3,))
    for k in range(3):
        out[..., k] = stretch(comps[k].astype(float), valid)
    out[~valid] = 1.0
    return out


def auc(x, dead, living):
    """P(dead pixel > living pixel), folded to [0.5, 1]: 0.5 is chance, 1 is perfect separation."""
    xd, xl = x[dead], x[living]
    ok_d, ok_l = np.isfinite(xd), np.isfinite(xl)
    xd, xl = xd[ok_d], xl[ok_l]
    r = rankdata(np.concatenate([xd, xl]))
    u = r[: len(xd)].sum() - len(xd) * (len(xd) + 1) / 2
    a = u / (len(xd) * len(xl))
    return max(a, 1 - a), a >= 0.5


with rasterio.open(RGB) as src:
    rgb = src.read()
    tf, res = src.transform, src.res[0]
R, G, B = rgb[0], rgb[1], rgb[2]
valid = ~(rgb == 0).all(axis=0)
seeds = read_points(PTS, tf)
rr, cc = np.mgrid[: R.shape[0], : R.shape[1]]
d2 = np.full(R.shape, np.inf)
for r0, c0 in seeds:
    d2 = np.minimum(d2, (rr - r0) ** 2 + (cc - c0) ** 2)
dead = valid & (d2 <= DEAD_R ** 2)
living = valid & (d2 > LIVING_R ** 2)

# ---- every component of every space, ranked by how well it separates dead from living ----
axes_all = {"RGB R": R.astype(float), "RGB G": G.astype(float), "RGB B": B.astype(float)}
for space in available_spaces():
    comps, names = convertbands(R, G, B, space)
    for c, n in zip(comps, names):
        axes_all[f"{space} {n}"] = c.astype(float)
ranked = sorted(((auc(v, dead, living)[0], k) for k, v in axes_all.items()),
                key=lambda t: (-round(t[0], 3), 0 if t[1].startswith("lab ") else 1, t[1]))   # ties: CIELAB first
best_rgb = max((a, k) for a, k in ranked if k.startswith("RGB"))
best = ranked[0]
print(f"scene {os.path.basename(RGB)}: {R.shape[1]} x {R.shape[0]} px at {res:g} m; {len(seeds)} dead-tree points; "
      f"{int(dead.sum()):,} dead px (within {DEAD_R * res:g} m), {int(living.sum()):,} living px (beyond {LIVING_R * res:g} m)")
print(f"{len(axes_all)} axes ranked by AUC dead vs living; top 12:")
for a, k in ranked[:12]:
    print(f"   {a:.3f}  {k}")
print(f"best RGB band: {best_rgb[1]} at {best_rgb[0]:.3f}; best colour-space axis: {best[1]} at {best[0]:.3f}")

# ---- figure 1: the scene in eight spaces, one window ------------------------------------
r0, c0, n = WINDOW
sl = (slice(r0, r0 + n), slice(c0, c0 + n))
fig, axes = plt.subplots(2, 4, figsize=(11.4, 6.1))
for ax, (space, label) in zip(axes.ravel(), GRID):
    if space == "rgb":
        img = composite([R, G, B], valid)
    else:
        comps, names = convertbands(R, G, B, space)
        img = composite(comps, valid)
    ax.imshow(img[sl], interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#d9d9d9")
    ax.set_xlabel(label, fontsize=9.5, color=INK, labelpad=6)
fig.subplots_adjust(wspace=0.05, hspace=0.22)
fig.savefig(os.path.join(HERE, "spaces.png"), dpi=160, bbox_inches="tight", facecolor="white")


# ---- figure 2: the separation -------------------------------------------------------------
def density_panel(ax, key, label):
    x = axes_all[key]
    a, dead_high = auc(x, dead, living)
    xd, xl = x[dead & np.isfinite(x)], x[living & np.isfinite(x)]
    lo, hi = np.percentile(np.concatenate([xd, xl]), [0.5, 99.5])
    grid = np.linspace(lo, hi, 240)
    for v, col, name in ((xl, BLUE, "living canopy"), (xd, ORANGE, "dead trees, within 1 m of a point")):
        ax.plot(grid, gaussian_kde(v)(grid), color=col, lw=2, label=name)
    ax.set_yticks([])
    ax.tick_params(labelsize=8, colors=MUTED)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_edgecolor(LINE)
    ax.grid(axis="x", color=LINE, lw=0.6)
    ax.set_xlabel(f"{label}   ·   AUC {a:.2f}", fontsize=9.5, color=INK, labelpad=6)
    return a


def image_panel(ax, key, label):
    x = axes_all[key]
    if key.split()[-1] in ("a", "b", "az", "bz", "u", "v"):                 # an opponent axis: zero is neutral
        lim = float(np.percentile(np.abs(x[valid & np.isfinite(x)]), 99))
        ax.imshow(np.where(valid, x, np.nan), cmap=DIVERGING, vmin=-lim, vmax=lim, interpolation="nearest")
    else:
        ax.imshow(np.where(valid, stretch(x, valid), np.nan), cmap=CMAP, vmin=0, vmax=1, interpolation="nearest")
    ax.scatter(seeds[:, 1], seeds[:, 0], s=14, c=INK, edgecolors="white", linewidths=0.8, zorder=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#d9d9d9")
    ax.set_xlabel(label, fontsize=9.5, color=INK, labelpad=6)


fig, axes = plt.subplots(1, 3, figsize=(11.4, 4.1), gridspec_kw={"width_ratios": [1, 1, 1.15]})
image_panel(axes[0], best[1], f"{PRETTY.get(best[1], best[1])}, with the dead-tree points")
density_panel(axes[1], best[1], f"{PRETTY.get(best[1], best[1])}, the best axis")
density_panel(axes[2], best_rgb[1], f"{PRETTY.get(best_rgb[1], best_rgb[1])}, the best RGB band")
axes[2].legend(loc="upper right", fontsize=8, frameon=False, labelcolor=INK)
fig.subplots_adjust(wspace=0.12)
fig.savefig(os.path.join(HERE, "separation.png"), dpi=160, bbox_inches="tight", facecolor="white")
print("written: www/spaces.png, www/separation.png")
