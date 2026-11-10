"""Artifact download router."""

import uuid
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.api.dependencies import get_db_session
from src.auth import AuthenticatedUser, get_current_user
from src.services.artifact_service import get_artifact_by_id

router = APIRouter(prefix="/api/v1/artifacts", tags=["Generated Artifacts & Cartography"])


@router.get(
    "/{artifact_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Analysis Artifact File",
    description="Download a specific generated figure (PNG), thumbnail (JPG), or raster (GeoTIFF).",
    response_class=FileResponse,
)
def download_artifact_endpoint(
    artifact_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Download an analysis artifact with ownership verification."""
    artifact, file_path = get_artifact_by_id(session, current_user, artifact_id)
    return FileResponse(
        path=str(file_path),
        media_type=artifact.mime_type,
        filename=artifact.file_name,
    )
