# DharaScope: Automated Satellite-Based Surface Water Dynamics Monitoring Platform
## Final Academic Capstone Project Presentation (15 Slides)

**Candidate:** DharaScope Engineering & Science Team  
**Degree / Program:** B.Tech. Computer Science & Engineering (Capstone Evaluation)  
**Session:** November 2026  
**Repository:** `https://github.com/Akshat-2923/END_SEM_PROJECT_AKSHAT_3274`  
**License:** MIT License  

---

### Slide 1: Title & Project Overview

```
========================================================================================
                                      DharaScope
         Automated Satellite-Based Surface Water Dynamics Monitoring Platform
========================================================================================
   An Enterprise Geospatial Information System (GIS) for Multi-Temporal Water Change
                       Detection Using Copernicus Sentinel-2
```

- **Project:** DharaScope — End-to-End Earth Observation Web GIS
- **Core Technology:** Copernicus Sentinel-2 Level-2A, McFeeters NDWI, FastAPI, PostgreSQL 16 + PostGIS 3.6, React 19 + Leaflet
- **Target Application:** Automated, reproducible surface water monitoring across alluvial and urbanized river networks
- **Study Area:** Urban Gomti River Study Reach, Lucknow, Uttar Pradesh, India

*Speaker Notes:*  
"Good morning, esteemed panel members and evaluators. Today, we present DharaScope, an automated, production-grade geospatial platform designed to bridge raw satellite Earth Observation data from the European Space Agency's Sentinel-2 constellation directly to an interactive, secure web GIS workstation for surface water dynamics monitoring."

---

### Slide 2: Problem Statement

- **Hydrological Extremes & Seasonality:** In monsoonal river networks, peak monsoon bankfull flows alternate with severe post-monsoon and winter recessions, impacting drinking water security and flood vulnerability.
- **Limitations of Conventional In-Situ Monitoring:**
  - *Spatial Sparsity:* River gauging stations are separated by tens or hundreds of kilometers, leaving vast floodplain reaches and dynamic wetlands unmonitored.
  - *Data Latency:* Gauge data is often proprietary, manually logged, or published with significant administrative latency.
- **The Earth Observation Data Bottleneck:**
  - While satellite data is openly available, a single Sentinel-2 granule is $\sim 500\text{ MB}$ to $1\text{ GB}$ ($10,980 \times 10,980\text{ pixels}$).
  - Downloading entire multi-band tiles across multi-temporal dates to inspect a localized $5\text{ km}^2$ reach consumes gigabytes of redundant bandwidth and excessive server RAM.
- **Lack of Integrated Multi-Tenant Systems:** Existing tools are either heavyweight desktop software (QGIS, ArcGIS) requiring specialized training, or closed cloud scripts lacking row-level database security and reproducible reporting.

*Speaker Notes:*  
"The fundamental problem in surface water monitoring is the spatial gap left by sparse in-situ gauges, combined with the engineering bottleneck of downloading gigabytes of satellite imagery just to monitor a localized river segment. DharaScope was engineered to make high-resolution Earth Observation automated, sub-granule, and accessible."

---

### Slide 3: Project Objectives & Scope

1. **Interactive Vector Digitization:** Allow users to digitize arbitrary polygon AOIs up to $100\text{ km}^2$ with real-time topological validation (`ST_IsValid`, `ST_Area`).
2. **Automated STAC Discovery:** Standardize multi-temporal satellite scene search via SpatioTemporal Asset Catalog (STAC) protocols with cloud cover filtering.
3. **Windowed Sub-Granule COG Streaming:** Implement byte-range HTTP streaming via GDAL Virtual File Systems (`/vsicurl/`) to extract only the required spectral bands over the AOI window, reducing data transfer by $>99\%$.
4. **Calibrated Spectral Processing:** Compute McFeeters NDWI at native 10m spatial resolution with zero-division protection and valid-data masking.
5. **Categorical 4-Class Change Detection:** Quantify water transitions into Permanent Water, Water Inundation, Water Recession, and Persistent Land.
6. **Multi-Tenant Database Isolation:** Enforce defense-in-depth isolation using PostgreSQL Row-Level Security (RLS) driven by Supabase JWT bearer claims.
7. **Automated Publication Reporting:** Programmatically compile 300 DPI publication cartography, transition tables, and analytical metadata into downloadable PDF and CSV reports.

