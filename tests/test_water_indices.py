"""Unit tests for NDWI calculation and water classification."""

import numpy as np
import pytest
from src.water_indices import classify_water, compute_ndwi_array


def test_ndwi_formula_correctness():
    # Clear water: high green reflectance, very low NIR reflectance
    # Green = 0.20, NIR = 0.05 -> (0.20 - 0.05) / (0.20 + 0.05) = 0.15 / 0.25 = 0.60
    b03 = np.array([[2000, 1000]], dtype=np.uint16)
    b08 = np.array([[500, 4000]], dtype=np.uint16)

    ndwi, valid = compute_ndwi_array(b03, b08)
    assert valid[0, 0] is np.True_
    assert np.isclose(ndwi[0, 0], (2000 - 500) / (2000 + 500), atol=1e-4)

    # Dense vegetation: low green, high NIR -> negative NDWI
    assert np.isclose(ndwi[0, 1], (1000 - 4000) / (1000 + 4000), atol=1e-4)
    assert ndwi[0, 1] < 0.0


def test_zero_denominator_and_nodata_handling():
    # Zero in both bands (nodata or total dark pixel)
    b03 = np.array([[0, 1500]], dtype=np.float32)
    b08 = np.array([[0, 1500]], dtype=np.float32)

    ndwi, valid = compute_ndwi_array(b03, b08, nodata_val=0.0)
    assert not valid[0, 0]
    assert np.isnan(ndwi[0, 0])

    # Equal reflectance -> NDWI = 0.0
    assert valid[0, 1]
    assert np.isclose(ndwi[0, 1], 0.0)


def test_water_classification():
    ndwi = np.array([-0.3, 0.0, 0.05, 0.45, np.nan], dtype=np.float32)
    valid = ~np.isnan(ndwi)

    # Threshold = 0.0
    mask_0 = classify_water(ndwi, valid, threshold=0.0)
    assert np.array_equal(mask_0, [False, False, True, True, False])

    # Configurable threshold = 0.1
    mask_custom = classify_water(ndwi, valid, threshold=0.1)
    assert np.array_equal(mask_custom, [False, False, False, True, False])


def test_shape_mismatch_error():
    b03 = np.ones((10, 10))
    b08 = np.ones((10, 12))
    with pytest.raises(ValueError, match="Shape mismatch"):
        compute_ndwi_array(b03, b08)
