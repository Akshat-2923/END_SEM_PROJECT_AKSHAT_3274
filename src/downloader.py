"""Copernicus Data Space Ecosystem (CDSE) Raster Downloader.

Implements robust authentication and retrieval of Sentinel-2 Level-2A rasters,
following official Copernicus Data Space Ecosystem documentation:
- Primary Route: OAuth2 token retrieval via Keycloak endpoint and OData single-band leaf node retrieval (B03/B08 10m JP2)
- Public Sentinel-2 Fallback: Open-access Level-2A Cloud-Optimized GeoTIFFs (COGs) from AWS Registry of Open Data / Earth Search
- Offline Synthetic Fallback: Georeferenced Level-2A synthetic sample benchmark data for offline presentations and testing
- Rigorous raster integrity, CRS, dimension, and content-type validation
"""

import logging
import os
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from src.config import (
    CDSE_ACCESS_TOKEN,
    CDSE_CLIENT_ID,
    CDSE_OAUTH_CLIENT_ID,
    CDSE_OAUTH_CLIENT_SECRET,
    CDSE_PASSWORD,
    CDSE_PROCESS_API_URL,
    CDSE_TOKEN_URL,
    CDSE_USERNAME,
    GOMTI_BBOX,
    LOGS_DIR,
    RAW_DATA_DIR,
)

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.mask import mask
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from shapely.geometry import box, mapping

logger = logging.getLogger("dhara_scope.downloader")


class AuthenticationRequiredError(Exception):
    """Raised when an authenticated CDSE operation is attempted without valid credentials."""
    pass


class DownloadError(Exception):
    """Raised when downloading a raster asset fails."""
    pass


def _mask_identity(val: Optional[str]) -> str:
    """Mask email or username for secure logging without disclosing sensitive details."""
    if not val:
        return "[not configured]"
    if "@" in val:
        user_part, domain = val.split("@", 1)
        masked_user = user_part[:2] + "***" if len(user_part) > 2 else "***"
        return f"{masked_user}@{domain}"
    if len(val) > 3:
        return val[:2] + "***"
    return "***"


class LocationTrustedSession(requests.Session):
    """Requests Session that preserves Authorization header across Copernicus redirect domains.

    Matches curl's `--location-trusted` flag recommended in official CDSE documentation,
    while safely stripping Authorization if redirected to AWS S3 presigned URLs.
    """

    TRUSTED_DOMAINS = (
        "copernicus.eu",
        "dataspace.copernicus.eu",
        "creodias.eu",
        "cloudferro.com",
    )

    def should_strip_auth(self, old_url: str, new_url: str) -> bool:
        if "X-Amz-Signature" in new_url:
            return True
        new_host = urllib.parse.urlparse(new_url).hostname or ""
        if any(new_host == d or new_host.endswith("." + d) for d in self.TRUSTED_DOMAINS):
            return False
        return super().should_strip_auth(old_url, new_url)


def verify_raster_file(file_path: Path) -> bool:
    """Check whether a downloaded file is a valid, readable raster using rasterio.

    Args:
        file_path: Path to the raster file.

    Returns:
        True if the file can be opened, has valid dimensions, CRS, and bands; False otherwise.
    """
    if not file_path.exists() or file_path.stat().st_size < 100_000:
        return False
    try:
        with rasterio.open(file_path) as src:
            if src.count < 1 or src.width <= 0 or src.height <= 0:
                return False
            if not src.crs:
                return False
            return True
    except Exception as exc:
        logger.debug("Raster verification failed for %s: %s", file_path.name, exc)
        return False


