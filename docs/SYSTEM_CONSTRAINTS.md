# System Constraints, Scientific Boundaries & Performance Targets
## DharaScope: Satellite-Based River Surface Water Dynamics Platform

**Document Version:** 2.1.0  
**Status:** Approved Reference  
**Scope:** Phase 2 Architecture & Operational Limits  

---

## 1. Physical & Remote-Sensing Constraints

### 1.1 Sensor & Spatial Resolution Boundaries
- **Native Ground Sampling Distance (GSD):** Sentinel-2 MSI Bands 3 (Green) and 8 (NIR) operate at a native spatial resolution of $10.0\text{ m} \times 10.0\text{ m}$ ($100\text{ m}^2$ per pixel).
- **Sub-Pixel Detection Limits:** Tributaries, irrigation off-takes, and narrow stream channels with surface widths $< 15–20\text{ m}$ (less than 2 full pixels) are subject to severe mixed-pixel edge effects where shoreline vegetation or dry sand dominates the spectral signature.
- **Spectral Signal Mixing:** Shoreline edge pixels represent a mixture of open water reflectance and terrestrial reflectance (riparian grass, concrete revetments, alluvial sand). While sub-pixel spectral unmixing is mathematically possible, DharaScope Phase 2 intentionally restricts analysis to discrete binary pixel classification ($\text{NDWI} > \tau$) to preserve computational transparency and avoid uncalibrated model assumptions.

### 1.2 Atmospheric & Meteorological Constraints
- **Optical Cloud Blockage:** Sentinel-2 is a passive optical sensor operating in the visible and near-infrared spectrum ($\lambda \in [400\text{ nm}, 2200\text{ nm}]$). It cannot penetrate dense cloud cover, convective thunderheads, or heavy atmospheric haze.
- **Monsoon Window Limitations:** In northern India (including Uttar Pradesh), heavy monsoon cloud cover persists from late June through early September. During this period, optical satellite observations frequently exhibit $80–100\%$ scene cloud coverage. Consequently, reliable surface water monitoring must focus on:
  - Post-monsoon bankfull stabilization (October–November).
  - Dry winter baseflow (December–February).
  - Pre-monsoon minimum discharge (April–May).
- **Cirrus & Cloud Shadow Artifacts:** Thin cirrus clouds and cloud shadows across river channels can depress optical reflectances and lead to false water classifications or spurious nodata masks. The pipeline rejects candidate scenes with scene cloud cover $> 10\%$ by default.

### 1.3 Hydrological & Hydrodynamic Constraints
- **Inundation Footprint vs. Volumetric Discharge:** Differences in NDWI-based surface water area measure the **two-dimensional surface water footprint (inundation area)**. They do **not** independently measure:
  - Three-dimensional river depth or volumetric discharge ($\text{m}^3/\text{s}$).
  - Sub-surface groundwater table recharge.
  - Bathymetric channel capacity changes without in-situ cross-sectional acoustic surveys.
- **Anthropogenic River Flow Regulation:** River stages along the Gomti River through Lucknow are actively manipulated by the **Gaughat Barrage** and city water supply withdrawals. Apparent surface water recession between October and December reflects both natural post-monsoon baseflow decline and human barrage gate operations.
- **Environmental Quality Disclaimer:** NDWI is an index of surface water reflectance, **not** an indicator of biochemical contamination, biological oxygen demand (BOD), fecal coliform levels, or industrial heavy metal pollution. Reductions in water area must never be conflated with chemical river pollution.

---

## 2. Geographical & Spatial AOI Constraints

### 2.1 Area of Interest (AOI) Bounds
To ensure robust numerical stability and adhere to single-node memory ceilings, user-submitted AOIs are strictly bounded:

$$0.10\text{ km}^2 \le \text{Area}_{\text{AOI}} \le 100.00\text{ km}^2$$

