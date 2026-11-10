# DharaScope: Comprehensive Development History
## Permanent Chronological Record of Architecture, Engineering Decisions, and Project Milestones

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Academic Affiliation:** Registered College Engineering Capstone Project  
**Core Study Area Baseline:** Gomti River Corridor, Lucknow, Uttar Pradesh, India (`[80.88, 26.80, 81.00, 26.90]`)  
**Repository:** `END_SEM_PROJECT_AKSHAT_3274`  
**Current Architecture Phase:** Phase 2.2 (Part A Complete: Geospatial Validation & Reporting)  

---

## Milestone 1: Phase 1 — Satellite Feasibility Validation Baseline
**Date:** 2026-10-28  
**Focus:** Proving feasibility of Sentinel-2 optical remote sensing for detecting surface water extent fluctuations along the Gomti River in Lucknow without frontend, authentication, or database scaffolding.

### 1.1 Environmental Inspection & Windows PROJ Conflict Resolution
- Inspected Python 3.11 virtual environment (`.venv`).
- **Discovered Critical Windows Conflict:** System environment variables `PROJ_LIB` and `PROJ_DATA` were globally pointed to a PostgreSQL 16 PostGIS installation (`DATABASE.LAYOUT.VERSION.MINOR = 2`), causing native GDAL/Rasterio crashes.
- **Architectural Fix:** Enforced explicit runtime path overrides in `src/config.py`:
  ```python
  _proj_dir = Path(sys.prefix) / "Lib" / "site-packages" / "rasterio" / "proj_data"
  if _proj_dir.exists():
      os.environ["PROJ_DATA"] = str(_proj_dir)
      os.environ["PROJ_LIB"] = str(_proj_dir)
  ```
  All system entrypoints (`main.py`, `app.py`, test runners) were required to import `src.config` before initializing rasterio or pyproj.

### 1.2 STAC Discovery & Candidate Scene Selection
- Integrated the official **Copernicus Data Space Ecosystem (CDSE) STAC API** (`https://stac.dataspace.copernicus.eu/v1/search`) in `src/stac_client.py`.
- Formulated `CDSESTACClient` with exponential backoff and retry adapters for status codes 429, 500, 502, 503, and 504.
- Implemented `SceneSelector` (`src/scene_selection.py`), performing polygon intersection tests against the Gomti study bounding box.
- Discovered 23 candidate observations within the temporal range `2023-10-01` to `2024-05-31`.
- Selected optimal multi-temporal observation pair with 0.0% cloud cover over the river reach:
  - **Earlier Observation ($T_1$):** `S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510` (Acquired: 2023-10-10, Post-Monsoon high stage).
  - **Later Observation ($T_2$):** `S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512` (Acquired: 2023-12-09, Early Winter low stage).
- Downloaded unauthenticated true-color overview thumbnails to `outputs/`.

### 1.3 Raster Ingestion & Dual-Route Retrieval Strategy
- Investigated CDSE OData single-band download endpoints. Documented HTTP 401 Unauthorized requirement for Keycloak credentials.
- Created `LocationTrustedSession` to preserve Bearer tokens across Copernicus domains (`dataspace.copernicus.eu`, `cloudferro.com`, `creodias.eu`) while stripping credentials if redirected to S3 presigned URLs.
- **Implemented Operational Public Fallback:** Connected to the **AWS Registry of Open Data / Earth Search STAC** hosting Sentinel-2 Level-2A Cloud-Optimized GeoTIFFs (COGs). Using GDAL/rasterio virtual file systems (`/vsicurl/`) and HTTP `Range` requests, the pipeline windowed and streamed only the Gomti River study reach without downloading full 500 MB+ tiles.
- **Implemented Offline Synthetic Fallback:** Built `generate_synthetic_sample` in `src/downloader.py` providing georeferenced simulated rasters tagged with immutable provenance labels (`PROVENANCE=SYNTHETIC_BENCHMARK_SAMPLE`) for offline presentations.

### 1.4 Spectral Indexing & Change Detection Algorithms
- Implemented McFeeters (1996) Normalized Difference Water Index in `src/water_indices.py`:
  $$\text{NDWI} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$$
