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
