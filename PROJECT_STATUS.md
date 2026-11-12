# DharaScope: Current Project Status
## Real-Time Subsystem Health, Test Coverage, Known Debt & Development Priorities

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Current Phase:** Phase 2.4.1 — Scientific Results Audit & GitHub Synchronization (Complete)  
**Last Updated:** 2026-11-12  
**Overall System Health:** `HEALTHY / OPERATIONAL / AUDITED & SYNCHRONIZED`  

---

## 1. Executive Summary

DharaScope has successfully completed **Phase 2.4.1 (Scientific Results Audit & GitHub Synchronization)**. This audit rigorously evaluated the mathematical, spatial, and hydrodynamic consistency between Phase 1 feasibility figures and Phase 2.4 live satellite validation results, verified reproducibility across all raster assets, and verified complete synchronization with the remote GitHub repository.

### Key Audit Findings:
1. **Scientific Scale Consistency:** Proved that both Phase 1 (184.56 ha / 139.33 ha, -24.51%) and Phase 2.4 (0.53 ha / 1.66 ha, +213.21%) were calculated from the **exact same** Sentinel-2 Level-2A acquisitions (`S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510` and `S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512`), identical 10m B03/B08 bands, identical McFeeters NDWI formulation ($\tau = 0.00$), and identical projected CRS (`EPSG:32644`). The numerical difference is 100% explained by spatial extent:
   - *Phase 1:* Regional basin corridor `[80.88, 26.80, 81.00, 26.90]` spanning **13,230.37 ha** (132.30 km²), encompassing wide meanders, oxbows, and floodplain wetlands experiencing natural post-monsoon recession (-45.23 ha). Note that this regional rectangle exceeds the single-run system ceiling of 100 km² established in Phase 2.2 (`MAX_AOI_AREA_KM2 = 100.00 km²`).
   - *Phase 2.4:* Urban reach polygon `[80.90, 26.84, 80.92, 26.86]` spanning **439.79 ha** (4.40 km², 3.32% of regional area) along the channelized Gomti Riverfront in Lucknow, where post-monsoon barrage impoundment (Gaughat and Gomti Barrages) elevates urban water pool levels (+1.13 ha).
2. **Cloud Cover Metadata Clarification:** Confirmed that the 0.0% cloud cover reported in STAC metadata represents whole-scene granule metadata (`eo:cloud_cover` across the $100 \times 100\text{ km}$ MGRS tile `T44RMQ`), rather than an AOI-clipped cloud mask.
3. **Reproducibility & Evidence Audit:** Verified all 8 Playwright browser screenshots (`outputs/validation_phase2_4/01_*.png` through `08_*.png`), execution summary JSON, matching CSV data manifest (`dharascope_analysis_c7463b8c.csv`), and 7.4 MB PDF report. Confirmed zero synthetic data intrusion into real orbital workflows.
4. **Automated Test Suite Status:** **203 passing automated tests** (185 backend pytest + 18 frontend Vitest) plus 8 live browser validation steps, with 100% pass rate.
5. **GitHub Synchronization:** All local commits up to Phase 2.4.1 fast-forward synchronized to `origin/main` on GitHub (`Akshat-2923/END_SEM_PROJECT_AKSHAT_3274`).

In **Phase 2.4**, the complete stack—comprising PostgreSQL 16.15 + PostGIS 3.6.2, the FastAPI ASGI application service layer, and the React 19 + TypeScript GIS Workstation—was executed concurrently and validated using genuine Sentinel-2 Level-2A multi-spectral observations over the Gomti River study reach (`[80.90, 26.84, 80.92, 26.86]` WGS84):
1. **Live Browser Automation (Playwright Chromium):** Automated script `scripts/validate_real_satellite_browser.mjs` drove a headless browser through all 8 user journey stages, verifying login, real-time PostGIS geometry validation (4.4048 km² / 440.48 ha), retrieval tier configuration, pipeline execution, real orbital badge display (`REAL ORBITAL S2`), scientific metrics rendering, authenticated cartographic artifact streaming, and publication report downloads.
2. **Empirical Satellite Observations (AWS Open Data COG Archive):** Discovered and streamed real Sentinel-2 Level-2A surface reflectance rasters without synthetic fallback:
   - $T_1$ Observation (2023-10-10): `S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510` (0.0% cloud cover).
   - $T_2$ Observation (2023-12-09): `S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512` (0.0% cloud cover).
   - Ground Sampling Distance (GSD): 10m native resolution across Band 3 (Green) and Band 8 (NIR) in UTM Zone 44N (EPSG:32644).
