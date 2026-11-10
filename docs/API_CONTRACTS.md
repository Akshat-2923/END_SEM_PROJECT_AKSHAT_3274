# DharaScope REST API Specification & Service Contracts
## Phase 2.2 Part C: Application Service Layer

**Document Version:** 1.0.0  
**Base URL:** `/api/v1`  
**OpenAPI Specification:** `/openapi.json` | Swagger UI: `/docs` | ReDoc: `/redoc`  
**Authentication Scheme:** HTTP Bearer JWT (`Authorization: Bearer <supabase_jwt>`)  

---

## 1. Overview & Security Architecture

The DharaScope FastAPI application service layer exposes RESTful endpoints for:
1. System health, service diagnostics, and API root discovery.
2. Authenticated user profile retrieval and administrative account management.
3. Geographical Area of Interest (AOI) validation, PostGIS spatial persistence, and ownership-enforced CRUD.
4. Sentinel-2 multi-temporal surface water analysis run dispatch and asynchronous lifecycle tracking.
5. Surface water change metrics inspection, artifact enumeration, and secure ReportLab PDF / CSV report downloads.

### Security & Access Control
- **Stateless Bearer JWT Validation:** Validates Supabase JWTs via `verify_supabase_jwt` using cryptographic HMAC or JWKS public keys.
- **Trusted Role Extraction:** Application authorization roles (`user` vs `admin`) are derived exclusively from `app_metadata.role`. Client-writable `user_metadata` is untrusted and discarded.
- **Row-Level Security (RLS) Propagation:** Database sessions enforce PostgreSQL 16 RLS by executing `SET LOCAL ROLE dharascope_app;` and binding session claims `request.jwt.claim.sub` and `request.jwt.claim.role`.
- **Zero Information Leakage:** System paths (e.g. `C:\...` or `/var/...`), provider passwords, and internal exception traces are strictly stripped and sanitized from API error responses.

---

## 2. Standard Error Response Envelope

All error responses across the API follow a standardized envelope:

```json
{
  "error": "AOIValidationError",
  "detail": "AOI surface area (0.0500 km²) is below the minimum threshold of 0.10 km².",
  "status_code": 400
}
```

