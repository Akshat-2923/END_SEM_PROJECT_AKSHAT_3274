# Changelog
All notable changes to the DharaScope platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-12
### Stabilized & Released
- **Phase 2.5: Final Product Stabilization & Demonstration Preparation:**
  - **Academic Release Baseline:** Officially closed and verified the DharaScope platform for final capstone demonstration and academic evaluation.
  - **Scientific Documentation Correction:**
    - Corrected unsupported causal claims in `src/reporting.py` and `app.py`, replacing hardcoded assertions about Gaughat Barrage operations with an objective, scientifically disciplined explanation attributing observed water expansion to post-monsoon baseflow stabilization and potential local factors (drainage, channel maintenance, or hydraulic adjustments).
    - Formulated barrage impoundment as an unverified local hypothesis alongside other municipal and morphological factors, explicitly noting that causal claims require in-situ river gauge hydrographs and operational gate logs.
    - Documented Phase 1's $132.30\text{ km}^2$ bounding box as a historical feasibility experiment that intentionally exceeded the current operational $100\text{ km}^2$ system limit.
  - **Frontend Quality, Usability & Cleanliness:**
    - Extracted `LUCKNOW_GOMTI_PRESET` from `frontend/src/components/MapPicker.tsx` to `frontend/src/constants/aoi.ts`, eliminating React Fast Refresh warnings.
    - Refactored `frontend/src/components/ArtifactsViewer.tsx` to derive `activeArtifact` during render, eliminating `react(set-state-in-effect)` linter warnings.
    - Added responsive CSS media queries for `<1024px`, `<768px`, and `<480px` in `frontend/src/index.css` for tablet and mobile viewing.
    - Updated `frontend/src/components/Header.tsx` version badge to `v2.5`.
    - Removed unused test imports in `frontend/src/__tests__/AuthModal.test.tsx`.
    - Confirmed 0 errors across 24 scanned TypeScript/TSX files in oxlint.
  - **Live Demonstration Verification:**
    - Executed automated browser validation via Playwright against live FastAPI (:8000) and Vite (:5173).
    - Confirmed 100% pass across all 8 stages with genuine Sentinel-2 Level-2A data (`2023-10-10` vs `2023-12-09`).
    - Verified metrics: $0.53\text{ ha} \to 1.66\text{ ha}$ ($+1.13\text{ ha}$, $+213.21\%$), real orbital badge (`REAL ORBITAL S2`), and verified download of 7.4 MB PDF report and CSV data manifest.
  - **Academic Documentation Suite:**
    - `README.md`: Comprehensively rewritten platform guide covering architecture, multi-scale findings, quickstart setup, testing, and documentation sitemap.
    - `docs/ARCHITECTURE.md`: Complete architectural specification with 3 Mermaid diagrams.
    - `docs/DEMO_GUIDE.md`: Step-by-step evaluator script and expected outputs.
    - `docs/SCIENTIFIC_METHODOLOGY.md`: Detailed remote sensing and optical index methodology.
    - `docs/PROJECT_REPORT.md`: Full academic capstone engineering report.

---

## [0.9.1] - 2026-11-12
### Audited
- **Phase 2.4.1: Scientific Results Audit & GitHub Synchronization:**
  - **Scientific Scale Consistency Audit:** Resolved the apparent discrepancy between Phase 1 reported water extents (184.56 ha / 139.33 ha, -24.51%) and Phase 2.4 verified results (0.53 ha / 1.66 ha, +213.21%).
  - **Identical Observation Data:** Verified that both analyses used the exact same Sentinel-2 Level-2A acquisitions (`S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510` on 2023-10-10 and `S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512` on 2023-12-09), identical Band 3 (Green 10m) and Band 8 (NIR 10m) rasters, identical McFeeters (1996) NDWI formulation, identical threshold ($\tau = 0.00$), and identical projected coordinate system (`EPSG:32644`).
  - **Spatial Scale Resolution:** Proved that the variation is 100% attributable to the difference in spatial bounding box extents:
    - Phase 1 Regional Corridor (`[80.88, 26.80, 81.00, 26.90]`): 13,230.37 ha (132.30 km², 1,323,037 pixels) capturing broad floodplain and natural wetland seasonal recession (-45.23 ha). Note that this regional envelope exceeds the single-run system ceiling of 100 km² established in Phase 2.2.
    - Phase 2.4 Urban Reach (`[80.90, 26.84, 80.92, 26.86]`): 439.79 ha (4.40 km², 43,979 pixels) covering only 3.32% of the regional area directly along the channelized Gomti Riverfront, where post-monsoon barrage impoundment (Gaughat and Gomti Barrages) elevates urban winter river stages (+1.13 ha).
  - **Cloud Cover Metadata Clarification:** Confirmed that reported 0.0% cloud cover reflects ESA Sen2Cor scene-level tile metadata (`eo:cloud_cover` for MGRS tile `T44RMQ`), rather than an AOI-specific cloud mask.
  - **Reproducibility & Evidence Audit:** Verified all 8 Playwright browser screenshots (`outputs/validation_phase2_4/01_*.png` through `08_*.png`), execution summary JSON, matching CSV data manifest (`dharascope_analysis_c7463b8c.csv`), and 7.4 MB PDF report. Confirmed zero synthetic data intrusion into real orbital workflows.
  - **GitHub Synchronization:** Synchronized local Git repository (`main` branch) with GitHub remote (`origin/main`).

