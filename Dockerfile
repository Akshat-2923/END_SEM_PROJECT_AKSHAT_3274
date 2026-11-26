# DharaScope Backend — FastAPI + Geospatial Remote Sensing Container
# Target Platform: Render Docker Web Service / Managed Cloud Containers

FROM python:3.11-slim-bookworm

LABEL maintainer="DharaScope Team" \
      description="DharaScope FastAPI Backend with Geospatial Processing (Rasterio, Shapely, PyProj, PostGIS)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PORT=8000

WORKDIR /app

# Install minimal runtime OS libraries required by Rasterio/GDAL wheels, Psycopg2, Matplotlib, and HTTP healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libexpat1 \
    libgomp1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install backend Python dependencies from single-source requirements.txt
# Omit dashboard UI (streamlit) and test runner (pytest) to keep production image lightweight
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && grep -Ev '^(streamlit|pytest)\b' requirements.txt > /tmp/requirements-backend.txt \
    && pip install --no-cache-dir -r /tmp/requirements-backend.txt \
    && rm -f /tmp/requirements-backend.txt

# Copy backend application, Alembic migrations, and lightweight baseline artifacts
COPY server.py alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY artifacts/maps ./artifacts/maps
COPY artifacts/reports ./artifacts/reports
COPY artifacts/metadata ./artifacts/metadata

# Create non-root runtime user and grant write permissions for runtime scratch/cache/logs
RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && mkdir -p /app/data/raw /app/outputs/metadata /app/outputs/reports /app/outputs/cache/supabase /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Container healthcheck against FastAPI /health endpoint using injected PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

# Start Uvicorn ASGI server bound to 0.0.0.0 and Render's assigned PORT
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
