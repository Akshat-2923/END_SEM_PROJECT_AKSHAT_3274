# DharaScope — Scientific Methodology & Earth Observation Principles
## Mathematical Formulations, Sensor Specifications, and Hydrological Limitations

**Project:** DharaScope — Satellite-Based River Surface Water Dynamics Platform  
**Document Version:** 2.5.0  
**Status:** Approved Scientific Documentation Baseline  

---

## 1. Earth Observation Satellite Constellation: Copernicus Sentinel-2

DharaScope utilizes optical multi-spectral data acquired by the **Copernicus Sentinel-2** constellation (Sentinel-2A and Sentinel-2B), operated by the European Space Agency (ESA) under the European Union Space Programme.

### 1.1 Sensor & Radiometric Characteristics
The Multi-Spectral Instrument (MSI) on board Sentinel-2 captures 13 spectral bands spanning the visible, near-infrared (NIR), and short-wave infrared (SWIR) wavelengths. DharaScope processes Level-2A (L2A) imagery, which provides **Bottom-Of-Atmosphere (BOA) surface reflectance** pre-corrected for atmospheric aerosols, Rayleigh scattering, and gaseous absorption using ESA's Sen2Cor processing chain.

| Band Identifier | Band Center Wavelength ($\lambda_c$) | Spectral Bandwidth ($\Delta\lambda$) | Native Spatial Resolution (GSD) | Hydrological Purpose |
| :---: | :---: | :---: | :---: | :--- |
| **Band 3 (Green)** | **560.0 nm** (S2A) / **559.0 nm** (S2B) | **36 nm** (S2A) / **35 nm** (S2B) | **10 metres** ($100\text{ m}^2/\text{pixel}$) | Peak liquid water reflectance; low vegetation reflectance |
| **Band 8 (NIR)** | **842.0 nm** (S2A) / **833.0 nm** (S2B) | **115 nm** (S2A) / **106 nm** (S2B) | **10 metres** ($100\text{ m}^2/\text{pixel}$) | Near-total water absorption; peak green vegetation reflectance |

### 1.2 MGRS Tiling System & Cloud Filtering
Sentinel-2 data are partitioned into $100 \times 100\text{ km}^2$ orthorectified tiles defined by the Military Grid Reference System (MGRS). The Gomti River study area through Lucknow is located entirely within tile **`T44RMQ`** in UTM Zone 44N.

```
+--------------------------------------------------------------------------------+
| Cloud Cover Metadata Clarification:                                           |
| The 0.0% cloud cover reported in STAC metadata represents whole-scene          |
| granule metadata (eo:cloud_cover across the full 100x100 km tile T44RMQ),     |
| as evaluated by ESA's Sen2Cor L2A processor. It is not an AOI-specific cloud   |
| mask. In both selected scenes, clear-sky conditions prevailed across the tile.  |
+--------------------------------------------------------------------------------+
```

---

## 2. Spectral Water Index: Normalized Difference Water Index (NDWI)

### 2.1 Theoretical Foundation
Pure and inland water bodies exhibit strong absorption in the near-infrared (NIR) spectrum while reflecting moderately in the green spectral region. In contrast, terrestrial vegetation and urban surfaces reflect strongly in the NIR spectrum due to leaf mesophyll scattering and structural surface reflectance.

To maximize water surface contrast and suppress non-water land covers, DharaScope implements the classic **Normalized Difference Water Index (NDWI)** formulated by **McFeeters (1996)**:

$$\text{NDWI} = \frac{\rho_{\text{Green}} - \rho_{\text{NIR}}}{\rho_{\text{Green}} + \rho_{\text{NIR}}} = \frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$$

Where:
- $\rho_{\text{Green}}$ is the Bottom-Of-Atmosphere surface reflectance in Sentinel-2 Band 3.
- $\rho_{\text{NIR}}$ is the Bottom-Of-Atmosphere surface reflectance in Sentinel-2 Band 8.

### 2.2 Numerical Safety & Physical Boundary Clamping
In digital image processing, division by zero or near-zero denominators can cause floating-point infinities and calculation artifacts along shadowed boundaries or cloud borders. DharaScope enforces strict numerical safeguards in `compute_ndwi_array()`:

