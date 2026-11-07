"""DharaScope - Phase 1: Satellite Feasibility Validation
Master execution and reporting pipeline.
"""

import src.config  # MUST be first to configure PROJ_DATA/PROJ_LIB before rasterio/GDAL initialize
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import rasterio

from src.config import (
    BASE_DIR,
    CDSE_COLLECTION,
    CDSE_STAC_BASE_URL,
    GOMTI_BBOX,
    LOGS_DIR,
    METADATA_DIR,
    NDWI_WATER_THRESHOLD,
    OUTPUTS_DIR,
    RAW_DATA_DIR,
)
from src.stac_client import CDSESTACClient, STACError
from src.scene_selection import SceneSelector, SceneSelectionError
from src.downloader import (
    CDSEDownloader,
    AuthenticationRequiredError,
    DownloadError,
    verify_raster_file,
)
from src.water_indices import process_scene_bands
from src.change_detection import compute_water_change, LIMITATION_STATEMENT
from src.visualization import (
    plot_single_observation,
    plot_water_change_map,
    plot_four_panel_comparison,
)

# Setup root logging
log_file = LOGS_DIR / "phase1_feasibility.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dhara_scope.main")


def run_pipeline(
    datetime_range: str = "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
    max_cloud_cover: float = 10.0,
    threshold: float = NDWI_WATER_THRESHOLD,
    data_source: str = "auto",
) -> Dict[str, Any]:
    """Execute the Phase 1 Feasibility Pipeline.

    Args:
        datetime_range: STAC interval for scene search.
        max_cloud_cover: Cloud filtering threshold.
        threshold: NDWI water classification cutoff.
        data_source: "auto" (CDSE -> Public COG -> Synthetic), "cdse", "public", or "synthetic".

    Returns:
        Structured feasibility report dictionary.
    """
    logger.info("=" * 70)
    logger.info("DHARASCOPE - PHASE 1: SATELLITE FEASIBILITY VALIDATION")
    logger.info("Objective: Validate water-covered area change detection along Gomti River (Lucknow)")
    logger.info("Study Bounding Box: %s", GOMTI_BBOX)
    logger.info("NDWI Threshold: %.2f", threshold)
    logger.info("Data Retrieval Mode: %s", data_source.upper())
    logger.info("=" * 70)

    report: Dict[str, Any] = {
        "project": "DharaScope",
        "phase": "Phase 1 - Satellite Feasibility Validation",
        "execution_timestamp": datetime.utcnow().isoformat() + "Z",
        "parameters": {
            "study_bbox": GOMTI_BBOX,
            "stac_endpoint": CDSE_STAC_BASE_URL,
            "collection": CDSE_COLLECTION,
            "search_datetime_range": datetime_range,
            "max_cloud_filter": max_cloud_cover,
            "ndwi_classification_threshold": threshold,
            "data_retrieval_mode": data_source,
        },
        "stages": {},
        "blockers": [],
        "evidence_files": [],
        "data_source_provenance": {},
        "limitation_notice": LIMITATION_STATEMENT,
    }

    # ---------------------------------------------------------
    # STAGE 1: Environment & Tooling Verification
    # ---------------------------------------------------------
    logger.info("[Step 1] Environment & Tooling Verification")
    env_info = {
        "python_version": sys.version.split()[0],
        "rasterio_version": rasterio.__version__,
        "numpy_version": np.__version__,
        "virtual_environment": sys.prefix != sys.base_prefix,
    }
    report["stages"]["environment_inspection"] = {
        "status": "SUCCESS",
        "details": env_info,
    }
    logger.info("Environment OK: Python %s, Rasterio %s, Numpy %s",
                env_info["python_version"], env_info["rasterio_version"], env_info["numpy_version"])

    # ---------------------------------------------------------
    # STAGE 2: Data-Access Route & STAC Catalogue Verification
    # ---------------------------------------------------------
    logger.info("[Step 2] Querying official Copernicus Data Space STAC API...")
    stac_client = CDSESTACClient()
    selector = SceneSelector(stac_client=stac_client, study_bbox=GOMTI_BBOX)

    try:
        earlier_scene, later_scene, candidates = selector.select_observation_pair(
            datetime_range=datetime_range,
            max_cloud_cover=max_cloud_cover,
            min_temporal_gap_days=30,
        )
        report["stages"]["catalogue_discovery"] = {
            "status": "SUCCESS",
            "total_candidates_found": len(candidates),
            "earlier_scene_id": earlier_scene["id"],
            "earlier_date": earlier_scene["datetime"],
            "earlier_cloud_cover": earlier_scene["cloud_cover"],
            "later_scene_id": later_scene["id"],
            "later_date": later_scene["datetime"],
            "later_cloud_cover": later_scene["cloud_cover"],
        }
        logger.info("Catalogue discovery SUCCESS. Found %d valid candidates covering 100%% of study area.",
                    len(candidates))
    except (STACError, SceneSelectionError) as exc:
        logger.error("Catalogue discovery FAILED: %s", exc)
        report["stages"]["catalogue_discovery"] = {
            "status": "FAILED",
            "error": str(exc),
        }
        report["blockers"].append(f"Catalogue discovery failed: {exc}")
        return report

    # ---------------------------------------------------------
    # STAGE 3: Retrieve Visual Overview Evidence
    # ---------------------------------------------------------
    logger.info("[Step 3] Retrieving visual overview thumbnails...")
    downloader = CDSEDownloader()
    thumb1_path = OUTPUTS_DIR / f"{earlier_scene['id']}_thumbnail.jpg"
    thumb2_path = OUTPUTS_DIR / f"{later_scene['id']}_thumbnail.jpg"

    p1 = downloader.download_thumbnail(earlier_scene, thumb1_path)
    p2 = downloader.download_thumbnail(later_scene, thumb2_path)
    thumb_files = []
    if p1 and p1.exists():
        rel1 = str(p1.relative_to(BASE_DIR))
        report["evidence_files"].append(rel1)
        thumb_files.append(rel1)
    if p2 and p2.exists():
        rel2 = str(p2.relative_to(BASE_DIR))
        report["evidence_files"].append(rel2)
        thumb_files.append(rel2)

    report["stages"]["thumbnail_retrieval"] = {
        "status": "SUCCESS" if len(thumb_files) == 2 else ("PARTIAL" if thumb_files else "FAILED"),
        "thumbnails": thumb_files,
    }

    # ---------------------------------------------------------
    # STAGE 4: Spectral Raster Data Retrieval
    # ---------------------------------------------------------
    logger.info("[Step 4] Retrieving Sentinel-2 Level-2A B03 (Green) and B08 (NIR) rasters...")
    raster_retrieval_success = False
    provider_used = "UNKNOWN"

    t1_b03_file: Optional[Path] = None
    t1_b08_file: Optional[Path] = None
    t2_b03_file: Optional[Path] = None
    t2_b08_file: Optional[Path] = None

    try:
        t1_b03_file, p1 = downloader.retrieve_band(
            earlier_scene, "B03", mode=data_source, clip_bbox=GOMTI_BBOX, is_earlier=True
        )
        t1_b08_file, _ = downloader.retrieve_band(
            earlier_scene, "B08", mode=data_source, clip_bbox=GOMTI_BBOX, is_earlier=True
        )
        t2_b03_file, p2 = downloader.retrieve_band(
            later_scene, "B03", mode=data_source, clip_bbox=GOMTI_BBOX, is_earlier=False
        )
        t2_b08_file, _ = downloader.retrieve_band(
            later_scene, "B08", mode=data_source, clip_bbox=GOMTI_BBOX, is_earlier=False
        )

        provider_used = p1
        raster_retrieval_success = True

        if provider_used == "COPERNICUS_CDSE_AUTHENTICATED":
            prov_desc = "Official Copernicus Data Space Ecosystem (CDSE) Keycloak/OData Authenticated Access"
            is_real = True
        elif provider_used == "PUBLIC_OPEN_SENTINEL2_COGS":
            prov_desc = "Public Open Sentinel-2 Level-2A Cloud-Optimized GeoTIFF Archive (AWS Registry of Open Data / ESA)"
            is_real = True
        else:
            prov_desc = "SYNTHETIC BENCHMARK SAMPLE (Simulated data for offline demonstration only; NOT real satellite observations)"
            is_real = False

        report["data_source_provenance"] = {
            "provider": provider_used,
            "is_real_satellite_data": is_real,
            "description": prov_desc,
        }

        report["stages"]["real_raster_retrieval"] = {
            "status": "SUCCESS" if is_real else "FALLBACK_SYNTHETIC_SAMPLE",
            "provider": provider_used,
            "description": prov_desc,
            "files": [f.name for f in [t1_b03_file, t1_b08_file, t2_b03_file, t2_b08_file] if f],
        }

        if not is_real:
            report["blockers"].append(
                "Offline/synthetic benchmark sample data used. Configure CDSE credentials or enable public internet access for live satellite imagery."
            )

    except Exception as exc:
        logger.error("Spectral raster retrieval failed: %s", exc)
        report["stages"]["real_raster_retrieval"] = {
            "status": "FAILED",
            "error": str(exc),
        }
        report["blockers"].append(f"Raster retrieval failed: {exc}")

    # ---------------------------------------------------------
    # STAGE 5 & 6: Water Index Calculation & Change Detection
    # ---------------------------------------------------------
    if raster_retrieval_success and t1_b03_file and t1_b08_file and t2_b03_file and t2_b08_file:
        logger.info("[Step 5] Calculating NDWI for both observations...")
        res_t1 = process_scene_bands(t1_b03_file, t1_b08_file, clip_bbox=GOMTI_BBOX, threshold=threshold)
        res_t2 = process_scene_bands(t2_b03_file, t2_b08_file, clip_bbox=GOMTI_BBOX, threshold=threshold)

        date_t1 = earlier_scene["datetime"][:10]
        date_t2 = later_scene["datetime"][:10]

        # Determine provenance badge for figures
        if provider_used == "SYNTHETIC_BENCHMARK_SAMPLE":
            badge = "BENCHMARK SAMPLE DATA (SYNTHETIC — NOT REAL SATELLITE DATA)"
            status_label = "SUCCESS_SYNTHETIC_SAMPLE"
        elif provider_used == "PUBLIC_OPEN_SENTINEL2_COGS":
            badge = "Validated Real Satellite Data: Sentinel-2 L2A (AWS Open Data / ESA)"
            status_label = "SUCCESS_REAL_DATA"
        else:
            badge = "Validated Real Satellite Data: Sentinel-2 L2A (Copernicus CDSE)"
            status_label = "SUCCESS_REAL_DATA"

        p_t1 = plot_single_observation(
            res_t1["ndwi"], res_t1["water_mask"], date_t1, earlier_scene["id"],
            OUTPUTS_DIR / f"observation_{date_t1}_ndwi.png",
            provenance_label=badge,
        )
        p_t2 = plot_single_observation(
            res_t2["ndwi"], res_t2["water_mask"], date_t2, later_scene["id"],
            OUTPUTS_DIR / f"observation_{date_t2}_ndwi.png",
            provenance_label=badge,
        )
        report["evidence_files"].extend([str(p_t1.relative_to(BASE_DIR)), str(p_t2.relative_to(BASE_DIR))])

        report["stages"]["real_ndwi_calculation"] = {
            "status": status_label,
            "provider": provider_used,
            "threshold": threshold,
            "earlier_date": date_t1,
            "earlier_water_pixels": int(np.count_nonzero(res_t1["water_mask"])),
            "later_date": date_t2,
            "later_water_pixels": int(np.count_nonzero(res_t2["water_mask"])),
            "crs": res_t1["crs"],
            "pixel_area_m2": res_t1["pixel_area_m2"],
        }

        logger.info("[Step 6] Comparing observations and computing water extent change...")
        change_res = compute_water_change(
            res_t1["water_mask"],
            res_t2["water_mask"],
            res_t1["valid_mask"],
            res_t2["valid_mask"],
            pixel_area_m2=res_t1["pixel_area_m2"],
        )

        p_ch = plot_water_change_map(
            change_res["change_matrix"], change_res["statistics"], date_t1, date_t2,
            OUTPUTS_DIR / f"water_change_{date_t1}_to_{date_t2}.png",
            provenance_label=badge,
        )
        p_panel = plot_four_panel_comparison(
            res_t1["ndwi"], res_t1["water_mask"], date_t1,
            res_t2["ndwi"], res_t2["water_mask"], date_t2,
            change_res["change_matrix"], change_res["statistics"],
            OUTPUTS_DIR / "gomti_water_change_comparison_panel.png",
            provenance_label=badge,
        )
        report["evidence_files"].extend([str(p_ch.relative_to(BASE_DIR)), str(p_panel.relative_to(BASE_DIR))])

        report["stages"]["real_change_detection"] = {
            "status": status_label,
            "provider": provider_used,
            "statistics": change_res["statistics"],
        }
    else:
        report["stages"]["real_ndwi_calculation"] = {
            "status": "PENDING_RASTERS",
            "message": "NDWI calculation requires valid Level-2A band rasters.",
        }
        report["stages"]["real_change_detection"] = {
            "status": "PENDING_RASTERS",
            "message": "Water change detection requires calculated NDWI layers.",
        }

    # ---------------------------------------------------------
    # STAGE 7: Save Reproducible Audit Evidence
    # ---------------------------------------------------------
    report_file = OUTPUTS_DIR / "phase1_feasibility_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Saved Phase 1 feasibility audit report to %s", report_file)

    logger.info("=" * 70)
    logger.info("PHASE 1 SUMMARY REPORT:")
    for stage_name, stage_data in report["stages"].items():
        logger.info("  * %-30s : %s", stage_name, stage_data.get("status"))
    logger.info("  * Data Provenance Provider       : %s", provider_used)
    if report["blockers"]:
        logger.info("Current Blockers:")
        for b in report["blockers"]:
            logger.info("  ! %s", b)
    else:
        logger.info("Status: 100%% END-TO-END PIPELINE SUCCESS (No Blockers)")
    logger.info("=" * 70)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DharaScope Phase 1 Satellite Feasibility Pipeline")
    parser.add_argument("--date-range", default="2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
                        help="STAC RFC3339 datetime interval")
    parser.add_argument("--max-cloud", type=float, default=10.0, help="Maximum scene cloud cover percentage")
    parser.add_argument("--threshold", type=float, default=NDWI_WATER_THRESHOLD, help="NDWI water threshold")
    parser.add_argument(
        "--source",
        choices=["auto", "cdse", "public", "synthetic"],
        default="auto",
        help="Data retrieval mode: 'auto' (CDSE -> Public COG -> Synthetic), 'cdse', 'public', or 'synthetic'"
    )
    args = parser.parse_args()

    run_pipeline(
        datetime_range=args.date_range,
        max_cloud_cover=args.max_cloud,
        threshold=args.threshold,
        data_source=args.source,
    )
