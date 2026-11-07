# Software Requirements Specification (SRS)
## DharaScope: Satellite-Based River Surface Water Dynamics Platform

**Document Version:** 2.1.0  
**Phase:** Phase 2.1 — SRS Validation & Architecture Blueprint  
**Status:** Approved for Implementation  
**Project Classification:** Academic Capstone / Registered College Project (Geospatial Remote Sensing)  
**Study Reach Baseline:** Gomti River Reach, Lucknow, Uttar Pradesh, India (`[80.88, 26.80, 81.00, 26.90]`)

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) establishes the complete functional, non-functional, interface, and data specifications for **DharaScope Phase 2**. Building directly upon the validated Phase 1 satellite-processing pipeline, Phase 2 transitions DharaScope from a standalone single-reach feasibility prototype into a robust, multi-user geospatial analytics platform capable of processing dynamic user-specified Areas of Interest (AOIs), enforcing role-based access control, managing spatiotemporal metadata, and generating verifiable audit reports.

### 1.2 Scope of the Platform
DharaScope ingests multi-temporal Sentinel-2 Multispectral Instrument (MSI) Level-2A imagery to evaluate, quantify, and map surface water area changes across river corridors.
- **In-Scope:**
  - Automated STAC catalog discovery and multi-temporal scene pair selection.
  - Spectral band retrieval (Band 3 Green and Band 8 Near-Infrared at 10m native ground sampling distance).
  - Normalized Difference Water Index (NDWI) calculation with zero-denominator safeguards and numerical clamping.
  - Binary water classification using configurable site-calibrated thresholds ($\tau$).
  - Four-class spatial transition matrix generation (perennial channel, apparent recession, apparent expansion, non-water).
  - Geographical AOI polygon ingestion with strict coordinate, vertex, and area bounds ($0.1\text{ km}^2$ to $100.0\text{ km}^2$).
  - Decoupled user authentication via Supabase Auth and token validation via FastAPI.
  - Persistent metadata tracking via PostgreSQL + PostGIS.
  - Reproducible, audit-grade reporting in structured CSV and cartographic PDF formats.
- **Out-of-Scope (Strict Non-Goals):**
  - Chemical, biological, or pollutant concentration analysis (NDWI measures optical water reflectance only).
  - Bathymetric depth modeling and volumetric discharge measurement (requires in-situ stream gauges).
  - Black-box AI/ML generative substitutes for physical optical reflectance values.
  - Commercial cloud infrastructure or unneeded microservice orchestration.

### 1.3 Definitions, Acronyms, and Abbreviations
- **AOI:** Area of Interest. A user-defined geographical polygon bounding the study area.
- **BOA:** Bottom-Of-Atmosphere reflectance (Level-2A surface reflectance corrected for atmospheric distortion).
- **CDSE:** Copernicus Data Space Ecosystem (official European Space Agency data gateway).
- **COG:** Cloud-Optimized GeoTIFF. A raster format enabling HTTP range requests for spatial subsetting.
- **CRS:** Coordinate Reference System (e.g., EPSG:4326 for WGS84 geographic, EPSG:32644 for UTM Zone 44N).
- **GSD:** Ground Sampling Distance (10 meters per pixel for Sentinel-2 Bands 3 and 8).
- **MSI:** Multispectral Instrument onboard Sentinel-2A and Sentinel-2B satellites.
- **NDWI:** Normalized Difference Water Index, defined as $(\text{B03} - \text{B08}) / (\text{B03} + \text{B08})$ [McFeeters, 1996].
- **RLS:** Row-Level Security (PostgreSQL access control policy).
- **STAC:** SpatioTemporal Asset Catalog specification.

---

## 2. System Overview & Architecture

### 2.1 System Context
The DharaScope platform operates as a modular, three-tier geospatial architecture:
1. **Frontend Presentation Tier:** Streamlit scientific GIS dashboard (Phase 1 verified) transitioning to a responsive modern client. Provides AOI drawing, temporal slider controls, multi-panel map viewports, and export triggers.
2. **Application & Processing Tier:** FastAPI backend wrapping the validated `src/` core processing pipeline (`stac_client`, `scene_selection`, `downloader`, `water_indices`, `change_detection`, `visualization`).
3. **Data & Storage Tier:** 
   - External Satellite Gateways: Copernicus Data Space Ecosystem (CDSE) and AWS Open Data Sentinel-2 COG archive.
   - Relational & Geospatial Database: Supabase PostgreSQL with PostGIS extensions.
   - Asset Storage: Supabase Storage S3-compatible buckets for raster masks, map figures, and reports.