---

## [0.9.0] - 2026-11-11
### Validated
- **Phase 2.4: Real Satellite End-to-End Validation:**
  - Validated full real-world pipeline using genuine Sentinel-2 Level-2A multi-spectral observations over the Gomti River reach in Lucknow (`[80.90, 26.84, 80.92, 26.86]` WGS84).
  - Retrieved 10m Ground Sampling Distance (GSD) surface reflectance rasters from the AWS Open Data Sentinel-2 COG archive (`PUBLIC_OPEN_SENTINEL2_COGS`):
    - Band 3 (Green 10m): `data/raw/S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510_B03_10m.tif` (1.98 MB)
    - Band 8 (NIR 10m): `data/raw/S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510_B08_10m.tif` (2.16 MB)
    - Band 3 (Green 10m): `data/raw/S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512_B03_10m.tif` (1.99 MB)
    - Band 8 (NIR 10m): `data/raw/S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512_B08_10m.tif` (2.18 MB)
  - Computed real surface water change dynamics across 43,979 common valid pixels (439.79 ha):
    - Earlier Water Area ($T_1$, 2023-10-10): 0.53 ha (53 pixels)
    - Later Water Area ($T_2$, 2023-12-09): 1.66 ha (166 pixels)
    - Perennial Channel Core (Persistent): 0.39 ha (39 pixels)
    - Seasonal Recession (Apparent Loss): 0.14 ha (14 pixels)
    - Inundation Expansion (Apparent Gain): 1.27 ha (127 pixels)
    - Net Surface Water Delta: +1.13 ha (+213.21%)
  - Executed automated browser validation suite via Playwright Chromium (`scripts/validate_real_satellite_browser.mjs`) against live FastAPI (port 8000) and React (port 5173):
    - Verified all 8 workflow stages: Landing, Supabase/Hydrologist Authentication, PostGIS Geometry Validation, Pipeline Parameter Configuration, Analysis Execution & Real Badge verification (`REAL ORBITAL S2`), Scientific Metrics & Transition Tables, Cartographic Artifact Streaming, and Report Downloads.
    - Verified real downloaded CSV data manifest (`# Real Satellite Data,TRUE`) and 7.4 MB publication ReportLab PDF.

