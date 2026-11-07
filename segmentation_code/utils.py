"""
utils.py
---------
Shared helper functions:
  - Combined CE + Dice loss
  - Pixel Accuracy, Mean IoU, F1/Dice per class
  - Visualization helpers
  - Checkpoint save/load
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ── Constants ─────────────────────────────────────────────────────────────────
NUM_CLASSES  = 2
IGNORE_INDEX = 255
CLASS_NAMES  = ["Ferrite", "Austenite"]

# Colors for visualization
CLASS_DISPLAY_COLORS = {
    0:   np.array([220, 50,  50],  dtype=np.uint8),   # red   → Ferrite
    1:   np.array([50,  200, 50],  dtype=np.uint8),   # green → Austenite
    255: np.array([25,  25,  25],  dtype=np.uint8),   # dark  → Unindexed
}


# ─────────────────────────────────────────────────────────────────────────────
#  Loss
# ─────────────────────────────────────────────────────────────────────────────

class DiceLoss(nn.Module):
    """
    Soft Dice Loss for multi-class segmentation.
    Ignores pixels with label == ignore_index.
    """
    def __init__(self, num_classes: int = NUM_CLASSES, ignore_index: int = IGNORE_INDEX,
                 smooth: float = 1e-6):
        super().__init__()
        self.num_classes   = num_classes
        self.ignore_index  = ignore_index
        self.smooth        = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        logits : (B, C, H, W)
        targets: (B, H, W)  long, may contain ignore_index
        """
        probs = F.softmax(logits, dim=1)  # (B, C, H, W)

        # Build valid mask (ignore unindexed pixels)
        valid = (targets != self.ignore_index)  # (B, H, W) bool

        dice_total = 0.0
        for c in range(self.num_classes):
            prob_c   = probs[:, c, :, :]               # (B, H, W)
            target_c = (targets == c).float()          # (B, H, W)

            # Apply valid mask
            prob_c   = prob_c   * valid.float()
            target_c = target_c * valid.float()

            intersection = (prob_c * target_c).sum()
            union        = prob_c.sum() + target_c.sum()
            dice_total  += (2.0 * intersection + self.smooth) / (union + self.smooth)

        return 1.0 - dice_total / self.num_classes


class CombinedLoss(nn.Module):
    """
    0.5 × CrossEntropyLoss + 0.5 × DiceLoss
    Both ignore pixels with label == ignore_index.
    """
    def __init__(self, class_weights: torch.Tensor = None,
                 num_classes: int = NUM_CLASSES,
                 ignore_index: int = IGNORE_INDEX,
                 ce_weight: float = 0.5,
                 dice_weight: float = 0.5):
        super().__init__()
        self.ce   = nn.CrossEntropyLoss(weight=class_weights, ignore_index=ignore_index)
        self.dice = DiceLoss(num_classes=num_classes, ignore_index=ignore_index)
        self.ce_w   = ce_weight
        self.dice_w = dice_weight

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        return self.ce_w * self.ce(logits, targets) + \
               self.dice_w * self.dice(logits, targets)


def compute_class_weights(label_dir: str, num_classes: int = NUM_CLASSES,
                          ignore_index: int = IGNORE_INDEX) -> torch.Tensor:
    """
    Compute per-class pixel frequency weights from all training label masks.
    Returns a (num_classes,) float tensor to pass to CrossEntropyLoss.
    """
    counts = np.zeros(num_classes, dtype=np.float64)
    for fname in os.listdir(label_dir):
        if not fname.endswith(".npy"):
            continue
        label = np.load(os.path.join(label_dir, fname))
        for c in range(num_classes):
            counts[c] += np.sum(label == c)

    total = counts.sum()
    weights = total / (num_classes * counts + 1e-8)
    weights = weights / weights.sum() * num_classes  # normalize
    print(f"Class weights: Ferrite={weights[0]:.3f}, Austenite={weights[1]:.3f}")
    return torch.tensor(weights, dtype=torch.float32)


# ─────────────────────────────────────────────────────────────────────────────
#  Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(preds: np.ndarray, targets: np.ndarray,
                    num_classes: int = NUM_CLASSES,
                    ignore_index: int = IGNORE_INDEX) -> dict:
    """
    Compute segmentation metrics.
    Args:
        preds:   (H, W) int predicted class map
        targets: (H, W) int ground truth (may contain ignore_index)
    Returns dict with:
        pixel_accuracy, mean_iou, per_class_iou, per_class_f1, phase_fractions
    """
    valid_mask = (targets != ignore_index)
    preds_v    = preds[valid_mask]
    targets_v  = targets[valid_mask]

    # Pixel accuracy
    pixel_acc = float(np.mean(preds_v == targets_v))

    iou_list = []
    f1_list  = []

    for c in range(num_classes):
        tp = np.sum((preds_v == c) & (targets_v == c))
        fp = np.sum((preds_v == c) & (targets_v != c))
        fn = np.sum((preds_v != c) & (targets_v == c))

        iou = tp / (tp + fp + fn + 1e-8)
        f1  = 2*tp / (2*tp + fp + fn + 1e-8)

        iou_list.append(float(iou))
        f1_list.append(float(f1))

    # Phase fractions (predicted)
    total_valid = valid_mask.sum()
    pred_fractions = {CLASS_NAMES[c]: float(np.sum(preds[valid_mask] == c) / total_valid)
                      for c in range(num_classes)}
    gt_fractions   = {CLASS_NAMES[c]: float(np.sum(targets_v == c) / len(targets_v))
                      for c in range(num_classes)}

    return {
        "pixel_accuracy": pixel_acc,
        "mean_iou":       float(np.mean(iou_list)),
        "per_class_iou":  dict(zip(CLASS_NAMES, iou_list)),
        "per_class_f1":   dict(zip(CLASS_NAMES, f1_list)),
        "pred_phase_fractions": pred_fractions,
        "gt_phase_fractions":   gt_fractions,
    }


