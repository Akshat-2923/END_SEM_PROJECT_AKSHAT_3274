"""Configuration module for DharaScope."""

import logging
import os
import sys
import sysconfig
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

from dotenv import load_dotenv

logger = logging.getLogger("dhara_scope.config")


def _configure_rasterio_proj() -> None:
    """Ensure rasterio uses its bundled PROJ database across Windows and Linux containers."""
    candidates = [
        Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data",
    ]
    purelib = sysconfig.get_paths().get("purelib")
    platlib = sysconfig.get_paths().get("platlib")
    for lib_dir in (platlib, purelib):
        if lib_dir:
            candidates.append(Path(lib_dir) / "rasterio" / "proj_data")

    for proj_dir in candidates:
        if proj_dir.exists():
            os.environ["PROJ_DATA"] = str(proj_dir)
            os.environ["PROJ_LIB"] = str(proj_dir)
            break


_configure_rasterio_proj()

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment variables from .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
OUTPUTS_DIR = BASE_DIR / "outputs"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
METADATA_DIR = OUTPUTS_DIR / "metadata"
REPORTS_DIR = OUTPUTS_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

for directory in [DATA_DIR, RAW_DATA_DIR, OUTPUTS_DIR, ARTIFACTS_DIR, METADATA_DIR, REPORTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Study Area: Gomti River, Lucknow, Uttar Pradesh, India
# Format: [min_lon, min_lat, max_lon, max_lat] (WGS84 EPSG:4326)
DEFAULT_BBOX = [80.88, 26.80, 81.00, 26.90]

bbox_str = os.getenv("DHARASCOPE_BBOX")
if bbox_str:
    try:
        GOMTI_BBOX = [float(coord.strip()) for coord in bbox_str.split(",")]
        if len(GOMTI_BBOX) != 4:
            GOMTI_BBOX = DEFAULT_BBOX
    except ValueError:
        GOMTI_BBOX = DEFAULT_BBOX
else:
    GOMTI_BBOX = DEFAULT_BBOX

# Sentinel-2 STAC & Copernicus Data Space Ecosystem (CDSE) Endpoints
CDSE_STAC_BASE_URL = "https://stac.dataspace.copernicus.eu/v1"
CDSE_COLLECTION = "sentinel-2-l2a"
CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_CLIENT_ID = "cdse-public"
CDSE_DOWNLOAD_BASE_URL = "https://download.dataspace.copernicus.eu/odata/v1"

# Credentials
CDSE_USERNAME = os.getenv("CDSE_USERNAME", "").strip()
CDSE_PASSWORD = os.getenv("CDSE_PASSWORD", "").strip()
CDSE_ACCESS_TOKEN = os.getenv("CDSE_ACCESS_TOKEN", "").strip()

# Optional: CDSE OAuth Client credentials for Sentinel Hub Process API (Spatial Subsetting)
CDSE_OAUTH_CLIENT_ID = os.getenv("CDSE_OAUTH_CLIENT_ID", os.getenv("SH_CLIENT_ID", "")).strip()
CDSE_OAUTH_CLIENT_SECRET = os.getenv("CDSE_OAUTH_CLIENT_SECRET", os.getenv("SH_CLIENT_SECRET", "")).strip()
CDSE_PROCESS_API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Analysis Parameters
# NDWI = (Green - NIR) / (Green + NIR)
# Normalized Difference Water Index threshold (Default 0.0)
DEFAULT_NDWI_THRESHOLD = 0.0
threshold_str = os.getenv("DHARASCOPE_NDWI_THRESHOLD")
if threshold_str:
    try:
        NDWI_WATER_THRESHOLD = float(threshold_str)
    except ValueError:
        NDWI_WATER_THRESHOLD = DEFAULT_NDWI_THRESHOLD
else:
    NDWI_WATER_THRESHOLD = DEFAULT_NDWI_THRESHOLD

# Geographical AOI Validation Parameters
MIN_AOI_AREA_KM2 = float(os.getenv("DHARASCOPE_MIN_AOI_KM2", "0.10"))
MAX_AOI_AREA_KM2 = float(os.getenv("DHARASCOPE_MAX_AOI_KM2", "100.00"))
MAX_AOI_VERTICES = int(os.getenv("DHARASCOPE_MAX_AOI_VERTICES", "500"))

# Supabase Auth Admin & Cloud Storage Configuration
# Service Role Key is strictly backend-only; never expose to clients or API responses
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_STORAGE_ENABLED = os.getenv("SUPABASE_STORAGE_ENABLED", "false").lower() in ("true", "1", "yes")

STORAGE_BUCKET_RASTERS = "rasters"
STORAGE_BUCKET_MAPS = "maps"
STORAGE_BUCKET_REPORTS = "reports"

_LOCAL_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

_PLACEHOLDER_MARKERS = (
    "your-project-ref",
    "your_supabase_",
    "your_copernicus_",
    "your_oauth_",
    "placeholder",
)


def get_app_environment() -> str:
    """Return normalized application runtime environment name."""
    raw = os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "development"
    return raw.strip().lower() or "development"


def is_production_env() -> bool:
    """Return True when running in production environment."""
    return get_app_environment() in ("production", "prod")


def _normalize_origin(raw_origin: str) -> Optional[str]:
    """Normalize an HTTP origin URL (scheme://host[:port]) without trailing slash."""
    cleaned = raw_origin.strip()
    if not cleaned or cleaned == "*":
        return None
    parts = urlsplit(cleaned)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}".lower()
    host = cleaned.rstrip("/")
    scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{scheme}://{host}".lower()


