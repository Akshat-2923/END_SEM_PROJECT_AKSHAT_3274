# DharaScope: Current Project Status
## Real-Time Subsystem Health, Test Coverage, Known Debt & Development Priorities

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Current Phase:** Phase 2.2 — Platform Evolution (Part A & Part B1 Complete; Part B2 Gateway Pending)  
**Last Updated:** 2026-11-07  
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

The automated test suite has expanded to **64 tests**, all passing with zero regressions.

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
- [x] **Requirements & Architectural Documentation (`docs/`):** Full SRS (`docs/SRS.md`), Traceability Matrix (`docs/REQUIREMENTS_TRACEABILITY.md`), Technical Decisions (`docs/TECHNICAL_DECISIONS.md`), and System Constraints (`docs/SYSTEM_CONSTRAINTS.md`).
- [x] **Version Control:** Published to GitHub under `Akshat-2923/END_SEM_PROJECT_AKSHAT_3274`.

### 2.2 In-Progress Subsystems
- [ ] **Phase 2.2, Part B2 Architecture:** FastAPI application gateway skeleton and Supabase Auth integration.

### 2.3 Pending Subsystems (Scheduled for Phase 2.2 Part B2 / Phase 2.3)
- [ ] **FastAPI Service Gateway (`server.py` & `src/auth.py`):** REST endpoints wrapping the analysis engine with Supabase JWT Bearer token authentication.
- [ ] **Supabase Storage Integration (`src/storage.py`):** Object storage partitioning (`rasters/`, `maps/`, `reports/`) and automated 90-day retention cleanup for intermediate rasters.
- [ ] **Empirical Performance Benchmarks (`benchmarks/`):** Load testing API latency ($< 500\text{ ms}$), PDF compilation ($< 10\text{ s}$), and worker memory footprint on $25\text{ km}^2$ AOIs ($< 2\text{ GB RAM}$).

### 2.4 Blocked Subsystems
- **None.** All prerequisites for Phase 2.2 Part B2 are satisfied.

---

## 3. Automated Test Suite Metrics

- **Total Automated Tests:** 64
- **Pass Rate:** 100% (64 passed, 0 failed, 4 deprecation warnings in 29.70s)
- **Test Modules:**
  1. `tests/test_aoi_validation.py`: 15 passed (valid bboxes, GeoJSON dicts, Features, Collections, strings, MultiPolygons, min/max area limits, topology self-intersections, coordinate bounds, vertex ceilings).
  2. `tests/test_change_detection.py`: 3 passed (change matrix, area metrics, zero-baseline percentage handling, spatial dimension mismatch).
  3. `tests/test_database_migrations.py`: 3 passed (Alembic configuration loading, migration script discovery, live PostgreSQL upgrade/downgrade cycle).
  4. `tests/test_database_models.py`: 17 passed (model metadata, profile role/quota constraints, AOI PostGIS insertion, geodetic spatial calculations, AOI area/vertex constraints, analysis run constraints, 1:1 water metrics uniqueness, artifact type/bucket constraints, cascading deletions).
  5. `tests/test_downloader.py`: 11 passed (auth errors, credential detection, Bearer token masking, redirect auth preservation, HTML error rejection, corrupted binary rejection, raster verification, synthetic generation, band retrieval modes).
  6. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full pipeline execution from bands to NDWI to change detection).
  7. `tests/test_reporting.py`: 7 passed (metrics extraction, CSV report generation, PDF report generation, synthetic badges).
  8. `tests/test_stac_client.py`: 3 passed (bbox validation, item metadata extraction, HTTP error backoff).
  9. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero-denominator protection, water classification, shape mismatch error).
  2. `tests/test_reporting.py`: 7 passed (manifest metric extraction, CSV formatting, PDF generation with/without figures, synthetic provenance tagging).
  3. `tests/test_change_detection.py`: 3 passed (change matrix, zero baseline, spatial mismatch).
  4. `tests/test_downloader.py`: 11 passed (credentials detection, auth requirements, trusted redirects, HTML rejection, file truncation, raster verification, synthetic generation, mode resolution).
  5. `tests/test_stac_client.py`: 3 passed (bbox validation, metadata extraction, HTTP error handling).
  6. `tests/test_water_indices.py`: 4 passed (NDWI formula, zero denominator, water classification, shape mismatch).
  7. `tests/test_end_to_end_raster_pipeline.py`: 1 passed (full integration from arrays to transition matrix).

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
2. **CDSE Keycloak Session Lifespans:** CDSE bearer tokens expire within 10 to 60 minutes. The downloader handles re-authentication, but unauthenticated public COG retrieval remains the most reliable zero-maintenance route.
3. **Pending Benchmarks:** The proposed $25\text{ km}^2$ memory footprint ceiling ($< 2\text{ GB RAM}$) and API latency target ($< 500\text{ ms}$) represent architecture specifications and must not be reported as verified until formal benchmark scripts are executed in Phase 2.2 Part B.
4. **Matplotlib Raster Memory:** Rendering 300 DPI multi-panel figures in `src/visualization.py` allocates ~$300–450\text{ MB}$ of transient memory. Memory is released upon plot close, but worker concurrency should be capped at 2–3 simultaneous runs per container.

---

## 6. Recommended Next Priorities (Phase 2.2, Part B)

1. **PostgreSQL + PostGIS Schema Migration:** Formulate SQL DDL scripts creating `profiles`, `aois`, `analysis_runs`, and `water_metrics` with Row-Level Security policies.
2. **FastAPI Application Gateway:** Build `server.py` and `src/auth.py` exposing REST endpoints for AOI validation, STAC search, pipeline dispatch, and report export.
3. **Supabase JWT Middleware:** Implement Bearer token extraction and cryptographic signature validation using Supabase JWKS.
4. **Empirical Benchmarking Suite:** Implement `benchmarks/benchmark_pipeline.py` to measure peak memory, CPU time, and latency on a standardized $25\text{ km}^2$ AOI.
