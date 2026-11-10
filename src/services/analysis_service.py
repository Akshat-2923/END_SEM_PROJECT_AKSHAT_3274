"""Analysis service orchestrating satellite pipeline execution, run lifecycle, and metrics."""

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.aoi_validation import validate_aoi_polygon
from src.auth import AuthenticatedUser, get_authenticated_db, get_or_create_profile
from src.change_detection import LIMITATION_STATEMENT, compute_water_change
from src.config import (
    BASE_DIR,
    CDSE_COLLECTION,
    CDSE_STAC_BASE_URL,
    GOMTI_BBOX,
    NDWI_WATER_THRESHOLD,
    OUTPUTS_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
)
from src.database.models.analysis import AnalysisRun
from src.database.models.aoi import AOI
from src.database.models.artifact import AnalysisArtifact
from src.database.models.water_metrics import WaterMetrics
from src.downloader import CDSEDownloader
from src.reporting import generate_csv_report, generate_pdf_report
from src.scene_selection import SceneSelector
from src.services.aoi_service import create_aoi, get_aoi
from src.visualization import (
    plot_four_panel_comparison,
    plot_single_observation,
    plot_water_change_map,
)
from src.water_indices import process_scene_bands

logger = logging.getLogger("dhara_scope.analysis_service")


def sanitize_error_message(raw_msg: str) -> str:
    """Sanitize error messages to eliminate internal system paths, tokens, or stack traces."""
    if not raw_msg:
        return "Unknown analysis failure"

    # Strip local absolute Windows or Unix paths
    sanitized = re.sub(r"[A-Za-z]:\\[^ \n\t\"']+", "[internal_path]", raw_msg)
    sanitized = re.sub(r"/(?:home|Users|var|tmp|app)/[^ \n\t\"']+", "[internal_path]", sanitized)

    # Strip bearer tokens or passwords
    sanitized = re.sub(r"(?i)(password|token|bearer|secret)\s*[:=]\s*[^ \n\t,;]+", r"\1=[REDACTED]", sanitized)

    # Keep message concise
    return sanitized.strip()[:500]


def get_analysis_run(session: Session, user: AuthenticatedUser, run_id: uuid.UUID) -> AnalysisRun:
    """Retrieve an AnalysisRun entity enforcing ownership (owner or admin)."""
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run '{run_id}' not found",
        )

    if run.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run '{run_id}' not found",
        )

    return run


def list_analysis_runs(
    session: Session,
    user: AuthenticatedUser,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[AnalysisRun], int]:
    """List analysis runs accessible to the user (own runs, or all for admin)."""
    if user.is_admin:
        stmt = select(AnalysisRun)
        count_stmt = select(func.count(AnalysisRun.id))
    else:
        stmt = select(AnalysisRun).where(AnalysisRun.user_id == user.id)
        count_stmt = select(func.count(AnalysisRun.id)).where(AnalysisRun.user_id == user.id)

    total = session.scalar(count_stmt) or 0
    items = list(
        session.scalars(
            stmt.order_by(AnalysisRun.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return items, total


def delete_analysis_run(session: Session, user: AuthenticatedUser, run_id: uuid.UUID) -> None:
    """Delete an analysis run and its cascading metrics/artifacts (owner or admin only)."""
    run = get_analysis_run(session, user, run_id)
    if run.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete this analysis run",
        )

    session.delete(run)
    session.flush()


def get_water_metrics(session: Session, user: AuthenticatedUser, run_id: uuid.UUID) -> WaterMetrics:
    """Retrieve WaterMetrics for a completed analysis run."""
    run = get_analysis_run(session, user, run_id)
    if run.status != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Metrics not available: Analysis run status is '{run.status}' (must be 'SUCCESS')",
        )

    metrics = session.scalar(select(WaterMetrics).where(WaterMetrics.analysis_run_id == run.id))
    if metrics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Water metrics record not found for this analysis run",
        )
    return metrics


def list_artifacts(session: Session, user: AuthenticatedUser, run_id: uuid.UUID) -> List[AnalysisArtifact]:
    """List generated artifacts for an analysis run."""
    run = get_analysis_run(session, user, run_id)
    return list(
        session.scalars(
            select(AnalysisArtifact)
            .where(AnalysisArtifact.analysis_run_id == run.id)
            .order_by(AnalysisArtifact.created_at.asc())
        ).all()
    )


