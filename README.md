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

### Multi-Scale Hydro-Spatial Dynamics

Remote sensing observations of surface water vary fundamentally across spatial scales. DharaScope highlights this principle through two validated analytical scales:

| Dimension / Metric | Macro-Scale Regional Basin (Phase 1 Baseline) | Meso-Scale Urban Reach (Phase 2.4/2.5 Operational) |
| :--- | :--- | :--- |
| **Spatial Bounding Box** | `[80.88, 26.80, 81.00, 26.90]` | `[80.90, 26.84, 80.92, 26.86]` |
| **Geographic Extent** | $132.30\text{ km}^2$ ($13,230\text{ ha}$) | $4.40\text{ km}^2$ ($441.78\text{ ha}$) |
| **Operational Limit Status** | **Exceeds $100\text{ km}^2$ limit** (Historical experiment) | **Within $100\text{ km}^2$ limit** (Standard operational) |
| **Grid Dimensions** | $1,110 \times 1,192\text{ pixels}$ ($1,323,120\text{ px}$) | $222 \times 199\text{ pixels}$ ($44,178\text{ px}$) |
| **$T_1$ Water Area (2023-10-10)** | **$184.56\text{ ha}$** ($18,456\text{ px}$) | **$0.53\text{ ha}$** ($53\text{ px}$) |
| **$T_2$ Water Area (2023-12-09)** | **$139.33\text{ ha}$** ($13,933\text{ px}$) | **$1.66\text{ ha}$** ($166\text{ px}$) |
| **Net Water Dynamics ($\Delta A$)** | **$-45.23\text{ ha}$** ($-24.51\%$ Net Loss) | **$+1.13\text{ ha}$** ($+213.21\%$ Net Gain) |
| **Permanent Water Area** | $\approx 112.4\text{ ha}$ | **$0.50\text{ ha}$** ($50\text{ px}$) |
| **Inundation / Gain Area** | $\approx 26.9\text{ ha}$ | **$1.16\text{ ha}$** ($116\text{ px}$) |
| **Recession / Loss Area** | $\approx 72.1\text{ ha}$ | **$0.03\text{ ha}$** ($3\text{ px}$) |
| **Persistent Land Area** | $\approx 13,018\text{ ha}$ | **$440.09\text{ ha}$** ($44,009\text{ px}$) |
| **Hydrological Synthesis** | Broad agricultural floodplains and shallow depressions naturally dry out post-monsoon. | Confined urban reach exhibits channel expansion due to baseflow stabilization and potential local drainage/weir factors. |

> [!NOTE]
> **Scientific Integrity Notice:** The observed $+1.13\text{ ha}$ increase in the urban channel reach is attributed to post-monsoon baseflow stabilization and potential local influences (such as urban drainage discharges, channel maintenance, or downstream barrage adjustments). Without in-situ stream gauge records and barrage operational logs, local hydraulic factors are presented as unverified hypotheses rather than proven causality.

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

## 5. Quickstart & Installation Guide

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

# 3. Initialize spatial database schema & PostGIS extensions
python -m src.db.migrate
```

### Step 3: Frontend Installation
```bash
cd frontend
npm install
cd ..
```

### Step 4: Launch Application Services
Open two terminal windows:

**Terminal 1 (Backend API):**
```bash
# With .venv activated
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
*API Swagger Documentation will be available at: `http://127.0.0.1:8000/docs`*

**Terminal 2 (Frontend Client):**
```bash
cd frontend
npm run dev
```
*Web GIS Interface will be available at: `http://127.0.0.1:5173`*

---

## 6. Verification & Automated Quality Assurance

### Automated Pytest Suite (Backend)
Run the 16 test modules covering API contracts, spatial queries, RLS policies, NDWI accuracy, and PDF generation:
```bash
pytest -v
```
*Expected: 185 Passed, 1 Skipped (live CDSE credential test).*

### Frontend Vitest & Static Analysis
```bash
# Run unit & component tests
npm --prefix frontend test -- --run

# Run static linter
npx --prefix frontend oxlint

# Run production build validation
npm --prefix frontend run build
```

### Automated Headless Browser Validation (Playwright)
Verify the entire end-to-end user journey on live running servers:
```bash
node scripts/validate_real_satellite_browser.mjs
```
*Executes all 8 steps, tests real orbital Sentinel-2 data, confirms metrics (0.53 ha $\to$ 1.66 ha), and verifies PDF/CSV downloads.*

---

## 7. Project Documentation Sitemap

| Document | Purpose & Contents |
| :--- | :--- |
| [docs/PROJECT_REPORT.md](file:///d:/Coding/Projects/DharaScope/docs/PROJECT_REPORT.md) | **Complete Academic Capstone Report:** Problem statement, literature review, requirements, architecture, multi-scale findings, and ethics. |
| [docs/ARCHITECTURE.md](file:///d:/Coding/Projects/DharaScope/docs/ARCHITECTURE.md) | **System Architecture:** Detailed component interactions, data flows, security boundaries, and Mermaid diagrams. |
| [docs/DEMO_GUIDE.md](file:///d:/Coding/Projects/DharaScope/docs/DEMO_GUIDE.md) | **Demonstration Guide:** Step-by-step evaluation script for examiners, judges, and reviewers. |
| [docs/SCIENTIFIC_METHODOLOGY.md](file:///d:/Coding/Projects/DharaScope/docs/SCIENTIFIC_METHODOLOGY.md) | **Earth Observation Methodology:** Sentinel-2 sensor physics, McFeeters NDWI, windowed streaming, and scale dynamics. |
| [docs/SYSTEM_CONSTRAINTS.md](file:///d:/Coding/Projects/DharaScope/docs/SYSTEM_CONSTRAINTS.md) | **Operational Constraints:** Approved MVP boundaries, $100\text{ km}^2$ size limit, and security guardrails. |
| [docs/TECHNICAL_DECISIONS.md](file:///d:/Coding/Projects/DharaScope/docs/TECHNICAL_DECISIONS.md) | **Architecture Decision Records (ADRs):** Technical rationale for COGs, McFeeters NDWI, PostGIS RLS, and role journals. |

---

## 8. License & Academic Disclaimer

This project is licensed under the **MIT License** — see the [LICENSE](file:///d:/Coding/Projects/DharaScope/LICENSE) file for details.

**Academic & Operational Disclaimer:**  
DharaScope was developed as an academic capstone research project. While satellite observations and spectral calculations utilize verified Copernicus Sentinel-2 Level-2A surface reflectance data, hydrological change assessments should be corroborated with in-situ river gauge hydrographs and official municipal records before making flood defense, irrigation, or engineering decisions.