3. **Hydrological Surface Water Dynamics Metrics:**
   - Overlapping Valid Spatial Domain: 439.79 ha (43,979 common valid pixels).
   - Earlier Surface Water ($T_1$, 2023-10-10): 0.53 ha (5,300 m²).
   - Later Surface Water ($T_2$, 2023-12-09): 1.66 ha (16,600 m²).
   - Persistent Water (Perennial channel core): 0.39 ha (3,900 m²).
   - Seasonal Recession (Apparent Loss): 0.14 ha (1,400 m²).
   - Inundation Expansion (Apparent Gain): 1.27 ha (12,700 m²).
   - Net Surface Delta: +1.13 ha (+213.21%).
4. **Data Provenance & Security Hardening:** Verified that CSV reports embed `# Real Satellite Data,TRUE` and exact scene IDs, and that PDF reports compile cleanly (7.4 MB). Hardened CORS configuration in `src/api/app.py` for standard browser credentialed fetch compliance, and standardized datetime/cloud parsing in `src/services/analysis_service.py` and `src/reporting.py`.

The full test suite stands at **203 automated tests** (185 backend pytest + 18 frontend Vitest) plus 8 live browser validation steps, with 100% pass rate.

---

## 2. Subsystem Implementation Status

### 2.1 Completed Subsystems & Features
- [x] **Satellite Catalogue Discovery (`src/stac_client.py`):** Copernicus Data Space Ecosystem (CDSE) STAC API client with pagination, exponential backoff, and item metadata extraction.
- [x] **Observation Pair Optimization (`src/scene_selection.py`):** Polygonal study area intersection, cloud cover filtering, and optimal temporal separation.
- [x] **Multi-Tier Raster Retrieval (`src/downloader.py`):**
  - Tier 1: Official CDSE Keycloak OAuth2 + OData single-band JP2 streaming (`LocationTrustedSession`).
  - Tier 2: Public Open AWS Sentinel-2 COG archive via windowed HTTP byte-range requests (`/vsicurl/`), clipping to study bbox without downloading full 500 MB+ tiles.
  - Tier 3: Georeferenced synthetic benchmark sample generator explicitly tagged with immutable provenance labels for offline demonstrations.
- [x] **Spectral Processing Engine (`src/water_indices.py`):** McFeeters (1996) NDWI computation from Band 3 (Green 10m) and Band 8 (NIR 10m), zero-denominator protection ($|\text{B03}+\text{B08}| \le 10^{-6}$), $[-1.0, 1.0]$ clamping, and water segmentation ($\tau = 0.00$).
- [x] **Multi-Temporal Change Detection (`src/change_detection.py`):** Intersection of common valid pixels ($T_1 \land T_2$), 4-class categorical transition matrix, quantitative area metrics ($\text{m}^2$, ha, % change, zero-baseline safety), and mandatory scientific limitation statements.
- [x] **Publication Cartography (`src/visualization.py`):** 300 DPI 4-panel comparison panel, single-observation NDWI maps, and categorical transition maps.
- [x] **Interactive GIS Dashboard (`app.py` & `.streamlit/`):** Restrained scientific GIS workstation featuring charcoal/forest-green styling, monospaced cartographic strips, aligned KPI ribbons, parameter tuning, live pipeline execution, and download actions.
- [x] **Geographical AOI Validation (`src/aoi_validation.py`):** Multi-format geometry parser, geodetic area calculation ($0.10–100.00\text{ km}^2$), Shapely topology validation, and vertex count limits ($\le 500$).
- [x] **Manifest Reporting Engine (`src/reporting.py`):** Structured CSV export and ReportLab publication-grade PDF report compiler.
- [x] **PostgreSQL 16 + PostGIS 3.6 Database Subsystem (`src/database/` & `alembic/`):**
  - Declarative SQLAlchemy models: `Profile`, `AOI`, `AnalysisRun`, `WaterMetrics`, `AnalysisArtifact`.
  - Spatiotemporal PostGIS geometry storage: `GEOMETRY(POLYGON, 4326)` with spatial GiST indexing (`idx_aois_geometry`).
  - Database-level check constraints: role validation, quota bounds, AOI area ($0.1–100\text{ km}^2$) and vertex count ($4–500$), analysis status, NDWI thresholds, and artifact storage buckets/types.
  - Foreign key cascading: `ondelete='SET NULL'` on AOI relations to preserve run history, `ondelete='CASCADE'` on profile and analysis metrics/artifacts.
  - Object storage decoupling: zero raster binaries in database; references to external object storage with 90-day retention metadata (`expires_at`).
  - Migration framework: Alembic with GeoAlchemy2 helpers, initial migration revision `53ebad6d6a09_initial_schema.py`.
