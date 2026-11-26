# DharaScope — Automated Satellite-Based Surface Water Dynamics Platform

> **Scope Statement:** DharaScope performs **optical satellite-based surface-water detection and two-date water-area change analysis** using Sentinel-2 multispectral imagery and deterministic Normalized Difference Water Index (**NDWI**) thresholding. It does **not** measure water pollution, chemical/biological water quality, water depth (bathymetry), or water volume, and its core water-detection algorithm is **spectral index computation rather than machine learning**.

---

## 1. Project Overview & Objective

**DharaScope** is a full-stack Geospatial Information System (GIS) web platform and reproducible Earth Observation pipeline built to detect surface water extent and quantify multi-temporal water-body changes from **Copernicus Sentinel-2 Level-2A** optical imagery.

### Problem Statement
Conventional satellite water-mapping workflows typically require downloading entire ~500–800 MB Sentinel-2 `.SAFE` tiles manually, managing coordinate reference systems and spatial clipping in desktop GIS software, and writing ad-hoc scripts that are difficult to reproduce, secure for multiple users, or summarize cleanly for technical evaluation.

### Why DharaScope Is Useful
- **Bandwidth-Efficient Cloud Streaming:** Streams only the Area of Interest (AOI) bounding window from Cloud-Optimized GeoTIFFs (COGs) via GDAL `/vsicurl/`, transferring megabytes/kilobytes instead of gigabyte archives.
- **Deterministic & Reproducible:** Uses a fixed, transparent physical spectral index (McFeeters NDWI) over a strictly aligned common valid-pixel mask ($T_1 \cap T_2$) with machine-readable CSV manifests and 300 DPI ReportLab PDF reports.
- **Multi-Tenant GIS Security:** Combines Leaflet AOI digitization, PostGIS spatial validation (`0.10–100.00 km²`, `<= 500` vertices), Supabase JWT verification, and database-enforced PostgreSQL Row-Level Security (RLS).

---

## 2. How DharaScope Works (Scientific & System Pipeline)

```text
[1. AOI Digitization (React + Leaflet)]
        │  GeoJSON Polygon (WGS84 / EPSG:4326)
        ▼
[2. Spatial Validation (FastAPI + Shapely + PyProj + PostGIS)]
        │  Verify topology, <= 500 vertices, geodesic area 0.10–100.00 km²
        ▼
[3. Scene Discovery (Copernicus CDSE STAC API v1)]
        │  Select optimal low-cloud Sentinel-2 L2A pair (T1, T2)
        ▼
[4. Band Retrieval (Multi-Tier Downloader)]
        │  Tier 1: CDSE OData JP2  |  Tier 2: AWS S2 COG (/vsicurl/)  |  Tier 3: Tagged Synthetic Fallback
        ▼
[5. NDWI & Change Detection Engine (Rasterio + NumPy)]
        │  NDWI = (B03 - B08) / (B03 + B08) -> Mask (NDWI > 0.0) -> 4-Class Transitions
        ▼
[6. Visualization, Storage & Reporting]
           300 DPI PNG Cartography + Structured CSV Manifest + ReportLab PDF Report
```

### Sentinel-2 Data & Spectral Bands Used
DharaScope queries **Sentinel-2 MSI Level-2A** (Bottom-of-Atmosphere surface reflectance) products at native **10 m spatial resolution** ($100\text{ m}^2 = 0.01\text{ ha}$ per pixel):
- **Band 3 (`B03`, Green, ~560 nm, 10 m GSD):** Water exhibits moderate green reflectance compared to longer wavelengths.
- **Band 8 (`B08`, Near-Infrared / NIR, ~842 nm, 10 m GSD):** Clear open water strongly absorbs NIR radiation (near-zero reflectance), whereas vegetation and dry bare soil reflect NIR strongly.

### NDWI Formula & Water Classification
DharaScope implements the **McFeeters (1996) Normalized Difference Water Index (NDWI)** in [src/water_indices.py](src/water_indices.py):

$$\text{NDWI} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$$

