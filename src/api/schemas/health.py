"""Health, diagnostics, and system status schemas."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health check response."""
    status: str = Field(..., description="Operational status ('healthy' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic API version")
    environment: str = Field(..., description="Active runtime environment")
    database: str = Field(..., description="Database connectivity status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatabasePoolMetrics(BaseModel):
    """SQLAlchemy connection pool operational metrics."""
    type: str = Field(..., description="Pool class name (e.g. QueuePool)")
    size: Optional[int] = Field(None, description="Configured permanent pool size")
    checked_in: Optional[int] = Field(None, description="Number of idle checked-in connections")
    checked_out: Optional[int] = Field(None, description="Number of actively checked-out connections")
    overflow: Optional[int] = Field(None, description="Active overflow connection count")


class DatabaseDiagnosticResponse(BaseModel):
    """Database connectivity and runtime diagnostics without credential exposure."""
    status: str = Field(..., description="Database operational status ('connected' or 'disconnected')")
    connected: bool = Field(..., description="Whether database connection succeeded")
    dialect: Optional[str] = Field(None, description="Database dialect (e.g. postgresql)")
    driver: Optional[str] = Field(None, description="Database driver (e.g. psycopg2)")
    host: Optional[str] = Field(None, description="Database host (sanitized)")
    port: Optional[int] = Field(None, description="Database port")
    database_name: Optional[str] = Field(None, description="Connected database name")
    username: Optional[str] = Field(None, description="Connected database username")
    sanitized_url: Optional[str] = Field(None, description="Sanitized connection URL with credentials redacted")
    ssl_mode: Optional[str] = Field(None, description="Configured SSL mode (e.g. require)")
    ssl_active: bool = Field(False, description="Whether SSL/TLS is actively used on the current connection")
    server_version: Optional[str] = Field(None, description="Database engine version string")
    postgis_version: Optional[str] = Field(None, description="PostGIS extension version string")
    pool: Optional[DatabasePoolMetrics] = Field(None, description="Connection pool diagnostic metrics")
    error: Optional[str] = Field(None, description="Sanitized connection error description if failed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

