# DharaScope: Comprehensive Evaluation & Technical Defense Q&A Guide
## Preparation Guide for Evaluators, Judges, and Academic Defense Panels

**Project:** DharaScope — Automated Satellite-Based Surface Water Dynamics Platform  
**Target Audience:** Capstone Examiners, Technical Judges, and Geospatial Peer Reviewers  
**Version:** 2.6.0 (Academic Defense Baseline)  
**Date:** November 2026  

---

## 1. Executive Presentations: 60-Second & 3-Minute Briefings

### The 60-Second Elevator Briefing (High-Level Overview)
> "Surface water bodies in monsoonal river networks fluctuate dramatically between flood and drought. Traditional river monitoring relies on physical stream gauges that are spaced dozens of kilometers apart, leaving massive stretches of floodplains completely unmonitored. 
> 
> Satellite data can solve this, but downloading massive 1-gigabyte satellite images for a localized 5-square-kilometer river reach is slow, expensive, and unscalable.
> 
> **DharaScope** is an automated web GIS platform that connects directly to the European Space Agency's Sentinel-2 satellite constellation. Instead of downloading full satellite scenes, our system uses Cloud-Optimized GeoTIFFs to stream only the exact pixels covering a user's digitized Area of Interest in seconds—reducing data transfer by over 99%. We calculate the Normalized Difference Water Index at 10-meter resolution, automatically detect water gains and losses, isolate each user's data using PostgreSQL Row-Level Security, and generate publication-quality PDF and CSV reports. 
> 
> On the Gomti River in Lucknow, we empirically proved that our platform detects real water dynamics accurately, safely, and reproducibly."

---

### The 3-Minute Technical Architecture Briefing (Engineering Panel)
> "Good morning, members of the evaluation committee. DharaScope was engineered as an enterprise-grade, open-source geospatial platform that operationalizes optical Earth Observation data into an automated web GIS workflow.
> 
> The platform addresses three fundamental bottlenecks in modern environmental remote sensing: data volume, multi-tenant security, and reproducible change analysis.
> 
> **First, on the data engineering front:** Traditional satellite processing requires ingesting full $100 \times 100\text{ km}$ Level-2A granules. DharaScope bypasses this by integrating a SpatioTemporal Asset Catalog (STAC) discovery client with GDAL Virtual File Systems (`/vsicurl/`). When a user digitizes an Area of Interest up to $100\text{ km}^2$, the system reprojects the polygon into the satellite's native UTM projection and issues HTTP byte-range GET requests to stream only Band 3 (Green) and Band 8 (NIR) at native 10-meter ground sampling distance. This achieves a greater than 99% reduction in network transfer, reducing gigabytes to tens of kilobytes.
> 
> **Second, on the scientific and spectral pipeline:** We compute McFeeters Normalized Difference Water Index (NDWI) with zero-division protection and $[-1.0, 1.0]$ physical domain clamping. A calibrated zero-threshold ($\text{NDWI} > 0.0$) segments water, followed by a 4-class multi-temporal transition matrix—quantifying Permanent Water, Water Inundation, Water Recession, and Persistent Land. On our urban Gomti River test reach, the system detected a net surface water expansion from $0.53\text{ ha}$ to $1.66\text{ ha}$ ($+1.13\text{ ha}$, $+213.21\%$) between October 10 and December 9, 2023. We verified that this localized channel expansion contrasts with regional floodplain recession ($-45.23\text{ ha}$) due to environmental spatial heterogeneity across diverse landscape zones. We strictly report observed planar surface reflectance changes and avoid unverified causal assertions without in-situ gauging.
> 
> **Third, on architecture and security:** The application is built on FastAPI, PostgreSQL 16 with PostGIS 3.6, and React 19 with Leaflet. We enforce defense-in-depth isolation using PostgreSQL native Row-Level Security (RLS) driven by Supabase JWT authentication, with connection-level session propagation (`SET LOCAL app.current_user_id`). Administrative endpoints verify privileges directly against the database `profiles` table to ensure instantaneous revocation. 
> 
> The platform is thoroughly validated: 203 automated tests passing with 100% success rate, automated Playwright headless browser verification against real orbital imagery, and automated compilation of 300 DPI publication PDF reports. Thank you."

