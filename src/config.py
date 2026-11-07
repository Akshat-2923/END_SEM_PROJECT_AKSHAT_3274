"""Configuration module for DharaScope Phase 1."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure rasterio uses its bundled PROJ database to prevent system conflicts (e.g. PostGIS on Windows)
_proj_dir = Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data"
if _proj_dir.exists():
    os.environ["PROJ_DATA"] = str(_proj_dir)
    os.environ["PROJ_LIB"] = str(_proj_dir)


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
METADATA_DIR = OUTPUTS_DIR / "metadata"
LOGS_DIR = BASE_DIR / "logs"

for directory in [DATA_DIR, RAW_DATA_DIR, OUTPUTS_DIR, METADATA_DIR, LOGS_DIR]:
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
