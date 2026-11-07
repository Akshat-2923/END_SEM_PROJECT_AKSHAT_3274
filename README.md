# DharaScope — Phase 1: Satellite Feasibility Validation

**DharaScope** is an earth observation project evaluating satellite-based surface water dynamics. Phase 1 validates the feasibility of detecting changes in water-covered area along the **Gomti River in Lucknow, Uttar Pradesh, India**, using Sentinel-2 Level-2A satellite imagery.

---

## ⚡ Presentation Quick-Reference & Evaluation Brief

> [!IMPORTANT]
> **College Presentation & Grading Reference (Phase 1 Feasibility)**  
> **Status**: Verified 100% complete. End-to-end pipeline executed with real Sentinel-2 satellite data.

| Component | Summary |
| :--- | :--- |
| **Study Area** | Gomti River, Lucknow, UP (`[80.88, 26.80, 81.00, 26.90]`, EPSG:4326 WGS84) |
| **Satellite Mission** | Sentinel-2A MSI Level-2A Bottom-Of-Atmosphere (BOA) Surface Reflectance |
| **Tile & Resolution** | Tile `T44RMQ` (100% spatial coverage), 10m Ground Sample Distance (GSD) |
| **Compared Dates** | **2023-10-10** (Post-Monsoon) vs **2023-12-09** (Early Winter) — 0.0% Cloud Cover |
| **Methodology** | Normalized Difference Water Index: $\text{NDWI} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$, threshold $\tau = 0.0$ |
| **Area Results** | $T_1$ (184.56 ha) $\rightarrow$ $T_2$ (139.33 ha) $\implies$ **Net Change: -45.23 ha (-24.51%)** |
| **Persistent Water**| **125.18 ha** |
| **Apparent Loss** | **59.38 ha** (seasonal post-monsoon baseflow drop & bank exposure) |
| **Apparent Gain** | **14.15 ha** |
| **Architecture** | Modular Python package (`stac_client`, `scene_selection`, `downloader`, `water_indices`, `change_detection`, `visualization`) |
| **Test Suite** | **22 automated unit/integration tests passing** (`pytest -v`) |
| **Demo Fallback** | Automatic fallback across CDSE Authenticated $\rightarrow$ Public Open S2 COGs $\rightarrow$ Synthetic Benchmark |

### 🚀 Exact Commands for Live Demo
```powershell
# 1. Activate Environment
.\.venv\Scripts\Activate.ps1

# 2. Run Live Pipeline (Real Sentinel-2 Satellite Data)
python main.py

# 3. View Master 4-Panel Comparison Map
Invoke-Item outputs\gomti_water_change_comparison_panel.png

# 4. (Optional) Run Test Suite Live
pytest -v

# 5. (Optional) Offline Classroom Fallback (No Internet)
python main.py --source synthetic
```

---

## 1. Objectives & Scope of Phase 1

- **Feasibility Objective**: Validate whether Sentinel-2 Level-2A multispectral observations can resolve surface water boundaries and detect changes along the Gomti River channel in Lucknow.
- **Study Area**: Gomti River segment, Lucknow, UP. Bounding box: `[80.88, 26.80, 81.00, 26.90]` (EPSG:4326 WGS84).
- **Satellite Data**: Sentinel-2 Level-2A (Surface Reflectance), Tile `T44RMQ` (10m resolution).
- **Scope Restriction**: Strict feasibility prototype. No frontend, authentication dashboards, databases, or cloud deployment in this phase.

---

## 2. Methodology & Formulations

### Spectral Water Index (NDWI)
Water surfaces exhibit high reflectance in the green spectrum and strong absorption in the near-infrared (NIR) spectrum. The Normalized Difference Water Index (McFeeters, 1996) is computed as:

$$\text{NDWI} = \frac{\text{B03 (Green)} - \text{B08 (NIR)}}{\text{B03 (Green)} + \text{B08 (NIR)}}$$

- **B03 (Green)**: 10m Ground Sample Distance (GSD), central wavelength ~560 nm.
- **B08 (NIR)**: 10m GSD, central wavelength ~842 nm.
- **Zero Denominator & Nodata Handling**: Pixels where $\text{B03} + \text{B08} \le 10^{-6}$ or where nodata values (0) are present are masked out as invalid (NaN) to prevent zero-division artifacts.

### Water Classification
Pixels with $\text{NDWI} > \tau$ (where $\tau = 0.0$ by default, configurable) within the valid spatial domain are classified as water:

$$\text{WaterMask} = (\text{NDWI} > \tau) \land \text{ValidMask}$$

### Multi-Temporal Change Matrix
Comparing two aligned observations ($T_1$ earlier, $T_2$ later) over the common valid spatial footprint:

| Class Code | Category | Condition |
| :---: | :--- | :--- |
| **0** | Non-Water | Non-water at both $T_1$ and $T_2$ |
| **1** | Persistent Water | Water at both $T_1$ and $T_2$ |
| **2** | Apparent Water Loss / Recession | Water at $T_1$, Non-water at $T_2$ |
| **3** | Apparent Water Gain / Expansion | Non-water at $T_1$, Water at $T_2$ |
| **255** | Invalid / Nodata | Nodata on either date |

$$\Delta \text{Area} = \text{Area}(T_2) - \text{Area}(T_1)$$
$$\text{Percentage Change} = \frac{\Delta \text{Area}}{\text{Area}(T_1)} \times 100\% \quad (\text{if } \text{Area}(T_1) > 0)$$

---

## 3. Verified Satellite Observations & Real Data Findings

Querying the live Copernicus Data Space Ecosystem STAC API (`sentinel-2-l2a` collection) over `[80.88, 26.80, 81.00, 26.90]` identified Sentinel-2 Tile **T44RMQ** providing **100% spatial intersection** with 0.0% cloud cover:

| Observation | Scene Identifier | Acquisition Date | Cloud Cover | Study Area Overlap |
| :--- | :--- | :--- | :---: | :---: |
| **$T_1$ (Earlier)** | `S2A_MSIL2A_20231010T050721_N0510_R019_T44RMQ_20241101T170510` | 2023-10-10 | 0.0% | 100.0% |
| **$T_2$ (Later)** | `S2A_MSIL2A_20231209T051211_N0510_R019_T44RMQ_20241102T132512` | 2023-12-09 | 0.0% | 100.0% |

### Real Satellite Quantitative Results (Lucknow Gomti River)

- **Earlier Observation ($T_1$, 2023-10-10, Post-Monsoon)**:
  - Surface water area: **184.56 hectares** (1,845,600 $m^2$, 18,456 pixels)
- **Later Observation ($T_2$, 2023-12-09, Early Winter)**:
  - Surface water area: **139.33 hectares** (1,393,300 $m^2$, 13,933 pixels)
- **Persistent Water Extent**: **125.18 hectares** (1,251,800 $m^2$)
- **Apparent Water Recession / Loss**: **59.38 hectares** (593,800 $m^2$)
- **Apparent Water Gain / Expansion**: **14.15 hectares** (141,500 $m^2$)
- **Net Absolute Area Change**: **-45.23 hectares** (-452,300 $m^2$)
- **Net Percentage Change**: **-24.51%**

*Interpretation*: The 24.5% net decline in apparent surface water extent between October and December 2023 reflects the expected post-monsoon baseflow recession and seasonal bank exposure along the middle reaches of the Gomti River basin.

---

## 4. Setup & Execution Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.11.9)
- Windows PowerShell (or bash/zsh)

### Installation (PowerShell)
```powershell
# 1. Navigate to project root
cd d:\Coding\Projects\DharaScope

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the End-to-End Pipeline

DharaScope provides three flexible data-access modes to ensure a bulletproof presentation on October 30:

```powershell
# Mode 1: Default / Auto Mode (Recommended)
# Automatically uses CDSE if credentials exist; otherwise retrieves real Sentinel-2 Level-2A
# satellite data from the public open COG archive without requiring any login!
python main.py

# Mode 2: Force Public Open Satellite Data (Real Sentinel-2 L2A via AWS Open Data)
python main.py --source public

# Mode 3: Offline Demo Fallback (Deterministic synthetic benchmark for classroom without internet)
python main.py --source synthetic

