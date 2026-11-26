# DharaScope — Cloud Deployment & Infrastructure Audit

- **Document Version:** 1.0.0
- **Audit Date:** 2026-11-26
**Target Stack:**
- **Frontend:** React 19 + Vite (Render Static Site)
- **Backend:** Python 3.11 + FastAPI + Uvicorn (Render Docker Web Service)
- **Database:** Supabase Managed PostgreSQL 16 + PostGIS
- **ORM & Migrations:** SQLAlchemy 2.x + GeoAlchemy2 + Alembic
- **Driver:** Psycopg (`psycopg2-binary`)
- **Object Storage:** Supabase Storage (`rasters`, `maps`, `reports` buckets)

---

## 1. Existing Architecture Overview

DharaScope is structured as a decoupled full-stack geospatial web application alongside standalone scientific pipeline entrypoints:

1. **Frontend (`frontend/`):**
   - **Entrypoint:** `frontend/index.html` $\to$ `frontend/src/main.tsx` $\to$ `frontend/src/App.tsx`.
   - **Build System:** Vite 8 + TypeScript 7 (`npm run build` executes `tsc -b && vite build`, emitting static assets to `frontend/dist/`).
   - **Mapping & Auth:** Interactive Leaflet map (`MapPicker.tsx`), Supabase JS client (`@supabase/supabase-js` v2.119.0 in `frontend/src/services/supabase.ts`), and custom `apiFetch` / `downloadFile` REST wrapper (`frontend/src/services/api.ts`).
   - **Dev Server:** Port `5173` with Vite dev proxy `/api -> http://localhost:8000` (`frontend/vite.config.ts`).

2. **Backend (`server.py` & `src/`):**
   - **Entrypoint:** `server.py` imports `src.config` first (configuring PROJ data paths before GDAL/Rasterio initialization) and instantiates `app = create_app()` from `src/api/app.py`.
   - **API Routers:**
     - `src/api/routers/health.py`: `/`, `/health`, `/api/v1/health`, `/health/db`, `/api/v1/health/db`.
     - `src/api/routers/auth.py`: `/api/v1/auth/me`, `/api/v1/admin/users`, `/api/v1/admin/users/{user_id}`, `/api/v1/admin/users/{user_id}/reconcile`.
     - `src/api/routers/aois.py`: `/api/v1/aois/validate`, `/api/v1/aois`, `/api/v1/aois/{aoi_id}`.
     - `src/api/routers/analyses.py`: `/api/v1/analyses`, `/api/v1/analyses/{id}`, `/metrics`, `/artifacts`, `/reports/csv`, `/reports/pdf`.
     - `src/api/routers/artifacts.py`: `/api/v1/artifacts/{artifact_id}/download`.
   - **Satellite Processing Core (Must Be Preserved Intact):**
     - `src/stac_client.py`: Copernicus Data Space Ecosystem (CDSE) STAC discovery client.
     - `src/scene_selection.py`: Polygon intersection and cloud cover pair selector.
     - `src/downloader.py`: Multi-tier raster retrieval (CDSE OData, AWS Open Data Sentinel-2 COG `/vsicurl/` sub-granule streaming, synthetic fallback).
     - `src/water_indices.py`: McFeeters (1996) NDWI `(B03 - B08) / (B03 + B08)` and binary water masking.
     - `src/change_detection.py`: Common-valid domain intersection and 4-class transition matrix.
     - `src/visualization.py`: 300 DPI Matplotlib cartographic panels and transition maps.
     - `src/reporting.py`: Immutable manifest CSV export and ReportLab PDF compiler.

3. **Database & Persistence (`src/database/` & `alembic/`):**
   - **ORM Layer:** SQLAlchemy 2.1.8 + GeoAlchemy2 0.21.0 + `psycopg2-binary` 2.9.13.
   - **Models:** `Profile`, `AOI` (`GEOMETRY(POLYGON, 4326)` + GiST spatial index), `AnalysisRun`, `WaterMetrics`, `AnalysisArtifact`.
   - **Migrations (`alembic/`):**
     - `53ebad6d6a09_initial_schema.py`: Enables `postgis` extension and creates the 5 tables, constraints, and GiST spatial index.
     - `5903f15a19ed_enable_rls_and_policies.py`: Enables & forces PostgreSQL Row-Level Security (RLS) across all 5 tables with non-superuser role `dharascope_app` and transaction-local claim context (`SET LOCAL ROLE dharascope_app` + `set_config('request.jwt.claim.sub', ...)`).
   - **Session & Pooling:** Cached engines in `src/database/session.py` (`QueuePool`, `pool_pre_ping=True`, configurable SSL `connect_args`).