1. **Precision Conversion:** Raw digital numbers are converted to single-precision floating-point arrays (`float32`).
2. **NoData Elimination:** Pixels where $\text{B03} = 0$ and $\text{B08} = 0$ (Sentinel-2 L2A default nodata) or containing $\text{NaN}$ values are flagged as invalid.
3. **Zero-Denominator Protection:** Any pixel with $|\text{B03} + \text{B08}| \le 10^{-6}$ is masked out to prevent division by zero.
4. **Physical Range Clamping:** Valid calculations are clamped strictly to the theoretical bounds:
   $$\text{NDWI}_{\text{clamped}} \in [-1.0, 1.0]$$

```
                   NDWI Value Spectrum
[-1.0] ----------------- [0.0] ----------------- [+1.0]
Dense Vegetation         Base Cutoff             Clear Open Water
Dry Soil & Built-Up      Threshold               Deep Channel Inundation
```

### 2.3 Water Surface Classification Threshold ($\tau$)
A pixel is classified as water if its calculated NDWI strictly exceeds the threshold $\tau$:

$$\text{WaterMask}(x, y) = \begin{cases} 
1 & \text{if } \text{NDWI}(x, y) > \tau \land \text{ValidMask}(x, y) \\
0 & \text{if } \text{NDWI}(x, y) \le \tau \land \text{ValidMask}(x, y) \\
\text{NoData} & \text{if } \neg\text{ValidMask}(x, y)
\end{cases}$$

- **Default Threshold ($\tau = 0.00$):** Standard baseline for open surface water bodies.
- **Configurable Range ($\tau \in [-0.30, +0.30]$):**
  - $\tau < 0.00$ (e.g., $-0.10$ to $-0.20$): Useful for turbid river reaches, high suspended sediment loads, or shallow edge wetlands.
  - $\tau > 0.00$ (e.g., $+0.10$ to $+0.20$): Useful for suppressing moist urban shadows and high-albedo riparian sands.

---

## 3. Multi-Temporal Change Detection & Transition Dynamics

### 3.1 Common Valid Spatial Footprint
To guarantee rigorous multi-temporal comparability, change detection must be evaluated strictly across pixels that are valid and non-cloud-obscured on **both** observation dates:

$$\text{ComparisonDomain} = \text{ValidMask}(T_1) \land \text{ValidMask}(T_2)$$

If either date contains NoData at pixel $(x, y)$, the pixel is assigned class `255` (Invalid / NoData) and excluded from area aggregations.

### 3.2 4-Class Categorical Transition Matrix
Comparing the earlier observation ($T_1$) and later observation ($T_2$) yields four mutually exclusive hydrological dynamics categories:

| Class Code | Categorical Class Name | Mathematical Definition | Hydrological Meaning |
| :---: | :--- | :--- | :--- |
| **0** | **Persistent Non-Water** | $\neg W(T_1) \land \neg W(T_2) \land \text{Valid}$ | Permanent terrestrial land, built-up banks, urban structures |
| **1** | **Persistent Water** | $W(T_1) \land W(T_2) \land \text{Valid}$ | Perennial channel core, stable river pools, permanent reservoirs |
| **2** | **Apparent Water Loss** | $W(T_1) \land \neg W(T_2) \land \text{Valid}$ | Seasonal baseflow recession, exposed sandbars, dry backwaters |
| **3** | **Apparent Water Gain** | $\neg W(T_1) \land W(T_2) \land \text{Valid}$ | Inundation expansion, bank inundation, seasonal channel widening |
| **255** | **NoData / Invalid** | $\neg\text{Valid}(T_1) \lor \neg\text{Valid}(T_2)$ | Cloud shadow, tile edge, or missing pixel on either date |

### 3.3 Quantitative Surface Area Equations
Because each Sentinel-2 Band 3 and Band 8 pixel has a native projected ground resolution of $10.0\text{ m} \times 10.0\text{ m}$ in UTM Zone 44N, the surface area represented by each pixel is:

$$\text{Area}_{\text{pixel}} = 10.0\text{ m} \times 10.0\text{ m} = 100.0\text{ m}^2 = 0.01\text{ hectares}$$

For any set of classified pixels $N$:
$$\text{Area}_{\text{m}^2} = N \times 100.0\text{ m}^2$$
$$\text{Area}_{\text{ha}} = \frac{\text{Area}_{\text{m}^2}}{10,000} = N \times 0.01\text{ ha}$$