- Guarded against zero/near-zero denominators ($|\text{B03} + \text{B08}| \le 10^{-6}$), clamped valid pixels to $[-1.0, 1.0]$, and applied water segmentation cutoff $\tau = 0.00$.
- Implemented `compute_water_change` in `src/change_detection.py`, intersecting valid pixel masks ($T_1 \land T_2$) across $1,323,037$ common pixels ($13,230.37\text{ ha}$) and categorizing into 4 discrete classes (0: Non-water, 1: Perennial water, 2: Seasonal recession, 3: Inundation expansion, 255: NoData).
- Generated publication cartography in `src/visualization.py`: 300 DPI 4-panel comparison panel, single-date NDWI maps, and categorical transition maps.
- **Empirical Findings:**
  - $T_1$ Inundation: $184.56\text{ ha}$ ($1,845,600\text{ m}^2$)
  - $T_2$ Inundation: $139.33\text{ ha}$ ($1,393,300\text{ m}^2$)
  - Net Delta: $-45.23\text{ ha}$ ($-24.51\%$ post-monsoon recession)
  - Perennial Channel Core: $125.18\text{ ha}$ ($67.83\%$ retention)
  - Seasonal Recession: $59.38\text{ ha}$ | Inundation Expansion: $14.15\text{ ha}$

---

## Milestone 2: Streamlit Interactive Presentation Dashboard
**Date:** 2026-10-28  
**Focus:** Rapidly building an interactive dashboard for college capstone presentation review while reusing the validated pipeline without modification.

### 2.1 Implementation
- Added `streamlit>=1.30.0` to `requirements.txt`.
- Created `app.py` importing `src.config` first to prevent PROJ collisions.
- Bound all metric displays dynamically to `outputs/phase1_feasibility_report.json` with zero hardcoding.
- Implemented sidebar controls: Study Area specs, data retrieval mode selector (`auto`, `public`, `cdse`, `synthetic`), NDWI threshold slider ($-0.30$ to $+0.30$), and "Run Satellite Analysis" execution button with live step-by-step status reporting.
- Provided tabbed inspection for the 4-panel comparison figure, categorical change map, dual observation inspector, spectral methodology, and JSON audit manifest with one-click download buttons.

---

## Milestone 3: Scientific GIS Frontend Redesign
**Date:** 2026-10-28  
**Focus:** Elevating the frontend from a generic AI dashboard to a professional, restrained remote-sensing GIS workstation.

### 3.1 Design Principles Applied
- **Eliminated AI Tropes:** Removed all emojis, rounded pill cards, and vibrant gradient buttons.
- **Restrained Cartographic Palette:** Deployed dark charcoal surfaces (`#0e1115` canvas, `#15191e` panels), deep forest green accents (`#2d6a4f`), muted slate text (`#cbd5e1`), and crisp 1px borders (`#272e38`).
- **Framed Map Viewports:** Visualizations wrapped in technical analytical frames displaying sensor geometry (Relative Orbit 019, MGRS Tile `T44RMQ`), grid CRS (`WGS 84 / UTM Zone 44N`), and ground sampling distance ($10.0\text{ m}$).
- **Aligned Tabular Ribbon:** Replaced card grid with an aligned 5-cell metric bar and a concise Altair bar chart displaying component hectares.
- **Academic Contextualization:** Expanded the hydrological limitation notice clarifying that surface area shifts reflect post-monsoon baseflow decline and Gaughat Barrage regulation rather than chemical pollution.

---

## Milestone 4: Version Control & GitHub Repository Publication
**Date:** 2026-11-07  
**Focus:** Establishing a clean remote repository on GitHub for project submission.

