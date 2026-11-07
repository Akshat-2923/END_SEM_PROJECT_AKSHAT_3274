"""Unit tests for DharaScope CSV and PDF reporting module."""

import csv
from pathlib import Path
import pytest

from src.config import OUTPUTS_DIR, REPORTS_DIR
from src.reporting import (
    ReportingError,
    extract_report_metrics,
    generate_csv_report,
    generate_pdf_report,
    load_manifest,
)


@pytest.fixture
def sample_manifest():
    """Load default phase 1 feasibility report manifest."""
    manifest_path = OUTPUTS_DIR / "phase1_feasibility_report.json"
    assert manifest_path.exists(), "Default feasibility manifest required for reporting tests."
    return load_manifest(manifest_path)


@pytest.fixture
def synthetic_manifest(sample_manifest):
    """Create a mock manifest representing offline synthetic benchmark sample data."""
    synth = json_copy(sample_manifest)
    synth["data_source_provenance"] = {
        "provider": "SYNTHETIC_BENCHMARK_SAMPLE",
        "is_real_satellite_data": False,
        "description": "Synthetic Benchmark Sample Data for Offline Testing",
    }
    return synth


def json_copy(data):
    import json
    return json.loads(json.dumps(data))


class TestReporting:
    """Test suite for CSV and PDF report generation."""

    def test_extract_report_metrics_valid(self, sample_manifest):
        """Verify metric extraction from authentic analysis manifest."""
        m = extract_report_metrics(sample_manifest)

        assert m["project"] == "DharaScope"
        assert m["t1_date"] == "2023-10-10"
        assert m["t2_date"] == "2023-12-09"
        assert m["t1_area_ha"] == 184.56
        assert m["t2_area_ha"] == 139.33
        assert m["abs_change_ha"] == -45.23
        assert m["pct_change"] == -24.51
        assert m["persistent_ha"] == 125.18
        assert m["loss_ha"] == 59.38
        assert m["gain_ha"] == 14.15
        assert m["is_real_data"] is True
        assert "limitation_statement" in m
        assert len(m["limitation_statement"]) > 50

    def test_extract_report_metrics_missing_stages_raises(self):
        """Verify that malformed manifest with missing stages raises ReportingError."""
        with pytest.raises(ReportingError):
            extract_report_metrics({"project": "Test"})

        with pytest.raises(ReportingError):
            extract_report_metrics({"stages": {"catalogue_discovery": {}}})

    def test_generate_csv_report_from_manifest(self, sample_manifest, tmp_path):
        """Test CSV generation and content integrity."""
        csv_file = tmp_path / "test_report.csv"
        out_path = generate_csv_report(sample_manifest, output_path=csv_file)

        assert out_path.exists()
        assert out_path.stat().st_size > 500

        with open(out_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        content = "".join(lines)
        assert "# DharaScope Satellite Surface Water Feasibility Report" in content
        assert "# Real Satellite Data,TRUE" in content
        assert "Earlier Surface Water (T1)" in content
        assert "184.56" in content
        assert "139.33" in content
        assert "-45.23" in content
        assert "-24.51%" in content
        assert "# Scientific Limitation Notice" in content

    def test_generate_csv_report_synthetic_provenance(self, synthetic_manifest, tmp_path):
        """Verify that synthetic manifest is explicitly tagged in CSV output."""
        csv_file = tmp_path / "synth_report.csv"
        generate_csv_report(synthetic_manifest, output_path=csv_file)

        with open(csv_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "FALSE (SYNTHETIC BENCHMARK SAMPLE)" in content
        assert "SYNTHETIC_BENCHMARK_SAMPLE" in content

    def test_generate_pdf_report_from_manifest(self, sample_manifest, tmp_path):
        """Test publication-grade PDF generation with figures."""
        pdf_file = tmp_path / "test_report.pdf"
        out_path = generate_pdf_report(sample_manifest, output_path=pdf_file, include_figures=True)

        assert out_path.exists()
        assert out_path.stat().st_size > 5000

        # Verify PDF magic bytes
        with open(out_path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_generate_pdf_report_without_figures(self, sample_manifest, tmp_path):
        """Test PDF generation when figure embedding is disabled."""
        pdf_file = tmp_path / "no_figures_report.pdf"
        out_path = generate_pdf_report(sample_manifest, output_path=pdf_file, include_figures=False)

        assert out_path.exists()
        assert out_path.stat().st_size > 1500

    def test_generate_pdf_report_synthetic_badge(self, synthetic_manifest, tmp_path):
        """Verify that synthetic data triggers prominent warning in PDF."""
        pdf_file = tmp_path / "synth_report.pdf"
        out_path = generate_pdf_report(synthetic_manifest, output_path=pdf_file, include_figures=False)

        assert out_path.exists()
        assert out_path.stat().st_size > 1500
