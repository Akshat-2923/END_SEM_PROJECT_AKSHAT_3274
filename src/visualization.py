"""Visualization module for DharaScope water index and change analysis."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np

from src.config import OUTPUTS_DIR

logger = logging.getLogger("dhara_scope.visualization")


def plot_single_observation(
    ndwi: np.ndarray,
    water_mask: np.ndarray,
    date_str: str,
    scene_id: str,
    output_path: Path,
    provenance_label: Optional[str] = None
) -> Path:
    """Generate and save dual-panel visualization for an observation: NDWI continuous + Water Mask."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    badge = f"\n[{provenance_label}]" if provenance_label else ""

    # Panel 1: NDWI
    im1 = axes[0].imshow(ndwi, cmap="coolwarm_r", vmin=-0.8, vmax=0.8)
    axes[0].set_title(
        f"NDWI Index - {date_str}\n{scene_id[:35]}...{badge}",
        fontsize=10,
        fontweight="bold"
    )
    axes[0].set_xlabel("Column (Pixels, 10m)")
    axes[0].set_ylabel("Row (Pixels, 10m)")
    cbar1 = fig.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
    cbar1.set_label("NDWI: (Green - NIR) / (Green + NIR)")

    # Panel 2: Classified Water Mask
    cmap_mask = ListedColormap(["#dcdcdc", "#1f77b4"])
    im2 = axes[1].imshow(water_mask.astype(int), cmap=cmap_mask, vmin=0, vmax=1)
    water_pixels = int(np.count_nonzero(water_mask))
    water_ha = (water_pixels * 100.0) / 10000.0
    axes[1].set_title(
        f"Classified Water Mask (NDWI > 0.0)\nWater Extent: {water_ha:.2f} ha ({water_pixels:,} px){badge}",
        fontsize=10,
        fontweight="bold"
    )
    axes[1].set_xlabel("Column (Pixels, 10m)")
    axes[1].set_ylabel("Row (Pixels, 10m)")
    cbar2 = fig.colorbar(im2, ax=axes[1], ticks=[0.25, 0.75], fraction=0.046, pad=0.04)
    cbar2.ax.set_yticklabels(["Non-Water", "Water"])

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved observation plot to %s", output_path)
    return output_path