*Speaker Notes:*  
"We defined seven rigorous, measurable objectives spanning front-end digitization, sub-granule satellite streaming, spectral calculation, transition modeling, database security, and automated report generation—all strictly bound to an operational limit of 100 square kilometers."

---

### Slide 4: Existing Approaches vs. Proposed Solution

| Evaluation Metric | Traditional In-Situ Gauging | Manual Desktop GIS (QGIS) | Proposed Solution: DharaScope |
| :--- | :--- | :--- | :--- |
| **Spatial Coverage** | Point-based (sparse gauges) | Synoptic (manual scenes) | **Synoptic & continuous (automated)** |
| **Data Ingestion** | Manual physical inspection | Full granule download ($>500\text{ MB}$) | **Windowed COG streaming ($\sim 88\text{ KB}$)** |
| **Spatial Resolution** | Zero spatial extent | 10m (Sentinel-2) | **10m native Ground Sampling Distance** |
| **Workflow Automation** | Manual logging & entry | Manual multi-step desktop GIS | **Fully automated via asynchronous API** |
| **Multi-User Security** | N/A (spreadsheets/paper) | None (single desktop user) | **PostgreSQL Row-Level Security (RLS)** |
| **Reporting** | Static tabular logs | Manual layout export | **Programmatic 300 DPI PDF & CSV** |

*Speaker Notes:*  
"Compared to manual desktop GIS workflows that require downloading 500 MB tiles for every analysis, DharaScope extracts only the spatial window covering the user's AOI in seconds, wrapping the entire scientific pipeline in a multi-tenant web application."

---

### Slide 5: System Architecture & Data Flow

```
+---------------------------------------------------------------------------------+
|                         PRESENTATION TIER (Browser Client)                      |
|                  React 19 + TypeScript + Vite + Leaflet Web GIS                 |
+----------------------------------------+----------------------------------------+
                                         | HTTPS / Bearer JWT (Supabase Auth)
+----------------------------------------v----------------------------------------+
|                          APPLICATION SERVICE TIER (FastAPI)                     |
|           - /api/v1/auth (JWT Verify)       - /api/v1/aois (Spatial BBOX)       |
|           - /api/v1/analyses (Workflows)    - /reports (PDF & CSV Downloads)    |
|           - Asynchronous In-Process Background Task Execution Core             |
+-------------------+------------------------------------+------------------------+
                    |                                    |
+-------------------v-------------------+    +-----------v------------------------+
|        SPATIAL PERSISTENCE TIER       |    |      SATELLITE PROCESSING CORE     |
|      PostgreSQL 16 + PostGIS 3.6      |    |   - STAC Discovery (CDSE / AWS)    |
|   - Row-Level Security (RLS Engine)   |    |   - GDAL /vsicurl/ COG Streamer    |
|   - Spatial GiST Indices (idx_geom)   |    |   - McFeeters NDWI Engine (B03/B08)|
|   - Strict Foreign Key Cascades       |    |   - 4-Class Transition Matrix      |
|   - Profiles, AOIs, Runs, Artifacts   |    |   - ReportLab 300 DPI PDF Engine   |
+---------------------------------------+    +------------------------------------+
```