```
+-----------------------------------------------------------------------------------+
|                           DharaScope Web Frontend                                 |
|         (GIS Map Viewport, AOI Digitizer, Temporal Controls, Metrics KPI)         |
+-----------------------------------------+-----------------------------------------+
                                          |
                      HTTPS / JWT Bearer  |
                                          v
+-----------------------------------------------------------------------------------+
|                          FastAPI Application Gateway                              |
|           [JWT Auth Validation] [AOI Geometry Validator] [Task Router]            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                       Core Scientific Analysis Engine (src/)                      |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  | stac_client.py     |  | downloader.py      |  | water_indices.py            |  |
|  | CDSE / EarthSearch |  | Auth / COG Range   |  | NDWI = (B03-B08)/(B03+B08)  |  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
|  | scene_selection.py |  | change_detection.py|  | visualization.py            |  |
|  | Pair Optimization  |  | 4-Class Transition |  | 300 DPI Spatial Cartography |  |
|  +--------------------+  +--------------------+  +-----------------------------+  |
+-------------------+---------------------+---------------------+-------------------+
                    |                     |                     |
                    v                     v                     v
+-----------------------+ +-------------------------+ +-----------------------------+
| External S2 Gateways  | | PostgreSQL + PostGIS    | | Supabase Object Storage     |
| - CDSE STAC / OData   | | - User Profiles / Roles | | - rasters/ (Intermediate)   |
| - AWS Open Data COGs  | | - AOI Polygons (EPSG)   | | - maps/ (PNG Figures)       |
| - S2A/S2B MSI L2A     | | - Analysis Runs & KPIs  | | - reports/ (PDF / CSV)      |
+-----------------------+ +-------------------------+ +-----------------------------+
```

---

## 3. User Roles & Access Control

### 3.1 Role Hierarchy
The platform recognizes two explicit operational roles:
1. **User (Authenticated Researcher / Student / Evaluator):**
   - Submit analysis requests for custom AOIs within allowed geographical limits ($0.1–100\text{ km}^2$).
   - Access historical personal analysis runs and metrics.
   - Export official CSV and PDF feasibility reports for personal runs.
   - View public demonstration runs (including the Gomti River Lucknow benchmark).
2. **Administrator:**
   - Inherits all User permissions.
   - Inspect platform-wide execution logs, system resource consumption, and error rates.
   - Configure global pipeline defaults (default cloud cover tolerance, satellite gateway timeouts).
   - Trigger automated storage lifecycle cleanups (90-day retention enforcement).
   - Adjust per-user analysis quotas.

---

## 4. Functional Requirements (FR)

### Module 1: Satellite Data Ingestion (FR-1)
- **FR-1.1 [STAC Discovery]:** The system shall query the Copernicus Data Space Ecosystem (CDSE) STAC API (`v1/search`) or secondary Earth Search STAC using RFC 3339 datetime intervals, spatial bounding boxes, and maximum cloud cover thresholds.
- **FR-1.2 [Product Specification]:** The system shall strictly consume Sentinel-2 Level-2A surface reflectance products (Bottom-Of-Atmosphere, atmospherically corrected).
- **FR-1.3 [Band Ingestion]:** The system shall ingest Band 3 (Green, central wavelength $\lambda = 560\text{ nm}$, bandwidth $36\text{ nm}$, $10\text{ m}$ GSD) and Band 8 (Near-Infrared, central wavelength $\lambda = 842\text{ nm}$, bandwidth $115\text{ nm}$, $10\text{ m}$ GSD).
- **FR-1.4 [Primary Retrieval Workflow]:** When valid CDSE credentials (`CDSE_USERNAME`, `CDSE_PASSWORD` or `CDSE_ACCESS_TOKEN`) are configured, the system shall authenticate against the CDSE Keycloak service and stream single-band JP2 assets via OData with redirect persistence (`LocationTrustedSession`).
- **FR-1.5 [Open-Access Operational Fallback]:** In unauthenticated or public modes, the system shall resolve matching Sentinel-2 scenes from the AWS Open Data Cloud-Optimized GeoTIFF archive and perform HTTP range requests (`/vsicurl/`) to window-clip only the requested study bounds without downloading full 500MB+ tiles.
- **FR-1.6 [Integrity Verification]:** Every downloaded or streamed raster file shall be verified prior to processing via `rasterio`. Files with missing CRS, non-positive dimensions, truncated payloads, or HTTP error strings (HTML/JSON error envelopes) shall be rejected immediately.
- **FR-1.7 [Synthetic Data Safeguard]:** Offline synthetic sample data shall only be triggered when external network gateways fail and synthetic mode is explicitly enabled. Synthetic rasters must carry immutable tags (`PROVENANCE=SYNTHETIC_BENCHMARK_SAMPLE`) and never be presented as genuine satellite observations.

