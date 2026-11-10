# Changelog
All notable changes to the DharaScope platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.3] - 2026-11-10
### Added
- **Distributed Role Consistency & Compensating Recovery (`src/services/role_sync_service.py`):**
  - Implemented `RoleSyncJournal` and `execute_reliable_role_update()` providing two-phase consistency across Supabase Auth GoTrue Admin API and PostgreSQL `profiles.role`.
  - Intent logging: records transitions (`PENDING`, `IDP_UPDATED`, `COMMITTED`, `COMPENSATING`, `COMPENSATED`, `FAILED`, `DESYNCHRONIZED`, `RECONCILED`) to durable JSONL journal (`outputs/metadata/role_sync_audit.jsonl`).
  - Compensating rollback: if PostgreSQL commit or flush fails after Supabase update, automatically dispatches compensating update to Supabase Auth restoring `old_role` (returning HTTP 500). If compensation also fails, records `DESYNCHRONIZED` and logs critical alert (HTTP 502).
  - Idempotent retries: unchanged roles return immediately without redundant external operations.
  - Reconciliation endpoint: added `POST /api/v1/admin/users/{user_id}/reconcile` and `reconcile_user_role()` for on-demand role reconciliation.
- **Decoupled Live Storage Integration Suite (`tests/test_storage.py`):**
  - Added `TestLiveSupabaseStorageIntegration` guarded by `@pytest.mark.skipif(os.getenv("DHARASCOPE_LIVE_SUPABASE_STORAGE") != "1")` to keep offline mock test suites strictly separated from live cloud infrastructure verification.

### Security
- **Immediate Admin Revocation (`src/auth.py`):**
  - Hardened `verify_admin_privileges()` and `require_admin()` to enforce authoritative database role checks on `profiles.role` using the caller's UUID in a restricted RLS-aware session.
  - Immediate revocation: revoked administrators presenting an unexpired JWT with `app_metadata.role = "admin"` are immediately blocked with `403 Forbidden` on their very next administrative request, eliminating token TTL window delays.
  - Fail-closed security: database connection or query errors during admin privilege verification fail closed with `500 Internal Server Error`, never permitting administrative bypass.
  - Ordinary authenticated user access (`/api/v1/auth/me`, `/api/v1/aois`, `/api/v1/analyses`) remains completely preserved.

---

## [0.7.2] - 2026-11-10
### Added
- **Supabase Auth Admin Synchronization (`src/auth.py`, `src/api/routers/auth.py`):**
  - Integrated `sync_user_role_to_supabase()` calling Supabase GoTrue Admin API (`PUT /auth/v1/admin/users/{user_id}`) to synchronize promoted or revoked user roles directly into authoritative `app_metadata.role`.
  - Atomic failure safety: if Supabase synchronization fails, the database transaction is aborted and PostgreSQL `profiles.role` remains unchanged.
  - Secure service-role key management: `SUPABASE_SERVICE_ROLE_KEY` is loaded strictly on the backend, guarded with production fail-closed checks, and never exposed in API serialization schemas or logs.
  - Documented stale JWT lifecycle and maximum revocation delay (token TTL = 3600 seconds).
  - Added 10 automated tests in `tests/test_admin_role_sync.py` covering promotion, revocation, network/server failure rollbacks, unauthorized rejections, and quota-only bypasses.
- **Storage Subsystem Abstraction (`src/storage.py`):**
  - Implemented `BaseStorageBackend` with `LocalStorageBackend` (default) and `SupabaseStorageBackend` (cloud deployments).
  - Integrated storage backend into pipeline worker (`src/services/analysis_service.py`), uploading generated comparison panels, water-change maps, single-date NDWI maps, reports (CSV, PDF), and band rasters to logical buckets (`maps`, `reports`, `rasters`).
  - Upload failure safety: artifacts failing upload are logged and excluded from `analysis_artifacts`, preventing misleading phantom records.
  - Updated `src/services/artifact_service.py` to resolve files through `storage.get_local_path()` and `storage.download_file()`, maintaining strict ownership verification and multi-tenant RLS isolation.
  - Added 16 automated tests in `tests/test_storage.py` testing local and Supabase storage lifecycle, mocked upload/download/signing endpoints, and pipeline upload failure handling. Full test suite expanded to 151 passing tests.

---