- [x] **Authentication, Authorization & Database Security (`src/auth.py` & `5903f15a19ed_enable_rls_and_policies.py`):**
  - Cryptographic Supabase JWT Bearer token validation (HS256 symmetric and RS256/ES256 asymmetric JWKS with caching).
  - FastAPI dependencies: `get_current_user` and `require_admin`.
  - Transaction-local PostgreSQL session identity propagation via `SET LOCAL ROLE dharascope_app;` and `set_config('request.jwt.claim.sub', :sub, true)`.
  - Native PostgreSQL Row-Level Security (RLS): enabled and forced across all 5 tables with 20 granular policies.
  - Profile auto-provisioning and database-enforced anti-privilege escalation guards.
- [x] **FastAPI Application Service Layer (`server.py`, `src/api/`, `src/services/`):**
  - Production ASGI server bootstrap (`server.py`) and FastAPI factory (`src/api/app.py`).
  - Health check endpoints (`/health`, `/api/v1/health`, `/`).
  - Authentication and administrative user endpoints (`/api/v1/auth/me`, `/api/v1/admin/users`).
  - AOI lifecycle & validation endpoints (`/api/v1/aois/validate`, `/api/v1/aois`, `/api/v1/aois/{id}`).
  - Asynchronous analysis lifecycle (`/api/v1/analyses`, `/api/v1/analyses/{id}`, `/metrics`, `/artifacts`).
  - Authorized report download endpoints (`/reports/csv`, `/reports/pdf`, `/api/v1/artifacts/{id}/download`).
  - Interactive OpenAPI documentation (`/docs`, `/redoc`, `/openapi.json`).
- [x] **Identity Provider Role Synchronization & Two-Phase Consistency (`src/auth.py`, `src/services/role_sync_service.py`):**
  - Supabase Auth Admin API synchronization via `PUT /auth/v1/admin/users/{user_id}` targeting `app_metadata.role`.
  - Guarded commit boundary: `session.commit()` inside try/except block with automatic compensating rollback restoring Supabase `old_role` on PostgreSQL commit failure.
  - Ambiguous commit recovery: verifies authoritative role via fresh database session (`get_session_factory()`). Reconciles Supabase to `new_role` on lost ACK; never blindly compensates.
  - Anti-split-brain invariant: never marks a synchronization `COMPENSATED` without proving both PostgreSQL and Supabase Auth contain `old_role`.
  - Immediate admin revocation via authoritative database check on `profiles.role` (0 delay).
  - Durable `RoleSyncJournal` with thread safety, `os.fsync()` disk synchronization, corrupted line resilience, and restart recovery.
  - Reconciliation endpoint (`POST /api/v1/admin/users/{user_id}/reconcile`) with strict anti-privilege escalation rejecting client-writable `user_metadata`.