### Module 2: Geographical AOI Validation (FR-2)
- **FR-2.1 [Area Range Bounds]:** The system shall validate that the user-supplied AOI polygon area satisfies:
  $$0.10\text{ km}^2 \le \text{Area}_{\text{AOI}} \le 100.00\text{ km}^2$$
  *(Note: Limits are configurable architecture design constraints based on 10m raster memory ceilings; they are not claimed as fully benchmarked stress limits).*
- **FR-2.2 [Area Projection Standard]:** Area calculations shall be performed by projecting input WGS84 geometries into an equal-area projection or local UTM projection (e.g., EPSG:32644 for Lucknow) to eliminate latitude-dependent distortion.
- **FR-2.3 [Topological Validity]:** The system shall reject invalid geometries, including self-intersecting rings, polygons with duplicate vertices, open rings, or MultiPolygons containing disconnected disjoint regions larger than $100\text{ km}^2$.
- **FR-2.4 [Vertex Count Ceiling]:** The system shall enforce a configurable maximum vertex count (default $\le 500$ vertices) to prevent denial-of-service via overly complex boundary paths.
- **FR-2.5 [Global Coordinate Envelope]:** All longitude coordinates must strictly reside in $[-180.0, +180.0]$ and latitudes in $[-90.0, +90.0]$.

### Module 3: Spectral Processing & NDWI Segmentation (FR-3)
- **FR-3.1 [Index Formulation]:** The system shall compute NDWI strictly according to McFeeters (1996):
  $$\text{NDWI} = \frac{\rho_{\text{B03}} - \rho_{\text{B08}}}{\rho_{\text{B03}} + \rho_{\text{B08}}}$$
- **FR-3.2 [Numerical Stability]:** The system shall handle zero or near-zero denominators ($|\text{B03} + \text{B08}| \le 10^{-6}$) by masking those pixels as invalid, preventing floating-point `ZeroDivisionError` or infinite values.
- **FR-3.3 [Value Clamping]:** For all valid pixels, computed NDWI values must be clamped to the theoretical physical domain $[-1.0, +1.0]$. Invalid, saturated, or nodata pixels shall evaluate to IEEE 754 `NaN`.
- **FR-3.4 [Water Segmentation Threshold]:** Pixels shall be classified as water if $\text{NDWI} > \tau$, where $\tau$ is a configurable threshold (default $\tau = 0.00$). The system shall support threshold tuning in the range $[-0.30, +0.30]$.
- **FR-3.5 [Spatial Co-Registration]:** Both temporal rasters ($T_1$ and $T_2$) must be aligned to the identical spatial grid, resolution ($10\text{ m}$), and extent before classification.

### Module 4: Multi-Temporal Change Detection (FR-4)
- **FR-4.1 [Common Valid Pixel Domain]:** Surface water comparisons shall evaluate exclusively across pixels that are valid on *both* observation dates:
  $$\text{Domain}_{\text{comparison}} = \text{Valid}_{T_1} \land \text{Valid}_{T_2}$$
- **FR-4.2 [Categorical Transition Scheme]:** The system shall output a spatial transition matrix with four discrete classes:
  - Class 0: Non-Water on both dates.
  - Class 1: Perennial Water (Water on both $T_1$ and $T_2$).
  - Class 2: Apparent Water Recession / Loss (Water at $T_1$, Non-Water at $T_2$).
  - Class 3: Apparent Water Expansion / Gain (Non-Water at $T_1$, Water at $T_2$).
  - Class 255: Invalid / NoData on either date.