### 4.1 Actions Taken
- Initialized local git repository, configured `.gitignore` to strictly exclude `.venv/`, raw GeoTIFF rasters (`*.tif`, `*.jp2`), execution logs (`*.log`), and secrets (`.env`).
- Created remote GitHub repository `END_SEM_PROJECT_AKSHAT_3274` under user account `Akshat-2923`.
- Set default branch to `main` and executed initial push containing core pipeline, tests, dashboard, and reproducible outputs:
  [https://github.com/Akshat-2923/END_SEM_PROJECT_AKSHAT_3274](https://github.com/Akshat-2923/END_SEM_PROJECT_AKSHAT_3274).

---

## Milestone 5: Phase 2.1 — Software Requirements Specification & Architectural Blueprint
**Date:** 2026-11-07  
**Focus:** Establishing formal engineering specifications, technical decision records, traceability matrices, and system constraint boundaries for multi-user platform evolution.

### 5.1 Documentation Deliverables Created
1. `docs/SRS.md`: Formal Software Requirements Specification defining User/Admin roles, 7 functional requirement modules (FR-1 to FR-7), 5 non-functional requirement modules (NFR-1 to NFR-5), and FastAPI endpoint blueprints.
2. `docs/REQUIREMENTS_TRACEABILITY.md`: Traceability matrix mapping all requirements to source files, verification methods, test IDs, and delivery milestones.
3. `docs/TECHNICAL_DECISIONS.md`: 8 Architecture Decision Records (ADRs):
   - ADR-001: Retention of Sentinel-2 MSI L2A as primary optical constellation.
   - ADR-002: Multi-tier satellite retrieval (CDSE + AWS COG + Synthetic).
   - ADR-003: Subsetting via `/vsicurl/` range requests vs full tile downloads.
   - ADR-004: Geographical AOI validation envelope ($0.1–100\text{ km}^2$).
   - ADR-005: Decoupled auth via Supabase Auth + FastAPI JWT validation.
   - ADR-006: Relational PostGIS schema design.
   - ADR-007: Object storage partitioning and 90-day output retention policy.
   - ADR-008: Publication-grade PDF and CSV reporting grounded in run manifests.
4. `docs/SYSTEM_CONSTRAINTS.md`: Sensor boundaries ($10\text{ m}$ GSD, mixed-pixel limits), monsoon optical cloud blockage, hydrological stage vs discharge distinctions, array memory ceilings, and a rigorous table distinguishing verified timings from proposed targets.

---

## Milestone 6: Phase 2.2, Part A — Geospatial Validation & Reporting
**Date:** 2026-11-07  
**Focus:** Implementing standalone geographical polygon validation and dynamic manifest-grounded reporting without touching database or authentication infrastructure.

### 6.1 Geographical AOI Validation (`src/aoi_validation.py`)
- Created `validate_aoi_polygon` supporting GeoJSON dicts, Features, FeatureCollections, bounding boxes, coordinate lists, and Shapely geometries.
- Enforced OGC topological validity via `shapely.validation.explain_validity`.
- Enforced vertex count limit ($\le 500$ vertices, configurable) to prevent DOS attacks.
- Computed true geodetic surface area on the WGS84 ellipsoid via `pyproj.Geod` without planar distortion.
- Enforced area limits: $0.10\text{ km}^2 \le \text{Area} \le 100.00\text{ km}^2$.
- Created `tests/test_aoi_validation.py` with 15 passing test cases.

### 6.2 Structured Reporting Engine (`src/reporting.py`)
- Integrated `reportlab>=4.0.0` into `.venv` and `requirements.txt`.
- Created `generate_csv_report` writing structured CSV reports with metadata headers, quantitative component metrics, and scientific limitation disclaimers.
- Created `generate_pdf_report` utilizing ReportLab flowables to build publication-ready PDF reports with header metadata strips, styled KPI tables, embedded 300 DPI figures, spectral index methodology, and academic disclaimers.
- Enforced strict manifest-grounded extraction: values are loaded dynamically from `phase1_feasibility_report.json` with zero hardcoding or fabrication.
- Created `tests/test_reporting.py` with 7 passing test cases.
- **Test Suite Results:** Expanded automated test suite from 22 to 44 tests, all passing with zero regressions (`44 passed, 4 warnings in 5.57s`).

---

## Milestone 7: Phase 2.2, Part B1 — PostgreSQL 16 + PostGIS Database Foundation
**Date:** 2026-11-07  
**Focus:** Implementing relational spatiotemporal schema, declarative SQLAlchemy 2.0 models, Alembic migrations, spatial PostGIS polygon geometries, check constraints, cascading deletion rules, and verification suites on native PostgreSQL 16 + PostGIS 3.6.

### 7.1 Database Architecture & Schema Design (`src/database/`)
- Created decoupled database package `src/database/` completely separated from satellite processing and numerical algorithms:
  - `src/database/base.py`: DeclarativeBase class.
  - `src/database/config.py`: Environment-driven database connection handling (`get_database_url`), supporting production (`dharascope`) and isolated test databases (`dharascope_test`).
  - `src/database/session.py`: Thread-safe engine pooling, session factories, and transactional `get_db()` context manager.
- Implemented 5 declarative relational entities (`src/database/models/`):
  1. `Profile` (`profiles`): Mapped to Supabase Auth UUID primary key, `role` check constraint (`'user'`, `'admin'`), non-negative `quota_monthly_runs`, unique indexed email, and audit timestamps.
  2. `AOI` (`aois`): User-digitized geographical boundaries stored as WGS84 PostGIS polygon geometries (`GEOMETRY(POLYGON, 4326)`) with automatic GiST spatial indexing (`idx_aois_geometry`). Enforces ellipsoidal area limits ($0.10 \le \text{area\_km2} \le 100.00$) and vertex limits ($4 \le \text{vertex\_count} \le 500$) via database check constraints. Stores bounding box and centroid JSON envelopes.
  3. `AnalysisRun` (`analysis_runs`): Multi-temporal pipeline execution records storing $T_1$ and $T_2$ scene IDs, acquisition dates, cloud percentages, NDWI threshold ($\tau \in [-1.0, 1.0]$), execution status (`'QUEUED'`, `'PROCESSING'`, `'SUCCESS'`, `'FAILED'`), execution duration, and data provider provenance. Foreign key to `aois` uses `ondelete='SET NULL'` to preserve user run histories if an AOI is removed.
  4. `WaterMetrics` (`water_metrics`): 1:1 relation to `analysis_runs` with unique foreign key (`ondelete='CASCADE'`). Records pixel counts, physical areas in square meters and hectares ($T_1$, $T_2$, persistent, loss, gain, absolute change), nullable percentage change for zero baselines, and scientific limitation statements.
  5. `AnalysisArtifact` (`analysis_artifacts`): Master index for external object storage references, strictly preventing raster binary bloat in PostgreSQL. Constrained to valid storage buckets (`'maps'`, `'reports'`, `'rasters'`) and artifact types (`'MAP_PNG'`, `'PANEL_PNG'`, `'REPORT_PDF'`, `'REPORT_CSV'`, `'RASTER_TIFF'`, `'THUMBNAIL_JPG'`). Includes `expires_at` column to enforce automated 90-day retention policies on intermediate rasters.

### 7.2 Alembic Migration Architecture (`alembic/`)
- Configured Alembic with `geoalchemy2.alembic_helpers` for spatial type awareness and GiST index management.
- Generated initial migration revision `53ebad6d6a09_initial_schema.py` creating the 5 tables, 19 indexes, and idempotently enabling PostGIS (`CREATE EXTENSION IF NOT EXISTS postgis;`).
- Verified complete round-trip migration cycle: `alembic upgrade head` $\to$ schema verification $\to$ `alembic downgrade base` $\to$ `alembic upgrade head`.

### 7.3 Automated Test Suite & Live PostGIS Verification
- Created `tests/test_database_models.py` (17 tests) validating:
  - Table and column metadata, constraint definitions, default values, and model `__repr__` methods.
  - Profile role and quota check constraint enforcement.
  - PostGIS geometry insertion via `WKTElement` and live `ST_Area(geometry::geography)` calculation matching Lucknow reach area (4.40 km²).
  - AOI area ($0.1–100\text{ km}^2$) and vertex count ($4–500$) check constraint rejections.
  - AnalysisRun status and NDWI threshold check constraints.
  - WaterMetrics 1:1 uniqueness and zero-baseline null percentage change.
  - AnalysisArtifact bucket and type constraint enforcement.
  - Relational cascading deletions: AOI deletion sets `analysis_runs.aoi_id` to NULL; AnalysisRun deletion cascades to WaterMetrics and AnalysisArtifacts; Profile deletion cascades to AOIs and AnalysisRuns.
- Created `tests/test_database_migrations.py` (3 tests) validating Alembic configuration, script discovery, and live upgrade/downgrade cycles.
- **Test Suite Results:** Expanded automated test suite from 44 to **64 tests**, all passing with zero regressions (`64 passed, 4 warnings in 29.70s`).

---

## Milestone 8: Phase 2.2, Part B2 — Authentication, Authorization, and Database Security
**Date:** 2026-11-07  
**Focus:** Implementing Supabase Auth JWT validation, FastAPI authentication and role-based access control dependencies, profile identity management, transaction-local PostgreSQL session identity propagation, and PostgreSQL Row-Level Security (RLS) policies across all 5 database entities.

### 8.1 Supabase Auth & FastAPI Authentication (`src/auth.py`)
- Formulated `verify_supabase_jwt` enforcing cryptographic validation of incoming Bearer tokens using PyJWT.
- Implemented dual algorithm support:
  - Symmetric HMAC (`HS256`) verification using `SUPABASE_JWT_SECRET`.
  - Asymmetric RSA/ECDSA (`RS256`, `ES256`) verification using Supabase JWKS endpoints (`PyJWKClient` with in-memory public key caching).
- Enforced strict payload checks: rejects missing tokens, expired tokens (`exp`), invalid signatures, forged issuers (`iss`), wrong audiences (`aud`), and non-UUID subject claims (`sub`).
- Implemented user identity model `AuthenticatedUser`:
  - Extracts canonical role from `app_metadata.role`, `user_metadata.role`, or top-level claims.
  - Defaults unprivileged accounts to `'user'` to prevent privilege escalation via client-set claims.
- Formulated FastAPI reusable dependencies:
  - `get_current_user`: extracts Bearer token from `Authorization` header, verifies JWT, and yields authenticated context.
  - `require_admin`: enforces admin role validation, returning HTTP 403 Forbidden for non-admin users.

### 8.2 Database Row-Level Security (RLS) & Session Propagation
- **Trust Boundary Resolution:** Resolved the impedance mismatch between pooled FastAPI database connections and PostgreSQL session identity. Connections do not automatically inherit user identities; FastAPI cryptographically verifies the client JWT, and then sets transaction-local configuration parameters:
  ```sql
  SET LOCAL ROLE dharascope_app;
  SELECT set_config('request.jwt.claim.sub', :user_id, true);
  SELECT set_config('request.jwt.claim.role', :role, true);
  ```
  Setting `is_local = true` scopes the parameters strictly to the current transaction. When the transaction commits or rolls back, PostgreSQL automatically resets identity settings, preventing connection pool pollution.
- **Role Enforcement:** Created non-superuser application role `dharascope_app`. Since PostgreSQL superusers bypass RLS even under `FORCE ROW LEVEL SECURITY`, `SET LOCAL ROLE dharascope_app` guarantees that row-level policies are evaluated unconditionally.
- **Compatibility Functions:** Created PostgreSQL functions in the `auth` schema: `auth.uid()` and `auth.role()` reading from `request.jwt.claim.*`, matching Supabase PostgREST conventions.
- **Alembic Migration (`5903f15a19ed_enable_rls_and_policies.py`):**
  - Enabled and forced RLS on `profiles`, `aois`, `analysis_runs`, `water_metrics`, and `analysis_artifacts`.
  - Authored 20 granular RLS policies:
    - `profiles`: Users access only their own profile; anti-privilege escalation prevents setting `role = 'admin'`.
    - `aois`: Users access their own private AOIs or public AOIs; only owners and admins can update or delete.
    - `analysis_runs`: Strict user isolation; only owners and admins can view, update, or delete.
    - `water_metrics` & `analysis_artifacts`: Child records inherit ownership restrictions from parent `analysis_runs` via subquery checks.

### 8.3 Profile Identity Management & Anti-Privilege Escalation
- Implemented `get_or_create_profile`: auto-provisions profile row upon verified JWT login without requiring separate registration webhooks.
- Implemented `update_user_profile`: non-admin users can update display attributes (`full_name`), but attempts to alter `role` or `quota_monthly_runs` raise HTTP 403 Forbidden at the API layer.
- Enforced defense-in-depth: Even if a malicious request bypassed the API guard, PostgreSQL's RLS policy check (`WITH CHECK ((auth.uid() = id AND role = 'user') OR auth.role() = 'admin')`) triggers an immediate database-level policy violation.

### 8.4 Automated Test Suite Expansion
- Created `tests/test_auth_jwt.py` (15 tests) testing valid tokens, admin tokens, missing tokens, invalid signatures, expired tokens, forged issuers, invalid audiences, non-UUID subjects, 403 admin enforcement, auto-provisioning, and API-level role escalation blocks.
- Created `tests/test_database_security_rls.py` (6 tests) verifying actual PostgreSQL RLS execution: User A vs User B private AOI isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection.
- **Test Suite Results:** Expanded automated test suite from 64 to **85 tests**, all passing with zero regressions (`85 passed, 4 warnings in 9.65s`).

---

## 9. Milestone 9: Phase 2.2B2 Security Hardening (Trusted Role Extraction & Production Guards)

**Date:** 2026-11-10  
**Phase:** 2.2 Part B2 Security Hardening  
**Scope:** Authentication Trust Boundary, Role Extraction, Production Fail-Closed Guards & Security Audit  

### 9.1 Vulnerability Identification & Root Cause
- In the initial Phase 2.2B2 implementation, `AuthenticatedUser.from_claims()` evaluated user authorization roles by falling back to `claims.get("user_metadata", {}).get("role")` and top-level `claims.get("role")`.
- In Supabase Auth, `user_metadata` is client-controlled: unauthenticated callers during `auth.signUp()` or authenticated users during `auth.updateUser()` can write arbitrary JSON payloads into `user_metadata`.
- Consequently, an untrusted user could supply `{"data": {"role": "admin"}}` during signup, causing the backend to elevate their session to `role = "admin"` and auto-provision an admin database profile.

### 9.2 Remediation & Architectural Hardening
- **Strict Role Extraction:** Modified `src/auth.py` so application roles are derived **strictly and exclusively** from `claims.get("app_metadata", {}).get("role")`.
- **Rejection of Client Metadata:** Discarded `user_metadata` entirely from authorization decisions.
- **Supabase System Role Separation:** Prevented mapping of Supabase's top-level session claim `role: "authenticated"` to application administrative permissions. Any unrecognized, non-string, or missing role unconditionally defaults to `"user"`.
- **Database Role Hardening:** Updated migration `5903f15a19ed_enable_rls_and_policies.py` to explicitly enforce `NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE` on the `dharascope_app` role. Audited PostgreSQL: verified `dharascope_app` does not own application tables (table owner remains `postgres`), ensuring RLS is strictly evaluated.
- **Production Fail-Closed Guards:** Updated `get_jwt_secret()` and `get_jwt_issuer()` in `src/auth.py` to raise HTTP 500 configuration errors in production (`ENVIRONMENT=production` or `DHARASCOPE_ENV=production`) if `SUPABASE_JWT_SECRET` or `SUPABASE_ISSUER` / `SUPABASE_URL` is missing.

### 9.3 Security Verification & Expanded Test Coverage
- Expanded `tests/test_auth_jwt.py` with 7 new security test cases:
  - `test_user_metadata_role_admin_cannot_obtain_admin_privileges`: Proves signed JWT with `user_metadata.role = "admin"` gets `role = "user"` and is denied admin access (HTTP 403).
  - `test_missing_app_metadata_role_defaults_to_user`: Proves missing role defaults safely to `"user"`.
  - `test_unknown_roles_cannot_obtain_elevated_privileges`: Proves invalid role strings (`superuser`, `root`, `manager`, integers, `None`) normalize to `"user"`.
  - `test_supabase_standard_role_claim_never_elevates`: Proves top-level `role: "authenticated"` never elevates privileges.
  - `test_profile_autoprovisioning_cannot_create_admin_from_user_metadata`: Proves profile auto-provisioning stores `role = "user"` even when user-metadata claims `role: "admin"`.
  - `test_production_missing_jwt_secret_fails_closed`: Proves missing secret in production triggers HTTP 500 fail-closed response.
  - `test_production_missing_issuer_fails_closed`: Proves missing issuer in production triggers HTTP 500 fail-closed response.
- **Automated Test Results:** Full test suite expanded from 85 to **92 tests**, all passing with zero regressions (`92 passed, 4 warnings in 18.68s`).

---

## 10. Milestone 10: Phase 2.2 Part C — FastAPI Application Service Layer

**Date:** 2026-11-10  
**Phase:** 2.2 Part C  
**Scope:** REST API Application Bootstrap, Pydantic Schemas, Service Layer, Asynchronous Pipeline Background Dispatch, Artifact Delivery, and Integration Tests  

### 10.1 Application Bootstrap & Schema Architecture
- Created `server.py` as the ASGI application entrypoint, instantiating `app = create_app()` and providing uvicorn server startup while ensuring `src.config` is loaded first to protect against Windows PROJ conflicts.
- Built `src/api/app.py` utilizing the application factory pattern, configuring CORS middleware, global exception handlers for `AOIValidationError`, `ReportingError`, `RequestValidationError`, `HTTPException`, and catching generic uncaught exceptions with sanitized error envelopes.
- Formulated Pydantic schema models in `src/api/schemas/`:
  - `common.py`: `APIErrorResponse` and `ValidationErrorResponse`.
  - `health.py`: Detailed subsystem status (`HealthResponse`).
  - `auth.py`: `UserProfileResponse` and `AdminUserUpdate`.
  - `aoi.py`: `AOIValidationRequest`, `AOIValidationResponse`, `AOICreateRequest`, `AOIUpdateRequest`, `AOIResponse`, and `AOIListResponse`.
  - `analysis.py`: `AnalysisCreateRequest`, `AnalysisResponse`, `AnalysisListResponse`, `WaterMetricsResponse`, and `ArtifactResponse`.

### 10.2 Service Layer & Asynchronous Background Execution
- **AOI Service (`src/services/aoi_service.py`):** Integrates geometry validation from `src/aoi_validation.py`, PostGIS `GEOMETRY(POLYGON, 4326)` conversion via WKT and GeoJSON, paginated queries, ownership enforcement, and safe updates/deletions.
- **Analysis Pipeline Service (`src/services/analysis_service.py`):**
  - Manages monthly user run quotas with transaction-safe checks.
  - Resolves target geometries either from registered database AOIs or validated inline GeoJSON polygons.
  - Creates database `analysis_runs` records in `QUEUED` state.
  - Dispatches heavy scientific raster processing via FastAPI `BackgroundTasks` to `execute_pipeline_worker`.
  - Orchestrates STAC search (`CDSESTACClient`), scene pair selection (`SceneSelector`), multi-tier band downloading (`CDSEDownloader`), NDWI calculation (`process_scene_bands`), multi-temporal change detection (`compute_water_change`), and figure generation (`plot_comparison_panel`, `plot_ndwi_single_observation`, `plot_water_change_map`).
  - Automatically records generated rasters, figures, and manifests in `analysis_artifacts` and writes summary metrics to `water_metrics`.
  - Sanitizes internal filesystem paths and sensitive credentials from diagnostic error messages using regex filters.
- **Artifact & Reporting Service (`src/services/artifact_service.py`):**
  - Enforces database ownership and Row-Level Security checks for artifact downloads.
  - Compiles on-demand ReportLab publication-ready PDFs and RFC 4180 CSV reports from persisted run manifests upon authorized requests.
  - Streams files using Starlette `FileResponse` without exposing absolute host filesystem paths in client responses.

### 10.3 API Endpoints & Routers
- Implemented modular routers in `src/api/routers/`:
  - `health.py`: `GET /health`, `GET /api/v1/health`, `GET /`.
  - `auth.py`: `GET /api/v1/auth/me`, `PATCH /api/v1/auth/me`, `GET /api/v1/admin/users`, `PATCH /api/v1/admin/users/{user_id}`.
  - `aois.py`: `POST /api/v1/aois/validate`, `POST /api/v1/aois`, `GET /api/v1/aois`, `GET /api/v1/aois/{id}`, `PATCH /api/v1/aois/{id}`, `DELETE /api/v1/aois/{id}`.
  - `analyses.py`: `POST /api/v1/analyses`, `GET /api/v1/analyses`, `GET /api/v1/analyses/{id}`, `DELETE /api/v1/analyses/{id}`, `GET /api/v1/analyses/{id}/metrics`, `GET /api/v1/analyses/{id}/artifacts`, `GET /api/v1/analyses/{id}/reports/csv`, `GET /api/v1/analyses/{id}/reports/pdf`.
  - `artifacts.py`: `GET /api/v1/artifacts/{id}/download`.

### 10.4 Architectural Decision Records & Traceability
- Added ADR-009 ("FastAPI Application Service Layer, Schema Validation, and Asynchronous Pipeline Worker") to `docs/TECHNICAL_DECISIONS.md`.
- Added Module 8 (FastAPI Application Service Layer & Gateway) with requirements FR-8.1 through FR-8.5 to `docs/SRS.md`.
- Documented complete endpoint specifications in `docs/API_CONTRACTS.md`.
- Documented REST API latency and background concurrency constraints in `docs/SYSTEM_CONSTRAINTS.md`.

### 10.5 Automated Integration Test Suite
- Built `tests/test_api_service_layer.py` containing 33 integration tests across 6 test classes:
  - `TestSystemHealthEndpoints`: Health check and OpenAPI docs availability.
  - `TestAuthenticationAndAuthorization`: JWT Bearer enforcement, role privileges, and admin quota administration.
  - `TestAOIEndpoints`: AOI geometry validation and full CRUD lifecycle.
  - `TestCrossUserResourceIsolation`: Multi-tenant isolation for private AOIs and public AOI shared viewing.
  - `TestAnalysisPipelineEndpoints`: Pipeline run triggers, parameter validations, and full background synthetic raster processing.
  - `TestReportDownloadEndpoints`: Authorized PDF/CSV downloads, uncompleted run download rejections, and cross-user report protections.
  - `TestErrorSanitizationAndEdgeCases`: 404/422 status codes and error payload sanitization.
- **Automated Test Suite Expansion:** Full repository test suite expanded from 92 to **125 tests**, all passing with zero regressions (`125 passed in 62.73s`).

---

## 11. Milestone 11: Phase 2.2C Post-Implementation Verification & Architecture Audit

**Date:** 2026-11-10  
**Phase:** 2.2 Part C Post-Implementation Verification  
**Scope:** Architectural Audit of Background Jobs, Storage Subsystems, Admin Role IdP Synchronization, and Deprecation Warning Remediation  

### 11.1 Background Jobs & Lifecycle Analysis
- **Restart Survival:** Verified that FastAPI `BackgroundTasks` operates strictly in-process. If the application server terminates or reboots during pipeline execution, pending or running tasks do not survive; corresponding database records remain frozen in `QUEUED` or `PROCESSING` state as orphaned jobs.
- **Worker Database Session Independence:** Confirmed that `execute_pipeline_worker()` borrows a brand new SQLAlchemy session via `get_authenticated_db(user)` distinct from the HTTP request context. The worker sets transaction-local RLS claims, commits upon success, executes rollback and records sanitized failure diagnostics on errors, and unconditionally closes the session in `finally:`.
- **Architectural Boundary:** In-process `BackgroundTasks` is appropriate for the current single-instance capstone prototype, but a durable persistent queue (e.g., Celery/Redis) with automatic job recovery is required for multi-worker production deployments.

### 11.2 Artifact Storage & Authorization Verification
- **Physical vs. Logical Storage:** Audited `src/services/analysis_service.py` and `src/services/artifact_service.py`. While the database entity `AnalysisArtifact` populates logical buckets (`rasters`, `maps`, `reports`), file payloads are stored exclusively on the local host filesystem (`outputs/<user_id>/<run_id>/`). No remote uploads to Supabase Storage / S3 occur in Phase 2.2.
- **Download Authorization:** Confirmed that `/api/v1/artifacts/{id}/download` and report download endpoints (`/reports/csv`, `/reports/pdf`) enforce strict user ownership validation via parent `AnalysisRun` ownership checks and PostgreSQL Row-Level Security before streaming files. Cross-user unauthorized downloads return HTTP 404/403.

### 11.3 Admin Role Synchronization & Token Lifecycle
- **Projection vs. Identity Provider:** Traced `PATCH /api/v1/admin/users/{user_id}`. The endpoint mutates `profiles.role` in the PostgreSQL database only. It does not update Supabase's `app_metadata.role` (which requires service-role Admin API access).
- **Stale Token & Revocation Behavior:** Because `src/auth.py` strictly derives application permissions from the verified JWT `app_metadata.role`, promoting a user in PostgreSQL does not grant admin access until Supabase reissues a token with `app_metadata.role = "admin"`. Conversely, revoking an admin in the database does not invalidate an active admin JWT until token expiry (standard TTL: 3600 seconds).

### 11.4 Warning Categorization & Actionable Remediation
- **Warning Count Audit:** Pytest reported 147 warnings across the 125-test suite:
  - 144 warnings: Upstream `PendingDeprecationWarning` in `rasterio` (`rasterio/features.py`, `windows.py`, `transform.py`) due to third-party Affine matrix multiplication using `*` rather than `@`.
  - 1 warning: Upstream `StarletteDeprecationWarning` in `fastapi.testclient` regarding `httpx` vs `httpx2`.
  - 2 warnings: Actionable deprecations in DharaScope codebase (`src/api/app.py:84,88`) using deprecated `status.HTTP_422_UNPROCESSABLE_ENTITY`.
- **Remediation:** Migrated `src/api/app.py` to `status.HTTP_422_UNPROCESSABLE_CONTENT` (RFC 9110). Reduced warning count from 147 to 145 with zero test regressions (125/125 passed in 71.75s).


