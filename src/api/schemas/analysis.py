"""Analysis run, water metrics, and artifact request/response schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreateRequest(BaseModel):
    """Payload to initiate a multi-temporal satellite analysis run."""
    aoi_id: Optional[uuid.UUID] = Field(
        None,
        description="UUID of an existing persisted AOI. If omitted, inline geometry must be provided.",
    )
    aoi_geometry: Optional[Any] = Field(
        None,
        description="Optional ad-hoc AOI geometry dict or bbox if aoi_id is not supplied.",
    )
    aoi_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Name to assign if creating an inline ad-hoc AOI.",
    )
    ndwi_threshold: float = Field(
        0.0,
        ge=-1.0,
        le=1.0,
        description="NDWI water segmentation threshold cutoff (default 0.00).",
    )
    max_cloud_cover: float = Field(
        10.0,
        ge=0.0,
        le=100.0,
        description="Maximum permissible scene cloud cover percentage (default 10.0%).",
    )
    datetime_range: str = Field(
        "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
        description="ISO-8601 temporal search interval.",
    )
    data_source: str = Field(
        "auto",
        pattern="^(auto|cdse|public|synthetic)$",
        description="Satellite retrieval tier ('auto', 'cdse', 'public', or 'synthetic').",
    )


class AnalysisResponse(BaseModel):
    """Analysis run status and metadata entity."""
    id: uuid.UUID
    user_id: uuid.UUID
    aoi_id: Optional[uuid.UUID] = None
    status: str = Field(..., description="Status ('QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED')")
    data_provider: str
    is_real_data: bool
    t1_scene_id: str
    t1_date: datetime
    t1_cloud_cover: Optional[float] = None
    t2_scene_id: str
    t2_date: datetime
    t2_cloud_cover: Optional[float] = None
    ndwi_threshold: float
    error_message: Optional[str] = None
    execution_duration_sec: Optional[float] = None
    execution_timestamp: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    """Paginated list of analysis runs."""
    items: List[AnalysisResponse]
    total: int


class WaterMetricsResponse(BaseModel):
    """Quantitative surface water area metrics and change transition breakdown."""
    id: uuid.UUID
    analysis_run_id: uuid.UUID
    common_valid_pixels: int
    common_valid_area_ha: float
    pixel_size_m2: float
    t1_water_pixels: int
    t1_water_area_m2: float
    t1_water_area_ha: float
    t2_water_pixels: int
    t2_water_area_m2: float
    t2_water_area_ha: float
    absolute_change_m2: float
    absolute_change_ha: float
    percentage_change: Optional[float] = None
    persistent_water_m2: float
    persistent_water_ha: float
    apparent_loss_m2: float
    apparent_loss_ha: float
    apparent_gain_m2: float
    apparent_gain_ha: float
    limitation_statement: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactResponse(BaseModel):
    """Reference to generated maps, figures, or reports stored in object storage."""
    id: uuid.UUID
    analysis_run_id: uuid.UUID
    artifact_type: str = Field(..., description="'MAP_PNG', 'PANEL_PNG', 'REPORT_PDF', 'REPORT_CSV', 'THUMBNAIL_JPG', 'RASTER_TIFF'")
    storage_bucket: str = Field(..., description="'maps', 'reports', 'rasters'")
    file_name: str
    file_size_bytes: Optional[int] = None
    mime_type: str
    download_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactListResponse(BaseModel):
    """List of generated artifacts for an analysis run."""
    items: List[ArtifactResponse]
    total: int
