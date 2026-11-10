# DharaScope: Current Project Status
## Real-Time Subsystem Health, Test Coverage, Known Debt & Development Priorities

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Current Phase:** Phase 2.2 — Platform Evolution (Complete: Part A, Part B1, Part B2, Part C, Part D, Part D.1, Part D.2 & Part D.3)  
**Last Updated:** 2026-11-10  
**Overall System Health:** `HEALTHY / OPERATIONAL`  

---

## 1. Executive Summary

DharaScope has successfully validated the core Phase 1 scientific satellite-processing pipeline (detecting a 24.51% post-monsoon surface water recession along the Gomti River in Lucknow between October and December 2023 using Sentinel-2 MSI Level-2A imagery). Phase 2.1 (SRS, Technical Decision Records, Traceability Matrix, and System Constraints) is fully approved. 

In **Phase 2.2, Part A**, the project completed two standalone modules:
1. `src/aoi_validation.py`: Enforcing OGC topological validity, coordinate bounds, vertex count limits ($\le 500$), and geodetic ellipsoidal area constraints ($0.10–100.00\text{ km}^2$) via `pyproj.Geod`.
2. `src/reporting.py`: Programmatically generating structured CSV and publication-ready cartographic PDF reports strictly derived from authentic analysis manifests.

In **Phase 2.2, Part B1**, the project implemented the complete PostgreSQL 16 + PostGIS 3.6 database foundation:
1. `src/database/models/`: Declarative models for `profiles`, `aois`, `analysis_runs`, `water_metrics`, and `analysis_artifacts`, enforcing strict database check constraints, spatial GiST indexing, and cascading deletion semantics.
2. `alembic/`: Complete database migration lifecycle using `geoalchemy2.alembic_helpers`, tested with full upgrade and downgrade cycles.
3. Live PostGIS verification: Executed against PostgreSQL 16.15 + PostGIS 3.6.2, verifying geodetic spatial calculations (`ST_Area(geometry::geography)`) align with the Python validation engine.

In **Phase 2.2, Part B2 & Security Hardening**, the project completed full authentication, authorization, database-level security, and role trust boundary hardening:
1. `src/auth.py`: Cryptographic Supabase JWT Bearer token validation (HS256 symmetric and RS256/ES256 asymmetric JWKS), identity and role extraction derived strictly and exclusively from `app_metadata.role`, FastAPI dependencies (`get_current_user`, `require_admin`), and profile auto-provisioning with anti-privilege escalation guards.
2. Untrusted Metadata Rejection: Completely eliminated user-writable `user_metadata` as a source of authorization claims and separated Supabase's standard session claim `role: "authenticated"` from application admin privileges.
3. Production Fail-Closed Guards: Enforced mandatory `SUPABASE_JWT_SECRET` and `SUPABASE_ISSUER` / `SUPABASE_URL` in production, failing closed with HTTP 500 upon missing configuration.
4. Transaction-local PostgreSQL session identity propagation: `SET LOCAL ROLE dharascope_app;` and `set_config('request.jwt.claim.sub', :sub, true)` scoped strictly to the active transaction.
5. PostgreSQL Row-Level Security (RLS): Enabled and forced across all 5 tables with 20 granular policies verifying cross-user isolation, public AOI protections, and child metric/artifact inheritance. Role `dharascope_app` is non-superuser, has `NOBYPASSRLS`, and does not own tables.

