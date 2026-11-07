"""Water index calculation and thresholding module for Sentinel-2 imagery."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
from shapely.geometry import box, mapping

from src.config import DEFAULT_NDWI_THRESHOLD, GOMTI_BBOX

logger = logging.getLogger("dhara_scope.water_indices")


class RasterProcessingError(Exception):
    """Raised when raster reading, alignment, or indexing fails."""
    pass


def compute_ndwi_array(
    b03: np.ndarray,
    b08: np.ndarray,
    nodata_val: Optional[float] = 0.0
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute Normalized Difference Water Index (NDWI) from Green and NIR arrays.

    NDWI = (B03 - B08) / (B03 + B08)  [McFeeters, 1996]

    Args:
        b03: Green band reflectance array.
        b08: NIR band reflectance array.
        nodata_val: Value representing nodata (Sentinel-2 L2A default is 0).

    Returns:
        Tuple of (ndwi_array, valid_mask):
            - ndwi_array: float32 array with NDWI values in [-1.0, 1.0], NaN for invalid.
            - valid_mask: bool array indicating valid, non-nodata pixels with non-zero denominator.
    """
    if b03.shape != b08.shape:
        raise ValueError(f"Shape mismatch: B03 shape {b03.shape} != B08 shape {b08.shape}")

    # Convert to float to avoid integer overflow / division issues
    green = b03.astype(np.float32)
    nir = b08.astype(np.float32)

    # Detect invalid pixels (NaNs or explicit nodata)
    invalid_mask = np.isnan(green) | np.isnan(nir)
    if nodata_val is not None:
        invalid_mask |= (green == nodata_val) & (nir == nodata_val)

    numerator = green - nir
    denominator = green + nir

    # Mask zero denominator to prevent division by zero
    zero_denom_mask = denominator <= 1e-6
    invalid_mask |= zero_denom_mask

    # Safe division using np.where
    ndwi = np.full(green.shape, np.nan, dtype=np.float32)
    valid_mask = ~invalid_mask

    np.divide(numerator, denominator, out=ndwi, where=valid_mask)
    # Clamp within physical NDWI range [-1, 1] for valid pixels
    np.clip(ndwi, -1.0, 1.0, out=ndwi, where=valid_mask)

    return ndwi, valid_mask


def classify_water(
    ndwi: np.ndarray,
    valid_mask: np.ndarray,
    threshold: float = DEFAULT_NDWI_THRESHOLD
) -> np.ndarray:
    """Classify water pixels based on a configurable NDWI threshold.

    Args:
        ndwi: NDWI float array.
        valid_mask: Boolean mask of valid pixels.
        threshold: NDWI cutoff threshold (typically 0.0, but site-dependent).

    Returns:
        Boolean array where True indicates water and False indicates non-water / invalid.
    """
    water_mask = (ndwi > threshold) & valid_mask
    return water_mask


def process_scene_bands(
    b03_path: Union[str, Path],
    b08_path: Union[str, Path],
    clip_bbox: Optional[List[float]] = None,
    threshold: float = DEFAULT_NDWI_THRESHOLD
) -> Dict[str, Any]:
    """Load B03 and B08 rasters, clip to study bbox, calculate NDWI, and classify water.

    Args:
        b03_path: Path to B03 Green raster (JP2 or TIF).
        b08_path: Path to B08 NIR raster (JP2 or TIF).
        clip_bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84 EPSG:4326.
        threshold: Water classification threshold.

    Returns:
        Dict containing ndwi, water_mask, valid_mask, profile, and spatial metadata.
    """
    b03_p = Path(b03_path)
    b08_p = Path(b08_path)

    if not b03_p.exists():
        raise RasterProcessingError(f"B03 raster not found: {b03_p}")
    if not b08_p.exists():
        raise RasterProcessingError(f"B08 raster not found: {b08_p}")

    clip_bounds = clip_bbox or GOMTI_BBOX
    geom_wgs84 = box(*clip_bounds)

    logger.info("Processing scene: B03=%s, B08=%s", b03_p.name, b08_p.name)

    with rasterio.open(b03_p) as src_green, rasterio.open(b08_p) as src_nir:
        if src_green.crs != src_nir.crs:
            raise RasterProcessingError(
                f"CRS mismatch between bands: B03 is {src_green.crs}, B08 is {src_nir.crs}"
            )
        if src_green.res != src_nir.res:
            raise RasterProcessingError(
                f"Resolution mismatch between bands: B03 is {src_green.res}, B08 is {src_nir.res}"
            )

        # Reproject study bounding box into raster's native projected CRS (e.g. UTM 44N)
        utm_bounds = transform_bounds(
            CRS.from_epsg(4326),
            src_green.crs,
            clip_bounds[0], clip_bounds[1], clip_bounds[2], clip_bounds[3]
        )
        clip_polygon = box(*utm_bounds)
        shapes = [mapping(clip_polygon)]

        # Mask/clip both bands to identical study area
        try:
            green_data, green_transform = mask(src_green, shapes, crop=True, nodata=src_green.nodata or 0)
            nir_data, nir_transform = mask(src_nir, shapes, crop=True, nodata=src_nir.nodata or 0)
        except ValueError as exc:
            raise RasterProcessingError(f"Clipping bounding box does not overlap raster: {exc}") from exc

        # Extract 2D array (first band)
        green_arr = green_data[0]
        nir_arr = nir_data[0]
        nodata_val = src_green.nodata

        profile = src_green.profile.copy()
        profile.update({
            "height": green_arr.shape[0],
            "width": green_arr.shape[1],
            "transform": green_transform,
            "count": 1,
            "dtype": rasterio.float32,
            "nodata": np.nan
        })

    ndwi, valid_mask = compute_ndwi_array(green_arr, nir_arr, nodata_val=nodata_val)
    water_mask = classify_water(ndwi, valid_mask, threshold=threshold)

    pixel_width = abs(profile["transform"][0])
    pixel_height = abs(profile["transform"][4])
    pixel_area_m2 = pixel_width * pixel_height

    return {
        "ndwi": ndwi,
        "water_mask": water_mask,
        "valid_mask": valid_mask,
        "profile": profile,
        "pixel_area_m2": pixel_area_m2,
        "threshold_used": threshold,
        "crs": str(profile["crs"]),
        "shape": ndwi.shape,
        "clip_bbox": clip_bounds
    }
