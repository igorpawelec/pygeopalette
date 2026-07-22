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
        Side of the square window the raster is processed in, in pixels.
        Peak memory is roughly ``block_size**2 * n_out_bands * 4`` bytes
        rather than the whole raster, which is what lets a scene larger
        than RAM be converted at all. The result does not depend on it —
        every conversion is pointwise, and ``tests/`` checks that the
        output is bit-identical across block sizes. ``0`` reads the whole
        raster in one go.
    quiet : bool
        Suppress progress messages.

    Returns
    -------
    Path
        The multi-band output when ``save_multiband`` is set, otherwise the
        output directory (single-band files are named after their
        components, so there is no single path to return).

    Raises
    ------
    ValueError
        If both ``save_multiband`` and ``save_singlebands`` are ``False``:
        the whole raster would be read and converted and nothing written,
        which is never intended and used to return a path to a file that
        was never created.
    """
    _check_rasterio()
    import time
    from contextlib import ExitStack
    from rasterio.windows import Window

    if not save_multiband and not save_singlebands:
        raise ValueError(
            "nothing to write: both save_multiband and save_singlebands are "
            "False. Set at least one."
        )

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem

    if not quiet:
        print(f"GeoPalette: {input_path.name} -> {space}")

    with rasterio.open(input_path) as src:
        meta = src.meta.copy()
        if not quiet:
            print(f"  Input: {src.height}x{src.width}, {src.count} bands, {src.dtypes[0]}")

        # One pixel through the conversion, only to learn how many bands
        # come out and what they are called. The output files have to be
        # opened before the first block can be written.
        probe, names = convertbands(*(np.zeros((1, 1), np.uint8),) * 3, space)
        n_out = len(probe)

        if block_size and block_size > 0:
            windows = [
                Window(c, r, min(block_size, src.width - c),
                       min(block_size, src.height - r))
                for r in range(0, src.height, block_size)
                for c in range(0, src.width, block_size)
            ]
        else:
            windows = [Window(0, 0, src.width, src.height)]

        meta_out = meta.copy()
        meta_out.update(count=n_out, dtype="float32", nodata=nodata)
        meta_s = meta.copy()
        meta_s.update(count=1, dtype="float32", nodata=nodata)

        multi_path = output_dir / f"{base}_{space}.tif"
        t0 = time.time()
        n_nodata = 0
        n_total = src.height * src.width

        with ExitStack() as stack:
            dst_multi = (stack.enter_context(
                rasterio.open(multi_path, "w", **meta_out))
                if save_multiband else None)
            dst_single = [
                stack.enter_context(
                    rasterio.open(output_dir / f"{base}_{n}.tif", "w", **meta_s))
                for n in names
            ] if save_singlebands else []

            for win in windows:
                R = src.read(1, window=win)
                G = src.read(2, window=win)
                B = src.read(3, window=win)
                # Where the source says "no data", every band is masked.
                # Without this the hole is converted as though it were
                # black: on SNP_21_2020_1.tif that is 34386 pixels, 21% of
                # the raster, coming out as L = -6e-08 and written as
                # valid. The output then declared nodata=-9999 that no
                # pixel carried, so a GIS had no way to tell.
                valid = np.ones(R.shape, dtype=bool)
                for b in range(1, 4):
                    valid &= src.read_masks(b, window=win) != 0

                comps, _ = convertbands(R, G, B, space)
                if not valid.all():
                    n_nodata += int((~valid).sum())
                    comps = tuple(np.where(valid, c, nodata) for c in comps)
                comps = [np.asarray(c, dtype=np.float32) for c in comps]

                if dst_multi is not None:
                    dst_multi.write(np.stack(comps), window=win)
                for dst, comp in zip(dst_single, comps):
                    dst.write(comp, 1, window=win)

        dt = time.time() - t0

    if n_nodata and not quiet:
        print(f"  Nodata: {n_nodata} px "
              f"({100 * n_nodata / n_total:.1f}%) written as {nodata}")
    if not quiet:
        blocks = f", {len(windows)} block(s) of {block_size}" if len(windows) > 1 else ""
        print(f"  Converted: {n_out} bands ({names}) in {dt:.3f}s{blocks}")
        if save_multiband:
            print(f"  Written: {multi_path.name}")
        if save_singlebands:
            print(f"  Written: {len(names)} single-band files")

    # Only the multiband file has a single path; single-band outputs are one
    # file per component, so the directory is the honest answer there. The
    # old code returned multi_path unconditionally, i.e. a path to a file it
    # had not written whenever save_multiband was False.
    return multi_path if save_multiband else output_dir
