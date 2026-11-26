# DharaScope — Automated Satellite-Based Surface Water Dynamics Monitoring Platform
## Enterprise Geospatial Information System (GIS) for Surface Water Change Detection

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![PostGIS 3.6](https://img.shields.io/badge/PostGIS-3.6-2E7D32.svg)](https://postgis.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Executive Summary

**DharaScope** is an end-to-end, open-source geospatial platform designed for automated, reproducible surface water detection and multi-temporal change monitoring. Leveraging the European Space Agency's (ESA) Copernicus Sentinel-2 constellation, DharaScope bridges raw aerospace multispectral observations down to an interactive modern web GIS workstation.

The platform eliminates the need for manual, heavyweight GIS workflows by streaming sub-granule spectral data via Cloud-Optimized GeoTIFFs (COGs), applying calibrated McFeeters Normalized Difference Water Index (NDWI) algorithms at 10-meter resolution, and computing 4-class categorical water transitions (Permanent Water, Water Inundation, Water Recession, Persistent Land) with strict mathematical verification.

Built for multi-tenant deployments, DharaScope implements defense-in-depth isolation via PostgreSQL Row-Level Security (RLS) tied to Supabase JWT authentication, authoritative database role checks, and automated generation of publication-grade cartographic figures (300 DPI) and comprehensive PDF/CSV analytical reports.

---

## 2. Core Architectural Features

- **Interactive Cartographic Digitization:** User-defined polygon Areas of Interest (AOIs) up to $100\text{ km}^2$ digitized via an interactive Leaflet web canvas with real-time topological validation (`ST_IsValid`, `ST_Area`).
- **Sub-Granule COG Streaming (`/vsicurl/`):** Byte-range HTTP requests extract only the required spectral bands (B03 Green, B08 NIR) intersecting the AOI bounding box, transferring kilobytes instead of full gigabyte granules.
- **Calibrated McFeeters NDWI Engine:** Computes $(\text{B03} - \text{B08}) / (\text{B03} + \text{B08})$ at native 10m Ground Sampling Distance (GSD) with zero-threshold classification ($\text{NDWI} > 0.0$) and valid-data masking.
- **Categorical 4-Class Transition Matrix:** Quantifies permanent water, inundation/gain, recession/loss, and persistent land, reporting both hectare areas and percentage dynamics.
- **Defense-in-Depth Multi-Tenancy:** PostgreSQL Row-Level Security (RLS) enforced at the database kernel level using transaction-local context (`SET LOCAL app.current_user_id`), preventing cross-tenant leakage.
- **Authoritative Database Role Verification:** Administrative actions check user privileges against the authoritative database `profiles` table, immediately revoking access even if a client possesses an unexpired JWT.
- **Dual Storage Abstraction:** Seamlessly switches between local filesystem storage (development) and Supabase Storage (production) with signed, time-limited URL generation.
- **Automated Publication Reporting:** Compiles 300 DPI publication cartography and analytical metrics into downloadable, audit-ready PDF reports (7.4+ MB) and CSV datasets.

---

## 3. Verified Scientific Findings: Gomti River Case Study

The platform has been empirically validated against real Copernicus Sentinel-2 Level-2A observations covering the Gomti River basin in Lucknow, Uttar Pradesh, India.

```
Observation T1 (Early Post-Monsoon):
- Granule: S2A_MSIL2A_20231010T051831_N0509_R019_T44RMQ_20231010T075727
- Acquisition Date: 2023-10-10 | Sun Elevation: 56.41° | Cloud Cover: 0.0%

Observation T2 (Late Post-Monsoon / Early Winter):
- Granule: S2A_MSIL2A_20231209T052211_N0510_R019_T44RMQ_20231209T080826
- Acquisition Date: 2023-12-09 | Sun Elevation: 40.18° | Cloud Cover: 0.0%
```

### Environmental Spatial Heterogeneity & Scale Analysis

Multi-temporal observations of surface water reflect the environmental characteristics of specific landscape units. DharaScope highlights this principle through two validated analytical envelopes:

| Dimension / Metric | Macro-Scale Regional Basin (Phase 1 Baseline) | Meso-Scale Urban Reach (Phase 2.4/2.5 Operational) |
| :--- | :--- | :--- |
| **Spatial Bounding Box** | `[80.88, 26.80, 81.00, 26.90]` | `[80.90, 26.84, 80.92, 26.86]` |
| **Geographic Extent** | $132.30\text{ km}^2$ ($13,230\text{ ha}$) | $4.40\text{ km}^2$ ($441.78\text{ ha}$) |
| **Operational Limit Status** | **Exceeds $100\text{ km}^2$ limit** (Historical experiment) | **Within $100\text{ km}^2$ limit** (Standard operational) |
| **Grid Dimensions** | $1,110 \times 1,192\text{ pixels}$ ($1,323,120\text{ px}$) | $222 \times 199\text{ px}$ (Inner: 44,178 px) / $223 \times 200\text{ px}$ (Outer: 44,600 px) |
| **$T_1$ Water Area (2023-10-10)** | **$184.56\text{ ha}$** ($18,456\text{ px}$) | **$0.53\text{ ha}$** ($53\text{ px}$) |
| **$T_2$ Water Area (2023-12-09)** | **$139.33\text{ ha}$** ($13,933\text{ px}$) | **$1.66\text{ ha}$** ($166\text{ px}$) |
| **Net Water Dynamics ($\Delta A$)** | **$-45.23\text{ ha}$** ($-24.51\%$ Net Loss) | **$+1.13\text{ ha}$** ($+213.21\%$ Net Gain) |
| **Permanent Water Area** | $\approx 112.4\text{ ha}$ | **$0.50\text{ ha}$** ($50\text{ px}$) |
| **Inundation / Gain Area** | $\approx 26.9\text{ ha}$ | **$1.16\text{ ha}$** ($116\text{ px}$) |
| **Recession / Loss Area** | $\approx 72.1\text{ ha}$ | **$0.03\text{ ha}$** ($3\text{ px}$) |
| **Persistent Land Area** | $\approx 13,018\text{ ha}$ | **$440.09\text{ ha}$** ($44,009\text{ px}$) |
| **Landscape Zone Dynamics** | Broad agricultural floodplains and shallow depressions naturally dry out post-monsoon. | Confined urban river corridor exhibits localized expansion in open-water reflectance footprint. |

> [!NOTE]
> **Scientific Integrity Notice:** The observed $+1.13\text{ ha}$ increase in the urban channel reach represents satellite-derived changes in optical surface reflectance (NDWI > 0.00). In both the 44,178-pixel inner window and the 44,600-pixel outer window, the detected water pixels (53 at $T_1$, 166 at $T_2$, net $+113$) are mathematically invariant. This localized expansion contrasts with regional floodplain recession due to environmental spatial heterogeneity across diverse landscape zones. Satellite data measures planar surface reflections; remote sensing cannot prove subsurface hydrological causes or hydraulic operations without in-situ gauging data.

---

## 4. System Architecture

```
+---------------------------------------------------------------------------------+
|                               Presentation Tier                                 |
|               React 19 + TypeScript + Vite + Leaflet Cartography                |
+----------------------------------------+----------------------------------------+
                                         | HTTPS / Bearer JWT
+----------------------------------------v----------------------------------------+
|                               API & Service Tier                                |
|                        FastAPI ASGI Server (Port 8000)                          |
|         - /api/v1/auth (JWT Validation)   - /api/v1/aois (Spatial Bounding)     |
|         - /api/v1/analyses (Pipelines)    - /reports (PDF & CSV Streaming)      |
+-------------------+------------------------------------+------------------------+
                    |                                    |
+-------------------v-------------------+    +-----------v------------------------+
|       Data & Persistence Tier         |    |      Satellite Processing Core     |
|   PostgreSQL 16 + PostGIS 3.6         |    |   - STAC Discovery (CDSE / AWS)    |
|   - Row-Level Security (RLS)          |    |   - GDAL /vsicurl/ COG Streamer    |
|   - Spatial GiST Indices              |    |   - McFeeters NDWI Engine (B03/B08)|
|   - Strict Foreign Key Cascades       |    |   - 4-Class Transition Matrix      |
|   - Profiles, AOIs, Runs, Artifacts   |    |   - ReportLab 300 DPI PDF Engine   |
+---------------------------------------+    +------------------------------------+
```

For complete architectural specifications and database entity-relationship diagrams, see [docs/ARCHITECTURE.md](file:///d:/Coding/Projects/DharaScope/docs/ARCHITECTURE.md).

---

## 5. Repository Organisation & Directory Layout

```
DharaScope/
├── src/                          # Backend application, API, auth, database & processing logic
│   ├── api/                      # FastAPI app factory, dependencies, routers & Pydantic schemas
│   ├── database/                 # SQLAlchemy 2.0 models, PostgreSQL session & engine management
│   ├── services/                 # Domain business services (analyses, AOIs, artifacts, role sync)
│   ├── aoi_validation.py         # Geodetic area calculation (0.1–100 km²) & Shapely topological validation
│   ├── auth.py                   # Supabase JWT validation, local HS256 dev signer & RLS context injection
│   ├── change_detection.py       # 4-class categorical water transitions & area statistics
│   ├── config.py                 # Central environment configuration & directory bootstrapping
│   ├── downloader.py             # CDSE OData JP2 & AWS /vsicurl/ COG sub-granule byte-range streamer
│   ├── reporting.py              # Publication-grade ReportLab PDF compiler & CSV manifest exporter
│   ├── scene_selection.py        # Spatiotemporal STAC intersection & cloud cover filtering
│   ├── stac_client.py            # Copernicus Data Space Ecosystem (CDSE) STAC catalogue client
│   ├── storage.py                # Dual storage abstraction (LocalFilesystemStorage & SupabaseStorage)
│   ├── visualization.py          # 300 DPI 4-panel comparison cartography & single NDWI figures
│   └── water_indices.py          # Calibrated McFeeters NDWI computation & binary water segmentation
│
├── frontend/                     # Modern React 19 GIS Workstation
│   ├── src/                      # TypeScript components, Leaflet MapPicker, state & Supabase Auth
│   ├── package.json              # Client dependencies (React 19, Leaflet, Lucide, Tailwind, Vite)
│   └── vite.config.ts            # Fast Vite bundling & dev server configuration
│
├── tests/                        # Automated Pytest Suite (202 passed, 1 skipped)
│   ├── test_azure_database_config.py   # Azure PostgreSQL Flexible Server SSL & pooling tests
│   ├── test_frontend_integration.py    # Complete 8-stage end-to-end user journey tests
│   ├── test_admin_role_sync.py         # Role promotion/revocation & anti-split-brain verification
│   ├── test_api_service_layer.py       # REST API endpoint contracts & authorization tests
│   └── ...                             # Spatial queries, RLS, NDWI, download & storage test suites
│
├── alembic/                      # Database Migrations (PostgreSQL 16 + PostGIS 3.6)
│   ├── versions/                 # Versioned DDL migrations (schema, GiST indices, RLS policies)
│   └── env.py                    # Migration runner with cloud SSL negotiation support
│
├── docs/                         # Comprehensive Academic & Technical Documentation
│   ├── PROJECT_REPORT.md         # Final Capstone Report (submission-quality, 10 sections)
│   ├── ARCHITECTURE.md           # Technical Architecture & component interaction specifications
│   ├── AZURE_POSTGRESQL.md       # Azure Flexible Server deployment, SSL & SKU guide
│   ├── FINAL_DEFENSE_SCRIPT.md   # Oral defense rehearsal guide, timing cues & examiner Q&A
│   ├── PRESENTATION.md           # Slide-by-slide 15-slide master presentation guide
│   ├── JUDGE_QA.md               # Evaluator defense challenges with two-tier responses
│   ├── DEMO_GUIDE.md             # Cue-by-cue live examination demonstration runbook
│   ├── SCIENTIFIC_METHODOLOGY.md # Earth Observation physics, NDWI formulas & scale analysis
│   ├── SRS.md                    # Software Requirements Specification (IEEE 830 standard)
│   ├── SYSTEM_CONSTRAINTS.md     # Approved MVP boundaries, 100 km² ceiling & security invariants
│   └── TECHNICAL_DECISIONS.md    # Architecture Decision Records (ADRs)
│
├── scripts/                      # Setup, Maintenance & Demonstration Scripts
│   ├── generate_presentation.py  # Automated PPTX slide deck generator using python-pptx
│   └── validate_real_satellite_browser.mjs # Automated Playwright Chromium browser test harness
│
├── data/                         # Datasets & Spatial Bounding Inputs
│   ├── raw/                      # Local Sentinel-2 GeoTIFF samples (gitignored)
│   └── .gitkeep                  # Preserved repository directory marker
│
├── artifacts/                    # Generated Demonstration Assets & Evaluation Outputs
│   ├── presentation/             # DharaScope_Final_Presentation.pptx (15-slide master deck)
│   ├── validation_phase2_4/      # Verified live browser run screenshots (Steps 1–8) & CSVs
│   ├── maps/                     # 300 DPI comparison panels, NDWI maps & thumbnails
│   ├── reports/                  # Sample publication PDF reports & CSV manifests
│   └── metadata/                 # Copernicus STAC scene discovery JSON metadata
│
├── .github/                      # Repository Automation & Workflows
│   └── workflows/ci.yml          # GitHub Actions CI for backend pytest & frontend vitest/build
│
├── server.py                     # Uvicorn ASGI entrypoint for FastAPI (Port 8000)
├── app.py                        # Streamlit GIS dashboard entrypoint (Port 8501)
├── main.py                       # Phase 1 CLI pipeline entrypoint
├── alembic.ini                   # Alembic migration configuration
├── requirements.txt              # Production Python dependency manifest
├── .env.example                  # Environment configuration template (placeholders only)
├── .gitignore                    # Git exclusion rules (rasters, secrets, temp caches)
├── DEVELOPMENT_HISTORY.md        # Chronological engineering log across all phases
├── PROMPT_LOG.md                 # Full prompt audit trail with verification outcomes
├── CHANGELOG.md                  # Semantic Versioning release notes (v1.0.0 – v1.0.4)
└── PROJECT_STATUS.md             # Real-time subsystem health & verification summary
```

---

## 6. Quickstart & Installation Guide

### Prerequisites
- **Operating System:** Linux, macOS, or Windows 10/11
- **Python:** 3.11 or higher
- **Node.js:** v18.0+ (LTS recommended) and `npm`
- **PostgreSQL / PostGIS:** PostgreSQL 16+ with PostGIS 3.6 extension enabled

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/dhara-scope/dharascope.git
cd dharascope
```

Create and populate the local `.env` configuration file:
```ini
# Database Connection (PostgreSQL 16 + PostGIS)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dharascope

# Application Security & JWT
JWT_SECRET=your-secure-jwt-signing-key-minimum-32-chars
JWT_ALGORITHM=HS256
ENVIRONMENT=development

# Storage Abstraction (local | supabase)
STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=outputs/artifacts
```

### Step 2: Backend Setup & Spatial Database Migrations
```bash
# 1. Create and activate Python virtual environment
python -m venv .venv
# Linux / macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install core scientific dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Apply spatial database migrations & PostGIS/RLS schema
alembic upgrade head
```

### Step 3: Frontend Installation
```bash
cd frontend
npm install
cd ..
```

### Step 4: Launch Application Services
Open two terminal windows:

**Terminal 1 (Backend FastAPI Server):**
```bash
# With .venv activated
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
# Alternatively: python server.py
```
*API Swagger Documentation will be available at: `http://127.0.0.1:8000/docs`*  
*Database Diagnostics will be available at: `http://127.0.0.1:8000/health/db`*

**Terminal 2 (Frontend React Client):**
```bash
cd frontend
npm run dev
```
*Web GIS Interface will be available at: `http://127.0.0.1:5173`*

*(Optional) Launch Streamlit GIS Workstation (Phase 1 Baseline):*
```bash
streamlit run app.py
```
*Streamlit Interface will be available at: `http://127.0.0.1:8501`*

---

## 7. Verification & Automated Quality Assurance

### Automated Pytest Suite (Backend)
Run the 18 test modules covering API contracts, spatial queries, RLS policies, NDWI accuracy, Supabase/Azure database config, cloud deployment guards, and PDF generation:
```bash
pytest -v
```
*Expected: 211 Passed, 1 Skipped (live Supabase Storage external credential test).*

### Frontend Vitest & Static Analysis
```bash
# Run unit & component tests
npm --prefix frontend test

# Run static linter
npm --prefix frontend run lint

# Run production build validation
npm --prefix frontend run build
```
*Expected: 19 Passed across 6 test suites, 0 lint errors, clean build.*

### Automated Headless Browser Validation (Playwright)
Verify the entire end-to-end user journey on live running servers:
```bash
node scripts/validate_real_satellite_browser.mjs
```
*Executes all 8 steps, tests real orbital Sentinel-2 data, confirms metrics (0.53 ha $\to$ 1.66 ha), and verifies PDF/CSV downloads.*

---

## 8. Project Documentation & Artifacts Sitemap

| Document / Asset | Purpose & Contents |
| :--- | :--- |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | **Cloud Deployment Guide:** End-to-end production setup on Supabase (Postgres/PostGIS/Auth/Storage) + Render (Docker Web Service & Static Site). |
| [docs/DEPLOYMENT_AUDIT.md](docs/DEPLOYMENT_AUDIT.md) | **Deployment & Infrastructure Audit:** Technical review of compatibility, CORS, RLS portability, and storage security before deployment. |
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | **Cloud & Deployment Status:** Real-time ledger of completed, pending, and blocked deployment tasks alongside verified test counts. |
| [render.yaml](render.yaml) | **Render Blueprint:** Declarative multi-service deployment specification for FastAPI Docker backend and React Static Site. |
| [Dockerfile](Dockerfile) | **Backend Container:** Lightweight `python:3.11-slim-bookworm` container running non-root Uvicorn + Rasterio/GeoAlchemy2. |
| [artifacts/presentation/DharaScope_Final_Presentation.pptx](file:///d:/Coding/Projects/DharaScope/artifacts/presentation/DharaScope_Final_Presentation.pptx) | **15-Slide Master Deck:** Comprehensive academic presentation with dark geospatial styling and speaker notes. |
| [docs/PROJECT_REPORT.md](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md) | **Complete Academic Capstone Report:** Problem statement, literature review, requirements, architecture, multi-scale findings, and ethics. |
| [docs/ARCHITECTURE.md](file:///d:/Coding/Projects/DharaScope/docs/ARCHITECTURE.md) | **System Architecture:** Detailed component interactions, data flows, security boundaries, and Mermaid diagrams. |
| [docs/AZURE_POSTGRESQL.md](file:///d:/Coding/Projects/DharaScope/docs/AZURE_POSTGRESQL.md) | **Azure PostgreSQL Flexible Server Guide:** SKU specifications, `azure.extensions` configuration, TLS/SSL, and cloud migration runbooks. |
| [docs/DEMO_GUIDE.md](file:///d:/Coding/Projects/DharaScope/docs/DEMO_GUIDE.md) | **Demonstration Guide:** Step-by-step evaluation script for examiners, judges, and reviewers. |
| [docs/FINAL_DEFENSE_SCRIPT.md](file:///d:/Coding/Projects/DharaScope/docs/FINAL_DEFENSE_SCRIPT.md) | **Oral Defense Script:** 60s elevator pitch, 3-min technical breakdown, 5-min demo runbook, and examiner Q&A answers. |
| [docs/PRESENTATION.md](file:///d:/Coding/Projects/DharaScope/docs/PRESENTATION.md) | **Presentation Specification:** Slide-by-slide master slide transcript, visual layouts, and detailed speaker scripts. |
| [docs/JUDGE_QA.md](file:///d:/Coding/Projects/DharaScope/docs/JUDGE_QA.md) | **Examiner Defense Q&A:** Comprehensive responses to 30 evaluator questions with plain-language summaries and technical deep-dives. |
| [docs/SCIENTIFIC_METHODOLOGY.md](file:///d:/Coding/Projects/DharaScope/docs/SCIENTIFIC_METHODOLOGY.md) | **Earth Observation Methodology:** Sentinel-2 sensor physics, McFeeters NDWI, windowed streaming, and scale dynamics. |
| [docs/SYSTEM_CONSTRAINTS.md](file:///d:/Coding/Projects/DharaScope/docs/SYSTEM_CONSTRAINTS.md) | **Operational Constraints:** Approved MVP boundaries, $100\text{ km}^2$ size limit, and security guardrails. |
| [docs/TECHNICAL_DECISIONS.md](file:///d:/Coding/Projects/DharaScope/docs/TECHNICAL_DECISIONS.md) | **Architecture Decision Records (ADRs):** Technical rationale for COGs, McFeeters NDWI, PostGIS RLS, and role journals. |

---

## 9. License & Academic Disclaimer

This project is licensed under the **MIT License** — see the [LICENSE](file:///d:/Coding/Projects/DharaScope/LICENSE) file for details.

**Academic & Operational Disclaimer:**  
DharaScope was developed as an academic capstone research project. While satellite observations and spectral calculations utilize verified Copernicus Sentinel-2 Level-2A surface reflectance data, hydrological change assessments should be corroborated with in-situ river gauge hydrographs and official municipal records before making flood defense, irrigation, or engineering decisions.