- [x] **Requirements & Architectural Documentation (`docs/`):** Full SRS (`docs/SRS.md`), Traceability Matrix (`docs/REQUIREMENTS_TRACEABILITY.md`), Technical Decisions (`docs/TECHNICAL_DECISIONS.md`), API Contracts (`docs/API_CONTRACTS.md`), and System Constraints (`docs/SYSTEM_CONSTRAINTS.md`).
- [x] **Version Control:** Published to GitHub under `Akshat-2923/END_SEM_PROJECT_AKSHAT_3274`.

### 2.2 Completed Subsystems in Phase 2.3
- [x] **Modern React 19 GIS Workstation (`frontend/`):**
  - Vite + React 19 + TypeScript modern client architecture.
  - Interactive Leaflet cartography (`CartoDB Dark Matter`, EPSG:4326 WGS84 coordinates) with pre-configured Gomti reach baseline polygon.
  - Real-time PostGIS geometry validation calling `POST /api/v1/aois/validate` enforcing equal-area ellipsoidal bounds ($0.10–100.00\text{ km}^2$), topological integrity, vertex limits ($\le 500$), centroid, and bounding box metrics.
  - AOI persistence & catalog (`POST /api/v1/aois`, `GET /api/v1/aois`, `DELETE /api/v1/aois/{id}`).
  - Supabase Auth session provider with Web Crypto HS256 development JWT generator for offline testing.
  - Bearer JWT injection into outbound requests with standardized error parsing (`APIErrorResponse`).
  - Analysis configuration panel: NDWI threshold cutoff ($\tau \in [-0.30, 0.30]$), max scene cloud cover ($\le 10\%$), ISO-8601 temporal search window, satellite retrieval tier, and synchronous/asynchronous execution modes.
  - Real-time polling loop (`GET /api/v1/analyses/{id}`) tracking `QUEUED` $\to$ `PROCESSING` $\to$ `SUCCESS` / `FAILED` with execution duration timer and Sentinel-2 $T_1/T_2$ scene discovery metadata.
  - Quantitative Surface Water Area KPIs: $T_1$ baseline area, $T_2$ comparison area, net surface delta ($\Delta$ ha and $\Delta \%$).
  - 4-Class Categorical Water Dynamics Breakdown: Persistent Water (Perennial), Apparent Water Loss (Recession), Apparent Water Gain (Inundation), and Persistent Non-Water.
  - Prominent scientific limitation statement prominently displayed from verified database metadata.
  - Authenticated map artifact streaming (`AuthenticatedImage`) with temporary blob URLs for dual-panel comparison, categorical change map, and single-observation NDWI maps.
  - One-click authenticated report downloads: publication-grade ReportLab PDF (`/reports/pdf`) and structured CSV manifest (`/reports/csv`).
  - Analysis runs archive drawer with historical run selection and cleanup.

### 2.3 Completed Subsystems in Phase 2.4 (Real Satellite End-to-End Validation)
- [x] **Live Multi-Service Concurrency & Browser Workstation Driving:**
  - Automated Playwright Chromium browser harness (`scripts/validate_real_satellite_browser.mjs`) driving full stack (PostgreSQL 16, FastAPI 8000, Vite 5173).
  - Validated all 8 interactive steps with full-page screenshots and empirical telemetry.
- [x] **Genuine Sentinel-2 Level-2A Multi-Spectral Surface Water Processing:**
  - Zero-synthetic constraint satisfied: verified genuine orbital acquisitions ($T_1$ 2023-10-10, $T_2$ 2023-12-09, 0.0% cloud cover).
  - Streamed Band 3 (Green 10m) and Band 8 (NIR 10m) rasters via AWS Open Data COG archive (`PUBLIC_OPEN_SENTINEL2_COGS`).
  - Calculated real NDWI surface water extent and 4-class categorical transitions over 439.79 ha common valid pixels (+1.13 ha net gain, +213.21%).
  - Displayed `REAL ORBITAL S2` badge, confirmed synthetic warning banners remain hidden for real data.
  - Authenticated map artifact streaming for comparison panel, single NDWI, and change map.
  - Downloaded and verified structured CSV data manifest with real provenance (`# Real Satellite Data,TRUE`) and publication-grade ReportLab PDF (7.4 MB).