---

## 2. Thirty Technical & Project Defense Questions and Answers

### Part A: Remote Sensing Physics & Satellite Data (Q1–Q6)

#### Q1: Why did you choose McFeeters NDWI over Xu's Modified NDWI (MNDWI)?
**Answer:**  
In the Sentinel-2 MultiSpectral Instrument (MSI), Band 3 (Green, 560 nm) and Band 8 (NIR, 842 nm) both operate at **native 10-meter Ground Sampling Distance (GSD)**. Xu's MNDWI substitutes the Near-Infrared band with Shortwave Infrared (SWIR, Band 11, 1610 nm). While SWIR can reduce false positives from built-up urban asphalt, Sentinel-2 Band 11 operates at **20-meter resolution**. Using MNDWI would have required spatial resampling or pan-sharpening, introducing spatial blur along narrow alluvial riverbanks. McFeeters NDWI preserves pure 10-meter edge delineation.

#### Q2: What are the physical spectral reflectance characteristics that allow NDWI to isolate water?
**Answer:**  
Liquid water strongly absorbs electromagnetic radiation in the near-infrared and shortwave-infrared spectra ($\rho_{\text{NIR}} < 1\%$), while reflecting moderately in blue and green optical wavelengths ($\rho_{\text{Green}} \approx 10\text{–}15\%$). Conversely, green vegetation exhibits high NIR reflectance ($40\text{–}60\%$) due to spongy mesophyll scattering, and bare soils reflect continuously across visible and NIR wavelengths. By computing $(\text{Green} - \text{NIR}) / (\text{Green} + \text{NIR})$, water bodies yield positive values ($\text{NDWI} > 0.0$), while terrestrial soil and vegetation yield negative values ($\text{NDWI} < 0.0$).

#### Q3: How does spatial resolution limit the detection of narrow water bodies?
**Answer:**  
At a 10-meter GSD, a single pixel covers $100\text{ m}^2$ on the ground. Boundary pixels along riverbanks contain a mixture of water, wet mud, and riparian vegetation—known as the **mixed pixel problem**. If a narrow irrigation ditch or stream is less than 10 meters wide, its spectral signature is diluted by surrounding soil and vegetation. Without sub-pixel spectral unmixing, features narrower than 10 meters cannot be cleanly resolved.

#### Q4: What is the difference between Sentinel-2 Level-1C and Level-2A products?
**Answer:**  
Level-1C provides Top-Of-Atmosphere (TOA) reflectance, which includes atmospheric scattering (Rayleigh scattering from air molecules and aerosol absorption). Level-2A products are processed through ESA's **Sen2Cor** processor to provide Bottom-Of-Atmosphere (BOA) surface reflectance. Level-2A eliminates atmospheric distortions, ensuring that multi-temporal comparisons between different observation dates reflect true surface changes rather than atmospheric variance.

#### Q5: How do you handle cloud cover, and what is the difference between scene-level and AOI-level cloud cover?
**Answer:**  
Scene-level cloud cover is stored in STAC metadata property `eo:cloud_cover`, computed by Sen2Cor across the entire $100 \times 100\text{ km}$ MGRS tile (`T44RMQ`). AOI-level cloud assessment inspects the specific pixels intersecting the user's bounding box using the Scene Classification Layer (SCL) and reflectance values. In our Gomti River validation, both dates (2023-10-10 and 2023-12-09) exhibited **0.0% cloud cover** at both the whole-tile level and within the $4.40\text{ km}^2$ AOI.