In **Phase 2.2, Part C**, the project implemented the complete FastAPI Application Service Layer:
1. Application Gateway & Bootstrap (`src/api/app.py`, `server.py`): Production ASGI entrypoint ensuring runtime PROJ isolation, CORS middleware, OpenAPI interactive documentation (`/docs`, `/redoc`), and standardized sanitized error envelopes (`APIErrorResponse`).
2. Authentication & Administration Endpoints (`src/api/routers/auth.py`): `/api/v1/auth/me` (profile retrieval/update) and `/api/v1/admin/users` (administrative quota controls) backed by `src/auth.py` dependency injection.
3. AOI CRUD & Geometry Validation (`src/api/routers/aois.py`, `src/services/aoi_service.py`): Enforcing $0.1–100\text{ km}^2$ equal-area geodetic bounds, 500-vertex ceilings, PostGIS persistence, and multi-tenant RLS ownership isolation.
4. Asynchronous Satellite Pipeline Dispatch (`src/api/routers/analyses.py`, `src/services/analysis_service.py`): Non-blocking execution via FastAPI `BackgroundTasks`, quota verification, pipeline execution (STAC discovery, scene selection, band streaming, NDWI indexing, change detection, cartography), progress tracking (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`), and regex diagnostic error sanitization.
5. Metrics Inspection & Artifact Delivery (`src/services/artifact_service.py`, `src/api/routers/artifacts.py`): Authorized streaming downloads for publication-grade ReportLab PDF reports, RFC 4180 CSV reports, and visualization maps without exposing filesystem paths.

In **Phase 2.2, Part D & Part D.1**, the project hardened admin role consistency, revocation, and storage verification boundaries:
1. Supabase Auth Admin Synchronization (`src/auth.py`, `src/api/routers/auth.py`): Synchronizes user promotions and revocations directly to Supabase Auth (`PUT /auth/v1/admin/users/{user_id}`) targeting `app_metadata.role`.
2. Distributed Two-Phase Consistency & SAGA Compensating Recovery (`src/services/role_sync_service.py`): Managed via `RoleSyncJournal`. If PostgreSQL commit or flush fails after Supabase update, an automatic compensating update restores the previous role in Supabase Auth (returning HTTP 500). Dual failure logs `DESYNCHRONIZED` alert (HTTP 502). Idempotent retries and `POST /api/v1/admin/users/{user_id}/reconcile` endpoint guarantee eventual consistency.
3. Immediate Admin Revocation (`src/auth.py`): Every administrative endpoint performs an authoritative database lookup on `profiles.role` using the caller's UUID within a restricted RLS-aware session. A revoked administrator is immediately blocked with HTTP 403 Forbidden on their very next request (0 delay), even when holding an unexpired JWT. Database errors fail closed with HTTP 500.
4. Storage Subsystem & Decoupled Verification Boundaries (`src/storage.py`, `tests/test_storage.py`): Local storage for offline/dev environments and Supabase Storage for cloud deployments. Mock-based test suite covers all unit/integration contracts offline; live testing is strictly decoupled into `TestLiveSupabaseStorageIntegration` guarded by `DHARASCOPE_LIVE_SUPABASE_STORAGE=1`.

In **Phase 2.2, Part D.2 & Part D.3**, the project hardened commit-failure recovery, journal durability, and ambiguous commit outcomes:
1. Guarded Commit Boundary & Commit-Failure Recovery (`src/services/role_sync_service.py`): Explicitly placed `session.commit()` inside the guarded `try/except` block of `execute_reliable_role_update()`. If commit definitely fails, compensating rollback restores the original role on Supabase Auth, rolling back PostgreSQL, and returning HTTP 500. Staging other profile fields (`quota_monthly_runs`, `full_name`) prior to execution ensures atomic all-or-nothing profile commits.
2. Ambiguous Commit Outcome Resolution (`src/services/role_sync_service.py`): If `session.commit()` raises an exception after PostgreSQL wrote to disk (lost ACK), system establishes authoritative role via an isolated fresh database session. If PostgreSQL contains `new_role`, system reconciles Supabase Auth to `new_role`, records `RECONCILED`, and returns HTTP 200 without blindly compensating to `old_role`. If database is unavailable, records `DESYNCHRONIZED` (HTTP 502). A synchronization is never marked `COMPENSATED` without proving both systems have `old_role`.
3. RoleSyncJournal Durability Audit (`tests/test_role_journal_durability.py`): Proved 20-thread concurrency safety, disk sync with `os.fsync()`, missing file auto-creation, recovery after process restart, graceful handling of corrupted/truncated JSONL lines, and disk failure fallback to in-memory state. Documented multi-process ASGI limitation and recommended database-backed audit table for horizontally scaled deployments.
4. Reconciliation Anti-Privilege Escalation (`tests/test_admin_role_sync.py`): Proved that reconciliation derives roles strictly from `app_metadata.role`, rejecting client-writable `user_metadata` or generic `role: "authenticated"` claims. Reconciliations are fully idempotent and reject unauthorized callers.

The automated test suite has expanded to **176 passed tests** (plus 1 skipped live integration test), all passing with zero regressions (100% pass rate).

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

### 2.2 In-Progress Subsystems
- **None.** Phase 2.2 is complete across Parts A, B1, B2, C, D, D.1, D.2, and D.3.

### 2.3 Pending Subsystems (Scheduled for Phase 2.3)
- [ ] **Empirical Performance Benchmarks (`benchmarks/`):** Load testing API latency ($< 500\text{ ms}$), PDF compilation ($< 10\text{ s}$), and worker memory footprint on $25\text{ km}^2$ AOIs ($< 2\text{ GB RAM}$).
- [ ] **Modern Web Frontend Migration / SPA Client:** Client-side React / Next.js web application consuming the FastAPI REST endpoints.

### 2.4 Blocked Subsystems
- **None.** All prerequisites for Phase 2.3 are satisfied.

---

## 3. Automated Test Suite Metrics

- **Total Automated Tests:** 176 passed, 1 skipped (177 total test definitions)
- **Pass Rate:** 100% (176 passed, 1 skipped, 173 warnings in 89.16s)
- **Warning Breakdown:** 144 upstream `rasterio` Affine matrix warnings (`PendingDeprecationWarning`), 1 upstream Starlette `httpx` warning (`StarletteDeprecationWarning`), 28 test-scoped Affine transform warnings, 0 DharaScope application code warnings.
- **Test Modules (15 modules):**
  1. `tests/test_admin_role_sync.py`: 27 passed (promotion, revocation, invalid roles, Supabase 404 user not found, 500/timeout failure rollbacks, database persistence, quota-only skip IdP, 403 non-admin rejection, 401 unauthenticated, production fail-closed, compensating rollback on commit failure, desynchronized reconciliation, unreachable Supabase error handling, reconciliation idempotency, anti-privilege escalation, lost ACK reconciliation to new_role, commit definitely fails compensation, DB unavailable during verification, Supabase unavailable during reconciliation).
  2. `tests/test_role_journal_durability.py`: 6 passed (missing file/directory auto-creation, 20-thread concurrent writes, process restart disk recovery, corrupted/truncated JSONL line resilience, disk write failure fallback to in-memory state, unreconciled entry lifecycle filtering).
  3. `tests/test_storage.py`: 16 passed, 1 skipped (local and Supabase storage lifecycle, upload failure error handling, decoupled live integration test).
  4. `tests/test_aoi_validation.py`: 15 passed (valid bboxes, GeoJSON dicts, Features, Collections, strings, MultiPolygons, min/max area limits, topology self-intersections, coordinate bounds, vertex ceilings).
  5. `tests/test_api_service_layer.py`: 33 passed (system health, root metadata, OpenAPI accessibility, unauthenticated rejection, invalid/expired JWT rejection, profile retrieval/update, admin user list, admin quota update, AOI geometry validation, out-of-bounds rejection, AOI CRUD, cross-user private AOI isolation, public AOI shared viewing and edit protections, analysis creation with existing/inline AOIs, missing geometry rejection, invalid threshold rejection, synthetic background pipeline execution, authorized report/artifact download, cross-user report download rejection, queued report rejection, 404/422 error sanitization).
  6. `tests/test_auth_jwt.py`: 24 passed (valid user/admin JWTs, untrusted user-metadata rejection, missing role defaults, unknown role handling, Supabase system claim isolation, missing token, invalid signature, expired token, forged issuer, invalid audience, non-UUID subject, 401/403 status responses, profile auto-creation, anti-privilege escalation, production missing secret/issuer fail-closed guards, immediate admin revocation with stale JWT, fail-closed DB errors).
  7. `tests/test_change_detection.py`: 3 passed (change matrix, area metrics, zero-baseline percentage handling, spatial dimension mismatch).
  8. `tests/test_database_migrations.py`: 3 passed (Alembic configuration loading, migration script discovery across all revisions, live PostgreSQL upgrade/downgrade cycle).
  9. `tests/test_database_models.py`: 17 passed (model metadata, profile role/quota constraints, AOI PostGIS insertion, geodetic spatial calculations, AOI area/vertex constraints, analysis run constraints, 1:1 water metrics uniqueness, artifact type/bucket constraints, cascading deletions).
  10. `tests/test_database_security_rls.py`: 6 passed (live PostgreSQL RLS tests verifying private AOI cross-user isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection).
  11. `tests/test_downloader.py`: 11 passed (auth errors, credential detection, Bearer token masking, redirect auth preservation, HTML error rejection, corrupted binary rejection, raster verification, synthetic generation, band retrieval modes).
  12. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full pipeline execution from bands to NDWI to change detection).
  13. `tests/test_reporting.py`: 7 passed (metrics extraction, CSV report generation, PDF report generation, synthetic badges).
  14. `tests/test_stac_client.py`: 3 passed (bbox validation, item metadata extraction, HTTP error backoff).
  15. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero-denominator protection, water classification, shape mismatch error).
  2. `tests/test_role_journal_durability.py`: 6 passed (missing file/directory auto-creation, 20-thread concurrent writes, process restart disk recovery, corrupted/truncated JSONL line resilience, disk write failure fallback to in-memory state, unreconciled entry lifecycle filtering).
  3. `tests/test_storage.py`: 16 passed, 1 skipped (local and Supabase storage lifecycle, upload failure error handling, decoupled live integration test).
  4. `tests/test_aoi_validation.py`: 15 passed (valid bboxes, GeoJSON dicts, Features, Collections, strings, MultiPolygons, min/max area limits, topology self-intersections, coordinate bounds, vertex ceilings).
  5. `tests/test_api_service_layer.py`: 33 passed (system health, root metadata, OpenAPI accessibility, unauthenticated rejection, invalid/expired JWT rejection, profile retrieval/update, admin user list, admin quota update, AOI geometry validation, out-of-bounds rejection, AOI CRUD, cross-user private AOI isolation, public AOI shared viewing and edit protections, analysis creation with existing/inline AOIs, missing geometry rejection, invalid threshold rejection, synthetic background pipeline execution, authorized report/artifact download, cross-user report download rejection, queued report rejection, 404/422 error sanitization).
  6. `tests/test_auth_jwt.py`: 24 passed (valid user/admin JWTs, untrusted user-metadata rejection, missing role defaults, unknown role handling, Supabase system claim isolation, missing token, invalid signature, expired token, forged issuer, invalid audience, non-UUID subject, 401/403 status responses, profile auto-creation, anti-privilege escalation, production missing secret/issuer fail-closed guards, immediate admin revocation with stale JWT, fail-closed DB errors).
  7. `tests/test_change_detection.py`: 3 passed (change matrix, area metrics, zero-baseline percentage handling, spatial dimension mismatch).
  8. `tests/test_database_migrations.py`: 3 passed (Alembic configuration loading, migration script discovery across all revisions, live PostgreSQL upgrade/downgrade cycle).
  9. `tests/test_database_models.py`: 17 passed (model metadata, profile role/quota constraints, AOI PostGIS insertion, geodetic spatial calculations, AOI area/vertex constraints, analysis run constraints, 1:1 water metrics uniqueness, artifact type/bucket constraints, cascading deletions).
  10. `tests/test_database_security_rls.py`: 6 passed (live PostgreSQL RLS tests verifying private AOI cross-user isolation, public AOI modification protection, analysis run cross-user isolation, child metric/artifact inheritance, and database-level RLS role escalation rejection).
  11. `tests/test_downloader.py`: 11 passed (auth errors, credential detection, Bearer token masking, redirect auth preservation, HTML error rejection, corrupted binary rejection, raster verification, synthetic generation, band retrieval modes).
  12. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full pipeline execution from bands to NDWI to change detection).
  13. `tests/test_reporting.py`: 7 passed (metrics extraction, CSV report generation, PDF report generation, synthetic badges).
  14. `tests/test_stac_client.py`: 3 passed (bbox validation, item metadata extraction, HTTP error backoff).
  15. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero-denominator protection, water classification, shape mismatch error).

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
