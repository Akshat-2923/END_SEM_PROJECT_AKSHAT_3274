"""
Script to generate DharaScope_Final_Presentation.pptx using python-pptx.
Implements a 15-slide academic geospatial presentation with a 16:9 widescreen layout,
dark scientific GIS aesthetic, embedded screenshots, data tables, and speaker notes.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]  # Blank slide

    # Color Palette
    BG_COLOR = RGBColor(15, 23, 42)        # Slate 900 #0f172a
    CARD_BG = RGBColor(30, 41, 59)         # Slate 800 #1e293b
    CARD_BORDER = RGBColor(51, 65, 85)     # Slate 700 #334155
    ACCENT_CYAN = RGBColor(56, 189, 248)   # Sky 400   #38bdf8
    ACCENT_GREEN = RGBColor(52, 211, 153)  # Emerald 400 #34d399
    ACCENT_BLUE = RGBColor(96, 165, 250)   # Blue 400  #60a5fa
    TEXT_WHITE = RGBColor(248, 250, 252)   # Slate 50  #f8fafc
    TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400 #94a3b8
    ACCENT_AMBER = RGBColor(251, 191, 36)  # Amber 400 #fbbf24

    def add_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="DHARASCOPE ACADEMIC DEFENSE"):
        # Category / Overline
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN
        p_cat.font.name = "Arial"

        # Slide Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.6))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(22)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_t.font.name = "Arial"

        # Accent Rule
        rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
        rule.fill.solid()
        rule.fill.fore_color.rgb = CARD_BORDER
        rule.line.fill.background()

    def add_card(slide, left, top, width, height, title=None, border_color=CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = border_color
        card.line.width = Pt(1)

        if title:
            tb = slide.shapes.add_textbox(Inches(left + 0.25), Inches(top + 0.2), Inches(width - 0.5), Inches(0.4))
            tf = tb.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = ACCENT_CYAN
            p.font.name = "Arial"
        return card

    def add_bullet_list(slide, left, top, width, height, items):
        tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(8)
            p.font.size = Pt(11)
            p.font.name = "Arial"
            
            if isinstance(item, tuple):
                header, body = item
                r_h = p.add_run()
                r_h.text = header + ": "
                r_h.font.bold = True
                r_h.font.color.rgb = ACCENT_GREEN
                
                r_b = p.add_run()
                r_b.text = body
                r_b.font.color.rgb = TEXT_WHITE
            else:
                r = p.add_run()
                r.text = item
                r.font.color.rgb = TEXT_WHITE

    def add_speaker_notes(slide, notes_text):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = notes_text

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_background(s1)
    
    # Title Card
    c1 = add_card(s1, 1.2, 1.0, 10.933, 5.5, border_color=ACCENT_CYAN)
    
    # Text inside Title Card
    tb = s1.shapes.add_textbox(Inches(1.8), Inches(1.5), Inches(9.733), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = "CAPSTONE PROJECT DEFENSE · B.TECH CSE"
    p0.font.size = Pt(12)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(14)
    
    p1 = tf.add_paragraph()
    p1.text = "DharaScope: Automated Satellite-Based\nSurface Water Dynamics Monitoring Platform"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(16)
    
    p2 = tf.add_paragraph()
    p2.text = "An Enterprise Web GIS for Multi-Temporal Water Change Detection Using Copernicus Sentinel-2"
    p2.font.size = Pt(14)
    p2.font.color.rgb = ACCENT_GREEN
    p2.space_after = Pt(24)
    
    p3 = tf.add_paragraph()
    p3.text = "Key Technologies: Copernicus Sentinel-2 Level-2A · McFeeters NDWI · FastAPI · PostgreSQL 16 + PostGIS 3.6 · React 19 + Leaflet"
    p3.font.size = Pt(11)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_after = Pt(20)
    
    p4 = tf.add_paragraph()
    p4.text = "Author: DharaScope Engineering Team | Academic Year: 2026 | Study Area: Urban Gomti River Study Reach, Lucknow, UP"
    p4.font.size = Pt(11)
    p4.font.bold = True
    p4.font.color.rgb = TEXT_WHITE
    
    add_speaker_notes(s1, 
        "Good morning, esteemed panel members and evaluators. Today, we present DharaScope, "
        "an automated, production-grade geospatial platform designed to bridge raw satellite Earth Observation data "
        "from the European Space Agency's Sentinel-2 constellation directly to an interactive, secure web GIS workstation "
        "for surface water dynamics monitoring."
    )

    # =========================================================================
    # SLIDE 2: Problem Statement
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_background(s2)
    add_header(s2, "Problem Statement: Hydrological Monitoring & Remote Sensing Bottlenecks")
    
    add_card(s2, 0.8, 1.6, 5.7, 5.2, "1. The Surface Water Monitoring Challenge")
    add_bullet_list(s2, 1.05, 2.2, 5.2, 4.3, [
        ("Monsoonal Extremes", "In northern India, rivers like the Gomti alternate between high monsoon bankfull storage and dry pre-monsoon recessions."),
        ("Spatial Sparsity", "Physical hydrometric stream gauges are separated by tens or hundreds of kilometers, leaving vast floodplain wetlands and agricultural river corridors unmonitored."),
        ("Data Latency", "In-situ gauge telemetry is often proprietary, manually logged, or released with substantial latency."),
        ("Resource Intensity", "Manual field surveys of dynamic wetlands are logistically prohibitive over regional watersheds.")
    ])
    
    add_card(s2, 6.8, 1.6, 5.7, 5.2, "2. Earth Observation Engineering Bottlenecks")
    add_bullet_list(s2, 7.05, 2.2, 5.2, 4.3, [
        ("Granule Ingestion Volume", "A single Sentinel-2 Level-2A granule is 500 MB to 1 GB (10,980 x 10,980 pixels). Downloading full scenes for a localized 5 km² reach wastes >99% bandwidth and server RAM."),
        ("Multi-Tenant Cloud Security", "Existing web GIS tools often lack rigorous database-level isolation. Multi-tenant systems require strict Row-Level Security (RLS) to prevent data leakage."),
        ("Desktop GIS Disconnect", "Specialists rely on manual desktop GIS software (QGIS/ArcGIS). Workflows are manual, non-standardized, and difficult for non-specialists to reproduce.")
    ])
    
    add_speaker_notes(s2,
        "The fundamental problem in surface water monitoring is the spatial gap left by sparse in-situ gauges, "
        "combined with the engineering bottleneck of downloading gigabytes of satellite imagery just to monitor a localized river segment. "
        "DharaScope was engineered to make high-resolution Earth Observation automated, sub-granule, and accessible."
    )

    # =========================================================================
    # SLIDE 3: Objectives & Scope
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_background(s3)
    add_header(s3, "Project Objectives & Scope: Seven Measurable Targets")
    
    add_card(s3, 0.8, 1.6, 11.733, 5.2, "Approved MVP Scope & Technical Objectives")
    add_bullet_list(s3, 1.1, 2.2, 11.1, 4.3, [
        ("1. Interactive Vector Digitization", "Enable users to draw arbitrary polygon AOIs up to 100 km² via Leaflet with real-time topological validation (ST_IsValid, ST_Area)."),
        ("2. Automated STAC Discovery", "Query live Copernicus Sentinel-2 catalogs with cloud cover filtering (<=10%) and temporal separation via open STAC protocols."),
        ("3. Windowed Sub-Granule COG Streaming", "Stream only Band 3 (Green) and Band 8 (NIR) covering the AOI via GDAL /vsicurl/ and HTTP range GET requests, cutting transfer by >99%."),
        ("4. Calibrated Spectral Indexing", "Compute McFeeters NDWI at native 10m spatial resolution with zero-division protections and valid-data masking."),
        ("5. Categorical 4-Class Change Detection", "Model water transitions into Permanent Water, Inundation, Recession, and Persistent Land with strict pixel-level conservation."),
        ("6. Multi-Tenant Database Security", "Enforce PostgreSQL Row-Level Security (RLS) driven by Supabase JWT bearer claims, with authoritative database role checks."),
        ("7. Automated Publication Reporting", "Programmatically compile 300 DPI publication cartography and analytical metrics into downloadable, audit-ready PDF (7.4 MB) and CSV datasets.")
    ])
    
    add_speaker_notes(s3,
        "We defined seven rigorous, measurable objectives spanning front-end digitization, sub-granule satellite streaming, "
        "spectral calculation, transition modeling, database security, and automated report generation—all strictly bound to an operational limit of 100 square kilometers."
    )

    # =========================================================================
    # SLIDE 4: Existing Approaches vs. Proposed Solution
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_background(s4)
    add_header(s4, "Existing Approaches vs. Proposed Solution: Strategic Comparison")
    
    # Table layout
    rows, cols = 7, 4
    table_shape = s4.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.1))
    table = table_shape.table
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(2.9)
    table.columns[2].width = Inches(3.2)
    table.columns[3].width = Inches(3.333)

    table_data = [
        ["Evaluation Dimension", "Traditional In-Situ Gauging", "Manual Desktop GIS (QGIS)", "DharaScope Platform"],
        ["Spatial Continuity", "Point-based (sparse station network)", "Synoptic (manual tile acquisition)", "Synoptic & automated continuous"],
        ["Data Ingestion Volume", "Physical log inspection", "Full granule download (>500 MB)", "Windowed COG streaming (~88 KB)"],
        ["Spatial Resolution", "Zero spatial resolution", "10m (Sentinel-2)", "10m native Ground Sampling Distance"],
        ["Workflow Automation", "Manual manual logging & collation", "Multi-step manual raster clipping", "Fully automated via asynchronous API"],
        ["Multi-User Security", "N/A (spreadsheets/paper)", "None (local desktop single-user)", "Native PostgreSQL Row-Level Security"],
        ["Reporting", "Tabular discharge records", "Manual map layout export", "Programmatic 300 DPI PDF & CSV"]
    ]

    for r_idx, row in enumerate(table_data):
        for c_idx, cell in enumerate(row):
            tc = table.cell(r_idx, c_idx)
            tc.text = cell
            p = tc.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            p.font.size = Pt(10)
            p.font.name = "Arial"
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = ACCENT_CYAN
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG
            else:
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG if r_idx % 2 == 0 else BG_COLOR
                if c_idx == 3:
                    p.font.bold = True
                    p.font.color.rgb = ACCENT_GREEN
                else:
                    p.font.color.rgb = TEXT_WHITE

    add_speaker_notes(s4,
        "Compared to manual desktop GIS workflows that require downloading 500 MB tiles for every analysis, "
        "DharaScope extracts only the spatial window covering the user's AOI in seconds, wrapping the entire scientific pipeline in a multi-tenant web application."
    )

    # =========================================================================
    # SLIDE 5: System Architecture & Component Interactions
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_background(s5)
    add_header(s5, "System Architecture: Decoupled Multi-Tier Topology")
    
    # 4 Architecture Cards
    c_w = 2.7
    c_h = 5.2
    
    add_card(s5, 0.8, 1.6, c_w, c_h, "1. Presentation Tier")
    add_bullet_list(s5, 0.95, 2.2, c_w - 0.3, 4.3, [
        ("Framework", "React 19 + TypeScript + Vite."),
        ("Cartography", "Leaflet web canvas with Dark Matter basemaps."),
        ("State & Auth", "Supabase client context, JWT Bearer propagation."),
        ("Telemetry", "Real-time polling for pipeline execution status.")
    ])
    
    add_card(s5, 3.8, 1.6, c_w, c_h, "2. API Service Layer")
    add_bullet_list(s5, 3.95, 2.2, c_w - 0.3, 4.3, [
        ("Framework", "FastAPI (ASGI) on Uvicorn."),
        ("Endpoints", "REST endpoints for AOI CRUD, analyses, and reports."),
        ("Validation", "Pydantic request/response schema enforcement."),
        ("Tasks", "In-process background processing core.")
    ])
    
    add_card(s5, 6.8, 1.6, c_w, c_h, "3. Spatial Persistence")
    add_bullet_list(s5, 6.95, 2.2, c_w - 0.3, 4.3, [
        ("Database", "PostgreSQL 16 + PostGIS 3.6."),
        ("Security", "Native Row-Level Security (RLS) policies."),
        ("Indexing", "GiST spatial index (idx_aois_geometry)."),
        ("Cascade", "Foreign keys with SET NULL / CASCADE rules.")
    ])
    
    add_card(s5, 9.8, 1.6, c_w, c_h, "4. Science Engine")
    add_bullet_list(s5, 9.95, 2.2, c_w - 0.3, 4.3, [
        ("STAC Client", "CDSE & AWS Element84 satellite discovery."),
        ("Streaming", "GDAL /vsicurl/ COG byte-range streaming."),
        ("NDWI Core", "NumPy McFeeters spectral indexing."),
        ("Reporting", "ReportLab 300 DPI PDF & CSV compiler.")
    ])

    add_speaker_notes(s5,
        "The system follows a multi-tier decoupled topology. The React client communicates with the FastAPI service layer via authenticated REST endpoints. "
        "FastAPI manages background task dispatch, invokes the scientific processing core, and persists geometries and run metadata in PostgreSQL 16 with PostGIS 3.6."
    )

    # =========================================================================
    # SLIDE 6: Technology Stack & Implementation Matrix
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_background(s6)
    add_header(s6, "Technology Stack & Production Engineering Baseline")
    
    rows, cols = 8, 4
    table_shape6 = s6.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(11.733), Inches(5.1))
    table6 = table_shape6.table
    table6.columns[0].width = Inches(2.2)
    table6.columns[1].width = Inches(2.8)
    table6.columns[2].width = Inches(1.8)
    table6.columns[3].width = Inches(4.933)

    tech_data = [
        ["Subsystem Tier", "Core Technology", "Version", "Engineering Role & Architectural Responsibility"],
        ["Frontend UI", "React / TypeScript", "19.0 / 5.7", "Component-driven GIS interface, compile-time type safety"],
        ["Frontend Bundler", "Vite", "7.3.1", "Fast Hot Module Replacement (HMR) and optimized production build"],
        ["Web Mapping", "Leaflet / React-Leaflet", "1.9.4", "Lightweight cartographic rendering, interactive AOI digitization"],
        ["Application API", "FastAPI (Python)", "0.115.6", "High-throughput asynchronous ASGI REST server, OpenAPI 3.1 docs"],
        ["Spatial Database", "PostgreSQL / PostGIS", "16.15 / 3.6.2", "Relational spatial data storage, GiST indexing, Row-Level Security"],
        ["Raster Processing", "Rasterio / GDAL", "1.4.4", "Windowed COG streaming via /vsicurl/, spatial reprojection"],
        ["Reporting & Output", "ReportLab / Matplotlib", "5.1.0 / 3.11", "300 DPI publication cartography figures and standalone PDF compiler"]
    ]

    for r_idx, row in enumerate(tech_data):
        for c_idx, cell in enumerate(row):
            tc = table6.cell(r_idx, c_idx)
            tc.text = cell
            p = tc.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            p.font.size = Pt(10)
            p.font.name = "Arial"
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = ACCENT_CYAN
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG
            else:
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG if r_idx % 2 == 0 else BG_COLOR
                if c_idx == 1:
                    p.font.bold = True
                    p.font.color.rgb = ACCENT_GREEN
                else:
                    p.font.color.rgb = TEXT_WHITE

    add_speaker_notes(s6,
        "Our technology stack leverages modern open-source foundations: React 19 and Leaflet on the presentation tier, "
        "FastAPI and SQLAlchemy on the service tier, PostgreSQL 16 with PostGIS 3.6 for spatial storage, "
        "and Rasterio/GDAL C-bindings for sub-granule raster extraction."
    )

    # =========================================================================
    # SLIDE 7: Database Design & Multi-Tenant Security
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_background(s7)
    add_header(s7, "Database Design: PostGIS Relational Schema & Row-Level Security")
    
    add_card(s7, 0.8, 1.6, 5.7, 5.2, "1. Spatial Relational Schema (PostGIS 3.6)")
    add_bullet_list(s7, 1.05, 2.2, 5.2, 4.3, [
        ("profiles", "User identity, quota bounds (e.g. 50 runs/mo), and role (user/admin)."),
        ("aois", "User-digitized GEOMETRY(POLYGON, 4326), GiST spatial index, check constraints: ST_IsValid(geom) and ST_Area <= 100 km²."),
        ("analysis_runs", "Run execution lifecycle (PENDING -> RUNNING -> SUCCESS/FAILED), scene IDs, cloud cover, and timestamps."),
        ("water_metrics", "1-to-1 with run: water area in ha (T1/T2), net change, % delta, and 4-class pixel transition counts."),
        ("analysis_artifacts", "File references, MIME types, and 90-day retention policies (zero heavy binaries stored in SQL rows).")
    ])
    
    add_card(s7, 6.8, 1.6, 5.7, 5.2, "2. Defense-in-Depth Multi-Tenancy (RLS)")
    add_bullet_list(s7, 7.05, 2.2, 5.7, 4.3, [
        ("Session Identity Injection", "FastAPI auth dependency sets transaction-local context: SET LOCAL app.current_user_id = '<uuid>';"),
        ("PostgreSQL RLS Policies", "Native database policies enforce USING (user_id = current_setting('app.current_user_id')::uuid) across all tables."),
        ("Zero Cross-Tenant Leakage", "Even if a query omits WHERE user_id = ..., the database engine returns 0 rows for other users."),
        ("Authoritative Admin Checks", "require_admin queries the database profiles table directly, blocking revoked admins immediately even with an unexpired JWT."),
        ("Role Sync Journal", "Two-phase distributed updates with compensating rollback logged to role_sync_audit.jsonl.")
    ])

    add_speaker_notes(s7,
        "Security is built from the database engine up. We enforce PostgreSQL Row-Level Security using transaction-local session propagation. "
        "Even if an API query omitted a user filter, PostgreSQL returns zero records for foreign tenant data. "
        "Admin actions verify privileges against the authoritative database profile, eliminating stale-JWT elevation."
    )

    # =========================================================================
    # SLIDE 8: Satellite Data Retrieval: Windowed COG Streaming
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_background(s8)
    add_header(s8, "Satellite Data Retrieval: Windowed COG Streaming Architecture")
    
    add_card(s8, 0.8, 1.6, 5.7, 5.2, "1. The Traditional Full-Granule Bottleneck")
    add_bullet_list(s8, 1.05, 2.2, 5.2, 4.3, [
        ("Granule Scale", "A standard Sentinel-2 Level-2A product spans 100 x 100 km (10,980 x 10,980 pixels at 10m)."),
        ("Full Archive Download", "Each granule archive is 500 MB to 1 GB. Ingesting two observation dates requires 1.0 to 2.0 GB of raw download."),
        ("Network & Memory Penalty", "Transfers take minutes and consume gigabytes of worker memory just to crop a 4 km² river segment."),
        ("Operational Failure", "Prohibitive for responsive multi-tenant web applications.")
    ])
    
    add_card(s8, 6.8, 1.6, 5.7, 5.2, "2. DharaScope Sub-Granule Streaming (/vsicurl/)")
    add_bullet_list(s8, 7.05, 2.2, 5.2, 4.3, [
        ("Reprojection Alignment", "Reprojects user WGS 84 AOI into the granule's native UTM Zone 44N (EPSG:32644) coordinate envelope."),
        ("HTTP Range GET Requests", "Using GDAL /vsicurl/ and rasterio, the server reads the COG tile index and requests ONLY byte-ranges covering the AOI."),
        ("Band Selection", "Extracts only Band 3 (Green 10m) and Band 8 (NIR 10m), completely skipping unnecessary bands."),
        ("Transfer Efficiency", "Data transferred drops from ~1 GB down to ~88 KB per band (>99.9% bandwidth reduction)."),
        ("Sub-Second Latency", "Sub-granule window extraction completes in 2–4 seconds.")
    ])

    add_speaker_notes(s8,
        "By using Cloud-Optimized GeoTIFFs and GDAL's virtual file system, we make HTTP range requests to download only the few byte-ranges "
        "covering the user's bounding box. Instead of transferring a gigabyte, we transfer less than 100 kilobytes per band, executing in seconds."
    )

    # =========================================================================
    # SLIDE 9: NDWI & Multi-Temporal Change Detection
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_background(s9)
    add_header(s9, "Spectral Indexing: McFeeters NDWI & 4-Class Transition Matrix")
    
    add_card(s9, 0.8, 1.6, 5.7, 5.2, "1. McFeeters NDWI Formulation")
    add_bullet_list(s9, 1.05, 2.2, 5.2, 4.3, [
        ("Mathematical Formulation", "NDWI = (Band 3 [Green] - Band 8 [NIR]) / (Band 3 [Green] + Band 8 [NIR])"),
        ("Physical Principle", "Water absorbs NIR radiation (reflectance < 1%) and reflects green light (10-15%). Terrestrial vegetation and soil reflect strongly in NIR."),
        ("Native 10m Resolution", "Both B03 and B08 operate natively at 10m GSD; zero spatial resampling required."),
        ("Numerical Safeguards", "Denominator |B03 + B08| <= 1e-6 masked as invalid; physical ratio clamped to [-1.0, 1.0]."),
        ("Binary Water Classification", "Water = True if NDWI > 0.00 and valid_mask = True.")
    ])
    
    add_card(s9, 6.8, 1.6, 5.7, 5.2, "2. Categorical 4-Class Transition Modeling")
    add_bullet_list(s9, 7.05, 2.2, 5.2, 4.3, [
        ("Transition Formula", "Class Code = 2 * Water(T1) + Water(T2)"),
        ("Code 0 (0 -> 0)", "Persistent Land: Terrestrial land, urban fabric, or canopy."),
        ("Code 1 (0 -> 1)", "Water Inundation: Newly submerged land, channel widening, or flood (+gain)."),
        ("Code 2 (1 -> 0)", "Water Recession: Exposed sediment, dry sandbar, or wetland loss (-loss)."),
        ("Code 3 (1 -> 1)", "Permanent Water: Stable perennial river thalweg or deep channel pools."),
        ("Area Conservation", "Area (ha) = Pixel Count * 10m * 10m * 1e-4 = Pixel Count * 0.01 ha.")
    ])

    add_speaker_notes(s9,
        "We compute McFeeters NDWI at native 10-meter resolution using Band 3 and Band 8. Pixels with NDWI greater than zero are classified as water. "
        "By comparing binary masks between two dates, we generate a mutually exclusive, collectively exhaustive 4-class transition matrix."
    )

    # =========================================================================
    # SLIDE 10: Application Demonstration (8 Workflow Stages)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_background(s10)
    add_header(s10, "Application Demonstration: Verified 8-Stage User Journey")
    
    # 2 columns: Left text stages, Right screenshot
    add_card(s10, 0.8, 1.6, 5.7, 5.2, "End-to-End User Journey (Playwright Verified)")
    add_bullet_list(s10, 1.05, 2.2, 5.2, 4.3, [
        ("Step 1: Landing", "Dark scientific aesthetic, telemetry pills, health status."),
        ("Step 2: Authentication", "Supabase JWT session, researcher/admin personas."),
        ("Step 3: AOI Selection", "Urban Gomti reach preset (4.40 km²), PostGIS real-time validation."),
        ("Step 4: Scene Discovery", "STAC query selects Oct 10 & Dec 09, 2023 granules (T44RMQ)."),
        ("Step 5: Execution", "Worker completes in 18s; REAL ORBITAL S2 badge rendered."),
        ("Step 6: Metrics & Transitions", "0.53 ha -> 1.66 ha (+1.13 ha / +213.21%) displayed."),
        ("Step 7: Cartography", "Interactive 300 DPI 4-panel and transition maps."),
        ("Step 8: Downloads", "Verified 7.4 MB publication PDF and CSV manifest.")
    ])
    
    # Try embedding real screenshot on right
    img_path = "outputs/validation_phase2_4/05_analysis_success_real_data.png"
    if os.path.exists(img_path):
        add_card(s10, 6.8, 1.6, 5.7, 5.2, "Live Workstation Interface (Verified Screenshot)")
        s10.shapes.add_picture(img_path, Inches(7.0), Inches(2.2), width=Inches(5.3))
    else:
        add_card(s10, 6.8, 1.6, 5.7, 5.2, "Live Workstation Interface")

    add_speaker_notes(s10,
        "Here we see the 8 stages of the user experience, proven through live browser automation. "
        "The user selects the Urban Gomti River Study Reach in Lucknow, configures cloud thresholds, triggers the pipeline, "
        "inspects the 4-class categorical map, and downloads publication-grade PDF and CSV reports."
    )

    # =========================================================================
    # SLIDE 11: Experimental Results: Urban Gomti River Study Reach
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_background(s11)
    add_header(s11, "Experimental Results: Urban Gomti River Study Reach Dynamics")
    
    # Left table, Right explanation
    rows, cols = 7, 3
    table_shape11 = s11.shapes.add_table(rows, cols, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.1))
    table11 = table_shape11.table
    table11.columns[0].width = Inches(2.5)
    table11.columns[1].width = Inches(1.6)
    table11.columns[2].width = Inches(1.6)

    res_data = [
        ["Transition Category", "Pixel Count", "Surface Area (ha)"],
        ["Earlier Water (T1, Oct 10)", "53 px", "0.53 ha (100.0%)"],
        ["Later Water (T2, Dec 09)", "166 px", "1.66 ha (313.2%)"],
        ["Net Water Dynamics (ΔA)", "+113 px", "+1.13 ha (+213.21%)"],
        ["Perennial Channel Core", "39 px", "0.39 ha (73.6%)"],
        ["Water Inundation (Gain)", "127 px", "1.27 ha (239.6%)"],
        ["Water Recession (Loss)", "14 px", "0.14 ha (26.4%)"]
    ]

    for r_idx, row in enumerate(res_data):
        for c_idx, cell in enumerate(row):
            tc = table11.cell(r_idx, c_idx)
            tc.text = cell
            p = tc.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            p.font.size = Pt(10)
            p.font.name = "Arial"
            if r_idx == 0:
                p.font.bold = True
                p.font.color.rgb = ACCENT_CYAN
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG
            else:
                tc.fill.solid()
                tc.fill.fore_color.rgb = CARD_BG if r_idx % 2 == 0 else BG_COLOR
                if r_idx == 3:
                    p.font.bold = True
                    p.font.color.rgb = ACCENT_GREEN
                else:
                    p.font.color.rgb = TEXT_WHITE

    add_card(s11, 6.8, 1.6, 5.7, 5.2, "Scientific Synthesis & Reconciliation")
    add_bullet_list(s11, 7.05, 2.2, 5.2, 4.3, [
        ("Pixel Discretization Reconciliation", "Common valid footprint: 43,979 px (439.79 ha). Inner window: 222x199 = 44,178 px. Outer window: 223x200 = 44,600 px. Invariant: Water pixels are strictly identical (53 px at T1, 166 px at T2, net +1.13 ha)."),
        ("Environmental Spatial Heterogeneity", "Regional basin (132.30 km², Phase 1): -45.23 ha (-24.51%) across drying agricultural floodplains. Urban Gomti reach (4.40 km², Phase 2.4): +1.13 ha (+213.21%) along confined riverfront. Distinct landscape zones, not an aggregation artifact."),
        ("Non-Causal Attribution Notice", "Remote sensing observes 2D planar reflectance. Causal factors (e.g. weir gates, urban runoff) remain unverified hypotheses without in-situ gauging telemetry.")
    ])

    add_speaker_notes(s11,
        "In our operational study area, the Urban Gomti River Study Reach in Lucknow, detected surface water increased from 0.53 ha (53 pixels) to 1.66 ha (166 pixels), "
        "a net gain of 1.13 ha (+113 pixels, +213.21%). The transition breakdown reveals 0.39 ha of perennial channel core, 1.27 ha of inundation expansion, "
        "and 0.14 ha of seasonal recession, surrounded by 437.99 ha of persistent land. Crucially, whether evaluating the 43,979 valid polygon pixels, "
        "the 44,178 inner window, or the 44,600 outer window, the detected water pixels are strictly invariant. "
        "Furthermore, the divergence from regional feasibility results illustrates environmental spatial heterogeneity across diverse landscape zones."
    )

    # =========================================================================
    # SLIDE 12: Testing, Quality Assurance & Security
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_background(s12)
    add_header(s12, "Testing, Quality Assurance & Security Verification")
    
    add_card(s12, 0.8, 1.6, 5.7, 5.2, "1. Automated Test Suite (185/185 Executed Passed, 1 Skipped)")
    add_bullet_list(s12, 1.05, 2.2, 5.2, 4.3, [
        ("Backend Pytest", "185 passed, 1 skipped (live CDSE credential check) across 16 test modules covering auth, RLS, STAC, NDWI, storage, and reporting."),
        ("Code Coverage", "83.0% verified statement coverage across 2,605 statements in src/ (with core modules reaching 89%–100%)."),
        ("Frontend Vitest", "18 passed across 6 test suites covering components and JWT security."),
        ("Total Automated Tests", "185/185 executed backend tests and 18/18 frontend tests passed (203 total passing tests)."),
        ("Static Analysis", "0 errors across 26 TypeScript/TSX files in Oxlint."),
        ("Production Build", "Vite production build succeeds in 5.97s with zero errors.")
    ])
    
    add_card(s12, 6.8, 1.6, 5.7, 5.2, "2. Security & Multi-Tenant Isolation")
    add_bullet_list(s12, 7.05, 2.2, 5.7, 4.3, [
        ("Secret Isolation", "DEV_JWT_SECRET tree-shaken from production bundles via import.meta.env.DEV."),
        ("Cross-Tenant Isolation", "Verified by test_cross_user_resource_isolation: User B cannot access User A's private AOIs or reports (HTTP 404)."),
        ("Immediate Revocation", "Verified by test_immediate_revocation_stale_jwt_rejected: Revoked admin blocked immediately at database level (HTTP 403)."),
        ("Distributed Consistency", "Verified by test_ambiguous_commit_outcome: Reconciles or compensates Supabase without split-brain.")
    ])

    add_speaker_notes(s12,
        "The platform has been validated through 203 automated tests spanning unit, integration, and security assertions—with all 185 executed backend tests "
        "and 18 frontend tests passing, and 1 live external credential test intentionally skipped. "
        "This is paired with static linting with Oxlint and headless browser testing with Playwright. "
        "Every security boundary—including RLS tenant isolation and immediate admin revocation—is verified by regression tests."
    )

    # =========================================================================
    # SLIDE 13: System Limitations & Scientific Boundaries
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_background(s13)
    add_header(s13, "System Limitations & Scientific Boundaries")
    
    add_card(s13, 0.8, 1.6, 11.733, 5.2, "Documented Physical & Operational Constraints")
    add_bullet_list(s13, 1.1, 2.2, 11.1, 4.3, [
        ("1. Optical Cloud Occlusion", "Sentinel-2 MSI cannot penetrate cloud cover. During peak monsoon months (July-August), cloud cover in northern India often exceeds 70%, requiring radar (SAR / Sentinel-1) integration."),
        ("2. Spatial Resolution Limit (10m GSD)", "Small farm ponds (<100 m²) and narrow field irrigation channels (<10m wide) cannot be cleanly resolved without sub-pixel spectral unmixing."),
        ("3. Planar Reflectance vs. Water Depth", "NDWI measures two-dimensional planar surface presence. It does NOT measure water depth, velocity, river cross-sectional bathymetry, or volumetric discharge."),
        ("4. Attribution Boundary (No In-Situ Telemetry)", "Satellite Earth observation detects surface reflectance changes. Without ground-truth stream gauges and barrage operational logs, local hydraulic causes cannot be proven."),
        ("5. Operational AOI Size Cap (100 km²)", "Enforced to maintain worker memory footprint below 500 MB on single-node servers."),
        ("6. In-Process Worker Lifecycle", "FastAPI BackgroundTasks run in-process and do not survive application restarts. Enterprise deployments should adopt distributed task queues (Celery/Redis).")
    ])

    add_speaker_notes(s13,
        "We maintain strict scientific transparency regarding limitations. Satellite remote sensing measures two-dimensional optical surface reflectance, "
        "not river volume or depth. Furthermore, during heavy monsoon cloud cover, optical sensors are blinded, and without in-situ gauging records, "
        "we report observed reflectance changes rather than claiming proven hydraulic causes."
    )

    # =========================================================================
    # SLIDE 14: Future Scope & Technical Roadmap
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_background(s14)
    add_header(s14, "Future Scope: Technical Roadmap & Sensor Fusion")
    
    add_card(s14, 0.8, 1.6, 5.7, 5.2, "1. Remote Sensing & Algorithmic Enhancements")
    add_bullet_list(s14, 1.05, 2.2, 5.2, 4.3, [
        ("Radar-Optical Fusion (Sentinel-1 SAR)", "Ingest Sentinel-1 C-band Synthetic Aperture Radar (SAR) Ground Range Detected (GRD) imagery to enable all-weather, cloud-penetrating water monitoring during monsoon storms."),
        ("Automated Dynamic Thresholding", "Implement Otsu bimodal histogram thresholding to dynamically adjust the NDWI decision boundary for turbid, sediment-laden river flows."),
        ("Sub-Pixel Deep Learning", "Deploy lightweight convolutional segmentation models (e.g. U-Net, SegFormer) to quantify fractional water coverage in boundary mixed pixels along riverbanks.")
    ])
    
    add_card(s14, 6.8, 1.6, 5.7, 5.2, "2. Infrastructure & Architectural Scaling")
    add_bullet_list(s14, 7.05, 2.2, 5.2, 4.3, [
        ("Distributed Task Queue", "Migrate in-process workers to Celery and Redis with horizontal auto-scaling across container clusters."),
        ("Cloud Object Storage", "Configure Amazon S3 / Supabase Storage buckets for multi-region raster caching and signed download streaming."),
        ("In-Situ Telemetry Ingestion", "Connect Central Water Commission (CWC) public stream-gauge APIs to correlate satellite surface extent with stage height."),
        ("Basin-Scale Tiling", "Support multi-tile spatial mosaic querying for continental-scale river basin monitoring.")
    ])

    add_speaker_notes(s14,
        "Our immediate research trajectory focuses on multi-sensor fusion: integrating Sentinel-1 Synthetic Aperture Radar to provide cloud-penetrating "
        "water detection during peak monsoon flooding, alongside automated dynamic thresholding for turbid waters."
    )

    # =========================================================================
    # SLIDE 15: Conclusion & Summary
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_background(s15)
    add_header(s15, "Conclusion: Summary of Academic Contributions")
    
    c15 = add_card(s15, 1.2, 1.6, 10.933, 5.2, "Key Achievements & Academic Contributions", border_color=ACCENT_CYAN)
    add_bullet_list(s15, 1.5, 2.2, 10.3, 4.3, [
        ("Operational Web GIS Delivered", "Successfully engineered and demonstrated an open-source, automated Earth Observation web platform bridging raw Sentinel-2 satellite data to an interactive web workstation."),
        ("Sub-Granule Ingestion Innovation", "Eliminated gigabyte-scale tile downloads using windowed Cloud-Optimized GeoTIFF streaming via /vsicurl/, achieving >99.9% bandwidth reduction."),
        ("Environmental Spatial Heterogeneity Proven", "Demonstrated that localized urban channel expansion (+1.13 ha) and regional floodplain recession (-45.23 ha) reflect authentic environmental spatial heterogeneity across diverse landscape zones."),
        ("Enterprise Multi-Tenant Security", "Pioneered native PostgreSQL Row-Level Security coupled to Supabase JWT authentication, with authoritative database role checks for immediate admin revocation."),
        ("Reproducible & Defensible Baseline", "Full 185/185 executed backend tests passed (1 live CDSE test skipped), 18/18 frontend tests passed, 83.0% statement coverage, verified Playwright browser automation, and submission-quality academic documentation published.")
    ])

    add_speaker_notes(s15,
        "In conclusion, DharaScope demonstrates that high-precision satellite Earth Observation can be operationalized into a secure, responsive, "
        "and reproducible web GIS. All 185 executed backend tests and 18 frontend tests are passing (1 live external test skipped), live browser demonstration is verified, "
        "and documentation is complete. Thank you. We welcome questions from the examination committee."
    )

    # Save presentation
    output_pptx = "DharaScope_Final_Presentation.pptx"
    prs.save(output_pptx)
    print(f"Presentation successfully created at {output_pptx} with {len(prs.slides)} slides.")

if __name__ == "__main__":
    create_presentation()
