# Changelog

## [0.6.1] — 2026-07-22

### Fixed
- **`geopalette.__version__` said 0.4.0 while the package was 0.6.0.** Two
  releases were cut in between and both missed it: the bump was done by
  editing the places someone remembered instead of searching for the old
  number, which is exactly what the release checklist added in the previous
  commit tells contributors not to do. Anyone importing from a source
  checkout and quoting `__version__` in a bug report was two releases out.

  `tests/test_version_consistency.py` now ties `__version__`, `pyproject.toml`
  and `CITATION.cff` together and requires a `CHANGELOG.md` heading for the
  version being released, so the next mismatch fails before the tag.


## [0.6.0] — 2026-07-22

### Added
- **`convert_raster(block_size=...)` now does what it always said it did.**
  It was a documented public parameter — "Tile size for block-based
  processing of large rasters" — that appeared in the signature and the
  docstring and nowhere else; the whole raster was read, converted and held
  in memory regardless. A scene larger than RAM could not be converted, and
  the parameter offered to solve exactly that.

  The raster is now read, converted and written one `block_size × block_size`
  window at a time, straight into the open output files. On
  `SNP_21_2020_1.tif` → `dlab` (six output bands) peak allocation drops from
  **14.90 MB to 1.94 MB** at `block_size=128`. `block_size=0` restores the
  old whole-raster behaviour.

  The result must not depend on it, and that is checked rather than assumed:
  all 15 spaces, block sizes 0/8/13/4096 — 13 divides neither raster
  dimension, so the trailing blocks are partial — pixels, nodata, transform,
  CRS and band count all bit-identical, single-band outputs included. Both
  the obvious ways to get blocking wrong (writing without the window,
  computing the mask outside it) were introduced deliberately and the tests
  failed on each.


## [0.5.0] — 2026-07-22

### Fixed
- **`convert_raster()` converted the nodata region as if it were black, and
  then declared a nodata value no pixel carried.** Every band was read raw,
  so a source hole went through the colour transform like ordinary dark
  pixels. On `SNP_21_2020_1.tif` that is 34,386 px — 21 % of the raster —
  coming out as `L = -6e-08` and written as valid, while the output header
  announced `nodata = -9999` that occurred nowhere. Nothing downstream could
  tell the hole from real canopy.

  It also explains a number that had been sitting in plain sight: the range
  table reported `L[0.00, 68.62]` for every space, and that zero minimum was
  the hole rather than the image. With the fix the valid range is
  `L[7.71, 68.62]`.

  The source mask is now honoured and the declared nodata is stamped into
  the pixels it describes. A raster without nodata is unaffected.

### Known issues
- `convert_raster(block_size=...)` does nothing. It appears in the signature
  and the docstring — "Tile size for block-based processing of large
  rasters" — and nowhere else; the whole raster is read at once regardless.
  Left in place rather than removed silently, since dropping a documented
  parameter is an API decision.


## [0.4.0]

### Added
- **`rgb_to_cam02` — real CIECAM02**, alongside the existing `rgb_to_jch`.
  Full forward model: CAT02 chromatic adaptation, surround terms, background
  induction. Returns J (lightness), C (chroma), h (hue angle 0-360°).
  Validated against `colour.XYZ_to_CIECAM02` to float32 precision across the
  average, dim and dark surrounds. Registered as the `cam02` space.

  Unlike the other conversions, it takes viewing-condition arguments —
  `L_A` (adapting luminance), `Y_b` (background), `surround` — because
  CIECAM02 models an observer, not a fixed function of RGB. They genuinely
  move the numbers (J shifts ~8 units between average and dark), so report
  what you used. `rgb_to_jch` stays as the cheap stand-in for when exact
  appearance values do not matter.

### Note
- `rgb_to_jch` is unchanged and still not CIECAM02. If you need appearance
  values you can defend in a manuscript, use `rgb_to_cam02`.

## [0.3.0]

Three conversions produced wrong numbers. The unit tests all passed, because
they only ever checked shapes, dtypes and ranges — never a value against a
reference. `tests/test_reference.py` now compares every space to
`colour-science` and `scikit-image`, and each fix below is guarded by a test
that fails if it is reverted.

