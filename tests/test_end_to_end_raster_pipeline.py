"""End-to-end integration test of raster processing, NDWI calculation, and visualization."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
from pathlib import Path

from src.water_indices import process_scene_bands
from src.change_detection import compute_water_change
from src.visualization import (
    plot_single_observation,
    plot_water_change_map,
    plot_four_panel_comparison,
)


@pytest.fixture
def synthetic_scenes(tmp_path):
    """Create paired synthetic Level-2A GeoTIFF rasters in UTM 44N (Lucknow area)."""
    # Coordinates in UTM zone 44N covering Lucknow ~ [686000, 2966000]
    crs = CRS.from_epsg(32644)
    transform = from_origin(686000, 2970000, 10, 10)  # 10m pixel size
    height, width = 120, 120

    # Scene 1: River channel in center with high Green, low NIR
    green_t1 = np.full((height, width), 1200, dtype=np.uint16)  # land background
    nir_t1 = np.full((height, width), 3500, dtype=np.uint16)    # vegetation background
    # River channel in middle 20 rows
    green_t1[50:70, :] = 2500
    nir_t1[50:70, :] = 400

    # Scene 2: River narrower (rows 55:65), representing summer low-flow / dry season
    green_t2 = np.full((height, width), 1200, dtype=np.uint16)
    nir_t2 = np.full((height, width), 3500, dtype=np.uint16)
    green_t2[55:65, :] = 2500
    nir_t2[55:65, :] = 400

    t1_b03 = tmp_path / "t1_b03.tif"
    t1_b08 = tmp_path / "t1_b08.tif"
    t2_b03 = tmp_path / "t2_b03.tif"
    t2_b08 = tmp_path / "t2_b08.tif"

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": rasterio.uint16,
        "crs": crs,
        "transform": transform,
        "nodata": 0
    }

    for path, data in [(t1_b03, green_t1), (t1_b08, nir_t1), (t2_b03, green_t2), (t2_b08, nir_t2)]:
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(data, 1)

    return {
        "t1_b03": t1_b03,
        "t1_b08": t1_b08,
        "t2_b03": t2_b03,
        "t2_b08": t2_b08,
        "tmp_dir": tmp_path
    }


def test_end_to_end_pipeline(synthetic_scenes):
    s = synthetic_scenes
    # Process T1 directly (without bbox clipping for test speed, or with bounds)
    with rasterio.open(s["t1_b03"]) as src_g, rasterio.open(s["t1_b08"]) as src_n:
        g1 = src_g.read(1)
        n1 = src_n.read(1)
        prof1 = src_g.profile

    with rasterio.open(s["t2_b03"]) as src_g, rasterio.open(s["t2_b08"]) as src_n:
        g2 = src_g.read(1)
        n2 = src_n.read(1)

    from src.water_indices import compute_ndwi_array, classify_water
    ndwi_1, val_1 = compute_ndwi_array(g1, n1)
    water_1 = classify_water(ndwi_1, val_1, threshold=0.0)

    ndwi_2, val_2 = compute_ndwi_array(g2, n2)
    water_2 = classify_water(ndwi_2, val_2, threshold=0.0)

    # In T1: rows 50:70 were water = 20 rows * 120 cols = 2400 pixels
    assert np.count_nonzero(water_1) == 2400
    # In T2: rows 55:65 were water = 10 rows * 120 cols = 1200 pixels
    assert np.count_nonzero(water_2) == 1200

    # Compute Change
    change_res = compute_water_change(water_1, water_2, val_1, val_2, pixel_area_m2=100.0)
    stats = change_res["statistics"]

    assert stats["water_area_earlier_t1"]["pixels"] == 2400
    assert stats["water_area_later_t2"]["pixels"] == 1200
    # Net change: -1200 pixels = -120,000 m^2 = -12.0 ha (-50.0%)
    assert stats["change_metrics"]["absolute_change_m2"] == -120000.0
    assert stats["change_metrics"]["absolute_change_hectares"] == -12.0
    assert stats["change_metrics"]["percentage_change"] == -50.0

    # Generate Visualizations
    out_dir = s["tmp_dir"] / "outputs"
    out_dir.mkdir(exist_ok=True)

    p1 = plot_single_observation(ndwi_1, water_1, "2023-12-24", "S2_T1", out_dir / "t1.png")
    assert p1.exists() and p1.stat().st_size > 1000

    p2 = plot_single_observation(ndwi_2, water_2, "2024-05-27", "S2_T2", out_dir / "t2.png")
    assert p2.exists() and p2.stat().st_size > 1000

    pch = plot_water_change_map(change_res["change_matrix"], stats, "2023-12-24", "2024-05-27", out_dir / "change.png")
    assert pch.exists() and pch.stat().st_size > 1000

    p_panel = plot_four_panel_comparison(
        ndwi_1, water_1, "2023-12-24",
        ndwi_2, water_2, "2024-05-27",
        change_res["change_matrix"], stats,
        out_dir / "panel.png"
    )
    assert p_panel.exists() and p_panel.stat().st_size > 1000
