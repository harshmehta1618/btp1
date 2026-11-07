"""
7_grain_size.py
---------------
OpenCV + Watershed grain size quantification and stereological analysis 
on predicted segmentation masks for Medium Mn Steel.

Features:
  1. Morphological conditioning tailored to continuous matrix (Ferrite) vs dispersed phase (Austenite)
  2. Euclidean distance transform + marker-controlled Watershed segmentation
  3. Stereological metrics: Area, Equivalent Circular Diameter (ECD), Perimeter, Circularity, Aspect Ratio
  4. ASTM E112 grain size number calculations:
       - Planimetric method (grain density N_A)
       - Heyn Linear Intercept method (mean intercept l)
       - Equivalent diameter method
  5. Multi-panel publication-grade visualizations (dark theme):
       - Individual phase grain maps + histograms
       - 4-panel comparison dashboard
       - Cumulative Distribution Function (CDF) with D10/D50/D90
       - Shape descriptor scatter (Circularity vs Aspect Ratio)
       - Microstructure boundary overlay on IQ image
  6. Tabular exports (CSV), JSON summary, and formatted ASTM text report

Usage:
    python 7_grain_size.py
    python 7_grain_size.py --mask outputs/inference/IQ_mask.npy --scale 0.5 --min_area 30
    python 7_grain_size.py --iq "../IQ and EBSD Phase maps/IQ.tif"
"""

import os
import argparse
import csv
import json
import math
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy import ndimage as ndi
from PIL import Image

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MASK = os.path.join(SCRIPT_DIR, "outputs", "inference", "IQ_mask.npy")
DEFAULT_IQ   = os.path.join(SCRIPT_DIR, "..", "IQ and EBSD Phase maps", "IQ.tif")
OUTPUT_DIR   = os.path.join(SCRIPT_DIR, "outputs", "grain_size")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  ASTM E112 Standard Calculations
# ─────────────────────────────────────────────────────────────────────────────

def astm_G_from_diameter(d_um: float) -> float:
    """
    Calculate ASTM Grain Size Number G from mean equivalent diameter (um).
    ASTM E112: G = -6.643856 * log10(d_mm) - 2.600
    """
    if d_um <= 0:
        return float("nan")
    d_mm = d_um / 1000.0
    return -6.643856 * math.log10(d_mm) - 2.600


def astm_G_from_count(n_per_mm2: float) -> float:
    """
    Calculate ASTM Grain Size Number G from planimetric grain density (grains/mm^2).
    ASTM E112 metric formula: G = 3.321928 * log10(N_A) - 2.954
    """
    if n_per_mm2 <= 0:
        return float("nan")
    return 3.321928 * math.log10(n_per_mm2) - 2.954


def astm_G_from_intercept(l_um: float) -> float:
    """
    Calculate ASTM Grain Size Number G from Heyn mean linear intercept l (um).
    ASTM E112: G = -6.643856 * log10(l_mm) - 3.288
    """
    if l_um <= 0:
        return float("nan")
    l_mm = l_um / 1000.0
    return -6.643856 * math.log10(l_mm) - 3.288


# ─────────────────────────────────────────────────────────────────────────────
#  Segmentation & Morphological Conditioning
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_mask(binary: np.ndarray, is_matrix: bool = False, min_area: int = 30) -> np.ndarray:
    """
    Filter out tiny noise components while preserving grain boundaries.
    For non-matrix phase (Austenite), fill internal indexing holes.
    For matrix phase (Ferrite), do NOT fill holes (which are Austenite islands).
    """
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    cleaned = np.zeros_like(binary)
    for lbl in range(1, n):
        if stats[lbl, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == lbl] = 255

    if not is_matrix:
        cleaned = ndi.binary_fill_holes(cleaned > 0).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    return cleaned