def print_metrics(metrics: dict, prefix: str = ""):
    print(f"{prefix}Pixel Acc : {metrics['pixel_accuracy']:.4f}")
    print(f"{prefix}Mean IoU  : {metrics['mean_iou']:.4f}")
    for cls, iou in metrics["per_class_iou"].items():
        f1 = metrics["per_class_f1"][cls]
        print(f"{prefix}  [{cls}]  IoU={iou:.4f}  F1={f1:.4f}")
    print(f"{prefix}Phase Fractions (Predicted vs GT):")
    for cls in CLASS_NAMES:
        pred_f = metrics["pred_phase_fractions"][cls]
        gt_f   = metrics["gt_phase_fractions"][cls]
        print(f"{prefix}  [{cls}]  Pred={pred_f:.3f}  GT={gt_f:.3f}  "
              f"Δ={abs(pred_f-gt_f):.3f}")


# ─────────────────────────────────────────────────────────────────────────────
#  Visualization
# ─────────────────────────────────────────────────────────────────────────────

def label_to_rgb(label: np.ndarray) -> np.ndarray:
    """Convert (H, W) label mask → (H, W, 3) RGB display image."""
    rgb = np.zeros((*label.shape, 3), dtype=np.uint8)
    for cls_id, color in CLASS_DISPLAY_COLORS.items():
        rgb[label == cls_id] = color
    return rgb


def plot_predictions(iq_patches, gt_labels, pred_labels, n: int = 4,
                     save_path: str = None):
    """
    Plot a row of [IQ | Ground Truth | Prediction | Overlay] for n samples.
    """
    fig, axes = plt.subplots(n, 4, figsize=(14, 3.5 * n))
    if n == 1:
        axes = axes[np.newaxis, :]

    for i in range(min(n, len(iq_patches))):
        iq   = iq_patches[i]
        gt   = gt_labels[i]
        pred = pred_labels[i]

        gt_rgb   = label_to_rgb(gt)
        pred_rgb = label_to_rgb(pred)

        axes[i, 0].imshow(iq, cmap="gray")
        axes[i, 0].set_title("IQ (input)", fontsize=8)
        axes[i, 0].axis("off")

        axes[i, 1].imshow(gt_rgb)
        axes[i, 1].set_title("Ground Truth", fontsize=8)
        axes[i, 1].axis("off")

        axes[i, 2].imshow(pred_rgb)
        axes[i, 2].set_title("Prediction", fontsize=8)
        axes[i, 2].axis("off")

        axes[i, 3].imshow(iq, cmap="gray")
        axes[i, 3].imshow(pred_rgb, alpha=0.45)
        axes[i, 3].set_title("Overlay", fontsize=8)
        axes[i, 3].axis("off")

    legend_patches = [
        mpatches.Patch(color=[220/255, 50/255, 50/255], label="Ferrite"),
        mpatches.Patch(color=[50/255, 200/255, 50/255], label="Austenite"),
        mpatches.Patch(color=[25/255,  25/255,  25/255], label="Unindexed"),
    ]
    fig.legend(handles=legend_patches, loc="upper right", fontsize=9)
    plt.suptitle("Segmentation Results", fontsize=13, fontweight="bold")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        print(f"Saved → {save_path}")
    plt.close()


# ─────────────────────────────────────────────────────────────────────────────
#  Checkpointing
# ─────────────────────────────────────────────────────────────────────────────

def save_checkpoint(model, optimizer, epoch: int, val_iou: float,
                    save_dir: str, filename: str = "best_model.pth"):
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, filename)
    torch.save({
        "epoch":     epoch,
        "val_iou":   val_iou,
        "model":     model.state_dict(),
        "optimizer": optimizer.state_dict(),
    }, path)
    print(f"  [OK] Checkpoint saved → {path}  (epoch={epoch}, val_iou={val_iou:.4f})")


def load_checkpoint(model, optimizer, save_dir: str,
                    filename: str = "best_model.pth", device: str = "cpu"):
    path = os.path.join(save_dir, filename)
    ckpt = torch.load(path, map_location=device)
    model.load_state_dict(ckpt["model"])
    if optimizer is not None:
        optimizer.load_state_dict(ckpt["optimizer"])
    print(f"  [OK] Loaded checkpoint from {path}  "
          f"(epoch={ckpt['epoch']}, val_iou={ckpt['val_iou']:.4f})")
    return ckpt["epoch"], ckpt["val_iou"]


def plot_training_curves(train_losses, val_losses, val_ious, save_path: str = None):
    epochs = range(1, len(train_losses) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(epochs, train_losses, label="Train Loss", color="#E74C3C")
    ax1.plot(epochs, val_losses,   label="Val Loss",   color="#3498DB")
    ax1.set_xlabel("Epoch"); ax1.set_ylabel("Loss")
    ax1.set_title("Training & Validation Loss")
    ax1.legend(); ax1.grid(alpha=0.3)

    ax2.plot(epochs, val_ious, label="Val Mean IoU", color="#2ECC71")
    ax2.set_xlabel("Epoch"); ax2.set_ylabel("Mean IoU")
    ax2.set_title("Validation Mean IoU")
    ax2.legend(); ax2.grid(alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        print(f"Training curves saved → {save_path}")
    plt.close()