4. **Authentication & Storage (`src/auth.py`, `src/storage.py`):**
   - **JWT Validation:** Supports both symmetric `HS256` (`SUPABASE_JWT_SECRET`) and asymmetric `RS256`/`ES256` via Supabase JWKS (`SUPABASE_URL/auth/v1/.well-known/jwks.json`). Extracts `app_metadata.role` (never `user_metadata`), fails closed in `production`, and syncs roles via GoTrue Admin API (`src/services/role_sync_service.py`).
   - **Object Storage:** Abstracted behind `BaseStorageBackend` with `LocalStorageBackend` (`outputs/`) and `SupabaseStorageBackend` (REST upload/download/signed URL to private buckets `rasters`, `maps`, `reports` cached under `outputs/cache/supabase`).

---

## 2. Current Implementation Status

| Component | Current Status | Readiness for Supabase + Render |
| :--- | :--- | :--- |
| FastAPI Service Layer & Processing Pipeline | Complete & tested (202 pytest tests pass locally) | Functional, needs env-based CORS & startup config check |
| SQLAlchemy Models & Alembic Initial Schema | Complete (`53ebad6d6a09`) | Compatible with Supabase PostGIS (`extensions` schema awareness needed if non-public) |
| Alembic RLS Migration (`5903f15a19ed`) | Complete for local/Azure Postgres | **Incompatible with Supabase managed Postgres** (`auth` ownership conflict) |
| Database Config & Pooling (`src/database/`) | Supports `DB_SSL_MODE`, `make_url`, diagnostics | Needs `postgres://` URL normalization and Supabase session-pooler tuning |
| Docker Backend Configuration | **Missing** | No `Dockerfile` or `.dockerignore` exists |
| Frontend Build & API Client (`frontend/`) | Builds cleanly (`vite build`, 18 tests) | Needs hardcoded localhost removal in `PROD`, URL normalization, and SPA fallback |
| Supabase Storage Integration (`src/storage.py`) | Implemented (`SupabaseStorageBackend`) | Ready; needs bucket policy documentation/automation & path hygiene checks |
| Environment Config (`.env.example`) | Azure-focused | Missing `FRONTEND_URL`, `CORS_ORIGINS`, `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_ENABLED`, `ENVIRONMENT` |
| Render Infrastructure Configuration | **Missing** | No `render.yaml` Blueprint |
| Live Docker Engine on Local Windows Host | Installed CLI (`Docker 28.5.2`), daemon stopped | Requires Docker Desktop startup to verify local container builds |

---

## 3. Missing Deployment Requirements

1. **Containerization Assets (`Dockerfile`, `.dockerignore`):**
   - Missing Linux `python:3.11-slim` Docker definition installing geospatial system runtime dependencies (`libexpat1`, `libpq5`, CA certificates, curl) and non-root runtime user execution bound to `0.0.0.0:$PORT`.
2. **Dynamic Production CORS (`src/api/app.py`):**
   - `CORSMiddleware` hardcodes only localhost origins (`localhost:5173`, `127.0.0.1:5173`, etc.). Missing environment-driven `FRONTEND_URL` and `CORS_ORIGINS` parsing.
3. **Production Startup Configuration Validation:**
   - Mandatory production environment checks (`DATABASE_URL`, `SUPABASE_URL`, auth keys, `FRONTEND_URL`) only happen lazily at first request inside `src/auth.py` rather than failing fast or warning clearly during application startup.
4. **Render Deployment Blueprint (`render.yaml`) & SPA Routing:**
   - Missing `render.yaml` defining the `dharascope-backend` Docker Web Service (with `/health` health check) and `dharascope-frontend` Static Site (with `/* -> /index.html` SPA rewrite).
5. **Comprehensive Cloud Deployment Guide (`docs/DEPLOYMENT_GUIDE.md`):**
   - Existing `docs/AZURE_POSTGRESQL.md` covers Azure, whereas a step-by-step Supabase + Render deployment guide is missing.

