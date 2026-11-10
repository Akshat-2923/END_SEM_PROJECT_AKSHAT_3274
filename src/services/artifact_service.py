"""Artifact service layer for retrieving and downloading generated files and reports."""

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

    # Resolve storage path securely relative to BASE_DIR
    target_path = BASE_DIR / artifact.storage_path
    if not target_path.exists():
        # Check fallback under outputs
        fallback_path = OUTPUTS_DIR / artifact.storage_path
        if fallback_path.exists():
            target_path = fallback_path
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
        target_path = BASE_DIR / artifact.storage_path
        if target_path.exists():
            return target_path, expected_mime, artifact.file_name

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
