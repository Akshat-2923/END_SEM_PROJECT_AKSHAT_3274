"""Geographical Area of Interest (AOI) Validation Module.

Enforces topological integrity, coordinate validity, vertex count limits,
and geographical area constraints (0.1–100 km²) using ellipsoidal equal-area
calculations via pyproj Geod and Shapely.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import pyproj
from shapely.geometry import Polygon, MultiPolygon, box, mapping, shape
from shapely.validation import explain_validity

from src.config import MAX_AOI_AREA_KM2, MAX_AOI_VERTICES, MIN_AOI_AREA_KM2

logger = logging.getLogger("dhara_scope.aoi_validation")


class AOIValidationError(Exception):
    """Custom exception raised for invalid geographical AOI geometries or bounds."""
    pass


def _calculate_geodetic_area(geom: Union[Polygon, MultiPolygon]) -> Tuple[float, float, float]:
    """Calculate geodetic surface area on WGS84 ellipsoid using pyproj.Geod.

    Args:
        geom: Shapely Polygon or MultiPolygon in WGS84 (EPSG:4326).

    Returns:
        Tuple of (area_m2, area_km2, area_hectares).
    """
    geod = pyproj.Geod(ellps="WGS84")
    total_area_m2 = 0.0

    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        raise AOIValidationError(f"Unsupported geometry type for area calculation: {geom.geom_type}")

    for poly in polygons:
        # geometry_area_perimeter returns signed (area, perimeter)
        area, _ = geod.geometry_area_perimeter(poly)
        total_area_m2 += abs(area)

    area_km2 = total_area_m2 / 1_000_000.0
    area_ha = total_area_m2 / 10_000.0
    return round(total_area_m2, 2), round(area_km2, 4), round(area_ha, 4)


def _count_vertices(geom: Union[Polygon, MultiPolygon]) -> int:
    """Count total vertices across exterior and all interior linear rings."""
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        return 0

    count = 0
    for poly in polygons:
        if poly.exterior:
            count += len(poly.exterior.coords)
        for interior in poly.interiors:
            count += len(interior.coords)
    return count


def _check_coordinate_bounds(geom: Union[Polygon, MultiPolygon]) -> None:
    """Verify that all coordinates fall strictly within WGS84 boundaries [-180, 180], [-90, 90]."""
    min_x, min_y, max_x, max_y = geom.bounds
    if min_x < -180.0 or max_x > 180.0:
        raise AOIValidationError(
            f"Longitude coordinates out of WGS84 bounds [-180, 180]: min={min_x}, max={max_x}"
        )
    if min_y < -90.0 or max_y > 90.0:
        raise AOIValidationError(
            f"Latitude coordinates out of WGS84 bounds [-90, 90]: min={min_y}, max={max_y}"
        )


def parse_geometry_input(
    geometry_input: Union[Dict[str, Any], str, List[float], List[Tuple[float, float]], Polygon, MultiPolygon]
) -> Union[Polygon, MultiPolygon]:
    """Parse various geometry input formats into a Shapely Polygon or MultiPolygon.

    Supports:
        - Shapely Polygon or MultiPolygon
        - Bounding box list: [min_lon, min_lat, max_lon, max_lat]
        - GeoJSON geometry dict: {"type": "Polygon", "coordinates": [...]}
        - GeoJSON Feature or FeatureCollection dict
        - JSON string of GeoJSON
        - Coordinate list: [(lon, lat), (lon, lat), ...]
    """
    if isinstance(geometry_input, (Polygon, MultiPolygon)):
        return geometry_input

    if isinstance(geometry_input, str):
        try:
            geometry_input = json.loads(geometry_input)
        except json.JSONDecodeError as exc:
            raise AOIValidationError(f"Invalid JSON string supplied for AOI geometry: {exc}") from exc

    if isinstance(geometry_input, (list, tuple)):
        # Check if 4-element bounding box
        if len(geometry_input) == 4 and all(isinstance(x, (int, float)) for x in geometry_input):
            min_x, min_y, max_x, max_y = [float(x) for x in geometry_input]
            if min_x >= max_x:
                raise AOIValidationError(f"Invalid bounding box: min_lon ({min_x}) >= max_lon ({max_x})")
            if min_y >= max_y:
                raise AOIValidationError(f"Invalid bounding box: min_lat ({min_y}) >= max_lat ({max_y})")
            return box(min_x, min_y, max_x, max_y)

        # Coordinate list [(lon, lat), ...]
        if len(geometry_input) >= 3 and all(isinstance(pt, (list, tuple)) and len(pt) >= 2 for pt in geometry_input):
            coords = [(float(pt[0]), float(pt[1])) for pt in geometry_input]
            try:
                return Polygon(coords)
            except Exception as exc:
                raise AOIValidationError(f"Failed to create polygon from coordinate list: {exc}") from exc

        raise AOIValidationError(
            "Geometry list must be a 4-element bounding box [min_lon, min_lat, max_lon, max_lat] "
            "or a coordinate ring with >= 3 points."
        )

    if isinstance(geometry_input, dict):
        # FeatureCollection
        if geometry_input.get("type") == "FeatureCollection":
            features = geometry_input.get("features", [])
            if not features:
                raise AOIValidationError("GeoJSON FeatureCollection contains no features.")
            geometry_input = features[0].get("geometry", {})

        # Feature
        if geometry_input.get("type") == "Feature":
            geometry_input = geometry_input.get("geometry", {})

        # Geometry dict
        geom_type = geometry_input.get("type")
        if geom_type not in ("Polygon", "MultiPolygon"):
            raise AOIValidationError(
                f"Unsupported geometry type '{geom_type}'. Only 'Polygon' or 'MultiPolygon' are supported."
            )

        try:
            geom = shape(geometry_input)
            if not isinstance(geom, (Polygon, MultiPolygon)):
                raise AOIValidationError(f"Parsed shape is not Polygon/MultiPolygon: {type(geom)}")
            return geom
        except Exception as exc:
            raise AOIValidationError(f"Failed to parse GeoJSON geometry: {exc}") from exc

    raise AOIValidationError(f"Unsupported geometry input type: {type(geometry_input)}")


def validate_aoi_polygon(
    geometry_input: Union[Dict[str, Any], str, List[float], List[Tuple[float, float]], Polygon, MultiPolygon],
    min_area_km2: float = MIN_AOI_AREA_KM2,
    max_area_km2: float = MAX_AOI_AREA_KM2,
    max_vertices: int = MAX_AOI_VERTICES,
) -> Dict[str, Any]:
    """Validate an Area of Interest (AOI) polygon against topological, coordinate, and area limits.

    Validation Rules:
        1. Coordinate bounds: All coordinates strictly within WGS84 range.
        2. Topology: Geometry must be non-empty and topologically valid according to OGC standards.
        3. Vertex count: Total vertices must not exceed `max_vertices` (default 500).
        4. Area limits: Ellipsoidal surface area must satisfy `min_area_km2 <= area <= max_area_km2`.

    Args:
        geometry_input: GeoJSON dict, Shapely Polygon, bbox [min_lon, min_lat, max_lon, max_lat], etc.
        min_area_km2: Minimum permissible area in km² (default 0.10).
        max_area_km2: Maximum permissible area in km² (default 100.00).
        max_vertices: Maximum allowed vertices (default 500).

    Returns:
        Structured dictionary containing validated GeoJSON geometry, bbox, centroid, and area metrics.

    Raises:
        AOIValidationError: If any validation rule is violated.
    """
    if min_area_km2 <= 0:
        raise ValueError(f"min_area_km2 must be positive: {min_area_km2}")
    if max_area_km2 <= min_area_km2:
        raise ValueError(f"max_area_km2 ({max_area_km2}) must be strictly greater than min_area_km2 ({min_area_km2})")
    if max_vertices < 4:
        raise ValueError(f"max_vertices must be at least 4: {max_vertices}")

    geom = parse_geometry_input(geometry_input)

    # 1. Non-empty check
    if geom.is_empty:
        raise AOIValidationError("AOI geometry is empty.")

    # 2. Coordinate range verification
    _check_coordinate_bounds(geom)

    # 3. Topological validity
    if not geom.is_valid:
        reason = explain_validity(geom)
        raise AOIValidationError(f"AOI geometry has topological errors: {reason}")

    # 4. Vertex count constraint
    vertex_count = _count_vertices(geom)
    if vertex_count > max_vertices:
        raise AOIValidationError(
            f"AOI geometry complexity exceeded: has {vertex_count} vertices, "
            f"exceeding maximum permissible limit of {max_vertices} vertices."
        )

    # 5. Geodetic Equal-Area measurement
    area_m2, area_km2, area_ha = _calculate_geodetic_area(geom)

    if area_km2 < min_area_km2:
        raise AOIValidationError(
            f"AOI surface area ({area_km2:.4f} km²) is below the minimum threshold of {min_area_km2:.2f} km² "
            f"({min_area_km2 * 1_000_000:,.0f} m²). Micro-polygons cannot be reliably evaluated at 10m pixel resolution."
        )

    if area_km2 > max_area_km2:
        raise AOIValidationError(
            f"AOI surface area ({area_km2:.2f} km²) exceeds the maximum threshold of {max_area_km2:.2f} km² "
            f"({max_area_km2 * 1_000_000:,.0f} m²). Please reduce the study reach size."
        )

    bounds = [round(float(coord), 6) for coord in geom.bounds]
    centroid = [round(float(geom.centroid.x), 6), round(float(geom.centroid.y), 6)]

    logger.info(
        "AOI validation SUCCESS: type=%s, area=%.2f km² (%.2f ha), vertices=%d, bbox=%s",
        geom.geom_type,
        area_km2,
        area_ha,
        vertex_count,
        bounds,
    )

    return {
        "valid": True,
        "geometry": mapping(geom),
        "shapely_geometry": geom,
        "bbox": bounds,
        "centroid": centroid,
        "area_m2": area_m2,
        "area_km2": area_km2,
        "area_hectares": area_ha,
        "vertex_count": vertex_count,
        "geometry_type": geom.geom_type,
    }
