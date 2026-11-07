# Architectural & Technical Decision Records (ADR)
## DharaScope: Satellite-Based River Surface Water Dynamics Platform

**Document Version:** 2.1.0  
**Status:** Approved Architectural Baseline  
**Scope:** Phase 2 Platform Evolution  

---

## Index of Technical Decisions

- [ADR-001: Retention of Sentinel-2 MSI Level-2A as Primary Optical Constellation](#adr-001-retention-of-sentinel-2-msi-level-2a-as-primary-optical-constellation)
- [ADR-002: Multi-Tier Satellite Data Retrieval & Fallback Architecture](#adr-002-multi-tier-satellite-data-retrieval--fallback-architecture)
- [ADR-003: Windowed HTTP Range Request Subsetting (/vsicurl/) vs Full Tile Ingestion](#adr-003-windowed-http-range-request-subsetting-vsicurl-vs-full-tile-ingestion)
- [ADR-004: Geographical AOI Validation Envelope (0.10–100.00 km²)](#adr-004-geographical-aoi-validation-envelope-01010000-km)
- [ADR-005: Decoupled Authentication via Supabase Auth + FastAPI JWT Validation](#adr-005-decoupled-authentication-via-supabase-auth--fastapi-jwt-validation)
- [ADR-006: Relational PostGIS Schema for Spatiotemporal Metadata Storage](#adr-006-relational-postgis-schema-for-spatiotemporal-metadata-storage)
- [ADR-007: Object Storage Partitioning and 90-Day Output Retention Policy](#adr-007-object-storage-partitioning-and-90-day-output-retention-policy)
- [ADR-008: Publication-Grade PDF & CSV Reporting Grounded in Immutable Run Manifests](#adr-008-publication-grade-pdf--csv-reporting-grounded-in-immutable-run-manifests)

---

### ADR-001: Retention of Sentinel-2 MSI Level-2A as Primary Optical Constellation

#### Status
**ACCEPTED & LOCKED** (Phase 1 Baseline Preserved)

#### Context
DharaScope aims to monitor river surface water extent fluctuations across dynamic inland corridors (such as the Gomti River in Lucknow, UP). We evaluated alternative earth observation constellations:
1. **Landsat 8/9 OLI:** Provides 30m spatial resolution and an 8-day combined revisit. A 30m pixel ($900\text{ m}^2$) is too coarse for Indian river corridors where dry-season channel widths can narrow to 50–120m, causing severe mixed-pixel edge contamination.
2. **PlanetScope / Commercial Imagery:** Offers high resolution ($3\text{ m}$), but requires costly commercial subscriptions incompatible with an open, reproducible academic project.
3. **Sentinel-1 C-Band Synthetic Aperture Radar (SAR):** Radar penetrates cloud cover, but suffers from specular backscatter confusion along urban shorelines, sandbars, and steep embankments (Gomti Riverfront concrete walls), requiring complex terrain speckle filtering.
4. **Sentinel-2 MSI Level-2A:** Provides 10m native ground sampling distance for Band 3 (Green) and Band 8 (NIR), a combined 5-day revisit cycle (Sentinel-2A + Sentinel-2B), open-access licensing, and pre-computed Bottom-Of-Atmosphere (BOA) surface reflectance.

#### Decision
DharaScope shall strictly retain **Copernicus Sentinel-2 Level-2A (MSI)** as its primary satellite data source. No constellation migration shall be conducted.

#### Consequences
- **Positive:** Optimal 10m spatial resolution ($100\text{ m}^2/\text{pixel}$), enabling accurate mapping of river meanders, point bars, and sandbars; zero data licensing costs; standardized atmospheric correction.
- **Negative:** Susceptible to optical cloud obscuration during the core monsoon season (July–August), necessitating cloud-cover filtering ($\le 10\%$) and post-monsoon evaluation windows (October–May).

---

### ADR-002: Multi-Tier Satellite Data Retrieval & Fallback Architecture

#### Status
**ACCEPTED & IMPLEMENTED** (Verified in Phase 1)

#### Context
External satellite API endpoints frequently experience transient outages, Keycloak session timeouts, quota throttling, or credential configuration barriers for non-registered evaluators. An academic platform demo must be resilient against external gateway downtime without fabricating data.

#### Decision
Implement a three-tier retrieval hierarchy in `src/downloader.py`:
1. **Tier 1 (Official Authenticated Gateway):** CDSE OData API using Keycloak OAuth2 bearer tokens (`LocationTrustedSession`). Downloads official 10m single-band JP2 rasters when user credentials (`CDSE_USERNAME`, `CDSE_PASSWORD`) are configured.
2. **Tier 2 (Public Open-Access Archive):** AWS Registry of Open Data / Earth Search STAC hosting Sentinel-2 Level-2A Cloud-Optimized GeoTIFFs (COGs). Streams authentic ESA Sentinel-2 rasters without requiring user login credentials.
3. **Tier 3 (Offline Benchmark Fallback):** Georeferenced synthetic sample generator that mathematically simulates Gomti River geometry and realistic surface reflectance values for offline presentations.

#### Architectural Safeguards
- The system shall never present Tier 3 synthetic sample data as genuine satellite observations.
- Synthetic outputs must embed immutable tags: `PROVENANCE=SYNTHETIC_BENCHMARK_SAMPLE`.
- When Tier 2 is active, report metadata records: `PROVIDER=PUBLIC_OPEN_SENTINEL2_COGS`.

---

### ADR-003: Windowed HTTP Range Request Subsetting (/vsicurl/) vs Full Tile Ingestion

#### Status
**ACCEPTED & IMPLEMENTED** (Verified in Phase 1)

#### Context
A standard Sentinel-2 Level-2A MGRS tile (e.g. `T44RMQ`) covers $100\text{ km} \times 100\text{ km}$ ($10,000\text{ km}^2$) and weighs between 500 MB and 1.1 GB compressed. Downloading entire tiles for an Area of Interest of only $10–100\text{ km}^2$ wastes bandwidth, saturates server disk I/O, and causes multi-minute download latencies.

#### Decision
Leverage Cloud-Optimized GeoTIFF (COG) internal tiling and GDAL/rasterio virtual file systems (`/vsicurl/`) via HTTP `Range` headers.
- The pipeline reprojects the user's bounding box into the native projected CRS of the tile (`EPSG:32644`).
- It requests only the byte ranges corresponding to the bounding spatial tiles for Band 3 and Band 8.
- Rasters are clipped on-the-fly and saved as lightweight local GeoTIFFs (~2 to 8 MB per band instead of 500 MB+).

#### Consequences
- Latency for raster ingestion dropped from ~180 seconds (full tile download and unpack) to ~8–15 seconds.
- Storage requirement reduced by $>98\%$ per analysis run.

---

### ADR-004: Geographical AOI Validation Envelope (0.10–100.00 km²)

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Unbounded AOI submission allows users to submit arbitrarily large polygons (e.g., entire river basins of $50,000\text{ km}^2$), which would exhaust worker RAM during array allocation ($50,000\text{ km}^2 \times 10\text{m GSD} = 5 \times 10^8\text{ pixels} \approx 2\text{ GB}$ per float32 band array), or micro-polygons ($< 1,000\text{ m}^2$) where sub-pixel effects render 10m NDWI statistically meaningless.

#### Decision
Establish a strict geographical validation envelope in `src/aoi_validation.py`:
1. **Area Bounds:** Minimum area $0.10\text{ km}^2$ ($100,000\text{ m}^2$, or 1,000 pixels at 10m); Maximum area $100.00\text{ km}^2$ ($100,000,000\text{ m}^2$, or $1,000,000$ pixels at 10m).
2. **Area Calculation:** Geometry is reprojected from WGS84 to an appropriate equal-area projection or local UTM projection prior to area calculation.
3. **Vertex Limitation:** Maximum 500 vertices per polygon to prevent denial-of-service via boundary parsing complexity.
4. **Topological Rules:** Polygon must be topologically valid (`shapely.is_valid == True`), closed, non-self-intersecting, and within global lat/lon boundaries.

#### Engineering Caveat
*These bounds are architectural design criteria designed for single-node worker memory ceilings (< 2 GB RAM). They have not yet been stress-tested across edge conditions and must NOT be claimed as empirical benchmarks.*

---

### ADR-005: Decoupled Authentication via Supabase Auth + FastAPI JWT Validation

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2B2)**

#### Context
Phase 1 operated as a local single-user script and Streamlit dashboard. Phase 2 requires multi-user capabilities, role isolation (User vs Admin), and secure API endpoints, while avoiding custom authentication implementations (which introduce severe security vulnerabilities).

#### Decision
Delegate identity management to **Supabase Auth** and validate sessions statelessly via **FastAPI**:
1. **Client Signup & Login:** Frontend communicates directly with Supabase Auth (OAuth / Email+Password) over TLS 1.3.
2. **Token Issuance:** Supabase Auth issues cryptographically signed JWT tokens containing user claims (`sub`, `email`, `role`, `exp`).
3. **API Validation:** The FastAPI backend intercepts all incoming HTTP requests via a dependency `get_current_user`:
   - Extracts `Authorization: Bearer <token>`.
   - Validates signature against Supabase JWKS public keys (`RS256`/`ES256`) or symmetric HMAC (`HS256`).
   - Rejects expired, altered, unverified tokens, wrong audience/issuer with HTTP 401 Unauthorized.
4. **Data Ownership & RLS Context:** FastAPI propagates verified identity into the database transaction:
   ```sql
   SET LOCAL ROLE dharascope_app;
   SELECT set_config('request.jwt.claim.sub', :user_id, true);
   SELECT set_config('request.jwt.claim.role', :role, true);
   ```
   Setting `is_local = true` ensures parameters are strictly transaction-scoped, preventing connection pool pollution. PostgreSQL RLS policies evaluate `auth.uid()` and `auth.role()` on all 5 entity tables.

---

### ADR-006: Relational PostGIS Schema for Spatiotemporal Metadata Storage

#### Status
**IMPLEMENTED AND VERIFIED (Phase 2.2B1 & 2.2B2)**

#### Context
Phase 1 stored scene metadata and feasibility reports in flat JSON files (`outputs/phase1_feasibility_report.json`). In a multi-user platform, flat files suffer from concurrent write corruption, lack relational indexing, and cannot efficiently perform spatial intersection queries.

#### Decision
Deploy a PostgreSQL database with **PostGIS** extension enabled:
1. `public.profiles`: Extends Supabase `auth.users` with user roles (`user`, `admin`) and analysis quotas.
2. `public.aois`: Stores user-digitized polygons as `GEOMETRY(Polygon, 4326)` with spatial GiST indexing and computed area.
3. `public.analysis_runs`: Master execution manifest storing $T_1$ and $T_2$ scene IDs, acquisition dates, cloud percentages, NDWI threshold ($\tau$), data provenance provider, and processing status (`QUEUED`, `PROCESSING`, `SUCCESS`, `FAILED`).
4. `public.water_metrics`: Quantitative area statistics ($T_1$ area, $T_2$ area, persistent channel, apparent recession, apparent expansion, net change, % change).
5. `public.storage_assets`: URLs and object keys of exported PNG maps, CSV files, and PDF reports in Supabase Storage.

---

### ADR-007: Object Storage Partitioning and 90-Day Output Retention Policy

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Storing raw clipped GeoTIFF rasters permanently for hundreds of analysis runs would rapidly exhaust cloud storage budgets. However, user audit trails, tabular statistics, and publication-ready PDF reports must remain accessible indefinitely.

#### Decision
Establish a tiered storage architecture in Supabase Storage:
- **Bucket `rasters/` (90-Day Ephemeral Retention):** Stores clipped band GeoTIFFs (`B03_10m.tif`, `B08_10m.tif`) and binary classification rasters (`water_mask.tif`). A scheduled database job purges raster assets older than 90 days.
- **Bucket `maps/` (Permanent Retention):** Stores rendered 300 DPI multi-panel figures and categorical change maps.
- **Bucket `reports/` (Permanent Retention):** Stores generated PDF reports and CSV datasets.
- **Object Partitioning Scheme:** `bucket_name/{user_id}/{analysis_id}/{filename}`.

---

### ADR-008: Publication-Grade PDF & CSV Reporting Grounded in Immutable Run Manifests

#### Status
**ACCEPTED FOR PHASE 2 IMPLEMENTATION**

#### Context
Academic evaluations and geospatial research require formal, reproducible deliverables that can be shared with faculty, governing agencies, or peers. All reported figures must be verifiable against raw analysis manifests.

#### Decision
Implement dedicated export builders in `src/reporting.py`:
1. **CSV Export:** Standard RFC 4180 CSV containing a metadata header block followed by aligned metric rows (pixels, $\text{m}^2$, hectares, percentage change, and spatial resolution).
2. **PDF Export:** A publication-ready multi-page report rendered via Python (ReportLab / WeasyPrint):
   - Header with DharaScope insignia, project title, and unique analysis UUID.
   - Evaluator metadata and temporal parameters.
   - Key quantitative findings and component distribution table.
   - Embedded 300 DPI synoptic 4-panel comparison figure and categorical transition map.
   - Spectral methodology section highlighting McFeeters (1996) formulation and band physics.
   - Prominently framed scientific disclaimer clarifying seasonal hydrological recession vs chemical pollution.
3. **Data Integrity Rule:** The reporting engine reads directly from the database `water_metrics` and `analysis_runs` tables (or `phase1_feasibility_report.json`). No parameter may be hardcoded or fabricated.
