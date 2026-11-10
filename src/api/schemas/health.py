"""Health and system status schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health check response."""
    status: str = Field(..., description="Operational status ('healthy' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic API version")
    environment: str = Field(..., description="Active runtime environment")
    database: str = Field(..., description="Database connectivity status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