- **Zero-Denominator & Range Protection:** Pixels where $|\text{B03} + \text{B08}| \le 10^{-6}$ or either band contains NoData are masked as invalid; valid values are clamped to $[-1.0, 1.0]$.
- **Binary Classification:** Using default cutoff $\tau = 0.00$ (configurable in $[-0.30, 0.30]$ via the UI/API):
  - $\text{NDWI} > \tau \implies \text{Water}$ (`1`)
  - $\text{NDWI} \le \tau \implies \text{Non-Water}$ (`0`)

### Temporal Comparison & Water-Area Change Calculation
To avoid comparing pixels where one date is obscured or missing, [src/change_detection.py](src/change_detection.py) restricts analysis strictly to the **common valid pixel intersection** ($\text{Valid}_{T_1} \land \text{Valid}_{T_2}$) and assigns every valid pixel to one of **four categorical transition classes**:

1. **Persistent Water (`1 -> 1`):** Surface water detected on both $T_1$ and $T_2$.
2. **Apparent Water Loss / Recession (`1 -> 0`):** Classified as water at $T_1$ and non-water at $T_2$.
3. **Apparent Water Gain / Expansion (`0 -> 1`):** Classified as non-water at $T_1$ and water at $T_2$.
4. **Persistent Non-Water (`0 -> 0`):** Classified as non-water on both dates.

Quantitative area metrics convert pixel counts at pixel area $A_{\text{px}}$ (nominally $100\text{ m}^2 = 0.01\text{ ha}$ in projected UTM coordinates, e.g., EPSG:32644 for Lucknow):
- $A_{T_1} = N_{T_1} \times A_{\text{px}}$, $A_{T_2} = N_{T_2} \times A_{\text{px}}$
- $\Delta A = A_{T_2} - A_{T_1}$, $\%\Delta A = \frac{A_{T_2} - A_{T_1}}{A_{T_1}} \times 100$ (handled safely when $A_{T_1} = 0$).

#### Verified Reference Results (Gomti River, Lucknow — Real Sentinel-2 L2A)
Scenes: `2023-10-10` ($T_1$, `0.0%` scene cloud) vs. `2023-12-09` ($T_2$, `0.0%` scene cloud), NDWI $> 0.00$:

| Study Envelope | Bounding Box (`EPSG:4326`) | Study Extent | $T_1$ Water Area | $T_2$ Water Area | Net Area Change | Observed Satellite Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Historical Phase 1 Macro Basin** *(exceeds current 100 km² cap)* | `[80.88, 26.80, 81.00, 26.90]` | `132.30 km²` (`13,230.37 ha` valid) | `184.56 ha` (`18,456 px`) | `139.33 ha` (`13,933 px`) | **`-45.23 ha` (`-24.51%`)** | Regional floodplain and shallow depression recession post-monsoon. |
| **Operational Urban Gomti Study Reach** *(within 100 km² limit)* | `[80.90, 26.84, 80.92, 26.86]` | `4.40 km²` (`441.78 ha` / `44,178` inner px; `44,600` outer px) | `0.53 ha` (`53 px`) | `1.66 ha` (`166 px`) | **`+1.13 ha` (`+213.21%`)** | Confined urban reach showed localized expansion in open-water optical reflectance (`50 px` persistent, `116 px` gain, `3 px` loss). |

