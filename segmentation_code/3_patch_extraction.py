"""
3_patch_extraction.py
----------------------
Extract 128×128 patches from IQ and Phase label pairs at IDENTICAL coordinates.
Applies augmentation to (IQ, label) simultaneously using albumentations.
Splits at image level (not patch level) to prevent data leakage.

Folder structure output:
    patches/
        train/
            iq/      img{i}_r{r}_c{c}.npy   float32 (128,128)
            phase/   img{i}_r{r}_c{c}.npy   uint8   (128,128)
        val/
            iq/
            phase/
        test/
            iq/
            phase/

Image-level train/val/test split:
    Train: img0, img1, img2, img3, img4  (5 images)
    Val:   img5                          (1 image)
    Test:  img6                          (1 image)
"""

import os
import numpy as np
import albumentations as A
import matplotlib.pyplot as plt
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────
PATCH_SIZE  = 128
STRIDE      = 128   # non-overlapping (stride == patch size)
IGNORE_IDX  = 255

# Discard patches where more than this fraction of pixels are unindexed
MAX_IGNORE_FRACTION = 0.5

# ── Paths ──────────────────────────────────────────────────────────────────────
IQ_DIR    = os.path.join(os.path.dirname(__file__), "preprocessed", "iq")
LABEL_DIR = os.path.join(os.path.dirname(__file__), "preprocessed", "labels")
PATCH_DIR = os.path.join(os.path.dirname(__file__), "patches")
VIZ_DIR   = os.path.join(os.path.dirname(__file__), "outputs", "patches")

for d in [VIZ_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Image-level split ──────────────────────────────────────────────────────────
SPLIT_MAP = {
    0: "train", 1: "train", 2: "train",
    3: "train", 4: "train",
    5: "val",
    6: "test",
}

# ── Augmentation pipelines ─────────────────────────────────────────────────────
# Applied to (image, mask) simultaneously — guarantees same spatial transform

BASE_AUG = A.Compose([
    # No spatial transform for original (identity)
])

AUGMENTATIONS = [
    ("orig",      A.Compose([])),
    ("hflip",     A.Compose([A.HorizontalFlip(p=1.0)])),
    ("vflip",     A.Compose([A.VerticalFlip(p=1.0)])),
    ("rot90",     A.Compose([A.Rotate(limit=(90, 90), p=1.0)])),
    ("rot180",    A.Compose([A.Rotate(limit=(180, 180), p=1.0)])),
    ("rot270",    A.Compose([A.Rotate(limit=(270, 270), p=1.0)])),
    ("bright",    A.Compose([A.RandomBrightnessContrast(
                                brightness_limit=0.12,
                                contrast_limit=0.12, p=1.0)])),
]


def make_patch_dirs():
    for split in ("train", "val", "test"):
        for kind in ("iq", "phase"):
            os.makedirs(os.path.join(PATCH_DIR, split, kind), exist_ok=True)


def extract_and_save(img_idx: int, iq: np.ndarray, label: np.ndarray, split: str):
    """
    Crop 128×128 patches from iq and label at IDENTICAL (r, c) coordinates.
    Apply augmentations in lockstep (same transform to both).
    Save to patches/{split}/iq/ and patches/{split}/phase/.
    """
    H, W = iq.shape
    n_r = H // PATCH_SIZE
    n_c = W // PATCH_SIZE

    total_saved = 0
    total_skipped = 0

    for ri in range(n_r):
        for ci in range(n_c):
            r_start = ri * PATCH_SIZE
            c_start = ci * PATCH_SIZE

            # ── SAME coordinates for IQ and Phase ──────────────────────────
            iq_patch    = iq[r_start:r_start+PATCH_SIZE, c_start:c_start+PATCH_SIZE]
            label_patch = label[r_start:r_start+PATCH_SIZE, c_start:c_start+PATCH_SIZE]

            # ── Discard if too many unindexed pixels ───────────────────────
            ignore_frac = np.mean(label_patch == IGNORE_IDX)
            if ignore_frac > MAX_IGNORE_FRACTION:
                total_skipped += 1
                continue

            # ── Apply augmentations in lockstep ────────────────────────────
            # albumentations expects uint8 image for some transforms
            iq_uint8 = (iq_patch * 255).astype(np.uint8)

            for aug_name, aug_fn in AUGMENTATIONS:
                result = aug_fn(image=iq_uint8, mask=label_patch)
                aug_iq    = result["image"].astype(np.float32) / 255.0  # back to float32
                aug_label = result["mask"]                               # uint8, unchanged

                filename = f"img{img_idx}_r{ri:02d}_c{ci:02d}_{aug_name}.npy"

                iq_out_path    = os.path.join(PATCH_DIR, split, "iq",    filename)
                phase_out_path = os.path.join(PATCH_DIR, split, "phase", filename)

                np.save(iq_out_path,    aug_iq)
                np.save(phase_out_path, aug_label)
                total_saved += 1

    # ── Austenite Minority-Class Oversampling (TRAIN ONLY - ZERO DATA LEAKAGE) ──
    # Strictly applied only to training images (img0-img4).
    # val (img5) and test (img6) are never oversampled or touched.
    if split == "train":
        aus_r, aus_c = np.where(label == 1)
        if len(aus_r) > 0:
            rng = np.random.default_rng(seed=100 + img_idx)
            candidate_indices = rng.choice(len(aus_r), size=min(200, len(aus_r)), replace=False)
            aus_added = 0
            half = PATCH_SIZE // 2

            for c_idx in candidate_indices:
                if aus_added >= 25:  # 25 extra austenite-centered patches per training image
                    break
                cr = int(np.clip(aus_r[c_idx], half, H - half))
                cc = int(np.clip(aus_c[c_idx], half, W - half))
                r_start = cr - half
                c_start = cc - half

                iq_patch    = iq[r_start:r_start+PATCH_SIZE, c_start:c_start+PATCH_SIZE]
                label_patch = label[r_start:r_start+PATCH_SIZE, c_start:c_start+PATCH_SIZE]

                ignore_frac = np.mean(label_patch == IGNORE_IDX)
                aus_frac    = np.mean(label_patch == 1)

                # Require meaningful austenite presence and low unindexed pixels
                if ignore_frac > MAX_IGNORE_FRACTION or aus_frac < 0.15:
                    continue

                iq_uint8 = (iq_patch * 255).astype(np.uint8)

                for aug_name, aug_fn in AUGMENTATIONS:
                    result = aug_fn(image=iq_uint8, mask=label_patch)
                    aug_iq    = result["image"].astype(np.float32) / 255.0
                    aug_label = result["mask"]

                    filename = f"img{img_idx}_aus_{aus_added:02d}_{aug_name}.npy"
                    iq_out_path    = os.path.join(PATCH_DIR, split, "iq",    filename)
                    phase_out_path = os.path.join(PATCH_DIR, split, "phase", filename)

                    np.save(iq_out_path,    aug_iq)
                    np.save(phase_out_path, aug_label)
                    total_saved += 1

                aus_added += 1

    return total_saved, total_skipped


def verify_patch_pair(split: str, sample_n: int = 3):
    """Verify a random sample of saved patch pairs are correctly aligned."""
    iq_dir    = os.path.join(PATCH_DIR, split, "iq")
    phase_dir = os.path.join(PATCH_DIR, split, "phase")

    files = sorted(os.listdir(iq_dir))
    if len(files) == 0:
        return

    sample_files = files[:sample_n]
    fig, axes = plt.subplots(sample_n, 3, figsize=(10, 3 * sample_n))
    if sample_n == 1:
        axes = axes[np.newaxis, :]

    for row, fname in enumerate(sample_files):
        iq_patch    = np.load(os.path.join(iq_dir,    fname))
        phase_patch = np.load(os.path.join(phase_dir, fname))  # same filename!

        assert iq_patch.shape == (PATCH_SIZE, PATCH_SIZE), \
            f"IQ patch shape mismatch: {iq_patch.shape}"
        assert phase_patch.shape == (PATCH_SIZE, PATCH_SIZE), \
            f"Phase patch shape mismatch: {phase_patch.shape}"

        # Build display phase
        display = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.uint8)
        display[phase_patch == 0]   = [220, 50, 50]
        display[phase_patch == 1]   = [50, 200, 50]
        display[phase_patch == 255] = [25, 25, 25]

        axes[row, 0].imshow(iq_patch, cmap="gray")
        axes[row, 0].set_title(f"IQ: {fname}", fontsize=7)
        axes[row, 0].axis("off")

        axes[row, 1].imshow(display)
        axes[row, 1].set_title(f"Phase: {fname}", fontsize=7)
        axes[row, 1].axis("off")

        axes[row, 2].imshow(iq_patch, cmap="gray")
        axes[row, 2].imshow(display, alpha=0.4)
        axes[row, 2].set_title("Overlay (verify alignment)", fontsize=7)
        axes[row, 2].axis("off")

    plt.suptitle(f"Patch Pair Verification — {split} set", fontsize=11)
    plt.tight_layout()
    out_path = os.path.join(VIZ_DIR, f"verify_{split}.png")
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    print(f"  Verification grid saved → {out_path}")