The net change between earlier baseline $T_1$ and later comparison $T_2$ is:
$$\Delta \text{Area}_{\text{ha}} = \text{Area}(T_2)_{\text{ha}} - \text{Area}(T_1)_{\text{ha}}$$
$$\text{Percentage Change} = \begin{cases} 
\left(\frac{\Delta \text{Area}_{\text{ha}}}{\text{Area}(T_1)_{\text{ha}}}\right) \times 100\% & \text{if } \text{Area}(T_1)_{\text{ha}} > 0 \\
0.0\% & \text{if } \text{Area}(T_1)_{\text{ha}} = 0 \land \text{Area}(T_2)_{\text{ha}} = 0 \\
\text{Undefined} & \text{if } \text{Area}(T_1)_{\text{ha}} = 0 \land \text{Area}(T_2)_{\text{ha}} > 0
\end{cases}$$

---

## 4. Multi-Scale Spatial Extent Dynamics: Regional Basin vs. Urban Reach

A critical remote sensing insight demonstrated by DharaScope is the principle of **spatial scale dependence**: surface water trends evaluated over a broad regional catchment reflect macro-hydrological balance, whereas trends evaluated over a local river reach reflect reach-scale geomorphology and localized hydraulic factors.

### 4.1 Comparative Empirical Results from Identical Sentinel-2 Observations

| Analytical Parameter | Historical Phase 1 Feasibility Baseline | Operational Phase 2.4 / 2.5 Study Reach |
| :--- | :--- | :--- |
| **Bounding Box (WGS84)** | `[80.88, 26.80, 81.00, 26.90]` | `[80.90, 26.84, 80.92, 26.86]` |
| **Spatial Scope** | Regional Gomti Basin Corridor (Lucknow Metropolitan) | Channelized Urban Gomti Riverfront Reach |
| **Geodetic Envelope Area** | **13,230.37 ha** ($132.30\text{ km}^2$) | **439.79 ha** ($4.40\text{ km}^2$) |
| **Ratio to Regional Basin** | 100.0% | **3.32%** |
| **Common Valid Pixels** | 1,323,037 pixels | 43,979 pixels |
| **Baseline Water ($T_1$, 2023-10-10)** | **184.56 ha** (18,456 pixels) | **0.53 ha** (53 pixels) |
| **Later Water ($T_2$, 2023-12-09)** | **139.33 ha** (13,933 pixels) | **1.66 ha** (166 pixels) |
| **Persistent Water** | 125.18 ha (12,518 pixels) | 0.39 ha (39 pixels) |
| **Apparent Water Loss** | 59.38 ha (5,938 pixels) | 0.14 ha (14 pixels) |
| **Apparent Water Gain** | 14.15 ha (1,415 pixels) | 1.27 ha (127 pixels) |
| **Net Surface Delta** | **-45.23 ha (-24.51%)** | **+1.13 ha (+213.21%)** |

```
Spatial Extent Scale Comparison:
+--------------------------------------------------------------------------------+
| Phase 1 Regional Basin Corridor: 13,230.37 ha (132.30 km²)                      |
| Encloses 40+ km of meandering channel, oxbows, floodplains, and canals.       |
| Net Change: -45.23 ha (-24.51% post-monsoon natural floodplain recession).     |
|                                                                                |
|    +-----------------------+                                                   |
|    | Phase 2.4/2.5 Reach:  |                                                   |
|    | 439.79 ha (4.40 km²)  |                                                   |
|    | (3.32% of regional)   |                                                   |
|    | Net: +1.13 ha (+213%) |                                                   |
|    +-----------------------+                                                   |
+--------------------------------------------------------------------------------+
```

### 4.2 Pixel Count Discretization Reconciliation (44,178 vs. 44,600 Pixels)
When transforming the WGS 84 geographic bounding box `[80.90, 26.84, 80.92, 26.86]` into UTM Zone 44N meters, the extent measures $1,988.50\text{ m} \times 2,216.55\text{ m}$ ($198.85 \times 221.65\text{ pixels}$ at 10m GSD).
- **Inner Truncated Window (`round_shape()`):** $222\text{ rows} \times 199\text{ cols} = \mathbf{44,178\text{ pixels}}$ ($441.78\text{ ha}$, 100% valid data mask).
- **Outer Expanded Window (ceiling grid bounds):** $223\text{ rows} \times 200\text{ cols} = \mathbf{44,600\text{ pixels}}$ ($446.00\text{ ha}$, with 43,979 common valid pixels inside the polygon mask).
- **Mathematical Invariance:** In both windowing formulations, the detected water pixels are **identical**: 53 pixels ($0.53\text{ ha}$) at $T_1$, 166 pixels ($1.66\text{ ha}$) at $T_2$, and net change $+113\text{ pixels}$ ($+1.13\text{ ha}$). The marginal outer boundary pixels ($44,600 - 44,178 = 422\text{ pixels}$) are purely terrestrial urban land with $\text{NDWI} \ll 0.0$.