- **Separation of Concerns:** Client rendering, application business logic, spatial relational persistence, and Earth Observation processing are strictly decoupled.
- **Reference:** For the complete architectural specification and component interaction diagrams, see [docs/ARCHITECTURE.md](file:///d:/Coding/Projects/DharaScope/docs/ARCHITECTURE.md).

*Speaker Notes:*  
"The system follows a multi-tier decoupled topology. The React client communicates with the FastAPI service layer via authenticated REST endpoints. FastAPI manages background task dispatch, invokes the scientific processing core, and persists geometries and run metadata in PostgreSQL 16 with PostGIS 3.6."

---

### Slide 6: Technology Stack & Implementation Details

```
+---------------------------------------------------------------------------------------+
|  Tier               Technology               Version        Role                      |
+---------------------------------------------------------------------------------------+
|  Frontend           React                    19.0.0         UI component framework    |
|                     TypeScript               5.7.0          Compile-time type safety  |
|                     Vite                     7.3.1          HMR & production bundler  |
|                     Leaflet / React-Leaflet  1.9.4          Cartographic canvas       |
|  Backend            FastAPI                  0.115.6        ASGI asynchronous web API |
|                     Pydantic                 2.10.0         Request/response schemas  |
|                     SQLAlchemy               2.0.36         Object-relational mapping |
|  Database           PostgreSQL               16.15          Relational spatial engine |
|                     PostGIS                  3.6.2          Spatial geometries & GiST |
|  Science Core       Rasterio / GDAL          1.4.3          Windowed COG /vsicurl/    |
|                     NumPy                    2.2.1          Vectorized array math     |
|                     Matplotlib               3.10.0         300 DPI cartography       |
|                     ReportLab                4.4.7          Publication PDF engine    |
+---------------------------------------------------------------------------------------+
```

- **Zero Heavyweight Client Dependencies:** All heavy geospatial processing is handled server-side; the client remains a lightweight, responsive browser application.

*Speaker Notes:*  
"Our technology stack leverages modern open-source foundations: React 19 and Leaflet on the presentation tier, FastAPI and SQLAlchemy on the service tier, PostgreSQL 16 with PostGIS 3.6 for spatial storage, and Rasterio/GDAL C-bindings for sub-granule raster extraction."

---

### Slide 7: Database Design & Multi-Tenant Security

- **Relational Spatial Schema (PostGIS 3.6):**
  - `profiles`: User identity, application role (`user`, `admin`), quota tracking.
  - `aois`: User-digitized spatial geometries (`GEOMETRY(POLYGON, 4326)`), GiST indexed, with check constraints enforcing $0.10 \le \text{Area} \le 100.00\text{ km}^2$ and vertex count $\le 500$.
  - `analysis_runs`: Run execution metadata, timestamps, scene IDs, status lifecycle (`PENDING` $\to$ `RUNNING` $\to$ `SUCCESS`/`FAILED`).
  - `water_metrics`: Quantitative analytical metrics (water areas in ha, % change, transition pixel counts).
  - `analysis_artifacts`: File metadata, retention expiry (90 days), and storage paths (decoupled from database binary storage).
- **Defense-in-Depth Row-Level Security (RLS):**
  - Every incoming request validates the Supabase JWT.
  - The connection pool sets transaction-local identity: `SET LOCAL app.current_user_id = '<uuid>';`.
  - Native PostgreSQL RLS policies restrict all table operations (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) to rows owned by the current tenant.
- **Authoritative Admin Role Check:**
  - Administrative endpoints verify roles directly against the database `profiles` table rather than relying solely on client JWT claims, ensuring instantaneous privilege revocation.

*Speaker Notes:*  
"Security is built from the database engine up. We enforce PostgreSQL Row-Level Security using transaction-local session propagation. Even if an API query omitted a user filter, PostgreSQL returns zero records for foreign tenant data. Admin actions verify privileges against the authoritative database profile, eliminating stale-JWT elevation."

---

### Slide 8: Satellite Data Retrieval: Windowed COG Streaming

- **The Traditional Bottleneck:**
  - Standard Sentinel-2 Level-2A product: Full zip archive $= 500\text{ MB} - 1\text{ GB}$.
  - Downloading two temporal granules requires $1.0 - 2.0\text{ GB}$ of bandwidth and minutes of wait time.
- **DharaScope's Windowed Streaming Architecture:**
  1. User digitizes a $4.40\text{ km}^2$ Area of Interest.
  2. STAC client queries AWS Open Data / CDSE catalogs for cloud-filtered scenes.
  3. Reprojects AOI bounding box into UTM Zone 44N (`EPSG:32644`).
  4. Rasterio `/vsicurl/` issues HTTP range GET requests targeting only the pixel tiles intersecting the AOI bounding box for Band 3 (Green) and Band 8 (NIR).
- **Performance Impact:**
  - **Data Transferred:** Reduced from $\sim 1\text{ GB}$ down to $\approx 88\text{ KB}$ per band.
  - **Network Transfer Reduction:** $> 99.9\%$ bandwidth savings.
  - **Latency:** Sub-granule window extraction completes in under $3\text{ seconds}$.

*Speaker Notes:*  
"By using Cloud-Optimized GeoTIFFs and GDAL's virtual file system, we make HTTP range requests to download only the few byte-ranges covering the user's bounding box. Instead of transferring a gigabyte, we transfer less than 100 kilobytes per band, executing in seconds."

---

### Slide 9: NDWI & Multi-Temporal Change Detection

- **McFeeters Normalized Difference Water Index (1996):**
  $$\text{NDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{NIR}}}{\rho_{\text{Green}} + \rho_{\text{NIR}}} = \frac{\text{Band 3} - \text{Band 8}}{\text{Band 3} + \text{Band 8}}$$
  - Native 10m Ground Sampling Distance (GSD) across both bands.
  - Zero-denominator protection: masked if $|\text{B03} + \text{B08}| \le 10^{-6}$.
  - Physical ratio clamped to $[-1.0, 1.0]$.
  - Classification threshold: $\text{Water} \iff \text{NDWI} > 0.00$ within valid mask.