def get_cors_origins() -> List[str]:
    """Compute allowed CORS origins from FRONTEND_URL, CORS_ORIGINS, and environment mode."""
    origins: List[str] = []

    def _add(origin: Optional[str]) -> None:
        if origin and origin not in origins:
            origins.append(origin)

    if not is_production_env():
        for dev_origin in _LOCAL_DEV_CORS_ORIGINS:
            _add(dev_origin)

    frontend_url = os.getenv("FRONTEND_URL", "")
    if frontend_url:
        _add(_normalize_origin(frontend_url))

    extra_origins = os.getenv("CORS_ORIGINS", "")
    if extra_origins:
        for item in extra_origins.split(","):
            _add(_normalize_origin(item))

    return origins


def _is_missing_or_placeholder(val: Optional[str]) -> bool:
    """Check if an environment variable value is empty or an unmodified template placeholder."""
    if not val or not val.strip():
        return True
    lowered = val.strip().lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def validate_startup_config(strict: Optional[bool] = None) -> Dict[str, str]:
    """Validate mandatory configuration on application startup.

    In production (`strict=True` or `ENVIRONMENT=production`), raises RuntimeError
    if mandatory database, Supabase auth, or CORS frontend origin settings are missing.
    In development/testing, logs clear guidance and allows offline work.
    """
    is_prod = strict if strict is not None else is_production_env()
    env_name = get_app_environment()

    database_url = os.getenv("DATABASE_URL", "").strip()
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    jwt_secret = (os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET") or "").strip()
    jwks_url = os.getenv("SUPABASE_JWKS_URL", "").strip()
    cors_origins = get_cors_origins()

    missing: List[str] = []
    if is_prod:
        if _is_missing_or_placeholder(database_url):
            missing.append("DATABASE_URL")
        if _is_missing_or_placeholder(supabase_url):
            missing.append("SUPABASE_URL")
        if _is_missing_or_placeholder(service_role_key):
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if _is_missing_or_placeholder(jwt_secret) and _is_missing_or_placeholder(jwks_url):
            missing.append("SUPABASE_JWT_SECRET (or SUPABASE_JWKS_URL)")
        if not cors_origins:
            missing.append("FRONTEND_URL (or CORS_ORIGINS)")

        if missing:
            raise RuntimeError(
                "Invalid production startup configuration; missing or placeholder environment variables: "
                + ", ".join(missing)
            )
    else:
        if not database_url:
            logger.info("DATABASE_URL not set; defaulting to local PostgreSQL development database.")
        if not cors_origins:
            logger.warning("No CORS origins configured.")

    storage_mode = (
        "supabase"
        if (
            os.getenv("SUPABASE_STORAGE_ENABLED", "false").lower() in ("true", "1", "yes")
            and not _is_missing_or_placeholder(supabase_url)
            and not _is_missing_or_placeholder(service_role_key)
        )
        else "local"
    )

    return {
        "environment": env_name,
        "storage_backend": storage_mode,
        "cors_origins_count": str(len(cors_origins)),
    }
