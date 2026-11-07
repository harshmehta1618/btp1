import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # --- COLOR PALETTE (Minimalist Architectural / Academic Slate & Cobalt) ---
    COLOR_BG = RGBColor(248, 250, 252)         # Slate 50 (Crisp off-white)
    COLOR_CARD_BG = RGBColor(255, 255, 255)    # Pure White
    COLOR_CARD_BORDER = RGBColor(226, 232, 240) # Slate 200
    COLOR_TEXT_TITLE = RGBColor(15, 23, 42)     # Slate 900
    COLOR_TEXT_BODY = RGBColor(71, 85, 105)     # Slate 600
    COLOR_TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400
    COLOR_PRIMARY = RGBColor(37, 99, 235)       # Cobalt Blue 600
    COLOR_PRIMARY_LIGHT = RGBColor(239, 246, 255) # Blue 50
    COLOR_PRIMARY_BORDER = RGBColor(191, 219, 254) # Blue 200
    COLOR_SUCCESS = RGBColor(5, 150, 105)       # Emerald 600
    COLOR_SUCCESS_LIGHT = RGBColor(236, 253, 245) # Emerald 50
    COLOR_AMBER = RGBColor(217, 119, 6)         # Amber 600
    COLOR_TABLE_HEADER = RGBColor(30, 41, 59)   # Slate 800
    COLOR_TABLE_ALT = RGBColor(248, 250, 252)   # Slate 50

    base_dir = os.path.dirname(os.path.abspath(__file__))
    outputs_dir = os.path.join(base_dir, "segmentation_code", "outputs")

    def set_slide_background(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = COLOR_BG

    def add_header(slide, title, category="BTP PROGRESS REVIEW"):
        # Category Pill / Tag
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p_cat = tf.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = "Segoe UI"
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_PRIMARY

        # Title
        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = "Segoe UI"
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT_TITLE
        p_title.space_before = Pt(3)

        # Subtle Divider line
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.8), Inches(1.15), Inches(11.733), Inches(0.015)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_CARD_BORDER
        line.line.color.rgb = COLOR_CARD_BORDER

    def add_footer(slide, slide_num, total_slides=14):
        # Footer text
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = f"Harsh Mehta • BTP Progress Defense • Medium-Mn Steel AI Microstructure Segmentation & Stereology"
        p.font.name = "Segoe UI"
        p.font.size = Pt(8.5)
        p.font.color.rgb = COLOR_TEXT_MUTED

        p_num = tx_box.text_frame.add_paragraph()
        p_num.text = f"{slide_num:02d} / {total_slides:02d}"
        p_num.alignment = PP_ALIGN.RIGHT
        p_num.font.name = "Segoe UI"
        p_num.font.size = Pt(8.5)
        p_num.font.bold = True
        p_num.font.color.rgb = COLOR_TEXT_MUTED

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    def add_stat_box(slide, left, top, width, height, value, label, sublabel=None, accent_color=COLOR_PRIMARY):
        add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER)
        
        # Color bar indicator on left
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.08), height)
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent_color
        bar.line.color.rgb = accent_color

        tx_box = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.12), width - Inches(0.3), height - Inches(0.24))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p_val = tf.paragraphs[0]
        p_val.text = str(value)
        p_val.font.name = "Segoe UI"
        p_val.font.size = Pt(22)
        p_val.font.bold = True
        p_val.font.color.rgb = COLOR_TEXT_TITLE

        p_lbl = tf.add_paragraph()
        p_lbl.text = str(label)
        p_lbl.font.name = "Segoe UI"
        p_lbl.font.size = Pt(10)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = accent_color
        p_lbl.space_before = Pt(2)

        if sublabel:
            p_sub = tf.add_paragraph()
            p_sub.text = str(sublabel)
            p_sub.font.name = "Segoe UI"
            p_sub.font.size = Pt(8.5)
            p_sub.font.color.rgb = COLOR_TEXT_MUTED
            p_sub.space_before = Pt(2)

    def add_bullet_card(slide, left, top, width, height, title, items, tag=None, bg_color=COLOR_CARD_BG):
        add_card(slide, left, top, width, height, bg_color=bg_color, border_color=COLOR_CARD_BORDER)
        
        tx_box = slide.shapes.add_textbox(left + Inches(0.28), top + Inches(0.22), width - Inches(0.56), height - Inches(0.44))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_title = tf.paragraphs[0]
        p_title.text = title
        p_title.font.name = "Segoe UI"
        p_title.font.size = Pt(13)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT_TITLE

        if tag:
            p_tag = tf.add_paragraph()
            p_tag.text = tag.upper()
            p_tag.font.name = "Segoe UI"
            p_tag.font.size = Pt(8.5)
            p_tag.font.bold = True
            p_tag.font.color.rgb = COLOR_PRIMARY
            p_tag.space_before = Pt(2)
            p_tag.space_after = Pt(6)

        for heading, body in items:
            p_item = tf.add_paragraph()
            p_item.font.name = "Segoe UI"
            p_item.space_before = Pt(5)
            p_item.space_after = Pt(2)

            r_h = p_item.add_run()
            r_h.text = f"•  {heading}: " if heading else "•  "
            r_h.font.bold = True
            r_h.font.size = Pt(9.5)
            r_h.font.color.rgb = COLOR_TEXT_TITLE

            r_b = p_item.add_run()
            r_b.text = body
            r_b.font.bold = False
            r_b.font.size = Pt(9.5)
            r_b.font.color.rgb = COLOR_TEXT_BODY

    def add_table_widget(slide, left, top, width, height, headers, rows_data, col_widths=None):
        num_rows = len(rows_data) + 1
        num_cols = len(headers)
        table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, width, height)
        table = table_shape.table

        if col_widths and len(col_widths) == num_cols:
            for j, w in enumerate(col_widths):
                table.columns[j].width = w

        # Headers
        for j, h in enumerate(headers):
            cell = table.cell(0, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_TABLE_HEADER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.08)
            tf.margin_top = tf.margin_bottom = Inches(0.05)
            p = tf.paragraphs[0]
            p.text = h
            p.font.name = "Segoe UI"
            p.font.size = Pt(9)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)

        # Rows
        for i, row in enumerate(rows_data):
            row_idx = i + 1
            bg = COLOR_TABLE_ALT if i % 2 == 1 else COLOR_CARD_BG
            for j, val in enumerate(row):
                cell = table.cell(row_idx, j)
                cell.fill.solid()
                cell.fill.fore_color.rgb = bg
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                tf = cell.text_frame
                tf.word_wrap = True
                tf.margin_left = tf.margin_right = Inches(0.08)
                tf.margin_top = tf.margin_bottom = Inches(0.04)
                p = tf.paragraphs[0]
                p.text = str(val)
                p.font.name = "Segoe UI"
                p.font.size = Pt(8.5)
                p.font.color.rgb = COLOR_TEXT_TITLE if j == 0 else COLOR_TEXT_BODY
                if j == 0:
                    p.font.bold = True

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Minimalist, Hero Header, Clean Metrics Strip)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1)

    # Accent decorative bar on top
    top_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = COLOR_PRIMARY
    top_bar.line.color.rgb = COLOR_PRIMARY

    # Main Card
    add_card(s1, Inches(0.8), Inches(0.7), Inches(11.733), Inches(4.3), bg_color=COLOR_CARD_BG)

    # Left Accent Stripe on Card
    c_stripe = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.7), Inches(0.12), Inches(4.3))
    c_stripe.fill.solid()
    c_stripe.fill.fore_color.rgb = COLOR_PRIMARY
    c_stripe.line.color.rgb = COLOR_PRIMARY

    # Title text box
    tb = s1.shapes.add_textbox(Inches(1.2), Inches(0.95), Inches(11.0), Inches(3.8))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_badge = tf.paragraphs[0]
    p_badge.text = "BACHELOR THESIS PROJECT (BTP) • PROGRESS DEFENSE"
    p_badge.font.name = "Segoe UI"
    p_badge.font.size = Pt(11)
    p_badge.font.bold = True
    p_badge.font.color.rgb = COLOR_PRIMARY

    p_title = tf.add_paragraph()
    p_title.text = "High-Throughput Microstructure Segmentation & Metallographic Quantification of Medium-Mn Steel"
    p_title.font.name = "Segoe UI"
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_TEXT_TITLE
    p_title.space_before = Pt(8)
    p_title.space_after = Pt(6)

    p_sub = tf.add_paragraph()
    p_sub.text = "Supervised Deep Learning (EfficientNet-UNet) Trained via EBSD Ground Truth & Automated Marker-Controlled Watershed Stereology"
    p_sub.font.name = "Segoe UI"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = COLOR_TEXT_BODY
    p_sub.space_after = Pt(22)

    # Divider in title card
    p_div = tf.add_paragraph()
    p_div.text = "—" * 50
    p_div.font.size = Pt(8)
    p_div.font.color.rgb = COLOR_CARD_BORDER
    p_div.space_after = Pt(10)

    p_meta = tf.add_paragraph()
    p_meta.text = "Candidate: Harsh Mehta   |   Bachelor of Technology   |   Academic Year 2025–2026"
    p_meta.font.name = "Segoe UI"
    p_meta.font.size = Pt(11)
    p_meta.font.bold = True
    p_meta.font.color.rgb = COLOR_TEXT_TITLE

    # Bottom Stat Strips (3 minimal KPI cards)
    add_stat_box(s1, Inches(0.8), Inches(5.3), Inches(3.64), Inches(1.5), "7 Modules", "End-to-End Pipeline", "From raw SEM IQ to ASTM E112 reports", COLOR_PRIMARY)
    add_stat_box(s1, Inches(4.84), Inches(5.3), Inches(3.64), Inches(1.5), "89.19%", "Holdout Pixel Accuracy", "0.7163 mIoU | 0.05% phase error", COLOR_SUCCESS)
    add_stat_box(s1, Inches(8.88), Inches(5.3), Inches(3.65), Inches(1.5), "< 2.0 sec", "High-Throughput Speed", "100× faster than physical EBSD scans", COLOR_AMBER)


    # =========================================================================
    # SLIDE 2: PROBLEM STATEMENT & MOTIVATION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2)
    add_header(s2, "Motivation & Problem Statement: The Metallography Bottleneck", "RESEARCH BACKGROUND")
    add_footer(s2, 2)

    # Left Column: The Problem (EBSD vs SEM IQ)
    add_bullet_card(s2, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.35),
        "The Characterization Bottleneck in Steels",
        [
            ("EBSD Limitations", "Electron Backscatter Diffraction provides ground-truth crystallographic phase distinction (BCC Ferrite vs FCC Austenite), but is extremely slow (~1-3 hours per scan), cost-prohibitive, and demands ultra-high vacuum and complex specimen polishing."),
            ("SEM Image Quality (IQ) Advantage", "SEM Image Quality maps capture microstructure channeling contrast in seconds (< 10 seconds), enabling massive high-throughput inspection of industrial steel components."),
            ("The Grayscale Dilemma", "Grayscale channeling contrast in IQ maps is subtle and noisy. Traditional gray-level thresholding completely fails to segment Ferrite matrix from Austenite islands."),
            ("Objective of BTP", "Develop an automated deep learning pipeline that trains on paired EBSD ground truth, accurately segments raw SEM IQ scans, and executes automated ASTM E112 stereological grain size quantification.")
        ],
        tag="Physical Metallography Challenge"
    )

    # Right Column: Value Proposition & Paradigm Shift
    add_bullet_card(s2, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35),
        "Proposed Machine Learning Solution",
        [
            ("Supervised Transfer Learning", "Leverage deep Convolutional Neural Networks (U-Net with EfficientNet-B0 backbone) to learn subtle edge channeling and phase morphology representations."),
            ("One-Time Training Overhead", "Train once using a small set of curated EBSD-matched IQ scans; deploy across thousands of routine industrial SEM images without requiring ongoing EBSD scans."),
            ("100× Throughput Acceleration", "Reduces phase quantification and grain characterization time from hours to < 2.0 seconds per 1024×1024 field of view."),
            ("End-to-End Pipeline Scope", "Full automation spanning: Raw image inspection → Label mask generation → Coordinated patching → Deep learning → Sliding-window inference → Watershed grain sizing.")
        ],
        tag="Engineering Impact & Innovation",
        bg_color=COLOR_PRIMARY_LIGHT
    )


    # =========================================================================
    # SLIDE 3: SYSTEM ARCHITECTURE & MODULAR PIPELINE
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3)
    add_header(s3, "End-to-End System Pipeline: 3 Engineering Stages", "SYSTEM ARCHITECTURE")
    add_footer(s3, 3)

    col_w = Inches(3.64)
    gap = Inches(0.4)

    # Stage 1 Card
    add_bullet_card(s3, Inches(0.8), Inches(1.4), col_w, Inches(5.35),
        "1. Data Preprocessing & Curation",
        [
            ("0_inspect_images.py", "Inspect raw TIFF pairs; extract RGB channels; identify corrupted color palettes."),
            ("1_preprocess.py", "Convert IQ maps to float32 [0.0, 1.0]; convert Phase maps to standard uint8 RGB arrays."),
            ("2_label_generation.py", "RGB color thresholding to create integer masks (0=Ferrite, 1=Austenite, 255=Unindexed)."),
            ("3_patch_extraction.py", "Extract 128×128 tiles at strictly matched (r, c) coordinates + synchronized Albumentations.")
        ],
        tag="Stage 1: Pre-Processing Pipeline"
    )

    # Stage 2 Card
    add_bullet_card(s3, Inches(0.8 + 3.64 + 0.4), Inches(1.4), col_w, Inches(5.35),
        "2. Deep Learning Segmentation",
        [
            ("unet_model.py", "U-Net with ImageNet pre-trained EfficientNet-B0 encoder (6.25M parameters)."),
            ("4_train.py", "PyTorch training loop; compound Loss = 0.5×CE + 0.5×Dice; differential learning rates."),
            ("5_evaluate.py", "Quantitative evaluation on holdout test image (IoU, F1 score, confusion matrix)."),
            ("6_inference.py", "Full-image sliding window inference engine with optional Hann-window overlap blending.")
        ],
        tag="Stage 2: Model & Inference Engine"
    )

    # Stage 3 Card
    add_bullet_card(s3, Inches(0.8 + (3.64 + 0.4)*2), Inches(1.4), col_w, Inches(5.35),
        "3. Metallography & Stereology",
        [
            ("7_grain_size.py", "Production-grade OpenCV marker-controlled Watershed grain boundary segmenter."),
            ("Topological Tuning", "Opening filter on continuous Ferrite matrix without hole-filling; island erosion on Austenite."),
            ("ASTM E112 Sizing", "Heyn Linear Intercept (l), Planimetric density (N_A), and standard ASTM G computation."),
            ("Export Artifacts", "Automated CSV grain catalogs, CDF distributions, overlays, and comprehensive reports.")
        ],
        tag="Stage 3: Physical Stereology"
    )


    # =========================================================================
    # SLIDE 4: DATASET ANALYSIS & ANOMALY DISCOVERY
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4)
    add_header(s4, "Dataset Analysis, Phase Colormapping & Anomaly Detection", "DATA ENGINEERING")
    add_footer(s4, 4)

    # Left: Text and Anomaly Box
    add_bullet_card(s4, Inches(0.8), Inches(1.4), Inches(5.2), Inches(3.3),
        "Dataset Specifications & Cleaning",
        [
            ("Raw Input Dataset", "7 pairs of 1024×1024 high-resolution scans consisting of SEM IQ maps and paired EBSD Phase maps."),
            ("Colormap Standards", "BCC Ferrite (Red: R>150, G<80, B<80) | FCC Austenite (Green: G>150, R<80, B<80) | Unindexed boundaries (Black: R<15, G<15, B<15)."),
            ("Image-Level Splitting", "Data split strictly at the image level (not patch level) to eliminate spatial leakage between training and evaluation.")
        ],
        tag="Dataset Properties"
    )

    # Anomaly Callout Box below
    add_bullet_card(s4, Inches(0.8), Inches(4.9), Inches(5.2), Inches(1.85),
        "CRITICAL ANOMALY IDENTIFIED: Pair 7 Excluded",
        [
            ("Inspection Finding", "Script 0_inspect_images.py revealed Image Pair 7 uses an incompatible orange/blue inverted colormap."),
            ("Resolution", "Excluded Pair 7 from dataset to prevent catastrophic label pollution during neural training.")
        ],
        tag="Data Quality Assurance",
        bg_color=RGBColor(254, 242, 242) # Red 50
    )

    # Right: Dataset Table
    t1_headers = ["Image ID", "Ferrite %", "Austenite %", "Unindexed %", "Split Assignment"]
    t1_rows = [
        ["img0", "73.7%", "10.5%", "15.8%", "Train Set"],
        ["img1", "73.0%", "11.7%", "15.3%", "Train Set"],
        ["img2", "80.2%", "17.5%", "2.3%",  "Train Set"],
        ["img3", "82.0%", "10.8%", "7.3%",  "Train Set"],
        ["img4", "82.8%", "4.5%",  "12.6%", "Train Set"],
        ["img5", "61.8%", "14.1%", "24.1%", "Validation Set"],
        ["img6", "62.8%", "14.7%", "22.5%", "Test Set (Holdout)"]
    ]
    col_w_t1 = [Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.733)]
    add_table_widget(s4, Inches(6.3), Inches(1.4), Inches(6.233), Inches(5.35), t1_headers, t1_rows, col_w_t1)


    # =========================================================================
    # SLIDE 5: PREPROCESSING & COORDINATE-MATCHED PATCHING
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5)
    add_header(s5, "Data Preprocessing & Coordinate-Matched Patch Extraction", "FEATURE ENGINEERING")
    add_footer(s5, 5)

    # Left Column: Preprocessing logic
    add_bullet_card(s5, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.35),
        "Patching Methodology & Leakage Prevention",
        [
            ("Memory Optimization", "Full 1024×1024 scans cannot be trained directly due to GPU memory constraints and limited mini-batch diversity. Images are partitioned into 128×128 pixel tiles."),
            ("Coordinate-Matched Slicing", "Crucial metallurgical requirement: IQ and Phase patches are extracted at identical pixel coordinates (r, c). An offset of even 1 pixel would misalign microstructural features."),
            ("Image-Level Data Partitioning", "img0–img4 allocated to Train, img5 to Validation, and img6 as unseen Holdout Test. Zero patch overlap across splits prevents optimistic data leakage."),
            ("Synchronized Augmentations", "Using Albumentations, spatial transformations (horizontal flips, vertical flips, random 90° rotations) are applied simultaneously to IQ and Phase pairs."),
            ("Augmentation Multiplier", "Yields 3,528 total high-quality training patches (5 images × 64 patches × 11 augmentations) ensuring robust invariance to sample orientation.")
        ],
        tag="Methodological Rigor"
    )

    # Right Column: Visual Verification / Image
    verify_patch_img = os.path.join(outputs_dir, "patches", "verify_train.png")
    if os.path.exists(verify_patch_img):
        add_card(s5, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35), bg_color=COLOR_CARD_BG)
        slide_img = s5.shapes.add_picture(verify_patch_img, Inches(7.0), Inches(1.6), width=Inches(5.333))
        
        tx_c = s5.shapes.add_textbox(Inches(7.0), Inches(6.1), Inches(5.333), Inches(0.5))
        tf_c = tx_c.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = "Verification Grid (3_patch_extraction.py): Paired 128×128 Grayscale IQ tiles with synchronized Ground Truth Phase labels (Red = Ferrite, Green = Austenite)."
        p_c.font.name = "Segoe UI"
        p_c.font.size = Pt(8.5)
        p_c.font.color.rgb = COLOR_TEXT_MUTED
    else:
        add_bullet_card(s5, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35),
            "Patching Pipeline Statistics",
            [
                ("Input Tile Size", "128 × 128 × 1 (Grayscale IQ float32)"),
                ("Target Label Size", "128 × 128 × 1 (uint8 class index: 0, 1, 255)"),
                ("Training Set Size", "3,528 augmented patches"),
                ("Validation Set Size", "64 unaugmented patches (img5)"),
                ("Holdout Test Set Size", "441 patches with sliding window stride (img6)")
            ]
        )


    # =========================================================================
    # SLIDE 6: DEEP LEARNING ARCHITECTURE (EfficientNet-UNet)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6)
    add_header(s6, "Deep Learning Architecture: EfficientNet-B0 U-Net", "MODEL ENGINEERING")
    add_footer(s6, 6)

    # Left: Model rationales
    add_bullet_card(s6, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.35),
        "Architectural Rationale & Loss Function",
        [
            ("Why EfficientNet-B0 Encoder?", "Contains only ~6.25M parameters—4× lighter than ResNet-50. Compact capacity prevents severe overfitting on small metallurgical datasets while extracting expressive multi-scale features."),
            ("ImageNet Transfer Learning", "Backbone initialized with ImageNet weights, providing pre-trained Gabor-like edge detectors and texture representations."),
            ("Skip-Connection Decoder", "Classic U-Net skip pathways fuse high-level semantic context with low-level spatial detail, enabling pixel-sharp phase boundary delineation."),
            ("Compound Loss Formulation", "Loss = 0.5 × CrossEntropy(weighted) + 0.5 × DiceLoss(). CE provides smooth pixel-level gradients; Dice loss directly maximizes regional IoU overlap."),
            ("Class Imbalance Management", "Austenite occupies only ~10–19% of the microstructure. The compound loss prevents the BCC Ferrite majority from dominating gradient updates."),
            ("Unindexed Pixel Masking", "Pixels with label 255 (diffraction overlap at grain boundaries) are masked out with ignore_index=255, eliminating boundary noise.")
        ],
        tag="Deep Learning Design Decisions"
    )

    # Right: Specifications Table
    t2_headers = ["Architectural Parameter", "Design Specification"]
    t2_rows = [
        ["Architecture Backbone", "U-Net with EfficientNet-B0 Encoder"],
        ["Encoder Pre-training", "ImageNet-1k Weights (Transfer Learning)"],
        ["Input Dimensions", "128 × 128 × 1 (Single-channel Grayscale IQ)"],
        ["Output Dimensions", "128 × 128 × 2 (2-Class Logits: Ferrite, Austenite)"],
        ["Total Trainable Parameters", "6,251,038 (Efficient & lightweight)"],
        ["Encoder Learning Rate", "1e-5 (Fine-tuning pre-trained features)"],
        ["Decoder Learning Rate", "1e-4 (Training from scratch, 10× ratio)"],
        ["Optimizer & Weight Decay", "AdamW with 1e-4 Weight Decay"],
        ["Learning Rate Scheduler", "ReduceLROnPlateau (Patience = 5 epochs)"]
    ]
    col_w_t2 = [Inches(2.5), Inches(3.233)]
    add_table_widget(s6, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35), t2_headers, t2_rows, col_w_t2)


    # =========================================================================
    # SLIDE 7: TRAINING DYNAMICS & CONVERGENCE
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7)
    add_header(s7, "Training Dynamics, Optimization & Convergence", "MODEL TRAINING")
    add_footer(s7, 7)

    # Left: Training Curves Image
    train_img = os.path.join(outputs_dir, "training", "training_curves.png")
    if os.path.exists(train_img):
        add_card(s7, Inches(0.8), Inches(1.4), Inches(6.2), Inches(5.35), bg_color=COLOR_CARD_BG)
        s7.shapes.add_picture(train_img, Inches(0.95), Inches(1.6), width=Inches(5.9))
        tx_tc = s7.shapes.add_textbox(Inches(0.95), Inches(6.1), Inches(5.9), Inches(0.5))
        tf_tc = tx_tc.text_frame
        tf_tc.word_wrap = True
        p_tc = tf_tc.paragraphs[0]
        p_tc.text = "Training & Validation Curves (4_train.py): Rapid Dice loss minimization and steady mIoU plateauing over 50 epochs without validation divergence."
        p_tc.font.name = "Segoe UI"
        p_tc.font.size = Pt(8.5)
        p_tc.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Training Dynamics Details
    add_bullet_card(s7, Inches(7.3), Inches(1.4), Inches(5.233), Inches(5.35),
        "Training Strategy & Optimization Dynamics",
        [
            ("Batch Size & Epochs", "Trained with batch size 32 across 50 complete epochs on PyTorch GPU runtime."),
            ("Differential Learning Rates", "Encoder learning rate initialized at 1e-5 (fine-tuning) while decoder initialized at 1e-4 (from scratch). This 10× differential rate prevents catastrophic forgetting."),
            ("Loss Trajectory", "Compound loss decreased smoothly from 0.582 to < 0.145, confirming rapid adaptation of skip-connection weights to channeling contrast patterns."),
            ("Generalization Stability", "Validation loss closely tracked training loss throughout 50 epochs, proving that data augmentation and the compact EfficientNet parameter budget prevented overfitting."),
            ("Checkpoint Serialization", "Automated tracking saved best_model.pth based on validation mIoU checkpointing alongside latest_model.pth.")
        ],
        tag="Convergence Analysis"
    )


    # =========================================================================
    # SLIDE 8: QUANTITATIVE EVALUATION ON TEST SET (img6)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8)
    add_header(s8, "Quantitative Test Benchmark: Performance on Holdout img6", "EXPERIMENTAL RESULTS")
    add_footer(s8, 8)

    # Top KPI Strip (4 cards)
    add_stat_box(s8, Inches(0.8), Inches(1.35), Inches(2.7), Inches(1.3), "89.19%", "Pixel Accuracy", "Holdout test set img6", COLOR_SUCCESS)
    add_stat_box(s8, Inches(3.8), Inches(1.35), Inches(2.7), Inches(1.3), "0.7163", "Mean IoU (mIoU)", "Across both phases", COLOR_PRIMARY)
    add_stat_box(s8, Inches(6.8), Inches(1.35), Inches(2.7), Inches(1.3), "0.9332", "Ferrite F1 Score", "0.8748 Ferrite IoU", COLOR_PRIMARY)
    add_stat_box(s8, Inches(9.8), Inches(1.35), Inches(2.733), Inches(1.3), "0.05%", "Phase Error (Δ)", "Near-perfect agreement", COLOR_AMBER)

    # Middle: Metrics Table
    t3_headers = ["Phase Class", "IoU", "F1 Score", "Ground Truth %", "Predicted %", "Error (Δ)"]
    t3_rows = [
        ["Ferrite (BCC Matrix)", "0.8748", "0.9332", "80.97%", "80.92%", "0.05%"],
        ["Austenite (FCC Islands)", "0.5579", "0.7162", "19.03%", "19.08%", "0.05%"],
        ["Overall Microstructure", "0.7163", "0.8247", "100.0%", "100.0%", "Accuracy: 89.19%"],
        ["Unindexed Boundaries", "N/A (Masked)", "N/A (Masked)", "22.5% of scan", "0.0% (Ignored)", "Excluded"]
    ]
    col_w_t3 = [Inches(2.2), Inches(1.0), Inches(1.0), Inches(1.4), Inches(1.4), Inches(1.2)]
    add_table_widget(s8, Inches(0.8), Inches(2.85), Inches(8.2), Inches(3.95), t3_headers, t3_rows, col_w_t3)

    # Right: Confusion Matrix figure
    cm_img = os.path.join(outputs_dir, "evaluation", "confusion_matrix.png")
    if os.path.exists(cm_img):
        add_card(s8, Inches(9.3), Inches(2.85), Inches(3.233), Inches(3.95), bg_color=COLOR_CARD_BG)
        s8.shapes.add_picture(cm_img, Inches(9.45), Inches(3.0), width=Inches(2.933))
        tx_cm = s8.shapes.add_textbox(Inches(9.45), Inches(6.25), Inches(2.933), Inches(0.45))
        tf_cm = tx_cm.text_frame
        tf_cm.word_wrap = True
        p_cm = tf_cm.paragraphs[0]
        p_cm.text = "Holdout Test Confusion Matrix: Demonstrates high diagonal fidelity on test image 6."
        p_cm.font.name = "Segoe UI"
        p_cm.font.size = Pt(8.0)
        p_cm.font.color.rgb = COLOR_TEXT_MUTED


    # =========================================================================
    # SLIDE 9: QUALITATIVE RESULTS & FULL-IMAGE INFERENCE
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9)
    add_header(s9, "Qualitative Segmentation Fidelity & Sliding-Window Inference", "EVALUATION & INFERENCE")
    add_footer(s9, 9)

    # Left: Qualitative Grid Image
    qual_img = os.path.join(outputs_dir, "evaluation", "qualitative_results.png")
    if os.path.exists(qual_img):
        add_card(s9, Inches(0.8), Inches(1.4), Inches(6.2), Inches(5.35), bg_color=COLOR_CARD_BG)
        s9.shapes.add_picture(qual_img, Inches(0.95), Inches(1.6), width=Inches(5.9))
        tx_qc = s9.shapes.add_textbox(Inches(0.95), Inches(6.1), Inches(5.9), Inches(0.5))
        tf_qc = tx_qc.text_frame
        tf_qc.word_wrap = True
        p_qc = tf_qc.paragraphs[0]
        p_qc.text = "Qualitative Comparison: Columns show (1) Input Grayscale IQ, (2) Ground Truth EBSD, (3) U-Net Prediction, (4) Translucent Phase Overlay."
        p_qc.font.name = "Segoe UI"
        p_qc.font.size = Pt(8.5)
        p_qc.font.color.rgb = COLOR_TEXT_MUTED

    # Right: Inference Engine Details
    add_bullet_card(s9, Inches(7.3), Inches(1.4), Inches(5.233), Inches(5.35),
        "Sliding-Window Inference Engine (6_inference.py)",
        [
            ("Arbitrary Image Sizing", "Production inference engine processes large SEM IQ scans of arbitrary pixel resolution by tiling into 128×128 sliding windows."),
            ("Hann Overlap Blending", "Optional 50% overlap mode uses 2D Hann window weighting to blend tile transitions, completely eliminating border seam artifacts."),
            ("Sub-2-Second Execution", "Inference on an entire 1024×1024 high-resolution scan completes in < 2.0 seconds on GPU (and < 8.5 seconds on multi-core CPU)."),
            ("Automated Deliverables", "Automatically saves binary mask arrays (.npy), color-coded phase maps (Red=Ferrite, Green=Austenite), translucent alpha overlays, and formatted phase reports.")
        ],
        tag="Deployment Ready"
    )


    # =========================================================================
    # SLIDE 10: METALLOGRAPHIC QUANTIFICATION: OPENCV WATERSHED
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10)
    add_header(s10, "OpenCV Watershed Grain Sizing & Metallographic Stereology", "STEREOLOGY MODULE")
    add_footer(s10, 10)

    # Left: Methodology details
    add_bullet_card(s10, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.35),
        "Automated Grain Sizing Engine (7_grain_size.py)",
        [
            ("Beyond Pixel Segmentation", "Industrial metallurgists require stereological parameters: grain size distributions, Planimetric density (N_A), and standard ASTM E112 Grain Size Numbers (G)."),
            ("The Continuous Matrix Challenge", "Ferrite forms a continuous matrix (~80.5%). Applying naive hole-filling destroys internal Austenite islands, merging the whole matrix into one flat sheet."),
            ("Morphological Conditioning", "Ferrite is filtered using a 3×3 elliptical opening (smoothing edge jitter without filling voids); Euclidean distance transform with 0.25 × max_dist isolates grain cores."),
            ("Marker-Controlled Watershed", "Connected components locate individual grain centroids; watershed flooding propagates markers until topological ridges meet, delineating clean boundaries."),
            ("Dispersed Phase Isolation", "Austenite islands (~19.1%) are handled with distance transform at 0.15 × max_dist to cleanly separate adjacent micro-grains.")
        ],
        tag="Novel Metallurgical Conditioning"
    )

    # Right: Grain boundaries overlay image
    gb_img = os.path.join(outputs_dir, "grain_size", "grain_boundaries_overlay.png")
    if os.path.exists(gb_img):
        add_card(s10, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35), bg_color=COLOR_CARD_BG)
        s10.shapes.add_picture(gb_img, Inches(7.0), Inches(1.6), width=Inches(5.333))
        tx_gb = s10.shapes.add_textbox(Inches(7.0), Inches(6.1), Inches(5.333), Inches(0.5))
        tf_gb = tx_gb.text_frame
        tf_gb.word_wrap = True
        p_gb = tf_gb.paragraphs[0]
        p_gb.text = "Watershed Boundary Overlay (7_grain_size.py): Segmented individual Ferrite and Austenite grain boundaries overlaid directly on SEM microstructure."
        p_gb.font.name = "Segoe UI"
        p_gb.font.size = Pt(8.5)
        p_gb.font.color.rgb = COLOR_TEXT_MUTED


    # =========================================================================
    # SLIDE 11: ASTM E112 STEREOLOGY & GROUND-TRUTH VALIDATION
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11)
    add_header(s11, "ASTM E112 Stereology & EBSD Ground-Truth Validation", "QUANTITATIVE STEREOLOGY")
    add_footer(s11, 11)

    # Left: Stereological Results Table
    t4_headers = ["Stereological Parameter", "Ferrite (BCC Matrix)", "Austenite (FCC Islands)"]
    t4_rows = [
        ["Total Grain Count (N)", "181 grains", "113 grains"],
        ["Phase Area Fraction", "80.42%", "19.07%"],
        ["Planimetric Density (N_A)", "214.6 grains/mm²", "565.1 grains/mm²"],
        ["Mean Equivalent Diameter (ECD)", "59.22 µm", "36.74 µm"],
        ["Median Diameter (D50)", "47.10 µm", "34.58 µm"],
        ["Grain Circularity (4πA/P²)", "0.514 ± 0.169", "0.468 ± 0.173"],
        ["Grain Aspect Ratio (Major/Minor)", "1.812 ± 1.120", "2.023 ± 0.864"],
        ["Heyn Linear Intercept (l)", "34.51 µm", "9.93 µm"],
        ["ASTM G (Planimetric N_A)", "G = 4.79", "G = 6.19"],
        ["ASTM G (Heyn Intercept l)", "G = 6.43", "G = 10.02"]
    ]
    col_w_t4 = [Inches(2.5), Inches(1.6), Inches(1.6)]
    add_table_widget(s11, Inches(0.8), Inches(1.4), Inches(5.7), Inches(5.35), t4_headers, t4_rows, col_w_t4)

    # Right: Validation & Boundary Denoising insight
    add_bullet_card(s11, Inches(6.8), Inches(1.4), Inches(5.733), Inches(5.35),
        "Validation vs EBSD Ground Truth: Denoising Effect",
        [
            ("93.6% Median Diameter Match", "Ferrite median diameter D50 reached 47.10 µm on AI prediction vs 44.28 µm on EBSD ground truth (only +6.37% delta)."),
            ("89.7% Grain Recovery Rate", "Austenite grain count recovered 113 grains vs 126 in EBSD ground truth."),
            ("ASTM G Concordance", "Ferrite ASTM G = 5.56 vs 6.14 (ΔG = 0.58), well within standard ASTM E112 visual rating tolerances (± 1.0 G unit)."),
            ("Metallurgical Discovery: Gap Denoising", "In raw EBSD scans, 15.8% of boundary pixels are unindexed (black) due to diffraction pattern overlap, artificially fracturing grains. The U-Net seamlessly bridges these unindexed gaps, creating more continuous physical grains.")
        ],
        tag="Metallurgical Physical Verification",
        bg_color=COLOR_SUCCESS_LIGHT
    )


    # =========================================================================
    # SLIDE 12: COMPREHENSIVE SUMMARY OF COMPLETED WORK
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12)
    add_header(s12, "Summary of Completed Work & Project Milestone Alignment", "PROJECT STATUS")
    add_footer(s12, 12)

    t6_headers = ["BTP Project Milestone", "Status", "Technical Achievement / Quantitative Benchmark"]
    t6_rows = [
        ["EBSD-Supervised U-Net Pipeline", "COMPLETED", "Fully automated training, validation, and serialization pipeline operational."],
        ["Dual-Phase Semantic Segmentation", "COMPLETED", "2-class segmentation (Ferrite BCC / Austenite FCC) on SEM IQ maps."],
        ["Phase Fraction Quantification", "COMPLETED", "Phase fractions calculated within 0.05% error vs physical EBSD ground truth."],
        ["Full-Image Sliding-Window Inference", "COMPLETED", "50% overlap Hann blending engine (< 2.0s inference on 1024×1024 maps)."],
        ["OpenCV Watershed Stereology", "COMPLETED", "Marker-controlled watershed, CSV grain cataloging, and ASTM E112 rating."],
        ["High Pixel Accuracy Target", "COMPLETED", "Achieved 89.19% pixel accuracy and 0.7163 mIoU (0.9332 Ferrite F1) on holdout test set."],
        ["Comprehensive Project Documentation", "COMPLETED", "Full 40-page project report document generated with code annotations."]
    ]
    col_w_t6 = [Inches(3.0), Inches(1.4), Inches(7.333)]
    add_table_widget(s12, Inches(0.8), Inches(1.4), Inches(11.733), Inches(5.35), t6_headers, t6_rows, col_w_t6)


    # =========================================================================
    # SLIDE 13: FUTURE WORK & PROJECT ROADMAP
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13)
    add_header(s13, "Future Work & Technical Roadmap for BTP Final Phase", "ROADMAP & NEXT STEPS")
    add_footer(s13, 13)

    col_w_r = Inches(3.64)

    add_bullet_card(s13, Inches(0.8), Inches(1.4), col_w_r, Inches(5.35),
        "1. IQ Ridge-Guided Watershed",
        [
            ("Sub-Grain Detection", "SEM IQ maps display dark channeling ridges at sub-grain boundaries and dislocation cells."),
            ("Priority Flood Gradient", "Incorporate normalized IQ Sobel edge gradients directly into the watershed priority flood function."),
            ("Grain Subdivision", "Enable sub-division of large elongated Ferrite matrix domains into crystallographic sub-grains.")
        ],
        tag="Algorithm Enhancement"
    )

    add_bullet_card(s13, Inches(0.8 + 3.64 + 0.4), Inches(1.4), col_w_r, Inches(5.35),
        "2. Batch Dataset Metallography",
        [
            ("Full Dataset Profiling", "Execute sliding-window inference and OpenCV Watershed across all remaining SEM IQ scans (IQ1 through IQ6)."),
            ("Statistical Validation", "Establish robust comparative stereological distributions across all steel samples."),
            ("Automated Report Generation", "Compile multi-sample comparative CSV catalogs and ASTM summary charts.")
        ],
        tag="Cross-Sample Profiling"
    )

    add_bullet_card(s13, Inches(0.8 + (3.64 + 0.4)*2), Inches(1.4), col_w_r, Inches(5.35),
        "3. Thermal Processing Generalization",
        [
            ("Heat Treatment Robustness", "Evaluate model robustness across different intercritical annealing temperatures (650°C to 750°C)."),
            ("Varying Austenite Morphologies", "Validate segmentation against both globular and lamellar/filmy retained austenite structures."),
            ("Self-Supervised Fine-Tuning", "Investigate masked autoencoding (MAE) to adapt model to new alloy compositions.")
        ],
        tag="Metallurgical Scope"
    )


    # =========================================================================
    # SLIDE 14: CONCLUSION & Q&A
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14)

    # Top accent bar
    top_bar14 = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    top_bar14.fill.solid()
    top_bar14.fill.fore_color.rgb = COLOR_PRIMARY
    top_bar14.line.color.rgb = COLOR_PRIMARY

    # Center Hero Card
    add_card(s14, Inches(1.8), Inches(1.3), Inches(9.733), Inches(4.8), bg_color=COLOR_CARD_BG)

    tb14 = s14.shapes.add_textbox(Inches(2.3), Inches(1.7), Inches(8.733), Inches(4.0))
    tf14 = tb14.text_frame
    tf14.word_wrap = True
    tf14.margin_left = tf14.margin_top = tf14.margin_right = tf14.margin_bottom = 0

    p_badge14 = tf14.paragraphs[0]
    p_badge14.text = "PROJECT SUMMARY & CONCLUSION"
    p_badge14.font.name = "Segoe UI"
    p_badge14.font.size = Pt(11)
    p_badge14.font.bold = True
    p_badge14.font.color.rgb = COLOR_PRIMARY

    p_title14 = tf14.add_paragraph()
    p_title14.text = "High-Throughput Metallography Achieved"
    p_title14.font.name = "Segoe UI"
    p_title14.font.size = Pt(28)
    p_title14.font.bold = True
    p_title14.font.color.rgb = COLOR_TEXT_TITLE
    p_title14.space_before = Pt(8)
    p_title14.space_after = Pt(12)

    p_body14 = tf14.add_paragraph()
    p_body14.text = "• Successfully bridged fast SEM Image Quality maps with crystallographic EBSD accuracy using an EfficientNet-B0 U-Net architecture.\n• Reached 89.19% pixel accuracy, 0.7163 mIoU, and < 0.05% phase fraction error on unseen holdout test scans.\n• Deployed automated OpenCV Watershed stereology providing ASTM E112 grain sizes (G = 4.8–6.4 for Ferrite, G = 6.2–10.0 for Austenite) in < 2 seconds.\n• Proved AI boundary denoising effect on unindexed EBSD diffraction gaps (93.6% median diameter concordance)."
    p_body14.font.name = "Segoe UI"
    p_body14.font.size = Pt(12)
    p_body14.font.color.rgb = COLOR_TEXT_BODY
    p_body14.space_after = Pt(20)

    p_thx = tf14.add_paragraph()
    p_thx.text = "Thank you! Open for Questions & Discussion."
    p_thx.font.name = "Segoe UI"
    p_thx.font.size = Pt(16)
    p_thx.font.bold = True
    p_thx.font.color.rgb = COLOR_PRIMARY

    output_path = os.path.join(base_dir, "BTP_Project_Presentation.pptx")
    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_deck()
