"""
pytest suite for GeoPalette.
Run: pytest tests/test_geopalette.py -v
"""

import numpy as np
import pytest


@pytest.fixture
def rgb_random():
    np.random.seed(42)
    R = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    G = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    B = np.random.randint(0, 256, (50, 50), dtype=np.uint8)
    return R, G, B


@pytest.fixture
def rgb_red():
    R = np.array([[255]], dtype=np.uint8)
    G = np.array([[0]], dtype=np.uint8)
    B = np.array([[0]], dtype=np.uint8)
    return R, G, B


@pytest.fixture
def rgb_white():
    v = np.array([[255]], dtype=np.uint8)
    return v, v.copy(), v.copy()


@pytest.fixture
def rgb_black():
    v = np.array([[0]], dtype=np.uint8)
    return v, v.copy(), v.copy()


class TestForwardConversions:

    def test_all_spaces_run(self, rgb_random):
        from geopalette import convertbands, available_spaces
        R, G, B = rgb_random
        for space in available_spaces():
            comps, names = convertbands(R, G, B, space)
            assert len(comps) == len(names)
            for c in comps:
                assert c.shape == (50, 50)
                assert c.dtype == np.float32

    def test_lab_reference_red(self, rgb_red):
        from geopalette import rgb_to_lab
        L, a, b = rgb_to_lab(*rgb_red)
        assert abs(L[0, 0] - 53.23) < 1.0
        assert abs(a[0, 0] - 80.11) < 1.0
        assert abs(b[0, 0] - 67.22) < 1.0

    def test_lab_white(self, rgb_white):
        from geopalette import rgb_to_lab
        L, a, b = rgb_to_lab(*rgb_white)
        assert abs(L[0, 0] - 100.0) < 1.0
        assert abs(a[0, 0]) < 1.0
        assert abs(b[0, 0]) < 1.0

    def test_lab_black(self, rgb_black):
        from geopalette import rgb_to_lab
        L, a, b = rgb_to_lab(*rgb_black)
        assert abs(L[0, 0]) < 1.0

    def test_oklab_reference_red(self, rgb_red):
        from geopalette import rgb_to_oklab
        L, a, b = rgb_to_oklab(*rgb_red)
        assert abs(L[0, 0] - 0.6279) < 0.01
        assert abs(a[0, 0] - 0.2249) < 0.01

    def test_hsv_red(self, rgb_red):
        from geopalette import rgb_to_hsv
        H, S, V = rgb_to_hsv(*rgb_red)
        assert abs(H[0, 0]) < 1.0  # H=0
        assert abs(S[0, 0] - 1.0) < 0.01
        assert abs(V[0, 0] - 1.0) < 0.01

    def test_ycbcr_reference(self, rgb_red):
        from geopalette import rgb_to_ycbcr
        Y, Cb, Cr = rgb_to_ycbcr(*rgb_red)
        assert abs(Y[0, 0] - 81.48) < 0.5
        assert abs(Cr[0, 0] - 240.0) < 0.5

    def test_jzazbz_runs(self, rgb_red):
        from geopalette import rgb_to_jzazbz
        Jz, az, bz = rgb_to_jzazbz(*rgb_red)
        assert Jz[0, 0] > 0
        assert Jz.dtype == np.float32

    def test_invalid_space(self, rgb_random):
        from geopalette import convertbands
        with pytest.raises(ValueError, match="Unknown space"):
            convertbands(*rgb_random, "nonexistent")