> [!NOTE]
> Detected water pixel counts (`53` at $T_1$, `166` at $T_2$, net `+113`) are identical across both the `44,178`-pixel clipped inner window and `44,600`-pixel outer raster grid. Observed differences between macro-basin recession and urban-reach expansion reflect spatial heterogeneity across different landscape units; optical satellite data alone cannot establish subsurface hydrology or barrage/hydraulic operations without in-situ river gauge data.

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite 8, Leaflet (Esri World Dark Gray Canvas base + reference label tiles), Lucide React |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn (ASGI), Pydantic |
| **Geospatial & Reporting** | Rasterio, GDAL (`/vsicurl/`), NumPy, Shapely, PyProj, Matplotlib (300 DPI), ReportLab (PDF), CSV |
| **Database & Migrations** | PostgreSQL 16/17 + PostGIS 3.3/3.6, SQLAlchemy 2.x, GeoAlchemy2, Alembic, `psycopg2-binary` |
| **Auth & Security** | Supabase Auth (`HS256` & `ES256`/`RS256` JWKS), PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY` + `dharascope_app` role), anti-privilege-escalation checks |
| **Object Storage** | `LocalStorageBackend` (`outputs/` for dev) and `SupabaseStorageBackend` (private `rasters`, `maps`, `reports` buckets in production) |
| **Testing & Tooling** | Pytest, Vitest, React Testing Library, Oxlint, TypeScript `tsc`, GitHub Actions CI, Docker, Render Blueprint |

---

## 4. System Architecture

```text
+-----------------------------------------------------------------------------+
|                             Presentation Tier                               |
|        React 19 + TypeScript + Vite Static Site + Leaflet MapPicker         |
+--------------------------------------+--------------------------------------+
                                       | HTTPS + Supabase Bearer JWT
+--------------------------------------v--------------------------------------+
|                           API & Service Tier                                |
|                      FastAPI ASGI Server (`server.py`)                      |
|  - /health, /health/db                  - /api/v1/auth/me, /admin/users     |
|  - /api/v1/aois/validate, /api/v1/aois  - /api/v1/analyses, /reports/{pdf,csv} |
+--------------------+------------------------------------+-------------------+
                     |                                    |
+--------------------v-------------------+  +-------------v-------------------+
|        Data & Persistence Tier         |  |    Satellite Processing Core      |
|  PostgreSQL + PostGIS (Supabase/Local) |  |  - CDSE STAC Search               |
|  - profiles, aois (POLYGON 4326 GiST)  |  |  - AWS COG / CDSE Band Streamer   |
|  - analysis_runs, water_metrics        |  |  - McFeeters NDWI (B03 / B08)     |
|  - analysis_artifacts (metadata only)  |  |  - 4-Class Change Detection       |
|  - Forced RLS (`dharascope_app`)       |  |  - 300 DPI Cartography & PDF/CSV  |
+--------------------+-------------------+  +-------------+-------------------+
                     |                                    |
                     +------------------+-----------------+
                                        v
                        Private Object Storage (`rasters`, `maps`, `reports`)