| HTTP Status | Error Name | Meaning / Trigger |
| :--- | :--- | :--- |
| `400 Bad Request` | `AOIValidationError`, `ReportingError`, `HTTPException` | Topological violation, area limit failure, invalid state |
| `401 Unauthorized` | `HTTPException` | Missing, expired, invalid signature, or malformed Bearer token |
| `403 Forbidden` | `HTTPException` | Insufficient permissions (e.g. non-admin accessing admin routes or modifying other user's public AOI) |
| `404 Not Found` | `HTTPException` | Requested entity (AOI, Run, Artifact) does not exist or belongs to another user |
| `422 Unprocessable` | `RequestValidationError` | Pydantic payload validation failure (e.g. invalid bounds, malformed UUID) |
| `429 Too Many Requests`| `HTTPException` | User monthly analysis run quota exceeded |
| `500 Server Error` | `InternalServerError` | Uncaught server exception (sanitized; details logged server-side) |

---

## 3. Endpoints Specification

### 3.1 System Health & Diagnostics

#### `GET /health` (Alias: `GET /api/v1/health`)
Checks uptime, active environment, and PostgreSQL connection.

- **Auth Required:** No
- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "app_name": "DharaScope",
    "version": "2.2.0",
    "environment": "development",
    "database": "connected",
    "timestamp": "2026-11-10T16:54:28.514951Z"
  }
  ```

#### `GET /`
Service discovery root.

- **Auth Required:** No
- **Response `200 OK`:**
  ```json
  {
    "service": "DharaScope API",
    "description": "Satellite-Based River Surface Water Dynamics Platform",
    "version": "2.2.0",
    "docs_url": "/docs",
    "redoc_url": "/redoc",
    "health_check": "/health",
    "status": "operational"
  }
  ```

---

### 3.2 Authentication & User Profiles

#### `GET /api/v1/auth/me`
Retrieves or auto-provisions the authenticated user's database profile.

- **Auth Required:** Yes (`user` or `admin`)
- **Headers:** `Authorization: Bearer <jwt>`
- **Response `200 OK`:**
  ```json
  {
    "id": "c698f83e-7f7d-458e-bd64-73368c952089",
    "email": "hydrologist@dharascope.org",
    "full_name": "Dr. Gomti Hydrologist",
    "role": "user",
    "quota_monthly_runs": 50,
    "created_at": "2026-11-10T22:25:02.753040Z",
    "updated_at": "2026-11-10T22:25:02.753040Z"
  }
  ```

#### `PATCH /api/v1/auth/me`
Updates user's own display profile (`full_name`). Regular users cannot alter `role` or `quota_monthly_runs`.

- **Auth Required:** Yes (`user` or `admin`)
- **Request Body:**
  ```json
  {
    "full_name": "Senior Hydrology Researcher"
  }
  ```
- **Response `200 OK`:** Updated `UserProfileResponse`.

#### `GET /api/v1/admin/users`
Lists all user profiles in the database.

- **Auth Required:** Yes (`admin` only)
- **Authoritative Database Privilege Check & Immediate Revocation:** Validates that the caller's UUID corresponds to an active `role = 'admin'` record in the PostgreSQL `profiles` table within a restricted RLS-aware session. A revoked administrator holding an unexpired JWT is immediately rejected with `403 Forbidden`. Database errors fail closed with `500 Internal Server Error`.
- **Response `200 OK`:** `List[UserProfileResponse]`
- **Response `403 Forbidden`:** If accessed by a regular user or revoked admin.

#### `PATCH /api/v1/admin/users/{user_id}`
Updates any user's role or monthly quota.

- **Auth Required:** Yes (`admin` only, verified authoritatively in PostgreSQL)
- **Request Body:**
  ```json
  {
    "role": "admin",
    "quota_monthly_runs": 200,
    "full_name": "Promoted Lead"
  }
  ```
- **Response `200 OK`:** Updated `UserProfileResponse`.
- **Distributed Two-Phase Consistency & Compensating Rollback (Phase 2.2D.1):** Modifying `role` records an audit intent in `RoleSyncJournal`, pushes updates to Supabase GoTrue Admin API (`PUT /auth/v1/admin/users/{user_id}`), and commits to PostgreSQL `profiles.role`. If Supabase fails, the database remains untouched. If Supabase succeeds but PostgreSQL commit fails, a compensating call immediately rolls back Supabase to the previous role (HTTP 500 returned). If both fail, `DESYNCHRONIZED` is logged and HTTP 502 returned. Retries are idempotent.
- **Immediate Admin Revocation (Phase 2.2D.1):** Revoked administrators lose access on their very next request to any administrative endpoint, eliminating the historical token TTL window delay.

#### `POST /api/v1/admin/users/{user_id}/reconcile`
Idempotently reconciles role drift between PostgreSQL and Supabase Auth.

- **Auth Required:** Yes (`admin` only)
- **Response `200 OK`:**
  ```json
  {
    "user_id": "c698f83e-7f7d-458e-bd64-73368c952089",
    "authoritative_role": "user",
    "status": "reconciled",
    "sync_id": "7f884210-61d4-4ea0-bd61-e0a5c48b2612"
  }
  ```

---

### 3.3 Geographical Area of Interest (AOI) Management

#### `POST /api/v1/aois/validate`
Validates geometry against topological integrity, coordinate envelope, vertex count ($\le 500$), and ellipsoidal area bounds ($0.10–100.00\text{ km}^2$) without saving.

- **Auth Required:** Yes
- **Request Body:**
  ```json
  {
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[80.90, 26.84], [80.92, 26.84], [80.92, 26.86], [80.90, 26.86], [80.90, 26.84]]]
    }
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "valid": true,
    "geometry": { "type": "Polygon", "coordinates": [...] },
    "geometry_type": "Polygon",
    "bbox": [80.90, 26.84, 80.92, 26.86],
    "centroid": [80.91, 26.85],
    "area_m2": 4402123.45,
    "area_km2": 4.4021,
    "area_hectares": 440.21,
    "vertex_count": 5
  }
  ```

#### `POST /api/v1/aois`
Creates and registers a new AOI with PostGIS geometry.

- **Auth Required:** Yes
- **Request Body:**
  ```json
  {
    "name": "Lucknow Gomti Urban Reach",
    "description": "Baseline monitoring reach",
    "geometry": { "type": "Polygon", "coordinates": [...] },
    "is_public": false
  }
  ```
- **Response `201 Created`:** `AOIResponse`.

#### `GET /api/v1/aois`
Lists AOIs accessible to user (private AOIs + public AOIs, or all for admin).

- **Query Parameters:** `limit: int = 50`, `offset: int = 0`, `public_only: bool = false`.
- **Response `200 OK`:**
  ```json
  {
    "items": [...],
    "total": 12
  }
  ```

#### `GET /api/v1/aois/{aoi_id}`
Retrieves a single AOI entity. Enforces privacy: private AOIs owned by other users return `404 Not Found`.

- **Response `200 OK`:** `AOIResponse`.

#### `PATCH /api/v1/aois/{aoi_id}`
Updates AOI name, description, or public sharing flag. Only the owner or an admin can update; other users receive `403 Forbidden`.

#### `DELETE /api/v1/aois/{aoi_id}`
Deletes an AOI. Only the owner or an admin can delete; other users receive `403 Forbidden`.

- **Response `204 No Content`**

---

### 3.4 Satellite Analysis & Hydrological Runs

#### `POST /api/v1/analyses`
Creates and launches an analysis run. Runs in the background without blocking the event loop.

- **Query Parameters:** `sync: bool = false` (if `true`, executes synchronously for tests).
- **Execution Lifecycle & Restart Note:** In default asynchronous mode (`sync=false`), the task is enqueued to FastAPI's in-process `BackgroundTasks`. Tasks do not survive server restarts; if the application process restarts during execution, jobs in `QUEUED` or `PROCESSING` state are orphaned in the database.
- **Request Body:**
  ```json
  {
    "aoi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "ndwi_threshold": 0.00,
    "max_cloud_cover": 10.0,
    "datetime_range": "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
    "data_source": "auto"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "id": "e4585f64-5717-4562-b3fc-2c963f66afa7",
    "user_id": "c698f83e-7f7d-458e-bd64-73368c952089",
    "aoi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "QUEUED",
    "data_provider": "PENDING_RETRIEVAL",
    "is_real_data": true,
    "t1_scene_id": "PENDING_DISCOVERY",
    "t1_date": "2026-11-10T16:54:28Z",
    "t1_cloud_cover": null,
    "t2_scene_id": "PENDING_DISCOVERY",
    "t2_date": "2026-11-10T16:54:28Z",
    "t2_cloud_cover": null,
    "ndwi_threshold": 0.0,
    "error_message": null,
    "execution_duration_sec": null,
    "execution_timestamp": "2026-11-10T16:54:28Z",
    "created_at": "2026-11-10T16:54:28Z",
    "updated_at": "2026-11-10T16:54:28Z"
  }
  ```

#### `GET /api/v1/analyses`
Lists user's analysis runs (or all runs for admin) with execution status.

#### `GET /api/v1/analyses/{analysis_id}`
Polls status (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`) and inspects timings.