## [0.7.1] - 2026-11-10
### Fixed
- **RFC 9110 Deprecation Remediation:** Updated `src/api/app.py` exception handlers from deprecated `status.HTTP_422_UNPROCESSABLE_ENTITY` to `status.HTTP_422_UNPROCESSABLE_CONTENT`. Actionable test deprecation warnings eliminated.

### Changed
- **Architectural Documentation & Audit Notes:**
  - Documented FastAPI `BackgroundTasks` lifecycle: tasks run in-process and do not survive application restarts. Worker database sessions verified as independently managed via `get_authenticated_db()`.
  - Documented artifact storage: files reside on local filesystem storage (`outputs/<user_id>/<run_id>/`); remote cloud object storage upload scheduled for Phase 2.3. Ownership authorization for downloads verified.
  - Documented admin role synchronization: `PATCH /api/v1/admin/users/{user_id}` updates PostgreSQL `profiles.role` projection only. Role changes require Supabase Admin API synchronization to propagate into authoritative `app_metadata.role` tokens; documented stale JWT TTL behavior.
  - Categorized test warnings: 144 upstream `rasterio` Affine matrix warnings, 1 upstream Starlette `httpx` warning, 0 application warnings remaining.

---

## [0.7.0] - 2026-11-10
### Added
- **FastAPI Application Bootstrap & Configuration (`src/api/app.py`, `server.py`):**
  - Application factory with configurable CORS middleware, standardized error handlers, and interactive OpenAPI documentation (`/docs`, `/redoc`, `/openapi.json`).
  - Production ASGI entrypoint `server.py` loading `src.config` first to guarantee Windows PROJ runtime isolation before initializing geospatial libraries.
- **Pydantic Validation & Serialization Layer (`src/api/schemas/`):**
  - Standardized error response envelopes (`APIErrorResponse`, `ValidationErrorResponse`) preventing internal stack trace and filesystem path leakage.
  - Health check schemas (`HealthResponse`), User/Admin management schemas (`UserProfileResponse`, `AdminUserUpdate`), AOI validation and CRUD schemas (`AOIValidationRequest`, `AOICreateRequest`, `AOIResponse`), and Analysis/Artifact schemas (`AnalysisCreateRequest`, `AnalysisResponse`, `WaterMetricsResponse`, `ArtifactResponse`).
- **Application Service Layer (`src/services/`):**
  - `aoi_service.py`: Encapsulates geographical polygon validation (`src/aoi_validation.py`), PostGIS geometry creation (`EPSG:4326`), paginated listing, ownership updates, and deletion.
  - `analysis_service.py`: Manages user run quotas, AOI resolution, asynchronous background pipeline execution via FastAPI `BackgroundTasks`, status tracking, and error sanitization.
  - `artifact_service.py`: Enforces ownership and RLS checks on artifact downloads, generates ReportLab PDF and RFC 4180 CSV reports on demand, and prepares streaming file responses.
- **RESTful Endpoints & Routers (`src/api/routers/`):**
  - `health.py`: `GET /health`, `GET /api/v1/health`, `GET /`.
  - `auth.py`: `GET /api/v1/auth/me`, `PATCH /api/v1/auth/me`, `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{user_id}`.
  - `aois.py`: `POST /api/v1/aois/validate`, `POST /api/v1/aois`, `GET /api/v1/aois`, `GET /api/v1/aois/{id}`, `PATCH /api/v1/aois/{id}`, `DELETE /api/v1/aois/{id}`.
  - `analyses.py`: `POST /api/v1/analyses`, `GET /api/v1/analyses`, `GET /api/v1/analyses/{id}`, `DELETE /api/v1/analyses/{id}`, `GET /api/v1/analyses/{id}/metrics`, `GET /api/v1/analyses/{id}/artifacts`, `GET /api/v1/analyses/{id}/reports/csv`, `GET /api/v1/analyses/{id}/reports/pdf`.
  - `artifacts.py`: `GET /api/v1/artifacts/{id}/download`.
- **Automated Integration Test Suite (`tests/test_api_service_layer.py`):**
  - Added 33 comprehensive integration tests covering system health, authentication, admin controls, AOI lifecycle and validation, multi-tenant RLS isolation, background pipeline execution, report downloads, and error sanitization. Full repository test suite expanded from 92 to 125 passing tests.

---

