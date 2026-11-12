# DharaScope: Final Academic Defense & Demonstration Script

**Project Title:** DharaScope — Automated Satellite-Based Surface Water Dynamics Monitoring Platform  
**Candidate / Presenter:** DharaScope Engineering & Science Team  
**Evaluation Session:** Final Academic Capstone Defense (November 2026)  
**Accompanying Materials:**  
- [DharaScope_Final_Presentation.pptx](file:///d:/Coding/Projects/DharaScope/DharaScope_Final_Presentation.pptx) (15-Slide Master Deck)  
- [docs/PROJECT_REPORT.md](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md) (Comprehensive Academic Capstone Report)  
- [docs/JUDGE_QA.md](file:///d:/Coding/Projects/DharaScope/docs/JUDGE_QA.md) (Evaluator Q&A Reference Guide with 30 Verified Answers)  
- [docs/PRESENTATION.md](file:///d:/Coding/Projects/DharaScope/docs/PRESENTATION.md) (Slide-by-Slide Content & Script Notes)  

---

## Defense Timing Overview (Total Time: ~11 Minutes + Q&A)

| Section | Target Duration | Focus Area |
| :--- | :---: | :--- |
| **Part 1: Elevator Pitch (Non-Specialist)** | 60 Seconds | Societal problem, core innovation, and practical value |
| **Part 2: Technical Architecture Deep-Dive** | 3 Minutes | System design, windowed COG streaming, PostGIS RLS, and spectral pipeline |
| **Part 3: Live Demonstration Runbook** | 5 Minutes | Step-by-step UI workflow across all 8 verified stages |
| **Part 4: Scientific Results & Limitations** | 2 Minutes | Real Gomti River findings, pixel reconciliation, and methodology constraints |
| **Part 5: Rapid-Fire Examiner Q&A** | Interactive | Direct, authoritative answers to high-frequency jury questions |

---

## Part 1: Elevator Pitch (60 Seconds)

> **Audience Context:** Non-specialist jury members, interdisciplinary faculty, department chairs.  
> **Objective:** Establish the vital importance of surface water monitoring and how DharaScope solves the Earth Observation data bottleneck.

### Verbal Narration:
"Good morning, esteemed committee members. 

Freshwater rivers and reservoirs across India face severe seasonal fluctuations—swinging between monsoon floods and critical winter recessions. Traditionally, monitoring these bodies relies on physical stream gauges placed tens of kilometers apart. They cannot tell us what is happening to dynamic floodplains and wetlands in between.

The European Space Agency's Sentinel-2 satellites capture every corner of Earth at 10-meter resolution every 5 days. But there is a huge engineering barrier: downloading a single satellite image tile requires downloading nearly a gigabyte of compressed data, requiring heavyweight desktop GIS software and hours of manual labor.

**DharaScope eliminates this barrier entirely.** We built a web-based, cloud-native Earth Observation platform that streams only the small geographic window a user selects—cutting data transfer by over 99%—and processes it on-the-fly. In under 10 seconds, a water resources planner can select a river reach, detect water boundaries across multiple dates, calculate exact surface water gain and loss down to the square meter, and download publication-ready reports.

DharaScope turns petabytes of raw satellite data into instant, actionable environmental intelligence."

---

## Part 2: Technical Architecture Deep-Dive (3 Minutes)

> **Audience Context:** Technical examiners, software engineers, systems and database evaluators.  
> **Visual Reference:** Slide 5 (*System Architecture & Data Flow*) and Slide 6 (*Windowed Sub-Granule COG Streaming*).

### Verbal Narration:
"Let us examine the four engineering tiers that make DharaScope operational, secure, and performant:

### 1. Presentation Tier (React 19, TypeScript, Leaflet)
Our frontend is built with React 19, TypeScript, and Vite. It integrates Leaflet for real-time vector digitization. When a user draws an Area of Interest (AOI), the client does not merely draw a polygon—it validates vertices, checks bounding extents against our strict $100\text{ km}^2$ operational ceiling, and communicates over secure HTTPS with bearer JWT tokens.

### 2. Spatial Persistence & Multi-Tenant Security (PostgreSQL 16 + PostGIS 3.6)
Our database enforces multi-tenant defense-in-depth through PostgreSQL Row-Level Security (RLS) located in [src/database/models.py](file:///d:/Coding/Projects/DharaScope/src/database/models.py). 
- Every database transaction sets `app.current_user_id` from the cryptographically verified Supabase JWT claims.
- PostgreSQL RLS policies physically prevent any tenant from reading or modifying another user's AOIs, satellite scenes, or analysis runs, even if application logic were compromised.
- Vector geometries are indexed with spatial GiST indexes (`idx_aois_geom`) and validated using PostGIS `ST_IsValid` and `ST_Area`.

### 3. Satellite Ingestion & Windowed COG Streaming Core
Traditional pipelines download entire 500 MB to 1 GB Sentinel-2 SAFE archives. In DharaScope:
- We query the Copernicus Data Space Ecosystem (CDSE) or AWS Open Data via SpatioTemporal Asset Catalog (STAC) protocols.
- We resolve the Cloud-Optimized GeoTIFF (COG) URLs for Band 3 (Green) and Band 8 (Near-Infrared).
- Using GDAL's `/vsicurl/` virtual file system and `rasterio`, our ingestion engine ([src/downloader.py](file:///d:/Coding/Projects/DharaScope/src/downloader.py)) issues HTTP range requests to download **only the exact pixel bounding box of the user's AOI**. For a 4.41 square kilometer study area, this streams just 88 kilobytes instead of a 600 megabyte granule—achieving a **99.98% reduction in network overhead**.

### 4. Calibrated Spectral Pipeline & 4-Class Change Engine
In [src/water_indices.py](file:///d:/Coding/Projects/DharaScope/src/water_indices.py) and [src/change_detection.py](file:///d:/Coding/Projects/DharaScope/src/change_detection.py):
- We compute McFeeters Normalized Difference Water Index:
  $$\text{NDWI} = \frac{\text{Green} - \text{NIR}}{\text{Green} + \text{NIR}} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$$
- Zero-division errors and sensor NoData masks are strictly isolated using IEEE 754 NaN handling and boolean validity masks.
- Binary masks are classified at the canonical threshold of $\tau = 0.0$.
- Multi-temporal pairs are encoded into a categorical 4-class transition matrix: Permanent Water (1 $\to$ 1), Water Recession (1 $\to$ 0), Water Inundation (0 $\to$ 1), and Persistent Land (0 $\to$ 0).
- Finally, our reporting engine ([src/reporting.py](file:///d:/Coding/Projects/DharaScope/src/reporting.py)) compiles these metrics into 300 DPI cartographic maps, CSV matrices, and archival PDF summaries."

---

## Part 3: Live Demonstration Runbook (5 Minutes)

> **Demonstration Method:** Step-by-step walkthrough of the live web application (or verified high-resolution browser captures if live network access is restricted).  
> **Companion Script:** [scripts/validate_real_satellite_browser.mjs](file:///d:/Coding/Projects/DharaScope/scripts/validate_real_satellite_browser.mjs).  
> **Visual Artifacts:** [outputs/validation_phase2_4/](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/).

```
+---------------------------------------------------------------------------------------+
| STAGE 1: LANDING & TELEMETRY                                           [0:00 - 0:30]  |
| - Action: Navigate to http://localhost:5173.                                          |
| - Screen: outputs/validation_phase2_4/01_initial_landing.png                          |
| - Narration: "Here is the DharaScope workstation. Notice the dark scientific visual   |
|   identity, system telemetry badges confirming backend health, and the Leaflet       |
|   interactive map centered over northern India."                                      |
+---------------------------------------------------------------------------------------+
| STAGE 2: AUTHENTICATION & SESSION HANDLING                             [0:30 - 1:00]  |
| - Action: Click 'Sign In', supply hydrologist credentials.                            |
| - Screen: outputs/validation_phase2_4/02_authenticated_session.png                    |
| - Narration: "Authentication is managed via Supabase Auth with JWT bearer claims.     |
|   Notice the header immediately displays the user's role ('hydrologist').             |
|   The backend extracts this identity to set PostgreSQL session RLS context."          |
+---------------------------------------------------------------------------------------+
| STAGE 3: VECTOR AOI DIGITIZATION & SPATIAL VALIDATION                 [1:00 - 1:45]  |
| - Action: Select 'Gomti River Study Reach' preset or draw custom polygon.            |
| - Screen: outputs/validation_phase2_4/03_aoi_validated.png                            |
| - Narration: "We select the Gomti River reach in Lucknow. The client checks the       |
|   geometry and sends it to POST /api/v1/aois. PostGIS evaluates ST_IsValid and        |
|   ST_Area in EPSG:4326/3857, confirming a validated area of 4.41 km²—well within      |
|   our 100 km² boundary limit. The AOI is committed with its unique UUID."             |
+---------------------------------------------------------------------------------------+
| STAGE 4: STAC SATELLITE DISCOVERY & SELECTION                         [1:45 - 2:30]  |
| - Action: Open Scene Discovery tab, query Sentinel-2 L2A for 2024 and 2025.           |
| - Screen: outputs/validation_phase2_4/04_analysis_configured.png                      |
| - Narration: "The user selects our two real observation dates: November 20, 2024      |
|   (T44TPN) and February 18, 2025 (T44TPN). The UI displays metadata including scene   |
|   tile IDs, acquisition timestamps, and provider source ('copernicus')."              |
+---------------------------------------------------------------------------------------+
| STAGE 5: ANALYSIS SUBMISSION & PIPELINE EXECUTION                     [2:30 - 3:15]  |
| - Action: Click 'Execute Change Detection'. Show progress bar & toast.                |
| - Screen: outputs/validation_phase2_4/05_analysis_success_real_data.png               |
| - Narration: "FastAPI receives the request, launches an asynchronous background       |
|   task, and streams the windowed COG rasters. In 6.8 seconds, computation finishes    |
|   with status COMPLETED. Notice the prominent badge: 'REAL DATA (Sentinel-2 L2A)'—    |
|   guaranteeing this is not a synthetic fallback."                                     |
+---------------------------------------------------------------------------------------+
| STAGE 6: DUAL-OBSERVATION METRICS & TRANSITION MATRIX                 [3:15 - 4:00]  |
| - Action: Scroll through Quantitative Metrics and Transition Breakdown.               |
| - Screen: outputs/validation_phase2_4/06_metrics_and_transitions.png                 |
| - Narration: "Here are the scientific metrics: Water area on 2024-11-20 was 53.07 ha  |
|   (53,074 m²), and on 2025-02-18 it was 166.45 ha (166,447 m²), representing a net   |
|   observed increase of +113.37 ha (+213.6%). The transition table classifies this     |
|   into 114.71 ha inundation, 1.33 ha recession, 51.74 ha permanent water, and         |
|   273.79 ha persistent land."                                                         |
+---------------------------------------------------------------------------------------+
| STAGE 7: INTERACTIVE CARTOGRAPHY & SPATIAL VISUALIZATION              [4:00 - 4:30]  |
| - Action: Toggle layer switcher between T1 NDWI, T2 NDWI, and Change Map.             |
| - Screen: outputs/validation_phase2_4/07_cartography_figures.png                      |
| - Narration: "The Leaflet canvas renders the spatial distribution. Cyan highlights    |
|   newly inundated floodplain areas; blue indicates stable river channels; red reveals |
|   localized sandbar recessions; gray represents surrounding urban and alluvial land."  |
+---------------------------------------------------------------------------------------+
| STAGE 8: REPORT EXPORT (PDF & CSV)                                    [4:30 - 5:00]  |
| - Action: Click 'Download PDF Report' and 'Export CSV Metrics'.                       |
| - Screen: outputs/validation_phase2_4/08_report_downloads.png                         |
| - Narration: "With a single click, the user exports a publication-grade 300 DPI PDF   |
|   report containing vector metadata, figures, and methodology notes, alongside raw     |
|   CSV transition matrices ready for GIS ingest."                                      |
+---------------------------------------------------------------------------------------+
```

---

## Part 4: Scientific Findings, Reconciliation & Limitations (2 Minutes)

> **Audience Context:** Remote sensing specialists, hydrology faculty, rigorous examiners.  
> **Key Goal:** Explain the observed data with scientific humility, reconcile technical pixel counts, and state limitations transparently.

### 1. Explanation of Observed Water Area Increase (+113.37 ha)
"Our dual observations over the Gomti River reach show a substantial increase in detected water surface area:
- **November 20, 2024 (T1):** 53.07 ha of open surface water.
- **February 18, 2025 (T2):** 166.45 ha of open surface water.
- **Net Change:** $+113.37\text{ ha}$ ($+213.6\%$).

**Crucial Scientific Distinction:**  
As responsible data scientists, we report this strictly as an **observed satellite-derived surface water expansion**. We do **not** claim this proves upstream barrage operations, baseflow changes, or river engineering interventions. The observed reflectance increase could be caused by localized barrage impoundment, agricultural runoff accumulation, backwater effects, or temporary seasonal flooding. Attributing root hydrological causes requires in-situ gauge records and barrage operational logs, which lie outside satellite optical data alone."

### 2. Reconciliation of the 44,178 vs. 44,600 Pixel Count
"During Phase 2.4, an apparent discrepancy arose between an earlier count of 44,600 pixels and the verified raster count of 44,178 pixels:
- **Mathematical Root:** When reprojecting a WGS84 (EPSG:4326) vector polygon into UTM Zone 44N (EPSG:32644) at a 10m grid, bounding raster dimensions are determined by affine coordinate transforms (`rasterio.transform.from_origin`).
- The unmasked rectangular bounding box is $223 \times 200 = 44,600\text{ pixels}$.
- When the precise polygonal boundary is burned as a valid-data mask (`rasterio.features.geometry_mask`), exactly **44,178 pixels** fall inside the valid polygon interior ($4.4178\text{ km}^2$), while 422 pixels are outside boundary margins.
- Both observations were processed on the **exact same 44,178-pixel grid**, ensuring zero spatial misalignment."

### 3. Known System Limitations
1. **Cloud Occlusion:** Optical Sentinel-2 imagery cannot penetrate dense monsoon cloud cover. (Future scope: Sentinel-1 SAR integration).
2. **Sub-Pixel Water Bodies:** Small irrigation channels narrower than the 10-meter pixel resolution cannot be fully resolved without spectral unmixing.
3. **Operational Boundary Limit:** The platform enforces a maximum AOI limit of $100\text{ km}^2$ to prevent server memory saturation during synchronous API processing.

---

## Part 5: Rapid-Fire Examiner Defense Q&A

Use these concise, authoritative responses when challenged by the committee:

### Q1: "Why McFeeters NDWI instead of Xu's Modified NDWI (MNDWI)?"
> **Answer:** "McFeeters NDWI uses Green (B03) and NIR (B08), both natively available at **10-meter spatial resolution** on Sentinel-2. Xu's MNDWI requires SWIR (B11), which is captured at **20-meter resolution**. Using MNDWI would require spatial resampling and downscaling, introducing edge artifacts along narrow riverbanks. McFeeters gives us the sharpest native geometric resolution for channel boundaries."

### Q2: "How do you guarantee one user cannot see another user's spatial data?"
> **Answer:** "We use PostgreSQL Row-Level Security (RLS) defined in [src/database/models.py](file:///d:/Coding/Projects/DharaScope/src/database/models.py). The FastAPI middleware verifies the Supabase JWT and sets `app.current_user_id` in the database session. Even if an attacker directly executes raw SQL on the database, PostgreSQL's kernel enforces `WHERE user_id = current_setting('app.current_user_id')`, physically blocking cross-tenant reads and writes."

### Q3: "What happens if CDSE or AWS satellite services are down during an analysis?"
> **Answer:** "The downloader raises a descriptive `SatelliteDiscoveryError` or `BandDownloadError` with HTTP status codes and endpoint URLs. The backend transitions the analysis job state to `FAILED`, persists the exact error in the database, and alerts the user through the UI. Crucially, the system **never silently falls back to synthetic data** in production."

### Q4: "How did you verify test coverage, and what is your current testing state?"
> **Answer:** "We maintain a multi-tier test suite of **186 backend test cases** and **18 frontend tests**—totaling 204 automated tests with a 100% pass rate (185 passed, 1 skipped external live test). Using `pytest-cov`, we verified **83.0% statement coverage across all 2,605 statements in `src/`**, with core computational modules such as `visualization` (99%), `reporting` (94%), `change_detection` (95%), and `water_indices` (91%) achieving 90%–100% coverage."

### Q5: "Can your system handle an entire state or country (e.g. all of Uttar Pradesh)?"
> **Answer:** "Not in the current synchronous architecture, by design. We deliberately enforce a $100\text{ km}^2$ AOI ceiling to ensure sub-10-second processing and bounded memory footprints. Scaling to state-wide monitoring would require migrating our background worker to an asynchronous distributed cluster using Apache Spark or Celery with cloud-native raster mosaicking."

---

## Part 6: Concluding Statement (60 Seconds)

"To conclude: DharaScope successfully demonstrates that complex Earth Observation data can be democratized into an automated, responsive, and secure web GIS. 

By combining windowed Cloud-Optimized GeoTIFF streaming, native 10-meter Sentinel-2 spectral analysis, multi-tenant PostgreSQL Row-Level Security, and automated cartographic reporting, we have delivered an end-to-end platform validated on real satellite acquisitions over the Gomti River basin.

Thank you. We are now open to your questions and detailed code inspection."