#### `DELETE /api/v1/analyses/{analysis_id}`
Deletes run and cascades deletion to metrics and artifacts (owner or admin only).

- **Response `204 No Content`**

#### `GET /api/v1/analyses/{analysis_id}/metrics`
Retrieves quantitative surface water area metrics and categorical transitions for completed runs.

- **Response `200 OK`:**
  ```json
  {
    "id": "8bb85f64-5717-4562-b3fc-2c963f66afb2",
    "analysis_run_id": "e4585f64-5717-4562-b3fc-2c963f66afa7",
    "common_valid_pixels": 1323037,
    "common_valid_area_ha": 13230.37,
    "pixel_size_m2": 100.0,
    "t1_water_pixels": 18456,
    "t1_water_area_m2": 1845600.0,
    "t1_water_area_ha": 184.56,
    "t2_water_pixels": 13933,
    "t2_water_area_m2": 1393300.0,
    "t2_water_area_ha": 139.33,
    "absolute_change_m2": -452300.0,
    "absolute_change_ha": -45.23,
    "percentage_change": -24.51,
    "persistent_water_m2": 1251800.0,
    "persistent_water_ha": 125.18,
    "apparent_loss_m2": 593800.0,
    "apparent_loss_ha": 59.38,
    "apparent_gain_m2": 141500.0,
    "apparent_gain_ha": 14.15,
    "limitation_statement": "Surface area changes indicate inundation variations...",
    "created_at": "2026-11-10T16:54:35Z"
  }
  ```