#### Q6: Is the zero threshold ($\text{NDWI} > 0.0$) universally valid for all water bodies?
**Answer:**  
A threshold of $\tau = 0.00$ is the standard theoretical boundary for clear, open water. However, in highly turbid rivers with suspended sediment, green reflectance increases and NIR absorption slightly weakens, shifting NDWI values toward zero. In our validation on the post-monsoon Gomti River, $\tau = 0.00$ accurately captured the open-water channel. For turbid monsoon flood conditions, future versions will incorporate automated dynamic thresholding (such as Otsu's bimodal histogram method).

---

### Part B: Geospatial Engineering & Windowed Streaming (Q7–Q11)

#### Q7: How does Cloud-Optimized GeoTIFF (COG) windowed streaming work in DharaScope?
**Answer:**  
COGs are standard TIFF files with internally organized, regular pixel tiles ($256 \times 256$ or $512 \times 512$ bytes) and an internal header index. Using GDAL's `/vsicurl/` driver inside `rasterio`, the server reads only the file header to determine the byte offsets of the tiles that intersect the AOI bounding box. It then issues HTTP GET range requests (`Range: bytes=start-end`) to fetch only those specific byte blocks. This avoids downloading the entire 500 MB file.

#### Q8: Why is coordinate transformation necessary when querying Sentinel-2 data?
**Answer:**  
User AOIs are digitized in geographic coordinates (WGS 84 / EPSG:4326, in degrees latitude/longitude). Sentinel-2 granules are tiled and projected in the projected Universal Transverse Mercator (UTM) coordinate system (e.g., UTM Zone 44N / EPSG:32644, in meters). Before reading pixel arrays, DharaScope reprojects the AOI polygon using `pyproj` into native UTM meters, ensuring that raster slicing aligns precisely with the underlying pixel grid and preserving accurate 10.0m metric area calculations.

#### Q9: Why did you impose an upper limit of $100\text{ km}^2$ on user AOIs?
**Answer:**  
The $100\text{ km}^2$ limit is an architectural safeguard documented in [docs/SYSTEM_CONSTRAINTS.md](file:///d:/Coding/Projects/DharaScope/docs/SYSTEM_CONSTRAINTS.md). A $100\text{ km}^2$ AOI corresponds to $1,000,000\text{ pixels}$ at 10m resolution. Processing a 1-million-pixel array across two dates and multiple bands requires $\approx 32\text{ MB}$ of RAM, allowing single-node workers to process jobs concurrently under a 500 MB RAM budget without triggering Out-Of-Memory (OOM) failures or denial-of-service conditions.

#### Q10: How are division-by-zero errors and invalid NoData values prevented?
**Answer:**  
In `src/water_indices.py`, pixels where raw Digital Numbers equal zero are masked out as invalid NoData. When computing NDWI, any pixel where the denominator $|\text{B03} + \text{B08}| \le 10^{-6}$ is masked as invalid to prevent floating-point division by zero. The resulting NDWI array is clamped to the theoretical physical bounds $[-1.0, 1.0]$.

#### Q11: Can you reconcile the discrepancy between 44,178 pixels and 44,600 pixels in project records?
**Answer:**  
Yes. Reprojecting the WGS 84 bounding box `[80.90, 26.84, 80.92, 26.86]` to UTM Zone 44N yields an exact dimension of $1,988.50\text{ m} \times 2,216.55\text{ m}$, or $198.85 \times 221.65\text{ pixels}$ at 10m GSD.
- **Inner Truncated Window (`round_shape()`):** Rounds dimensions to nearest integers: $222\text{ rows} \times 199\text{ cols} = \mathbf{44,178\text{ pixels}}$ ($441.78\text{ ha}$, 100% valid mask).
- **Outer Expanded Window (ceiling grid bounds):** Rounds coordinates outward to integer grid lines: $223\text{ rows} \times 200\text{ cols} = \mathbf{44,600\text{ pixels}}$ ($446.00\text{ ha}$, with 43,979 valid pixels inside the polygon mask).
- **Invariant:** In both window formulations, the detected water pixels are **identical**: $53\text{ pixels}$ ($0.53\text{ ha}$) at $T_1$, $166\text{ pixels}$ ($1.66\text{ ha}$) at $T_2$, yielding an identical net gain of $+1.13\text{ ha}$. Because the river lies in the center of the box, the 422 marginal outer pixels are purely terrestrial land.

---

### Part C: Scientific Validity & Hydro-Spatial Dynamics (Q12–Q17)

#### Q12: Why did Phase 1 report a water decrease of $-45.23\text{ ha}$, while Phase 2.4/2.5 reports an increase of $+1.13\text{ ha}$?
**Answer:**  
Both analyses were computed from the **exact same Sentinel-2 Level-2A granules** (`2023-10-10` and `2023-12-09`). The difference is purely due to the spatial extent analyzed:
- **Phase 1 ($132.30\text{ km}^2$):** A regional basin corridor enclosing over 40 km of the Gomti river, expansive agricultural floodplains, and unchannelized oxbow lakes outside Lucknow city. In this regional zone, post-monsoon drying naturally desiccated temporary floodplain wetlands, producing a net loss of $-45.23\text{ ha}$ ($-24.51\%$).
- **Phase 2.4/2.5 ($4.40\text{ km}^2$):** A focused reach covering only 3.32% of the regional area, situated strictly within the channelized urban riverfront in downtown Lucknow, where satellite imagery observed an open-water expansion of $+1.13\text{ ha}$ ($+213.21\%$).

#### Q13: Does this mean your Phase 1 feasibility results were incorrect?
**Answer:**  
No. Phase 1 results are 100% mathematically and scientifically accurate for the $132.30\text{ km}^2$ regional envelope. When clipping the same Sentinel-2 rasters to the Phase 1 bounding box, our scripts reproduce the exact $184.56\text{ ha} \to 139.33\text{ ha}$ numbers. However, the Phase 1 regional box exceeded our single-run $100\text{ km}^2$ system limit. In Phase 2.4, we focused on the compliant $4.40\text{ km}^2$ urban reach.

#### Q14: Is this discrepancy merely a statistical scale aggregation effect?
**Answer:**  
No, it is fundamentally an expression of **environmental spatial heterogeneity**. A simple scale effect implies that a uniform process is merely diluted over a larger area. Here, the two envelopes capture fundamentally different landscape zones: the regional corridor contains unconfined floodplains and shallow seasonal depressions that dry out post-monsoon, whereas the urban reach contains a confined, embanked river channel. Sampling different geomorphic zones yields authentic physical differences.

#### Q15: Did the Gaughat Barrage gate operations cause the observed $+1.13\text{ ha}$ water expansion?
**Answer:**  
We **cannot** scientifically assert that barrage operations caused the change. While barrage impoundment, urban runoff, and riverfront dredging are plausible contributing hypotheses, satellite Earth observation measures only planar surface reflectance. Without synchronized in-situ stream gauge hydrographs and official barrage operational gate logs, claiming a proven hydraulic cause would be scientifically irresponsible. We strictly report the observation as an observed satellite-derived reflectance expansion.

#### Q16: How do you guarantee that synthetic data does not contaminate real satellite analyses?
**Answer:**  
Synthetic datasets generated by our offline demonstration tier are permanently tagged with an immutable metadata flag (`is_real_data: false`, `# Real Satellite Data,FALSE`). The frontend displays a persistent amber warning banner whenever synthetic data is viewed, while real satellite runs display a distinct green `REAL ORBITAL S2` badge. Our Playwright automated tests verify that when running real satellite data, the synthetic banner is absent and `is_real_data` is strictly true in the database, API response, and downloaded CSV/PDF reports.

#### Q17: Can DharaScope calculate river water volume or flow discharge?
**Answer:**  
No. Multispectral satellite imagery provides two-dimensional surface reflectance. NDWI indicates the planar presence or absence of open water; it does not measure water depth, cross-sectional bathymetry, stream velocity, or volumetric discharge. A 10 cm water layer over a flat silt bar produces the same binary water mask as a 5-meter-deep channel. Volumetric calculations require bathymetric sonar surveys and in-situ hydrometric rating curves.

---

### Part D: Web Architecture & Database Security (Q18–Q24)

#### Q18: Why did you choose FastAPI over traditional Python web frameworks like Django or Flask?
**Answer:**  
FastAPI operates on ASGI (`uvicorn`), providing native Python asynchronous `async/await` concurrency for non-blocking I/O. It uses Pydantic for compile-time and runtime data validation, automatically generates interactive OpenAPI/Swagger documentation, and provides a lightweight dependency-injection system that cleanly handles database sessions and authentication checks without Django's monolithic ORM overhead.

#### Q19: Why PostgreSQL 16 and PostGIS 3.6 instead of a NoSQL or file-based spatial database?
**Answer:**  
PostGIS is the industry standard for enterprise spatial data. It provides rigorous topological validation (`ST_IsValid`), geodetic distance/area calculations (`ST_Area`), and R-tree spatial indexing via Generalized Search Trees (GiST). Furthermore, PostgreSQL's advanced transactional engine enables native Row-Level Security (RLS) policies, foreign key cascades, and check constraints that cannot be replicated in document stores.

#### Q20: How does Row-Level Security (RLS) guarantee multi-tenant data isolation?
**Answer:**  
In our database architecture, the application connects as the restricted `dharascope_app` role. For every incoming HTTP request, the FastAPI authentication dependency extracts the authenticated user's UUID from the validated JWT and executes `SET LOCAL app.current_user_id = '<uuid>';`. Native PostgreSQL RLS policies enforce `USING (user_id = current_setting('app.current_user_id')::uuid)`. Even if an application developer forgets a `WHERE user_id = ...` clause, the database kernel will not return foreign tenant rows.

#### Q21: What happens if an admin's role is revoked, but they still hold an unexpired JWT?
**Answer:**  
To prevent privilege persistence through stale tokens, our `require_admin` dependency does **not** rely solely on client JWT claims. It uses the user's UUID to query the authoritative PostgreSQL `profiles` table within the active session. If the user's role has been revoked to `user` in the database, the request is immediately rejected with HTTP 403 Forbidden, regardless of JWT expiration time.

#### Q22: How is distributed transaction consistency maintained between Supabase Auth and PostgreSQL during role updates?
**Answer:**  
Updating user roles across Supabase Auth (`app_metadata.role`) and PostgreSQL (`profiles.role`) is a two-phase distributed operation. Our `RoleSyncService` follows an audit-journaled pattern:
1. Updates Supabase Auth.
2. Flushes the update to PostgreSQL.
3. If PostgreSQL commit fails, the service executes a compensating rollback in Supabase to restore the original role.
4. If the commit outcome is ambiguous (e.g., lost socket ACK), a fresh independent database session checks the committed role. If the DB committed the new role, Supabase is reconciled to the new role; if not, Supabase is compensated. All transitions are logged to `outputs/metadata/role_sync_audit.jsonl`.

#### Q23: Why decouple raster artifact storage from the PostgreSQL database?
**Answer:**  
Storing multi-megabyte binary rasters (GeoTIFFs, PNGs, PDFs) in PostgreSQL table columns (BLOBs/ByteA) bloats database table sizes, degrades buffer pool cache hit ratios, slows database backups, and creates heavy I/O contention. DharaScope stores only metadata, bounding boxes, and relative storage paths in PostgreSQL, delegating binary storage to local disk or Supabase Object Storage with time-limited signed download URLs.

#### Q24: How does the in-process background worker operate, and what are its limitations?
**Answer:**  
FastAPI's `BackgroundTasks` executes analysis pipelines in an in-process thread pool after returning an HTTP 202 Accepted response. While zero-dependency and sufficient for single-node deployments, in-process tasks do not survive application restarts or server crashes. If the server restarts during processing, running jobs are lost and must be re-submitted. In enterprise deployments, this should be migrated to a distributed task queue (Celery/RabbitMQ or Redis).

---

### Part E: Frontend GIS Workstation & UI/UX (Q25–Q27)

#### Q25: Why React 19 and Leaflet over more complex WebGL frameworks like Cesium or OpenLayers?
**Answer:**  
Leaflet is lightweight ($< 40\text{ KB}$ core), highly extensible, and adheres strictly to OGC standards. It renders 2D GeoJSON polygons and satellite tile layers with high performance on standard mobile and desktop browsers. Cesium is designed for heavy 3D globe visualizations and requires substantial GPU resources, which is unnecessary for 2D bounding box digitization and planar NDWI cartography.

#### Q26: How does the frontend validate user AOI geometries before submission?
**Answer:**  
When a user draws a polygon or clicks a preset, the frontend calculates the geodetic bounding box and area using turf.js algorithms, checks that the vertex count is between 4 and 500, and verifies that the area does not exceed $100\text{ km}^2$. It then sends the geometry to the backend `/api/v1/aois/validate` endpoint, where PostGIS executes `ST_IsValid` and `ST_Area` before the user can trigger an analysis.

#### Q27: How does the application handle offline or poor network connectivity?
**Answer:**  
For offline demonstration environments (such as examination halls without internet access), DharaScope includes a Tier 3 synthetic benchmark mode (`python main.py --source synthetic`). The frontend gracefully handles network timeouts with retry mechanisms and displays descriptive error states without unhandled UI crashes.

---

### Part F: Testing, Quality Assurance & Future Roadmap (Q28–Q30)

#### Q28: How did you test the full stack, and what is your overall test coverage?
**Answer:**  
Our testing regime combines three distinct tiers:
1. **Backend Pytest Suite:** 186 test cases across 16 test modules covering API endpoints, STAC discovery, NDWI computation, change detection, storage backends, RLS tenant isolation, and report generation (185 passed, 1 skipped live credential test, 87.4% coverage).
2. **Frontend Vitest Suite:** 18 test cases across 6 suites verifying component rendering, user interactions, and token security.
3. **End-to-End Playwright Automation:** Headless Chromium drives the live web GIS through all 8 user stages against running FastAPI and Vite servers with real Sentinel-2 data.
Total passing automated tests: **203 tests (100% pass rate)**.

#### Q29: What are the primary physical and operational limitations of the system?
**Answer:**  
1. **Optical Cloud Occlusion:** Optical sensors cannot penetrate cloud cover during the peak monsoon season (July–August).
2. **10-Meter Spatial Resolution:** Narrow headwater streams and small farm ponds ($< 100\text{ m}^2$) cannot be cleanly resolved.
3. **Planar Reflectance vs. Bathymetry:** NDWI detects surface water presence, not water depth or volume.
4. **Lack of In-Situ Telemetry:** Satellite data alone cannot prove hydraulic operational causes (e.g., barrage adjustments) without river gauge data.
5. **AOI Size Cap ($100\text{ km}^2$):** Required to prevent single-node server memory exhaustion.

#### Q30: If you had another 6 months of development, what would you prioritize?
**Answer:**  
1. **Sentinel-1 SAR Radar Integration:** Ingest Synthetic Aperture Radar (SAR) C-band data to enable cloud-penetrating water monitoring during monsoon storm events.
2. **Automated Dynamic Thresholding (Otsu Algorithm):** Implement automated histogram thresholding to adjust NDWI dynamically for turbid river conditions.
3. **Sub-Pixel Machine Learning:** Train lightweight U-Net or Random Forest models to resolve fractional water content in mixed riverbank pixels.
4. **Distributed Task Queue:** Scale the backend using Celery and Redis to support horizontal worker clustering.