- **4-Class Categorical Transition Modeling:**
  $$\text{Class Code} = 2 \cdot W_{T_1} + W_{T_2}$$

```
+------------+------------+--------------------+------------------------------------------+
|  W(T1)     |  W(T2)     |  Class Label       |  Hydrological / Environmental Meaning    |
+------------+------------+--------------------+------------------------------------------+
|  0 (Land)  |  0 (Land)  |  Persistent Land   |  Terrestrial soil, urban fabric, canopy  |
|  0 (Land)  |  1 (Water) |  Water Inundation  |  Apparent surface expansion / widening   |
|  1 (Water) |  0 (Land)  |  Water Recession   |  Apparent surface contraction / sandbars |
|  1 (Water) |  1 (Water) |  Permanent Water   |  Stable river thalweg, perennial pools   |
+------------+------------+--------------------+------------------------------------------+
```

- **Areal Quantification:** $\text{Area (ha)} = \text{Pixel Count} \times 10\text{m} \times 10\text{m} \times 10^{-4} = \text{Pixel Count} \times 0.01\text{ ha}$.

*Speaker Notes:*  
"We compute McFeeters NDWI at native 10-meter resolution using Band 3 and Band 8. Pixels with NDWI greater than zero are classified as water. By comparing binary masks between two dates, we generate a mutually exclusive, collectively exhaustive 4-class transition matrix."

---

### Slide 10: Application Demonstration (Workflow Stages)

The complete end-to-end user journey was verified on live servers across 8 workflow stages:

1. **Landing & Session Initialization:** Clean, dark scientific GIS workstation interface with real-time status telemetry.
   - Evidence: [01_initial_landing.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/01_initial_landing.png)
2. **Authenticated Session:** Secure Supabase login; token claims displayed in header.
   - Evidence: [02_authenticated_session.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/02_authenticated_session.png)
3. **Interactive AOI Validation:** Urban Gomti River Study Reach, Lucknow preset validated via backend PostGIS ($4.40\text{ km}^2$, simple polygon).
   - Evidence: [03_aoi_validated.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/03_aoi_validated.png)
4. **Satellite Scene Discovery:** Automated STAC discovery identifies clear Sentinel-2A granules for October 10 and December 9, 2023 (T44RMQ).
   - Evidence: [04_analysis_configured.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/04_analysis_configured.png)
5. **Pipeline Execution & Provenance:** Background worker executes in 18.4s; `REAL ORBITAL S2` badge rendered.
   - Evidence: [05_analysis_success_real_data.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/05_analysis_success_real_data.png)
6. **Metrics & Transitions Display:** Real-time KPI cards display $0.53\text{ ha} \to 1.66\text{ ha}$ ($+1.13\text{ ha}$, $+213.21\%$).
   - Evidence: [06_metrics_and_transitions.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/06_metrics_and_transitions.png)
7. **Cartographic Map Display:** High-resolution 4-panel comparison figure and transition maps rendered.
   - Evidence: [07_cartography_figures.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/07_cartography_figures.png)