### Fixed
- **CORS Configuration Hardening (`src/api/app.py`):**
  - Replaced wildcard `allow_origins=["*"]` with explicit local hosts (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:8000`, `http://127.0.0.1:8000`, `http://localhost:3000`, `http://127.0.0.1:3000`), resolving W3C browser CORS rejections for credentialed requests.
- **Sentinel-2 Discovery Metadata Extraction (`src/services/analysis_service.py`):**
  - Standardized parsing of flat item dictionaries returned by `SceneSelector` (`item["datetime"]`, `item["cloud_cover"]`) alongside raw STAC items, ensuring `t1_date`, `t2_date`, `t1_cloud_cover`, and `t2_cloud_cover` are properly formatted ISO timestamps and floats in database runs and manifest stages.
- **Report Manifest Stage Alignment (`src/reporting.py`):**
  - Extended `extract_report_metrics()` to inspect `catalogue_discovery`, `water_classification`, and `scene_selection` stages, guaranteeing that CSV and PDF reports render actual Sentinel-2 acquisition dates (`2023-10-10`, `2023-12-09`) and scene IDs.

---

## [0.8.1] - 2026-11-11
### Security
- **Frontend JWT Secret Isolation & Tree-Shaking:**
  - Guarded client-side `DEV_JWT_SECRET` in `frontend/src/services/supabase.ts` with `import.meta.env.DEV`, ensuring the development fallback key is excluded from production bundles.
  - Hardened `createDevSignedJwt()` to throw if executed in `import.meta.env.PROD` or when `DEV_JWT_SECRET` is empty.
  - Guarded `signInDevAccount()` in `frontend/src/context/AuthContext.tsx` to prevent accidental dev account activation in production.
  - Hid "Developer Presets" tab in `frontend/src/components/AuthModal.tsx` when `!import.meta.env.DEV`.
  - Added regression test `test_production_rejects_development_fallback_secret_tokens` in `tests/test_auth_jwt.py` proving backend in production mode rejects tokens signed with the development fallback secret with HTTP 401 Unauthorized.
  - Added unit tests in `frontend/src/__tests__/jwt_security.test.ts` verifying DEV signing allowance and PROD rejection.

### Added
- **Synthetic Benchmark Provenance Labelling:**
  - Added prominent amber warning banner to `frontend/src/components/MetricsDisplay.tsx` explaining synthetic benchmark provenance when `isRealData={false}`.
  - Added `SYNTHETIC BENCHMARK` status badge in `frontend/src/components/AnalysisStatus.tsx`.
  - Added cartographic provenance banner overlay in `frontend/src/components/ArtifactsViewer.tsx` for synthetic map figures.
  - Added backend regression test in `tests/test_frontend_integration.py` ensuring synthetic runs persist `is_real_data: false`, `data_provider: "SYNTHETIC_BENCHMARK_SAMPLE"`, and explicit CSV provenance headers.
- **Session Expiry & Unauthorized Handling:**
  - Added backend test in `tests/test_frontend_integration.py` proving expired tokens (`exp_delta < 0`) and malformed Authorization headers return HTTP 401 Unauthorized for client-side session cleanup.
- **Pytest Warnings Audit:**
  - Audited all 257 test warnings: confirmed 0 application-originated warnings (1 upstream Starlette deprecation, 256 upstream rasterio matrix multiplication deprecations).

---

## [0.8.0] - 2026-11-11
### Added
- **Phase 2.3: Frontend–Backend Integration:**
  - Modern React 19 + TypeScript + Vite GIS Workstation (`frontend/`).
  - Decoupled, responsive GIS interface styled with Charcoal canvas (`#0e1115`), Forest Green accent (`#2d6a4f`), Muted Slate (`#1c2128`) cards, and monospace telemetry typography.
  - Interactive Leaflet cartographic map integrating CartoDB Dark Matter tiles and EPSG:4326 WGS84 coordinates.
  - Pre-configured baseline study reach for the Gomti River in Lucknow, Uttar Pradesh, India.
  - Real-time PostGIS geometry validation calling `POST /api/v1/aois/validate`: validates topology, computes ellipsoidal area (enforcing $0.10 \le \text{area} \le 100.00\text{ km}^2$), vertex limits ($\le 500$), centroid, and bounding box coordinates.
  - Persistent AOI catalog management (`POST /api/v1/aois`, `GET /api/v1/aois`, `DELETE /api/v1/aois/{id}`).
  - Supabase Auth integration supporting password sign-in/up, session recovery, and Web Crypto client-side HS256 JWT generation for offline developer testing.
  - Bearer JWT injection into all outbound REST API requests with standardized error parsing (`APIErrorResponse`).
  - Sentinel-2 multi-temporal analysis parameters: NDWI cutoff threshold ($\tau \in [-0.30, 0.30]$), max scene cloud cover filter ($\le 10\%$), ISO-8601 interval, retrieval tier (`auto`, `cdse`, `public`, `synthetic`), and sync/async mode.
  - Real-time analysis status polling (`GET /api/v1/analyses/{id}`) through `QUEUED` $\to$ `PROCESSING` $\to$ `SUCCESS` / `FAILED` with execution timers and Sentinel-2 scene discovery metadata.
  - Quantitative Surface Water Area KPIs: $T_1$ baseline area, $T_2$ later area, net surface delta ($\Delta$ ha and $\Delta \%$).
  - 4-Class Categorical Water Dynamics Transitions: Persistent Water (Perennial), Apparent Water Loss (Recession), Apparent Water Gain (Inundation), and Persistent Non-Water.
  - Prominent scientific limitation statement prominently displayed from verified database metadata.
  - Authenticated map artifact streaming (`AuthenticatedImage`) for dual-panel comparison, categorical change map, and single-observation NDWI maps.
  - One-click authenticated report downloads: publication-ready ReportLab PDF (`/reports/pdf`) and structured CSV manifest (`/reports/csv`).
  - Analysis runs archive drawer with historical run selection and cleanup.
- **Frontend & Integration Test Suites:**
  - Added 15 unit and component tests in `frontend/src/__tests__/` (Vitest) verifying API client, MetricsDisplay, ReportActions, AuthModal, and MapPicker.
  - Added 6 end-to-end integration tests in `tests/test_frontend_integration.py` (pytest) validating complete user journeys from health discovery to report downloads and cross-user isolation.

---

## [0.7.5] - 2026-11-10
### Added
- **Ambiguous PostgreSQL Commit Resolution (`src/services/role_sync_service.py`):**
  - Resolved distributed-transaction edge case where `session.commit()` raises an exception after PostgreSQL successfully writes to WAL (lost acknowledgement).
  - Implemented authoritative state recovery: rolls back the failed session and queries `profiles.role` using an isolated fresh database session (`get_session_factory(session.get_bind())`).
  - Added smart branch resolution:
    - *Commit Succeeded (Ack Lost):* If fresh session confirms `new_role`, system reconciles Supabase Auth to `new_role`, marks `RECONCILED` in the journal, and returns HTTP 200 with the updated profile. Never blindly compensates to `old_role`!
    - *Commit Definitely Failed:* If fresh session confirms `old_role`, system compensates Supabase Auth to `old_role`, marks `COMPENSATED`, and returns HTTP 500.
    - *Database Unavailable:* If database cannot be queried during verification, system marks `DESYNCHRONIZED`, refrains from mutating Supabase Auth, and returns HTTP 502.
  - Enforced anti-split-brain invariant: A synchronization is NEVER marked `COMPENSATED` without proving both PostgreSQL and Supabase Auth contain `old_role`.
  - Hardened `reconcile_user_role()` to transition any prior unreconciled records for the user (`DESYNCHRONIZED`, `COMPENSATING`, `FAILED`, `PENDING`, `IDP_UPDATED`) to `RECONCILED`.
- **Ambiguous Commit Regression Test Suite (`tests/test_admin_role_sync.py`):**
  - Added `test_ambiguous_commit_outcome_commit_succeeded_reconciles_supabase`: Verifies lost ACK detection, Supabase reconciliation to `new_role`, `RECONCILED` journal state, and HTTP 200 response.
  - Added `test_ambiguous_commit_outcome_commit_definitely_fails_compensates_supabase`: Verifies definitive commit failure detection, Supabase compensation to `old_role`, `COMPENSATED` journal state, and HTTP 500 response.
  - Added `test_ambiguous_commit_outcome_database_unavailable_during_verification`: Verifies unavailable DB during verification records `DESYNCHRONIZED` and returns HTTP 502 without blind compensation.
  - Added `test_ambiguous_commit_outcome_supabase_unavailable_during_reconciliation`: Verifies unavailable Supabase during reconciliation records `DESYNCHRONIZED` and returns HTTP 502.

---

## [0.7.4] - 2026-11-10
### Added
- **Explicit Commit Boundary & Commit-Failure Recovery (`src/services/role_sync_service.py`):**
  - Moved `session.commit()` inside the guarded `try/except` execution block of `execute_reliable_role_update()`.
  - Guarantees that if a PostgreSQL commit fails after Supabase Auth was updated, a compensating update (`sync_user_role_to_supabase(old_role)`) is immediately executed, session is rolled back, the journal marks `COMPENSATED`, and HTTP 500 is raised.
  - Updated `admin_update_user` in `src/api/routers/auth.py` to stage other profile fields (`quota_monthly_runs`, `full_name`) before executing the reliable role update, committing the entire profile update atomically.
  - Added regression test `test_cross_system_sync_postgres_commit_failure_compensating_rollback_succeeds` in `tests/test_admin_role_sync.py` simulating flush success followed by commit failure.
- **Reconciliation & Anti-Privilege Escalation Test Suite (`tests/test_admin_role_sync.py`):**
  - Added tests for desynchronized state reconciliation, unreachable Supabase failure handling (HTTP 502), idempotency of repeated reconciliations, and unauthorized request rejections (HTTP 401, HTTP 403).
  - Added `test_reconciliation_never_elevates_from_user_metadata` verifying that client-supplied `user_metadata` and generic `role: "authenticated"` can never elevate application roles during reconciliation.
- **RoleSyncJournal Durability & Concurrency Suite (`tests/test_role_journal_durability.py`):**
  - Added 6 comprehensive durability audit tests: missing file/directory creation, 20-thread concurrent write safety, process restart state recovery from disk, corrupted/truncated JSONL line resilience, disk write failure fallback to in-memory state, and unreconciled entry lifecycle filtering.
- **Journal Disk Flushing & Durability Hardening (`src/services/role_sync_service.py`):**
  - Added explicit `f.flush()` and `os.fsync(f.fileno())` inside safe OS exception handling in `_persist_entry_unlocked()` to ensure write durability across OS crashes.
  - Documented multi-process ASGI limitation (in-memory state process-isolated across Gunicorn workers) and recommended database-backed journal (`role_sync_audit_log`) for horizontally scaled production environments.

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