def execute_pipeline_worker(
    run_id: uuid.UUID,
    user: AuthenticatedUser,
    bbox: List[float],
    ndwi_threshold: float,
    max_cloud_cover: float,
    datetime_range: str,
    data_source: str,
) -> None:
    """Background worker executing the full Sentinel-2 analysis pipeline.

    Executes in a background thread without blocking the FastAPI event loop.
    All errors are caught, sanitized, and recorded in the database status.
    """
    logger.info("Starting background analysis worker for run %s (user %s)", run_id, user.id)
    start_time = time.time()

    with get_authenticated_db(user) as session:
        run = session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))
        if not run:
            logger.error("AnalysisRun %s not found in worker thread", run_id)
            return

        run.status = "PROCESSING"
        session.commit()

        try:
            # 1. Scene Discovery
            selector = SceneSelector(study_bbox=bbox)
            t1_item, t2_item, _ = selector.select_observation_pair(
                datetime_range=datetime_range,
                max_cloud_cover=max_cloud_cover,
            )

            # 2. Band Retrieval
            run_artifacts_dir = OUTPUTS_DIR / str(user.id) / str(run_id)
            run_artifacts_dir.mkdir(parents=True, exist_ok=True)

            downloader = CDSEDownloader()
            t1_b3, p1 = downloader.retrieve_band(
                t1_item, "B03", mode=data_source, clip_bbox=bbox, is_earlier=True
            )
            t1_b8, _ = downloader.retrieve_band(
                t1_item, "B08", mode=data_source, clip_bbox=bbox, is_earlier=True
            )
            t2_b3, p2 = downloader.retrieve_band(
                t2_item, "B03", mode=data_source, clip_bbox=bbox, is_earlier=False
            )
            t2_b8, _ = downloader.retrieve_band(
                t2_item, "B08", mode=data_source, clip_bbox=bbox, is_earlier=False
            )

            is_real = bool(p1 != "SYNTHETIC_BENCHMARK_SAMPLE" and p2 != "SYNTHETIC_BENCHMARK_SAMPLE")
            data_provider = p1 if p1 == p2 else f"{p1}/{p2}"

            # 3. Spectral Processing (NDWI)
            res_t1 = process_scene_bands(t1_b3, t1_b8, clip_bbox=bbox, threshold=ndwi_threshold)
            res_t2 = process_scene_bands(t2_b3, t2_b8, clip_bbox=bbox, threshold=ndwi_threshold)
            t1_ndwi = res_t1["ndwi"]
            t1_mask = res_t1["water_mask"]
            t2_ndwi = res_t2["ndwi"]
            t2_mask = res_t2["water_mask"]

            # 4. Change Detection
            change_res = compute_water_change(
                res_t1["water_mask"],
                res_t2["water_mask"],
                res_t1["valid_mask"],
                res_t2["valid_mask"],
                pixel_area_m2=res_t1["pixel_area_m2"],
            )
            stats = change_res["statistics"]
            cp = stats["comparison_pixels"]
            t1_w = stats["water_area_earlier_t1"]
            t2_w = stats["water_area_later_t2"]
            ch_m = stats["change_metrics"]

            # 5. Visualizations
            t1_date_str = str(t1_item.get("properties", {}).get("datetime", "2023-10-10"))[:10]
            t2_date_str = str(t2_item.get("properties", {}).get("datetime", "2023-12-09"))[:10]

            panel_path = run_artifacts_dir / "gomti_water_change_comparison_panel.png"
            change_map_path = run_artifacts_dir / f"water_change_{t1_date_str}_to_{t2_date_str}.png"
            t1_map_path = run_artifacts_dir / f"observation_{t1_date_str}_ndwi.png"
            t2_map_path = run_artifacts_dir / f"observation_{t2_date_str}_ndwi.png"

            badge = f"[{data_provider}]"

            plot_four_panel_comparison(
                ndwi_t1=t1_ndwi,
                water_t1=t1_mask,
                date_t1=t1_date_str,
                ndwi_t2=t2_ndwi,
                water_t2=t2_mask,
                date_t2=t2_date_str,
                change_matrix=change_res["change_matrix"],
                stats=stats,
                output_path=panel_path,
                provenance_label=badge,
            )

            plot_water_change_map(
                change_matrix=change_res["change_matrix"],
                stats=stats,
                date_t1=t1_date_str,
                date_t2=t2_date_str,
                output_path=change_map_path,
                provenance_label=badge,
            )

            plot_single_observation(
                ndwi=t1_ndwi,
                water_mask=t1_mask,
                date_str=t1_date_str,
                scene_id=t1_item.get("id", "S2_T1"),
                output_path=t1_map_path,
                provenance_label=badge,
            )

            plot_single_observation(
                ndwi=t2_ndwi,
                water_mask=t2_mask,
                date_str=t2_date_str,
                scene_id=t2_item.get("id", "S2_T2"),
                output_path=t2_map_path,
                provenance_label=badge,
            )

            # 6. Build Manifest & Generate Reports
            manifest = {
                "project": "DharaScope",
                "phase": "Phase 2 - Platform Service Layer",
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": {
                    "study_bbox": bbox,
                    "ndwi_classification_threshold": ndwi_threshold,
                    "max_cloud_filter": max_cloud_cover,
                },
                "data_source_provenance": {
                    "provider": data_provider,
                    "is_real_satellite_data": is_real,
                    "description": f"Retrieved via {data_provider}",
                },
                "stages": {
                    "scene_selection": {
                        "selected_earlier_scene": t1_item,
                        "selected_later_scene": t2_item,
                    },
                    "water_classification": {
                        "earlier_date": t1_date_str,
                        "later_date": t2_date_str,
                        "earlier_scene_id": t1_item.get("id", "S2_T1"),
                        "later_scene_id": t2_item.get("id", "S2_T2"),
                        "earlier_cloud_cover": float(t1_item.get("properties", {}).get("cloudCover", 0.0)),
                        "later_cloud_cover": float(t2_item.get("properties", {}).get("cloudCover", 0.0)),
                    },
                    "real_ndwi_calculation": {
                        "status": "SUCCESS",
                        "provider": data_provider,
                        "threshold": ndwi_threshold,
                        "crs": res_t1["crs"],
                        "pixel_area_m2": res_t1["pixel_area_m2"],
                    },
                    "real_change_detection": {
                        "status": "SUCCESS",
                        "statistics": stats,
                    },
                },
                "limitation_notice": LIMITATION_STATEMENT,
            }

            csv_path = run_artifacts_dir / f"dharascope_report_{t1_date_str}_to_{t2_date_str}.csv"
            pdf_path = run_artifacts_dir / f"dharascope_report_{t1_date_str}_to_{t2_date_str}.pdf"

            generate_csv_report(manifest_source=manifest, output_path=csv_path)
            generate_pdf_report(
                manifest_source=manifest,
                output_path=pdf_path,
                include_figures=True,
            )

            # 7. Persist WaterMetrics
            metrics = WaterMetrics(
                analysis_run_id=run.id,
                common_valid_pixels=cp["common_valid_pixels"],
                common_valid_area_ha=cp["common_valid_area_ha"],
                pixel_size_m2=cp.get("pixel_size_m2", 100.0),
                t1_water_pixels=t1_w["pixels"],
                t1_water_area_m2=t1_w["area_m2"],
                t1_water_area_ha=t1_w["area_hectares"],
                t2_water_pixels=t2_w["pixels"],
                t2_water_area_m2=t2_w["area_m2"],
                t2_water_area_ha=t2_w["area_hectares"],
                absolute_change_m2=ch_m["absolute_change_m2"],
                absolute_change_ha=ch_m["absolute_change_hectares"],
                percentage_change=ch_m["percentage_change"],
                persistent_water_m2=ch_m["persistent_water_m2"],
                persistent_water_ha=ch_m["persistent_water_hectares"],
                apparent_loss_m2=ch_m["apparent_loss_m2"],
                apparent_loss_ha=ch_m["apparent_loss_hectares"],
                apparent_gain_m2=ch_m["apparent_gain_m2"],
                apparent_gain_ha=ch_m["apparent_gain_hectares"],
                limitation_statement=LIMITATION_STATEMENT,
            )
            session.add(metrics)

            # 8. Register AnalysisArtifact Entities
            artifacts_to_create = [
                ("PANEL_PNG", "maps", panel_path, "image/png"),
                ("MAP_PNG", "maps", change_map_path, "image/png"),
                ("MAP_PNG", "maps", t1_map_path, "image/png"),
                ("MAP_PNG", "maps", t2_map_path, "image/png"),
                ("REPORT_CSV", "reports", csv_path, "text/csv"),
                ("REPORT_PDF", "reports", pdf_path, "application/pdf"),
            ]

            for art_type, bucket, file_p, mime in artifacts_to_create:
                if file_p.exists():
                    rel_storage_path = str(file_p.relative_to(BASE_DIR)).replace("\\", "/")
                    artifact = AnalysisArtifact(
                        analysis_run_id=run.id,
                        artifact_type=art_type,
                        storage_bucket=bucket,
                        storage_path=rel_storage_path,
                        file_name=file_p.name,
                        file_size_bytes=file_p.stat().st_size,
                        mime_type=mime,
                    )
                    session.add(artifact)

            # 9. Mark Status SUCCESS
            duration = round(time.time() - start_time, 2)
            run.status = "SUCCESS"
            run.data_provider = data_provider
            run.is_real_data = is_real
            run.t1_scene_id = t1_item.get("id", "S2_T1")
            run.t1_date = datetime.fromisoformat(t1_date_str.replace("Z", "+00:00"))
            run.t1_cloud_cover = float(t1_item.get("properties", {}).get("cloudCover", 0.0))
            run.t2_scene_id = t2_item.get("id", "S2_T2")
            run.t2_date = datetime.fromisoformat(t2_date_str.replace("Z", "+00:00"))
            run.t2_cloud_cover = float(t2_item.get("properties", {}).get("cloudCover", 0.0))
            run.execution_duration_sec = duration
            run.error_message = None

            session.commit()
            logger.info("Analysis run %s completed successfully in %.2fs", run_id, duration)

        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            logger.exception("Analysis worker failed for run %s: %s", run_id, exc)
            session.rollback()

            # Record failure in database safely
            run = session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))
            if run:
                run.status = "FAILED"
                run.error_message = sanitize_error_message(str(exc))
                run.execution_duration_sec = duration
                session.commit()