def main():
    print("=" * 65)
    print("  Patch Extraction (128×128, non-overlapping, augmented)")
    print("=" * 65)

    make_patch_dirs()

    total_counts = {"train": 0, "val": 0, "test": 0}
    total_skips  = 0

    for img_idx in range(7):
        iq_path    = os.path.join(IQ_DIR,    f"img{img_idx}.npy")
        label_path = os.path.join(LABEL_DIR, f"img{img_idx}.npy")

        iq    = np.load(iq_path)    # float32 (1024,1024)
        label = np.load(label_path) # uint8   (1024,1024)

        split = SPLIT_MAP[img_idx]
        print(f"\nimg{img_idx} → split='{split}'")

        saved, skipped = extract_and_save(img_idx, iq, label, split)

        total_counts[split] += saved
        total_skips  += skipped

        print(f"  Saved: {saved} patches  |  Skipped (too many unindexed): {skipped}")

    print("\n" + "=" * 65)
    print("  Patch Extraction Summary")
    print("=" * 65)
    for split, cnt in total_counts.items():
        print(f"  {split:8s}: {cnt:5,} patches  "
              f"(raw={cnt // len(AUGMENTATIONS)}, ×{len(AUGMENTATIONS)} augmentations)")
    print(f"  Skipped  : {total_skips} patches (>{int(MAX_IGNORE_FRACTION*100)}% unindexed)")

    # Verify alignment of saved patches
    print("\n── Verifying patch pair alignment ──")
    for split in ["train", "val", "test"]:
        verify_patch_pair(split, sample_n=3)

    print("\n[OK] Patch extraction complete.")
    print(f"   Patches → {PATCH_DIR}")


if __name__ == "__main__":
    main()