- [x] **CORS & Service Layer Hardening:**
  - Configured explicit origins for browser credentialed requests in `src/api/app.py`.
  - Hardened item datetime, cloud cover, and discovery stage metadata parsing in `src/services/analysis_service.py` and `src/reporting.py`.

### 2.4 Pending Subsystems (Scheduled for Phase 3 / Production Hardening)
- [ ] **Empirical Performance Benchmarks (`benchmarks/`):** Load testing API latency ($< 500\text{ ms}$), PDF compilation ($< 10\text{ s}$), and worker memory footprint on $25\text{ km}^2$ AOIs ($< 2\text{ GB RAM}$).
- [ ] **Durable Task Queue Migration:** Celery/Redis worker migration for distributed background jobs across server restarts.

### 2.5 Blocked Subsystems
- **None.** All prerequisites for Phase 2.4 are fully satisfied and validated.

---

## 3. Automated Test Suite Metrics & Audit Categorization

- **Total Automated Tests:** 203 passing tests (185 backend pytest tests + 18 frontend Vitest tests, 1 skipped live integration test)
- **Pass Rate:** 100% (203 passing tests, zero regressions)
- **Backend Test Modules (16 modules, 185 passed, 1 skipped):**
  1. `tests/test_frontend_integration.py`: 8 passed (complete user journey: health, auth, AOI validate/persist, analysis run, metrics, artifacts, PDF/CSV downloads, tenant isolation, synthetic provenance enforcement, expired/unauthorized token handling).
  2. `tests/test_admin_role_sync.py`: 27 passed (promotion, revocation, invalid roles, Supabase 404 user not found, 500/timeout failure rollbacks, database persistence, quota-only skip IdP, 403 non-admin rejection, 401 unauthenticated, production fail-closed, compensating rollback on commit failure, desynchronized reconciliation, unreachable Supabase error handling, reconciliation idempotency, anti-privilege escalation, lost ACK reconciliation to new_role, commit definitely fails compensation, DB unavailable during verification, Supabase unavailable during reconciliation).
  3. `tests/test_role_journal_durability.py`: 6 passed (missing file/directory auto-creation, 20-thread concurrent writes, process restart disk recovery, corrupted/truncated JSONL line resilience, disk write failure fallback to in-memory state, unreconciled entry lifecycle filtering).
  4. `tests/test_storage.py`: 16 passed, 1 skipped (local and Supabase storage lifecycle, upload failure error handling, decoupled live integration test).
  5. `tests/test_aoi_validation.py`: 15 passed (valid bboxes, GeoJSON dicts, Features, Collections, strings, MultiPolygons, min/max area limits, topology self-intersections, coordinate bounds, vertex ceilings).
  6. `tests/test_api_service_layer.py`: 33 passed (system health, root metadata, OpenAPI accessibility, unauthenticated rejection, invalid/expired JWT rejection, profile retrieval/update, admin user list, admin quota update, AOI geometry validation, out-of-bounds rejection, AOI CRUD, cross-user private AOI isolation, public AOI shared viewing and edit protections, analysis creation with existing/inline AOIs, missing geometry rejection, invalid threshold rejection, synthetic background pipeline execution, authorized report/artifact download, cross-user report download rejection, queued report rejection, 404/422 error sanitization).
  7. `tests/test_auth_jwt.py`: 25 passed (valid user/admin JWTs, untrusted user-metadata rejection, missing role defaults, unknown role handling, Supabase system claim isolation, missing token, invalid signature, expired token, forged issuer, invalid audience, non-UUID subject, 401/403 status responses, profile auto-creation, anti-privilege escalation, production missing secret/issuer fail-closed guards, development fallback secret rejection in production, immediate admin revocation with stale JWT, fail-closed DB errors).
  8. `tests/test_change_detection.py`: 3 passed (change matrix, area metrics, zero-baseline percentage handling, spatial dimension mismatch).
  9. `tests/test_database_migrations.py`: 3 passed (Alembic configuration loading, migration script discovery across all revisions, live PostgreSQL upgrade/downgrade cycle).
  10. `tests/test_database_models.py`: 17 passed (model metadata, profile role/quota constraints, AOI PostGIS insertion, geodetic spatial calculations, AOI area/vertex constraints, analysis run constraints, 1:1 water metrics uniqueness, artifact type/bucket constraints, cascading deletions).
  11. `tests/test_database_security_rls.py`: 6 passed (live PostgreSQL RLS tests verifying private AOI cross-user isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection).
  12. `tests/test_downloader.py`: 11 passed (auth errors, credential detection, Bearer token masking, redirect auth preservation, HTML error rejection, corrupted binary rejection, raster verification, synthetic generation, band retrieval modes).
  13. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full pipeline execution from bands to NDWI to change detection).
  14. `tests/test_reporting.py`: 7 passed (metrics extraction, CSV report generation, PDF report generation, synthetic badges).
  15. `tests/test_stac_client.py`: 3 passed (bbox validation, item metadata extraction, HTTP error backoff).
  16. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero-denominator protection, water classification, shape mismatch error).
