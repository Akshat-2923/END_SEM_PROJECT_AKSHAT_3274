"""Copernicus Data Space Ecosystem (CDSE) STAC API Client."""

import logging
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import CDSE_COLLECTION, CDSE_STAC_BASE_URL, LOGS_DIR

logger = logging.getLogger("dhara_scope.stac")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOGS_DIR / "stac_client.log", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


class STACError(Exception):
    """Custom exception raised for STAC API errors."""
    pass


class CDSESTACClient:
    """Client for interacting with the Copernicus Data Space Ecosystem STAC API."""

    def __init__(self, base_url: str = CDSE_STAC_BASE_URL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.search_url = f"{self.base_url}/search"
        self.timeout = timeout
        self.session = self._create_resilient_session()

    @staticmethod
    def _create_resilient_session() -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def search_scenes(
        self,
        bbox: List[float],
        datetime_range: str,
        collection: str = CDSE_COLLECTION,
        max_cloud_cover: Optional[float] = None,
        limit_per_page: int = 50,
        max_items: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """Search Sentinel-2 scenes matching criteria, handling pagination.

        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat] in WGS84.
            datetime_range: RFC 3339 formatted interval, e.g. "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z".
            collection: STAC collection name (default sentinel-2-l2a).
            max_cloud_cover: Optional maximum cloud cover percentage (0-100).
            limit_per_page: Number of items per page.
            max_items: Total maximum items to retrieve across pages.

        Returns:
            List of parsed STAC feature dictionaries.
        """
        if len(bbox) != 4:
            raise ValueError(f"bbox must contain exactly 4 floats [min_lon, min_lat, max_lon, max_lat]. Got {bbox}")
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            raise ValueError(f"Invalid bounding box coordinates: {bbox}")

        payload: Dict[str, Any] = {
            "collections": [collection],
            "bbox": bbox,
            "datetime": datetime_range,
            "limit": limit_per_page
        }

        if max_cloud_cover is not None:
            payload["query"] = {
                "eo:cloud_cover": {"lte": float(max_cloud_cover)}
            }

        logger.info(
            "Initiating CDSE STAC search: collection=%s, bbox=%s, datetime=%s, max_cloud=%s",
            collection, bbox, datetime_range, max_cloud_cover
        )

        all_features: List[Dict[str, Any]] = []
        next_url: Optional[str] = None
        current_payload: Optional[Dict[str, Any]] = payload
        page_idx = 1

        while True:
            try:
                if next_url:
                    logger.debug("Requesting next page: %s", next_url)
                    response = self.session.get(next_url, timeout=self.timeout)
                else:
                    logger.debug("Posting STAC search payload: %s", current_payload)
                    response = self.session.post(self.search_url, json=current_payload, timeout=self.timeout)

            except requests.exceptions.Timeout as exc:
                msg = f"CDSE STAC API request timed out after {self.timeout}s: {exc}"
                logger.error(msg)
                raise STACError(msg) from exc
            except requests.exceptions.RequestException as exc:
                msg = f"Network failure communicating with CDSE STAC API: {exc}"
                logger.error(msg)
                raise STACError(msg) from exc

            if response.status_code != 200:
                msg = f"CDSE STAC API returned HTTP {response.status_code}: {response.text[:300]}"
                logger.error(msg)
                raise STACError(msg)

            try:
                data = response.json()
            except ValueError as exc:
                msg = f"Malformed JSON response received from STAC API: {response.text[:200]}"
                logger.error(msg)
                raise STACError(msg) from exc

            features = data.get("features", [])
            logger.info("Page %d retrieved %d features", page_idx, len(features))
            all_features.extend(features)

            if max_items and len(all_features) >= max_items:
                all_features = all_features[:max_items]
                logger.info("Reached requested max_items limit of %d", max_items)
                break

            # Check pagination links
            links = data.get("links", [])
            next_link = next((lnk for lnk in links if lnk.get("rel") == "next"), None)
            if not next_link or not next_link.get("href"):
                break

            next_url = next_link.get("href")
            current_payload = None
            page_idx += 1

        logger.info("STAC search completed: total %d items retrieved", len(all_features))
        return all_features

    @staticmethod
    def extract_item_metadata(feature: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized scene metadata from a raw STAC item."""
        props = feature.get("properties", {})
        assets = feature.get("assets", {})

        def get_band_info(band_key_prefix: str) -> Optional[Dict[str, Any]]:
            # S2 STAC assets are often named e.g. B03_10m or B03
            for key, asset in assets.items():
                if key.upper().startswith(band_key_prefix.upper()):
                    alt_https = (
                        asset.get("alternate", {}).get("https", {}).get("href")
                        or asset.get("alternate", {}).get("HTTPS", {}).get("href")
                    )
                    return {
                        "asset_key": key,
                        "s3_href": asset.get("href"),
                        "https_href": alt_https,
                        "type": asset.get("type"),
                        "roles": asset.get("roles", []),
                        "file_size": asset.get("file:size")
                    }
            return None

        thumb_asset = assets.get("thumbnail") or assets.get("overview")
        thumbnail_url = thumb_asset.get("href") if thumb_asset else None

        item_id = feature.get("id", "UNKNOWN")
        tile_id = props.get("s2:mgrs_tile")
        if not tile_id and "_" in item_id:
            # Fallback parse tile ID from S2 SAFE naming convention e.g. T44RMQ
            parts = item_id.split("_")
            for p in parts:
                if len(p) == 6 and p.startswith("T") and p[1:3].isdigit():
                    tile_id = p
                    break

        return {
            "id": item_id,
            "collection": feature.get("collection", CDSE_COLLECTION),
            "datetime": props.get("datetime"),
            "cloud_cover": props.get("eo:cloud_cover"),
            "platform": props.get("platform"),
            "tile_id": tile_id,
            "geometry": feature.get("geometry"),
            "bbox": feature.get("bbox"),
            "thumbnail_url": thumbnail_url,
            "b03_asset": get_band_info("B03"),
            "b08_asset": get_band_info("B08"),
            "total_assets_count": len(assets),
            "asset_keys": list(assets.keys())
        }