## [0.6.1] - 2026-11-10
### Security
- **Hardened JWT Role Derivation:** Patched `AuthenticatedUser.from_claims()` in `src/auth.py` to extract user authorization roles strictly from server-controlled `app_metadata.role`.
- **Eliminated User Metadata Trust:** Completely removed `user_metadata` as a source of authorization claims, preventing client self-promotion to `admin` during signup or profile updates.
- **Supabase System Role Decoupling:** Explicitly separated Supabase's standard session claim `role: "authenticated"` from application authorization; non-explicit or missing roles default unconditionally to `user`.
- **Database Non-Superuser Role Hardening:** Updated migration `5903f15a19ed_enable_rls_and_policies.py` to explicitly declare `NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE` on `dharascope_app` to ensure PostgreSQL Row-Level Security cannot be bypassed.
- **Production Fail-Closed Enforcement:** Added fail-closed checks in `get_jwt_secret()` and `get_jwt_issuer()` to raise HTTP 500 in production when `SUPABASE_JWT_SECRET` or `SUPABASE_ISSUER` / `SUPABASE_URL` is omitted.

### Fixed
- Fixed security test `test_production_missing_jwt_secret_fails_closed` in `tests/test_auth_jwt.py` to isolate missing secret evaluation from missing issuer evaluation.

### Added
- Added 7 automated security tests in `tests/test_auth_jwt.py` verifying client `user_metadata.role = admin` rejection, missing role defaults, invalid role strings, Supabase system claim isolation, auto-provisioning role safety, and production fail-closed behaviors. Test suite total expanded to 92 passing tests.

---

## [0.6.0] - 2026-11-07
### Added
- Implemented Supabase Auth and FastAPI security layer in `src/auth.py`:
  - `AuthenticatedUser`: Data structure encapsulating verified user identity, canonical role extraction, and raw JWT claims.
  - `verify_supabase_jwt`: Cryptographic verification supporting HMAC (`HS256`) and asymmetric (`RS256`, `ES256`) via Supabase JWKS endpoints with key caching. Enforces expiration, signature, issuer, audience, and UUID subject claims.
  - `get_current_user`: Reusable FastAPI dependency extracting Bearer credentials from the `Authorization` header.
  - `require_admin`: Role guard dependency returning HTTP 403 Forbidden for non-admin accounts.
  - `apply_rls_context` & `get_authenticated_db`: Transaction-local session context manager setting `SET LOCAL ROLE dharascope_app;` and `set_config('request.jwt.claim.*', ..., true)` to propagate verified identities into PostgreSQL.
  - Profile identity management: `get_or_create_profile` with auto-provisioning and `update_user_profile` with strict anti-privilege escalation guards.
- Created Alembic migration `5903f15a19ed_enable_rls_and_policies.py`:
  - Created `auth` schema and compatibility functions `auth.uid()` and `auth.role()`.
  - Created non-superuser application role `dharascope_app` with default privileges.
  - Enabled and forced Row-Level Security on all 5 tables (`profiles`, `aois`, `analysis_runs`, `water_metrics`, `analysis_artifacts`).
  - Implemented 20 granular RLS policies enforcing user ownership isolation, public read access for shared AOIs, child record ownership inheritance, and database-level prevention of role self-promotion.
- Added 21 automated security tests:
  - `tests/test_auth_jwt.py` (15 tests): Valid/admin JWTs, missing token, invalid signature, expired token, forged issuer, invalid audience, non-UUID subject, 403 admin enforcement, auto-provisioning, and role escalation rejections.
  - `tests/test_database_security_rls.py` (6 tests): Live PostgreSQL RLS tests verifying private AOI cross-user isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection.
- Added dependencies to `requirements.txt`:
  - `fastapi>=0.110.0`
  - `uvicorn>=0.28.0`
  - `pyjwt[crypto]>=2.8.0`
  - `httpx>=0.27.0`

### Changed
- Updated `alembic/env.py` to route database connections dynamically to programmatic URLs passed via `set_main_option("sqlalchemy.url", ...)`.
- Updated `.env.example` with Supabase Auth configuration variables (`SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`, `SUPABASE_AUDIENCE`).


---

## [0.5.0] - 2026-11-07
### Added
- Implemented PostgreSQL 16 + PostGIS 3.6 database subsystem in `src/database/`:
  - `src/database/base.py`: DeclarativeBase metadata registry.
  - `src/database/config.py`: Environment-driven connection configuration supporting isolated testing.
  - `src/database/session.py`: Engine pooling, sessionmaker factory, and transactional `get_db()` context manager.
