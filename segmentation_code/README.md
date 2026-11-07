# BTP: EfficientNet-UNet Microstructure Segmentation
### Medium Manganese Steel — Ferrite / Austenite Phase Segmentation

Implements the paper:
> *"A generic high-throughput microstructure segmentation and quantification method for complex steels using a machine learning model trained by electron backscatter diffraction"*

---

## Dataset
- **Input**:  IQ (Image Quality) grayscale maps — 7 × 1024×1024 images
- **Labels**: EBSD Phase maps (Red=Ferrite, Green=Austenite) — 7 × 1024×1024 images
- **IQ 7 / Phase 7**: Excluded (inconsistent orange/blue colormap)

## Model
- **Architecture**: U-Net with EfficientNet-B0 encoder (`segmentation-models-pytorch`)
- **Pre-training**: ImageNet weights on encoder
- **Input**: 128×128 grayscale IQ patches
- **Output**: 2-class pixel mask (Ferrite / Austenite)

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Run in Order

```bash
# Step 0: Inspect images, print Phase colors
python 0_inspect_images.py

# Step 1: Preprocess (IQ → grayscale, Phase → RGB .npy)
python 1_preprocess.py

# Step 2: Generate label masks (Phase RGB → class integers)
python 2_label_generation.py

# Step 3: Extract 128×128 patches at matched coordinates + augmentation
python 3_patch_extraction.py

# Step 4: Train EfficientNet-UNet (~50 epochs)
python 4_train.py

# Step 5: Evaluate on test set (IoU, F1, phase fractions)
python 5_evaluate.py

# Step 6: Full-image inference on any new IQ image
python 6_inference.py --iq "../IQ and EBSD Phase maps/IQ.tif"
python 6_inference.py --iq "../IQ and EBSD Phase maps/IQ.tif" --overlap

# Step 7: OpenCV Watershed grain size quantification & ASTM E112 stereology
python 7_grain_size.py
python 7_grain_size.py --mask outputs/inference/IQ_mask.npy --scale 1.0 --phase both
```

---

## Output Directory Structure

```
segmentation_code/
├── preprocessed/
│   ├── iq/         img0-6.npy  (float32 grayscale)
│   ├── phase/      img0-6.npy  (RGB uint8)
│   └── labels/     img0-6.npy  (uint8: 0=Ferrite, 1=Austenite, 255=ignore)
├── patches/
│   ├── train/
│   │   ├── iq/     img{i}_r{r}_c{c}_{aug}.npy
│   │   └── phase/  img{i}_r{r}_c{c}_{aug}.npy  ← matching filenames!
│   ├── val/
│   └── test/
├── checkpoints/
│   ├── best_model.pth
│   └── latest_model.pth
└── outputs/
    ├── inspection/       inspection_grid.png
    ├── preprocessing/    preprocessed_pairs.png
    ├── labels/           label_masks.png
    ├── patches/          verify_train.png, verify_val.png, verify_test.png
    ├── training/         training_curves.png
    ├── evaluation/       confusion_matrix.png, phase_fractions.png, ...
    ├── inference/        *_segmentation.png, *_overlay.png, *_report.txt
    └── grain_size/       ferrite_grains.png, austenite_grains.png,
                          grain_size_summary.png, grain_size_cdf.png,
                          shape_descriptors_scatter.png, grain_boundaries_overlay.png,
                          *.csv, grain_size_report.txt, grain_size_summary.json
```

---

## Key Design Decisions

| Decision | Detail |
|---|---|
| Patch coordination | IQ and Phase patches always extracted at **identical (row, col)** coordinates |
| Augmentation | Applied to IQ and Phase **simultaneously** via `albumentations.Compose` |
| Encoder | EfficientNet-B0 (ImageNet pre-trained) — 10× lower LR than decoder |
| Loss | 0.5 × CrossEntropy + 0.5 × Dice — handles class imbalance |
| Unindexed pixels | `ignore_index=255` — masked from loss and metrics |
| Split | Image-level (not patch-level) — prevents data leakage |