8. **Report Downloads:** Download of 7.4 MB publication PDF and matching CSV data manifest.
   - Evidence: [08_report_downloads.png](file:///d:/Coding/Projects/DharaScope/outputs/validation_phase2_4/08_report_downloads.png)

*Speaker Notes:*  
"Here we see the 8 stages of the user experience, proven through live browser automation. The user selects the Urban Gomti River Study Reach, Lucknow, configures cloud thresholds, triggers the pipeline, inspects the 4-class categorical map, and downloads publication-grade PDF and CSV reports."

---

### Slide 11: Experimental Results: Urban Gomti River Study Reach Dynamics

```
Study Area: Urban Gomti River Study Reach, Lucknow, UP [80.90, 26.84, 80.92, 26.86]
Satellite: Sentinel-2A MSI Level-2A (UTM 44N / EPSG:32644, 10m GSD)
Observation T1: 2023-10-10 (0.0% Cloud Cover) | Observation T2: 2023-12-09 (0.0% Cloud Cover)
```

| Metric / Transition Category | Pixel Count | Area (Hectares) | Percentage of Total AOI |
| :--- | :---: | :---: | :---: |
| **Earlier Water Area ($T_1$, Oct 10)** | **53 px** | **$0.53\text{ ha}$** | **$0.12\%$** |
| **Later Water Area ($T_2$, Dec 09)** | **166 px** | **$1.66\text{ ha}$** | **$0.38\%$** |
| **Net Water Dynamics ($\Delta A$)** | **$+113\text{ px}$** | **$+1.13\text{ ha}$** | **$+213.21\%$** |
| **Perennial Channel Core (Persistent)** | 39 px | $0.39\text{ ha}$ | $0.09\%$ |
| **Water Inundation (Apparent Gain)** | 127 px | $1.27\text{ ha}$ | $0.29\%$ |
| **Water Recession (Apparent Loss)** | 14 px | $0.14\text{ ha}$ | $0.03\%$ |
| **Persistent Land (Terrestrial Urban)** | 43,799 px | $437.99\text{ ha}$ | $99.59\%$ |
| **Total Valid Overlapping Footprint** | **43,979 px** | **$439.79\text{ ha}$** | **$100.00\%$** |

- **Reconciliation of 44,178 vs 44,600 Pixels:**
  - $43,979\text{ pixels}$ represents the non-NoData common valid polygon footprint.
  - $44,178\text{ pixels}$ ($222 \times 199$) represents the truncated inner integer raster window.
  - $44,600\text{ pixels}$ ($223 \times 200$) represents the ceiling outer bounding box raster window.
  - **Invariant:** In all formulations, detected water pixels are strictly identical: 53 px at $T_1$, 166 px at $T_2$ ($+1.13\text{ ha}$ net gain).
- **Environmental Spatial Heterogeneity:**
  - *Regional Basin ($132.30\text{ km}^2$, Phase 1):* $184.56\text{ ha} \to 139.33\text{ ha}$ ($-45.23\text{ ha}$, $-24.51\%$) across drying agricultural floodplains.
  - *Urban Gomti Reach ($4.40\text{ km}^2$, Phase 2.4):* $0.53\text{ ha} \to 1.66\text{ ha}$ ($+1.13\text{ ha}$, $+213.21\%$) along the confined city riverfront.
  - Divergent directions of change reflect distinct landscape zones, not an aggregation artifact.

*Speaker Notes:*  
"In our operational study area, the Urban Gomti River Study Reach in Lucknow, detected surface water increased from 0.53 ha (53 pixels) to 1.66 ha (166 pixels), a net gain of 1.13 ha (+113 pixels, +213.21%). The transition breakdown reveals 0.39 ha of perennial channel core, 1.27 ha of inundation expansion, and 0.14 ha of seasonal recession, surrounded by 437.99 ha of persistent land. Crucially, whether evaluating the 43,979 valid polygon pixels, the 44,178 inner window, or the 44,600 outer window, the detected water pixels are strictly invariant. Furthermore, the divergence from regional feasibility results illustrates environmental spatial heterogeneity across diverse landscape zones."

---

### Slide 12: Testing, Quality Assurance & Security

- **Automated Verification Harness (185/185 Executed Passed, 1 Skipped):**
  - **Backend Pytest Suite:** 185 passed, 1 skipped (live CDSE credential check) across 16 test modules.
  - **Frontend Vitest Suite:** 18 passed across 6 test suites.
  - **Total Automated Tests:** **203 automated test cases (185/185 executed backend passed, 1 skipped; 18/18 frontend passed)**.
- **Static Code Analysis & Compilation:**
  - **Oxlint:** 0 errors across 26 TypeScript/TSX files.
  - **Vite Production Build:** Completed in 5.97s with zero bundle errors.
- **Security & Authorization Rigor:**
  - Zero development signing secrets enter production bundles (`import.meta.env.DEV` guards).
  - PostgreSQL Row-Level Security verified: Cross-tenant AOI and run leakage rejected at database engine level.
  - Revoked admin access verified: Database role check blocks stale JWT administrative access immediately (HTTP 403).

*Speaker Notes:*  
"The platform has been validated through 203 automated tests spanning unit, integration, and security assertions, alongside static linting with Oxlint and headless browser testing with Playwright. Every security boundary—including RLS tenant isolation and immediate admin revocation—is verified by regression tests."

---

### Slide 13: System Limitations & Scientific Boundaries

To ensure scientific defensibility, we explicitly document the system's operational and physical limitations:

1. **Optical Cloud Contamination:** Sentinel-2 MSI cannot penetrate cloud cover. Operational monitoring during monsoon peak months (July–August) requires radar (SAR / Sentinel-1) integration.
2. **Spatial Resolution Limits (10m GSD):** Narrow water bodies ($< 10\text{ m}$ wide), shallow field ditches, and small farm ponds ($< 100\text{ m}^2$) cannot be cleanly resolved without sub-pixel spectral unmixing.
3. **Planar Extent vs. Bathymetry:** NDWI measures two-dimensional surface reflectance presence; it does NOT measure water depth, velocity, discharge, or volumetric capacity.
4. **Attribution Boundary (No In-Situ Gauging):** Satellite Earth observation detects surface reflectance changes. Without ground-truth in-situ stream gauge hydrographs and official barrage gate operational records, local hydraulic causes cannot be proven.
5. **Operational AOI Size Cap ($100\text{ km}^2$):** Enforced to ensure memory bounds ($< 500\text{ MB}$) on single-node processing workers.

*Speaker Notes:*  
"We maintain strict scientific transparency regarding limitations. Satellite remote sensing measures two-dimensional optical surface reflectance, not river volume or depth. Furthermore, during heavy monsoon cloud cover, optical sensors are blinded, and without in-situ gauging records, we report observed reflectance changes rather than claiming proven hydraulic causes."

---

### Slide 14: Future Scope & Roadmap

1. **Radar-Optical Fusion (Sentinel-1 SAR):**
   - Ingest Sentinel-1 C-band Synthetic Aperture Radar (SAR) Ground Range Detected (GRD) rasters.
   - Enable all-weather, cloud-penetrating flood detection during peak monsoonal storm events.
2. **Automated Dynamic Thresholding (Otsu Algorithm):**
   - Implement automated bimodal histogram thresholding to adjust the NDWI decision boundary dynamically for turbid, sediment-laden river flows.
3. **Sub-Pixel Spectral Unmixing & Deep Learning:**
   - Deploy lightweight convolutional/transformer segmentation models (e.g., U-Net, SegFormer) to quantify fractional water coverage in boundary pixels along riverbanks.
4. **Distributed Task Queue & Cloud Storage:**
   - Migrate in-process workers to Celery and Redis with horizontal auto-scaling.
   - Configure S3 / Supabase Storage buckets for multi-region raster caching.

*Speaker Notes:*  
"Our immediate research trajectory focuses on multi-sensor fusion: integrating Sentinel-1 Synthetic Aperture Radar to provide cloud-penetrating water detection during peak monsoon flooding, alongside automated dynamic thresholding for turbid waters."

---

### Slide 15: Conclusion & Summary

```
========================================================================================
                                      CONCLUSION
========================================================================================
```

- **Mission Accomplished:** Delivered an open-source, reproducible, production-grade geospatial platform for automated river surface water monitoring.
- **Core Engineering Innovation:** Replaced gigabyte-scale tile downloads with windowed Cloud-Optimized GeoTIFF streaming ($> 99.9\%$ bandwidth savings).
- **Core Scientific Contribution:** Demonstrated that localized urban channel dynamics ($+1.13\text{ ha}$) and regional floodplain recession ($-45.23\text{ ha}$) reflect environmental spatial heterogeneity across diverse geomorphic zones.
- **Enterprise Security:** Demonstrated that modern web GIS platforms can enforce multi-tenant isolation via native PostgreSQL Row-Level Security and cryptographic JWT validation.
- **Evaluation Readiness:** 185/185 executed backend tests passed (1 live CDSE test skipped), 18/18 frontend tests passed (203 total passing tests), live browser demonstration validated, full academic report and documentation suite published, and repository synchronized with GitHub.

**Thank you. We welcome questions from the examination committee.**

---

*Academic Documentation Links:*  
- Project Report: [docs/PROJECT_REPORT.md](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md)  
- Architecture Specification: [docs/ARCHITECTURE.md](file:///d:/Coding/Projects/DharaScope/docs/ARCHITECTURE.md)  
- Scientific Methodology: [docs/SCIENTIFIC_METHODOLOGY.md](file:///d:/Coding/Projects/DharaScope/docs/SCIENTIFIC_METHODOLOGY.md)  
- Judge Q&A Guide: [docs/JUDGE_QA.md](file:///d:/Coding/Projects/DharaScope/docs/JUDGE_QA.md)  
- Evaluator Demonstration Guide: [docs/DEMO_GUIDE.md](file:///d:/Coding/Projects/DharaScope/docs/DEMO_GUIDE.md)  