---

## 4. Potential Compatibility & Security Issues Discovered

### Critical Issues (Must Fix Before Cloud Deployment)

1. **Alembic RLS Migration Fails on Supabase Managed PostgreSQL (`alembic/versions/5903f15a19ed_enable_rls_and_policies.py`):**
   - Migration `5903f15a19ed` executes `CREATE SCHEMA IF NOT EXISTS auth;` and `CREATE OR REPLACE FUNCTION auth.uid() ...` and `CREATE OR REPLACE FUNCTION auth.role() ...`.
   - On Supabase-managed PostgreSQL, the `auth` schema and `auth.uid()` / `auth.role()` functions already exist and are owned by `supabase_auth_admin`. Executing `CREATE OR REPLACE FUNCTION auth.uid()` as `postgres` raises **`ERROR: must be owner of function uid`**.
   - Additionally, on PostgreSQL 16 without superuser privileges (as in Supabase), executing `SET LOCAL ROLE dharascope_app` requires the connecting role (`postgres` / `CURRENT_USER`) to be granted membership in `dharascope_app` (`GRANT dharascope_app TO CURRENT_USER`).
   - Similarly, `downgrade()` runs `DROP FUNCTION IF EXISTS auth.uid()`, which would fail on Supabase.

2. **Hardcoded Localhost CORS in FastAPI (`src/api/app.py`):**
   - Production requests from Render Static Site (`https://<site>.onrender.com`) will be rejected by browsers with CORS preflight errors because `allow_origins` contains only `localhost` and `127.0.0.1`.

3. **Frontend Production Fallback to Localhost (`frontend/src/services/api.ts`):**
   - `const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'` falls back to `localhost` even when `import.meta.env.PROD` is true. In addition, if `VITE_API_BASE_URL` is configured as `https://api.example.com` (without `/api/v1` suffix, e.g. from Render service host), endpoints would 404 unless normalized.

### Moderate Issues & Edge Cases

4. **Windows-Only `PROJ_DATA` Path Detection (`src/config.py`):**
   - `src/config.py` lines 9–12 construct `Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data"`. On Debian/Linux Docker containers, `Lib` is lowercase `lib/python3.X`, causing `_proj_dir.exists()` to evaluate `False`. Cross-platform lookup via `sysconfig.get_paths()["purelib"]` ensures consistent `PROJ_DATA` resolution on both Windows and Linux containers.

5. **`DATABASE_URL` Scheme Normalization (`postgres://` vs `postgresql+psycopg2://`):**
   - Dashboard copy-paste or PaaS providers frequently provide `postgres://...` URLs. SQLAlchemy 2.x rejects the `postgres://` dialect prefix (`NoSuchModuleError`). Normalizing `postgres://` $\to$ `postgresql+psycopg2://` and `postgresql://` $\to$ `postgresql+psycopg2://` ensures reliable psycopg2 driver selection.

6. **Supabase Connection Mode Compatibility (Direct vs Session Pooler vs Transaction Pooler):**
   - Direct connections (`db.<ref>.supabase.co:5432`) in Supabase may resolve to IPv6 only unless IPv4 add-on is purchased, whereas Render services typically use IPv4 egress. Therefore, DharaScope should default deployment guidance to the **Supabase Session Pooler** (`aws-0-<region>.pooler.supabase.com:5432`), which supports IPv4, SSL (`sslmode=require`), Alembic migrations, `SET LOCAL ROLE`, and SQLAlchemy `QueuePool` safely.

7. **Hardcoded `reload=True` in `server.py` `__main__`:**
   - Running `python server.py` directly always enables Uvicorn hot-reloading (`reload=True`), which is inappropriate for production containers.

8. **Ephemeral Filesystem vs Object Storage Lifecycle (`src/services/analysis_service.py` & `src/storage.py`):**
   - Render Web Services use an ephemeral disk. Local files saved in `outputs/` disappear on redeploy/restart.
   - Because `src/services/artifact_service.py` delegates to `get_storage_backend()`, setting `SUPABASE_STORAGE_ENABLED=true` ensures artifacts (reports, maps, rasters) persist across restarts in private Supabase buckets (`reports`, `maps`, `rasters`) and are downloaded on-demand to `cache/supabase/`.
   - However, when `delete_analysis_run()` deletes a run, remote Supabase Storage objects are not currently cleaned up, and private storage bucket creation/policies should be verified and documented.

