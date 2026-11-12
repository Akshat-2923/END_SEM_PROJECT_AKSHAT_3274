"""DharaScope Reporting Module.

Generates structured CSV and publication-ready cartographic PDF reports
strictly derived from authentic Sentinel-2 analysis manifests and outputs.
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.change_detection import LIMITATION_STATEMENT
from src.config import BASE_DIR, OUTPUTS_DIR, REPORTS_DIR

logger = logging.getLogger("dhara_scope.reporting")


class ReportingError(Exception):
    """Raised when report generation fails due to missing or invalid manifest data."""
    pass


def load_manifest(manifest_source: Union[Dict[str, Any], Path, str, None] = None) -> Dict[str, Any]:
    """Load and validate an analysis manifest dictionary from a file or memory object."""
    if manifest_source is None:
        manifest_path = OUTPUTS_DIR / "phase1_feasibility_report.json"
        if not manifest_path.exists():
            raise ReportingError(f"Default analysis manifest not found at {manifest_path}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if isinstance(manifest_source, dict):
        return manifest_source

    path = Path(manifest_source)
    if not path.exists():
        raise ReportingError(f"Analysis manifest file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise ReportingError(f"Failed to parse analysis manifest JSON from {path}: {exc}") from exc


def extract_report_metrics(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate all required metrics directly from the analysis manifest."""
    stages = manifest.get("stages", {})
    if not stages:
        raise ReportingError("Manifest missing 'stages' payload.")

    cat_stage = stages.get("catalogue_discovery") or stages.get("water_classification") or stages.get("scene_selection", {})
    change_stage = stages.get("real_change_detection", {})
    stats = change_stage.get("statistics", {})

    if not stats:
        raise ReportingError("Manifest missing change detection statistics.")

    params = manifest.get("parameters", {})
    provenance = manifest.get("data_source_provenance", {})

    t1_date = cat_stage.get("earlier_date", "UNKNOWN")[:10]
    t2_date = cat_stage.get("later_date", "UNKNOWN")[:10]
    t1_cloud = cat_stage.get("earlier_cloud_cover", 0.0)
    t2_cloud = cat_stage.get("later_cloud_cover", 0.0)
    t1_scene_id = cat_stage.get("earlier_scene_id", "N/A")
    t2_scene_id = cat_stage.get("later_scene_id", "N/A")

    comp_px = stats.get("comparison_pixels", {})
    water_t1 = stats.get("water_area_earlier_t1", {})
    water_t2 = stats.get("water_area_later_t2", {})
    change_m = stats.get("change_metrics", {})

    ndwi_stage = stages.get("real_ndwi_calculation", {})
    crs = ndwi_stage.get("crs", "EPSG:32644 (UTM Zone 44N)")
    threshold = params.get("ndwi_classification_threshold", 0.0)

    is_real = provenance.get("is_real_satellite_data", False)
    provider_name = provenance.get("provider", "UNKNOWN")
    provider_desc = provenance.get("description", "Not documented")

    limitation = manifest.get("limitation_notice") or stats.get("limitation_statement") or LIMITATION_STATEMENT

    return {
        "execution_timestamp": manifest.get("execution_timestamp", datetime.utcnow().isoformat() + "Z"),
        "project": manifest.get("project", "DharaScope"),
        "phase": manifest.get("phase", "Phase 1 - Satellite Feasibility Validation"),
        "study_bbox": params.get("study_bbox", [80.88, 26.80, 81.00, 26.90]),
        "threshold": threshold,
        "crs": crs,
        "t1_date": t1_date,
        "t2_date": t2_date,
        "t1_cloud": t1_cloud,
        "t2_cloud": t2_cloud,
        "t1_scene_id": t1_scene_id,
        "t2_scene_id": t2_scene_id,
        "is_real_data": is_real,
        "provider_name": provider_name,
        "provider_desc": provider_desc,
        "total_pixels": comp_px.get("total_pixels", 0),
        "common_valid_pixels": comp_px.get("common_valid_pixels", 0),
        "common_valid_area_ha": comp_px.get("common_valid_area_ha", 0.0),
        "pixel_size_m2": comp_px.get("pixel_size_m2", 100.0),
        "t1_pixels": water_t1.get("pixels", 0),
        "t1_area_m2": water_t1.get("area_m2", 0.0),
        "t1_area_ha": water_t1.get("area_hectares", 0.0),
        "t2_pixels": water_t2.get("pixels", 0),
        "t2_area_m2": water_t2.get("area_m2", 0.0),
        "t2_area_ha": water_t2.get("area_hectares", 0.0),
        "abs_change_m2": change_m.get("absolute_change_m2", 0.0),
        "abs_change_ha": change_m.get("absolute_change_hectares", 0.0),
        "pct_change": change_m.get("percentage_change"),
        "persistent_m2": change_m.get("persistent_water_m2", 0.0),
        "persistent_ha": change_m.get("persistent_water_hectares", 0.0),
        "loss_m2": change_m.get("apparent_loss_m2", 0.0),
        "loss_ha": change_m.get("apparent_loss_hectares", 0.0),
        "gain_m2": change_m.get("apparent_gain_m2", 0.0),
        "gain_ha": change_m.get("apparent_gain_hectares", 0.0),
        "limitation_statement": limitation,
    }


