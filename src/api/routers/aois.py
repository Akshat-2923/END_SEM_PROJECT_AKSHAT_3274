"""Area of Interest (AOI) management router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db_session
from src.api.schemas.aoi import (
    AOICreateRequest,
    AOIListResponse,
    AOIResponse,
    AOIUpdateRequest,
    AOIValidateRequest,
    AOIValidateResponse,
)
from src.auth import AuthenticatedUser, get_current_user
from src.services.aoi_service import (
    aoi_to_dict,
    create_aoi,
    delete_aoi,
    get_aoi,
    list_aois,
    update_aoi,
    validate_geometry,
)

router = APIRouter(prefix="/api/v1/aois", tags=["Area of Interest (AOI) Management"])


@router.post(
    "/validate",
    response_model=AOIValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Geographical AOI Geometry",
    description="Validate topology, coordinates, vertex count (<=500), and ellipsoidal area (0.10-100.00 km2).",
)
def validate_aoi_endpoint(
    payload: AOIValidateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AOIValidateResponse:
    """Validate geometry against topological and area limits without persisting."""
    res = validate_geometry(
        geometry_input=payload.geometry,
        min_area_km2=payload.min_area_km2,
        max_area_km2=payload.max_area_km2,
        max_vertices=payload.max_vertices,
    )
    return AOIValidateResponse(
        valid=res["valid"],
        geometry=res["geometry"],
        geometry_type=res["geometry_type"],
        bbox=res["bbox"],
        centroid=res["centroid"],
        area_m2=res["area_m2"],
        area_km2=res["area_km2"],
        area_hectares=res["area_hectares"],
        vertex_count=res["vertex_count"],
    )


@router.post(
    "",
    response_model=AOIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Register New AOI",
    description="Validates geometry, computes ellipsoidal area, and persists AOI with spatial PostGIS geometry.",
)
def create_aoi_endpoint(
    payload: AOICreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AOIResponse:
    """Create a new user-owned AOI record."""
    aoi = create_aoi(
        session=session,
        user=current_user,
        name=payload.name,
        description=payload.description,
        geometry_input=payload.geometry,
        is_public=payload.is_public,
    )
    return AOIResponse(**aoi_to_dict(aoi))


@router.get(
    "",
    response_model=AOIListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Accessible AOIs",
    description="Retrieve user-owned private AOIs and public study reaches with pagination.",
)
def list_aois_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    public_only: bool = Query(False, description="Filter to only public AOIs"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AOIListResponse:
    """List accessible AOIs."""
    items, total = list_aois(
        session=session,
        user=current_user,
        limit=limit,
        offset=offset,
        public_only=public_only,
    )
    return AOIListResponse(
        items=[AOIResponse(**aoi_to_dict(a)) for a in items],
        total=total,
    )


@router.get(
    "/{aoi_id}",
    response_model=AOIResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AOI by ID",
    description="Retrieve a specific AOI. Private AOIs require ownership or administrator authority.",
)
def get_aoi_endpoint(
    aoi_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AOIResponse:
    """Retrieve single AOI entity."""
    aoi = get_aoi(session, current_user, aoi_id)
    return AOIResponse(**aoi_to_dict(aoi))


@router.patch(
    "/{aoi_id}",
    response_model=AOIResponse,
    status_code=status.HTTP_200_OK,
    summary="Update AOI Metadata or Visibility",
    description="Update name, description, or public sharing flag. Only owners and administrators may modify.",
)
def update_aoi_endpoint(
    aoi_id: uuid.UUID,
    payload: AOIUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AOIResponse:
    """Update existing AOI attributes."""
    aoi = update_aoi(
        session=session,
        user=current_user,
        aoi_id=aoi_id,
        name=payload.name,
        description=payload.description,
        is_public=payload.is_public,
    )
    return AOIResponse(**aoi_to_dict(aoi))


@router.delete(
    "/{aoi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete AOI",
    description="Remove an AOI. Only owners and administrators may delete.",
)
def delete_aoi_endpoint(
    aoi_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> None:
    """Delete an AOI."""
    delete_aoi(session, current_user, aoi_id)
