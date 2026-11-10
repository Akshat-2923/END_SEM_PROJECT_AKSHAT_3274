"""Analysis run orchestration, metrics, and report download router."""

import uuid
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.api.dependencies import get_db_session
from src.api.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisListResponse,
    AnalysisResponse,
    ArtifactListResponse,
    ArtifactResponse,
    WaterMetricsResponse,
)
from src.auth import AuthenticatedUser, get_current_user
from src.database.models.analysis import AnalysisRun
from src.database.models.artifact import AnalysisArtifact
from src.database.models.water_metrics import WaterMetrics
from src.services.analysis_service import (
    create_analysis_run,
    delete_analysis_run,
    get_analysis_run,
    get_water_metrics,
    list_analysis_runs,
    list_artifacts,
)
from src.services.artifact_service import get_report_file

router = APIRouter(prefix="/api/v1/analyses", tags=["Satellite Analysis & Hydrological Runs"])


def run_to_response(run: AnalysisRun) -> AnalysisResponse:
    """Format an AnalysisRun entity for API response."""
    return AnalysisResponse(
        id=run.id,
        user_id=run.user_id,
        aoi_id=run.aoi_id,
        status=run.status,
        data_provider=run.data_provider,
        is_real_data=run.is_real_data,
        t1_scene_id=run.t1_scene_id,
        t1_date=run.t1_date,
        t1_cloud_cover=run.t1_cloud_cover,
        t2_scene_id=run.t2_scene_id,
        t2_date=run.t2_date,
        t2_cloud_cover=run.t2_cloud_cover,
        ndwi_threshold=run.ndwi_threshold,
        error_message=run.error_message,
        execution_duration_sec=run.execution_duration_sec,
        execution_timestamp=run.execution_timestamp,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def metrics_to_response(m: WaterMetrics) -> WaterMetricsResponse:
    """Format a WaterMetrics entity for API response."""
    return WaterMetricsResponse(
        id=m.id,
        analysis_run_id=m.analysis_run_id,
        common_valid_pixels=m.common_valid_pixels,
        common_valid_area_ha=m.common_valid_area_ha,
        pixel_size_m2=m.pixel_size_m2,
        t1_water_pixels=m.t1_water_pixels,
        t1_water_area_m2=m.t1_water_area_m2,
        t1_water_area_ha=m.t1_water_area_ha,
        t2_water_pixels=m.t2_water_pixels,
        t2_water_area_m2=m.t2_water_area_m2,
        t2_water_area_ha=m.t2_water_area_ha,
        absolute_change_m2=m.absolute_change_m2,
        absolute_change_ha=m.absolute_change_ha,
        percentage_change=m.percentage_change,
        persistent_water_m2=m.persistent_water_m2,
        persistent_water_ha=m.persistent_water_ha,
        apparent_loss_m2=m.apparent_loss_m2,
        apparent_loss_ha=m.apparent_loss_ha,
        apparent_gain_m2=m.apparent_gain_m2,
        apparent_gain_ha=m.apparent_gain_ha,
        limitation_statement=m.limitation_statement,
        created_at=m.created_at,
    )


def artifact_to_response(art: AnalysisArtifact) -> ArtifactResponse:
    """Format an AnalysisArtifact entity for API response without exposing system paths."""
    return ArtifactResponse(
        id=art.id,
        analysis_run_id=art.analysis_run_id,
        artifact_type=art.artifact_type,
        storage_bucket=art.storage_bucket,
        file_name=art.file_name,
        file_size_bytes=art.file_size_bytes,
        mime_type=art.mime_type,
        download_url=f"/api/v1/artifacts/{art.id}/download",
        created_at=art.created_at,
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Launch Satellite Analysis Run",
    description="Enqueue a multi-temporal Sentinel-2 water dynamics analysis. Runs asynchronously in background.",
)
def create_analysis_endpoint(
    payload: AnalysisCreateRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="If True, executes synchronously (useful for deterministic tests)"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    """Create and launch a multi-temporal satellite analysis run."""
    run = create_analysis_run(
        session=session,
        user=current_user,
        aoi_id=payload.aoi_id,
        aoi_geometry=payload.aoi_geometry,
        aoi_name=payload.aoi_name,
        ndwi_threshold=payload.ndwi_threshold,
        max_cloud_cover=payload.max_cloud_cover,
        datetime_range=payload.datetime_range,
        data_source=payload.data_source,
        background_tasks=background_tasks,
        sync=sync,
    )
    return run_to_response(run)


@router.get(
    "",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Analysis Runs",
    description="Retrieve user's analysis runs with execution status, timings, and metadata.",
)
def list_analyses_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AnalysisListResponse:
    """List accessible analysis runs."""
    items, total = list_analysis_runs(
        session=session,
        user=current_user,
        limit=limit,
        offset=offset,
    )
    return AnalysisListResponse(
        items=[run_to_response(r) for r in items],
        total=total,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Run Status & Metadata",
    description="Poll status ('QUEUED', 'PROCESSING', 'SUCCESS', 'FAILED') and retrieve execution details.",
)
def get_analysis_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> AnalysisResponse:
    """Retrieve single analysis run details."""
    run = get_analysis_run(session, current_user, analysis_id)
    return run_to_response(run)


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Analysis Run",
    description="Remove an analysis run and its associated metrics and artifacts.",
)
def delete_analysis_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> None:
    """Delete an analysis run."""
    delete_analysis_run(session, current_user, analysis_id)


@router.get(
    "/{analysis_id}/metrics",
    response_model=WaterMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Surface Water Change Metrics",
    description="Retrieve pixel counts, physical area, transition components, and percentage changes.",
)
def get_metrics_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> WaterMetricsResponse:
    """Retrieve quantitative water change metrics."""
    metrics = get_water_metrics(session, current_user, analysis_id)
    return metrics_to_response(metrics)


@router.get(
    "/{analysis_id}/artifacts",
    response_model=ArtifactListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Generated Artifacts",
    description="List all generated figures, maps, thumbnails, and reports with secure download URLs.",
)
def list_artifacts_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> ArtifactListResponse:
    """List artifacts for an analysis run."""
    artifacts = list_artifacts(session, current_user, analysis_id)
    return ArtifactListResponse(
        items=[artifact_to_response(a) for a in artifacts],
        total=len(artifacts),
    )


@router.get(
    "/{analysis_id}/reports/csv",
    status_code=status.HTTP_200_OK,
    summary="Download Analysis CSV Report",
    description="Download structured CSV report generated from immutable run manifest.",
    response_class=FileResponse,
)
def download_csv_report_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Download analysis CSV report."""
    file_path, mime_type, filename = get_report_file(session, current_user, analysis_id, "csv")
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=filename,
    )


@router.get(
    "/{analysis_id}/reports/pdf",
    status_code=status.HTTP_200_OK,
    summary="Download Publication-Ready PDF Report",
    description="Download publication-quality ReportLab PDF report containing figures and scientific metrics.",
    response_class=FileResponse,
)
def download_pdf_report_endpoint(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Download analysis PDF report."""
    file_path, mime_type, filename = get_report_file(session, current_user, analysis_id, "pdf")
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=filename,
    )