class TestInverseConversions:

    def test_lab_roundtrip(self, rgb_random):
        from geopalette import rgb_to_lab, lab_to_rgb
        R, G, B = rgb_random
        L, a, b = rgb_to_lab(R, G, B)
        R2, G2, B2 = lab_to_rgb(L, a, b)
        # Roundtrip: correlation > 0.99
        corr = np.corrcoef(R2.ravel(), (R / 255.0).ravel())[0, 1]
        assert corr > 0.99

    def test_oklab_roundtrip(self, rgb_random):
        from geopalette import rgb_to_oklab, oklab_to_rgb
        R, G, B = rgb_random
        L, a, b = rgb_to_oklab(R, G, B)
        R2, G2, B2 = oklab_to_rgb(L, a, b)
        corr = np.corrcoef(np.clip(R2, 0, 1).ravel(), (R / 255.0).ravel())[0, 1]
        assert corr > 0.99

    def test_hsv_roundtrip(self, rgb_random):
        from geopalette import rgb_to_hsv, hsv_to_rgb
        R, G, B = rgb_random
        H, S, V = rgb_to_hsv(R, G, B)
        R2, G2, B2 = hsv_to_rgb(H, S, V)
        # HSV roundtrip should be near-perfect
        np.testing.assert_allclose(R2, R / 255.0, atol=0.01)
        np.testing.assert_allclose(G2, G / 255.0, atol=0.01)
        np.testing.assert_allclose(B2, B / 255.0, atol=0.01)

    def test_hsl_roundtrip(self, rgb_random):
        from geopalette import rgb_to_hsl, hsl_to_rgb
        R, G, B = rgb_random
        H, S, L = rgb_to_hsl(R, G, B)
        R2, G2, B2 = hsl_to_rgb(H, S, L)
        np.testing.assert_allclose(R2, R / 255.0, atol=0.01)
        np.testing.assert_allclose(G2, G / 255.0, atol=0.01)
        np.testing.assert_allclose(B2, B / 255.0, atol=0.01)

    def test_lab_red_roundtrip(self, rgb_red):
        from geopalette import rgb_to_lab, lab_to_rgb
        L, a, b = rgb_to_lab(*rgb_red)
        R2, G2, B2 = lab_to_rgb(L, a, b)
        assert abs(R2[0, 0] * 255 - 255) < 2.0
        assert abs(G2[0, 0] * 255) < 2.0
        assert abs(B2[0, 0] * 255) < 2.0


class TestAvailableSpaces:

    def test_count(self):
        from geopalette import available_spaces
        spaces = available_spaces()
        assert len(spaces) >= 14

    def test_jzazbz_included(self):
        from geopalette import available_spaces
        assert "jzazbz" in available_spaces()
        assert "jzczhz" in available_spaces()


class TestImports:

    def test_import(self):
        import geopalette
        assert hasattr(geopalette, '__version__')

    def test_import_inverses(self):
        from geopalette import lab_to_rgb, oklab_to_rgb, hsv_to_rgb, hsl_to_rgb
        assert callable(lab_to_rgb)
        assert callable(oklab_to_rgb)
        assert callable(hsv_to_rgb)
        assert callable(hsl_to_rgb)

    def test_convert_raster_quiet_param(self):
        """convert_raster accepts quiet parameter."""
        from geopalette.io_utils import convert_raster
        import inspect
        sig = inspect.signature(convert_raster)
        assert 'quiet' in sig.parameters