- Implemented 5 relational models in `src/database/models/`:
  - `Profile` (`profiles`): UUID primary key mapped to Supabase Auth, check constraints for valid roles (`user`, `admin`) and positive quotas.
  - `AOI` (`aois`): WGS84 PostGIS polygon geometry (`GEOMETRY(POLYGON, 4326)`) with spatial GiST indexing (`idx_aois_geometry`), area limits ($0.10–100.00\text{ km}^2$), vertex limits ($4–500$), bounding box, and centroid JSON metadata.
  - `AnalysisRun` (`analysis_runs`): Master run manifest recording multi-temporal scene metadata, dates, clouds, NDWI threshold ($\tau \in [-1.0, 1.0]$), and status (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`).
  - `WaterMetrics` (`water_metrics`): 1:1 relation to analysis runs recording pixel counts, physical area (ha, $\text{m}^2$), nullable percentage change for zero baselines, transition breakdown, and scientific limitations.
  - `AnalysisArtifact` (`analysis_artifacts`): Object storage reference registry constrained to valid buckets (`maps`, `reports`, `rasters`) and artifact types, with `expires_at` support for 90-day retention policies.
- Configured Alembic migration framework (`alembic.ini`, `alembic/env.py`, `alembic/versions/`):
  - Integrated `geoalchemy2.alembic_helpers` for spatial type and GiST index autodetection.
  - Initial migration revision `53ebad6d6a09_initial_schema.py` creating the 5 tables, 19 indexes, and enabling PostGIS extension.
- Added 20 new automated unit and integration tests:
  - `tests/test_database_models.py` (17 tests): Validating model metadata, role/quota constraints, AOI area/vertex constraints, AnalysisRun status/threshold constraints, artifact type/bucket constraints, 1:1 water metrics uniqueness, cascading deletions, and live PostGIS `ST_Area` spatial calculations.
  - `tests/test_database_migrations.py` (3 tests): Validating Alembic configuration, migration discovery, and round-trip upgrade/downgrade execution.
- Added database dependencies to `requirements.txt`:
  - `sqlalchemy>=2.0.0`
  - `geoalchemy2>=0.14.0`
  - `alembic>=1.13.0`
  - `psycopg2-binary>=2.9.9`

### Changed
- Updated `.env.example` with `DATABASE_URL` and `TEST_DATABASE_URL` connection strings.


---

## [0.4.1] - 2026-11-07
### Added
- Created permanent historical documentation suite in repository root:
  - `DEVELOPMENT_HISTORY.md`: Comprehensive narrative of all project milestones, architecture decisions, and scientific findings.
  - `PROMPT_LOG.md`: Verbatim record of all coding agent tasks, dates, outcomes, and modified files.
  - `CHANGELOG.md`: Versioned record of changes categorized by type.
  - `PROJECT_STATUS.md`: Real-time implementation status, test metrics, known technical debt, and pending priorities.

---

## [0.4.0] - 2026-11-07
### Added
- Implemented `src/aoi_validation.py`:
  - Input parsing for GeoJSON Polygon/MultiPolygon, Features, FeatureCollections, serialized JSON, and bounding boxes.
  - Geodetic ellipsoidal equal-area calculation via `pyproj.Geod` on WGS84.
  - Enforced geographical area boundaries ($0.10\text{ km}^2 \le \text{Area} \le 100.00\text{ km}^2$).
  - Topological integrity verification via `shapely.validation.explain_validity`.
  - Vertex count limitation ($\le 500$ vertices) to protect single-worker memory.
- Implemented `src/reporting.py`:
  - Dynamic CSV report builder (`generate_csv_report`) with metadata headers, quantitative component metrics, and limitation notices.
  - Publication-grade PDF report builder (`generate_pdf_report`) using ReportLab, incorporating executive KPI tables, spectral index methodology, data provenance status badges, and embedded 300 DPI map figures.
- Added 22 new unit tests:
  - `tests/test_aoi_validation.py` (15 tests).
  - `tests/test_reporting.py` (7 tests).
- Added `reportlab>=4.0.0` to `requirements.txt`.

### Changed
- Updated `src/config.py`:
  - Added `REPORTS_DIR = OUTPUTS_DIR / "reports"`.
  - Added configurable AOI validation limits: `MIN_AOI_AREA_KM2`, `MAX_AOI_AREA_KM2`, `MAX_AOI_VERTICES`.

---

## [0.3.0] - 2026-11-07
### Added
- Formulated Phase 2.1 architecture and specification blueprint in `docs/`:
  - `docs/SRS.md`: Complete Software Requirements Specification covering 7 functional requirement modules (FR-1 to FR-7), User/Admin access roles, and REST endpoint blueprints.
  - `docs/REQUIREMENTS_TRACEABILITY.md`: Traceability matrix linking all requirements to source modules, verification methods, test IDs, and delivery milestones.
  - `docs/TECHNICAL_DECISIONS.md`: 8 Architecture Decision Records (ADRs) justifying Sentinel-2 constellation lock, dual-tier retrieval, COG HTTP range subsetting, $0.1–100\text{ km}^2$ AOI validation bounds, Supabase Auth + FastAPI JWT model, PostgreSQL/PostGIS schema, 90-day storage retention, and report specifications.
  - `docs/SYSTEM_CONSTRAINTS.md`: Remote sensing boundaries, sub-pixel detection limits ($10\text{ m}$), monsoon optical cloud blockage, hydrological stage vs discharge distinctions, array memory ceilings, and a rigorous table distinguishing verified timings from proposed targets.

---

## [0.2.2] - 2026-11-07
### Added
- Published project version control repository to GitHub: `END_SEM_PROJECT_AKSHAT_3274` under `Akshat-2923`.
- Added remote tracking on branch `main`.

### Security
- Updated `.gitignore` to explicitly exclude execution log files (`*.log`, `logs/*.log`) while preserving directory markers (`!logs/.gitkeep`).

---

## [0.2.1] - 2026-10-28
### Changed
- Redesigned Streamlit web application (`app.py`) to a restrained, professional scientific GIS interface:
  - Deployed charcoal/forest-green remote-sensing palette (`#0e1115`/`#2d6a4f`).
  - Eliminated decorative emojis, gradients, and rounded pill badges.
  - Replaced card grid with aligned 5-cell analytical KPI ribbon.
  - Added monospaced cartographic metadata strips (Relative Orbit 019, MGRS Tile `T44RMQ`, EPSG:32644, 10m GSD).
  - Framed multi-panel viewports with download buttons.
  - Integrated scientific Altair bar visualization for component breakdown.
- Updated `.streamlit/config.toml` theme colors.

---

## [0.2.0] - 2026-10-28
### Added
- Built interactive presentation dashboard in Streamlit (`app.py`):
  - Dynamic metric binding to `outputs/phase1_feasibility_report.json`.
  - Sidebar parameter controls: study area specifications, data retrieval mode (`auto`, `public`, `cdse`, `synthetic`), NDWI threshold slider ($\tau \in [-0.30, 0.30]$), and cloud filter.
  - Live "Run Satellite Analysis" execution trigger with step-by-step status reporting.
  - Multi-tab presentation views for 4-panel comparison, categorical change map, dual observation inspector, and methodology.
  - Download buttons for JSON audit manifests and high-resolution figures.
- Added `streamlit>=1.30.0` to `requirements.txt`.

---

## [0.1.0] - 2026-10-28
### Added
- Initial implementation of DharaScope Phase 1: Satellite Feasibility Validation:
  - `src/config.py`: Path registries, CDSE STAC/OData endpoints, Gomti River study bounding box (`[80.88, 26.80, 81.00, 26.90]`).
  - `src/stac_client.py`: Resilient STAC client with pagination and retry logic.
  - `src/scene_selection.py`: Spatial intersection, coverage calculation, and low-cloud pair selection.
  - `src/downloader.py`: Multi-tier raster retrieval (CDSE Keycloak OAuth2 + AWS Open Data COG `/vsicurl/` range requests + synthetic sample generator) with raster integrity validation.
  - `src/water_indices.py`: McFeeters (1996) NDWI computation, zero-denominator safeguards, and binary water classification.
  - `src/change_detection.py`: Common valid pixel mask intersection, 4-class spatial transition matrix (0, 1, 2, 3, 255), and quantitative area metrics.
  - `src/visualization.py`: 300 DPI 4-panel comparison figure, single-date NDWI maps, and categorical transition maps.
  - `main.py`: Master pipeline runner saving `outputs/phase1_feasibility_report.json`.
  - Complete 22-test automated unit and integration suite in `tests/`.

### Fixed
- Resolved Windows PostGIS PROJ database conflict (`DATABASE.LAYOUT.VERSION.MINOR = 2`) by forcing runtime override to `rasterio/proj_data` before GDAL/rasterio initialization.
