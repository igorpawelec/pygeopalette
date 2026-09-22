# pygeopalette

<img src="https://raw.githubusercontent.com/igorpawelec/pygeopalette/main/www/pygeopalette.png" align="right" width="200"/>

[![tests](https://github.com/igorpawelec/pygeopalette/actions/workflows/tests.yml/badge.svg)](https://github.com/igorpawelec/pygeopalette/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/igorpawelec/pygeopalette)](https://github.com/igorpawelec/pygeopalette/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

**Colour space conversions for geospatial raster data.**

Three RGB bands go in; the components of any of 15 colour spaces come out, as arrays or as a GeoTIFF. Pure NumPy, vectorised over whole bands, no pixel loops, and `rasterio` only for the file I/O.

> **R users:** the same conversions are in [rgeopalette](https://github.com/igorpawelec/rgeopalette). The two are separate repositories because their tooling and idioms do not mix. They agree to better than 1.7e-6 of each component's range — but, unlike the adaptels twins, they are **not bit-identical** and cannot be: pygeopalette stores single precision, R has no single-precision type.

## The problem it solves

The three bands of an orthophoto are the camera's axes, not the analyst's. Red, green and blue are correlated with each other and with brightness, so a bleached crown in the sun and a healthy one in the shade can differ more along every band than a dead tree differs from a living one. The questions a forester or an image analyst asks — how bright, how saturated, how far towards red — live on other axes, and CIE colorimetry has been describing those axes since 1976.

pygeopalette moves raster bands onto them. It implements the standard chain — sRGB linearisation (IEC 61966-2-1), CIE XYZ under D65, then CIELAB, CIELUV, their cylindrical LCH forms, DIN99, Oklab, Jzazbz, CIECAM02 and the video and hue-based spaces — with the numerical care a scientific application needs, and checks every space against an independent implementation.

<img src="https://raw.githubusercontent.com/igorpawelec/pygeopalette/main/www/spaces.png" alt="A 30 by 30 m window of a spruce plot orthophoto in RGB and in seven colour spaces, each space's three components shown as the red, green and blue channels" width="100%"/>

*A 30 × 30 m window of a 0.25 m orthophoto of a spruce stand (`test_data/SNP_21_2020_1.tif`) in RGB and in seven of the fifteen spaces, each space's three components shown as the red, green and blue channels and stretched for display. In the opponent spaces — CIELAB, Oklab, CIELUV, Jzazbz — the dead crowns turn magenta, because their `a*` is positive and the living canopy's is negative; the hue-based spaces wrap around the colour circle wherever a pixel is nearly neutral, which is the caveat below made visible. Made by `www/figures.py`.*

## Why it matters, measured

The plot has 36 standing dead trees digitised as points. Take every pixel within 1 m of a point as dead and every pixel further than 2 m from all of them as living — 1,759 against 118,627 — and ask of each axis how well it tells the two apart, as the probability that a random dead pixel outranks a random living one (an AUC: 0.5 is chance, 1 is perfect). Fifty-one axes: the three RGB bands and all 48 components of the fifteen spaces.

<img src="https://raw.githubusercontent.com/igorpawelec/pygeopalette/main/www/separation.png" alt="CIELAB a* over the plot with the dead-tree points, the dead trees red on a blue canopy; the densities of dead and living pixels along a*, AUC 0.97; and along the blue band, the best RGB band, AUC 0.93" width="100%"/>

*Left: CIELAB `a*` over the plot, red for positive, blue for negative, with the 36 points. Middle: dead and living pixels along `a*` — AUC 0.97, the best of the 51 axes (Oklab `a` and DIN99 `a` tie with it to three decimals). Right: the same along the blue band, the best that RGB can do — AUC 0.93, with the dead trees spread across the whole upper half of the living distribution. The hue axes score 0.94 but are undefined on neutral pixels; the green–red opponent axis is the one that carries the difference, which is why the dead-tree recipe in pygeoadaptels' `grow_seeds` weights `a*` by 2.5.*

The practical reading: convert before you segment or classify, and choose the axis for the question. Brightness lives on `L*`, the dead-versus-living difference on `a*`, and a colour difference with a meaning — a ΔE — only exists in CIELAB, which is what gives a tolerance like `grow_seeds`' `max_cost` its unit.

## When to use it, and when not

Use pygeopalette to prepare an RGB orthophoto for object-based analysis — adaptels, a classifier over segment features, a seeded growing with a ΔE tolerance — or to read an appearance attribute off it. `rgb_to_cam02` runs the full CIECAM02 model with viewing conditions when the numbers have to be defensible; `rgb_to_jch` is the fast stand-in when they do not.

It is not a colour-management tool: no ICC profiles, and the input is taken as sRGB under D65, which is what an 8-bit aerial orthophoto is for practical purposes. It has nothing to say about a near-infrared band — there is no colour space for one; use an index.

### The package family

pygeopalette is the first step of a longer chain; the other steps are separate packages, each with a Python and an R twin.

| Step | Python | R |
|---|---|---|
| Colour-space conversion of orthophotos | **pygeopalette** | [rgeopalette](https://github.com/igorpawelec/rgeopalette) |
| Adaptive superpixels and seeded growing on orthophotos | [pygeoadaptels](https://github.com/igorpawelec/pygeoadaptels) | [rgeoadaptels](https://github.com/igorpawelec/rgeoadaptels) |
| Crowns from a canopy height model | [pycacumen](https://github.com/igorpawelec/pycacumen) | [rcacumen](https://github.com/igorpawelec/rcacumen) |
| Standing dead trees on orthophotos | [pygeosnag](https://github.com/igorpawelec/pygeosnag) | — |
| The same, inside QGIS | [qgis-geoadaptels-geopalette](https://github.com/igorpawelec/qgis-geoadaptels-geopalette), [qgis-geosnag](https://github.com/igorpawelec/qgis-geosnag) | |
| Polish national geodata (GUGiK, BDL) | — | [rgeopl](https://github.com/igorpawelec/rgeopl) |

## Installation

```bash
conda install -c conda-forge numpy rasterio
pip install --no-deps git+https://github.com/igorpawelec/pygeopalette.git
```

Rasterio is only needed for GeoTIFF I/O; every conversion works on plain NumPy arrays, so `pip install numpy` and the package is the minimal install. The `--no-deps` flag keeps pip from overwriting conda's GDAL/PROJ stack.

## Quick start

```python
import numpy as np
from pygeopalette import convertbands, available_spaces

print(available_spaces())
# ['cam02', 'dlab', 'hsi', 'hsl', 'hsv', 'jch', 'jzazbz', 'jzczhz', 'lab', 'lchab', 'lchuv', 'luv', 'oklab', 'xyY', 'ycbcr']

comps, names = convertbands(R, G, B, "lab")     # uint8 bands in; a list of float32 arrays out
print(names)                                    # ['L', 'a', 'b']
```

```python
from pygeopalette import rgb_to_lab, rgb_to_oklab, rgb_to_cam02, lab_to_rgb

L, a, b = rgb_to_lab(R, G, B)
J, C, h = rgb_to_cam02(R, G, B, L_A=64, Y_b=20, surround="average")
R2, G2, B2 = lab_to_rgb(L, a, b)                # inverse, sRGB in [0, 1]
```

```python
from pygeopalette.io_utils import convert_raster

convert_raster("ortho_rgb.tif", "results/", "lab", save_multiband=True, save_singlebands=True)
```

```bash
pygeopalette -i ortho_rgb.tif -o results/ -s lab
pygeopalette -i ortho_rgb.tif -o results/ -s oklab --single-bands
python -m pygeopalette --help
```

## Reference

### Supported colour spaces

| Space | Components | Category |
|-------|-----------|----------|
| **HSL** | H (0–360°), S, L (0–1) | Hue-based |
| **HSV** | H (0–360°), S, V (0–1) | Hue-based |
| **HSI** | H (0–360°), S (%), I (0–255) | Hue-based |
| **CIELAB** | L* (0–100), a*, b* | Perceptual (CIE) |
| **DIN99 (DLab)** | L*, a*, b*, L99, a99, b99 | Perceptual (DIN) |
| **Oklab** | L, a, b | Perceptual (modern) |
| **CIELUV** | L*, u*, v* | Perceptual (CIE) |
| **LCH(ab)** | L*, C, H (0–360°) | Cylindrical CIELAB |
| **LCH(uv)** | L*, C, H (0–360°) | Cylindrical CIELUV |
| **xyY** | x, y (chromaticity), Y (luminance) | CIE chromaticity |
| **JCH** | J, C, H (0–360°) | CIECAM02-like (fast stand-in) |
| **CIECAM02 (cam02)** | J, C, h (0–360°) | Colour appearance model |
| **YCbCr** | Y (16–235), Cb, Cr (16–240) | Video (BT.601) |
| **Jzazbz** | Jz, az, bz | HDR perceptual |
| **JzCzHz** | Jz, Cz, hz (0–360°) | HDR cylindrical |

Inverse conversions: **CIELAB → RGB**, **Oklab → RGB**, **HSV → RGB**, **HSL → RGB**. The forward functions take uint8 0–255 and the inverses return float32 0–1, so they do not compose directly: `(R2 * 255).round().astype(np.uint8)`.

### Three things worth knowing before stacking bands

- **Scales differ between spaces.** Hue is 0–360, HSL/HSV saturation and value 0–1, HSI saturation 0–100 per cent and intensity 0–255, `L*` 0–100 with `a*`/`b*` unbounded, `jch` hue 0–324 (an HSV hue scaled by 0.9), `ycbcr` studio swing with Y 16–235. Normalise before you stack.
- **Hue is undefined on the neutral axis.** `Hab`, `Huv`, `hz` and CIECAM02 `h` come from `atan2` over an opponent pair that is zero for a neutral pixel, so the angle is floating-point noise there — grey, white, black, deep shadow and still water are all neutral, which is ordinary in imagery. Do not segment or classify on a hue band without masking low-chroma pixels first. The HSL/HSV/HSI/JCH hues are forced to 0 for achromatic pixels instead.
- **`cam02` is real CIECAM02; `jch` is not.** `rgb_to_cam02` runs the full model — CAT02 adaptation, surround, background — and takes viewing conditions because CIECAM02 models an observer: `L_A` the adapting luminance (~318 for a sunlit scene, ~64 for a screen), `Y_b` the background (20 = grey world), `surround` one of `average` / `dim` / `dark`. They move the result — J shifts about 8 units between average and dark — so report them. `jch` has none of that: it tracks CIECAM02 at r ≈ 0.98 on J and 0.89 on C, but its hue can be off by 70°.

<details>
<summary><b>Accuracy</b></summary>

Every conversion is checked against an independent implementation (`colour-science`, `scikit-image`) in `tests/test_reference.py`:

```bash
pip install -e ".[validate]"
pytest tests/test_reference.py -v
```

All 15 spaces match their reference to float32 precision. Where a tolerance looks loose it is the module's own float32 storage: the PQ curve inside Jzazbz carries an exponent of 134, which turns a float32 input error of ~1e-7 into ~1e-5 on the output.

`ycbcr` is BT.601 studio swing, not full range: black is Y = 16, white is Y = 235. Rescale with `(Y - 16) * 255 / 219` if you need 0–255.

</details>

<details>
<summary><b>Repository layout, requirements, testing</b></summary>

```
pygeopalette/
├── pygeopalette/         # Package source
│   ├── __init__.py       # Public API
│   ├── __main__.py       # CLI entry point
│   ├── conversions.py    # All conversion functions
│   └── io_utils.py       # GeoTIFF read/write helpers
├── tests/                # Pytest suite, incl. the reference check
├── test_data/            # The sample plot and its dead-tree points
├── www/                  # Logo and the README figures, with the script that makes them
├── pyproject.toml
├── environment.yaml
├── CITATION.cff
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

- Python ≥ 3.9, NumPy ≥ 1.21
- Rasterio ≥ 1.3 *(optional, for GeoTIFF I/O)*

```bash
pip install pytest
pytest tests/ -v
```

The README figures are remade with `python www/figures.py` from the files in `test_data/`.

</details>

## Citation

If you use this software in your research, please cite:

1. **This implementation:**

   > Pawelec, I. (2026). pygeopalette — Color space conversions for geospatial raster data [Software]. https://github.com/igorpawelec/pygeopalette

2. **For CIELAB/CIELUV conversions:**

   > CIE 15:2004. Colorimetry (3rd ed.). Commission Internationale de l'Éclairage.

3. **For Oklab:**

   > Ottosson, B. (2020). A perceptual color space for image processing. https://bottosson.github.io/posts/oklab/

4. **For Jzazbz/JzCzHz:**

   > Safdar, M., Cui, G., Kim, Y.J., & Luo, M.R. (2017). Perceptually uniform color space for image signals including high dynamic range and wide gamut. *Optics Express*, 25(13), 15131–15151.

DIN99 follows DIN 6176:2003 and the sRGB linearisation IEC 61966-2-1:1999. See also [CITATION.cff](CITATION.cff).

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).
