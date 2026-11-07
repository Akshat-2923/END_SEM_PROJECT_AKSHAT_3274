"""Unit tests for geographical Area of Interest (AOI) validation."""

import json
import math
import pytest
from shapely.geometry import Point, Polygon, MultiPolygon, box

from src.aoi_validation import (
    AOIValidationError,
    parse_geometry_input,
    validate_aoi_polygon,
)


def create_regular_polygon(center_lon: float, center_lat: float, radius_km: float, num_points: int) -> Polygon:
    """Helper to generate an approximate regular polygon in WGS84 for testing."""
    coords = []
    # 1 deg lat ~ 111 km, 1 deg lon ~ 111 km * cos(lat)
    lat_scale = radius_km / 111.0
    lon_scale = radius_km / (111.0 * math.cos(math.radians(center_lat)))

    for i in range(num_points):
        angle = 2.0 * math.pi * i / num_points
        lon = center_lon + lon_scale * math.cos(angle)
        lat = center_lat + lat_scale * math.sin(angle)
        coords.append((round(lon, 6), round(lat, 6)))
    coords.append(coords[0])
    return Polygon(coords)


class TestAOIValidation:
    """Test suite for AOI geometry parsing and validation."""

    def test_valid_bbox_input(self):
        """Test a standard 4-element bounding box covering ~4 km²."""
        # 0.02 deg lon x 0.02 deg lat at lat 26.85 is ~2.0 km x 2.2 km ~ 4.4 km²
        bbox = [80.90, 26.84, 80.92, 26.86]
        result = validate_aoi_polygon(bbox)

        assert result["valid"] is True
        assert result["geometry_type"] == "Polygon"
        assert result["bbox"] == [80.90, 26.84, 80.92, 26.86]
        assert 3.0 < result["area_km2"] < 6.0
        assert result["vertex_count"] == 5

    def test_valid_geojson_polygon_dict(self):
        """Test validation with a GeoJSON Polygon dictionary."""
        geojson_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [80.90, 26.84],
                    [80.92, 26.84],
                    [80.92, 26.86],
                    [80.90, 26.86],
                    [80.90, 26.84],
                ]
            ],
        }
        res = validate_aoi_polygon(geojson_poly)
        assert res["valid"] is True
        assert res["area_km2"] > 0.1
        assert res["geometry"]["type"] == "Polygon"

    def test_valid_geojson_feature_and_collection(self):
        """Test GeoJSON Feature and FeatureCollection input parsing."""
        feature = {
            "type": "Feature",
            "properties": {"name": "Gomti Test Sub-reach"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [80.90, 26.84],
                        [80.92, 26.84],
                        [80.92, 26.86],
                        [80.90, 26.86],
                        [80.90, 26.84],
                    ]
                ],
            },
        }
        res_feat = validate_aoi_polygon(feature)
        assert res_feat["valid"] is True

        feature_coll = {
            "type": "FeatureCollection",
            "features": [feature],
        }
        res_coll = validate_aoi_polygon(feature_coll)
        assert res_coll["valid"] is True
        assert res_coll["centroid"] is not None

    def test_valid_json_string(self):
        """Test GeoJSON passed as serialized JSON string."""
        raw_json = json.dumps(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [80.90, 26.84],
                        [80.92, 26.84],
                        [80.92, 26.86],
                        [80.90, 26.86],
                        [80.90, 26.84],
                    ]
                ],
            }
        )
        res = validate_aoi_polygon(raw_json)
        assert res["valid"] is True

    def test_valid_shapely_polygon_and_multipolygon(self):
        """Test direct Shapely geometry objects."""
        poly1 = box(80.90, 26.84, 80.91, 26.85)
        poly2 = box(80.92, 26.85, 80.93, 26.86)
        mpoly = MultiPolygon([poly1, poly2])

        res = validate_aoi_polygon(mpoly)
        assert res["valid"] is True
        assert res["geometry_type"] == "MultiPolygon"
        assert res["area_km2"] > 0.1

    def test_minimum_area_violation(self):
        """Test rejection when area is below minimum threshold (<0.1 km²)."""
        # Very tiny polygon: 0.0005 deg ~ 50m x 50m ~ 0.0025 km²
        tiny_bbox = [80.900, 26.840, 80.9005, 26.8405]
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(tiny_bbox, min_area_km2=0.10)
        assert "below the minimum threshold of 0.10 km²" in str(exc_info.value)

    def test_maximum_area_violation(self):
        """Test rejection when area exceeds maximum threshold (>100 km²)."""
        # Gomti default bbox: [80.88, 26.80, 81.00, 26.90] is ~132.3 km²
        gomti_bbox = [80.88, 26.80, 81.00, 26.90]
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(gomti_bbox, max_area_km2=100.0)
        assert "exceeds the maximum threshold of 100.00 km²" in str(exc_info.value)

    def test_configurable_area_thresholds(self):
        """Verify that bounds are configurable."""
        gomti_bbox = [80.88, 26.80, 81.00, 26.90]
        # Gomti bbox is ~132.3 km²; with max_area_km2=150.0 it should pass cleanly
        res = validate_aoi_polygon(gomti_bbox, max_area_km2=150.0)
        assert res["valid"] is True
        assert 130.0 < res["area_km2"] < 135.0

    def test_self_intersecting_polygon_rejected(self):
        """Test rejection of self-intersecting (figure-8 / bowtie) geometry."""
        bowtie_coords = [
            (80.90, 26.84),
            (80.92, 26.86),
            (80.90, 26.86),
            (80.92, 26.84),
            (80.90, 26.84),
        ]
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(bowtie_coords)
        assert "topological errors" in str(exc_info.value).lower()
        assert "self-intersection" in str(exc_info.value).lower()

    def test_coordinate_out_of_wgs84_bounds(self):
        """Test rejection of latitude or longitude outside standard bounds."""
        invalid_lon = [185.0, 26.84, 186.0, 26.86]
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(invalid_lon)
        assert "Longitude coordinates out of WGS84 bounds" in str(exc_info.value)

        invalid_lat = [80.90, -95.0, 80.92, -94.0]
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(invalid_lat)
        assert "Latitude coordinates out of WGS84 bounds" in str(exc_info.value)

    def test_inverted_bbox_rejected(self):
        """Test rejection of min_lon >= max_lon or min_lat >= max_lat."""
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon([81.00, 26.80, 80.88, 26.90])
        assert "min_lon" in str(exc_info.value)

        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon([80.88, 26.90, 81.00, 26.80])
        assert "min_lat" in str(exc_info.value)

    def test_vertex_count_ceiling_enforced(self):
        """Test that high-complexity polygons (> 500 vertices) are rejected."""
        # Create a circle with 550 vertices (radius 1 km, area ~3.14 km²)
        complex_poly = create_regular_polygon(80.91, 26.85, radius_km=1.0, num_points=550)
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(complex_poly, max_vertices=500)
        assert "complexity exceeded" in str(exc_info.value)
        assert "exceeding maximum permissible limit of 500 vertices" in str(exc_info.value)

    def test_configurable_vertex_limit(self):
        """Test that vertex limit is configurable."""
        # 16-point polygon (17 vertices with closure)
        poly = create_regular_polygon(80.91, 26.85, radius_km=1.0, num_points=16)
        # Should fail with max_vertices=10
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon(poly, max_vertices=10)
        assert "exceeding maximum permissible limit of 10 vertices" in str(exc_info.value)

        # Should pass with max_vertices=20
        res = validate_aoi_polygon(poly, max_vertices=20)
        assert res["valid"] is True

    def test_unsupported_geometry_types(self):
        """Test rejection of Point, LineString, and malformed inputs."""
        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon({"type": "Point", "coordinates": [80.90, 26.84]})
        assert "Unsupported geometry type" in str(exc_info.value)

        with pytest.raises(AOIValidationError) as exc_info:
            validate_aoi_polygon("not a json string")
        assert "Invalid JSON string" in str(exc_info.value)

    def test_invalid_validation_arguments(self):
        """Test parameter sanity checks for min/max area and vertex arguments."""
        poly = box(80.90, 26.84, 80.92, 26.86)
        with pytest.raises(ValueError):
            validate_aoi_polygon(poly, min_area_km2=-1.0)

        with pytest.raises(ValueError):
            validate_aoi_polygon(poly, min_area_km2=50.0, max_area_km2=10.0)

        with pytest.raises(ValueError):
            validate_aoi_polygon(poly, max_vertices=2)
