"""Scene selection module for identifying optimal Sentinel-2 observation pairs."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from shapely.geometry import box, shape

from src.config import GOMTI_BBOX, METADATA_DIR
from src.stac_client import CDSESTACClient, STACError

logger = logging.getLogger("dhara_scope.scene_selection")


class SceneSelectionError(Exception):
    """Raised when suitable observation pairs cannot be selected."""
    pass


class SceneSelector:
    """Evaluates and selects suitable pairs of Sentinel-2 observations for Gomti River monitoring."""

    def __init__(self, stac_client: Optional[CDSESTACClient] = None, study_bbox: Optional[List[float]] = None):
        self.client = stac_client or CDSESTACClient()
        self.study_bbox = study_bbox or GOMTI_BBOX
        self.study_geom = box(*self.study_bbox)

    def select_observation_pair(
        self,
        datetime_range: str = "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
        max_cloud_cover: float = 10.0,
        min_temporal_gap_days: int = 30
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
        """Search and select two high-quality, low-cloud observations covering the Gomti River study area.

        Args:
            datetime_range: Period to search.
            max_cloud_cover: Cloud filter threshold.
            min_temporal_gap_days: Minimum days between observations.

        Returns:
            Tuple of (earlier_scene_meta, later_scene_meta, all_candidates)
        """
        cached_file = METADATA_DIR / "selected_scenes.json"

        try:
            raw_features = self.client.search_scenes(
                bbox=self.study_bbox,
                datetime_range=datetime_range,
                max_cloud_cover=max_cloud_cover,
                limit_per_page=50,
                max_items=100
            )
        except Exception as exc:
            if cached_file.exists():
                logger.warning(
                    "Live CDSE STAC search failed (%s). Falling back to verified cached scene metadata: %s",
                    exc,
                    cached_file,
                )
                with open(cached_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return (
                    cached_data["selected_earlier_scene"],
                    cached_data["selected_later_scene"],
                    cached_data.get("candidates_overview", []),
                )
            raise SceneSelectionError(f"STAC search failed and no cached scenes exist: {exc}") from exc

        if not raw_features:
            if cached_file.exists():
                logger.warning("Empty search results. Falling back to cached scene selection metadata.")
                with open(cached_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return (
                    cached_data["selected_earlier_scene"],
                    cached_data["selected_later_scene"],
                    cached_data.get("candidates_overview", []),
                )
            msg = (
                f"No Sentinel-2 scenes found for bbox={self.study_bbox} in range={datetime_range} "
                f"with cloud_cover<={max_cloud_cover}%."
            )
            logger.error(msg)
            raise SceneSelectionError(msg)

        candidates = []
        for feat in raw_features:
            meta = self.client.extract_item_metadata(feat)
            if not meta.get("geometry"):
                continue

            feat_geom = shape(meta["geometry"])
            if not feat_geom.intersects(self.study_geom):
                continue

            intersection_area = feat_geom.intersection(self.study_geom).area
            coverage_pct = (intersection_area / self.study_geom.area) * 100.0
            meta["coverage_pct"] = round(coverage_pct, 2)

            # Must fully cover Gomti study area (coverage >= 99.9%)
            if coverage_pct >= 99.9:
                candidates.append(meta)

        if len(candidates) < 2:
            if cached_file.exists():
                logger.warning(
                    "Found only %d candidate(s). Falling back to verified cached scene selection metadata.",
                    len(candidates),
                )
                with open(cached_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                return (
                    cached_data["selected_earlier_scene"],
                    cached_data["selected_later_scene"],
                    cached_data.get("candidates_overview", []),
                )
            msg = (
                f"Insufficient fully covering scenes found (needed >=2, got {len(candidates)}). "
                f"Consider expanding the date range or allowing slightly higher cloud cover threshold."
            )
            logger.error(msg)
            raise SceneSelectionError(msg)

        # Sort candidates chronologically
        candidates.sort(key=lambda x: x["datetime"])

        # Find best pair with lowest cloud cover and adequate temporal separation
        best_pair = None
        best_combined_cloud = float("inf")

        for i in range(len(candidates)):
            dt_i = datetime.fromisoformat(candidates[i]["datetime"].replace("Z", "+00:00"))
            cloud_i = candidates[i]["cloud_cover"] or 0.0

            for j in range(i + 1, len(candidates)):
                dt_j = datetime.fromisoformat(candidates[j]["datetime"].replace("Z", "+00:00"))
                cloud_j = candidates[j]["cloud_cover"] or 0.0

                gap_days = abs((dt_j - dt_i).days)
                if gap_days >= min_temporal_gap_days:
                    combined_cloud = cloud_i + cloud_j
                    if combined_cloud < best_combined_cloud:
                        best_combined_cloud = combined_cloud
                        best_pair = (candidates[i], candidates[j])

        if not best_pair:
            best_pair = (candidates[0], candidates[-1])
            logger.warning(
                "Could not strictly satisfy cloud optimization with temporal gap >= %d days. Selected widest interval.",
                min_temporal_gap_days
            )

        earlier_scene, later_scene = best_pair
        logger.info(
            "Selected Scene 1 (Earlier): %s (Date: %s, Cloud: %s%%)",
            earlier_scene["id"], earlier_scene["datetime"], earlier_scene["cloud_cover"]
        )
        logger.info(
            "Selected Scene 2 (Later): %s (Date: %s, Cloud: %s%%)",
            later_scene["id"], later_scene["datetime"], later_scene["cloud_cover"]
        )

        summary_payload = {
            "study_area_bbox": self.study_bbox,
            "datetime_search_range": datetime_range,
            "max_cloud_cover_filter": max_cloud_cover,
            "total_candidates_found": len(candidates),
            "selected_earlier_scene": earlier_scene,
            "selected_later_scene": later_scene,
            "candidates_overview": [
                {
                    "id": c["id"],
                    "datetime": c["datetime"],
                    "cloud_cover": c["cloud_cover"],
                    "tile_id": c["tile_id"],
                    "coverage_pct": c["coverage_pct"]
                }
                for c in candidates
            ]
        }

        output_path = METADATA_DIR / "selected_scenes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)
        logger.info("Saved scene selection evidence to %s", output_path)

        return earlier_scene, later_scene, candidates