class TestCLI:
    """The command line had no tests at all until now.

    plGeoAdaptels, the sibling package, shipped two CLI defects that its
    changelog records -- a raw traceback where a message belonged, and a
    zero exit code on failure, which any script checking $? would have
    missed. Neither is exotic; both are invisible from inside the library.
    """

    @staticmethod
    def _raster():
        import pathlib
        p = pathlib.Path(__file__).resolve().parent.parent / "test_data" / \
            "SNP_21_2020_1.tif"
        if not p.exists():
            pytest.skip("test_data/SNP_21_2020_1.tif not present")
        return str(p)

    def test_parser_is_named(self):
        from geopalette.__main__ import main
        with pytest.raises(SystemExit):
            main(["--help"])

    def test_runs_and_writes(self, tmp_path):
        from geopalette.__main__ import main
        rc = main(["-i", self._raster(), "-o", str(tmp_path), "-s", "lab"])
        assert rc == 0
        assert any(tmp_path.iterdir()), "nothing was written"

    def test_missing_input_returns_one(self, tmp_path):
        """Not zero, and not a traceback."""
        from geopalette.__main__ import main
        rc = main(["-i", str(tmp_path / "nope.tif"), "-o", str(tmp_path),
                   "-s", "lab"])
        assert rc == 1

    def test_unknown_space_is_rejected_by_the_parser(self, tmp_path):
        from geopalette.__main__ import main
        with pytest.raises(SystemExit):
            main(["-i", self._raster(), "-o", str(tmp_path), "-s", "nope"])

    def test_single_bands_writes_more(self, tmp_path):
        from geopalette.__main__ import main
        multi = tmp_path / "multi"; multi.mkdir()
        both = tmp_path / "both"; both.mkdir()
        main(["-i", self._raster(), "-o", str(multi), "-s", "lab"])
        main(["-i", self._raster(), "-o", str(both), "-s", "lab",
              "--single-bands"])
        assert len(list(both.iterdir())) > len(list(multi.iterdir()))

    def test_progress_output_survives_a_non_utf8_console(self, tmp_path):
        """The progress messages must encode on the console they print to.

        They used to carry `->` as U+2192 and `x` as U+00D7. On a cp1250
        console -- the default on a Polish Windows -- the first print raised
        UnicodeEncodeError, which subclasses ValueError, so the CLI caught it
        as a user error and exited 1 having written nothing. The whole CLI
        was unusable there.

        The existing tests missed it because pytest captures stdout to a
        UTF-8 buffer, which encodes anything. This forces the strictest
        realistic console, ascii, so a stray non-ASCII byte fails here
        instead of on the user's machine.
        """
        import io
        import sys
        from geopalette.__main__ import main

        buf = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(["-i", self._raster(), "-o", str(tmp_path), "-s", "lab"])
            buf.flush()
        finally:
            sys.stdout = old
        assert rc == 0
        assert any(tmp_path.iterdir())


