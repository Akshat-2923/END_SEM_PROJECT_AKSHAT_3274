"""Unit tests for change detection and area metrics."""

import numpy as np
import pytest
from src.change_detection import compute_water_change, LIMITATION_STATEMENT


def test_change_matrix_and_area_metrics():
    # 4 pixels:
    # px 0: non-water -> non-water (class 0)
    # px 1: water -> water (persistent, class 1)
    # px 2: water -> non-water (apparent loss, class 2)
    # px 3: non-water -> water (apparent gain, class 3)
    w_t1 = np.array([False, True, True, False])
    w_t2 = np.array([False, True, False, True])
    val_t1 = np.array([True, True, True, True])
    val_t2 = np.array([True, True, True, True])

    # 10m x 10m pixels -> 100 m^2 each
    res = compute_water_change(w_t1, w_t2, val_t1, val_t2, pixel_area_m2=100.0)

    ch_mat = res["change_matrix"]
    assert np.array_equal(ch_mat, [0, 1, 2, 3])

    stats = res["statistics"]
    # T1: 2 pixels = 200 m^2 = 0.02 ha
    assert stats["water_area_earlier_t1"]["pixels"] == 2
    assert stats["water_area_earlier_t1"]["area_m2"] == 200.0
    assert stats["water_area_earlier_t1"]["area_hectares"] == 0.02

    # T2: 2 pixels = 200 m^2 = 0.02 ha
    assert stats["water_area_later_t2"]["pixels"] == 2
    assert stats["water_area_later_t2"]["area_m2"] == 200.0

    # Net change = 0.0 m^2, 0.0%
    assert stats["change_metrics"]["absolute_change_m2"] == 0.0
    assert stats["change_metrics"]["percentage_change"] == 0.0
    assert stats["change_metrics"]["persistent_water_m2"] == 100.0
    assert stats["change_metrics"]["apparent_loss_m2"] == 100.0
    assert stats["change_metrics"]["apparent_gain_m2"] == 100.0

    # Verify presence of limitation notice
    assert "Scientific Limitation Notice" in stats["limitation_statement"]


def test_zero_baseline_percentage_handling():
    # T1 has 0 water pixels, T2 has 5 water pixels
    w_t1 = np.zeros(10, dtype=bool)
    w_t2 = np.ones(10, dtype=bool)
    val = np.ones(10, dtype=bool)

    res = compute_water_change(w_t1, w_t2, val, val, pixel_area_m2=100.0)
    stats = res["statistics"]
    assert stats["water_area_earlier_t1"]["area_m2"] == 0.0
    assert stats["change_metrics"]["percentage_change"] is None
    assert stats["change_metrics"]["absolute_change_m2"] == 1000.0


def test_spatial_dimension_mismatch():
    w_t1 = np.zeros((10, 10), dtype=bool)
    w_t2 = np.zeros((10, 12), dtype=bool)
    val = np.ones((10, 10), dtype=bool)

    with pytest.raises(ValueError, match="Spatial dimension mismatch"):
        compute_water_change(w_t1, w_t2, val, val)