#### `GET /api/v1/analyses/{analysis_id}/artifacts`
Lists all generated figure PNGs, thumbnails, and report artifacts. Note: internal absolute file paths are strictly omitted; only relative IDs and secure download URLs are exposed.

- **Response `200 OK`:**
  ```json
  {
    "items": [
      {
        "id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
        "analysis_run_id": "e4585f64-5717-4562-b3fc-2c963f66afa7",
        "artifact_type": "REPORT_PDF",
        "storage_bucket": "reports",
        "file_name": "dharascope_report_2023-10-10_to_2023-12-09.pdf",
        "file_size_bytes": 182450,
        "mime_type": "application/pdf",
        "download_url": "/api/v1/artifacts/1fa85f64-5717-4562-b3fc-2c963f66afa1/download",
        "created_at": "2026-11-10T16:54:35Z"
      }
    ],
    "total": 6
  }
  ```

#### `GET /api/v1/analyses/{analysis_id}/reports/csv`
Downloads the structured analysis CSV report (`Content-Disposition: attachment; filename=...`).

- **Response `200 OK`:** File stream (`text/csv`).

#### `GET /api/v1/analyses/{analysis_id}/reports/pdf`
Downloads publication-ready ReportLab PDF report (`Content-Disposition: attachment; filename=...`).

- **Response `200 OK`:** File stream (`application/pdf`).

---

### 3.5 Generated Artifact Downloads

#### `GET /api/v1/artifacts/{artifact_id}/download`
Downloads any individual generated artifact (PNG comparison panel, transition map, single-observation NDWI map, thumbnail, or GeoTIFF raster) with parent run ownership verification.

- **Auth Required:** Yes
- **Response `200 OK`:** File stream with appropriate MIME type.
- **Storage Subsystem (Phase 2.2D & 2.2D.1):** Handled via `src/storage.py` abstraction. In local mode (`SUPABASE_STORAGE_ENABLED=false`), artifacts are streamed directly from `outputs/`. In cloud mode (`SUPABASE_STORAGE_ENABLED=true`), artifacts are downloaded from Supabase Storage buckets (`maps`, `reports`, `rasters`) via authenticated requests using the backend service-role key, cached, and streamed securely to the verified owner. Cross-user access is strictly blocked via parent `AnalysisRun` ownership verification.
- **Verification Boundary Notice:** Offline and CI test environments verify the Supabase Storage subsystem through mocked HTTP responses (`tests/test_storage.py`). Live external cloud verification is decoupled into `TestLiveSupabaseStorageIntegration` and requires actual external credentials (`DHARASCOPE_LIVE_SUPABASE_STORAGE=1`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) with pre-provisioned buckets.

