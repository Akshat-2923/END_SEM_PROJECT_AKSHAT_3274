# DharaScope: Comprehensive Evaluation & Technical Defense Q&A Guide
## Preparation Guide for Evaluators, Judges, and Academic Defense Panels

**Project:** DharaScope — Automated Satellite-Based Surface Water Dynamics Platform  
**Target Audience:** Capstone Examiners, Technical Judges, and Geospatial Peer Reviewers  
**Version:** 2.7.0 (Final Defense Baseline)  
**Date:** November 2026  

---

## 1. Executive Presentations: 60-Second & 3-Minute Briefings

### The 60-Second Elevator Briefing (For Non-Specialists)
> "Surface water bodies in monsoonal river networks fluctuate dramatically between monsoon flooding and dry winters. Traditional river monitoring relies on physical stream gauges that are spaced dozens of kilometers apart, leaving massive stretches of floodplains and dynamic wetlands completely unmonitored. 
> 
> Satellite data can solve this, but downloading massive 1-gigabyte satellite images for a localized 5-square-kilometer river reach is slow, expensive, and unscalable.
> 
> **DharaScope** is an automated web GIS platform that connects directly to the European Space Agency's Sentinel-2 satellite constellation. Instead of downloading full satellite scenes, our system uses Cloud-Optimized GeoTIFFs to stream only the exact pixels covering a user's digitized Area of Interest in seconds—reducing data transfer by over 99%. We calculate the Normalized Difference Water Index at 10-meter resolution, automatically detect water gains and losses, isolate each user's data using PostgreSQL Row-Level Security, and generate publication-quality PDF and CSV reports. 
> 
> On the Gomti River in Lucknow, we empirically proved that our platform detects real water dynamics accurately, safely, and reproducibly."

---

### The 3-Minute Technical Architecture Briefing (For Engineering & GIS Panel)
> "Good morning, members of the evaluation committee. DharaScope was engineered as an enterprise-grade, open-source geospatial platform that operationalizes optical Earth Observation data into an automated web GIS workflow.
> 
> The platform addresses three fundamental bottlenecks in modern environmental remote sensing: data volume, multi-tenant security, and reproducible change analysis.
> 
> **First, on the data engineering front:** Traditional satellite processing requires ingesting full $100 \times 100\text{ km}$ Level-2A granules. DharaScope bypasses this by integrating a SpatioTemporal Asset Catalog (STAC) discovery client with GDAL Virtual File Systems (`/vsicurl/`). When a user digitizes an Area of Interest up to $100\text{ km}^2$, the system reprojects the polygon into the satellite's native UTM projection and issues HTTP byte-range GET requests to stream only Band 3 (Green) and Band 8 (NIR) at native 10-meter ground sampling distance. This achieves a greater than 99% reduction in network transfer, reducing gigabytes to tens of kilobytes.
> 
> **Second, on the scientific and spectral pipeline:** We compute McFeeters Normalized Difference Water Index (NDWI) with zero-division protection and $[-1.0, 1.0]$ physical domain clamping. A calibrated zero-threshold ($\text{NDWI} > 0.0$) segments water, followed by a 4-class multi-temporal transition matrix—quantifying Permanent Water, Water Inundation, Water Recession, and Persistent Land. On our operational test area, the Urban Gomti River Study Reach, Lucknow, the system detected a net surface water expansion from $0.53\text{ ha}$ to $1.66\text{ ha}$ ($+1.13\text{ ha}$, $+213.21\%$) between October 10 and December 9, 2023. We verified that this localized channel expansion contrasts with regional floodplain recession ($-45.23\text{ ha}$) due to environmental spatial heterogeneity across diverse landscape zones. We strictly report observed planar surface reflectance changes and avoid unverified causal assertions without in-situ gauging.
> 
> **Third, on architecture and security:** The application is built on FastAPI, PostgreSQL 16 with PostGIS 3.6, and React 19 with Leaflet. We enforce defense-in-depth isolation using PostgreSQL native Row-Level Security (RLS) driven by Supabase JWT authentication, with connection-level session propagation (`SET LOCAL app.current_user_id`). Administrative endpoints verify privileges directly against the database `profiles` table to ensure instantaneous revocation. 
> 
> The platform is thoroughly validated: 185/185 executed backend tests passing (1 live CDSE test skipped) and 18/18 frontend tests passing (203 total passing tests), verified 83.0% statement coverage across `src/`, automated Playwright headless browser verification against real orbital imagery, and automated compilation of 300 DPI publication PDF reports. Thank you."

