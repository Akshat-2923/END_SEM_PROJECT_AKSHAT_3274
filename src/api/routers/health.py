"""Health check and system metadata endpoints."""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.dependencies import get_anonymous_db_session
from src.api.schemas.health import (
    DatabaseDiagnosticResponse,
    DatabasePoolMetrics,
    HealthResponse,
)
from src.database.session import check_database_connectivity

router = APIRouter(tags=["System Health & Diagnostics"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Inspect application operational status and database connectivity.",
)
@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def check_health(session: Session = Depends(get_anonymous_db_session)) -> HealthResponse:
    """Verify application uptime and PostgreSQL connectivity."""
    db_status = "connected"
    try:
        session.execute(text("SELECT 1;"))
    except Exception:
        db_status = "disconnected"

    env = os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "development"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        app_name="DharaScope",
        version="2.2.0",
        environment=env,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/db",
    response_model=DatabaseDiagnosticResponse,
    status_code=status.HTTP_200_OK,
    summary="Database Connectivity Diagnostics",
    description="Inspect sanitized database parameters, PostGIS availability, SSL status, and pool metrics.",
)
@router.get(
    "/api/v1/health/db",
    response_model=DatabaseDiagnosticResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def check_database_health() -> DatabaseDiagnosticResponse:
    """Perform non-sensitive database diagnostic and return sanitized metrics."""
    diag = check_database_connectivity()
    pool_metrics = None
    if diag.get("pool"):
        pool_metrics = DatabasePoolMetrics(**diag["pool"])

    return DatabaseDiagnosticResponse(
        status=diag["status"],
        connected=diag["connected"],
        dialect=diag.get("dialect"),
        driver=diag.get("driver"),
        host=diag.get("host"),
        port=diag.get("port"),
        database_name=diag.get("database_name"),
        username=diag.get("username"),
        sanitized_url=diag.get("sanitized_url"),
        ssl_mode=diag.get("ssl_mode"),
        ssl_active=diag.get("ssl_active", False),
        server_version=diag.get("server_version"),
        postgis_version=diag.get("postgis_version"),
        pool=pool_metrics,
        error=diag.get("error"),
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="API Root Information",
    description="Provides basic service metadata and documentation links.",
)
def api_root():
    """Root metadata response."""
    return {
        "service": "DharaScope API",
        "description": "Satellite-Based River Surface Water Dynamics Platform",
        "version": "2.2.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/health",
        "status": "operational",
    }

