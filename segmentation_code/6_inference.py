"""
6_inference.py
---------------
Run the trained model on a full 1024×1024 IQ image using a sliding 128×128 window.
Stitches patch predictions back into a full-resolution segmentation map.

Usage:
    python 6_inference.py --iq "path/to/IQ.tif" [--overlap]

Output:
    outputs/inference/
        <name>_segmentation.png    RGB colored segmentation
        <name>_overlay.png         IQ + segmentation overlay
        <name>_mask.npy            raw label mask (uint8)
        <name>_report.txt          phase fractions
"""

import os
import argparse
import numpy as np
import torch
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from unet_model import build_model
from utils      import load_checkpoint, label_to_rgb, CLASS_NAMES, IGNORE_INDEX

# ── Paths ──────────────────────────────────────────────────────────────────────
CKPT_DIR   = os.path.join(os.path.dirname(__file__), "checkpoints")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "inference")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PATCH_SIZE = 128


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_iq_image(path: str) -> np.ndarray:
    """Load an IQ image (.tif) → grayscale float32 [0,1] numpy array."""
    img = Image.open(path).convert("L")
    return np.array(img, dtype=np.float32) / 255.0


@torch.no_grad()
def sliding_window_inference(
    model: torch.nn.Module,
    iq: np.ndarray,
    patch_size: int = PATCH_SIZE,
    overlap: bool = False,
    device: torch.device = torch.device("cpu"),
) -> np.ndarray:
    """
    Run model on full IQ image using non-overlapping (or overlapping) windows.

    Args:
        model:      trained UNet
        iq:         (H, W) float32 grayscale IQ image
        patch_size: 128
        overlap:    if True, use stride=patch_size//2 and average overlapping predictions
        device:     torch device

    Returns:
        pred_map: (H, W) uint8 label mask — 0=Ferrite, 1=Austenite, 255=unindexed
    """
    model.eval()
    H, W = iq.shape
    stride = patch_size // 2 if overlap else patch_size

    # Pad image so it tiles evenly
    pad_h = (patch_size - H % patch_size) % patch_size
    pad_w = (patch_size - W % patch_size) % patch_size
    iq_padded = np.pad(iq, ((0, pad_h), (0, pad_w)), mode="reflect")
    H_pad, W_pad = iq_padded.shape

    # Accumulation buffers
    score_map = np.zeros((2, H_pad, W_pad), dtype=np.float32)   # logit scores
    count_map = np.zeros((H_pad, W_pad),    dtype=np.float32)   # overlap counts

    # Slide window
    row_positions = range(0, H_pad - patch_size + 1, stride)
    col_positions = range(0, W_pad - patch_size + 1, stride)

    patches_batch = []
    positions     = []

    for r in row_positions:
        for c in col_positions:
            patch = iq_padded[r:r+patch_size, c:c+patch_size]
            patches_batch.append(patch)
            positions.append((r, c))

    # Run in mini-batches of 32 for speed
    BATCH = 32
    for batch_start in range(0, len(patches_batch), BATCH):
        batch = patches_batch[batch_start:batch_start+BATCH]
        pos   = positions[batch_start:batch_start+BATCH]

        # Stack: (B, 1, 128, 128)
        tensor = torch.from_numpy(
            np.stack(batch, axis=0)[:, np.newaxis, :, :]
        ).float().to(device)

        logits = model(tensor).cpu().numpy()  # (B, 2, 128, 128)

        for logit, (r, c) in zip(logits, pos):
            score_map[:, r:r+patch_size, c:c+patch_size] += logit
            count_map[   r:r+patch_size, c:c+patch_size] += 1.0

    # Average overlapping predictions
    count_map = np.maximum(count_map, 1.0)
    score_map /= count_map[np.newaxis, :, :]

    # Argmax over classes
    pred_map = score_map.argmax(axis=0).astype(np.uint8)

    # Crop back to original size
    pred_map = pred_map[:H, :W]

    return pred_map