---

## 2. Thirty Technical & Project Defense Questions and Answers

### Part A: Remote Sensing Physics & Satellite Data (Q1–Q6)

#### Q1: Why did you choose McFeeters NDWI over Xu's Modified NDWI (MNDWI)?
- **Plain-Language Summary:** McFeeters uses Band 3 and Band 8, which both have crisp 10-meter resolution. Xu's index uses Band 11, which is blurrier at 20-meter resolution.
- **Technical Answer:** In the Sentinel-2 MultiSpectral Instrument (MSI), Band 3 (Green, 560 nm) and Band 8 (NIR, 842 nm) both operate at native 10-meter Ground Sampling Distance (GSD). Xu's MNDWI substitutes NIR with Shortwave Infrared (SWIR, Band 11, 1610 nm). While SWIR can suppress urban building noise, Band 11 has a 20-meter resolution. Using MNDWI would require spatial resampling or pan-sharpening, introducing spatial blur and interpolation error along narrow river channels. McFeeters NDWI preserves clean 10-meter boundary delineation.
- **Code Reference:** [`src/water_indices.py`](file:///d:/Coding/Projects/DharaScope/src/water_indices.py#L34-L72) (`calculate_ndwi`).

#### Q2: What are the physical spectral reflectance characteristics that allow NDWI to isolate water?
- **Plain-Language Summary:** Water reflects green light but completely swallows infrared light. Vegetation and soil do the opposite—they reflect infrared strongly.
- **Technical Answer:** Liquid water strongly absorbs radiation in near-infrared and shortwave-infrared wavelengths ($\rho_{\text{NIR}} < 1\%$), while reflecting moderately in green wavelengths ($\rho_{\text{Green}} \approx 10\text{–}15\%$). Conversely, green vegetation reflects 40–60% of NIR energy due to internal leaf mesophyll scattering, while bare soils reflect steadily across visible and NIR. Computing $(\text{Green} - \text{NIR}) / (\text{Green} + \text{NIR})$ yields positive values ($+0.15$ to $+0.80$) for water, and negative values ($-0.80$ to $-0.10$) for terrestrial vegetation and soil.
- **Code Reference:** [`src/water_indices.py`](file:///d:/Coding/Projects/DharaScope/src/water_indices.py#L45-L65).

#### Q3: How does spatial resolution limit the detection of narrow water bodies?
- **Plain-Language Summary:** If a ditch or canal is narrower than 10 meters, it shares a pixel with the riverbank, diluting the water signal.
- **Technical Answer:** At 10m GSD, a single pixel represents a $100\text{ m}^2$ square on the surface. Boundary pixels along riverbanks contain a mixture of water, mud, and riparian canopy (the "mixed pixel problem"). If a channel or pond is narrower than 10 meters, its spectral signature blends with surrounding terrestrial matter, pulling NDWI below zero. Sub-pixel spectral unmixing or higher-resolution sensors (e.g., PlanetScope 3m) are required to resolve sub-10m streams.
- **Code Reference:** [`docs/SCIENTIFIC_METHODOLOGY.md`](file:///d:/Coding/Projects/DharaScope/docs/SCIENTIFIC_METHODOLOGY.md#L175-L189).

#### Q4: What is the difference between Sentinel-2 Level-1C and Level-2A products?
- **Plain-Language Summary:** Level-1C is raw top-of-atmosphere imagery including atmospheric haze. Level-2A is surface reflectance with the atmosphere mathematically removed.
- **Technical Answer:** Level-1C delivers Top-Of-Atmosphere (TOA) reflectance containing Rayleigh scattering, cirrus haze, and aerosol distortions. Level-2A products are processed by ESA's Sen2Cor algorithm to produce Bottom-Of-Atmosphere (BOA) surface reflectance. Level-2A ensures multi-temporal reflectance comparisons reflect true ground surface changes rather than atmospheric variations between acquisition dates.
- **Code Reference:** [`src/downloader.py`](file:///d:/Coding/Projects/DharaScope/src/downloader.py#L25-L50).

#### Q5: How do you handle cloud cover, and what is the difference between scene-level and AOI-level cloud cover?
- **Plain-Language Summary:** Scene cloud cover tells you how cloudy the entire 100 km region is; AOI cloud cover checks if clouds are actually blocking your specific river study area.
- **Technical Answer:** Scene-level cloud cover is extracted from STAC metadata (`eo:cloud_cover`), computed across the entire $100 \times 100\text{ km}$ tile (`T44RMQ`). AOI-level cloud cover inspects the specific pixels intersecting the user's bounding box using Sen2Cor's Scene Classification Layer (SCL) and valid reflectance data. In our Gomti River case study, both dates (2023-10-10 and 2023-12-09) had 0.0% cloud cover at both the whole-tile level and within the $4.40\text{ km}^2$ study area.
- **Code Reference:** [`src/stac_client.py`](file:///d:/Coding/Projects/DharaScope/src/stac_client.py#L140-L165), [`src/scene_selection.py`](file:///d:/Coding/Projects/DharaScope/src/scene_selection.py#L40-L80).

#### Q6: Is the zero threshold ($\text{NDWI} > 0.0$) universally valid for all water bodies?
- **Plain-Language Summary:** Zero is the standard theoretical cutoff for clean water, but heavy silt or mud can shift the number.
- **Technical Answer:** A threshold of $\tau = 0.00$ is the standard theoretical boundary. However, in heavily turbid or sediment-laden waters, suspended solids increase green reflectance and scatter NIR light, shifting NDWI closer to zero. While $\tau = 0.00$ performed cleanly for the post-monsoon Gomti River, dynamic thresholding algorithms (such as Otsu's bimodal histogram method) are planned for high-turbidity flood seasons.
- **Code Reference:** [`src/water_indices.py`](file:///d:/Coding/Projects/DharaScope/src/water_indices.py#L75-L110) (`classify_water`).

---

### Part B: Geospatial Engineering & Windowed Streaming (Q7–Q11)

#### Q7: How does Cloud-Optimized GeoTIFF (COG) windowed streaming work in DharaScope?
- **Plain-Language Summary:** Instead of downloading an entire book to read one sentence, we read the index and download only the single paragraph we need.
- **Technical Answer:** COGs organize raster pixels into regular internal tiles ($256 \times 256$ or $512 \times 512$ bytes) with an internal header index. Using GDAL's `/vsicurl/` driver inside `rasterio`, the server reads the remote TIFF header index via HTTP range requests, identifies the byte offsets of the tiles that intersect the AOI bounding box, and requests only those byte ranges. This avoids downloading the 500 MB granule.
- **Code Reference:** [`src/downloader.py`](file:///d:/Coding/Projects/DharaScope/src/downloader.py#L340-L395) (`retrieve_band_via_cog_window`).

#### Q8: Why is coordinate transformation necessary when querying Sentinel-2 data?
- **Plain-Language Summary:** Web maps use latitude/longitude degrees (WGS 84), while satellite rasters are laid out in meters (UTM). We must translate degrees into meters to cut the raster correctly.
- **Technical Answer:** User AOIs are digitized in geographic coordinates (WGS 84 / EPSG:4326, in degrees). Sentinel-2 granules are tiled in the projected Universal Transverse Mercator system (UTM Zone 44N / EPSG:32644, in meters). Before reading pixel arrays, DharaScope reprojects the AOI polygon using `pyproj` into native UTM meters, aligning the clipping window with the pixel matrix and ensuring accurate 10.0m metric area calculations.
- **Code Reference:** [`src/downloader.py`](file:///d:/Coding/Projects/DharaScope/src/downloader.py#L365-L385).

#### Q9: Why did you impose an upper limit of $100\text{ km}^2$ on user AOIs?
- **Plain-Language Summary:** To prevent a single user from crashing the server by requesting a giant area that runs the machine out of memory.
- **Technical Answer:** A $100\text{ km}^2$ AOI corresponds to $1,000,000\text{ pixels}$ at 10m GSD. Processing 1 million pixels across two dates and multiple bands requires $\approx 32\text{ MB}$ of array RAM. Capping the AOI at $100\text{ km}^2$ guarantees that concurrent worker tasks remain well under our 500 MB RAM budget per worker, preventing Out-Of-Memory (OOM) crashes on shared hardware.
- **Code Reference:** [`src/aoi_validation.py`](file:///d:/Coding/Projects/DharaScope/src/aoi_validation.py#L25-L45) (`MAX_AOI_AREA_KM2 = 100.00`).

#### Q10: How are division-by-zero errors and invalid NoData values prevented?
- **Plain-Language Summary:** We check for zero denominators before dividing, and clamp extreme numbers to safe physical limits.
- **Technical Answer:** In `src/water_indices.py`, raw pixels equal to NoData (0) are masked out. When computing NDWI, any pixel where the denominator $|\text{B03} + \text{B08}| \le 10^{-6}$ is masked as invalid to eliminate zero division. The resulting NDWI array is clamped to the theoretical physical domain $[-1.0, 1.0]$.
- **Code Reference:** [`src/water_indices.py`](file:///d:/Coding/Projects/DharaScope/src/water_indices.py#L55-L65).

#### Q11: Can you reconcile the discrepancy between 44,178 pixels and 44,600 pixels in project records?
- **Plain-Language Summary:** One formula rounded the window dimensions inward ($222 \times 199 = 44,178$), while the other rounded outward ($223 \times 200 = 44,600$). In both cases, the detected river pixels were 100% identical.
- **Technical Answer:** The bounding box `[80.90, 26.84, 80.92, 26.86]` in UTM Zone 44N spans $1,988.50\text{ m} \times 2,216.55\text{ m}$ ($198.85 \times 221.65\text{ pixels}$ at 10m GSD).
  - Truncated inner window (`round_shape()`): $222 \times 199 = \mathbf{44,178\text{ pixels}}$ ($441.78\text{ ha}$, 100% valid mask).
  - Outer expanded bounding window (ceiling offsets): $223 \times 200 = \mathbf{44,600\text{ pixels}}$ ($446.00\text{ ha}$, with 43,979 valid pixels inside the polygon mask).
  - **Invariant:** Because the river lies in the center of the box, the 422 marginal outer pixels are purely terrestrial urban land with $\text{NDWI} \ll 0.0$. In both formulations, detected water pixels are strictly identical: **53 pixels ($0.53\text{ ha}$) at $T_1$, 166 pixels ($1.66\text{ ha}$) at $T_2$, and net change $+1.13\text{ ha}$**.
- **Code Reference:** [`docs/SCIENTIFIC_METHODOLOGY.md`](file:///d:/Coding/Projects/DharaScope/docs/SCIENTIFIC_METHODOLOGY.md#L155-L168).

---

### Part C: Scientific Validity & Hydro-Spatial Dynamics (Q12–Q17)

#### Q12: Why did Phase 1 report a water decrease of $-45.23\text{ ha}$, while Phase 2.4/2.5 reports an increase of $+1.13\text{ ha}$?
- **Plain-Language Summary:** They looked at two different areas: Phase 1 examined a giant 132 km² regional basin containing rural floodplains that dried up, while Phase 2 looked closely at a 4.4 km² city river reach.
- **Technical Answer:** Both analyses used the exact same Sentinel-2 granules (`2023-10-10` and `2023-12-09`). The difference is spatial extent:
  - Phase 1 Regional Basin ($132.30\text{ km}^2$): Evaluated over 40 km of the Gomti river, expansive rural floodplains, and unconfined oxbow wetlands that naturally desiccated post-monsoon, producing a net loss of $-45.23\text{ ha}$ ($-24.51\%$).
  - Phase 2 Operational Reach ($4.40\text{ km}^2$): Focused strictly on the channelized urban corridor through downtown Lucknow, where satellite imagery observed an open-water surface expansion of $+1.13\text{ ha}$ ($+213.21\%$).
- **Code Reference:** [`docs/TECHNICAL_DECISIONS.md`](file:///d:/Coding/Projects/DharaScope/docs/TECHNICAL_DECISIONS.md#L365-L390) (ADR-014).

#### Q13: Does this mean your Phase 1 feasibility results were incorrect?
- **Plain-Language Summary:** No, both calculations are 100% correct. If you clip the satellite image to the Phase 1 box today, you get the exact same -45.23 ha result.
- **Technical Answer:** Phase 1 results are completely accurate for the $132.30\text{ km}^2$ regional envelope. When clipping the raw GeoTIFFs to the Phase 1 bounding box, our scripts reproduce the exact $184.56\text{ ha} \to 139.33\text{ ha}$ metrics. However, Phase 1 was a preliminary feasibility experiment that exceeded the $100\text{ km}^2$ operational safety bound adopted in Phase 2. In Phase 2, we focused on the compliant $4.40\text{ km}^2$ urban reach.
- **Code Reference:** [`DEVELOPMENT_HISTORY.md`](file:///d:/Coding/Projects/DharaScope/DEVELOPMENT_HISTORY.md#L700-L725).

#### Q14: Is this discrepancy merely a statistical scale aggregation effect?
- **Plain-Language Summary:** No. It's not a math trick—the riverfront in the city is physically different from the agricultural floodplains in the countryside.
- **Technical Answer:** It is an expression of **environmental spatial heterogeneity**. A simple scale effect implies that a uniform physical process is merely averaged or diluted over a larger window. Here, the two envelopes capture fundamentally different landscape zones: unconfined rural floodplains and shallow seasonal depressions that dry out post-monsoon vs. a confined, embanked urban river channel. Sampling different landscape units captures their distinct physical behaviors.
- **Code Reference:** [`docs/PROJECT_REPORT.md`](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md#L350-L375).

#### Q15: Did Gaughat Barrage gate operations cause the observed $+1.13\text{ ha}$ water expansion?
- **Plain-Language Summary:** We cannot prove that without gauge logs. The satellite sees water on the surface, but cannot tell you why the water rose.
- **Technical Answer:** We **cannot** scientifically assert that barrage operations caused the change. While barrage impoundment, urban runoff, and riverfront dredging are plausible contributing hypotheses, satellite Earth observation measures only planar surface reflectance. Without synchronized in-situ stream gauge hydrographs and official barrage operational gate logs, claiming a proven hydraulic cause would be scientifically irresponsible. We strictly report the observation as an observed satellite-derived reflectance expansion.
- **Code Reference:** [`src/reporting.py`](file:///d:/Coding/Projects/DharaScope/src/reporting.py#L565-L575).

#### Q16: How do you guarantee that synthetic test data does not contaminate real satellite analyses?
- **Plain-Language Summary:** Synthetic data carries a permanent digital label, displays a bright yellow warning on the screen, and cannot pretend to be real satellite data.
- **Technical Answer:** Synthetic datasets generated by our offline tier are permanently tagged with metadata flags (`is_real_data: false`, `# Real Satellite Data,FALSE`). The frontend displays a persistent amber warning banner whenever synthetic data is viewed, while real satellite runs display a green `REAL ORBITAL S2` badge. Our Playwright automated tests verify that when running real satellite data, the synthetic banner is absent and `is_real_data` is strictly true in the database, API response, and downloaded CSV/PDF reports.
- **Code Reference:** [`scripts/validate_real_satellite_browser.mjs`](file:///d:/Coding/Projects/DharaScope/scripts/validate_real_satellite_browser.mjs#L140-L165).

#### Q17: Can DharaScope calculate river water volume or flow discharge?
- **Plain-Language Summary:** No. Satellites take a flat picture from above; they cannot see how deep the river is or how fast it is flowing.
- **Technical Answer:** No. Multispectral satellite imagery provides two-dimensional planar surface reflectance. NDWI indicates the presence or absence of open surface water; it does not measure water depth, cross-sectional bathymetry, stream velocity, or volumetric discharge ($\text{m}^3/\text{s}$). A 10 cm water layer over a flat sandbar produces the same binary water mask as a 5-meter-deep channel. Volumetric calculations require bathymetric sonar surveys and in-situ hydrometric rating curves.
- **Code Reference:** [`docs/SYSTEM_CONSTRAINTS.md`](file:///d:/Coding/Projects/DharaScope/docs/SYSTEM_CONSTRAINTS.md#L25-L33).

---

### Part D: Web Architecture & Database Security (Q18–Q24)

#### Q18: Why did you choose FastAPI over traditional Python web frameworks like Django or Flask?
- **Plain-Language Summary:** FastAPI is modern, handles asynchronous non-blocking web traffic natively, validates all inputs automatically, and generates interactive API documentation.
- **Technical Answer:** FastAPI operates on ASGI (`uvicorn`), providing native Python asynchronous `async/await` concurrency for non-blocking I/O. It uses Pydantic for compile-time and runtime data validation, automatically generates interactive OpenAPI/Swagger documentation, and provides a lightweight dependency-injection system that cleanly handles database sessions and authentication checks without Django's monolithic ORM overhead.
- **Code Reference:** [`src/api/app.py`](file:///d:/Coding/Projects/DharaScope/src/api/app.py#L1-L60).

#### Q19: Why PostgreSQL 16 and PostGIS 3.6 instead of a NoSQL or file-based spatial database?
- **Plain-Language Summary:** PostGIS is the gold standard for spatial math (checking for invalid polygons and calculating exact areas), while PostgreSQL provides bulletproof security features like Row-Level Security.
- **Technical Answer:** PostGIS provides industry-standard topological validation (`ST_IsValid`), geodetic distance/area calculations (`ST_Area`), and R-tree spatial indexing via Generalized Search Trees (GiST). Furthermore, PostgreSQL's advanced transactional engine enables native Row-Level Security (RLS) policies, foreign key cascades, and check constraints that cannot be replicated in document stores.
- **Code Reference:** [`src/database/models/aoi.py`](file:///d:/Coding/Projects/DharaScope/src/database/models/aoi.py#L20-L45).

#### Q20: How does Row-Level Security (RLS) guarantee multi-tenant data isolation?
- **Plain-Language Summary:** The database itself locks the doors: even if a programmer writes a buggy SQL query without a user filter, the database refuse to show rows belonging to other users.
- **Technical Answer:** In our database architecture, the application connects as the restricted `dharascope_app` role. For every incoming HTTP request, the FastAPI authentication dependency extracts the authenticated user's UUID from the validated JWT and executes `SET LOCAL app.current_user_id = '<uuid>';`. Native PostgreSQL RLS policies enforce `USING (user_id = current_setting('app.current_user_id')::uuid)`. Even if an application query omitted a `WHERE user_id = ...` filter, the database kernel will not return foreign tenant rows.
- **Code Reference:** [`src/auth.py`](file:///d:/Coding/Projects/DharaScope/src/auth.py#L485-L525) (`get_db_session`).

#### Q21: What happens if an admin's role is revoked, but they still hold an unexpired JWT?
- **Plain-Language Summary:** We check their status directly in the database on every sensitive request. If they were demoted, they are kicked out immediately, even if their token hasn't expired.
- **Technical Answer:** To prevent privilege persistence through stale tokens, our `require_admin` dependency does **not** rely solely on client JWT claims. It uses the user's UUID to query the authoritative PostgreSQL `profiles` table within the active session. If the user's role has been revoked to `user` in the database, the request is immediately rejected with HTTP 403 Forbidden, regardless of JWT expiration time.
- **Code Reference:** [`src/auth.py`](file:///d:/Coding/Projects/DharaScope/src/auth.py#L275-L315) (`require_admin`).

#### Q22: How is distributed transaction consistency maintained between Supabase Auth and PostgreSQL during role updates?
- **Plain-Language Summary:** We use a two-step update with a safety net: if the database fails to save the change, we immediately roll back the change in Supabase and log the event.
- **Technical Answer:** Updating user roles across Supabase Auth (`app_metadata.role`) and PostgreSQL (`profiles.role`) is a two-phase distributed operation. Our `RoleSyncService` follows an audit-journaled pattern:
  1. Updates Supabase Auth.
  2. Flushes the update to PostgreSQL.
  3. If PostgreSQL commit fails, the service executes a compensating rollback in Supabase to restore the original role.
  4. If the commit outcome is ambiguous (e.g., lost socket ACK), a fresh independent database session checks the committed role. If the DB committed the new role, Supabase is reconciled; if not, Supabase is compensated. All transitions are logged to `outputs/metadata/role_sync_audit.jsonl`.
- **Code Reference:** [`src/services/role_sync_service.py`](file:///d:/Coding/Projects/DharaScope/src/services/role_sync_service.py#L290-L380) (`execute_reliable_role_update`).

#### Q23: Why decouple raster artifact storage from the PostgreSQL database?
- **Plain-Language Summary:** Storing multi-megabyte image files inside database tables slows down the entire system. We store files on disk/cloud storage and keep only lightweight links in the database.
- **Technical Answer:** Storing multi-megabyte binary rasters (GeoTIFFs, PNGs, PDFs) in PostgreSQL table columns (BLOBs/ByteA) bloats database table sizes, degrades buffer pool cache hit ratios, slows database backups, and creates heavy I/O contention. DharaScope stores only metadata, bounding boxes, and relative storage paths in PostgreSQL, delegating binary storage to local disk or Supabase Object Storage with time-limited signed download URLs.
- **Code Reference:** [`src/storage.py`](file:///d:/Coding/Projects/DharaScope/src/storage.py#L1-L60).

#### Q24: How does the in-process background worker operate, and what are its limitations?
- **Plain-Language Summary:** It runs analyses in the background using Python threads. It works great on a single machine, but if the server reboots while an analysis is running, that job must be re-submitted.
- **Technical Answer:** FastAPI's `BackgroundTasks` executes analysis pipelines in an in-process thread pool after returning an HTTP 202 Accepted response. While zero-dependency and sufficient for single-node deployments, in-process tasks do not survive application restarts or server crashes. If the server restarts during processing, running jobs are lost and must be re-submitted. In enterprise deployments, this should be migrated to a distributed task queue (Celery/RabbitMQ or Redis).
- **Code Reference:** [`src/api/routers/analyses.py`](file:///d:/Coding/Projects/DharaScope/src/api/routers/analyses.py#L140-L165).

---

### Part E: Frontend GIS Workstation & UI/UX (Q25–Q27)

#### Q25: Why React 19 and Leaflet over more complex WebGL frameworks like Cesium or OpenLayers?
- **Plain-Language Summary:** Leaflet is fast, lightweight, and perfect for 2D maps. Cesium is meant for heavy 3D spinning globes and would slow down regular laptops unnecessarily.
- **Technical Answer:** Leaflet is lightweight ($< 40\text{ KB}$ core), highly extensible, and adheres strictly to OGC standards. It renders 2D GeoJSON polygons and satellite tile layers with high performance on standard mobile and desktop browsers. Cesium is designed for heavy 3D globe visualizations and requires substantial GPU resources, which is unnecessary for 2D bounding box digitization and planar NDWI cartography.
- **Code Reference:** [`frontend/src/components/MapPicker.tsx`](file:///d:/Coding/Projects/DharaScope/frontend/src/components/MapPicker.tsx#L1-L60).

#### Q26: How does the frontend validate user AOI geometries before submission?
- **Plain-Language Summary:** The map checks the polygon immediately in the browser, and then sends it to PostGIS to make sure it's valid before allowing you to run the analysis.
- **Technical Answer:** When a user draws a polygon or clicks a preset, the frontend calculates the geodetic bounding box and area using turf.js algorithms, checks that the vertex count is between 4 and 500, and verifies that the area does not exceed $100\text{ km}^2$. It then sends the geometry to the backend `/api/v1/aois/validate` endpoint, where PostGIS executes `ST_IsValid` and `ST_Area` before the user can trigger an analysis.
- **Code Reference:** [`frontend/src/components/MapPicker.tsx`](file:///d:/Coding/Projects/DharaScope/frontend/src/components/MapPicker.tsx#L70-L120).

#### Q27: How does the application handle offline or poor network connectivity?
- **Plain-Language Summary:** We have an offline demonstration mode with pre-packaged data, so the system works perfectly even if the presentation room has no Wi-Fi.
- **Technical Answer:** For offline demonstration environments (such as examination halls without internet access), DharaScope includes a Tier 3 synthetic benchmark mode (`python main.py --source synthetic`). The frontend gracefully handles network timeouts with retry mechanisms and displays descriptive error states without unhandled UI crashes.
- **Code Reference:** [`src/downloader.py`](file:///d:/Coding/Projects/DharaScope/src/downloader.py#L150-L200).

---

### Part F: Testing, Quality Assurance & Future Roadmap (Q28–Q30)

#### Q28: How did you test the full stack, and what is your overall test coverage?
- **Plain-Language Summary:** We wrote 203 automated tests covering the database, API, and frontend. Our automated coverage report proves 83.0% statement coverage across all backend code, with core modules reaching 89%–100%.
- **Technical Answer:** Our testing regime combines three distinct tiers:
  1. **Backend Pytest Suite:** 186 test cases across 16 test modules covering API endpoints, STAC discovery, NDWI computation, change detection, storage backends, RLS tenant isolation, and report generation (185 passed, 1 skipped live credential test). Statement coverage across all 2,605 statements in `src/` is **83.0%**, with core modules (`visualization`, `database/models`, `api/routers`, `change_detection`, `reporting`, `water_indices`, `role_sync_service`) achieving **89%–100% coverage**.
  2. **Frontend Vitest Suite:** 18 test cases across 6 suites verifying component rendering, user interactions, and token security.
  3. **End-to-End Playwright Automation:** Headless Chromium drives the live web GIS through all 8 user stages against running FastAPI and Vite servers with real Sentinel-2 data.
  Total passing automated tests: **203 tests (185/185 executed backend tests passed, 1 skipped; 18/18 frontend tests passed)**.
- **Code Reference:** [`tests/`](file:///d:/Coding/Projects/DharaScope/tests/).

#### Q29: What are the primary physical and operational limitations of the system?
- **Plain-Language Summary:** Clouds block the camera in monsoon season, small farm ponds under 10 meters can't be resolved, the satellite can't measure depth, and jobs in the background don't survive a server reboot.
- **Technical Answer:**
  1. **Optical Cloud Occlusion:** Optical sensors cannot penetrate cloud cover during the peak monsoon season (July–August).
  2. **10-Meter Spatial Resolution:** Narrow headwater streams and small farm ponds ($< 100\text{ m}^2$) cannot be cleanly resolved without sub-pixel spectral unmixing.
  3. **Planar Reflectance vs. Bathymetry:** NDWI detects surface water presence, not water depth or volume.
  4. **Lack of In-Situ Telemetry:** Satellite data alone cannot prove hydraulic operational causes (e.g., barrage adjustments) without river gauge data.
  5. **AOI Size Cap ($100\text{ km}^2$):** Required to prevent single-node server memory exhaustion.
- **Code Reference:** [`docs/SYSTEM_CONSTRAINTS.md`](file:///d:/Coding/Projects/DharaScope/docs/SYSTEM_CONSTRAINTS.md#L15-L55).

#### Q30: If you had another 6 months of development, what would you prioritize?
- **Plain-Language Summary:** Radar satellites to see through clouds during monsoon floods, dynamic thresholding for muddy water, and distributed servers for nationwide scaling.
- **Technical Answer:**
  1. **Sentinel-1 SAR Radar Integration:** Ingest Synthetic Aperture Radar (SAR) C-band data to enable cloud-penetrating water monitoring during monsoon storm events.
  2. **Automated Dynamic Thresholding (Otsu Algorithm):** Implement automated histogram thresholding to adjust NDWI dynamically for turbid river conditions.
  3. **Sub-Pixel Machine Learning:** Train lightweight U-Net or Random Forest models to resolve fractional water content in mixed riverbank pixels.
  4. **Distributed Task Queue:** Scale the backend using Celery and Redis to support horizontal worker clustering.
- **Code Reference:** [`docs/PROJECT_REPORT.md`](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md#L450-L470).