def plot_water_change_map(
    change_matrix: np.ndarray,
    stats: Dict[str, Any],
    date_t1: str,
    date_t2: str,
    output_path: Path,
    provenance_label: Optional[str] = None
) -> Path:
    """Generate and save comprehensive water change map."""
    fig, ax = plt.subplots(figsize=(10, 8))

    cmap = ListedColormap(["#f0f0f0", "#0055ff", "#e63946", "#2a9d8f", "#bbbbbb"])
    bounds = [-0.5, 0.5, 1.5, 2.5, 3.5, 256.0]
    norm = BoundaryNorm(bounds, cmap.N)

    mapped = change_matrix.copy()
    mapped[mapped == 255] = 4

    im = ax.imshow(mapped, cmap=cmap, norm=norm)

    ch_m = stats.get("change_metrics", {})
    t1_m = stats.get("water_area_earlier_t1", {})
    t2_m = stats.get("water_area_later_t2", {})

    badge = f" — [{provenance_label}]" if provenance_label else ""
    title = (
        f"Gomti River Water Extent Change: {date_t1} -> {date_t2}{badge}\n"
        f"Net Change: {ch_m.get('absolute_change_hectares', 0):+.2f} ha "
        f"({ch_m.get('percentage_change', 0):+.1f}%)"
    )
    ax.set_title(title, fontsize=11, fontweight="bold", pad=12)
    ax.set_xlabel("Easting / Columns (10m pixels)")
    ax.set_ylabel("Northing / Rows (10m pixels)")

    # Custom Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#f0f0f0", edgecolor="gray", label="Non-Water (Both dates)"),
        Patch(facecolor="#0055ff", edgecolor="gray",
              label=f"Persistent Water ({ch_m.get('persistent_water_hectares', 0):.2f} ha)"),
        Patch(facecolor="#e63946", edgecolor="gray",
              label=f"Apparent Water Loss / Recession ({ch_m.get('apparent_loss_hectares', 0):.2f} ha)"),
        Patch(facecolor="#2a9d8f", edgecolor="gray",
              label=f"Apparent Water Gain / Expansion ({ch_m.get('apparent_gain_hectares', 0):.2f} ha)"),
        Patch(facecolor="#bbbbbb", edgecolor="gray", label="Nodata / Invalid")
    ]
    ax.legend(handles=legend_elements, loc="upper right", framealpha=0.9, fontsize=9)

    # Subtitle disclaimer at bottom
    disclaimer = (
        "Disclaimer: NDWI difference reflects apparent surface water variations; "
        "does not independently establish pollution or permanent loss."
    )
    if provenance_label and "SYNTHETIC" in provenance_label:
        disclaimer = "DEMO NOTICE: SYNTHETIC SAMPLE BENCHMARK DATA. FOR OFFLINE ALGORITHM VERIFICATION ONLY."

    fig.text(
        0.5, 0.01,
        disclaimer,
        ha="center", fontsize=8, style="italic", color="#444444"
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved water change map to %s", output_path)
    return output_path


def plot_four_panel_comparison(
    ndwi_t1: np.ndarray,
    water_t1: np.ndarray,
    date_t1: str,
    ndwi_t2: np.ndarray,
    water_t2: np.ndarray,
    date_t2: str,
    change_matrix: np.ndarray,
    stats: Dict[str, Any],
    output_path: Path,
    provenance_label: Optional[str] = None
) -> Path:
    """Generate complete 4-panel comparison figure."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))

    # (0,0) T1 NDWI
    im00 = axes[0, 0].imshow(ndwi_t1, cmap="coolwarm_r", vmin=-0.8, vmax=0.8)
    axes[0, 0].set_title(f"(A) NDWI Index: Earlier Observation ({date_t1})", fontweight="bold")
    fig.colorbar(im00, ax=axes[0, 0], fraction=0.046, pad=0.04)

    # (0,1) T2 NDWI
    im01 = axes[0, 1].imshow(ndwi_t2, cmap="coolwarm_r", vmin=-0.8, vmax=0.8)
    axes[0, 1].set_title(f"(B) NDWI Index: Later Observation ({date_t2})", fontweight="bold")
    fig.colorbar(im01, ax=axes[0, 1], fraction=0.046, pad=0.04)

    # (1,0) T1 vs T2 Water Masks Overlay
    overlay = np.zeros(water_t1.shape, dtype=np.uint8)
    overlay[water_t1 & (~water_t2)] = 1
    overlay[(~water_t1) & water_t2] = 2
    overlay[water_t1 & water_t2] = 3
    cmap_ov = ListedColormap(["#f7f7f7", "#e63946", "#2a9d8f", "#0055ff"])
    im10 = axes[1, 0].imshow(overlay, cmap=cmap_ov, vmin=0, vmax=3)
    axes[1, 0].set_title("(C) Water Masks Comparison", fontweight="bold")
    from matplotlib.patches import Patch
    leg_ov = [
        Patch(facecolor="#f7f7f7", edgecolor="gray", label="Non-Water"),
        Patch(facecolor="#0055ff", label=f"Both Dates ({date_t1} & {date_t2})"),
        Patch(facecolor="#e63946", label=f"Water in {date_t1} only"),
        Patch(facecolor="#2a9d8f", label=f"Water in {date_t2} only")
    ]
    axes[1, 0].legend(handles=leg_ov, loc="upper right", fontsize=8)

    # (1,1) Change Matrix Map
    cmap_ch = ListedColormap(["#f0f0f0", "#0055ff", "#e63946", "#2a9d8f", "#bbbbbb"])
    mapped = change_matrix.copy()
    mapped[mapped == 255] = 4
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], 5)
    im11 = axes[1, 1].imshow(mapped, cmap=cmap_ch, norm=norm)
    ch = stats.get("change_metrics", {})
    axes[1, 1].set_title(
        f"(D) Water-Covered Area Change Map\n"
        f"Net: {ch.get('absolute_change_hectares', 0):+.2f} ha ({ch.get('percentage_change', 0):+.1f}%)",
        fontweight="bold"
    )
    leg_ch = [
        Patch(facecolor="#0055ff", label=f"Persistent ({ch.get('persistent_water_hectares', 0):.2f} ha)"),
        Patch(facecolor="#e63946", label=f"Recession / Loss ({ch.get('apparent_loss_hectares', 0):.2f} ha)"),
        Patch(facecolor="#2a9d8f", label=f"Expansion / Gain ({ch.get('apparent_gain_hectares', 0):.2f} ha)")
    ]
    axes[1, 1].legend(handles=leg_ch, loc="upper right", fontsize=8)

    fig.suptitle(
        "DharaScope Phase 1: Gomti River (Lucknow) Satellite Feasibility Validation",
        fontsize=15, fontweight="bold", y=0.98
    )

    if provenance_label:
        if "SYNTHETIC" in provenance_label:
            fig.text(
                0.5, 0.945,
                "[DEMONSTRATION BENCHMARK: SYNTHETIC SAMPLE DATA — NOT REAL SATELLITE FINDINGS]",
                ha="center", fontsize=10, fontweight="bold", color="#b71c1c",
                bbox=dict(boxstyle="round,pad=0.4", fc="#ffebee", ec="#d32f2f", lw=1.5)
            )
        else:
            fig.text(
                0.5, 0.945,
                f"[{provenance_label}]",
                ha="center", fontsize=10, fontweight="bold", color="#1b5e20",
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec="#2e7d32", lw=1.2)
            )

    disclaimer = (
        "Notice: Differences in NDWI area reflect apparent surface water dynamics and do not independently establish pollution or permanent loss."
    )
    if provenance_label and "SYNTHETIC" in provenance_label:
        disclaimer = "DEMO NOTICE: SYNTHETIC SAMPLE BENCHMARK DATA. FOR OFFLINE ALGORITHM VERIFICATION ONLY. NOT REAL SATELLITE OBSERVATIONS."

    fig.text(
        0.5, 0.01,
        disclaimer,
        ha="center", fontsize=9, style="italic", color="#333333"
    )

    plt.tight_layout(rect=[0, 0.02, 1, 0.94 if provenance_label else 0.97])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved 4-panel comparison plot to %s", output_path)
    return output_path