class TestConvertRasterNodata:
    """The hole must be written as nodata, not converted as if it were black.

    convert_raster() read every band raw, so a source nodata region went
    through the colour transform like ordinary dark pixels: on
    SNP_21_2020_1.tif that is 34386 px, 21% of the raster, coming out as
    L = -6e-08. The output then declared nodata = -9999, which no pixel
    carried, so nothing downstream could tell the hole from real canopy.
    It also explains the suspiciously round `L[0.00, ...]` in the range
    table -- that minimum was the hole, not the image.
    """

    @staticmethod
    def _raster():
        import pathlib
        p = pathlib.Path(__file__).resolve().parent.parent / "test_data" / \
            "SNP_21_2020_1.tif"
        if not p.exists():
            pytest.skip("test_data/SNP_21_2020_1.tif not present")
        return str(p)

    def test_nodata_is_stamped_into_the_output(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster

        src = self._raster()
        out = convert_raster(src, str(tmp_path), "lab", quiet=True)

        with rasterio.open(src) as s:
            hole = (s.read() == 0).all(axis=0)
        if not hole.any():
            pytest.skip("this raster has no nodata to test with")

        with rasterio.open(out) as o:
            data = o.read()
            assert int((data[0] == o.nodata).sum()) == int(hole.sum()), \
                "declared nodata does not match the pixels it describes"
            # And the valid range no longer starts at the hole.
            assert data[0][~hole].min() > 1.0, \
                "L still reaches ~0, so the hole is still being converted"

    def test_a_raster_without_nodata_is_untouched(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster
        import numpy as np

        f = tmp_path / "full.tif"
        data = np.random.default_rng(0).integers(1, 256, (3, 12, 15),
                                                 dtype=np.uint8)
        with rasterio.open(f, "w", driver="GTiff", height=12, width=15,
                           count=3, dtype="uint8") as dst:
            dst.write(data)

        out = convert_raster(str(f), str(tmp_path), "lab", quiet=True)
        with rasterio.open(out) as o:
            assert int((o.read(1) == o.nodata).sum()) == 0


class TestBlockSize:
    """block_size must change memory, never the pixels.

    Until 0.6.0 the parameter was documented and did nothing: it was in the
    signature and the docstring and nowhere else, and the whole raster was
    read at once. Now that it is real, the thing worth guarding is that it
    stays invisible in the output -- every conversion is pointwise, so a
    block boundary must not be detectable in the result.
    """

    @staticmethod
    def _scene(d, h=37, w=53):
        rasterio = pytest.importorskip("rasterio")
        from rasterio.transform import from_origin
        import pathlib
        rng = np.random.default_rng(4)
        rgb = rng.integers(1, 256, (3, h, w), dtype=np.uint8)
        # A nodata hole straddling the boundary at block_size=8, so a
        # per-block mask that was computed for the wrong window would show.
        rgb[:, 5:12, 5:12] = 0
        p = pathlib.Path(d) / "scene.tif"
        with rasterio.open(p, "w", driver="GTiff", height=h, width=w, count=3,
                           dtype="uint8", nodata=0,
                           transform=from_origin(0, 0, 1, 1),
                           crs="EPSG:2180") as f:
            f.write(rgb)
        return p

    def test_output_is_independent_of_block_size(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster
        from geopalette.conversions import available_spaces
        src = self._scene(tmp_path)
        for space in available_spaces():
            ref = None
            # 0 reads the whole raster; 8 and 13 tile it, and 13 divides
            # neither 37 nor 53, so the last row and column of blocks are
            # partial. 4096 exceeds the raster, giving a single window.
            for bs in (0, 8, 13, 4096):
                out = tmp_path / f"o_{space}_{bs}"
                out.mkdir()
                got = convert_raster(src, out, space, block_size=bs, quiet=True)
                with rasterio.open(got) as f:
                    cur = (f.read(), f.nodata, f.transform, f.crs, f.count)
                if ref is None:
                    ref = cur
                    continue
                assert np.array_equal(cur[0], ref[0], equal_nan=True), (
                    f"{space}: block_size={bs} changed the pixels, "
                    f"max |diff| = {np.nanmax(np.abs(cur[0] - ref[0]))}")
                assert cur[1:] == ref[1:], f"{space}: block_size={bs} header differs"

    def test_return_path_is_honest_about_what_it_wrote(self, tmp_path):
        """save_multiband=False must not return a multiband path that was
        never created -- it did, contradicting the docstring."""
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster
        src = self._scene(tmp_path)
        out = tmp_path / "s"; out.mkdir()
        ret = convert_raster(src, out, "lab", save_multiband=False,
                             save_singlebands=True, quiet=True)
        assert ret == out, ret
        # Whatever comes back, a caller must be able to reach the output.
        assert ret.exists()

    def test_writing_nothing_is_refused(self, tmp_path):
        """Both flags off used to read and convert the whole raster, write
        nothing, and return a path to a file it never made."""
        from geopalette.io_utils import convert_raster
        src = self._scene(tmp_path)
        out = tmp_path / "n"; out.mkdir()
        with pytest.raises(ValueError, match="nothing to write"):
            convert_raster(src, out, "lab", save_multiband=False,
                           save_singlebands=False, quiet=True)

    def test_the_hole_survives_blocking(self, tmp_path):
        """Guards the test above: with no hole it would prove much less."""
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster
        src = self._scene(tmp_path)
        out = tmp_path / "o"
        out.mkdir()
        got = convert_raster(src, out, "lab", block_size=8, quiet=True)
        with rasterio.open(got) as f:
            assert int((f.read(1) == f.nodata).sum()) == 49

    def test_single_bands_are_blocked_too(self, tmp_path):
        rasterio = pytest.importorskip("rasterio")
        from geopalette.io_utils import convert_raster
        src = self._scene(tmp_path)
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir(); b.mkdir()
        convert_raster(src, a, "lab", block_size=0,
                       save_multiband=False, save_singlebands=True, quiet=True)
        convert_raster(src, b, "lab", block_size=8,
                       save_multiband=False, save_singlebands=True, quiet=True)
        names = sorted(p.name for p in a.glob("*.tif"))
        assert len(names) == 3, names
        for n in names:
            with rasterio.open(a / n) as f1, rasterio.open(b / n) as f2:
                assert np.array_equal(f1.read(), f2.read(), equal_nan=True), n
