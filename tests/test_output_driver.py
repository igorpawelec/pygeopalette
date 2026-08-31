"""The converted raster is a GeoTIFF whatever the input was.

`convert_raster` builds its output profile from the input's metadata, and that
metadata carries the input's driver. Without an explicit override the result is
written in the input's format under a .tif name -- and for a VRT input the write
fails outright with "Writing through VRTSourcedRasterBand is not supported",
which is how this was found: choosing which band is red in the QGIS plugin hands
this function a VRT of the selected bands.

ENVI is used as the awkward input because rasterio writes it without needing the
GDAL Python bindings, and it is emphatically not GTiff.

Run: pytest tests/test_output_driver.py -v
"""
import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")

from rasterio.transform import from_origin  # noqa: E402

from pygeopalette.io_utils import convert_raster  # noqa: E402


def _make(path, driver):
    with rasterio.open(
        str(path), "w", driver=driver, height=16, width=16, count=3,
        dtype="float32", crs="EPSG:2180",
        transform=from_origin(500000, 300000, 0.25, 0.25), nodata=0.0,
    ) as dst:
        rng = np.random.default_rng(0)
        dst.write(rng.integers(20, 200, (3, 16, 16)).astype("float32"))


@pytest.mark.parametrize("driver,ext", [("ENVI", ""), ("GTiff", ".tif")])
def test_convert_raster_always_writes_gtiff(tmp_path, driver, ext):
    """A profile inherited from a non-GTiff input must not decide the output."""
    src = tmp_path / f"in_{driver}{ext}"
    _make(src, driver)
    out_dir = tmp_path / f"out_{driver}"
    out_dir.mkdir()
    convert_raster(str(src), str(out_dir), "lab", quiet=True)

    tifs = sorted(out_dir.glob("*.tif"))
    assert tifs, f"no GeoTIFF written for a {driver} input"
    with rasterio.open(str(tifs[0])) as res:
        assert res.meta["driver"] == "GTiff", (
            f"input driver {driver} leaked into the output")
        assert res.count == 3
        assert res.meta["dtype"] == "float32"
