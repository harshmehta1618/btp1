"""
2_label_generation.py
----------------------
Convert Phase RGB maps → integer class masks.

Color mapping (confirmed for Medium Mn Steel):
    Red-ish   (R>150, G<80, B<80)  → class 0  : Ferrite (BCC/α)
    Green-ish (G>150, R<80, B<80)  → class 1  : Austenite (FCC/γ)
    Black     (R<15, G<15, B<15)   → class 255 : Unindexed (masked during loss)

Output:
    preprocessed/
        labels/  img0.npy ... img6.npy  (shape: 1024×1024, uint8)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image

# ── Paths ──────────────────────────────────────────────────────────────────────
PHASE_DIR  = os.path.join(os.path.dirname(__file__), "preprocessed", "phase")
LABEL_DIR  = os.path.join(os.path.dirname(__file__), "preprocessed", "labels")
VIZ_DIR    = os.path.join(os.path.dirname(__file__), "outputs", "labels")

for d in [LABEL_DIR, VIZ_DIR]:
    os.makedirs(d, exist_ok=True)

NUM_IMAGES = 7  # img0 to img6

# ── Class definitions ──────────────────────────────────────────────────────────
CLASS_NAMES  = {0: "Ferrite (BCC)", 1: "Austenite (FCC)", 255: "Unindexed"}
CLASS_COLORS = {0: [255, 60, 60], 1: [60, 220, 60], 255: [30, 30, 30]}

# Visualization colormap: maps class id → display color
VIZ_CMAP = {0: [0.9, 0.2, 0.2],   # red for ferrite
            1: [0.2, 0.8, 0.2]}    # green for austenite


def rgb_to_label(phase_rgb: np.ndarray) -> np.ndarray:
    """
    Convert (H, W, 3) uint8 RGB Phase map → (H, W) uint8 label mask.

    Rules:
        Red-ish   → 0  (Ferrite)
        Green-ish → 1  (Austenite)
        Anything else (incl. black) → 255 (ignore)
    """
    R, G, B = phase_rgb[..., 0], phase_rgb[..., 1], phase_rgb[..., 2]

    label = np.full(phase_rgb.shape[:2], fill_value=255, dtype=np.uint8)

    # Ferrite: dominant red channel
    ferrite_mask   = (R > 150) & (G < 100) & (B < 100)
    # Austenite: dominant green channel
    austenite_mask = (G > 150) & (R < 100) & (B < 100)

    label[ferrite_mask]   = 0
    label[austenite_mask] = 1

    return label


def label_to_display(label: np.ndarray) -> np.ndarray:
    """Convert label mask → RGB image for visualization."""
    display = np.zeros((*label.shape, 3), dtype=np.uint8)
    display[label == 0]   = [220, 50,  50]   # Ferrite: red
    display[label == 1]   = [50,  200, 50]   # Austenite: green
    display[label == 255] = [25,  25,  25]   # Unindexed: dark gray
    return display


def print_class_stats(label: np.ndarray, name: str):
    total = label.size
    for cls_id, cls_name in CLASS_NAMES.items():
        count = int(np.sum(label == cls_id))
        pct   = 100.0 * count / total
        print(f"    class {cls_id if cls_id < 255 else '255'} ({cls_name}): "
              f"{count:8,} px  ({pct:5.1f}%)")


def main():
    print("=" * 60)
    print("  Label Generation: Phase RGB → Class Masks")
    print("=" * 60)

    fig, axes = plt.subplots(NUM_IMAGES, 3, figsize=(13, 3.5 * NUM_IMAGES))

    for idx in range(NUM_IMAGES):
        phase_path = os.path.join(PHASE_DIR, f"img{idx}.npy")
        phase_rgb  = np.load(phase_path)                 # (1024, 1024, 3) uint8

        label = rgb_to_label(phase_rgb)

        # Stats
        print(f"\nimg{idx} — Phase label statistics:")
        print_class_stats(label, f"img{idx}")

        # Check for unmapped pixels (not ferrite, not austenite, not pure black)
        unmapped = np.sum(label == 255)
        unindexed_pct = 100.0 * unmapped / label.size
        if unindexed_pct > 20:
            print(f"  [!]  High unindexed rate ({unindexed_pct:.1f}%) — "
                  f"check color thresholds in rgb_to_label()")

        # Save label
        label_path = os.path.join(LABEL_DIR, f"img{idx}.npy")
        np.save(label_path, label)
        print(f"  Saved → {label_path}")

        # Visualize
        display = label_to_display(label)
        axes[idx, 0].imshow(phase_rgb)
        axes[idx, 0].set_title(f"Phase RGB: img{idx}", fontsize=8)
        axes[idx, 0].axis("off")

        axes[idx, 1].imshow(display)
        axes[idx, 1].set_title(f"Label mask: img{idx}", fontsize=8)
        axes[idx, 1].axis("off")

        # Overlay: IQ + label contours
        iq_path = os.path.join(os.path.dirname(PHASE_DIR), "iq", f"img{idx}.npy")
        if os.path.exists(iq_path):
            iq = np.load(iq_path)
            axes[idx, 2].imshow(iq, cmap="gray")
            axes[idx, 2].imshow(display, alpha=0.35)
            axes[idx, 2].set_title(f"IQ + label overlay: img{idx}", fontsize=8)
            axes[idx, 2].axis("off")

    # Legend
    legend_patches = [
        mpatches.Patch(color=[220/255, 50/255, 50/255],  label="Ferrite (class 0)"),
        mpatches.Patch(color=[50/255, 200/255, 50/255],  label="Austenite (class 1)"),
        mpatches.Patch(color=[25/255, 25/255, 25/255],   label="Unindexed (class 255)"),
    ]
    fig.legend(handles=legend_patches, loc="upper right", fontsize=9)

    plt.suptitle("Phase RGB → Label Masks", fontsize=13, fontweight="bold")
    plt.tight_layout()
    out_path = os.path.join(VIZ_DIR, "label_masks.png")
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    print(f"\n[OK] Saved label visualization → {out_path}")
    print("\n[OK] Label generation complete.")
    print(f"   Labels → {LABEL_DIR}")


if __name__ == "__main__":
    main()
