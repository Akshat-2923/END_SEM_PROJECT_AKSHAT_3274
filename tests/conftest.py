"""Pytest configuration and PROJ environment normalization."""

import os
import sys
from pathlib import Path

# Ensure rasterio/GDAL uses its bundled PROJ database to avoid conflicts with system installations (e.g. PostGIS)
rasterio_proj = Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data"
if rasterio_proj.exists():
    os.environ["PROJ_DATA"] = str(rasterio_proj)
    os.environ["PROJ_LIB"] = str(rasterio_proj)