class CDSEDownloader:
    """Manages authentication, raster downloads, and robust fallbacks for DharaScope."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        oauth_client_id: Optional[str] = None,
        oauth_client_secret: Optional[str] = None,
    ):
        self.username = username if username is not None else CDSE_USERNAME
        self.password = password if password is not None else CDSE_PASSWORD
        self._access_token = access_token if access_token is not None else CDSE_ACCESS_TOKEN
        self.oauth_client_id = oauth_client_id if oauth_client_id is not None else CDSE_OAUTH_CLIENT_ID
        self.oauth_client_secret = (
            oauth_client_secret if oauth_client_secret is not None else CDSE_OAUTH_CLIENT_SECRET
        )
        self.session = LocationTrustedSession()

    def has_credentials(self) -> bool:
        """Check if any CDSE authentication method is configured."""
        return bool(
            self._access_token
            or (self.username and self.password)
            or (self.oauth_client_id and self.oauth_client_secret)
        )

    def has_oauth_client(self) -> bool:
        """Check if CDSE Sentinel Hub OAuth Client credentials are configured."""
        return bool(self.oauth_client_id and self.oauth_client_secret)

    def authenticate(self) -> str:
        """Obtain a valid bearer access token from CDSE Keycloak or configured environment.

        Returns:
            Bearer access token string.

        Raises:
            AuthenticationRequiredError: If credentials are not provided or authentication fails.
        """
        if self._access_token:
            logger.info("Using pre-configured CDSE access token.")
            return self._access_token

        # Check standard user credentials
        if self.username and self.password:
            logger.info(
                "Authenticating with CDSE Keycloak service for user: %s",
                _mask_identity(self.username),
            )
            auth_data = {
                "client_id": CDSE_CLIENT_ID,
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
            }
            try:
                resp = self.session.post(CDSE_TOKEN_URL, data=auth_data, timeout=30)
            except requests.exceptions.RequestException as exc:
                msg = f"Network failure contacting CDSE authentication endpoint: {exc}"
                logger.error(msg)
                raise AuthenticationRequiredError(msg) from exc

            if resp.status_code != 200:
                msg = (
                    f"CDSE Authentication failed (HTTP {resp.status_code}): {resp.text[:300]}\n"
                    "Please verify your username and password at https://dataspace.copernicus.eu/."
                )
                logger.error(msg)
                raise AuthenticationRequiredError(msg)

            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise AuthenticationRequiredError("Token response did not include 'access_token'.")

            self._access_token = token
            logger.info(
                "Successfully obtained CDSE bearer token (expires_in: %ss)",
                data.get("expires_in", "unknown"),
            )
            return token

        # Check OAuth client credentials
        if self.oauth_client_id and self.oauth_client_secret:
            logger.info(
                "Authenticating with CDSE Keycloak service via OAuth Client: %s",
                _mask_identity(self.oauth_client_id),
            )
            auth_data = {
                "client_id": self.oauth_client_id,
                "client_secret": self.oauth_client_secret,
                "grant_type": "client_credentials",
            }
            try:
                resp = self.session.post(CDSE_TOKEN_URL, data=auth_data, timeout=30)
            except requests.exceptions.RequestException as exc:
                msg = f"Network failure contacting CDSE authentication endpoint: {exc}"
                logger.error(msg)
                raise AuthenticationRequiredError(msg) from exc

            if resp.status_code != 200:
                msg = (
                    f"CDSE OAuth Client Authentication failed (HTTP {resp.status_code}): {resp.text[:300]}\n"
                    "Verify your OAuth client credentials generated on CDSE Dashboard."
                )
                logger.error(msg)
                raise AuthenticationRequiredError(msg)

            data = resp.json()
            token = data.get("access_token")
            if not token:
                raise AuthenticationRequiredError("Token response did not include 'access_token'.")

            self._access_token = token
            logger.info(
                "Successfully obtained CDSE OAuth bearer token (expires_in: %ss)",
                data.get("expires_in", "unknown"),
            )
            return token

        msg = (
            "Copernicus Data Space Ecosystem (CDSE) credentials are not configured.\n"
            "To download real Level-2A raster assets (B03/B08) from CDSE, follow these steps:\n"
            "1. Register a free account at: https://dataspace.copernicus.eu/\n"
            "2. Create a .env file in the DharaScope root directory (or copy from .env.example).\n"
            "3. Set your credentials:\n"
            "   CDSE_USERNAME=your_username_or_email\n"
            "   CDSE_PASSWORD=your_password\n"
            "4. Alternatively, configure CDSE_ACCESS_TOKEN if generated externally."
        )
        logger.warning(msg)
        raise AuthenticationRequiredError(msg)

    def download_thumbnail(self, scene_meta: Dict[str, Any], output_path: Path) -> Optional[Path]:
        """Download scene overview thumbnail (typically unauthenticated browse image)."""
        thumb_url = scene_meta.get("thumbnail_url")
        if not thumb_url:
            logger.warning("Scene %s does not list a thumbnail URL.", scene_meta.get("id"))
            return None

        try:
            resp = self.session.get(thumb_url, timeout=20, stream=True)
            if resp.status_code in (200, 206):
                ctype = resp.headers.get("content-type", "").lower()
                if "html" in ctype or "json" in ctype:
                    logger.warning("Thumbnail returned non-image content-type '%s' for %s", ctype, thumb_url)
                    return None
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                logger.info("Saved overview thumbnail (%d bytes) to %s", output_path.stat().st_size, output_path)
                return output_path
            else:
                logger.warning("Thumbnail download returned HTTP %s for %s", resp.status_code, thumb_url)
        except Exception as exc:
            logger.warning("Failed to fetch thumbnail for %s: %s", scene_meta.get("id"), exc)

        return None

    def download_band(
        self,
        scene_meta: Dict[str, Any],
        band: str,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Download Sentinel-2 Level-2A 10m raster file for a specific band (B03 or B08) from CDSE.

        Validates HTTP status code, follows trusted redirects, checks content-type,
        file size, and verifies raster integrity via rasterio.
        """
        token = self.authenticate()
        target_dir = output_dir or RAW_DATA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        asset_key = "b03_asset" if band.upper() == "B03" else "b08_asset"
        asset_info = scene_meta.get(asset_key)

        if not asset_info or not asset_info.get("https_href"):
            raise DownloadError(
                f"Scene {scene_meta.get('id')} does not have HTTPS download URL for band {band}."
            )

        download_url = asset_info["https_href"]
        file_name = f"{scene_meta['id']}_{band.upper()}_10m.jp2"
        dest_path = target_dir / file_name

        if dest_path.exists():
            if verify_raster_file(dest_path):
                logger.info(
                    "Band raster already exists and is verified valid on disk: %s (%d bytes)",
                    dest_path.name,
                    dest_path.stat().st_size,
                )
                return dest_path
            else:
                logger.warning(
                    "Cached file %s is corrupt or incomplete. Re-downloading...",
                    dest_path.name,
                )
                dest_path.unlink(missing_ok=True)

        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Downloading %s band raster from: %s", band, download_url)

        try:
            with self.session.get(download_url, headers=headers, stream=True, timeout=90) as resp:
                if resp.status_code in (401, 403):
                    msg = (
                        f"CDSE Download Unauthorized (HTTP {resp.status_code}) for band {band}.\n"
                        f"Response: {resp.text[:300]}\n"
                        "Verify your credentials or refresh your access token."
                    )
                    logger.error(msg)
                    raise AuthenticationRequiredError(msg)

                if resp.status_code != 200:
                    raise DownloadError(
                        f"Failed downloading {band} from CDSE: HTTP {resp.status_code} - {resp.text[:200]}"
                    )

                content_type = resp.headers.get("content-type", "").lower()
                if any(err_type in content_type for err_type in ["text/html", "application/json", "application/xml"]):
                    raise DownloadError(
                        f"Failed downloading {band}: Server returned '{content_type}' instead of raster binary. "
                        f"Response preview: {resp.text[:300]}"
                    )

                temp_path = dest_path.with_suffix(".tmp")
                total_bytes = 0
                with open(temp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)

                if total_bytes < 1_000_000:
                    temp_path.unlink(missing_ok=True)
                    raise DownloadError(
                        f"Downloaded file for {band} is suspiciously small ({total_bytes} bytes). "
                        "Expected > 10 MB raster binary."
                    )

                try:
                    with rasterio.open(temp_path) as src:
                        if src.count < 1 or src.width <= 0 or src.height <= 0:
                            raise DownloadError(f"Raster has invalid dimensions: {src.width}x{src.height}")
                        if not src.crs:
                            raise DownloadError("Raster is missing CRS metadata.")
                        logger.info(
                            "Verified valid %s raster: %dx%d, CRS=%s, driver=%s",
                            band,
                            src.width,
                            src.height,
                            src.crs,
                            src.driver,
                        )
                except Exception as exc:
                    temp_path.unlink(missing_ok=True)
                    raise DownloadError(f"Downloaded file for {band} is not a valid JP2 raster: {exc}") from exc

                temp_path.replace(dest_path)
                logger.info(
                    "Successfully downloaded and verified %s (%d bytes) to %s",
                    band,
                    total_bytes,
                    dest_path.name,
                )
                return dest_path

        except requests.exceptions.RequestException as exc:
            msg = f"Network failure during raster download for {band}: {exc}"
            logger.error(msg)
            raise DownloadError(msg) from exc

    def download_band_public_cog(
        self,
        scene_meta: Dict[str, Any],
        band: str,
        output_dir: Optional[Path] = None,
        clip_bbox: Optional[List[float]] = None,
    ) -> Path:
        """Download Sentinel-2 Level-2A band from public AWS Registry of Open Data COG repository.

        Performs windowed spatial subsetting over HTTP range requests for the study area,
        providing authentic Sentinel-2 Level-2A raster observations without requiring user credentials.

        Args:
            scene_meta: Standardized scene metadata dict.
            band: Band name ("B03" or "B08").
            output_dir: Target output directory.
            clip_bbox: [min_lon, min_lat, max_lon, max_lat] in EPSG:4326.

        Returns:
            Path to downloaded and verified GeoTIFF raster.
        """
        target_dir = output_dir or RAW_DATA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        bbox = clip_bbox or GOMTI_BBOX
        band_key = band.upper()
        date_str = scene_meta.get("datetime", "")[:10]  # YYYY-MM-DD
        tile_id = scene_meta.get("tile_id") or "T44RMQ"
        if tile_id.startswith("T"):
            tile_clean = tile_id[1:]
        else:
            tile_clean = tile_id

        file_name = f"{scene_meta['id']}_{band_key}_10m.tif"
        dest_path = target_dir / file_name

        if dest_path.exists() and verify_raster_file(dest_path):
            logger.info("Public Sentinel-2 raster already exists and verified on disk: %s", dest_path.name)
            return dest_path

        logger.info(
            "Querying AWS Open Data Sentinel-2 COG archive for date=%s, tile=%s, band=%s",
            date_str,
            tile_clean,
            band_key,
        )

        cog_url = None
        # Query Earth Search STAC API for the exact scene assets
        try:
            stac_url = "https://earth-search.aws.element84.com/v1/search"
            payload = {
                "collections": ["sentinel-2-l2a"],
                "bbox": bbox,
                "datetime": f"{date_str}T00:00:00Z/{date_str}T23:59:59Z",
                "limit": 5,
            }
            resp = self.session.post(stac_url, json=payload, timeout=15)
            if resp.status_code == 200:
                features = resp.json().get("features", [])
                matching = [f for f in features if tile_clean in f.get("id", "")]
                if matching:
                    feat = matching[0]
                    asset_name = "green" if band_key == "B03" else "nir"
                    if asset_name in feat.get("assets", {}):
                        cog_url = feat["assets"][asset_name]["href"]
                        logger.info("Resolved public COG URL from Earth Search STAC: %s", cog_url)
        except Exception as exc:
            logger.warning("Earth Search STAC lookup failed: %s. Falling back to S3 direct path...", exc)

        if not cog_url:
            year = date_str[:4]
            month = str(int(date_str[5:7]))
            part_utm = tile_clean[:2]
            part_lat = tile_clean[2]
            part_sq = tile_clean[3:]
            s2_id_guess = f"S2A_{tile_clean}_{date_str.replace('-', '')}_0_L2A"
            cog_url = (
                f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/"
                f"{part_utm}/{part_lat}/{part_sq}/{year}/{month}/{s2_id_guess}/{band_key}.tif"
            )
            logger.info("Trying direct AWS Open Data COG path: %s", cog_url)

        try:
            logger.info("Opening remote Sentinel-2 COG via HTTP range requests...")
            with rasterio.open(cog_url) as src:
                utm_bounds = transform_bounds(CRS.from_epsg(4326), src.crs, *bbox)
                geom = [mapping(box(*utm_bounds))]
                data, transform = mask(src, geom, crop=True)

                profile = src.profile.copy()
                profile.update({
                    "driver": "GTiff",
                    "height": data.shape[1],
                    "width": data.shape[2],
                    "transform": transform,
                    "count": 1,
                    "compress": "deflate",
                })

                temp_path = dest_path.with_suffix(".tmp")
                with rasterio.open(temp_path, "w", **profile) as dst:
                    dst.write(data)
                    dst.update_tags(
                        PROVIDER="AWS_OPEN_DATA_SENTINEL2_COGS",
                        COLLECTION="sentinel-2-l2a",
                        OBSERVATION_DATE=date_str,
                        BAND=band_key,
                        STUDY_AREA="Gomti_River_Lucknow",
                    )

                if not verify_raster_file(temp_path):
                    temp_path.unlink(missing_ok=True)
                    raise DownloadError(f"Clipped raster failed validation for {band_key}")

                temp_path.replace(dest_path)
                logger.info(
                    "Successfully retrieved and verified public Sentinel-2 %s raster (%d bytes) to %s",
                    band_key,
                    dest_path.stat().st_size,
                    dest_path.name,
                )
                return dest_path

        except Exception as exc:
            msg = f"Failed to retrieve public Sentinel-2 COG raster for {band_key}: {exc}"
            logger.error(msg)
            raise DownloadError(msg) from exc

    def generate_synthetic_sample(
        self,
        scene_id: str,
        date_str: str,
        band: str,
        is_earlier: bool = True,
        output_dir: Optional[Path] = None,
        clip_bbox: Optional[List[float]] = None,
    ) -> Path:
        """Generate a realistic, georeferenced synthetic sample Level-2A raster.

        Used strictly as a reliable fallback for offline classroom demonstrations, dry-runs,
        or when external satellite gateways are temporarily unreachable.

        IMPORTANT: Synthetic sample rasters are marked with prominent metadata tags and must
        never be presented as real satellite observations.
        """
        target_dir = output_dir or RAW_DATA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        bbox = clip_bbox or GOMTI_BBOX
        band_key = band.upper()
        file_name = f"{scene_id}_{band_key}_10m_SYNTHETIC.tif"
        dest_path = target_dir / file_name

        if dest_path.exists() and verify_raster_file(dest_path):
            return dest_path

        logger.info(
            "Generating synthetic sample Level-2A %s raster (Gomti River geometry, Lucknow)...",
            band_key,
        )

        utm_bounds = transform_bounds(CRS.from_epsg(4326), CRS.from_epsg(32644), *bbox)
        min_x, min_y, max_x, max_y = utm_bounds
        res = 10.0
        width = int(np.ceil((max_x - min_x) / res))
        height = int(np.ceil((max_y - min_y) / res))
        transform = from_origin(min_x, max_y, res, res)

        # Generate realistic Gomti River meandering path across Lucknow study bounds
        cols = np.arange(width)
        river_center = (
            (height * 0.42)
            + (height * 0.16) * np.sin(cols / (width * 0.22))
            + (cols / width) * (height * 0.18)
        )
        rows = np.arange(height)[:, None]
        dist_from_river = np.abs(rows - river_center)

        # Seasonal channel width variation:
        # Earlier (post-monsoon October): Wider channel (half-width ~10 pixels = 200m)
        # Later (winter / pre-monsoon): Narrower channel (half-width ~6 pixels = 120m)
        channel_half_width = 10.0 if is_earlier else 6.0
        water_mask = dist_from_river <= channel_half_width

        # Floodplain vegetation zone adjacent to river
        riparian_mask = (dist_from_river > channel_half_width) & (dist_from_river <= channel_half_width + 12.0)
        urban_mask = ~water_mask & ~riparian_mask

        # Seed reproducible noise based on date and band
        seed = abs(hash(f"{date_str}_{band_key}")) % (2**31)
        rng = np.random.RandomState(seed)

        data = np.zeros((height, width), dtype=np.uint16)

        if band_key == "B03":  # Green band
            data[water_mask] = rng.normal(2400, 80, size=np.count_nonzero(water_mask)).clip(1800, 3200)
            data[riparian_mask] = rng.normal(1050, 60, size=np.count_nonzero(riparian_mask)).clip(700, 1600)
            data[urban_mask] = rng.normal(1400, 90, size=np.count_nonzero(urban_mask)).clip(900, 2200)

        elif band_key == "B08":  # NIR band
            data[water_mask] = rng.normal(450, 40, size=np.count_nonzero(water_mask)).clip(200, 800)
            data[riparian_mask] = rng.normal(4200, 120, size=np.count_nonzero(riparian_mask)).clip(3200, 5500)
            data[urban_mask] = rng.normal(1650, 100, size=np.count_nonzero(urban_mask)).clip(1100, 2600)
        else:
            data[:] = 1000

        profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 1,
            "dtype": rasterio.uint16,
            "crs": CRS.from_epsg(32644),
            "transform": transform,
            "nodata": 0,
            "compress": "deflate",
        }

        with rasterio.open(dest_path, "w", **profile) as dst:
            dst.write(data, 1)
            dst.update_tags(
                PROVENANCE="SYNTHETIC_BENCHMARK_SAMPLE",
                DISCLAIMER="Synthetic sample data generated for offline demonstration. NOT real satellite observations.",
                OBSERVATION_DATE=date_str,
                BAND=band_key,
                STUDY_AREA="Gomti_River_Lucknow",
            )

        logger.info(
            "Saved synthetic sample raster (%d bytes) to %s (PROVENANCE=SYNTHETIC_BENCHMARK_SAMPLE)",
            dest_path.stat().st_size,
            dest_path.name,
        )
        return dest_path

    def retrieve_band(
        self,
        scene_meta: Dict[str, Any],
        band: str,
        mode: str = "auto",
        output_dir: Optional[Path] = None,
        clip_bbox: Optional[List[float]] = None,
        is_earlier: bool = True,
    ) -> Tuple[Path, str]:
        """Unified band retrieval managing CDSE authentication, public COG, and synthetic fallback.

        Args:
            scene_meta: Standardized scene metadata dictionary.
            band: Band identifier ("B03" or "B08").
            mode: "auto", "cdse", "public", or "synthetic".
            output_dir: Directory to save downloaded/generated raster.
            clip_bbox: Bounding box [min_lon, min_lat, max_lon, max_lat].
            is_earlier: True for earlier observation, False for later.

        Returns:
            Tuple of (raster_file_path, provider_label):
            - "COPERNICUS_CDSE_AUTHENTICATED"
            - "PUBLIC_OPEN_SENTINEL2_COGS"
            - "SYNTHETIC_BENCHMARK_SAMPLE"
        """
        target_dir = output_dir or RAW_DATA_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        date_str = scene_meta.get("datetime", "")[:10]

        if mode == "cdse":
            p = self.download_band(scene_meta, band, output_dir=target_dir)
            return p, "COPERNICUS_CDSE_AUTHENTICATED"

        if mode == "public":
            p = self.download_band_public_cog(scene_meta, band, output_dir=target_dir, clip_bbox=clip_bbox)
            return p, "PUBLIC_OPEN_SENTINEL2_COGS"

        if mode == "synthetic":
            p = self.generate_synthetic_sample(
                scene_meta["id"], date_str, band, is_earlier=is_earlier, output_dir=target_dir, clip_bbox=clip_bbox
            )
            return p, "SYNTHETIC_BENCHMARK_SAMPLE"

        # Mode == "auto"
        # 1. Try CDSE if user configured credentials
        if self.has_credentials():
            try:
                p = self.download_band(scene_meta, band, output_dir=target_dir)
                return p, "COPERNICUS_CDSE_AUTHENTICATED"
            except (AuthenticationRequiredError, DownloadError) as exc:
                logger.warning("CDSE download route failed: %s. Attempting public Sentinel-2 COG fallback...", exc)

        # 2. Try Public Open Sentinel-2 COG route (real ESA Sentinel-2 L2A data via AWS Registry of Open Data)
        try:
            p = self.download_band_public_cog(scene_meta, band, output_dir=target_dir, clip_bbox=clip_bbox)
            return p, "PUBLIC_OPEN_SENTINEL2_COGS"
        except Exception as exc:
            logger.warning(
                "Public Sentinel-2 COG access failed: %s. Generating synthetic benchmark sample fallback...",
                exc,
            )

        # 3. Fallback to synthetic benchmark sample (offline / presentation demo safety net)
        p = self.generate_synthetic_sample(
            scene_meta["id"], date_str, band, is_earlier=is_earlier, output_dir=target_dir, clip_bbox=clip_bbox
        )
        return p, "SYNTHETIC_BENCHMARK_SAMPLE"
