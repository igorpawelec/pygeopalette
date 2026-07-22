"""
geopalette.io_utils
~~~~~~~~~~~~~~~~~~~
Convenience helpers for reading / writing raster bands via rasterio.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import rasterio
except ImportError:
    rasterio = None  # type: ignore[assignment]

from .conversions import convertbands


def _check_rasterio():
    if rasterio is None:
        raise ImportError(
            "rasterio is required for I/O utilities. "
            "Install it with: conda install -c conda-forge rasterio"
        )


def convert_raster(
    input_path: str | Path,
    output_dir: str | Path,
    space: str,
    *,
    save_multiband: bool = True,
    save_singlebands: bool = False,
    nodata: float = -9999.0,
    block_size: int = 512,
    quiet: bool = False,
) -> Path:
    """Read an RGB GeoTIFF, convert to *space*, and write the result.

    Parameters
    ----------
    input_path : path-like
        Input RGB raster (≥ 3 bands; bands 1-3 used as R, G, B).
    output_dir : path-like
        Directory for output files.
    space : str
        Target color space (see ``available_spaces()``).
    save_multiband : bool
        Write a single multi-band TIFF (default ``True``).
    save_singlebands : bool
        Write each component as a separate single-band TIFF.
    nodata : float
        NoData value for output rasters.
    block_size : int
        Tile size for block-based processing of large rasters.
    quiet : bool
        Suppress progress messages.

    Returns
    -------
    Path
        Path to the multi-band output (or output dir if only single bands).
    """
    _check_rasterio()
    import time

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem

    if not quiet:
        print(f"GeoPalette: {input_path.name} → {space}")

    with rasterio.open(input_path) as src:
        R = src.read(1)
        G = src.read(2)
        B = src.read(3)
        meta = src.meta.copy()
        # Where the source says "no data", every band is masked. Without
        # this the hole is converted as though it were black: on
        # SNP_21_2020_1.tif that is 34386 pixels, 21% of the raster, coming
        # out as L = -6e-08 and written as valid. The output then declared
        # nodata=-9999 that no pixel carried, so a GIS had no way to tell.
        valid = np.ones(R.shape, dtype=bool)
        for b in range(1, 4):
            valid &= src.read_masks(b) != 0
        if not quiet:
            print(f"  Input: {src.height}×{src.width}, {src.count} bands, {src.dtypes[0]}")

    t0 = time.time()
    comps, names = convertbands(R, G, B, space)
    dt = time.time() - t0

    # Stamp the declared nodata into the pixels it describes.
    if not valid.all():
        comps = tuple(np.where(valid, c, nodata).astype(np.float32)
                      for c in comps)
        if not quiet:
            print(f"  Nodata: {int((~valid).sum())} px "
                  f"({100 * (~valid).mean():.1f}%) written as {nodata}")
    if not quiet:
        print(f"  Converted: {len(comps)} bands ({names}) in {dt:.3f}s")

    # Multi-band output
    multi_path = output_dir / f"{base}_{space}.tif"
    if save_multiband:
        meta_out = meta.copy()
        meta_out.update(count=len(comps), dtype="float32", nodata=nodata)
        with rasterio.open(multi_path, "w", **meta_out) as dst:
            dst.write(np.stack(comps).astype(np.float32))
        if not quiet:
            print(f"  Written: {multi_path.name}")

    # Single-band outputs
    if save_singlebands:
        meta_s = meta.copy()
        meta_s.update(count=1, dtype="float32", nodata=nodata)
        for comp, name in zip(comps, names):
            path = output_dir / f"{base}_{name}.tif"
            with rasterio.open(path, "w", **meta_s) as dst:
                dst.write(comp.astype(np.float32), 1)
        if not quiet:
            print(f"  Written: {len(names)} single-band files")

    return multi_path
