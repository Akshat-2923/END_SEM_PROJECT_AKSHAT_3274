# Changelog
All notable changes to the DharaScope platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