def save_results(iq: np.ndarray, pred_map: np.ndarray, name: str):
    """Save segmentation image, overlay, mask, and phase fraction report."""

    seg_rgb = label_to_rgb(pred_map)  # (H, W, 3) uint8

    # ── Save raw mask ─────────────────────────────────────────────────────────
    mask_path = os.path.join(OUTPUT_DIR, f"{name}_mask.npy")
    np.save(mask_path, pred_map)

    # ── Segmentation PNG ──────────────────────────────────────────────────────
    seg_path = os.path.join(OUTPUT_DIR, f"{name}_segmentation.png")
    Image.fromarray(seg_rgb).save(seg_path)

    # ── Figure: IQ | Segmentation | Overlay ──────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].imshow(iq, cmap="gray")
    axes[0].set_title("IQ Image (input)", fontsize=11)
    axes[0].axis("off")

    axes[1].imshow(seg_rgb)
    axes[1].set_title("Predicted Segmentation", fontsize=11)
    axes[1].axis("off")

    axes[2].imshow(iq, cmap="gray")
    axes[2].imshow(seg_rgb, alpha=0.4)
    axes[2].set_title("IQ + Segmentation Overlay", fontsize=11)
    axes[2].axis("off")

    legend_patches = [
        mpatches.Patch(color=[220/255, 50/255, 50/255], label="Ferrite (class 0)"),
        mpatches.Patch(color=[50/255, 200/255, 50/255], label="Austenite (class 1)"),
    ]
    fig.legend(handles=legend_patches, loc="upper right", fontsize=10)
    plt.suptitle(f"EfficientNet-UNet Segmentation: {name}", fontsize=13, fontweight="bold")
    plt.tight_layout()

    overlay_path = os.path.join(OUTPUT_DIR, f"{name}_overlay.png")
    plt.savefig(overlay_path, dpi=120, bbox_inches="tight")
    print(f"  Figure saved → {overlay_path}")
    plt.close()

    # ── Phase fractions report ────────────────────────────────────────────────
    total_px  = pred_map.size
    ferrite   = float(np.sum(pred_map == 0)) / total_px * 100
    austenite = float(np.sum(pred_map == 1)) / total_px * 100
    unindexed = float(np.sum(pred_map == 255)) / total_px * 100

    report = (
        f"Phase Fraction Report — {name}\n"
        f"{'='*40}\n"
        f"Ferrite   (class 0): {ferrite:.2f}%\n"
        f"Austenite (class 1): {austenite:.2f}%\n"
        f"Unindexed (class 255): {unindexed:.2f}%\n"
    )
    print("\n" + report)

    report_path = os.path.join(OUTPUT_DIR, f"{name}_report.txt")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Report saved → {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="EfficientNet-UNet inference on a full IQ image"
    )
    parser.add_argument(
        "--iq", type=str,
        default=os.path.join(os.path.dirname(__file__),
                             "..", "IQ and EBSD Phase maps", "IQ.tif"),
        help="Path to the IQ .tif image"
    )
    parser.add_argument(
        "--overlap", action="store_true",
        help="Use 50%% overlapping windows (smoother boundaries, slower)"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("  Full-Image Inference — EfficientNet-B0 UNet")
    print("=" * 65)
    print(f"  Input : {args.iq}")
    print(f"  Overlap: {args.overlap}")

    device = get_device()

    # ── Load model ────────────────────────────────────────────────────────────
    model = build_model().to(device)
    load_checkpoint(model, optimizer=None, save_dir=CKPT_DIR,
                    filename="best_model.pth", device=str(device))

    # ── Load IQ image ─────────────────────────────────────────────────────────
    iq   = load_iq_image(args.iq)
    name = os.path.splitext(os.path.basename(args.iq))[0].replace(" ", "_")
    print(f"  IQ image shape: {iq.shape}")

    # ── Sliding window inference ──────────────────────────────────────────────
    print(f"\nRunning sliding-window inference (patch={PATCH_SIZE}, overlap={args.overlap})...")
    pred_map = sliding_window_inference(model, iq, PATCH_SIZE, args.overlap, device)
    print(f"  Prediction shape: {pred_map.shape}")

    # ── Save results ──────────────────────────────────────────────────────────
    save_results(iq, pred_map, name)

    print("\n[OK] Inference complete.")
    print(f"   Outputs → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
