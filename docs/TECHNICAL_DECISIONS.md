# Architectural & Technical Decision Records (ADR)
## DharaScope: Satellite-Based River Surface Water Dynamics Platform

**Document Version:** 2.2.0  
**Status:** Approved Architectural Baseline  
**Scope:** Phase 2 Platform Evolution  

---

## Index of Technical Decisions

- [ADR-001: Retention of Sentinel-2 MSI Level-2A as Primary Optical Constellation](#adr-001-retention-of-sentinel-2-msi-level-2a-as-primary-optical-constellation)
- [ADR-002: Multi-Tier Satellite Data Retrieval & Fallback Architecture](#adr-002-multi-tier-satellite-data-retrieval--fallback-architecture)
- [ADR-003: Windowed HTTP Range Request Subsetting (/vsicurl/) vs Full Tile Ingestion](#adr-003-windowed-http-range-request-subsetting-vsicurl-vs-full-tile-ingestion)
- [ADR-004: Geographical AOI Validation Envelope (0.10–100.00 km²)](#adr-004-geographical-aoi-validation-envelope-01010000-km)
- [ADR-005: Decoupled Authentication via Supabase Auth + FastAPI JWT Validation](#adr-005-decoupled-authentication-via-supabase-auth--fastapi-jwt-validation)
- [ADR-006: Relational PostGIS Schema for Spatiotemporal Metadata Storage](#adr-006-relational-postgis-schema-for-spatiotemporal-metadata-storage)
- [ADR-007: Object Storage Partitioning and 90-Day Output Retention Policy](#adr-007-object-storage-partitioning-and-90-day-output-retention-policy)
- [ADR-008: Publication-Grade PDF & CSV Reporting Grounded in Immutable Run Manifests](#adr-008-publication-grade-pdf--csv-reporting-grounded-in-immutable-run-manifests)
- [ADR-009: FastAPI Application Service Layer and Asynchronous Pipeline Dispatch](#adr-009-fastapi-application-service-layer-and-asynchronous-pipeline-dispatch)
- [ADR-010: Supabase Auth Admin Role Synchronization and Cloud Storage Abstraction](#adr-010-supabase-auth-admin-role-synchronization-and-cloud-storage-abstraction)
- [ADR-011: Distributed Role Consistency, Compensating Updates, and Immediate Admin Revocation](#adr-011-distributed-role-consistency-compensating-updates-and-immediate-admin-revocation)
- [ADR-012: PostgreSQL Commit Recovery Lifecycle and Role Journal Durability Audit](#adr-012-postgresql-commit-recovery-lifecycle-and-role-journal-durability-audit)

---

### ADR-001: Retention of Sentinel-2 MSI Level-2A as Primary Optical Constellation

#### Status
**ACCEPTED & LOCKED** (Phase 1 Baseline Preserved)

#### Context
DharaScope aims to monitor river surface water extent fluctuations across dynamic inland corridors (such as the Gomti River in Lucknow, UP). We evaluated alternative earth observation constellations:
1. **Landsat 8/9 OLI:** Provides 30m spatial resolution and an 8-day combined revisit. A 30m pixel ($900\text{ m}^2$) is too coarse for Indian river corridors where dry-season channel widths can narrow to 50–120m, causing severe mixed-pixel edge contamination.
2. **PlanetScope / Commercial Imagery:** Offers high resolution ($3\text{ m}$), but requires costly commercial subscriptions incompatible with an open, reproducible academic project.
3. **Sentinel-1 C-Band Synthetic Aperture Radar (SAR):** Radar penetrates cloud cover, but suffers from specular backscatter confusion along urban shorelines, sandbars, and steep embankments (Gomti Riverfront concrete walls), requiring complex terrain speckle filtering.
4. **Sentinel-2 MSI Level-2A:** Provides 10m native ground sampling distance for Band 3 (Green) and Band 8 (NIR), a combined 5-day revisit cycle (Sentinel-2A + Sentinel-2B), open-access licensing, and pre-computed Bottom-Of-Atmosphere (BOA) surface reflectance.

#### Decision
DharaScope shall strictly retain **Copernicus Sentinel-2 Level-2A (MSI)** as its primary satellite data source. No constellation migration shall be conducted.

#### Consequences
- **Positive:** Optimal 10m spatial resolution ($100\text{ m}^2/\text{pixel}$), enabling accurate mapping of river meanders, point bars, and sandbars; zero data licensing costs; standardized atmospheric correction.
- **Negative:** Susceptible to optical cloud obscuration during the core monsoon season (July–August), necessitating cloud-cover filtering ($\le 10\%$) and post-monsoon evaluation windows (October–May).

---

### ADR-002: Multi-Tier Satellite Data Retrieval & Fallback Architecture

#### Status
**ACCEPTED & IMPLEMENTED** (Verified in Phase 1)

#### Context
External satellite API endpoints frequently experience transient outages, Keycloak session timeouts, quota throttling, or credential configuration barriers for non-registered evaluators. An academic platform demo must be resilient against external gateway downtime without fabricating data.

#### Decision
Implement a three-tier retrieval hierarchy in `src/downloader.py`:
1. **Tier 1 (Official Authenticated Gateway):** CDSE OData API using Keycloak OAuth2 bearer tokens (`LocationTrustedSession`). Downloads official 10m single-band JP2 rasters when user credentials (`CDSE_USERNAME`, `CDSE_PASSWORD`) are configured.
2. **Tier 2 (Public Open-Access Archive):** AWS Registry of Open Data / Earth Search STAC hosting Sentinel-2 Level-2A Cloud-Optimized GeoTIFFs (COGs). Streams authentic ESA Sentinel-2 rasters without requiring user login credentials.
3. **Tier 3 (Offline Benchmark Fallback):** Georeferenced synthetic sample generator that mathematically simulates Gomti River geometry and realistic surface reflectance values for offline presentations.

#### Architectural Safeguards
- The system shall never present Tier 3 synthetic sample data as genuine satellite observations.
- Synthetic outputs must embed immutable tags: `PROVENANCE=SYNTHETIC_BENCHMARK_SAMPLE`.
- When Tier 2 is active, report metadata records: `PROVIDER=PUBLIC_OPEN_SENTINEL2_COGS`.

---

### ADR-003: Windowed HTTP Range Request Subsetting (/vsicurl/) vs Full Tile Ingestion

#### Status
**ACCEPTED & IMPLEMENTED** (Verified in Phase 1)

#### Context
A standard Sentinel-2 Level-2A MGRS tile (e.g. `T44RMQ`) covers $100\text{ km} \times 100\text{ km}$ ($10,000\text{ km}^2$) and weighs between 500 MB and 1.1 GB compressed. Downloading entire tiles for an Area of Interest of only $10–100\text{ km}^2$ wastes bandwidth, saturates server disk I/O, and causes multi-minute download latencies.

#### Decision
Leverage Cloud-Optimized GeoTIFF (COG) internal tiling and GDAL/rasterio virtual file systems (`/vsicurl/`) via HTTP `Range` headers.
- The pipeline reprojects the user's bounding box into the native projected CRS of the tile (`EPSG:32644`).
- It requests only the byte ranges corresponding to the bounding spatial tiles for Band 3 and Band 8.
- Rasters are clipped on-the-fly and saved as lightweight local GeoTIFFs (~2 to 8 MB per band instead of 500 MB+).

#### Consequences
- Latency for raster ingestion dropped from ~180 seconds (full tile download and unpack) to ~8–15 seconds.
- Storage requirement reduced by $>98\%$ per analysis run.

---

### ADR-004: Geographical AOI Validation Envelope (0.10–100.00 km²)

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Unbounded AOI submission allows users to submit arbitrarily large polygons (e.g., entire river basins of $50,000\text{ km}^2$), which would exhaust worker RAM during array allocation ($50,000\text{ km}^2 \times 10\text{m GSD} = 5 \times 10^8\text{ pixels} \approx 2\text{ GB}$ per float32 band array), or micro-polygons ($< 1,000\text{ m}^2$) where sub-pixel effects render 10m NDWI statistically meaningless.

#### Decision
Establish a strict geographical validation envelope in `src/aoi_validation.py`:
1. **Area Bounds:** Minimum area $0.10\text{ km}^2$ ($100,000\text{ m}^2$, or 1,000 pixels at 10m); Maximum area $100.00\text{ km}^2$ ($100,000,000\text{ m}^2$, or $1,000,000$ pixels at 10m).
2. **Area Calculation:** Geometry is reprojected from WGS84 to an appropriate equal-area projection or local UTM projection prior to area calculation.
3. **Vertex Limitation:** Maximum 500 vertices per polygon to prevent denial-of-service via boundary parsing complexity.
4. **Topological Rules:** Polygon must be topologically valid (`shapely.is_valid == True`), closed, non-self-intersecting, and within global lat/lon boundaries.

#### Engineering Caveat
*These bounds are architectural design criteria designed for single-node worker memory ceilings (< 2 GB RAM). They have not yet been stress-tested across edge conditions and must NOT be claimed as empirical benchmarks.*

---

### ADR-005: Decoupled Authentication via Supabase Auth + FastAPI JWT Validation

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2B2)**

#### Context
Phase 1 operated as a local single-user script and Streamlit dashboard. Phase 2 requires multi-user capabilities, role isolation (User vs Admin), and secure API endpoints, while avoiding custom authentication implementations (which introduce severe security vulnerabilities).

#### Decision
Delegate identity management to **Supabase Auth** and validate sessions statelessly via **FastAPI**:
1. **Client Signup & Login:** Frontend communicates directly with Supabase Auth (OAuth / Email+Password) over TLS 1.3.
2. **Token Issuance:** Supabase Auth issues cryptographically signed JWT tokens containing user claims (`sub`, `email`, `role`, `exp`).
3. **API Validation:** The FastAPI backend intercepts all incoming HTTP requests via a dependency `get_current_user`:
   - Extracts `Authorization: Bearer <token>`.
   - Validates signature against Supabase JWKS public keys (`RS256`/`ES256`) or symmetric HMAC (`HS256`).
   - Rejects expired, altered, unverified tokens, wrong audience/issuer with HTTP 401 Unauthorized.
4. **Data Ownership & RLS Context:** FastAPI propagates verified identity into the database transaction:
   ```sql
   SET LOCAL ROLE dharascope_app;
   SELECT set_config('request.jwt.claim.sub', :user_id, true);
   SELECT set_config('request.jwt.claim.role', :role, true);
   ```
   Setting `is_local = true` ensures parameters are strictly transaction-scoped, preventing connection pool pollution. PostgreSQL RLS policies evaluate `auth.uid()` and `auth.role()` on all 5 entity tables.
5. **Trusted Role Extraction & Metadata Boundary:**
   In Supabase Auth, `user_metadata` is writable by unauthenticated and authenticated clients during signup and profile updates (`auth.updateUser()`). Therefore, `user_metadata` must **never** be used to determine authorization privileges. Application roles (`admin` vs `user`) are extracted strictly from server-managed `app_metadata.role` (which can only be altered by database triggers or service-role administrative endpoints). Supabase's default top-level `role: "authenticated"` is a system audience identifier and is never mapped to administrative authority. Any token missing an explicit `app_metadata.role = "admin"` defaults to `user`.
6. **Production Configuration Fail-Closed Guards:**
   When `ENVIRONMENT=production`, FastAPI halts startup / token verification with HTTP 500 if either `SUPABASE_JWT_SECRET` (or `JWT_SECRET`) or `SUPABASE_ISSUER` / `SUPABASE_URL` is omitted, eliminating reliance on development defaults or unverified issuers in production.

---

### ADR-006: Relational PostGIS Schema for Spatiotemporal Metadata Storage

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2B1 & 2.2B2)**

#### Context
Phase 1 stored scene metadata and feasibility reports in flat JSON files (`outputs/phase1_feasibility_report.json`). In a multi-user platform, flat files suffer from concurrent write corruption, lack relational indexing, and cannot efficiently perform spatial intersection queries.

#### Decision
Deploy a PostgreSQL database with **PostGIS** extension enabled:
1. `public.profiles`: Extends Supabase `auth.users` with user roles (`user`, `admin`) and analysis quotas.
2. `public.aois`: Stores user-digitized polygons as `GEOMETRY(Polygon, 4326)` with spatial GiST indexing and computed area.
3. `public.analysis_runs`: Master execution manifest storing $T_1$ and $T_2$ scene IDs, acquisition dates, cloud percentages, NDWI threshold ($\tau$), data provenance provider, and processing status (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`).
4. `public.water_metrics`: Quantitative area statistics ($T_1$ area, $T_2$ area, persistent channel, apparent recession, apparent expansion, net change, % change).
5. `public.storage_assets`: URLs and object keys of exported PNG maps, CSV files, and PDF reports in Supabase Storage.

---

### ADR-007: Object Storage Partitioning and 90-Day Output Retention Policy

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Storing raw clipped GeoTIFF rasters permanently for hundreds of analysis runs would rapidly exhaust cloud storage budgets. However, user audit trails, tabular statistics, and publication-ready PDF reports must remain accessible indefinitely.

#### Decision
Establish a tiered storage architecture in Supabase Storage:
- **Bucket `rasters/` (90-Day Ephemeral Retention):** Stores clipped band GeoTIFFs (`B03_10m.tif`, `B08_10m.tif`) and binary classification rasters (`water_mask.tif`). A scheduled database job purges raster assets older than 90 days.
- **Bucket `maps/` (Permanent Retention):** Stores rendered 300 DPI multi-panel figures and categorical change maps.
- **Bucket `reports/` (Permanent Retention):** Stores generated PDF reports and CSV datasets.
- **Object Partitioning Scheme:** `bucket_name/{user_id}/{analysis_id}/{filename}`.

---

### ADR-008: Publication-Grade PDF & CSV Reporting Grounded in Immutable Run Manifests

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Academic evaluations and geospatial research require formal, reproducible deliverables that can be shared with faculty, governing agencies, or peers. All reported figures must be verifiable against raw analysis manifests.

#### Decision
Implement dedicated export builders in `src/reporting.py`:
1. **CSV Export:** Standard RFC 4180 CSV containing a metadata header block followed by aligned metric rows (pixels, $\text{m}^2$, hectares, percentage change, and spatial resolution).
2. **PDF Export:** A publication-ready multi-page report rendered via Python (ReportLab / WeasyPrint):
   - Header with DharaScope insignia, project title, and unique analysis UUID.
   - Evaluator metadata and temporal parameters.
   - Key quantitative findings and component distribution table.
   - Embedded 300 DPI synoptic 4-panel comparison figure and categorical transition map.
   - Spectral methodology section highlighting McFeeters (1996) formulation and band physics.
   - Prominently framed scientific disclaimer clarifying seasonal hydrological recession vs chemical pollution.
3. **Data Integrity Rule:** The reporting engine reads directly from the database `water_metrics` and `analysis_runs` tables (or `phase1_feasibility_report.json`). No parameter may be hardcoded or fabricated.

---

### ADR-009: FastAPI Application Service Layer and Asynchronous Pipeline Dispatch

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2 Part C)**

#### Context
Prior to Phase 2.2C, the satellite pipeline was invoked directly via command-line scripts (`main.py`) or Streamlit sub-processes (`app.py`). Exposing an enterprise REST API requires non-blocking asynchronous pipeline dispatch, unified dependency injection for database sessions bound to transaction-local RLS claims, and sanitized error responses that never leak filesystem paths or credentials.

#### Decision
Implement a modular FastAPI service layer in `src/api/` and `src/services/` with ASGI entrypoint `server.py`:
1. **Asynchronous Dispatch:** `POST /api/v1/analyses` accepts user requests, registers an `AnalysisRun` entity in state `QUEUED`, and delegates computation to FastAPI `BackgroundTasks`. The API returns HTTP 201 immediately, keeping the event loop unblocked.
2. **Deterministic Synchronous Mode:** For automated integration testing, the endpoint supports `?sync=true` to execute in-process and block until `SUCCESS` or `FAILED`.
3. **Dependency Injection & RLS Binding:** Every user-owned route uses `get_db_session`, which auto-provisions or retrieves user profiles and executes `SET LOCAL ROLE dharascope_app` with session variables `request.jwt.claim.sub` and `request.jwt.claim.role`.
4. **Information Leakage Prevention:** Global exception handlers catch internal errors, log stack traces server-side, and return sanitized envelopes (`{"error": ..., "detail": ..., "status_code": ...}`). File paths and credentials are removed via `sanitize_error_message`.
5. **Artifact Delivery Security:** Artifact listings provide secure relative download URLs (`/api/v1/artifacts/{id}/download`) instead of absolute local file paths, with ownership checks before streaming files.

#### Post-Implementation Audit & Known Limitations (Phase 2.2C Audit)
1. **In-Memory Background Worker Limitations:**
   - FastAPI `BackgroundTasks` operates strictly in-process. If the Uvicorn process restarts, crashes, or is deployed during execution, tasks in `QUEUED` or `PROCESSING` state are dropped from memory and remain frozen as orphaned records in the database.
   - Worker database sessions are independently managed and closed via `get_authenticated_db()`, but job durability across restarts requires an external persistent task queue (e.g. Celery, Redis Queue, or ARQ) for production environments.
2. **Artifact Storage Medium:**
   - Artifacts (rasters, maps, CSVs, PDFs) are currently persisted exclusively to the local filesystem (`outputs/<user_id>/<run_id>/`).
   - The database records logical bucket names (`rasters`, `maps`, `reports`), but physical upload to remote Supabase Storage / S3 buckets remains deferred to Phase 2.3.
3. **Admin Role Synchronization & Stale JWT Propagation:**
   - In Phase 2.2C audit, `PATCH /api/v1/admin/users/{user_id}` only mutated `profiles.role` in PostgreSQL without updating Supabase `app_metadata.role`.
   - Resolved in Phase 2.2D via ADR-010.

---

### ADR-010: Supabase Auth Admin Role Synchronization and Cloud Storage Abstraction

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2 Part D)**

#### Context
1. **IdP vs. Projection Split-Brain:** Following Phase 2.2B2 Security Hardening, application authorization derived strictly from the cryptographically verified JWT claim `app_metadata.role`. Updating `profiles.role` in the database via administrative endpoints failed to propagate to Supabase Auth, preventing users from receiving actual admin privileges on future tokens. Conversely, revoking privileges in the database left unexpired admin JWTs active.
2. **Local vs. Cloud Storage Decoupling:** In Phase 2.2C, generated rasters, maps, CSVs, and PDFs were saved exclusively to the local filesystem (`outputs/<user_id>/<run_id>/`). Stateless container deployments require cloud object storage (Supabase Storage / S3) with authenticated downloads and upload failure safeguards.

#### Decision
1. **Authoritative Admin Role Synchronization:**
   - Integrated Supabase Auth GoTrue Admin API (`PUT /auth/v1/admin/users/{user_id}`) on the backend using `SUPABASE_SERVICE_ROLE_KEY`.
   - When updating roles, `src/auth.py` synchronizes `app_metadata.role` with Supabase Auth first. If the remote identity provider call fails (e.g. 502/network timeout/404), the transaction aborts and PostgreSQL `profiles.role` is never modified.
   - Kept `SUPABASE_SERVICE_ROLE_KEY` strictly in backend environment configuration; it is never exposed in client bundles, API responses, or logs.
   - **Stale JWT Lifespan:** Acknowledged and documented that active access tokens in circulation retain their claims until expiration. The maximum revocation delay is the JWT TTL (default 3600 seconds in Supabase).
2. **Storage Subsystem Abstraction (`src/storage.py`):**
   - Formulated `BaseStorageBackend` with concrete implementations:
     - `LocalStorageBackend`: Default for local development, tests, and offline runs. Stores and serves directly from local disk.
     - `SupabaseStorageBackend`: Uploads artifacts to Supabase Storage buckets (`rasters`, `maps`, `reports`) via REST API using service-role credentials.
   - **Upload Failure Integrity:** During pipeline execution, if an artifact upload fails, the error is caught and logged, and the database record is **not** created. This prevents phantom database rows referencing non-existent storage payloads.
   - **Authorized Delivery:** Downloads continue to enforce parent `AnalysisRun` ownership and RLS checks before serving file bytes.


---

### ADR-011: Distributed Role Consistency, Compensating Updates, and Immediate Admin Revocation

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2 Part D.1)**

#### Context
1. **Cross-System Synchronization Asymmetry:** In Phase 2.2D, `admin_update_user` called Supabase Auth GoTrue Admin API before updating PostgreSQL `profiles.role`. If Supabase succeeded but the PostgreSQL commit subsequently failed (e.g., database constraint failure, connection dropout, disk exhaustion), Supabase Auth remained updated to the new role while PostgreSQL rolled back to the old role, resulting in cross-system state drift.
2. **Stale JWT Revocation Delay:** Because authorization checks relied on cryptographic JWT claims (`app_metadata.role`), a revoked administrator holding an unexpired JWT retained administrative access for the remainder of the token TTL (up to 3600 seconds).
3. **Storage Verification Boundaries:** Automated tests for Supabase Storage relied on mocked HTTP responses, which needed explicit demarcation from live cloud integration requiring live credentials and buckets.

#### Decision
1. **Two-Phase Consistency & Compensating Rollback:**
   - Implemented `RoleSyncJournal` in `src/services/role_sync_service.py` to record audit intents (`PENDING`, `IDP_UPDATED`, `COMMITTED`, `COMPENSATING`, `COMPENSATED`, `FAILED`, `DESYNCHRONIZED`, `RECONCILED`).
   - If PostgreSQL commit or flush fails after Supabase Auth was updated, a compensating update is immediately dispatched to Supabase Auth to restore `old_role`.
   - If compensation succeeds, the journal records `COMPENSATED`, PostgreSQL rolls back, and the client receives HTTP 500. Both systems remain in agreement at `old_role`.
   - If compensation also fails, the journal records `DESYNCHRONIZED`, a critical alert is logged, and the client receives HTTP 502. The systems never silently report success while disagreeing.
   - Idempotency guarantees prevent duplicate or corrupt state changes on retries.
   - Added `POST /api/v1/admin/users/{user_id}/reconcile` and `reconcile_user_role` for durable admin reconciliation.
2. **Immediate Admin Revocation (Authoritative Database Check):**
   - Hardened `verify_admin_privileges` and `require_admin` in `src/auth.py`.
   - For all administrative requests, the backend performs a two-tier check:
     1. Fast-path check: JWT must claim `app_metadata.role == 'admin'`.
     2. Authoritative check: Queries `profiles.role` for the caller's UUID within a restricted RLS-aware database session.
   - A revoked admin presenting an unexpired JWT is immediately rejected with HTTP 403 Forbidden on the subsequent request, achieving immediate revocation (0 delay).
   - Database connection or query errors fail closed with HTTP 500, never granting administrative bypass.
   - Ordinary authenticated user access (`/api/v1/auth/me`, `/api/v1/aois`, `/api/v1/analyses`) remains unaffected.
3. **Decoupled Live Storage Integration:**
   - Dedicated `TestLiveSupabaseStorageIntegration` in `tests/test_storage.py` guarded by `@pytest.mark.skipif(os.getenv("DHARASCOPE_LIVE_SUPABASE_STORAGE") != "1")`.
   - Mock-based unit and integration tests verify contract behavior offline, while live testing is strictly opt-in with verified external credentials.

---

### ADR-012: PostgreSQL Commit Recovery Lifecycle and Role Journal Durability Audit

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2 Part D.2)**

#### Context
1. **Explicit Commit Boundary in Distributed Updates:** In Phase 2.2D.1, the distributed role update sequence in `execute_reliable_role_update` relied on `session.flush()` before Supabase Auth synchronization, deferring `session.commit()` to the outer FastAPI dependency teardown (`get_db()`). If the PostgreSQL commit failed *after* the request handler completed (due to connection loss, deferred constraint violations, or disk exhaustion), the outer session rollback occurred without triggering the compensating update on Supabase Auth.
2. **Durability & Multi-Process Audit of RoleSyncJournal:** The journal implementation was backed by an append-only JSONL file (`outputs/metadata/role_sync_audit.jsonl`) and an in-memory dictionary. A formal audit was required to evaluate thread safety, process isolation in multi-worker ASGI environments (e.g. Gunicorn/Uvicorn workers), behavior on corrupted or missing files, disk write failures, and restart recovery.
3. **Reconciliation Security & Idempotency:** The administrative reconciliation mechanism needed rigorous verification to ensure anti-privilege escalation (untrusted metadata cannot grant admin rights) and idempotency across repeated executions.

#### Decision
1. **Guarded Commit Boundary & Compensating Rollback:**
   - Explicitly moved `session.commit()` inside the guarded `try/except` block of `execute_reliable_role_update()` in `src/services/role_sync_service.py`.
   - The transaction lifecycle is strictly ordered:
     1. Transaction starts when `get_admin_db_session()` opens an administrative session and queries the target profile.
     2. Update intent recorded as `PENDING` in `RoleSyncJournal`.
     3. Supabase Auth Admin API is called (`PUT /auth/v1/admin/users/{user_id}`). On success, journal transitions to `IDP_UPDATED`.
     4. PostgreSQL profile model is updated (`target_profile.role = new_role`), followed by `session.flush()`.
     5. `session.commit()` is explicitly executed within the guarded block. If the commit fails:
        - The `except Exception` handler catches the commit failure immediately.
        - Journal transitions to `COMPENSATING`.
        - A compensating call to Supabase Auth Admin API restores `old_role`.
        - On compensation success, journal records `COMPENSATED`, PostgreSQL transaction is rolled back (`session.rollback()`), and HTTP 500 is raised.
        - On compensation failure, journal records `DESYNCHRONIZED`, critical alert is logged, and HTTP 502 is raised.
     6. Only if `session.commit()` succeeds does the journal transition to `COMMITTED`.
   - In `src/api/routers/auth.py`, other profile attributes (`quota_monthly_runs`, `full_name`) are staged *prior* to `execute_reliable_role_update()`, ensuring the entire profile change commits atomically within the verified boundary.

2. **RoleSyncJournal Durability Audit Findings & Enhancements:**
   - **Thread Safety:** Verified. Single-process concurrency is safely managed via `threading.Lock()`.
   - **Disk Flushing:** Enhanced `_persist_entry_unlocked()` with explicit `f.flush()` and `os.fsync(f.fileno())` inside safe OS exception handling to guarantee OS buffer writes survive crashes.
   - **Missing File / Directory:** Handled gracefully. Parent directories and the JSONL file are auto-created on first write.
   - **Corrupted / Truncated Lines:** Handled gracefully. During reload on startup (`_load_from_disk()`), malformed or truncated JSON lines are logged as warnings and skipped, while valid records are fully recovered.
   - **Storage I/O Failure Resilience:** Handled gracefully. If disk writes fail (e.g. read-only filesystem or disk full), the journal logs an error without crashing the transaction and preserves state in memory.
   - **Process Isolation Limitation (Multi-Process ASGI):** Documented architectural constraint: In multi-worker ASGI deployments (e.g. Gunicorn with multiple Uvicorn workers), each worker process maintains its own in-memory dictionary. While the append-only JSONL file captures writes from all processes, workers do not reload other workers' entries in real-time until process restart.
   - **Production Recommendation:** For horizontally scaled production environments, migrate `RoleSyncJournal` from a local JSONL file to a dedicated PostgreSQL audit table (`role_sync_audit_log`) accessed via an independent session, or employ an Outbox/CDC pattern.

3. **Reconciliation Verification & Anti-Privilege Escalation:**
   - Verified that `reconcile_user_role()` correctly identifies and resolves desynchronized states.
   - Verified graceful handling when Supabase is unreachable (returns HTTP 502 without corrupting local state).
   - Verified repeated reconciliation calls are completely idempotent.
   - Verified unauthorized calls are rejected (HTTP 401 unauthenticated, HTTP 403 non-admin).
   - Verified strict anti-privilege escalation: reconciliation never derives roles from user-writable `user_metadata` or top-level `role` claims, enforcing provenance exclusively from trusted `app_metadata.role`.
