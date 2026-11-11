# DharaScope: Current Project Status
## Real-Time Subsystem Health, Test Coverage, Known Debt & Development Priorities

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Current Phase:** Phase 2.3 — Frontend–Backend Integration (Complete)  
**Last Updated:** 2026-11-11  
**Overall System Health:** `HEALTHY / OPERATIONAL`  

---

## 1. Executive Summary

DharaScope has successfully validated the core Phase 1 scientific satellite-processing pipeline (detecting a 24.51% post-monsoon surface water recession along the Gomti River in Lucknow between October and December 2023 using Sentinel-2 MSI Level-2A imagery). Phase 2.1 (SRS, Technical Decision Records, Traceability Matrix, and System Constraints) and Phase 2.2 (Parts A, B1, B2, C, D, D.1, D.2, D.3) are fully verified and approved.

In **Phase 2.3**, the project built and verified the complete Modern React 19 + TypeScript GIS Workstation (`frontend/`), fully integrating with the FastAPI application service layer and PostgreSQL 16 + PostGIS 3.6 database without modifying or inventing any API endpoints:
1. **Supabase Auth & Session Management (`frontend/src/context/`):** Bearer token extraction, session persistence, authoritative profile synchronization via `GET /api/v1/auth/me`, role badge extraction (`admin` vs `user`), and browser Web Crypto HS256 development JWT generator matching the backend development fallback secret for offline testing.
2. **Interactive Cartography & Real-Time PostGIS Validation (`frontend/src/components/MapPicker.tsx`):** Leaflet map integrating CartoDB Dark Matter tiles, Gomti reach preset, and real-time backend validation (`POST /api/v1/aois/validate`) verifying topology, geodetic area ($0.10–100.00\text{ km}^2$), vertex ceilings ($\le 500$), centroid, and bounding box coordinates.
3. **AOI Catalog & Persistence (`frontend/src/components/AOIManager.tsx`):** Saving polygons to PostGIS (`POST /api/v1/aois`), catalog selection (`GET /api/v1/aois`), and deletion with tenant ownership checks.
4. **Satellite Analysis Pipeline Control & Lifecycle Tracking (`frontend/src/components/AnalysisForm.tsx`, `AnalysisStatus.tsx`):** Parameter controls for NDWI threshold ($\tau \in [-0.30, 0.30]$), max scene cloud cover ($\le 10\%$), ISO-8601 temporal search intervals, retrieval tier, and synchronous/asynchronous execution modes. Real-time polling loop (`GET /api/v1/analyses/{id}`) tracking `QUEUED` $\to$ `PROCESSING` $\to$ `SUCCESS` / `FAILED` with execution timers and Sentinel-2 $T_1/T_2$ scene discovery metadata.
5. **Quantitative Metrics & 4-Class Categorical Cartography (`frontend/src/components/MetricsDisplay.tsx`, `ArtifactsViewer.tsx`):** Quantitative KPI cards ($T_1$ area, $T_2$ area, $\Delta$ ha and $\Delta \%$), 4-class categorical dynamics (Persistent Water, Apparent Loss, Apparent Gain, Persistent Non-Water), prominent mandatory hydrological limitation statement, and authenticated map artifact streaming (`AuthenticatedImage`).
6. **Publication Report Downloads (`frontend/src/components/ReportActions.tsx`):** One-click streaming downloads for ReportLab publication PDF reports and structured CSV data manifests.

The automated test suite has expanded to **197 total passing tests** (182 backend pytest tests + 15 frontend Vitest tests, plus 1 skipped live external storage test) with zero regressions (100% pass rate).

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

### 2.3 Pending Subsystems (Scheduled for Phase 2.4 / Production Hardening)
- [ ] **Empirical Performance Benchmarks (`benchmarks/`):** Load testing API latency ($< 500\text{ ms}$), PDF compilation ($< 10\text{ s}$), and worker memory footprint on $25\text{ km}^2$ AOIs ($< 2\text{ GB RAM}$).
- [ ] **Durable Task Queue Migration:** Celery/Redis worker migration for distributed background jobs across server restarts.

### 2.4 Blocked Subsystems
- **None.** All prerequisites for Phase 2.3 are satisfied.

---

## 3. Automated Test Suite Metrics