def create_analysis_run(
    session: Session,
    user: AuthenticatedUser,
    aoi_id: Optional[uuid.UUID] = None,
    aoi_geometry: Optional[Any] = None,
    aoi_name: Optional[str] = None,
    ndwi_threshold: float = 0.0,
    max_cloud_cover: float = 10.0,
    datetime_range: str = "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
    data_source: str = "auto",
    background_tasks: Optional[BackgroundTasks] = None,
    sync: bool = False,
) -> AnalysisRun:
    """Create and queue an analysis run, optionally executing synchronously for testing."""
    profile = get_or_create_profile(session, user)

    # 1. Quota Check
    if not user.is_admin:
        run_count = session.scalar(
            select(func.count(AnalysisRun.id)).where(AnalysisRun.user_id == user.id)
        ) or 0
        if run_count >= profile.quota_monthly_runs:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly analysis quota exceeded ({run_count}/{profile.quota_monthly_runs} runs used).",
            )

    # 2. Resolve AOI and Bounding Box
    target_aoi: Optional[AOI] = None
    if aoi_id is not None:
        target_aoi = get_aoi(session, user, aoi_id)
        bbox = target_aoi.bbox
    elif aoi_geometry is not None:
        name = aoi_name or f"Ad-hoc Reach ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')})"
        target_aoi = create_aoi(
            session=session,
            user=user,
            name=name,
            geometry_input=aoi_geometry,
            is_public=False,
        )
        bbox = target_aoi.bbox
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'aoi_id' or 'aoi_geometry' must be provided to initiate an analysis run",
        )

    # 3. Create AnalysisRun Record
    now_utc = datetime.now(timezone.utc)
    run = AnalysisRun(
        user_id=user.id,
        aoi_id=target_aoi.id if target_aoi else None,
        status="QUEUED",
        data_provider="PENDING_RETRIEVAL",
        is_real_data=True,
        t1_scene_id="PENDING_DISCOVERY",
        t1_date=now_utc,
        t2_scene_id="PENDING_DISCOVERY",
        t2_date=now_utc,
        ndwi_threshold=ndwi_threshold,
        execution_timestamp=now_utc,
    )
    session.add(run)
    session.flush()

    # 4. Dispatch Execution
    if sync:
        # Run synchronously (e.g. for deterministic unit/integration testing)
        session.commit()
        execute_pipeline_worker(
            run_id=run.id,
            user=user,
            bbox=bbox,
            ndwi_threshold=ndwi_threshold,
            max_cloud_cover=max_cloud_cover,
            datetime_range=datetime_range,
            data_source=data_source,
        )
        session.refresh(run)
    elif background_tasks is not None:
        session.commit()
        background_tasks.add_task(
            execute_pipeline_worker,
            run_id=run.id,
            user=user,
            bbox=bbox,
            ndwi_threshold=ndwi_threshold,
            max_cloud_cover=max_cloud_cover,
            datetime_range=datetime_range,
            data_source=data_source,
        )
    else:
        session.commit()

    return run
