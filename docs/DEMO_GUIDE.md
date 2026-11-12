# DharaScope — Academic Evaluation & Demonstration Guide
## Step-by-Step Evaluator Script for Live Demonstration & Verification

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Target Audience:** Academic Evaluators, Capstone Project Judges, and External Reviewers  
**Platform Version:** Phase 2.5 (Release 0.9.1)  

---

## 1. Evaluation Briefing & System Verification Matrix

DharaScope is an automated earth observation platform designed to quantify surface water fluctuations along inland river networks using European Space Agency (ESA) Copernicus Sentinel-2 Level-2A imagery.

| Evaluation Criterion | Implementation Evidence | Verification Command / Step |
| :--- | :--- | :--- |
| **Real Satellite Data Ingestion** | Genuine Sentinel-2 Level-2A 10m rasters (Band 3 & Band 8) | AWS Open Data COG streaming (`PUBLIC_OPEN_SENTINEL2_COGS`) |
| **Spectral Index Processing** | McFeeters (1996) NDWI with zero-division protection | `calculate_ndwi()`, $\tau = 0.00$ |
| **Multi-Temporal Change Detection** | 4-class categorical transition matrix ($T_1 \land T_2$) | Persistent, Recession, Inundation, Non-Water |
| **Spatial Database Architecture** | PostgreSQL 16 + PostGIS 3.6 with GiST spatial indexing | 20 Row-Level Security policies, ellipsoidal area checks |
| **Application Service Layer** | FastAPI ASGI backend with dependency-injected auth | OpenAPI 3.1 documentation at `/docs` |
| **Modern GIS Workstation** | React 19 + TypeScript + Vite + Leaflet mapping | Dark Matter cartographic canvas at `http://localhost:5173` |
| **Automated Testing Suite** | **203 passing tests** (185 backend + 18 frontend) | `pytest` and `vitest` (100% pass rate) |
| **Browser E2E Automation** | Headless Chromium driving 8 interactive steps | `node scripts/validate_real_satellite_browser.mjs` |

---

## 2. Environment Prerequisites

Ensure the following runtimes are installed on the evaluation machine:
- **Python:** Version 3.11.x (with `.venv` active).
- **Node.js:** Version 18.x, 20.x, or 22.x (with `npm`).
- **PostgreSQL:** Version 16.x with PostGIS 3.6.x extension listening on `localhost:5432`.
- **Operating System:** Windows 10/11, macOS, or Linux.

---

## 3. Starting the Demonstration Environment

Open two separate terminal windows from the repository root (`DharaScope/`):

### Terminal 1: FastAPI Backend Application Server
```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Verify database migrations are at head
alembic current

# 3. Start Uvicorn ASGI server on port 8000
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```
*Expected Output:* Server starts at `http://127.0.0.1:8000`. Health check available at `http://127.0.0.1:8000/api/v1/health`.

### Terminal 2: React GIS Workstation Frontend
```powershell
# 1. Navigate to frontend directory (if starting fresh, run: npm install)
cd frontend

# 2. Start Vite development server on port 5173
npm run dev -- --host 127.0.0.1 --port 5173
```
*Expected Output:* Application available at `http://127.0.0.1:5173`.

---

## 4. Step-by-Step Live Demonstration Walkthrough

### Step 1: Accessing the Workstation
1. Open Google Chrome, Firefox, or Edge and navigate to `http://127.0.0.1:5173`.
2. Observe the **Workstation Header**:
   - Platform Identity: `DharaScope v2.5`
   - Telemetry Pill: `S2-MSI · 10m GSD · B03/B08`
   - Backend Status: `API Online (connected)` with green live status indicator.

### Step 2: Authentication & Role Inspection
1. Click the **"Connect Session to Begin"** button (or **"Connect Session"** in the header).
2. The **Authentication Modal** appears with two tabs:
   - *Tab 1: Developer Presets (Offline Testing):*
     - Click **"Dr. Gomti Hydrologist (Standard User)"** to load a verified researcher account with a 50 runs/month quota.
     - Notice the header badge updates to green `USER` displaying quota usage.
   - *Tab 2: Administrator Persona:*
     - Switch account to **"Chief Remote Sensing Admin (Admin)"** to inspect administrative privileges (`ADMIN` badge).

### Step 3: Interactive AOI Selection & PostGIS Validation
1. In the left panel, inspect the **Geographical Area of Interest (AOI)** card.
2. The Leaflet map initializes centered on the **Gomti River urban corridor in Lucknow, India** (`26.85°N, 80.91°E`).
3. Click the **"Gomti Reach (Lucknow)"** preset button to load the canonical benchmark polygon (`[80.90, 26.84]` to `[80.92, 26.86]`).
4. Observe the real-time **PostGIS Validation Box**:
   - Status: `Valid AOI Geometry (PostGIS Verified)`
   - Geometry: `Polygon`
   - Ellipsoidal Area: **4.4048 km²** (440.48 ha)
   - Vertices: **5 / 500**
   - Centroid: `[80.910°E, 26.850°N]`
5. *(Optional)* Click **"GeoJSON Editor"** to inspect or modify raw coordinate arrays, testing how the backend rejects out-of-bound areas ($> 100\text{ km}^2$) or self-intersecting topologies.