- **Lower Boundary ($0.10\text{ km}^2 = 100,000\text{ m}^2 = 1,000\text{ pixels}$):** Below this threshold, 10m pixel granularity produces excessive statistical variance where single-pixel classification shifts cause disproportionate percentage swings.
- **Upper Boundary ($100.00\text{ km}^2 = 100,000,000\text{ m}^2 = 1,000,000\text{ pixels}$):** Restricts the maximum array dimensions to approximately $1000 \times 1000$ elements, ensuring memory footprint stays under $500\text{ MB}$ per analysis run on a single worker node.
- **Configurability:** Bounds are governed by `MIN_AOI_AREA_KM2` and `MAX_AOI_AREA_KM2` environment variables in `src/config.py`.

### 2.2 Boundary Complexity & Topology Limits
- **Maximum Vertex Count:** Polygons must contain $\le 500$ vertices to prevent computational bottlenecks during geometry intersection calculations and raster masking.
- **Geometric Topology:** Self-intersecting polygons, polygons with holes that invert geometry, and disconnected MultiPolygons exceeding the cumulative $100\text{ km}^2$ bound are rejected.
- **Equal-Area Projection Rule:** Geometric area calculations must be performed in equal-area projections (e.g., Albers Equal Area or local UTM Zone 44N EPSG:32644) rather than planar calculations in geographic coordinates (EPSG:4326), which distort areas away from the equator.

---

## 3. Performance Targets & Benchmark Verification Status

The table below documents all operational performance targets for DharaScope. Each target is explicitly designated as **VERIFIED IN PHASE 1** (empirically measured on existing code) or **PROPOSED FOR PHASE 2 (REQUIRES BENCHMARKING)** (engineering criteria to be validated via formal benchmark tests in Phase 2.2):

| System Operation | Performance Target | Current Verification Status | Measured Baseline / Verification Evidence |
| :--- | :---: | :---: | :--- |
| **GIS Dashboard Initial Load** | $< 3.0\text{ s}$ | **VERIFIED** | Streamlit headless local instance responds HTTP 200 within **$1.1–1.4\text{ s}$**; health check `/_stcore/health` returns `ok` in $< 50\text{ ms}$. |
| **REST API Normal Endpoints** | $< 500\text{ ms}$ | **PROPOSED** | Target for FastAPI endpoints (`/api/v1/aoi/validate`, `/status`); requires synthetic load benchmarking in Phase 2.2. |
| **STAC Satellite Discovery** | $< 15.0\text{ s}$ | **VERIFIED** | `src/stac_client.py` queries CDSE STAC across 23 candidate scenes in **$2.8–6.5\text{ s}$** over broadband internet. |
| **End-to-End Analysis (25 km²)** | $< 60.0\text{ s}$ | **VERIFIED** | Lucknow Gomti study area ($132.3\text{ km}^2$, exceeding 25 km² target) executes complete pipeline in **$12.4–28.1\text{ s}$** using AWS Open Data COG range requests. |
| **Report Generation (PDF/CSV)** | $< 10.0\text{ s}$ | **PROPOSED** | Target for compilation of 300 DPI figures and multi-page PDF; requires benchmark upon integrating ReportLab in Phase 2.2. |
| **Worker Peak RAM (25 km² AOI)** | $< 2.0\text{ GB RAM}$ | **PROPOSED** | Phase 1 peak Python process memory observed at **~$450\text{ MB}$** on $132\text{ km}^2$; formal concurrent multi-worker benchmark required in Phase 2.2. |

> [!IMPORTANT]
> **Benchmarking Integrity Notice:** The targets marked *Proposed* represent active architecture design specifications. DharaScope team members must never report proposed targets as empirical benchmark results in academic reviews until formal load-test scripts have executed under controlled test environments.

---

## 4. Computational & Memory Constraints

### 4.1 Numerical Precision & Memory Budget
- **Array Memory Footprint:** Each 10m single-band raster layer for a $100\text{ km}^2$ AOI requires:
  $$\text{Pixels} = \frac{100 \times 10^6\text{ m}^2}{100\text{ m}^2/\text{pixel}} = 1,000,000\text{ pixels}$$
  $$\text{Memory per Band (Float32)} = 1,000,000 \times 4\text{ bytes} \approx 3.81\text{ MB}$$