- **FR-4.3 [Quantitative Area Metrics]:** The system shall compute:
  - Total valid comparison area ($\text{m}^2$ and hectares).
  - Water extent at $T_1$ and $T_2$ ($\text{m}^2$, hectares, and pixel counts).
  - Absolute surface area difference: $\Delta A = A_{T_2} - A_{T_1}$.
  - Percentage change relative to baseline: $\Delta A\% = (\Delta A / A_{T_1}) \times 100$, with explicit handling when $A_{T_1} = 0$.
- **FR-4.4 [Scientific Limitation Disclaimer]:** Every output manifest, visualization, and report must embed the scientific limitation statement: surface area variations indicate inundation footprint changes caused by seasonal monsoon cycles, dam regulation, and morphology, and do not independently establish chemical pollution or permanent desiccation.

### Module 5: Authentication & Authorization (FR-5)
- **FR-5.1 [Identity Delegation]:** User registration, password authentication, and session issuance shall be delegated to Supabase Auth. Profiles are auto-synchronized into the `profiles` table upon verified JWT presentation with non-negative quotas. *(Implemented in Phase 2.2B2)*
- **FR-5.2 [JWT Verification]:** The FastAPI backend shall validate the authenticity, signature (JWKS/RS256/ES256 or secret/HS256), expiration (`exp`), audience (`aud`), and issuer (`iss`) of incoming Bearer JWT tokens via `verify_supabase_jwt`. *(Implemented in Phase 2.2B2)*
- **FR-5.3 [Data Ownership & Isolation]:** Every analysis request shall bind to the authenticated user's UUID (`sub` claim). Users shall access only their own records and public AOIs, enforced by PostgreSQL Row-Level Security (RLS) with transaction-local session identity propagation (`set_config`). Child records (`water_metrics`, `analysis_artifacts`) inherit ownership restrictions from parent runs. *(Implemented in Phase 2.2B2)*
- **FR-5.4 [Zero Secrets in Client]:** No database master passwords, service role keys, or external satellite provider passwords shall be bundled into frontend assets or source repositories. *(Implemented)*

### Module 6: Storage & Output Retention (FR-6)
- **FR-6.1 [Relational Metadata Store]:** PostgreSQL with PostGIS shall store user profiles, AOI geometries, analysis execution records, and quantitative area statistics.
- **FR-6.2 [Object Storage Hierarchy]:** Supabase Storage buckets shall manage file assets partitioned by user UUID and analysis ID:
  - `rasters/{user_id}/{analysis_id}/`: Clipped band GeoTIFFs and binary water masks.
  - `maps/{user_id}/{analysis_id}/`: High-resolution PNG figures.
  - `reports/{user_id}/{analysis_id}/`: Generated PDF and CSV files.
- **FR-6.3 [90-Day Retention Policy]:** Intermediate clipped rasters and binary mask files in `rasters/` shall be scheduled for automated lifecycle purge after 90 days. Summary metrics, metadata records, and generated PDF/CSV reports shall be retained indefinitely until explicitly deleted by the user.
- **FR-6.4 [Scratch Isolation]:** Temporary scratch directories used during processing shall be located in local ephemeral storage and cleaned immediately upon task completion.

### Module 7: Reporting & Export (FR-7)
- **FR-7.1 [Report Provenance]:** All numerical values in generated reports must originate directly from the immutable analysis manifest (`phase1_feasibility_report.json` or database run record). Hardcoded or fabricated values are strictly prohibited.
- **FR-7.2 [CSV Report Specification]:** The CSV report shall provide a structured machine-readable document containing metadata headers (Analysis ID, AOI coordinates, acquisition dates, tile IDs, data provider) followed by quantitative metrics (pixels, $\text{m}^2$, hectares, persistent channel, loss, gain, percentage change).
- **FR-7.3 [PDF Report Specification]:** The PDF report shall provide a formal, publication-ready multi-page document incorporating the project title, evaluator attribution, executive KPI table, embedded high-resolution cartographic figures (synoptic panel and categorical transition map), spectral index formulation, and the mandatory scientific disclaimer.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Performance Targets
The following operational targets are specified for Phase 2. Target statuses are explicitly categorized as **VERIFIED IN PHASE 1** or **PROPOSED FOR PHASE 2 (REQUIRES BENCHMARKING)**:

