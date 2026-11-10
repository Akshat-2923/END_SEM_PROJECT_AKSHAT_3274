"""Area of Interest (AOI) service layer handling validation, persistence, and access control."""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.aoi_validation import AOIValidationError, validate_aoi_polygon
from src.auth import AuthenticatedUser
from src.database.models.aoi import AOI


def aoi_to_dict(aoi: AOI) -> Dict[str, Any]:
    """Convert an AOI database entity into an API response dictionary with GeoJSON geometry."""
    try:
        geom_shape = to_shape(aoi.geometry)
        geojson_geom = mapping(geom_shape)
    except Exception:
        # Fallback if geometry is already dict or WKT
        geojson_geom = {"type": "Polygon", "coordinates": []}

    return {
        "id": aoi.id,
        "user_id": aoi.user_id,
        "name": aoi.name,
        "description": aoi.description,
        "geometry": geojson_geom,
        "area_km2": aoi.area_km2,
        "area_hectares": aoi.area_hectares,
        "bbox": aoi.bbox,
        "centroid": aoi.centroid,
        "vertex_count": aoi.vertex_count,
        "is_public": aoi.is_public,
        "created_at": aoi.created_at,
        "updated_at": aoi.updated_at,
    }


def validate_geometry(
    geometry_input: Any,
    min_area_km2: Optional[float] = None,
    max_area_km2: Optional[float] = None,
    max_vertices: Optional[int] = None,
) -> Dict[str, Any]:
    """Validate incoming geometry without persisting."""
    kwargs = {}
    if min_area_km2 is not None:
        kwargs["min_area_km2"] = min_area_km2
    if max_area_km2 is not None:
        kwargs["max_area_km2"] = max_area_km2
    if max_vertices is not None:
        kwargs["max_vertices"] = max_vertices

    return validate_aoi_polygon(geometry_input, **kwargs)


def create_aoi(
    session: Session,
    user: AuthenticatedUser,
    name: str,
    geometry_input: Any,
    description: Optional[str] = None,
    is_public: bool = False,
) -> AOI:
    """Validate geometry and create a new persisted AOI for the authenticated user."""
    v_res = validate_aoi_polygon(geometry_input)
    shapely_geom = v_res["shapely_geometry"]

    aoi = AOI(
        user_id=user.id,
        name=name.strip(),
        description=description.strip() if description else None,
        geometry=WKTElement(shapely_geom.wkt, srid=4326),
        area_km2=v_res["area_km2"],
        area_hectares=v_res["area_hectares"],
        bbox=v_res["bbox"],
        centroid=v_res["centroid"],
        vertex_count=v_res["vertex_count"],
        is_public=is_public,
    )
    session.add(aoi)
    session.flush()
    return aoi


def get_aoi(session: Session, user: AuthenticatedUser, aoi_id: uuid.UUID) -> AOI:
    """Retrieve an AOI ensuring read permissions (owner, public, or admin)."""
    aoi = session.scalar(select(AOI).where(AOI.id == aoi_id))
    if aoi is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AOI with id '{aoi_id}' not found",
        )

    # Cross-user isolation check
    if not aoi.is_public and aoi.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AOI with id '{aoi_id}' not found",
        )

    return aoi


def list_aois(
    session: Session,
    user: AuthenticatedUser,
    limit: int = 50,
    offset: int = 0,
    public_only: bool = False,
) -> Tuple[List[AOI], int]:
    """List AOIs accessible to the authenticated user with pagination."""
    if public_only:
        stmt = select(AOI).where(AOI.is_public.is_(True))
        count_stmt = select(func.count(AOI.id)).where(AOI.is_public.is_(True))
    elif user.is_admin:
        stmt = select(AOI)
        count_stmt = select(func.count(AOI.id))
    else:
        condition = or_(AOI.user_id == user.id, AOI.is_public.is_(True))
        stmt = select(AOI).where(condition)
        count_stmt = select(func.count(AOI.id)).where(condition)

    total = session.scalar(count_stmt) or 0
    items = list(session.scalars(stmt.order_by(AOI.created_at.desc()).offset(offset).limit(limit)).all())
    return items, total


def update_aoi(
    session: Session,
    user: AuthenticatedUser,
    aoi_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> AOI:
    """Update metadata or visibility of an existing AOI (owner or admin only)."""
    aoi = get_aoi(session, user, aoi_id)

    # Write permission check: only the owner or admin may modify
    if aoi.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to modify this AOI",
        )

    if name is not None:
        aoi.name = name.strip()
    if description is not None:
        aoi.description = description.strip() if description else None
    if is_public is not None:
        aoi.is_public = is_public

    session.flush()
    return aoi


def delete_aoi(session: Session, user: AuthenticatedUser, aoi_id: uuid.UUID) -> None:
    """Delete an existing AOI (owner or admin only)."""
    aoi = get_aoi(session, user, aoi_id)

    # Delete permission check: only owner or admin
    if aoi.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete this AOI",
        )

    session.delete(aoi)
    session.flush()