### Step 4: Multi-Temporal Analysis Configuration
In the **Analysis Parameters & Execution** card:
1. **NDWI Threshold Slider (τ):** Set to `0.00` (standard clear water index cutoff; configurable from -0.30 to +0.30).
2. **Max Scene Cloud Cover Slider:** Set to `10.0%` (standard optical quality filter).
3. **Temporal Search Interval:** Default set to `2023-10-01T00:00:00Z/2024-05-31T23:59:59Z` (capturing the post-monsoon to early-winter transition).
4. **Retrieval Tier:** Select `Earth Search / AWS STAC` (or `Auto` to prioritize public Sentinel-2 Cloud-Optimized GeoTIFFs).
5. Click **"Launch Surface Water Analysis"**.

### Step 5: Live Pipeline Execution & Real-Time Tracking
1. The right panel transitions into the **Run Lifecycle & Satellite Metadata** card.
2. An animated shimmer progress bar tracks execution through `QUEUED` $\to$ `PROCESSING PIPELINE`.
3. Within **6–9 seconds**, the job transitions to `SUCCESS`.
4. Observe the **Satellite Discovery Metadata**:
   - Status: `SUCCESS`
   - Provenance Badge: Green `REAL ORBITAL S2` (confirming genuine satellite data).
   - $T_1$ Observation (Baseline): `S2A_MSIL2A_20231010T050721...` (Acquired: 10/10/2023, 0.0% cloud).
   - $T_2$ Observation (Comparison): `S2A_MSIL2A_20231209T051211...` (Acquired: 12/09/2023, 0.0% cloud).
   - Provider: `PUBLIC_OPEN_SENTINEL2_COGS · Real Sentinel-2 Multi-spectral`.

### Step 6: Scientific Surface Water Metrics & Transitions
Inspect the **Surface Water Area & Transition Dynamics** card:
- **Baseline Water Area ($T_1$, Oct 2023):** `0.53 ha` ($5,300\text{ m}^2$, 53 pixels).
- **Later Water Area ($T_2$, Dec 2023):** `1.66 ha` ($16,600\text{ m}^2$, 166 pixels).
- **Net Surface Delta (Δ):** `+1.13 ha` (`+213.21%` net change).
- **Categorical Breakdown:**
  - *Persistent Water (Perennial channel core):* `0.39 ha` ($3,900\text{ m}^2$).
  - *Apparent Water Loss (Recession):* `0.14 ha` ($1,400\text{ m}^2$).
  - *Apparent Water Gain (Inundation expansion):* `1.27 ha` ($12,700\text{ m}^2$).
- **Scientific Limitation Notice:** A prominent callout reminds evaluators that satellite-derived surface extent reflects optical surface reflections governed by baseflow, channel morphology, and local hydraulic controls, and does not establish chemical water quality without in-situ gauging.

### Step 7: Cartographic Map Inspection
In the **Cartographic Visualizations & Generated Maps** card:
1. Examine the **4-Class Categorical GIS Map Legend**:
   - Blue: Persistent Water
   - Teal: Apparent Water Gain
   - Amber: Apparent Water Loss
   - Slate Gray: Non-Water
2. Click between layer tabs:
   - `4-Panel Comparison Panel`: 300 DPI multi-panel figure displaying earlier/later RGBs, NDWI, and transition map.
   - `Observation T1 NDWI Map`: Calibrated Green-NIR index surface.
   - `Observation T2 NDWI Map`: Winter comparison surface.
   - `Water Change Transition Map`: High-contrast categorical dynamics map.
3. Observe that images stream securely via authenticated Bearer token blob requests.

### Step 8: Authenticated Report Downloads
In the **Scientific Report & Data Export** card:
1. Click **"PDF"**: Downloads a publication-ready **7.4 MB PDF** generated dynamically via ReportLab containing the complete study narrative, metadata banners, 300 DPI figures, KPI tables, and academic disclaimers.
2. Click **"CSV"**: Downloads structured tabular CSV data with immutable provenance headers:
   ```csv
   # Data Provenance Provider,PUBLIC_OPEN_SENTINEL2_COGS
   # Real Satellite Data,TRUE
   # Observation T1 (Earlier),S2A_MSIL2A_20231010T050721...,2023-10-10,0.00% cloud
   # Observation T2 (Later),S2A_MSIL2A_20231209T051211...,2023-12-09,0.00% cloud
   ```

---

## 5. Offline Demonstration Mode (Synthetic Benchmark Fallback)

If the evaluation environment lacks internet access or experiences firewall restrictions:
1. In the **Retrieval Tier** dropdown, select `Synthetic GIS Benchmark`.
2. Launch the analysis.
3. Observe the system's **strict provenance guardrails**:
   - The status badge renders in amber: `SYNTHETIC BENCHMARK`.
   - A prominent amber alert banner appears:
     > **SYNTHETIC BENCHMARK DATASET:** These surface water metrics were computed from an offline synthetic calibration sample. They do NOT represent genuine orbital Sentinel-2 acquisitions.
   - The downloaded CSV explicitly outputs `# Real Satellite Data,FALSE (SYNTHETIC BENCHMARK SAMPLE)`.

---

## 6. Automated Quality Verification Commands

To independently verify test coverage and code health during evaluation, run:

```powershell
# 1. Full Backend Test Suite (185 passed, 1 skipped)
python -m pytest -v

# 2. Frontend Unit & Component Tests (18 passed)
npm --prefix frontend test -- --run

# 3. Production Bundle Build (Zero TypeScript errors)
npm --prefix frontend run build

# 4. Automated Playwright Headless Browser E2E Test (8/8 passed)
node scripts/validate_real_satellite_browser.mjs
```
