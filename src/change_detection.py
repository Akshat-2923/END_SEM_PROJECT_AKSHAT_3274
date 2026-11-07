"""Change detection module comparing two Sentinel-2 water observations."""

import logging
from typing import Any, Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger("dhara_scope.change_detection")

LIMITATION_STATEMENT = (
    "Scientific Limitation Notice: Differences in NDWI-classified water-covered area reflect "
    "apparent surface water extent fluctuations. These fluctuations are primarily governed by "
    "seasonal precipitation, upstream dam releases, agricultural withdrawal, channel morphology, "
    "and riparian vegetation growth. NDWI-based area changes do NOT independently establish "
    "permanent water loss, environmental degradation, or river pollution without calibrated in-situ "
    "hydrological gauging, bathymetric surveys, and water quality sampling."
)


def compute_water_change(
    water_mask_t1: np.ndarray,
    water_mask_t2: np.ndarray,
    valid_mask_t1: np.ndarray,
    valid_mask_t2: np.ndarray,
    pixel_area_m2: float = 100.0
) -> Dict[str, Any]:
    """Compare two observation dates and compute water area statistics and change classes.

    Change Classification Scheme:
        0: Non-water (non-water at both dates)
        1: Persistent water (water at both T1 and T2)
        2: Apparent water loss / recession (water at T1, non-water at T2)
        3: Apparent water gain / expansion (non-water at T1, water at T2)
        255: Invalid / Nodata (invalid on either date)

    Args:
        water_mask_t1: Boolean water mask for earlier date.
        water_mask_t2: Boolean water mask for later date.
        valid_mask_t1: Boolean valid pixel mask for earlier date.
        valid_mask_t2: Boolean valid pixel mask for later date.
        pixel_area_m2: Spatial resolution area per pixel in m^2 (default 100m^2 for 10m).

    Returns:
        Dict with change_matrix, area statistics (m2, ha), absolute and percent changes, and limitations.
    """
    if water_mask_t1.shape != water_mask_t2.shape:
        raise ValueError(
            f"Spatial dimension mismatch: T1 shape {water_mask_t1.shape} != T2 shape {water_mask_t2.shape}. "
            "Both rasters must be aligned to the identical extent, resolution, and grid."
        )

    # Establish strictly identical comparison domain
    common_valid = valid_mask_t1 & valid_mask_t2
    total_valid_pixels = int(np.count_nonzero(common_valid))

    if total_valid_pixels == 0:
        logger.warning("No overlapping valid pixels found between observations.")
        return {
            "error": "No common valid pixels between observations",
            "limitation_statement": LIMITATION_STATEMENT
        }

    # Constrain water masks to common valid pixels
    w1 = water_mask_t1 & common_valid
    w2 = water_mask_t2 & common_valid

    count_w1 = int(np.count_nonzero(w1))
    count_w2 = int(np.count_nonzero(w2))

    area_t1_m2 = count_w1 * pixel_area_m2
    area_t1_ha = area_t1_m2 / 10000.0

    area_t2_m2 = count_w2 * pixel_area_m2
    area_t2_ha = area_t2_m2 / 10000.0

    abs_change_m2 = area_t2_m2 - area_t1_m2
    abs_change_ha = area_t2_ha - area_t1_ha

    if area_t1_m2 > 0:
        pct_change = (abs_change_m2 / area_t1_m2) * 100.0
    else:
        pct_change = None
        logger.warning("Baseline T1 water area is 0 m2; percentage change cannot be computed safely.")

    # Categorize changes
    persistent_mask = w1 & w2
    loss_mask = w1 & (~w2)
    gain_mask = (~w1) & w2
    non_water_mask = (~w1) & (~w2) & common_valid

    count_persistent = int(np.count_nonzero(persistent_mask))
    count_loss = int(np.count_nonzero(loss_mask))
    count_gain = int(np.count_nonzero(gain_mask))

    change_matrix = np.full(water_mask_t1.shape, 255, dtype=np.uint8)
    change_matrix[non_water_mask] = 0
    change_matrix[persistent_mask] = 1
    change_matrix[loss_mask] = 2
    change_matrix[gain_mask] = 3

    stats = {
        "comparison_pixels": {
            "total_pixels": int(water_mask_t1.size),
            "common_valid_pixels": total_valid_pixels,
            "common_valid_area_ha": round((total_valid_pixels * pixel_area_m2) / 10000.0, 2),
            "pixel_size_m2": pixel_area_m2
        },
        "water_area_earlier_t1": {
            "pixels": count_w1,
            "area_m2": round(area_t1_m2, 2),
            "area_hectares": round(area_t1_ha, 4)
        },
        "water_area_later_t2": {
            "pixels": count_w2,
            "area_m2": round(area_t2_m2, 2),
            "area_hectares": round(area_t2_ha, 4)
        },
        "change_metrics": {
            "absolute_change_m2": round(abs_change_m2, 2),
            "absolute_change_hectares": round(abs_change_ha, 4),
            "percentage_change": round(pct_change, 2) if pct_change is not None else None,
            "persistent_water_m2": round(count_persistent * pixel_area_m2, 2),
            "persistent_water_hectares": round((count_persistent * pixel_area_m2) / 10000.0, 4),
            "apparent_loss_m2": round(count_loss * pixel_area_m2, 2),
            "apparent_loss_hectares": round((count_loss * pixel_area_m2) / 10000.0, 4),
            "apparent_gain_m2": round(count_gain * pixel_area_m2, 2),
            "apparent_gain_hectares": round((count_gain * pixel_area_m2) / 10000.0, 4)
        },
        "limitation_statement": LIMITATION_STATEMENT
    }

    return {
        "change_matrix": change_matrix,
        "common_valid_mask": common_valid,
        "statistics": stats
    }