### 4.3 Environmental Spatial Heterogeneity vs. Simple Scale Effect
The divergent directions of change between the regional corridor ($-45.23\text{ ha}$) and the urban reach ($+1.13\text{ ha}$) reflect **environmental spatial heterogeneity**, not a mere statistical scale aggregation effect:
1. **Heterogeneous Landscape Elements:** The regional corridor ($132.30\text{ km}^2$) contains broad agricultural floodplains, low-lying paddy depressions, and unconfined oxbow wetlands that naturally dry out post-monsoon.
2. **Confined Urban Reach:** The operational reach ($4.40\text{ km}^2$) is a heavily channelized urban river corridor in central Lucknow flanked by embankments, where open water surface extent expanded.
3. **Synthesis:** Sampling different landscape units captures their distinct physical and geomorphic behaviors rather than averaging a uniform process over different window sizes.

### 4.4 Distinguishing Observed Changes from Hypothesized Explanations
1. **Verified Empirical Observations:**
   - At the regional scale ($132.30\text{ km}^2$), surface water area decreased by 45.23 ha (-24.51%) between October 10 and December 9, 2023.
   - At the local reach scale ($4.40\text{ km}^2$), surface water area increased by 1.13 ha (+213.21%) within the downtown Gomti Riverfront embankments over the identical period.
2. **Documenting Phase 1 as a Historical Feasibility Experiment:**
   - The Phase 1 AOI ($132.30\text{ km}^2$) was an exploratory macro-scale study. Because it exceeds the subsequently adopted $100.00\text{ km}^2$ operational safety limit (ADR-004), it remains preserved as historical benchmark data and cannot be submitted through standard user analysis endpoints.
3. **Hypothesized Contributing Factors (Non-Causal Notice):**
   - In urban Lucknow, river stages are influenced by local hydraulic structures (including Gaughat Barrage upstream and Gomti Barrage downstream), municipal drainage inflows, riverfront embankments, and seasonal aquatic weed clearance.
   - However, **optical satellite reflectance alone does NOT prove causality**. Without verified, time-synchronized in-situ stream gauging data and barrage gate operational logs, hydraulic impoundment cannot be asserted as the definitive cause of the local water expansion; it is one hypothesized factor among several.

---

## 5. Scientific Limitations & Academic Disclaimers

Every output generated by DharaScope incorporates the mandatory hydrological disclaimer:

> **Scientific Limitation Notice:** Differences in NDWI-classified water-covered area reflect apparent surface water extent fluctuations. These fluctuations are primarily governed by seasonal precipitation, upstream dam releases, agricultural withdrawal, channel morphology, and riparian vegetation growth. NDWI-based area changes do NOT independently establish permanent water loss, environmental degradation, or river pollution without calibrated in-situ hydrological gauging, bathymetric surveys, and water quality sampling.

### 5.1 Two-Dimensional Area vs. Three-Dimensional Volume
NDWI measures the horizontal two-dimensional water surface footprint ($m^2$ or ha). It does not measure:
- Water depth or cross-sectional bathymetry.
- Volumetric river discharge ($m^3/s$).
- Sub-surface alluvial groundwater exchange.

A shallow water spread over a flat silt bar yields the same NDWI signature as a deep channel pool.

### 5.2 Spectral Reflectance vs. Chemical Water Quality
NDWI is sensitive solely to the contrast between green light reflectance and near-infrared absorption. It is **not** a biochemical water quality sensor. It cannot detect:
- Dissolved oxygen (DO) depletion or biochemical oxygen demand (BOD).
- Heavy metal concentrations or industrial effluent toxicity.
- Fecal coliform counts or pathogenic bacterial loads.

A reduction in NDWI water extent indicates channel narrowing, drying, or exposed sediment shoals—never chemical pollution.