# Mode 4: Strict Copernicus Data Space Ecosystem Mode (Requires .env credentials)
python main.py --source cdse
```

### Running the Test Suite
```powershell
pytest -v
```

All 22 unit and integration tests validate:
- Bounding box and projection transformations (WGS84 EPSG:4326 to UTM Zone 44N EPSG:32644).
- NDWI formula, zero-division, and negative value handling.
- Spatial dimension mismatch detection.
- Zero-baseline percentage change safety.
- Location-trusted redirect authentication.
- Content-type rejection for HTML/XML error payloads.
- Raster integrity verification with `rasterio`.
- Synthetic benchmark generation and tagging.

### Interactive Presentation Dashboard (Streamlit)
To launch the interactive presentation dashboard:
```powershell
.\.venv\Scripts\streamlit run app.py
```
Open **`http://localhost:8501`** in any browser. The dashboard includes:
- **Dark Geospatial Theme:** Optimized for college projectors and high-contrast presentations.
- **Dynamic KPI Ribbon:** Direct readings of earlier water extent (184.56 ha), later water extent (139.33 ha), and post-monsoon recession (-45.23 ha / -24.51%).
- **Interactive Multi-Panel Comparison:** Synoptic 4-panel figure with zoom and full-resolution PNG download.
- **Categorical Water Change Map:** Breakdown of persistent channel, recession, and expansion with interactive bar charts.
- **Dual Observation Inspector:** Side-by-side true-color thumbnails, continuous NDWI, and binary masks.
- **Methodology & Disclaimer:** Mathematical formulations, sensor wavelength specifications, and academic caveats.
- **Live Pipeline Execution:** "Run Satellite Analysis" button to trigger the pipeline end-to-end with real-time progress.

---

## 5. Account & Credential Configuration (Optional)

1. **Default & Public Modes**: **No account or credentials required**. Real Level-2A imagery is retrieved via the open-access Sentinel-2 Cloud-Optimized GeoTIFF archive with HTTP range subsetting.
2. **Official CDSE Keycloak Mode**: To download directly from the official Copernicus Data Space Ecosystem:
   - Register a free account at [https://dataspace.copernicus.eu/](https://dataspace.copernicus.eu/)
   - Copy `.env.example` to `.env`:
     ```powershell
     Copy-Item .env.example .env
     ```
   - Provide your credentials:
     ```ini
     CDSE_USERNAME=your_copernicus_username_or_email
     CDSE_PASSWORD=your_copernicus_password
     ```

---

## 6. Generated Evidence Files

All outputs are saved to the `outputs/` folder:
- `outputs/observation_2023-10-10_ndwi.png`: Continuous NDWI map and binary water mask for earlier observation.
- `outputs/observation_2023-12-09_ndwi.png`: Continuous NDWI map and binary water mask for later observation.
- `outputs/water_change_2023-10-10_to_2023-12-09.png`: 4-class categorical water change map (persistent, loss, gain, non-water).
- `outputs/gomti_water_change_comparison_panel.png`: Complete 4-panel comparison presentation figure.
- `outputs/metadata/selected_scenes.json`: Full scene metadata, bounding coordinates, and cloud cover metrics.
- `outputs/phase1_feasibility_report.json`: Machine-readable audit report with separate statuses for all pipeline stages.

---

## 7. Directory Structure

```
DharaScope/
├── .env.example         # Template for CDSE credentials
├── .gitignore            # Excludes large rasters, secrets, logs, cache
├── requirements.txt      # Pinned geospatial & data-access dependencies
├── main.py               # Master orchestration pipeline
├── README.md             # Documentation, methodology & reproduction guide
├── src/
│   ├── __init__.py
│   ├── config.py         # Endpoints, bbox coordinates, PROJ environment paths
│   ├── stac_client.py    # Resilient CDSE STAC API client with pagination
│   ├── scene_selection.py# Footprint intersection, pair selection, & cache fallback
│   ├── downloader.py     # CDSE auth, public COG downloader, & synthetic fallback
│   ├── water_indices.py  # NDWI calculation, clipping, thresholding
│   ├── change_detection.py # Water area statistics & multi-temporal change matrix
│   └── visualization.py  # Map generation, provenance badges, & 4-panel plots
├── tests/
│   ├── conftest.py
│   ├── test_stac_client.py
│   ├── test_downloader.py
│   ├── test_water_indices.py
│   ├── test_change_detection.py
│   └── test_end_to_end_raster_pipeline.py
├── data/
│   └── raw/              # Downloaded Level-2A GeoTIFF rasters (.gitignore-protected)
├── outputs/
│   ├── metadata/         # Selected scenes & audit JSON
│   └── *.png / *.jpg     # High-resolution visual evidence & change maps
└── logs/
    └── *.log             # Execution audit logs
```

---

## 8. Scientific Limitations & Caveats

> [!WARNING]
> **Interpretation Caveats**: Differences in NDWI-based water extent quantify apparent surface water reflections and stage fluctuations. They **do not independently establish**:
> - Chemical contamination, biological load, or river pollution.
> - Permanent water loss or river dry-up (seasonal monsoon recharge heavily alters river geometry).
> - Sub-surface hydrologic volume without bathymetry and calibrated stream gauge data.
