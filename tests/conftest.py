"""Pytest configuration and PROJ environment normalization."""

import os
import sys
from pathlib import Path

# Ensure rasterio/GDAL uses its bundled PROJ database to avoid conflicts with system installations (e.g. PostGIS)
rasterio_proj = Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data"
if rasterio_proj.exists():
    os.environ["PROJ_DATA"] = str(rasterio_proj)
    os.environ["PROJ_LIB"] = str(rasterio_proj)

# Test environment configuration defaults
os.environ.setdefault("SUPABASE_JWT_SECRET", "super_secret_test_key_for_dharascope_verification_32_bytes")
os.environ.setdefault("SUPABASE_ISSUER", "https://testproject.supabase.co/auth/v1")
os.environ.setdefault("SUPABASE_URL", "https://testproject.supabase.co")
os.environ.setdefault("SUPABASE_AUDIENCE", "authenticated")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test_supabase_service_role_key_for_dharascope_verification_32_bytes")

