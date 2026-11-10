"""Common Pydantic schemas and error models for DharaScope API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""
    error: str = Field(..., description="High-level error classification or exception name")
    detail: str = Field(..., description="Sanitized human-readable error description")
    status_code: int = Field(..., description="HTTP status code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "AOIValidationError",
                "detail": "AOI surface area (0.0500 km²) is below the minimum threshold of 0.10 km².",
                "status_code": 400,
            }
        }
    )
