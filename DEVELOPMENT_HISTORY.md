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


