"""
unet_model.py
--------------
EfficientNet-B0 encoder + U-Net decoder via segmentation-models-pytorch.

Usage:
    from unet_model import build_model
    model = build_model()
"""

import torch
import segmentation_models_pytorch as smp


NUM_CLASSES = 2   # Ferrite (0), Austenite (1)
IN_CHANNELS = 1   # Grayscale IQ input


def build_model(
    encoder_name: str   = "efficientnet-b0",
    encoder_weights: str = "imagenet",
    num_classes: int    = NUM_CLASSES,
    in_channels: int    = IN_CHANNELS,
) -> torch.nn.Module:
    """
    Build EfficientNet-B0 UNet segmentation model.

    EfficientNet-B0 is pre-trained on ImageNet (RGB 3-channel).
    For grayscale input (in_channels=1), smp handles the channel adaptation
    automatically (replicates the single channel 3× internally for the
    first conv layer, then uses pre-trained weights).

    Args:
        encoder_name:    EfficientNet variant (b0 optimal for 128px patches)
        encoder_weights: "imagenet" for transfer learning, None for random init
        num_classes:     number of output segmentation classes
        in_channels:     1 for grayscale IQ images

    Returns:
        smp.Unet model (PyTorch nn.Module)
    """
    model = smp.Unet(
        encoder_name    = encoder_name,
        encoder_weights = encoder_weights,
        in_channels     = in_channels,
        classes         = num_classes,
        activation      = None,            # raw logits; loss fn applies softmax
        decoder_use_batchnorm = True,
    )
    return model


def get_param_groups(model, encoder_lr: float = 1e-5, decoder_lr: float = 1e-4):
    """
    Return parameter groups with different learning rates:
        encoder: lower LR (fine-tune pre-trained weights gently)
        decoder: higher LR (train from scratch)

    Usage:
        optimizer = torch.optim.AdamW(get_param_groups(model), weight_decay=1e-4)
    """
    encoder_params = list(model.encoder.parameters())
    decoder_params = [p for p in model.parameters()
                      if not any(p is ep for ep in encoder_params)]

    return [
        {"params": encoder_params, "lr": encoder_lr},
        {"params": decoder_params, "lr": decoder_lr},
    ]


def count_parameters(model) -> int:
    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total params    : {total:,}")
    print(f"Trainable params: {trainable:,}")
    return trainable


if __name__ == "__main__":
    model = build_model()
    count_parameters(model)

    # Sanity check: forward pass
    dummy = torch.randn(2, 1, 128, 128)   # batch=2, C=1, H=128, W=128
    with torch.no_grad():
        out = model(dummy)
    print(f"Input  shape: {dummy.shape}")
    print(f"Output shape: {out.shape}")   # should be (2, 2, 128, 128)
    assert out.shape == (2, NUM_CLASSES, 128, 128), "Output shape mismatch!"
    print("[OK] Model forward pass OK")