def generate_csv_report(
    manifest_source: Union[Dict[str, Any], Path, str, None] = None,
    output_path: Optional[Union[Path, str]] = None,
) -> Path:
    """Generate a structured CSV feasibility report from an analysis manifest.

    Args:
        manifest_source: Manifest dict, Path to JSON, or None for default output manifest.
        output_path: Target CSV file path. If None, saves to outputs/reports/.

    Returns:
        Path to the written CSV report.
    """
    manifest = load_manifest(manifest_source)
    m = extract_report_metrics(manifest)

    if output_path is None:
        target_file = REPORTS_DIR / f"dharascope_report_{m['t1_date']}_to_{m['t2_date']}.csv"
    else:
        target_file = Path(output_path)

    target_file.parent.mkdir(parents=True, exist_ok=True)

    t1_ha = m["t1_area_ha"] or 1.0
    pct_persistent = (m["persistent_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_loss = (m["loss_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_gain = (m["gain_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_change_str = f"{m['pct_change']:.2f}%" if m["pct_change"] is not None else "N/A (Zero Baseline)"

    with open(target_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header Metadata Comments
        writer.writerow(["# DharaScope Satellite Surface Water Feasibility Report"])
        writer.writerow(["# Project", m["project"]])
        writer.writerow(["# Execution Timestamp", m["execution_timestamp"]])
        writer.writerow(["# Data Provenance Provider", m["provider_name"]])
        writer.writerow(["# Real Satellite Data", "TRUE" if m["is_real_data"] else "FALSE (SYNTHETIC BENCHMARK SAMPLE)"])
        writer.writerow(["# Provider Description", m["provider_desc"]])
        writer.writerow(["# Study Area Bounding Box (WGS84)", str(m["study_bbox"])])
        writer.writerow(["# Native Coordinate Reference System", m["crs"]])
        writer.writerow(["# Spatial Ground Sampling Distance", f"{int(m['pixel_size_m2']**0.5)}m ({m['pixel_size_m2']} m²/pixel)"])
        writer.writerow(["# NDWI Classification Threshold (tau)", f"{m['threshold']:.2f}"])
        writer.writerow(["# Observation T1 (Earlier)", m["t1_scene_id"], m["t1_date"], f"{m['t1_cloud']:.2f}% cloud"])
        writer.writerow(["# Observation T2 (Later)", m["t2_scene_id"], m["t2_date"], f"{m['t2_cloud']:.2f}% cloud"])
        writer.writerow([])

        # Quantitative Metrics Table
        writer.writerow([
            "Metric Group",
            "Hydrological Category",
            "Observation Date / Period",
            "Pixel Count",
            "Area (Square Metres)",
            "Area (Hectares)",
            "Percentage of Baseline (T1)",
        ])

        writer.writerow([
            "Spatial Envelope",
            "Common Overlapping Valid Pixels",
            "Both Dates",
            m["common_valid_pixels"],
            f"{m['common_valid_pixels'] * m['pixel_size_m2']:.0f}",
            f"{m['common_valid_area_ha']:.2f}",
            "100.00%",
        ])

        writer.writerow([
            "Water Extent",
            "Earlier Surface Water (T1)",
            m["t1_date"],
            m["t1_pixels"],
            f"{m['t1_area_m2']:.0f}",
            f"{m['t1_area_ha']:.2f}",
            "100.00%",
        ])

        writer.writerow([
            "Water Extent",
            "Later Surface Water (T2)",
            m["t2_date"],
            m["t2_pixels"],
            f"{m['t2_area_m2']:.0f}",
            f"{m['t2_area_ha']:.2f}",
            f"{(m['t2_area_ha'] / t1_ha) * 100.0:.2f}%",
        ])

        writer.writerow([
            "Transition Component",
            "Perennial Channel Core (Persistent)",
            f"{m['t1_date']} to {m['t2_date']}",
            int(m["persistent_m2"] / m["pixel_size_m2"]),
            f"{m['persistent_m2']:.0f}",
            f"{m['persistent_ha']:.2f}",
            f"{pct_persistent:.2f}%",
        ])

        writer.writerow([
            "Transition Component",
            "Seasonal Recession (Apparent Loss)",
            f"{m['t1_date']} to {m['t2_date']}",
            int(m["loss_m2"] / m["pixel_size_m2"]),
            f"{m['loss_m2']:.0f}",
            f"{m['loss_ha']:.2f}",
            f"{pct_loss:.2f}%",
        ])

        writer.writerow([
            "Transition Component",
            "Inundation Expansion (Apparent Gain)",
            f"{m['t1_date']} to {m['t2_date']}",
            int(m["gain_m2"] / m["pixel_size_m2"]),
            f"{m['gain_m2']:.0f}",
            f"{m['gain_ha']:.2f}",
            f"{pct_gain:.2f}%",
        ])

        writer.writerow([
            "Summary Delta",
            "Net Surface Water Change",
            f"{m['t1_date']} to {m['t2_date']}",
            int(m["abs_change_m2"] / m["pixel_size_m2"]),
            f"{m['abs_change_m2']:.0f}",
            f"{m['abs_change_ha']:.2f}",
            pct_change_str,
        ])

        writer.writerow([])
        writer.writerow(["# Scientific Limitation Notice", m["limitation_statement"]])

    logger.info("Saved CSV report to %s", target_file)
    return target_file


def generate_pdf_report(
    manifest_source: Union[Dict[str, Any], Path, str, None] = None,
    output_path: Optional[Union[Path, str]] = None,
    include_figures: bool = True,
) -> Path:
    """Generate a publication-ready cartographic PDF feasibility report using ReportLab.

    Args:
        manifest_source: Manifest dict, Path to JSON, or None for default output manifest.
        output_path: Target PDF file path. If None, saves to outputs/reports/.
        include_figures: Whether to embed high-res PNG map figures if available.

    Returns:
        Path to the generated PDF document.
    """
    manifest = load_manifest(manifest_source)
    m = extract_report_metrics(manifest)

    if output_path is None:
        target_file = REPORTS_DIR / f"dharascope_report_{m['t1_date']}_to_{m['t2_date']}.pdf"
    else:
        target_file = Path(output_path)

    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Document Geometry
    doc = SimpleDocTemplate(
        str(target_file),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom Clean Typographic Styles
    c_charcoal = colors.HexColor("#1e293b")
    c_forest = colors.HexColor("#1b4332")
    c_muted = colors.HexColor("#64748b")
    c_light_bg = colors.HexColor("#f8fafc")
    c_border = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_charcoal,
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=c_muted,
        spaceAfter=12,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=c_forest,
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_charcoal,
    )

    code_style = ParagraphStyle(
        "ReportCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.0,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    callout_style = ParagraphStyle(
        "ReportCallout",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.0,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("DharaScope: Satellite Surface Water Extent Report", title_style))
    story.append(
        Paragraph(
            "Sentinel-2 MSI Level-2A Feasibility Assessment &middot; Gomti River, Lucknow, UP &middot; "
            f"Execution: {m['execution_timestamp'][:19]}Z",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=c_border, spaceAfter=8))

    # 2. Data Provenance Status Strip
    if m["is_real_data"]:
        prov_title = "VALIDATED REAL SATELLITE DATA"
        prov_color = colors.HexColor("#166534")
        prov_bg = colors.HexColor("#f0fdf4")
        prov_border = colors.HexColor("#86efac")
    else:
        prov_title = "BENCHMARK SAMPLE DATA (SYNTHETIC — NOT REAL SATELLITE OBSERVATIONS)"
        prov_color = colors.HexColor("#9a3412")
        prov_bg = colors.HexColor("#fff7ed")
        prov_border = colors.HexColor("#fed7aa")

    prov_p = Paragraph(
        f"<b>PROVENANCE STATUS: {prov_title}</b><br/>"
        f"Provider: {m['provider_name']} &mdash; {m['provider_desc']}",
        ParagraphStyle("ProvP", parent=body_style, textColor=prov_color, fontSize=8.0, leading=11),
    )
    prov_table = Table([[prov_p]], colWidths=[540])
    prov_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), prov_bg),
            ("BOX", (0, 0), (-1, -1), 1, prov_border),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(prov_table)
    story.append(Spacer(1, 8))

    # 3. Parameters & Metadata Strip
    meta_data = [
        [
            Paragraph("<b>Study Reach:</b> Gomti River, Lucknow", body_style),
            Paragraph(f"<b>CRS:</b> {m['crs']}", body_style),
            Paragraph(f"<b>Resolution:</b> {int(m['pixel_size_m2']**0.5)}m ({m['pixel_size_m2']} m²/px)", body_style),
        ],
        [
            Paragraph(f"<b>Study Bounding Box:</b> {m['study_bbox']}", body_style),
            Paragraph(f"<b>NDWI Threshold:</b> &tau; = {m['threshold']:.2f}", body_style),
            Paragraph(f"<b>Evaluated Area:</b> {m['common_valid_area_ha']:,.2f} ha", body_style),
        ],
        [
            Paragraph(f"<b>Observation T1:</b> {m['t1_date']} ({m['t1_cloud']:.1f}% cloud)", body_style),
            Paragraph(f"<b>Observation T2:</b> {m['t2_date']} ({m['t2_cloud']:.1f}% cloud)", body_style),
            Paragraph(f"<b>Interval:</b> 60 calendar days", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[180, 180, 180])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_light_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 4. Quantitative Change Analysis Table
    story.append(Paragraph("1. Quantitative Surface Water Dynamic Metrics", section_heading))

    t1_ha = m["t1_area_ha"] or 1.0
    pct_persistent = (m["persistent_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_loss = (m["loss_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_gain = (m["gain_ha"] / t1_ha) * 100.0 if t1_ha > 0 else 0.0
    pct_change_str = f"{m['pct_change']:.2f}%" if m["pct_change"] is not None else "N/A"
    sign_abs = "+" if m["abs_change_ha"] > 0 else ""

    metrics_rows = [
        ["Hydrological Classification Category", "Pixel Count", "Area (m²)", "Area (ha)", "% of T1 Baseline"],
        [
            Paragraph("<b>Earlier Inundation (T1)</b>", body_style),
            f"{m['t1_pixels']:,}",
            f"{m['t1_area_m2']:,.0f}",
            f"{m['t1_area_ha']:,.2f}",
            "100.00%",
        ],
        [
            Paragraph("<b>Later Inundation (T2)</b>", body_style),
            f"{m['t2_pixels']:,}",
            f"{m['t2_area_m2']:,.0f}",
            f"{m['t2_area_ha']:,.2f}",
            f"{(m['t2_area_ha'] / t1_ha) * 100.0:.2f}%",
        ],
        [
            Paragraph("Perennial Channel Core (Persistent)", body_style),
            f"{int(m['persistent_m2'] / m['pixel_size_m2']):,}",
            f"{m['persistent_m2']:,.0f}",
            f"{m['persistent_ha']:,.2f}",
            f"{pct_persistent:.2f}%",
        ],
        [
            Paragraph("Seasonal Channel Recession (Apparent Loss)", body_style),
            f"{int(m['loss_m2'] / m['pixel_size_m2']):,}",
            f"{m['loss_m2']:,.0f}",
            f"{m['loss_ha']:,.2f}",
            f"{pct_loss:.2f}%",
        ],
        [
            Paragraph("Localized Inundation Expansion (Apparent Gain)", body_style),
            f"{int(m['gain_m2'] / m['pixel_size_m2']):,}",
            f"{m['gain_m2']:,.0f}",
            f"{m['gain_ha']:,.2f}",
            f"{pct_gain:.2f}%",
        ],
        [
            Paragraph("<b>Net Surface Extent Delta (T2 - T1)</b>", body_style),
            f"{int(m['abs_change_m2'] / m['pixel_size_m2']):,}",
            f"{sign_abs}{m['abs_change_m2']:,.0f}",
            f"{sign_abs}{m['abs_change_ha']:,.2f}",
            f"<b>{pct_change_str}</b>",
        ],
    ]

    metric_table = Table(metrics_rows, colWidths=[200, 75, 95, 80, 90])
    metric_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.0),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
            ("BACKGROUND", (0, 1), (-1, 1), c_light_bg),
            ("BACKGROUND", (0, 2), (-1, 2), c_light_bg),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ])
    )
    story.append(metric_table)
    story.append(Spacer(1, 10))

    # 5. Embedded Map Figures (if requested and present)
    if include_figures:
        panel_img_path = OUTPUTS_DIR / "gomti_water_change_comparison_panel.png"
        change_map_path = OUTPUTS_DIR / f"water_change_{m['t1_date']}_to_{m['t2_date']}.png"

        if panel_img_path.exists():
            story.append(KeepTogether([
                Paragraph("2. Multi-Temporal Cartographic Visualization", section_heading),
                Paragraph(
                    "Figure 1: Synoptic 4-panel analysis illustrating continuous NDWI distributions, "
                    "binary water masks, and the spatial transition matrix over Lucknow.",
                    body_style,
                ),
                Spacer(1, 4),
                Image(str(panel_img_path), width=7.2 * inch, height=3.6 * inch),
                Spacer(1, 8),
            ]))

        if change_map_path.exists():
            story.append(KeepTogether([
                Paragraph("Figure 2: Four-class categorical water transition map.", section_heading),
                Image(str(change_map_path), width=5.5 * inch, height=3.8 * inch),
                Spacer(1, 8),
            ]))

    # 6. Scientific Methodology Section
    story.append(Paragraph("3. Spectral Index Formulation & Analytical Methodology", section_heading))
    method_text = (
        "<b>Normalized Difference Water Index (NDWI) [McFeeters, 1996]:</b><br/>"
        "Surface water boundaries are delineated using the normalized difference of green and near-infrared reflectances: "
        "<code>NDWI = (Band 3 [Green] - Band 8 [NIR]) / (Band 3 [Green] + Band 8 [NIR])</code>.<br/>"
        "Liquid water exhibits high reflectance in optical green wavelengths (560 nm) and near-total absorption in near-infrared "
        "(842 nm), whereas terrestrial vegetation and urban soils strongly reflect NIR radiation. "
        "Pixels satisfying <code>NDWI &gt; 0.00</code> across common valid pixels are classified as open water.<br/>"
        "<b>Numerical Protections:</b> Denominators satisfying <code>|B03 + B08| &le; 1e-6</code> are masked as invalid to eliminate "
        "division by zero, and valid ratios are constrained to the theoretical physical domain <code>[-1.0, 1.0]</code>."
    )
    story.append(Paragraph(method_text, body_style))
    story.append(Spacer(1, 8))

    # 7. Scientific Limitation & Academic Disclaimer
    story.append(Paragraph("4. Hydrological Limitations & Evaluation Disclaimer", section_heading))
    callout_p = Paragraph(
        f"<b>ACADEMIC NOTICE:</b> {m['limitation_statement']}<br/><br/>"
        "<b>Observed Satellite-Derived Changes:</b> Analytical metrics report observed variations in optical open-water surface reflectance (NDWI &gt; 0.00) between the analyzed observation dates. "
        "Satellite Earth observation measures planar surface reflectance and does NOT directly observe or prove underlying hydrological processes, channel bathymetry, or hydraulic operations. "
        "Observed surface water changes represent optical surface reflections and do NOT independently establish permanent volumetric changes, "
        "groundwater interactions, discharge rates, or water contamination without synchronized in-situ stream gauging, bathymetric surveys, and operational records.",
        callout_style,
    )
    callout_table = Table([[callout_p]], colWidths=[540])
    callout_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(callout_table)

    # Build Document
    doc.build(story)
    logger.info("Saved PDF report to %s", target_file)
    return target_file
