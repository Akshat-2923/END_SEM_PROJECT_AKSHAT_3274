"""Artifact service layer for retrieving and downloading generated files and reports."""

import logging
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth import AuthenticatedUser
from src.config import BASE_DIR, OUTPUTS_DIR
from src.database.models.analysis import AnalysisRun
from src.database.models.artifact import AnalysisArtifact
from src.services.analysis_service import get_analysis_run
from src.storage import get_storage_backend

logger = logging.getLogger("dhara_scope.artifact_service")


def get_artifact_by_id(
    session: Session,
    user: AuthenticatedUser,
    artifact_id: uuid.UUID,
) -> Tuple[AnalysisArtifact, Path]:
    """Retrieve an AnalysisArtifact and its verified local filesystem path.

    Enforces cross-user ownership isolation via the parent AnalysisRun.
    """
    artifact = session.scalar(
        select(AnalysisArtifact).where(AnalysisArtifact.id == artifact_id)
    )
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )

    # Verify user ownership of the parent analysis run
    _ = get_analysis_run(session, user, artifact.analysis_run_id)

    # Resolve storage path via storage abstraction
    storage = get_storage_backend()
    target_path = storage.get_local_path(artifact.storage_bucket, artifact.storage_path)
    if target_path is None or not target_path.exists():
        try:
            target_path = storage.download_file(artifact.storage_bucket, artifact.storage_path)
        except Exception as exc:
            logger.warning("Failed to retrieve artifact payload from storage: %s", exc)
            target_path = None

    if target_path is None or not target_path.exists():
        # Fallback to direct path resolution under BASE_DIR / OUTPUTS_DIR
        candidate = BASE_DIR / artifact.storage_path
        if candidate.exists():
            target_path = candidate
        else:
            fallback = OUTPUTS_DIR / artifact.storage_path
            if fallback.exists():
                target_path = fallback
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Artifact file payload does not exist on storage",
                )

    return artifact, target_path


def get_report_file(
    session: Session,
    user: AuthenticatedUser,
    run_id: uuid.UUID,
    report_format: str,
) -> Tuple[Path, str, str]:
    """Resolve report file path, MIME type, and download filename for a completed run."""
    fmt = report_format.lower().strip()
    if fmt not in ("pdf", "csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported report format: '{report_format}'. Supported formats: 'pdf', 'csv'.",
        )

    run = get_analysis_run(session, user, run_id)
    if run.status != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot download report: Analysis run status is '{run.status}' (must be 'SUCCESS')",
        )

    expected_type = "REPORT_PDF" if fmt == "pdf" else "REPORT_CSV"
    expected_mime = "application/pdf" if fmt == "pdf" else "text/csv"

    artifact = session.scalar(
        select(AnalysisArtifact)
        .where(
            AnalysisArtifact.analysis_run_id == run.id,
            AnalysisArtifact.artifact_type == expected_type,
        )
        .order_by(AnalysisArtifact.created_at.desc())
    )

    if artifact:
        storage = get_storage_backend()
        target_path = storage.get_local_path(artifact.storage_bucket, artifact.storage_path)
        if target_path is None or not target_path.exists():
            try:
                target_path = storage.download_file(artifact.storage_bucket, artifact.storage_path)
            except Exception as exc:
                logger.warning("Failed to retrieve report payload from storage: %s", exc)
                target_path = None

        if target_path and target_path.exists():
            return target_path, expected_mime, artifact.file_name

        # Direct disk fallback
        candidate = BASE_DIR / artifact.storage_path
        if candidate.exists():
            return candidate, expected_mime, artifact.file_name

    # Check run directory for matching file
    run_dir = OUTPUTS_DIR / str(run.user_id) / str(run.id)
    candidates = list(run_dir.glob(f"*.{fmt}"))
    if candidates:
        candidate = candidates[0]
        return candidate, expected_mime, candidate.name

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Report of format '{fmt}' has not been generated for analysis run '{run_id}'",
    )