def watershed_segment(binary: np.ndarray, is_matrix: bool = False) -> tuple:
    """
    Distance transform + Marker-controlled Watershed segmentation.
    Returns:
        grain_map: (H, W) int32 array with grain IDs 1..N (0 = background)
        boundary_mask: (H, W) uint8 binary mask of grain boundaries (255 = boundary)
    """
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

    # Adaptive threshold on distance transform
    thresh = 0.25 if is_matrix else 0.35
    _, sure_fg = cv2.threshold(dist, thresh * dist.max(), 255, cv2.THRESH_BINARY)
    sure_fg = sure_fg.astype(np.uint8)

    # Dilate binary to find region of interest & unknown band
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    sure_bg = cv2.dilate(binary, k, iterations=2)
    unknown = cv2.subtract(sure_bg, sure_fg)

    # Seed connected components
    num_fg, fg_markers = cv2.connectedComponents(sure_fg, connectivity=8)

    # Shift markers: background seed = 1, unknown = 0, grain seeds = 2..N+1
    markers = fg_markers + 1
    markers[unknown == 255] = 0
    markers[binary == 0] = 1

    # Watershed
    img_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    markers = cv2.watershed(img_bgr, markers)

    # Boundary mask (where watershed placed boundaries)
    boundary_mask = np.zeros_like(binary)
    boundary_mask[(markers == -1) & (binary > 0)] = 255

    # Extract valid grains inside phase
    raw_grains = np.zeros_like(markers, dtype=np.int32)
    valid_grain_px = (markers >= 2) & (binary > 0)
    raw_grains[valid_grain_px] = markers[valid_grain_px]

    # Re-index consecutively 1..N
    unique_ids = np.unique(raw_grains[raw_grains > 0])
    grain_map = np.zeros_like(raw_grains, dtype=np.int32)
    for new_id, old_id in enumerate(unique_ids, start=1):
        grain_map[raw_grains == old_id] = new_id

    return grain_map, boundary_mask


# ─────────────────────────────────────────────────────────────────────────────
#  Grain Measurement & Stereology
# ─────────────────────────────────────────────────────────────────────────────

def measure_grains(grain_map: np.ndarray, phase_name: str, scale: float, min_area: int = 30) -> list:
    """
    Compute per-grain geometric and stereological properties.
    """
    results = []
    unique_ids = np.unique(grain_map[grain_map > 0])

    for gid in unique_ids:
        mask = (grain_map == gid).astype(np.uint8) * 255
        area_px = int(np.sum(mask > 0))
        if area_px < min_area:
            continue

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        cnt = max(contours, key=cv2.contourArea)

        peri_px = cv2.arcLength(cnt, closed=True)
        circ = min((4.0 * math.pi * area_px / (peri_px ** 2)) if peri_px > 0 else 0.0, 1.0)
        ecd_px = math.sqrt(4.0 * area_px / math.pi)

        # Ellipse fitting for aspect ratio & orientation
        aspect = 1.0
        major_axis_px = ecd_px
        minor_axis_px = ecd_px
        angle_deg = 0.0

        if len(cnt) >= 5:
            try:
                (cx_e, cy_e), (d1, d2), angle_deg = cv2.fitEllipse(cnt)
                major = max(d1, d2)
                minor = min(d1, d2)
                if minor > 0:
                    aspect = major / minor
                    major_axis_px = major
                    minor_axis_px = minor
            except Exception:
                pass

        # Moments & centroid
        M = cv2.moments(cnt)
        cx = (M["m10"] / M["m00"]) if M["m00"] > 0 else float(cnt[:, 0, 0].mean())
        cy = (M["m01"] / M["m00"]) if M["m00"] > 0 else float(cnt[:, 0, 1].mean())

        # Bounding box & Feret dimensions
        x, y, bw, bh = cv2.boundingRect(cnt)
        rect = cv2.minAreaRect(cnt)
        feret_max_px = max(rect[1][0], rect[1][1]) if (rect[1][0] > 0 and rect[1][1] > 0) else max(bw, bh)
        feret_min_px = min(rect[1][0], rect[1][1]) if (rect[1][0] > 0 and rect[1][1] > 0) else min(bw, bh)

        results.append({
            "grain_id":           int(gid),
            "phase":              phase_name,
            "area_px":            area_px,
            "area_um2":           round(area_px * (scale ** 2), 4),
            "equivalent_diam_px": round(ecd_px, 3),
            "equivalent_diam_um": round(ecd_px * scale, 3),
            "perimeter_px":       round(peri_px, 3),
            "perimeter_um":       round(peri_px * scale, 3),
            "circularity":        round(circ, 4),
            "aspect_ratio":       round(aspect, 4),
            "major_axis_um":      round(major_axis_px * scale, 3),
            "minor_axis_um":      round(minor_axis_px * scale, 3),
            "orientation_deg":    round(angle_deg, 2),
            "feret_max_um":       round(feret_max_px * scale, 3),
            "feret_min_um":       round(feret_min_px * scale, 3),
            "centroid_x":         round(cx, 1),
            "centroid_y":         round(cy, 1),
        })

    return results