- **Frontend Test Suites (6 suites, 18 passed in Vitest):**
  1. `src/__tests__/jwt_security.test.ts`: 2 passed (Web Crypto dev token generation in DEV mode, strict rejection in PROD mode).
  2. `src/__tests__/api.test.ts`: 5 passed (Bearer injection, 400 error, 401 error, blob download).
  3. `src/__tests__/MetricsDisplay.test.tsx`: 4 passed (KPI cards, 4-class transitions, limitation statement, synthetic benchmark alert banner).
  4. `src/__tests__/ReportActions.test.tsx`: 3 passed (PDF/CSV download dispatch and notifications).
  5. `src/__tests__/AuthModal.test.tsx`: 2 passed (Dev session options, token mode tab switching).
  6. `src/__tests__/MapPicker.test.tsx`: 2 passed (Gomti preset, Leaflet initialization, backend validation feedback).
- **Audit Categorization Matrix:**
  - *Tier A (Mocked Unit Tests):* Fast, isolated verification mocking external APIs and cloud storage (`test_admin_role_sync.py`, `test_storage.py` mock suites).
  - *Tier B (FastAPI TestClient Subsystem Tests):* In-memory ASGI requests through full FastAPI middleware, dependencies, schemas, and services (`test_api_service_layer.py`, `test_frontend_integration.py`).
  - *Tier C (Local PostgreSQL 16 + PostGIS 3.6 Hardware Tests):* Real database execution validating spatial indexes, geometry constraints, foreign key cascades, and real PostgreSQL Row-Level Security policies (`test_database_models.py`, `test_database_security_rls.py`).
  - *Tier D (Live External Cloud Services):* Real external network queries: CDSE STAC search (23 features retrieved), public AWS COG byte-range reads (`/vsicurl/`). Commercial APIs (SentinelHub) skipped when unconfigured.
