"""Area of Interest (AOI) request and response schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class AOIValidateRequest(BaseModel):
    """Payload to validate geometry without persisting to the database."""
    geometry: Any = Field(
        ...,
        description="GeoJSON geometry dict, bounding box [min_lon, min_lat, max_lon, max_lat], or WKT string",
    )
    min_area_km2: Optional[float] = Field(None, gt=0, description="Optional custom minimum area bound")
    max_area_km2: Optional[float] = Field(None, gt=0, description="Optional custom maximum area bound")
    max_vertices: Optional[int] = Field(None, ge=4, description="Optional custom vertex limit")


class AOIValidateResponse(BaseModel):
    """Result of AOI geometry validation."""
    valid: bool = Field(True, description="True if geometry passes all validation criteria")
    geometry: Dict[str, Any] = Field(..., description="Canonical GeoJSON geometry mapping")
    geometry_type: str = Field(..., description="Geometry type (e.g. Polygon, MultiPolygon)")
    bbox: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    centroid: List[float] = Field(..., description="[centroid_lon, centroid_lat]")
    area_m2: float = Field(..., description="Ellipsoidal area in square meters")
    area_km2: float = Field(..., description="Ellipsoidal area in square kilometers")
    area_hectares: float = Field(..., description="Ellipsoidal area in hectares")
    vertex_count: int = Field(..., description="Total vertex count")


class AOICreateRequest(BaseModel):
    """Payload to register and store an Area of Interest."""
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable reach name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional study notes")
    geometry: Any = Field(
        ...,
        description="GeoJSON geometry dict, bounding box [min_lon, min_lat, max_lon, max_lat], or WKT string",
    )
    is_public: bool = Field(False, description="Whether this AOI is visible to other users")


class AOIUpdateRequest(BaseModel):
    """Payload to update an existing AOI metadata or visibility."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    is_public: Optional[bool] = None


class AOIResponse(BaseModel):
    """AOI entity representation returned to clients."""
    id: uuid.UUID = Field(..., description="Unique AOI UUID")
    user_id: uuid.UUID = Field(..., description="Owner user UUID")
    name: str = Field(..., description="AOI name")
    description: Optional[str] = Field(None, description="AOI description")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON polygon geometry")
    area_km2: float = Field(..., description="Area in km²")
    area_hectares: float = Field(..., description="Area in hectares")
    bbox: List[float] = Field(..., description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    centroid: List[float] = Field(..., description="Centroid [lon, lat]")
    vertex_count: int = Field(..., description="Vertex count")
    is_public: bool = Field(..., description="Public visibility flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AOIListResponse(BaseModel):
    """Paginated list of AOI entities."""
    items: List[AOIResponse]
    total: int
