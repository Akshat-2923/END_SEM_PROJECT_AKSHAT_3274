"""Health check and system metadata endpoints."""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.dependencies import get_anonymous_db_session
from src.api.schemas.health import HealthResponse

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