```

For database entity diagrams and detailed component contracts, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md).

---

## 5. Repository Structure

```text
DharaScope/
├── src/                               # Backend application, geospatial core, API & DB layers
│   ├── api/                           # FastAPI app factory, dependencies, routers & Pydantic schemas
│   ├── database/                      # SQLAlchemy models, URL/SSL config & pooled sessions
│   ├── services/                      # AOI, analysis, artifact & two-phase role-sync services
│   ├── aoi_validation.py              # Geodesic area (0.10–100 km²) & Shapely geometry checks
│   ├── auth.py                        # Supabase JWT/JWKS validation & RLS context propagation
│   ├── change_detection.py            # Common-valid intersection & 4-class transition matrix
│   ├── config.py                      # Environment loading, CORS origins & startup validation
│   ├── downloader.py                  # CDSE OData, AWS COG (/vsicurl/) & synthetic fallback
│   ├── reporting.py                   # CSV manifest & ReportLab PDF compiler
│   ├── scene_selection.py             # Temporal pair & cloud-cover optimization
│   ├── stac_client.py                 # Copernicus CDSE STAC discovery client
│   ├── storage.py                     # Local & Supabase private object storage abstraction
│   ├── visualization.py               # 300 DPI comparison panels, NDWI & change maps
│   └── water_indices.py               # McFeeters NDWI computation & water segmentation
├── frontend/                          # React 19 + Vite + TypeScript GIS workstation
│   ├── public/                        # Static assets & Render SPA `_redirects` rule
│   ├── src/                           # Components (`MapPicker`, `AuthModal`, etc.), API & Auth context
│   ├── .env.example                   # Frontend placeholder env variables (`VITE_*`)
│   ├── package.json                   # Frontend scripts (`dev`, `build`, `lint`, `test`)
│   └── vite.config.ts                 # Vite & Vitest configuration
├── alembic/                           # Database migrations (`53ebad6d6a09` -> `5903f15a19ed`)
├── tests/                             # 18 Pytest modules (unit, API, RLS, PostGIS, cloud config)
├── docs/                              # Technical reports, SRS, defense scripts & deployment guides
├── scripts/                           # Presentation generator & Playwright verification harness
├── artifacts/                         # Preserved demo outputs (PPTX, maps, PDF/CSV reports, captures)
├── data/                              # Local raw raster cache directory (rasters gitignored)
├── outputs/                           # Runtime output scratch directory (contents gitignored)
├── logs/                              # Runtime log directory (contents gitignored)
├── .github/workflows/ci.yml           # GitHub Actions CI for backend pytest & frontend build/tests
├── server.py                          # Production/local FastAPI Uvicorn ASGI entrypoint
├── app.py                             # Optional Streamlit GIS dashboard (Phase 1 baseline UI)
├── main.py                            # Standalone CLI pipeline runner
├── Dockerfile                         # Non-root Python 3.11 FastAPI + Rasterio container image
├── render.yaml                        # Render Blueprint (Docker Web Service + Static Site)
├── requirements.txt                   # Python dependencies
├── .env.example                       # Backend placeholder environment configuration
└── README.md                          # Project overview, setup, methodology & evaluation guide
```

---

## 6. Local Setup Instructions

### Prerequisites
- **Python:** 3.11+
- **Node.js & npm:** Node.js 20 LTS (or 18+)
- **Database:** PostgreSQL 16+ with the PostGIS 3.x extension enabled

### 1. Clone the Repository
```bash
git clone https://github.com/Akshat-2923/END_SEM_PROJECT_AKSHAT_3274.git
cd END_SEM_PROJECT_AKSHAT_3274
```

### 2. Configure Environment Variables (Placeholders Only)
Copy the provided templates and populate your own local or Supabase credentials (**never commit `.env` files**):

```bash
# Linux / macOS
cp .env.example .env
cp frontend/.env.example frontend/.env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

Key backend variables in `.env` (from [.env.example](.env.example)):
```ini
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/dharascope
TEST_DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/dharascope_test
DB_SSL_MODE=
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_ANON_KEY=<your-supabase-anon-or-publishable-key>
SUPABASE_SERVICE_ROLE_KEY=<your-supabase-service-role-key>
SUPABASE_JWT_SECRET=<your-supabase-jwt-secret>
# Or for asymmetric ES256/RS256 tokens:
# SUPABASE_JWKS_URL=https://<your-project-ref>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_STORAGE_ENABLED=false
```

Key frontend variables in `frontend/.env` (from [frontend/.env.example](frontend/.env.example)):
```ini
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_SUPABASE_URL=https://<your-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-supabase-anon-or-publishable-key>
```

### 3. Install Backend Dependencies & Apply Migrations
```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
```

### 4. Install Frontend Dependencies
```bash
npm --prefix frontend install
```

---

## 7. Running the Application & Tests

### Run Backend & Frontend Locally
Open two terminals:

- **Terminal 1 — FastAPI Backend (`http://127.0.0.1:8000`):**
  ```bash
  uvicorn server:app --host 127.0.0.1 --port 8000 --reload
  ```
  Interactive API docs: `http://127.0.0.1:8000/docs` | DB diagnostics: `http://127.0.0.1:8000/health/db`

- **Terminal 2 — React + Vite Frontend (`http://127.0.0.1:5173`):**
  ```bash
  npm --prefix frontend run dev
  ```

- *(Optional Phase 1 UI / CLI)* Run `streamlit run app.py` or `python main.py`.