def mean_linear_intercept(binary: np.ndarray, scale: float, n_lines: int = 50) -> float:
    """
    Heyn Linear Intercept method (ASTM E112).
    Casts n_lines horizontally and vertically across the phase mask.
    Returns:
        mean_intercept_um: mean intercept length in um
    """
    H, W = binary.shape
    tot_length_um = 0.0
    tot_intercepts = 0

    # Horizontal test lines
    row_indices = np.linspace(10, H - 10, n_lines, dtype=int)
    for r in row_indices:
        line = binary[r, :]
        in_phase = (line > 0).astype(int)
        crossings = int(np.sum(np.diff(in_phase) != 0))
        if crossings > 0:
            tot_length_um += np.sum(in_phase) * scale
            tot_intercepts += crossings

    # Vertical test lines
    col_indices = np.linspace(10, W - 10, n_lines, dtype=int)
    for c in col_indices:
        line = binary[:, c]
        in_phase = (line > 0).astype(int)
        crossings = int(np.sum(np.diff(in_phase) != 0))
        if crossings > 0:
            tot_length_um += np.sum(in_phase) * scale
            tot_intercepts += crossings

    if tot_intercepts == 0:
        return 0.0
    return tot_length_um / tot_intercepts


def compute_summary(grain_data: list, binary: np.ndarray, total_img_px: int, scale: float) -> dict:
    """
    Aggregate phase statistics, size distribution quantiles, and ASTM numbers.
    """
    if not grain_data:
        return {}

    diams   = [g["equivalent_diam_um"] for g in grain_data]
    circs   = [g["circularity"] for g in grain_data]
    aspects = [g["aspect_ratio"] for g in grain_data]
    n       = len(grain_data)

    phase_px = int(np.sum(binary > 0))
    phase_area_um2 = phase_px * (scale ** 2)
    phase_area_mm2 = phase_area_um2 / 1e6
    phase_fraction = (phase_px / total_img_px) * 100.0

    # Planimetric grain density N_A (grains/mm^2)
    g_per_mm2 = (n / phase_area_mm2) if phase_area_mm2 > 0 else 0.0

    # Heyn linear intercept
    L_um = mean_linear_intercept(binary, scale)

    # ASTM Grain Size Numbers
    G_diam  = astm_G_from_diameter(float(np.mean(diams)))
    G_count = astm_G_from_count(g_per_mm2)
    G_int   = astm_G_from_intercept(L_um)

    return {
        "n_grains":                n,
        "phase_fraction_pct":      round(phase_fraction, 2),
        "phase_area_um2":          round(phase_area_um2, 2),
        "mean_diam_um":            round(float(np.mean(diams)), 3),
        "std_diam_um":             round(float(np.std(diams)), 3),
        "median_diam_um":          round(float(np.median(diams)), 3),
        "min_diam_um":             round(float(np.min(diams)), 3),
        "max_diam_um":             round(float(np.max(diams)), 3),
        "D10_um":                  round(float(np.percentile(diams, 10)), 3),
        "D50_um":                  round(float(np.percentile(diams, 50)), 3),
        "D90_um":                  round(float(np.percentile(diams, 90)), 3),
        "mean_circularity":        round(float(np.mean(circs)), 4),
        "std_circularity":         round(float(np.std(circs)), 4),
        "mean_aspect_ratio":       round(float(np.mean(aspects)), 4),
        "std_aspect_ratio":        round(float(np.std(aspects)), 4),
        "mean_intercept_um":       round(L_um, 3),
        "grains_per_mm2":          round(g_per_mm2, 2),
        "ASTM_G_planimetric":      (round(G_count, 2) if not math.isnan(G_count) else "N/A"),
        "ASTM_G_intercept":        (round(G_int, 2) if not math.isnan(G_int) else "N/A"),
        "ASTM_G_diameter":         (round(G_diam, 2) if not math.isnan(G_diam) else "N/A"),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Visualizations
# ─────────────────────────────────────────────────────────────────────────────

def get_random_colormap(n_colors: int = 512, seed: int = 42) -> ListedColormap:
    """Generate high-contrast randomized colormap with background at index 0."""
    rng = np.random.RandomState(seed)
    colors = rng.uniform(0.2, 0.95, size=(n_colors, 3))
    colors[0] = [0.07, 0.07, 0.10]  # dark background
    return ListedColormap(colors)


def plot_grain_map(labels: np.ndarray, phase_name: str, grain_data: list, save_path: str):
    """
    2-panel figure: Colored grain label map + Equivalent diameter histogram.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), facecolor="#0E0E14")

    # Grain Map
    n_labels = max(int(labels.max()) + 2, 512)
    cmap = get_random_colormap(n_labels)
    disp = labels.copy().astype(float)
    disp[disp < 0] = 0

    ax1.set_facecolor("#0E0E14")
    ax1.imshow(disp, cmap=cmap, interpolation="nearest", vmin=0, vmax=max(float(disp.max()), 1))
    ax1.set_title(f"{phase_name} Grain Map ({len(grain_data)} grains)",
                  color="white", fontsize=13, fontweight="bold", pad=12)
    ax1.axis("off")

    # Distribution Histogram
    colour = "#FF5C5C" if phase_name == "Ferrite" else "#4ADE80"
    ax2.set_facecolor("#161622")
    ax2.tick_params(colors="#CCCCCC", labelsize=10)
    for sp in ax2.spines.values():
        sp.set_color("#3A3A4C")

    diams = [g["equivalent_diam_um"] for g in grain_data]
    if diams:
        n_bins = min(40, max(12, len(diams) // 4))
        ax2.hist(diams, bins=n_bins, color=colour, alpha=0.85,
                 edgecolor="#FFFFFF", linewidth=0.5, density=False)
        mean_val = float(np.mean(diams))
        median_val = float(np.median(diams))
        d10 = float(np.percentile(diams, 10))
        d90 = float(np.percentile(diams, 90))

        ax2.axvline(mean_val, color="#FDE047", lw=2, ls="--",
                    label=f"Mean = {mean_val:.2f} um")
        ax2.axvline(median_val, color="#38BDF8", lw=2, ls=":",
                    label=f"Median = {median_val:.2f} um")
        ax2.axvline(d10, color="#A78BFA", lw=1.2, ls="-.",
                    label=f"D10 = {d10:.2f} um")
        ax2.axvline(d90, color="#FB923C", lw=1.2, ls="-.",
                    label=f"D90 = {d90:.2f} um")
        ax2.legend(fontsize=9, facecolor="#161622", edgecolor="#3A3A4C", labelcolor="white")

    ax2.set_xlabel("Equivalent Circular Diameter (um)", color="white", fontsize=11, labelpad=8)
    ax2.set_ylabel("Grain Count", color="white", fontsize=11, labelpad=8)
    ax2.set_title(f"{phase_name} Grain Size Distribution",
                  color="white", fontsize=13, fontweight="bold", pad=12)
    ax2.grid(True, linestyle="--", alpha=0.15, color="white")

    plt.tight_layout()
    plt.savefig(save_path, dpi=180, bbox_inches="tight", facecolor="#0E0E14")
    plt.close()
    print("  Saved ->", save_path)


def plot_combined_dashboard(f_data: list, a_data: list, f_labels: np.ndarray,
                            a_labels: np.ndarray, save_path: str):
    """
    4-panel dashboard: Ferrite map, Austenite map, Ferrite histogram, Austenite histogram.
    """
    fig = plt.figure(figsize=(18, 13), facecolor="#0E0E14")
    gs = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.22)

    configs = [
        (f_labels, f_data, "Ferrite (BCC Matrix)", "#FF5C5C", 0),
        (a_labels, a_data, "Austenite (FCC Dispersed)", "#4ADE80", 1),
    ]

    for labels, data, name, colour, col_idx in configs:
        # Spatial Map
        cmap = get_random_colormap(max(int(labels.max()) + 2, 512), seed=10 + col_idx)
        ax_map = fig.add_subplot(gs[0, col_idx])
        ax_map.set_facecolor("#0E0E14")
        disp = labels.copy().astype(float)
        disp[disp < 0] = 0
        ax_map.imshow(disp, cmap=cmap, interpolation="nearest", vmin=0, vmax=max(float(disp.max()), 1))
        ax_map.set_title(f"{name} -- {len(data)} Grains",
                         color="white", fontsize=12, fontweight="bold", pad=10)
        ax_map.axis("off")

        # Histogram
        ax_hist = fig.add_subplot(gs[1, col_idx])
        ax_hist.set_facecolor("#161622")
        ax_hist.tick_params(colors="#CCCCCC", labelsize=9)
        for sp in ax_hist.spines.values():
            sp.set_color("#3A3A4C")

        diams = [g["equivalent_diam_um"] for g in data]
        if diams:
            n_bins = min(40, max(12, len(diams) // 4))
            ax_hist.hist(diams, bins=n_bins, color=colour, alpha=0.85,
                         edgecolor="#FFFFFF", linewidth=0.4)
            mean_v = float(np.mean(diams))
            med_v = float(np.median(diams))
            ax_hist.axvline(mean_v, color="#FDE047", lw=1.8, ls="--", label=f"Mean={mean_v:.1f} um")
            ax_hist.axvline(med_v, color="#38BDF8", lw=1.8, ls=":", label=f"Median={med_v:.1f} um")
            ax_hist.legend(fontsize=9, facecolor="#161622", edgecolor="#3A3A4C", labelcolor="white")

        ax_hist.set_xlabel("Equivalent Diameter (um)", color="white", fontsize=10, labelpad=6)
        ax_hist.set_ylabel("Grain Count", color="white", fontsize=10, labelpad=6)
        ax_hist.set_title(f"{name} Size Distribution", color="white", fontsize=11, fontweight="bold", pad=8)
        ax_hist.grid(True, linestyle="--", alpha=0.15, color="white")

    fig.suptitle("Dual-Phase Microstructure Grain Quantification -- Medium Mn Steel",
                 color="white", fontsize=15, fontweight="bold", y=0.98)

    plt.savefig(save_path, dpi=180, bbox_inches="tight", facecolor="#0E0E14")
    plt.close()
    print("  Saved ->", save_path)


def plot_cdf(f_data: list, a_data: list, save_path: str):
    """
    Cumulative Distribution Function (CDF) comparing Ferrite vs Austenite.
    """
    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor="#0E0E14")
    ax.set_facecolor("#161622")
    ax.tick_params(colors="#CCCCCC", labelsize=10)
    for sp in ax.spines.values():
        sp.set_color("#3A3A4C")

    curves = [
        (f_data, "Ferrite",   "#FF5C5C"),
        (a_data, "Austenite", "#4ADE80"),
    ]

    for data, name, colour in curves:
        if not data:
            continue
        diams = sorted([g["equivalent_diam_um"] for g in data])
        cdf = np.arange(1, len(diams) + 1) / len(diams)
        ax.plot(diams, cdf, color=colour, lw=2.5, label=f"{name} (n={len(data)})")

        d10 = float(np.percentile(diams, 10))
        d50 = float(np.percentile(diams, 50))
        d90 = float(np.percentile(diams, 90))
        ax.axvline(d50, color=colour, lw=1.2, ls="--", alpha=0.7)
        ax.scatter([d10, d50, d90], [0.10, 0.50, 0.90], color=colour, s=40, zorder=5)

    ax.set_xlabel("Equivalent Circular Diameter (um)", color="white", fontsize=12, labelpad=8)
    ax.set_ylabel("Cumulative Probability P(D <= d)", color="white", fontsize=12, labelpad=8)
    ax.set_title("Grain Size Cumulative Distribution Function (CDF)",
                 color="white", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=10, facecolor="#161622", edgecolor="#3A3A4C", labelcolor="white")
    ax.grid(True, linestyle="--", alpha=0.2, color="white")

    plt.tight_layout()
    plt.savefig(save_path, dpi=180, bbox_inches="tight", facecolor="#0E0E14")
    plt.close()
    print("  Saved ->", save_path)


def plot_shape_descriptors(f_data: list, a_data: list, save_path: str):
    """
    Bivariate scatter plot: Aspect Ratio vs Circularity for both phases.
    """
    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor="#0E0E14")
    ax.set_facecolor("#161622")
    ax.tick_params(colors="#CCCCCC", labelsize=10)
    for sp in ax.spines.values():
        sp.set_color("#3A3A4C")

    if f_data:
        f_circ = [g["circularity"] for g in f_data]
        f_asp  = [g["aspect_ratio"] for g in f_data]
        ax.scatter(f_circ, f_asp, color="#FF5C5C", alpha=0.55, edgecolors="none",
                   s=35, label=f"Ferrite (n={len(f_data)})")

    if a_data:
        a_circ = [g["circularity"] for g in a_data]
        a_asp  = [g["aspect_ratio"] for g in a_data]
        ax.scatter(a_circ, a_asp, color="#4ADE80", alpha=0.65, edgecolors="none",
                   s=35, label=f"Austenite (n={len(a_data)})")

    ax.set_xlabel("Circularity (1.0 = perfect circle)", color="white", fontsize=12, labelpad=8)
    ax.set_ylabel("Aspect Ratio (Major / Minor Axis, 1.0 = equiaxed)", color="white", fontsize=12, labelpad=8)
    ax.set_title("Grain Morphology -- Aspect Ratio vs Circularity",
                 color="white", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=10, facecolor="#161622", edgecolor="#3A3A4C", labelcolor="white")
    ax.grid(True, linestyle="--", alpha=0.2, color="white")

    plt.tight_layout()
    plt.savefig(save_path, dpi=180, bbox_inches="tight", facecolor="#0E0E14")
    plt.close()
    print("  Saved ->", save_path)


def plot_boundaries_overlay(iq_path: str, f_bounds: np.ndarray, a_bounds: np.ndarray,
                            pred_mask: np.ndarray, save_path: str):
    """
    Overlay grain boundary network onto either IQ image (if exists) or phase mask.
    """
    H, W = pred_mask.shape
    if os.path.exists(iq_path):
        base = np.array(Image.open(iq_path).convert("L"), dtype=np.uint8)
        base = cv2.resize(base, (W, H))
        rgb = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB)
    else:
        # Fallback to dark background with phase tints
        rgb = np.zeros((H, W, 3), dtype=np.uint8)
        rgb[pred_mask == 0] = [80, 25, 25]    # dark red
        rgb[pred_mask == 1] = [25, 75, 25]    # dark green

    # Ferrite boundaries in Cyan [0, 240, 255]
    rgb[f_bounds > 0] = [0, 240, 255]
    # Austenite boundaries in Yellow [255, 235, 59]
    rgb[a_bounds > 0] = [255, 235, 59]

    fig, ax = plt.subplots(figsize=(10, 10), facecolor="#0E0E14")
    ax.imshow(rgb)
    ax.set_title("Microstructure Grain Boundary Network Overlay\n"
                 "[Cyan = Ferrite Boundaries | Yellow = Austenite Boundaries]",
                 color="white", fontsize=12, fontweight="bold", pad=12)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches="tight", facecolor="#0E0E14")
    plt.close()
    print("  Saved ->", save_path)


# ─────────────────────────────────────────────────────────────────────────────
#  Reporting & Export
# ─────────────────────────────────────────────────────────────────────────────

def save_csv(grain_data: list, path: str):
    """Export grain properties table to CSV."""
    if not grain_data:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(grain_data[0].keys()))
        w.writeheader()
        w.writerows(grain_data)
    print("  CSV   ->", path)


def write_report(f_sum: dict, a_sum: dict, scale: float, mask_path: str,
                 min_area: int, save_path: str):
    """Write formatted ASTM E112 stereological inspection report."""
    sep = "=" * 65
    subsep = "-" * 65

    scale_str = f"{scale:.4f} um/pixel" if scale != 1.0 else "1.0000 px/px (Uncalibrated, set --scale)"

    lines = [
        sep,
        "   METALLOGRAPHIC GRAIN SIZE & STEREOLOGY REPORT",
        "   Medium Mn Steel | EfficientNet-UNet AI Segmentation",
        sep,
        f"  Mask Path       : {mask_path}",
        f"  Spatial Scale   : {scale_str}",
        f"  Min Area Cutoff : {min_area} pixels",
        "",
    ]

    for title, s in [("FERRITE PHASE (BCC Matrix)", f_sum), ("AUSTENITE PHASE (FCC Dispersed)", a_sum)]:
        if not s:
            continue
        lines += [
            subsep,
            f"  {title}",
            subsep,
            f"  Phase Area Fraction          : {s['phase_fraction_pct']:.2f}%",
            f"  Phase Area                   : {s['phase_area_um2']:.1f} um^2",
            f"  Total Grain Count            : {s['n_grains']}",
            f"  Planimetric Grain Density N_A: {s['grains_per_mm2']:.1f} grains/mm^2",
            "",
            "  -- Equivalent Circular Diameter (ECD) --",
            f"  Mean ECD                     : {s['mean_diam_um']:.3f} um",
            f"  Standard Deviation           : {s['std_diam_um']:.3f} um",
            f"  Median ECD (D50)             : {s['median_diam_um']:.3f} um",
            f"  D10                          : {s['D10_um']:.3f} um",
            f"  D90                          : {s['D90_um']:.3f} um",
            f"  Min / Max ECD                : {s['min_diam_um']:.3f} / {s['max_diam_um']:.3f} um",
            "",
            "  -- Morphological Descriptors --",
            f"  Mean Circularity (4*pi*A/P^2): {s['mean_circularity']:.4f} +/- {s['std_circularity']:.4f}  (1.0 = circle)",
            f"  Mean Aspect Ratio (Major/Min): {s['mean_aspect_ratio']:.4f} +/- {s['std_aspect_ratio']:.4f}  (1.0 = equiaxed)",
            "",
            "  -- ASTM E112 Grain Size Number --",
            f"  Heyn Mean Linear Intercept l : {s['mean_intercept_um']:.3f} um",
            f"  ASTM G (Planimetric N_A)     : {s['ASTM_G_planimetric']}",
            f"  ASTM G (Heyn Intercept l)    : {s['ASTM_G_intercept']}",
            f"  ASTM G (Mean Diameter d)     : {s['ASTM_G_diameter']}",
            "",
        ]

    lines += [
        sep,
        "  ASTM E112 Standard Reference Benchmark:",
        "    G =  1  -> ~254 um | G =  5 -> ~63.5 um | G =  8 -> ~22.5 um",
        "    G = 10  -> ~11.2 um | G = 12 ->  ~5.6 um | G = 14 ->  ~2.8 um",
        "  Note: Higher ASTM G indicates finer microstructure.",
        sep,
    ]

    report_text = "\n".join(lines)
    print("\n" + report_text)

    with open(save_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print("  Report ->", save_path)


# ─────────────────────────────────────────────────────────────────────────────
#  Pipeline Execution
# ─────────────────────────────────────────────────────────────────────────────

def process_single_phase(pred_mask: np.ndarray, class_id: int, phase_name: str,
                         scale: float, min_area: int) -> tuple:
    """Run full preprocessing, watershed, and measurement on one phase."""
    print(f"\n[Processing Phase] {phase_name} (Class {class_id})")
    is_matrix = (class_id == 0)

    binary = (pred_mask == class_id).astype(np.uint8) * 255
    px = int(np.sum(binary > 0))
    pct = (px / pred_mask.size) * 100.0
    print(f"  Raw Pixels        : {px} ({pct:.2f}%)")

    cleaned = preprocess_mask(binary, is_matrix=is_matrix, min_area=min_area)
    print(f"  Cleaned Pixels    : {int(np.sum(cleaned > 0))}")

    grain_map, boundary_mask = watershed_segment(cleaned, is_matrix=is_matrix)
    n_grains_raw = int(grain_map.max())
    print(f"  Watershed Regions : {n_grains_raw}")

    grain_data = measure_grains(grain_map, phase_name, scale, min_area)
    print(f"  Qualified Grains  : {len(grain_data)}")

    summary = compute_summary(grain_data, cleaned, pred_mask.size, scale)
    return grain_data, summary, grain_map, boundary_mask


def main():
    parser = argparse.ArgumentParser(
        description="OpenCV Watershed Grain Size & Stereology Module for UNet Masks"
    )
    parser.add_argument("--mask", default=DEFAULT_MASK,
                        help="Path to .npy or image segmentation mask")
    parser.add_argument("--iq", default=DEFAULT_IQ,
                        help="Path to original IQ .tif image (for boundary overlay)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Spatial calibration in microns per pixel (default: 1.0)")
    parser.add_argument("--min_area", type=int, default=30,
                        help="Minimum grain area cutoff in pixels (default: 30)")
    parser.add_argument("--phase", default="both",
                        choices=["both", "ferrite", "austenite"],
                        help="Phase to quantify (default: both)")
    parser.add_argument("--out_dir", default=OUTPUT_DIR,
                        help="Output directory for reports and figures")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("=" * 65)
    print("  OpenCV Watershed Grain Size & Stereology Module")
    print("  Medium Mn Steel | EfficientNet-UNet")
    print("=" * 65)
    print(f"  Mask Input : {args.mask}")
    print(f"  IQ Input   : {args.iq}")
    print(f"  Scale      : {args.scale} um/pixel")
    print(f"  Min Area   : {args.min_area} px")
    print(f"  Phase      : {args.phase}")

    if not os.path.exists(args.mask):
        print(f"[ERROR] Mask not found: {args.mask}")
        print("  Please run 6_inference.py first to generate the segmentation mask.")
        return

    # Load mask
    if args.mask.endswith(".npy"):
        pred_mask = np.load(args.mask)
    else:
        pred_mask = np.array(Image.open(args.mask).convert("L"))

    print(f"  Mask Shape : {pred_mask.shape}, Labels : {np.unique(pred_mask)}")

    f_data, f_sum, f_map, f_bounds = [], {}, np.zeros_like(pred_mask, np.int32), np.zeros_like(pred_mask, np.uint8)
    a_data, a_sum, a_map, a_bounds = [], {}, np.zeros_like(pred_mask, np.int32), np.zeros_like(pred_mask, np.uint8)

    # ── Ferrite Quantification ─────────────────────────────────────────────────
    if args.phase in ("both", "ferrite"):
        f_data, f_sum, f_map, f_bounds = process_single_phase(
            pred_mask, 0, "Ferrite", args.scale, args.min_area
        )
        plot_grain_map(
            f_map, "Ferrite", f_data,
            os.path.join(args.out_dir, "ferrite_grains.png")
        )
        save_csv(f_data, os.path.join(args.out_dir, "ferrite_grain_stats.csv"))

    # ── Austenite Quantification ───────────────────────────────────────────────
    if args.phase in ("both", "austenite"):
        a_data, a_sum, a_map, a_bounds = process_single_phase(
            pred_mask, 1, "Austenite", args.scale, args.min_area
        )
        plot_grain_map(
            a_map, "Austenite", a_data,
            os.path.join(args.out_dir, "austenite_grains.png")
        )
        save_csv(a_data, os.path.join(args.out_dir, "austenite_grain_stats.csv"))

    # ── Combined Deliverables ──────────────────────────────────────────────────
    all_grains = f_data + a_data
    if all_grains:
        save_csv(all_grains, os.path.join(args.out_dir, "all_grains_stats.csv"))

    if args.phase == "both" and f_data and a_data:
        plot_combined_dashboard(
            f_data, a_data, f_map, a_map,
            os.path.join(args.out_dir, "grain_size_summary.png")
        )
        plot_cdf(
            f_data, a_data,
            os.path.join(args.out_dir, "grain_size_cdf.png")
        )
        plot_shape_descriptors(
            f_data, a_data,
            os.path.join(args.out_dir, "shape_descriptors_scatter.png")
        )
        plot_boundaries_overlay(
            args.iq, f_bounds, a_bounds, pred_mask,
            os.path.join(args.out_dir, "grain_boundaries_overlay.png")
        )

    # ── Text & JSON Reports ───────────────────────────────────────────────────
    write_report(
        f_sum, a_sum, args.scale, args.mask, args.min_area,
        os.path.join(args.out_dir, "grain_size_report.txt")
    )

    summary_json = {
        "metadata": {
            "mask_path": args.mask,
            "iq_path": args.iq,
            "scale_um_per_px": args.scale,
            "min_area_px": args.min_area,
            "image_dimensions": list(pred_mask.shape),
        },
        "ferrite": f_sum,
        "austenite": a_sum,
    }
    json_path = os.path.join(args.out_dir, "grain_size_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)
    print("  JSON  ->", json_path)

    print("\n[OK] Grain Size Analysis Completed Successfully.")
    print(f"  All deliverables saved in: {args.out_dir}")


if __name__ == "__main__":
    main()