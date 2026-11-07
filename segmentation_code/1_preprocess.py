"""
1_preprocess.py
----------------
Load all valid IQ and Phase image pairs, preprocess them, and save as .npy arrays.

IQ images  (RGB 1024×1024) → grayscale float32 [0,1]
Phase maps (RGB 1024×1024) → kept as RGB uint8 (for label generation in next step)

Output:
    preprocessed/
        iq/     img0.npy ... img6.npy   (shape: 1024×1024, float32)
        phase/  img0.npy ... img6.npy   (shape: 1024×1024×3, uint8)
"""

import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# ── Paths ──────────────────────────────────────────────────────────────────────
IMAGE_DIR    = os.path.join(os.path.dirname(__file__), "..", "IQ and EBSD Phase maps")
PREPROC_DIR  = os.path.join(os.path.dirname(__file__), "preprocessed")
IQ_OUT_DIR   = os.path.join(PREPROC_DIR, "iq")
PHASE_OUT_DIR= os.path.join(PREPROC_DIR, "phase")
VIZ_DIR      = os.path.join(os.path.dirname(__file__), "outputs", "preprocessing")

for d in [IQ_OUT_DIR, PHASE_OUT_DIR, VIZ_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Valid pairs ────────────────────────────────────────────────────────────────
PAIRS = [
    ("IQ.tif",   "Phase.tif"),
    ("IQ 1.tif", "Phase 1.tif"),
    ("IQ 2.tif", "Phase 2.tif"),
    ("IQ 3.tif", "Phase 3.tif"),
    ("IQ 4.tif", "Phase 4.tif"),
    ("IQ 5.tif", "Phase 5.tif"),
    ("IQ 6.tif", "Phase 6.tif"),
]

EXPECTED_SIZE = (1024, 1024)


def load_iq_as_gray(path: str) -> np.ndarray:
    """Load an IQ image (RGB false-color) → grayscale float32 [0, 1]."""
    img = Image.open(path).convert("L")  # L = luminance/grayscale
    arr = np.array(img, dtype=np.float32) / 255.0
    return arr


def load_phase_rgb(path: str) -> np.ndarray:
    """Load a Phase image as RGB uint8."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


def verify_size(arr: np.ndarray, name: str):
    h, w = arr.shape[:2]
    if (w, h) != EXPECTED_SIZE:
        print(f"  [!]  {name}: unexpected size {(w, h)}, expected {EXPECTED_SIZE}")
    else:
        print(f"  [OK] {name}: size OK {(w, h)}")


def main():
    print("=" * 60)
    print("  Preprocessing IQ & Phase Images")
    print("=" * 60)

    fig, axes = plt.subplots(len(PAIRS), 2, figsize=(10, 3.5 * len(PAIRS)))

    for idx, (iq_name, phase_name) in enumerate(PAIRS):
        iq_path    = os.path.join(IMAGE_DIR, iq_name)
        phase_path = os.path.join(IMAGE_DIR, phase_name)

        print(f"\nPair {idx}: {iq_name} | {phase_name}")

        # Load & process
        iq_gray   = load_iq_as_gray(iq_path)
        phase_rgb = load_phase_rgb(phase_path)

        verify_size(iq_gray, iq_name)
        verify_size(phase_rgb, phase_name)

        print(f"  IQ    → shape={iq_gray.shape}, dtype={iq_gray.dtype}, "
              f"min={iq_gray.min():.3f}, max={iq_gray.max():.3f}")
        print(f"  Phase → shape={phase_rgb.shape}, dtype={phase_rgb.dtype}")

        # Save
        iq_out    = os.path.join(IQ_OUT_DIR,    f"img{idx}.npy")
        phase_out = os.path.join(PHASE_OUT_DIR, f"img{idx}.npy")
        np.save(iq_out,    iq_gray)
        np.save(phase_out, phase_rgb)
        print(f"  Saved: {iq_out}")
        print(f"  Saved: {phase_out}")

        # Visualize overlay to confirm alignment
        axes[idx, 0].imshow(iq_gray, cmap="gray")
        axes[idx, 0].set_title(f"IQ Gray: {iq_name}", fontsize=8)
        axes[idx, 0].axis("off")

        axes[idx, 1].imshow(phase_rgb)
        axes[idx, 1].set_title(f"Phase RGB: {phase_name}", fontsize=8)
        axes[idx, 1].axis("off")

    plt.suptitle("Preprocessed IQ (gray) & Phase (RGB) — Alignment Check", fontsize=12)
    plt.tight_layout()
    out_path = os.path.join(VIZ_DIR, "preprocessed_pairs.png")
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    print(f"\n[OK] Saved visualization → {out_path}")

    print("\n[OK] Preprocessing complete.")
    print(f"   IQ arrays   → {IQ_OUT_DIR}")
    print(f"   Phase arrays → {PHASE_OUT_DIR}")


if __name__ == "__main__":
    main()
