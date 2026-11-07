"""
5_evaluate.py
--------------
Load best model checkpoint and evaluate on the held-out TEST set.

Outputs:
  - Per-class IoU, F1, Pixel Accuracy
  - Phase fraction (predicted vs EBSD ground truth)
  - Confusion matrix
  - Qualitative segmentation grid (IQ | GT | Pred | Overlay)
  
  Saved to: outputs/evaluation/
"""

import os
import numpy as np
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from tqdm import tqdm

from dataset    import get_dataloaders
from unet_model import build_model
from utils      import (compute_metrics, print_metrics, label_to_rgb,
                        load_checkpoint, plot_predictions, IGNORE_INDEX,
                        CLASS_NAMES, NUM_CLASSES)

# ── Paths ──────────────────────────────────────────────────────────────────────
PATCH_DIR  = os.path.join(os.path.dirname(__file__), "patches")
CKPT_DIR   = os.path.join(os.path.dirname(__file__), "checkpoints")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "evaluation")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BATCH_SIZE  = 16
NUM_WORKERS = 0


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@torch.no_grad()
def run_inference_on_loader(model, loader, device, use_tta: bool = True):
    """
    Run model on full test loader.
    Supports Test-Time Augmentation (TTA) via 4-fold flip averaging.
    Returns (all_preds, all_labels, sample_iq).
    """
    model.eval()
    all_preds  = []
    all_labels = []
    sample_iq  = []  # for visualization

    for iq_batch, label_batch in tqdm(loader, desc=f"  Inference (TTA={use_tta})"):
        iq_batch = iq_batch.to(device)

        if use_tta:
            # 4 symmetric flips: orig, hflip, vflip, both
            p1 = torch.softmax(model(iq_batch), dim=1)
            p2 = torch.flip(torch.softmax(model(torch.flip(iq_batch, dims=[-1])), dim=1), dims=[-1])
            p3 = torch.flip(torch.softmax(model(torch.flip(iq_batch, dims=[-2])), dim=1), dims=[-2])
            p4 = torch.flip(torch.softmax(model(torch.flip(iq_batch, dims=[-1, -2])), dim=1), dims=[-1, -2])
            avg_probs = (p1 + p2 + p3 + p4) / 4.0
            preds = avg_probs.argmax(dim=1).cpu().numpy()
        else:
            logits = model(iq_batch)
            preds  = logits.argmax(dim=1).cpu().numpy()  # (B, 128, 128)

        all_preds.append(preds)
        all_labels.append(label_batch.numpy())
        sample_iq.append(iq_batch.cpu().squeeze(1).numpy())  # (B, 128, 128)

    return (
        np.concatenate(all_preds,  axis=0),   # (N, 128, 128)
        np.concatenate(all_labels, axis=0),   # (N, 128, 128)
        np.concatenate(sample_iq,  axis=0),   # (N, 128, 128)
    )


def plot_confusion_matrix(all_preds: np.ndarray, all_labels: np.ndarray,
                          save_path: str):
    valid = all_labels != IGNORE_INDEX
    cm = confusion_matrix(
        all_labels[valid], all_preds[valid],
        labels=list(range(NUM_CLASSES))
    )
    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=CLASS_NAMES
    )
    fig, ax = plt.subplots(figsize=(6, 5))
    disp.plot(ax=ax, colorbar=True, cmap="Blues", values_format="d")
    ax.set_title("Confusion Matrix — Test Set", fontsize=12)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    print(f"  Confusion matrix saved → {save_path}")
    # plt.close()