**Minkowski-free note for existing users:** `lab`, `luv`, `hsv`, `hsl`,
`xyY`, `oklab`, `lchab`, `lchuv` and `ycbcr` were already correct and are
unchanged. If you only used those, your results stand.

### Fixed
- **Jzazbz was wrong twice over.** It skipped the pre-scaling of X and Y that
  Safdar et al. (2017) define in eq. 8-9 (`X' = b·X − (b−1)·Z`,
  `Y' = g·Y − (g−1)·X`, with b=1.15, g=0.66) — the LMS matrix is defined
  against those primed values, not raw XYZ. It also used `d_0` (1.63e-11) in
  the Jz curve where the constant `d` (−0.56) belongs, which collapsed the
  formula to `Jz ≈ Iz`. Jz was out by ~0.17 against a range of 0.01-0.21.
  Both now match `colour.XYZ_to_Jzazbz` to float32 precision. `jzczhz` is
  derived from the same numbers and was wrong with it.
- **DIN99 dropped the 0.7 factor.** DIN 6176 defines
  `f = 0.7·(−a*·sin16° + b*·cos16°)`; without it a99/b99 were out by up to
  7 units. The whole point of DIN99 is that one unit is one perceptual step,
  so the scale has to be right.
- **RuntimeWarnings on achromatic pixels.** `hsl`, `hsv`, `jch`, `luv` and
  `dlab` divided by zero on every grey, white or black pixel, then discarded
  the NaN. The results were right and the warnings were noise — but grey,
  shadow and water are everywhere in a raster. Two causes: masking after
  dividing instead of indexing first, and `np.where`, which is not lazy and
  evaluates both branches.

### Changed
- **`ycbcr` docstring said "full-range" while implementing studio swing.**
  The formula is BT.601 legal range — black is Y=16, white is Y=235 — and
  matches `colour-science` with `out_legal=True`. Only the docstring was
  wrong, but it was wrong in a way that would silently mis-scale someone's
  data.
- **`jch` is documented for what it is.** It is not CIECAM02: no chromatic
  adaptation, no surround, no background. It tracks real CIECAM02 at r≈0.98
  on J and r≈0.89 on C, but hue can be off by 70°. Its H spans 0-324°, not
  the 0-360° previously documented, because it scales an HSV hue by 0.9.
- `test_conversions.py` moved to `tests/`, where its own header already said
  it lived. `geopalette_test.py`, which is an example rather than a test,
  moved to `examples/convert_geotiff.py`.
- `test_available_spaces_count` asserted a hardcoded 13 against 14 registered
  spaces, so it failed for whoever added the fourteenth. It now checks the
  properties that matter: sorted, unique, non-empty.
- Licence declared as an SPDX expression with `license-files` (PEP 639); the
  TOML table form is deprecated and stops working 2027-02-18. Needs
  setuptools >= 77.

- **`python -m geopalette` always exited 0.** `__main__.py` called `main()`
  without passing its return value to `sys.exit()` — `sys` was imported and
  unused, which was the tell — so a failed conversion reported success and
  any script checking `$?` missed it. It also printed raw tracebacks for a
  missing file; user mistakes now get one clean line on stderr and exit 1.
- Unused imports removed; `pyflakes` is clean outside the deliberate
  re-exports in `__init__.py`.

### Added
- GitHub Actions CI: tests and lint on Linux/macOS/Windows across Python
  3.9-3.12.
- `pip install geopalette[validate]` pulls the reference implementations.

## [0.1.0] — 2025-XX-XX

### Added
- Initial release
- 13 forward color space conversions: HSL, HSV, HSI, CIELAB, DIN99 (DLab), 
  Oklab, CIELUV, LCH(ab), LCH(uv), xyY, JCH, YCbCr, JzCzHz
- 1 inverse conversion: CIELAB → RGB
- `convertbands()` dispatcher for easy single-call conversion
- `convert_raster()` I/O utility for GeoTIFF workflows
- CLI: `python -m geopalette` / `geopalette` command
- Test suite with synthetic data