### Verification Commands
```bash
# Backend Pytest suite
pytest tests/ -v

# Frontend Vitest suite, static linter, and production build
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 8. Cloud Deployment Summary

DharaScope is configured for production deployment across **Render** and **Supabase**:
- **Frontend (Render Static Site):** `https://dharascope-frontend.onrender.com` — built from `frontend/` (`npm install && npm run build`, publish `dist/`, SPA rewrite via [frontend/public/_redirects](frontend/public/_redirects)).
- **Backend (Render Docker Web Service):** `https://dharascope-backend.onrender.com` — built from [Dockerfile](Dockerfile) as non-root `appuser` serving FastAPI over `$PORT` with OpenAPI docs at `/docs`.
- **Database, Auth & Storage (Dedicated Supabase Project `iyjvjapdzbnzsrfvrctl`, `ap-southeast-1`):** PostgreSQL 17.12 + PostGIS `3.3.7` (`extensions` schema), Alembic revisions `53ebad6d6a09` $\to$ `5903f15a19ed`, `dharascope_app` RLS role with 20 forced-RLS policies, and private `rasters`, `maps`, and `reports` buckets.

Required Render Backend env vars for live cross-origin operation (defined in [render.yaml](render.yaml) and [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)):
- `ENVIRONMENT=production`
- `FRONTEND_URL=https://dharascope-frontend.onrender.com`
- `DATABASE_URL` (Supabase IPv4 Session Pooler `:5432`) & `DB_SSL_MODE=require`
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET` and/or `SUPABASE_JWKS_URL`
- `SUPABASE_STORAGE_ENABLED=true`

---

## 9. Current Limitations & Future Scope

### Current Limitations
- **Optical & Physical Boundaries:** Optical Sentinel-2 imagery cannot penetrate dense cloud cover; NDWI detects surface water extent only and does **not** measure water quality, turbidity chemistry, depth, or volume.
- **Spatial Envelope Bounds:** AOIs are validated between `0.10 km²` and `100.00 km²` (`<= 500` vertices) to maintain bounded memory and interactive processing times.
- **In-Process Task Queue:** Background pipeline runs execute via FastAPI `BackgroundTasks` and do not survive worker restarts; concurrent 300 DPI Matplotlib rendering should stay within 2–3 simultaneous runs per container.
- **Render Free-Tier Cold Starts:** Initial requests after idle periods on Render free instances incur container wake-up latency (~30–50 s).

### Future Scope
- **All-Weather SAR Fusion:** Integrate Sentinel-1 C-band Synthetic Aperture Radar (SAR) backscatter to maintain flood and channel mapping under persistent monsoon cloud cover.
- **Multi-Date Time-Series Analytics:** Support $N$-date seasonal hydrograph area curves instead of pairwise ($T_1$, $T_2$) comparison alone.
- **Durable Distributed Queue:** Migrate background analysis execution from in-process `BackgroundTasks` to Redis + Celery/ARQ workers.

---

## 10. Documentation & Evaluation Sitemap

| Document / Artifact | Purpose |
| :--- | :--- |
| [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | Complete academic capstone project report |
| [docs/SCIENTIFIC_METHODOLOGY.md](docs/SCIENTIFIC_METHODOLOGY.md) | Sentinel-2 physics, McFeeters NDWI equations, and scale analysis |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, ER schema, and component interactions |
| [docs/SRS.md](docs/SRS.md) & [docs/SYSTEM_CONSTRAINTS.md](docs/SYSTEM_CONSTRAINTS.md) | Formal requirements specification and validated operational constraints |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Step-by-step Supabase + Render + Docker rollout guide |
| [docs/SUPABASE_INTEGRATION_REPORT.md](docs/SUPABASE_INTEGRATION_REPORT.md) | Live dedicated Supabase (`iyjvjapdzbnzsrfvrctl`) schema, RLS, PostGIS & Storage audit |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) & [docs/FINAL_DEFENSE_SCRIPT.md](docs/FINAL_DEFENSE_SCRIPT.md) | Practical demonstration script and oral defense walkthrough |
| [docs/JUDGE_QA.md](docs/JUDGE_QA.md) | Viva / examiner Q&A reference guide |
| [artifacts/presentation/DharaScope_Final_Presentation.pptx](artifacts/presentation/DharaScope_Final_Presentation.pptx) | 15-slide evaluation presentation deck |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) & [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | Live subsystem status and verification ledger |
