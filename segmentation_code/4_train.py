"""
4_train.py
-----------
Train the EfficientNet-B0 UNet on the extracted EBSD patches.

Hyperparameters:
    - Optimizer    : AdamW
    - Loss         : 0.5 × CrossEntropyLoss + 0.5 × DiceLoss
    - LR (encoder) : 1e-5  (fine-tune pre-trained weights gently)
    - LR (decoder) : 1e-4  (train from scratch)
    - Scheduler    : ReduceLROnPlateau (patience=5, factor=0.5)
    - Epochs       : 50
    - Batch size   : 16
    - ignore_index : 255 (unindexed pixels masked from loss)

Best model saved to: checkpoints/best_model.pth
Training curves  to: outputs/training/training_curves.png
"""

import os
import time
from datetime import datetime, timedelta
import numpy as np
import torch
from tqdm import tqdm

from dataset     import get_dataloaders
from unet_model  import build_model, get_param_groups
from utils       import (CombinedLoss, compute_class_weights, compute_metrics,
                         print_metrics, save_checkpoint, load_checkpoint, plot_training_curves)

# ── Configuration ──────────────────────────────────────────────────────────────
PATCH_DIR   = os.path.join(os.path.dirname(__file__), "patches")
LABEL_DIR   = os.path.join(os.path.dirname(__file__), "preprocessed", "labels")
CKPT_DIR    = os.path.join(os.path.dirname(__file__), "checkpoints")
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "outputs", "training")
os.makedirs(CKPT_DIR,   exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Hyperparameters
EPOCHS       = 35
BATCH_SIZE   = 16  # optimal for CPU & GPU
ENCODER_LR   = 1e-5
DECODER_LR   = 1e-4
WEIGHT_DECAY = 1e-4
LR_PATIENCE  = 4       # epochs before LR reduction
LR_FACTOR    = 0.5
IGNORE_INDEX = 255
NUM_WORKERS  = 0       # 0 = safe on Windows; increase if on Linux


def get_device() -> torch.device:
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        print(f"[OK] Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        dev = torch.device("cpu")
        print("[!]  CUDA not available — training on CPU (will be slow)")
    return dev


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0

    for iq_batch, label_batch in tqdm(loader, desc="  Train", leave=False):
        iq_batch    = iq_batch.to(device)        # (B, 1, 128, 128)
        label_batch = label_batch.to(device)     # (B, 128, 128)

        optimizer.zero_grad()
        logits = model(iq_batch)                 # (B, 2, 128, 128)
        loss   = criterion(logits, label_batch)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * iq_batch.size(0)

    return total_loss / len(loader.dataset)


@torch.no_grad()
def validate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds  = []
    all_labels = []

    for iq_batch, label_batch in tqdm(loader, desc="  Val  ", leave=False):
        iq_batch    = iq_batch.to(device)
        label_batch = label_batch.to(device)

        logits = model(iq_batch)
        loss   = criterion(logits, label_batch)
        total_loss += loss.item() * iq_batch.size(0)

        preds = logits.argmax(dim=1)             # (B, 128, 128)
        all_preds.append(preds.cpu().numpy())
        all_labels.append(label_batch.cpu().numpy())

    all_preds  = np.concatenate(all_preds,  axis=0)  # (N, 128, 128)
    all_labels = np.concatenate(all_labels, axis=0)

    avg_loss = total_loss / len(loader.dataset)
    metrics  = compute_metrics(all_preds.ravel(), all_labels.ravel())

    return avg_loss, metrics


def main():
    print("=" * 65)
    print("  EfficientNet-B0 UNet Training — Medium Mn Steel Segmentation")
    print("=" * 65)

    device = get_device()

    # ── Data ──────────────────────────────────────────────────────────────────
    train_loader, val_loader, _ = get_dataloaders(
        PATCH_DIR, batch_size=BATCH_SIZE, num_workers=NUM_WORKERS
    )

    # ── Class weights (handle ferrite/austenite imbalance) ────────────────────
    # Minority boosting: 1.0 for Ferrite, 3.5 for Austenite
    class_weights = torch.tensor([1.0, 3.5], dtype=torch.float32).to(device)
    print(f"  Class weights (Ferrite, Austenite): [{class_weights[0]:.2f}, {class_weights[1]:.2f}]")

    # ── Model ─────────────────────────────────────────────────────────────────
    model = build_model().to(device)
    print(f"\nModel: EfficientNet-B0 UNet")
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total params    : {total:,}")
    print(f"  Trainable params: {trainable:,}")

    # ── Loss ──────────────────────────────────────────────────────────────────
    # dice_weight=0.65 directly maximizes region overlap for the minority class
    criterion = CombinedLoss(
        class_weights=class_weights,
        ignore_index=IGNORE_INDEX,
        ce_weight=0.35,
        dice_weight=0.65,
    )

    # ── Optimizer (differential LR) ───────────────────────────────────────────
    param_groups = get_param_groups(model, encoder_lr=ENCODER_LR, decoder_lr=DECODER_LR)
    optimizer    = torch.optim.AdamW(param_groups, weight_decay=WEIGHT_DECAY)

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", patience=LR_PATIENCE, factor=LR_FACTOR
    )

    # ── Training loop ─────────────────────────────────────────────────────────
    train_losses, val_losses, val_ious = [], [], []
    best_val_iou = 0.0
    start_epoch  = 1

    # Resume from latest checkpoint if available
    latest_ckpt_path = os.path.join(CKPT_DIR, "latest_model.pth")
    if os.path.exists(latest_ckpt_path):
        res_epoch, res_iou = load_checkpoint(model, optimizer, CKPT_DIR, "latest_model.pth", device=str(device))
        start_epoch  = res_epoch + 1
        best_val_iou = res_iou
        # Also check best_model.pth for highest recorded iou
        best_ckpt_path = os.path.join(CKPT_DIR, "best_model.pth")
        if os.path.exists(best_ckpt_path):
            best_ckpt = torch.load(best_ckpt_path, map_location=str(device))
            best_val_iou = max(best_val_iou, best_ckpt.get("val_iou", 0.0))
        print(f"  [Resume] Continuing training from Epoch {start_epoch} to {EPOCHS} (Current best Val IoU: {best_val_iou:.4f})\n")

    print(f"\nStarting training for {EPOCHS} epochs (from epoch {start_epoch})...")
    print(f"  Batch size : {BATCH_SIZE}")
    print(f"  Encoder LR : {ENCODER_LR}")
    print(f"  Decoder LR : {DECODER_LR}")
    print()

    training_start = time.time()
    epoch_times    = []

    for epoch in range(start_epoch, EPOCHS + 1):
        t0 = time.time()

        train_loss            = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_metrics = validate(model, val_loader, criterion, device)

        val_iou = val_metrics["mean_iou"]
        scheduler.step(val_iou)

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        val_ious.append(val_iou)

        elapsed = time.time() - t0
        epoch_times.append(elapsed)

        # ── ETA calculation ───────────────────────────────────────────────────
        epochs_left      = EPOCHS - epoch
        avg_epoch_time   = sum(epoch_times) / len(epoch_times)
        eta_seconds      = epochs_left * avg_epoch_time
        eta_datetime     = datetime.now() + timedelta(seconds=eta_seconds)
        total_elapsed    = time.time() - training_start
        eta_str          = eta_datetime.strftime("%H:%M:%S on %d %b") if epochs_left > 0 else "Done!"

        print(f"Epoch [{epoch:3d}/{EPOCHS}] | "
              f"Train Loss: {train_loss:.4f} | "
              f"Val Loss: {val_loss:.4f} | "
              f"Val IoU: {val_iou:.4f} (Aus: {val_metrics['per_class_iou']['Austenite']:.4f}) | "
              f"Epoch: {elapsed:.0f}s | "
              f"Elapsed: {timedelta(seconds=int(total_elapsed))} | "
              f"ETA: {eta_str}")

        # Print full metrics every 10 epochs
        if epoch % 10 == 0:
            print_metrics(val_metrics, prefix="  ")

        # Save best checkpoint
        if val_iou > best_val_iou:
            best_val_iou = val_iou
            save_checkpoint(model, optimizer, epoch, val_iou, CKPT_DIR, "best_model.pth")

        # Save latest checkpoint (resume support)
        save_checkpoint(model, optimizer, epoch, val_iou, CKPT_DIR, "latest_model.pth")

    # ── Final plots ───────────────────────────────────────────────────────────
    curves_path = os.path.join(OUTPUT_DIR, "training_curves.png")
    plot_training_curves(train_losses, val_losses, val_ious, save_path=curves_path)

    print("\n" + "=" * 65)
    print(f"  Training complete! Best Val IoU: {best_val_iou:.4f}")
    print(f"  Best model → {os.path.join(CKPT_DIR, 'best_model.pth')}")
    print("=" * 65)


if __name__ == "__main__":
    main()
