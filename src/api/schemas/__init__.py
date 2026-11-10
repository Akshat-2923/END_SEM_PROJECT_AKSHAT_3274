"""Schema exports for DharaScope API."""

from src.api.schemas.common import ErrorResponse
from src.api.schemas.health import HealthResponse
from src.api.schemas.auth import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    AdminUserUpdateRequest,
)
from src.api.schemas.aoi import (
    AOIValidateRequest,
    AOIValidateResponse,
    AOICreateRequest,
    AOIUpdateRequest,
    AOIResponse,
    AOIListResponse,
)
from src.api.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisResponse,
    AnalysisListResponse,
    WaterMetricsResponse,
    ArtifactResponse,
    ArtifactListResponse,
)

__all__ = [
    "ErrorResponse",
    "HealthResponse",
    "UserProfileResponse",
    "UserProfileUpdateRequest",
    "AdminUserUpdateRequest",
    "AOIValidateRequest",
    "AOIValidateResponse",
    "AOICreateRequest",
    "AOIUpdateRequest",
    "AOIResponse",
    "AOIListResponse",
    "AnalysisCreateRequest",
    "AnalysisResponse",
    "AnalysisListResponse",
    "WaterMetricsResponse",
    "ArtifactResponse",
    "ArtifactListResponse",
]