def plot_phase_fraction_comparison(metrics: dict, save_path: str):
    """Bar chart comparing predicted vs GT phase fractions."""
    classes    = CLASS_NAMES
    pred_fracs = [metrics["pred_phase_fractions"][c] * 100 for c in classes]
    gt_fracs   = [metrics["gt_phase_fractions"][c]   * 100 for c in classes]

    x = np.arange(len(classes))
    w = 0.35

    fig, ax = plt.subplots(figsize=(7, 5))
    bars_gt   = ax.bar(x - w/2, gt_fracs,   w, label="EBSD (Ground Truth)",
                       color=["#C0392B", "#27AE60"])
    bars_pred = ax.bar(x + w/2, pred_fracs, w, label="U-Net Prediction",
                       color=["#E74C3C", "#2ECC71"], alpha=0.8)

    ax.set_xlabel("Phase", fontsize=12)
    ax.set_ylabel("Phase Fraction (%)", fontsize=12)
    ax.set_title("Predicted vs EBSD Phase Fractions — Test Set", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(classes, fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # Annotate bars with values
    for bar in bars_gt:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)
    for bar in bars_pred:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=120, bbox_inches="tight")
    print(f"  Phase fraction chart saved → {save_path}")
    # plt.close()


def main():
    print("=" * 65)
    print("  Evaluation — Test Set")
    print("=" * 65)

    device = get_device()

    # ── Load model ────────────────────────────────────────────────────────────
    model = build_model().to(device)
    load_checkpoint(model, optimizer=None, save_dir=CKPT_DIR,
                    filename="best_model.pth", device=str(device))

    # ── Load test data ────────────────────────────────────────────────────────
    _, _, test_loader = get_dataloaders(PATCH_DIR, batch_size=BATCH_SIZE,
                                        num_workers=NUM_WORKERS)

    # ── Inference (TTA enabled for optimal boundary precision) ────────────────
    all_preds, all_labels, all_iq = run_inference_on_loader(model, test_loader, device, use_tta=True)

    # ── Metrics ───────────────────────────────────────────────────────────────
    print("\n── Test Set Metrics (with Test-Time Augmentation) ──")
    metrics = compute_metrics(all_preds.ravel(), all_labels.ravel())
    print_metrics(metrics, prefix="  ")

    # ── Confusion matrix ──────────────────────────────────────────────────────
    cm_path = os.path.join(OUTPUT_DIR, "confusion_matrix.png")
    plot_confusion_matrix(all_preds, all_labels, cm_path)

    # ── Phase fraction comparison ─────────────────────────────────────────────
    pf_path = os.path.join(OUTPUT_DIR, "phase_fractions.png")
    plot_phase_fraction_comparison(metrics, pf_path)

    # ── Qualitative results ───────────────────────────────────────────────────
    qual_path = os.path.join(OUTPUT_DIR, "qualitative_results.png")
    plot_predictions(
        iq_patches   = all_iq[:8],
        gt_labels    = all_labels[:8],
        pred_labels  = all_preds[:8],
        n            = 8,
        save_path    = qual_path,
    )

    # ── Summary report ────────────────────────────────────────────────────────
    report_path = os.path.join(OUTPUT_DIR, "test_report.txt")
    with open(report_path, "w") as f:
        f.write("=" * 50 + "\n")
        f.write("  Test Evaluation Report\n")
        f.write("  Medium Mn Steel — EfficientNet-B0 UNet\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Pixel Accuracy : {metrics['pixel_accuracy']:.4f}\n")
        f.write(f"Mean IoU       : {metrics['mean_iou']:.4f}\n\n")
        for cls in CLASS_NAMES:
            f.write(f"[{cls}]\n")
            f.write(f"  IoU  : {metrics['per_class_iou'][cls]:.4f}\n")
            f.write(f"  F1   : {metrics['per_class_f1'][cls]:.4f}\n")
            f.write(f"  GT   : {metrics['gt_phase_fractions'][cls]*100:.2f}%\n")
            f.write(f"  Pred : {metrics['pred_phase_fractions'][cls]*100:.2f}%\n\n")

    print(f"\n  Report saved → {report_path}")
    print("[OK] Evaluation complete.")


if __name__ == "__main__":
    main()