9. **Asymmetric Supabase JWT Verification (`RS256`/`ES256`) vs Startup Guard (`src/auth.py`):**
   - Modern Supabase projects may issue `ES256` or `RS256` tokens verified via JWKS (`SUPABASE_URL/auth/v1/.well-known/jwks.json`) instead of `HS256` (`SUPABASE_JWT_SECRET`), though existing production tests in `tests/test_auth_jwt.py` require fail-closed checks when `SUPABASE_JWT_SECRET` is omitted unless configured explicitly. Care must be taken not to break those security regression tests.

10. **`.env.example` Default `DB_SSL_MODE=require` Conflict on Local PostgreSQL:**
    - Root `.env.example` currently sets `DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/dharascope` paired with `DB_SSL_MODE=require`. Local PostgreSQL installations on developer workstations typically run with SSL disabled (`ssl_active=false`, as observed on localhost PostgreSQL 16.15). Copying `.env.example` verbatim would break local startup unless `DB_SSL_MODE` is documented cleanly for local vs cloud.

---

## 5. Recommended Incremental Changes (Roadmap)

1. **Phase 2 — Supabase PostgreSQL Integration:**
   - Update `src/database/config.py` and `src/database/session.py` to normalize `postgres://` / `postgresql://` URLs cleanly, configure graceful SSL defaults for remote Supabase hosts (preserving local non-SSL dev), configure pooling limits appropriate for Supabase Session Pooler, and preserve clean session teardown.
   - Update `alembic/versions/5903f15a19ed_enable_rls_and_policies.py` (safely guarding existing `auth` functions on Supabase without breaking clean local Postgres or Azure migrations) and review `53ebad6d6a09_initial_schema.py` PostGIS setup.
2. **Phase 3 — Environment Configuration & CORS:**
   - Update `.env.example` with clean placeholders (`DATABASE_URL=`, `SUPABASE_URL=`, `SUPABASE_ANON_KEY=`, `SUPABASE_SERVICE_ROLE_KEY=`, `FRONTEND_URL=`, etc.).
   - Add startup configuration validation module (`validate_startup_config()`) invoked safely during production initialization without breaking offline unit tests.
   - Update `src/api/app.py` to read `FRONTEND_URL` and `CORS_ORIGINS` dynamically.
   - Update `server.py` so `reload` is only enabled in development.
3. **Phase 4 — Docker Backend:**
   - Fix cross-platform `PROJ_DATA` resolution in `src/config.py`.
   - Create lightweight production `Dockerfile` (`python:3.11-slim`, non-root user `appuser`, `$PORT` binding on `0.0.0.0`, no `--reload`, Docker healthcheck) and `.dockerignore`.
4. **Phase 5 — Frontend Deployment (Render Static Site):**
   - Update `frontend/src/services/api.ts` to enforce `VITE_API_BASE_URL` in production, normalize trailing slashes / `/api/v1` suffix consistently, and remove hardcoded `localhost` in production builds.
   - Add SPA fallback rewrite rule (`frontend/public/_redirects` + `render.yaml` route).
   - Verify `npm run build` produces clean production bundles with zero backend secrets.
5. **Phase 6 — Artifact Storage Hardening:**
   - Verify `SupabaseStorageBackend` path safety, upload failure isolation, private bucket expectations, and delete cleanup (best-effort storage deletion on run delete), and document Supabase `storage.objects` private RLS policies.
6. **Phase 7 — Render Blueprint (`render.yaml`):**
   - Author accurate `render.yaml` specifying `dharascope-backend` (Docker Web Service, `/health`) and `dharascope-frontend` (Static Site, `dist`, `VITE_API_BASE_URL`) without embedding any secrets.
7. **Phase 8 & Documentation:**
   - Run full backend/frontend test suites, Alembic migration checks, Docker build/startup/health/CORS verification (contingent on starting local Docker Desktop daemon), author `docs/DEPLOYMENT_GUIDE.md`, and synchronize `PROJECT_STATUS.md` and `docs/PROJECT_STATUS.md`.