- **Pytest Warnings Audit (Phase 2.3.1):**
  - Total warnings: 257 (0 application warnings).
  - Upstream Starlette: 1 warning (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`).
  - Upstream rasterio: 256 warnings (`PendingDeprecationWarning: Use @ matmul instead of * mul operator for matrix multiplication` inside `rasterio/features.py`, `windows.py`, `transform.py`).

---

## 4. Current Baseline Scientific Findings (Gomti Reach, Lucknow)

- **Study Bounding Box:** `[80.88, 26.80, 81.00, 26.90]` (EPSG:4326) / UTM Zone 44N (EPSG:32644)
- **Observation T1 (2023-10-10):** $184.56\text{ ha}$ ($1,845,600\text{ m}^2$, $18,456\text{ pixels}$, $0.0\%\text{ cloud}$)
- **Observation T2 (2023-12-09):** $139.33\text{ ha}$ ($1,393,300\text{ m}^2$, $13,933\text{ pixels}$, $0.0\%\text{ cloud}$)
- **Net Area Delta:** $-45.23\text{ ha}$ ($-24.51\%$ post-monsoon recession)
- **Perennial Core Channel:** $125.18\text{ ha}$ ($1,251,800\text{ m}^2$, $67.83\%$ retention)
- **Seasonal Channel Recession:** $59.38\text{ ha}$ | **Inundation Expansion:** $14.15\text{ ha}$
- **Total Valid Comparison Area:** $13,230.37\text{ ha}$ ($1,323,037\text{ common pixels}$)
- **Data Provenance:** Authenticated Sentinel-2 MSI Level-2A via AWS Open Data Archive (`PUBLIC_OPEN_SENTINEL2_COGS`).

---

## 5. Known Technical Debt & Operational Constraints

1. **Windows System PROJ Conflicts:** External PostGIS installations on Windows set global `PROJ_LIB` variables that conflict with `rasterio`. **Workaround:** `src/config.py` overrides `PROJ_DATA` and `PROJ_LIB` dynamically at startup.
2. **BackgroundTasks Restart Durability:** Pipeline tasks dispatched via FastAPI `BackgroundTasks` run in-process and do not survive application restarts. Tasks interrupted by process restarts remain frozen in `QUEUED` or `PROCESSING` state in the database. Worker database sessions are verified independent and closed, but durable background queues (Celery/Redis) are recommended for multi-worker production.
3. **Stale JWT Revocation Elimination (Resolved):** In Phase 2.2D.1, immediate admin revocation was implemented via authoritative database checks on `profiles.role` for all administrative requests. Even if a revoked admin presents an unexpired JWT, they are rejected with HTTP 403 immediately (0 delay). Ordinary user tokens continue to reflect normal permissions.
4. **CDSE Keycloak Session Lifespans:** CDSE bearer tokens expire within 10 to 60 minutes. The downloader handles re-authentication, but unauthenticated public COG retrieval remains the most reliable zero-maintenance route.
5. **Pending Benchmarks:** The proposed $25\text{ km}^2$ memory footprint ceiling ($< 2\text{ GB RAM}$) and API latency target ($< 500\text{ ms}$) represent architecture specifications and must not be reported as verified until formal benchmark scripts are executed in Phase 2.3.
6. **Matplotlib Raster Memory:** Rendering 300 DPI multi-panel figures in `src/visualization.py` allocates ~$300–450\text{ MB}$ of transient memory. Memory is released upon plot close, but worker concurrency should be capped at 2–3 simultaneous runs per container.
7. **RoleSyncJournal Multi-Process Isolation (Phase 2.2D.2 Audit):** `RoleSyncJournal` persists to an append-only JSONL file with `os.fsync()` durability. In multi-process ASGI configurations (e.g. multiple Gunicorn workers), in-memory states are process-isolated and do not observe peer workers' updates in real time until reload. **Recommendation for production:** Migrate the journal to a dedicated PostgreSQL audit table (`role_sync_audit_log`) accessed via an independent non-rolled-back connection.
4. **CDSE Keycloak Session Lifespans:** CDSE bearer tokens expire within 10 to 60 minutes. The downloader handles re-authentication, but unauthenticated public COG retrieval remains the most reliable zero-maintenance route.
5. **Pending Benchmarks:** The proposed $25\text{ km}^2$ memory footprint ceiling ($< 2\text{ GB RAM}$) and API latency target ($< 500\text{ ms}$) represent architecture specifications and must not be reported as verified until formal benchmark scripts are executed in Phase 2.3.
6. **Matplotlib Raster Memory:** Rendering 300 DPI multi-panel figures in `src/visualization.py` allocates ~$300–450\text{ MB}$ of transient memory. Memory is released upon plot close, but worker concurrency should be capped at 2–3 simultaneous runs per container.

---

## 6. Recommended Next Priorities (Phase 2.3)

1. **Empirical Benchmarking Suite:** Implement `benchmarks/benchmark_pipeline.py` to measure peak memory, CPU time, and latency on a standardized $25\text{ km}^2$ AOI.
2. **Durable Task Queue Evaluation:** Evaluate migrating from FastAPI `BackgroundTasks` to a durable task broker (Celery / ARQ / Redis) for distributed multi-worker deployments.
3. **Modern Web Frontend Migration / SPA Client:** Client-side React / Next.js web application consuming the FastAPI REST endpoints.
