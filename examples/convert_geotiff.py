"""
pygeopalette_test.py
~~~~~~~~~~~~~~~~~~
Example usage: convert an RGB GeoTIFF to CIELAB and display results.

Usage::

    python pygeopalette_test.py
"""

import os
import numpy as np

# ── Config ──────────────────────────────────────────────────────────────

INPUT = r"test_data/sample_rgb.tif"
BASE_OUT = r"results"
SPACE = "lab"

# ── Run ─────────────────────────────────────────────────────────────────

def main():
    import rasterio
    import matplotlib.pyplot as plt
    from pygeopalette import convertbands, available_spaces

    print(f"Available spaces: {available_spaces()}")

    os.makedirs(BASE_OUT, exist_ok=True)
    out_dir = os.path.join(BASE_OUT, SPACE)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(INPUT))[0]

    # Read raster
    with rasterio.open(INPUT) as src:
        meta = src.meta.copy()
        R, G, B = src.read(1), src.read(2), src.read(3)

    # Convert
    comps, names = convertbands(R, G, B, SPACE)
    print(f"Converted to {SPACE}: components = {names}")

    # Save multi-band
    multi_path = os.path.join(out_dir, f"{base}_{SPACE}.tif")
    meta3 = meta.copy()
    meta3.update(count=len(comps), dtype="float32")
    with rasterio.open(multi_path, "w", **meta3) as dst:
        dst.write(np.stack(comps).astype(np.float32))
    print(f"Saved: {multi_path}")

    # Plot
    orig = np.dstack((R, G, B)) / 255.0
    raw = np.dstack(comps[:3])
    conv = np.stack(
        [
            (lambda ch: (ch - ch.min()) / (ch.max() - ch.min() + 1e-8))(
                raw[..., i]
            )
            for i in range(min(3, len(comps)))
        ],
        axis=-1,
    )

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    ax[0].imshow(orig)
    ax[0].set_title("RGB")
    ax[0].axis("off")
    ax[1].imshow(conv)
    ax[1].set_title(SPACE.upper())
    ax[1].axis("off")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
