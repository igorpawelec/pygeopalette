"""
geopalette.__main__
~~~~~~~~~~~~~~~~~~~
Command-line interface:  ``python -m geopalette``
"""

import argparse
import sys

from .conversions import available_spaces
from .io_utils import convert_raster


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="geopalette",
        description="Convert RGB rasters to different color spaces.",
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Input RGB GeoTIFF"
    )
    parser.add_argument(
        "-o", "--outdir", required=True, help="Output directory"
    )
    parser.add_argument(
        "-s", "--space", required=True,
        choices=available_spaces(),
        help="Target color space",
    )
    parser.add_argument(
        "--single-bands", action="store_true",
        help="Also save each component as a separate TIFF",
    )
    parser.add_argument(
        "--no-multiband", action="store_true",
        help="Skip writing multi-band output",
    )
    parser.add_argument(
        "--nodata", type=float, default=-9999.0,
        help="NoData value (default: -9999.0)",
    )

    args = parser.parse_args(argv)

    try:
        out = convert_raster(
            args.input,
            args.outdir,
            args.space,
            save_multiband=not args.no_multiband,
            save_singlebands=args.single_bands,
            nodata=args.nodata,
        )
    except (OSError, ValueError) as e:
        # a missing raster or a bad space is a user mistake, not a crash;
        # a traceback helps nobody here
        print(f"geopalette: error: {e}", file=sys.stderr)
        return 1

    print(f"Done -> {out}")
    return 0


if __name__ == "__main__":
    # main()'s return value is the exit code. Without sys.exit() a failure
    # still reports success, and any script or CI step checking $? misses it.
    sys.exit(main())