- Even with 6 concurrent layers allocated in RAM ($T_1\text{ B03}$, $T_1\text{ B08}$, $T_1\text{ NDWI}$, $T_2\text{ B03}$, $T_2\text{ B08}$, $T_2\text{ NDWI}$, plus classification masks and change matrix), the active raster data structure footprint remains $< 50\text{ MB}$.
- **Rasterio / GDAL Heap:** The dominant memory consumer is GDAL's internal block cache and Matplotlib's 300 DPI rendering engine (`src/visualization.py`), which allocates up to $300–450\text{ MB}$ during multi-panel figure generation.
- **Worker Concurrency Limit:** Single-node execution profiles must limit concurrent analysis jobs to 2–3 active pipelines per 4 GB RAM container to prevent out-of-memory (OOM) process termination.

### 4.2 Operating System & PROJ Database Conflicts
- On Windows operating systems with external GIS software installed (e.g., PostgreSQL with PostGIS or OSGeo4W), system environment variables `PROJ_LIB` and `PROJ_DATA` often point to mismatched PROJ database versions (e.g., PostGIS PROJ 8 vs Rasterio PROJ 9).
- **Mandatory Guard:** `src/config.py` enforces runtime isolation by explicitly setting `os.environ["PROJ_DATA"]` and `os.environ["PROJ_LIB"]` to `rasterio/proj_data` before GDAL or rasterio initialize. All entrypoints (`main.py`, `app.py`, `server.py`) must import `src.config` before any geospatial library.

---

## 5. Network & External Gateway Constraints

### 5.1 Copernicus Data Space Ecosystem (CDSE)
- **Token Lifespan:** CDSE Keycloak bearer tokens expire within 600 seconds (10 minutes) to 3600 seconds (1 hour). The downloader must implement automatic token renewal on HTTP 401 response.
- **OData Leaf Node Redirects:** CDSE OData asset downloads issue HTTP 302/303 redirects across trusted domains (`copernicus.eu`, `dataspace.copernicus.eu`, `cloudferro.com`, `creodias.eu`). The downloader uses `LocationTrustedSession` to preserve credentials across trusted redirect hops while stripping them if redirected to AWS S3 presigned URLs.
- **Rate Limiting:** Unauthenticated CDSE STAC requests are throttled at ~50 requests per minute. `CDSESTACClient` implements exponential backoff with retry on status codes 429, 500, 502, 503, and 504.

### 5.2 AWS Open Data Sentinel-2 COG Archive
- **S3 HTTP Range Throttling:** Rapid sequential byte-range requests can occasionally trigger HTTP 503 Slow Down responses from Amazon S3. The pipeline bundles range requests into consolidated spatial bounding windows to minimize request frequency.

---

## 6. Security, Credential & Data Isolation Constraints

### 6.1 Credential Boundaries
- No passwords, client secrets, API tokens, or database connection strings may be committed to version control.
- All secrets are loaded through local ignored environment files (`.env`) validated by `.gitignore`.
- User identity is verified statelessly via cryptographic JWT validation without storing user passwords in application memory.

### 6.2 Data Isolation & Row-Level Security Boundaries
- **Trust Boundary & Session Identity:** FastAPI connections authenticate as a dedicated application role (`dharascope_app`). Because PostgreSQL superusers bypass RLS, application connections switch to non-superuser context and bind verified user claims per transaction:
  ```sql
  SET LOCAL ROLE dharascope_app;
  SELECT set_config('request.jwt.claim.sub', :user_id, true);
  SELECT set_config('request.jwt.claim.role', :role, true);
  ```
- **Transaction Scope (`is_local = true`):** Claims are strictly scoped to the transaction boundary. When transactions commit or rollback, the claims reset automatically, preventing cross-tenant leakage across connection pools.
- **Child Record Inheritance:** Child tables (`water_metrics`, `analysis_artifacts`) inherit ownership restrictions from `analysis_runs` via correlated existence queries.
- **Anti-Privilege Escalation:** PostgreSQL RLS `WITH CHECK` policies prevent regular users from updating their `role` to `'admin'`.
- **90-Day Output Retention:** Intermediate raster files in the `rasters/` storage bucket are purged after 90 days to respect storage limits, while summary metrics and PDF reports are preserved permanently for academic auditability.