- **Total Automated Tests:** 197 passing tests (182 backend pytest tests + 15 frontend Vitest tests, 1 skipped live integration test)
- **Pass Rate:** 100% (197 passing tests, zero regressions)
- **Backend Test Modules (16 modules, 182 passed, 1 skipped):**
  1. `tests/test_frontend_integration.py`: 6 passed (complete user journey: health, auth, AOI validate/persist, analysis run, metrics, artifacts, PDF/CSV downloads, tenant isolation).
  2. `tests/test_admin_role_sync.py`: 27 passed (promotion, revocation, invalid roles, Supabase 404 user not found, 500/timeout failure rollbacks, database persistence, quota-only skip IdP, 403 non-admin rejection, 401 unauthenticated, production fail-closed, compensating rollback on commit failure, desynchronized reconciliation, unreachable Supabase error handling, reconciliation idempotency, anti-privilege escalation, lost ACK reconciliation to new_role, commit definitely fails compensation, DB unavailable during verification, Supabase unavailable during reconciliation).
  3. `tests/test_role_journal_durability.py`: 6 passed (missing file/directory auto-creation, 20-thread concurrent writes, process restart disk recovery, corrupted/truncated JSONL line resilience, disk write failure fallback to in-memory state, unreconciled entry lifecycle filtering).
  4. `tests/test_storage.py`: 16 passed, 1 skipped (local and Supabase storage lifecycle, upload failure error handling, decoupled live integration test).
  5. `tests/test_aoi_validation.py`: 15 passed (valid bboxes, GeoJSON dicts, Features, Collections, strings, MultiPolygons, min/max area limits, topology self-intersections, coordinate bounds, vertex ceilings).
  6. `tests/test_api_service_layer.py`: 33 passed (system health, root metadata, OpenAPI accessibility, unauthenticated rejection, invalid/expired JWT rejection, profile retrieval/update, admin user list, admin quota update, AOI geometry validation, out-of-bounds rejection, AOI CRUD, cross-user private AOI isolation, public AOI shared viewing and edit protections, analysis creation with existing/inline AOIs, missing geometry rejection, invalid threshold rejection, synthetic background pipeline execution, authorized report/artifact download, cross-user report download rejection, queued report rejection, 404/422 error sanitization).
  7. `tests/test_auth_jwt.py`: 24 passed (valid user/admin JWTs, untrusted user-metadata rejection, missing role defaults, unknown role handling, Supabase system claim isolation, missing token, invalid signature, expired token, forged issuer, invalid audience, non-UUID subject, 401/403 status responses, profile auto-creation, anti-privilege escalation, production missing secret/issuer fail-closed guards, immediate admin revocation with stale JWT, fail-closed DB errors).
  8. `tests/test_change_detection.py`: 3 passed (change matrix, area metrics, zero-baseline percentage handling, spatial dimension mismatch).
  9. `tests/test_database_migrations.py`: 3 passed (Alembic configuration loading, migration script discovery across all revisions, live PostgreSQL upgrade/downgrade cycle).
  10. `tests/test_database_models.py`: 17 passed (model metadata, profile role/quota constraints, AOI PostGIS insertion, geodetic spatial calculations, AOI area/vertex constraints, analysis run constraints, 1:1 water metrics uniqueness, artifact type/bucket constraints, cascading deletions).
  11. `tests/test_database_security_rls.py`: 6 passed (live PostgreSQL RLS tests verifying private AOI cross-user isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection).
  12. `tests/test_downloader.py`: 11 passed (auth errors, credential detection, Bearer token masking, redirect auth preservation, HTML error rejection, corrupted binary rejection, raster verification, synthetic generation, band retrieval modes).
  13. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full pipeline execution from bands to NDWI to change detection).
  14. `tests/test_reporting.py`: 7 passed (metrics extraction, CSV report generation, PDF report generation, synthetic badges).
  15. `tests/test_stac_client.py`: 3 passed (bbox validation, item metadata extraction, HTTP error backoff).
  16. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero-denominator protection, water classification, shape mismatch error).
- **Frontend Test Suites (5 suites, 15 passed in Vitest):**
  1. `src/__tests__/api.test.ts`: 5 passed (Bearer injection, 400 error, 401 error, blob download).
  2. `src/__tests__/MetricsDisplay.test.tsx`: 3 passed (KPI cards, 4-class transitions, limitation statement).
  3. `src/__tests__/ReportActions.test.tsx`: 3 passed (PDF/CSV download dispatch and notifications).
  4. `src/__tests__/AuthModal.test.tsx`: 2 passed (Dev session options, token mode tab switching).
  5. `src/__tests__/MapPicker.test.tsx`: 2 passed (Gomti preset, Leaflet initialization, backend validation feedback).

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
