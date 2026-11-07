"""
0_inspect_images.py
--------------------
Inspect all IQ and Phase image pairs:
  - Print image sizes and modes
  - Print unique RGB colors in each Phase map
  - Save side-by-side visualization grid
  
Run this FIRST before any preprocessing.
"""

import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter

# ── Paths ──────────────────────────────────────────────────────────────────────
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "IQ and EBSD Phase maps")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "inspection")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Valid pairs (IQ 7 excluded — inconsistent colormap) ───────────────────────
PAIRS = [
    ("IQ.tif",   "Phase.tif"),
    ("IQ 1.tif", "Phase 1.tif"),
    ("IQ 2.tif", "Phase 2.tif"),
    ("IQ 3.tif", "Phase 3.tif"),
    ("IQ 4.tif", "Phase 4.tif"),
    ("IQ 5.tif", "Phase 5.tif"),
    ("IQ 6.tif", "Phase 6.tif"),
]


def get_unique_colors(phase_arr: np.ndarray, top_n: int = 10):
    """Return the top-N most common (R,G,B) colors in a phase image."""
    h, w, c = phase_arr.shape
    pixels = phase_arr.reshape(-1, c)
    # Convert each pixel to a tuple
    color_counts = Counter(map(tuple, pixels.tolist()))
    return color_counts.most_common(top_n)


def main():
    print("=" * 65)
    print("  EBSD Image Inspection Report")
    print("=" * 65)

    n = len(PAIRS)
    fig, axes = plt.subplots(n, 2, figsize=(10, 3.5 * n))

    for idx, (iq_name, phase_name) in enumerate(PAIRS):
        iq_path    = os.path.join(IMAGE_DIR, iq_name)
        phase_path = os.path.join(IMAGE_DIR, phase_name)

        iq_img    = Image.open(iq_path).convert("RGB")
        phase_img = Image.open(phase_path).convert("RGB")

        iq_arr    = np.array(iq_img)
        phase_arr = np.array(phase_img)

        # Convert IQ to grayscale for display
        iq_gray = np.array(iq_img.convert("L"))

        print(f"\nPair {idx}:")
        print(f"  IQ    → {iq_name}    | size={iq_img.size} | mode={iq_img.mode}")
        print(f"  Phase → {phase_name} | size={phase_img.size} | mode={phase_img.mode}")

        unique_colors = get_unique_colors(phase_arr)
        print(f"  Top unique Phase RGB colors (R,G,B): pixel_count")
        for color, count in unique_colors:
            pct = 100.0 * count / (phase_arr.shape[0] * phase_arr.shape[1])
            label = "← Ferrite?" if color[0] > 150 and color[1] < 80 else \
                    "← Austenite?" if color[1] > 150 and color[0] < 80 else \
                    "← Unindexed?" if all(c < 15 for c in color) else ""
            print(f"    RGB{color} → {count:7,} px ({pct:5.1f}%)  {label}")

        # Plot
        axes[idx, 0].imshow(iq_gray, cmap="gray")
        axes[idx, 0].set_title(f"IQ: {iq_name}", fontsize=9)
        axes[idx, 0].axis("off")

        axes[idx, 1].imshow(phase_arr)
        axes[idx, 1].set_title(f"Phase: {phase_name}", fontsize=9)
        axes[idx, 1].axis("off")

    plt.suptitle("IQ & Phase Map Pairs — Visual Inspection", fontsize=13, fontweight="bold")
    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "inspection_grid.png")
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    print(f"\n[OK] Saved inspection grid → {out_path}")
    plt.show()


if __name__ == "__main__":
    main()