| Performance Metric | Proposed Target | Phase 1 Status | Verification Plan / Methodology |
| :--- | :---: | :---: | :--- |
| **Dashboard Initial Load** | $< 3.0\text{ s}$ | **Verified** | Measured via Streamlit local HTTP health check ($< 1.5\text{ s}$). |
| **Normal REST API Latency** | $< 500\text{ ms}$ | **Proposed** | To be benchmarked with Locust/k6 against FastAPI endpoints. |
| **Satellite STAC Discovery** | $< 15.0\text{ s}$ | **Verified** | CDSE STAC search for 100 items executes in $2.8–6.5\text{ s}$. |
| **End-to-End Analysis (25 km²)**| $< 60.0\text{ s}$ | **Verified** | Lucknow Gomti AOI ($132\text{ km}^2$) executes in $12–28\text{ s}$ via COG HTTP range requests. |
| **Report Generation (PDF/CSV)**| $< 10.0\text{ s}$ | **Proposed** | Requires benchmark upon integrating ReportLab / WeasyPrint pipeline. |
| **Memory Footprint (25 km² AOI)**| $< 2.0\text{ GB RAM}$ | **Proposed** | Phase 1 peak usage observed at ~450 MB; formal 25 km² stress testing required. |

*Disclaimer: Targets marked "Proposed" represent engineering criteria; they must not be reported as validated until formal benchmark scripts are executed in Phase 2.2.*

### 5.2 Security & Data Protection
- **NFR-SEC-1:** All network traffic between client, backend, and external gateways shall use TLS 1.3 (HTTPS).
- **NFR-SEC-2:** Bearer tokens shall expire within 3600 seconds (1 hour) with automatic refresh token rotation managed by Supabase Auth.
- **NFR-SEC-3:** Passwords, API keys, and database connection strings shall be loaded exclusively via environment variables (`.env`) and excluded from version control via `.gitignore`.
- **NFR-SEC-4:** Input geometries must be strictly sanitized to prevent SQL injection or GDAL/PROJ buffer overflow attacks.

### 5.3 Scientific & Cartographic Integrity
- **NFR-SCI-1:** Spectral calculations must maintain full 32-bit floating-point precision throughout array operations before final reporting.
- **NFR-SCI-2:** All exported map figures must embed standardized graphical scale bars, north orientation arrows, coordinate ticks, color-blind accessible legends, and unambiguous data provenance labels.

### 5.4 Maintainability & Compatibility
- **NFR-MAINT-1:** Python runtime environment shall target Python 3.11 with explicit PROJ database path initialization to prevent system GDAL/PostGIS library collisions on Windows.
- **NFR-MAINT-2:** Automated test suite must maintain $\ge 90\%$ branch coverage across all core scientific calculation modules.

---

## 6. External Interface Requirements

### 6.1 REST API Endpoints (FastAPI Blueprint)
- `POST /api/v1/auth/verify`: Validates JWT token and returns authenticated user context.
- `POST /api/v1/aoi/validate`: Accepts GeoJSON polygon, validates geometry, checks area ($0.1–100\text{ km}^2$), and returns centroid/bounding box.
- `POST /api/v1/analysis/search`: Queries satellite STAC catalog for candidate Sentinel-2 scene pairs over the validated AOI.
- `POST /api/v1/analysis/run`: Dispatches asynchronous analysis job; returns `job_id`.
- `GET /api/v1/analysis/{job_id}/status`: Polls progress, status (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`), and live logs.
- `GET /api/v1/analysis/{job_id}/results`: Returns complete JSON metrics payload.
- `GET /api/v1/analysis/{job_id}/export/csv`: Streams formatted CSV report.
- `GET /api/v1/analysis/{job_id}/export/pdf`: Streams publication-grade PDF document.

---

## 7. Compliance & Sign-Off Criteria for Phase 2.1
- [x] Full backward compatibility with Phase 1 pipeline (`main.py`, `src/`).
- [x] No disruption to existing 22 automated test cases.
- [x] Clear demarcation between verified Phase 1 metrics and proposed Phase 2 targets.
- [x] Formal approval of requirements traceability and technical decision records.
