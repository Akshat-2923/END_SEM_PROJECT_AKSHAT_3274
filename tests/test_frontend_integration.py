"""Integration tests verifying full frontend workflow against FastAPI backend service layer.

Validates the complete end-to-end user journey matching Phase 2.3 requirements:
1. Health & service discovery (GET /api/v1/health).
2. Bearer authentication & user profile retrieval (GET /api/v1/auth/me).
3. Geographical AOI validation (POST /api/v1/aois/validate) for valid and invalid polygons.
4. AOI persistence and catalog listing (POST /api/v1/aois, GET /api/v1/aois).
5. Satellite analysis run dispatch, status polling, and execution (POST /api/v1/analyses).
6. Quantitative surface water metrics & limitation statement (GET /api/v1/analyses/{id}/metrics).
7. Cartographic artifact enumeration & secure downloads (GET /api/v1/analyses/{id}/artifacts, GET /api/v1/artifacts/{id}/download).
8. Publication-ready ReportLab PDF and CSV report streaming (GET /api/v1/analyses/{id}/reports/pdf, csv).
9. Authorization enforcement & cross-user tenant isolation.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

import server
from tests.test_auth_jwt import create_test_jwt

client = TestClient(server.app)

LUCKNOW_GOMTI_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [
            [80.90, 26.84],
            [80.92, 26.84],
            [80.92, 26.86],
            [80.90, 26.86],
            [80.90, 26.84],
        ]
    ],
}

INVALID_TINY_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [
            [80.9000, 26.8400],
            [80.9001, 26.8400],
            [80.9001, 26.8401],
            [80.9000, 26.8401],
            [80.9000, 26.8400],
        ]
    ],
}


@pytest.fixture
def hydrologist_user():
    """Authenticated hydrologist user fixture."""
    uid = str(uuid.uuid4())
    email = f"gomti_{uid[:8]}@dharascope.org"
    token = create_test_jwt(
        sub=uid,
        email=email,
        app_metadata={"role": "user"},
        user_metadata={"full_name": "Dr. Gomti Hydrologist"},
    )
    return {
        "id": uid,
        "email": email,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def other_user():
    """Second independent user fixture for isolation verification."""
    uid = str(uuid.uuid4())
    email = f"other_{uid[:8]}@dharascope.org"
    token = create_test_jwt(
        sub=uid,
        email=email,
        app_metadata={"role": "user"},
    )
    return {
        "id": uid,
        "email": email,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


class TestFrontendBackendIntegrationWorkflow:
    """Verifies complete interactive workflow corresponding to frontend components."""

    def test_step_1_health_and_telemetry(self):
        """Frontend telemetry check against GET /api/v1/health."""
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("healthy", "operational")
        assert data["app_name"] == "DharaScope"
        assert "database" in data

    def test_step_2_authentication_and_profile_sync(self, hydrologist_user):
        """Frontend session initialization against GET /api/v1/auth/me."""
        # Unauthenticated request rejected
        unauth_res = client.get("/api/v1/auth/me")
        assert unauth_res.status_code == 401

        # Authenticated request auto-provisions profile
        res = client.get("/api/v1/auth/me", headers=hydrologist_user["headers"])
        assert res.status_code == 200
        profile = res.json()
        assert profile["id"] == hydrologist_user["id"]
        assert profile["email"] == hydrologist_user["email"]
        assert profile["role"] == "user"
        assert profile["quota_monthly_runs"] > 0

    def test_step_3_aoi_real_backend_validation(self, hydrologist_user):
        """MapPicker backend validation feedback via POST /api/v1/aois/validate."""
        # Valid Gomti reach polygon
        valid_res = client.post(
            "/api/v1/aois/validate",
            json={"geometry": LUCKNOW_GOMTI_GEOMETRY},
            headers=hydrologist_user["headers"],
        )
        assert valid_res.status_code == 200
        val_data = valid_res.json()
        assert val_data["valid"] is True
        assert val_data["geometry_type"] == "Polygon"
        assert val_data["area_km2"] >= 0.10
        assert val_data["area_km2"] <= 100.00
        assert val_data["vertex_count"] == 5
        assert len(val_data["bbox"]) == 4
        assert len(val_data["centroid"]) == 2

        # Invalid tiny geometry (< 0.10 km²) returns 400 AOIValidationError
        invalid_res = client.post(
            "/api/v1/aois/validate",
            json={"geometry": INVALID_TINY_GEOMETRY},
            headers=hydrologist_user["headers"],
        )
        assert invalid_res.status_code == 400
        err_data = invalid_res.json()
        assert err_data["error"] == "AOIValidationError"
        assert "below the minimum threshold" in err_data["detail"]

    def test_step_4_aoi_persistence_and_catalog(self, hydrologist_user):
        """AOIManager persistence via POST /api/v1/aois and listing via GET /api/v1/aois."""
        create_res = client.post(
            "/api/v1/aois",
            json={
                "name": "Lucknow Gomti Baseline Reach",
                "description": "Urban monitoring reach for Sentinel-2 surface water dynamics",
                "geometry": LUCKNOW_GOMTI_GEOMETRY,
                "is_public": False,
            },
            headers=hydrologist_user["headers"],
        )
        assert create_res.status_code == 201
        aoi = create_res.json()
        aoi_id = aoi["id"]
        assert aoi["name"] == "Lucknow Gomti Baseline Reach"
        assert aoi["area_km2"] > 0

        # Enumerate AOIs
        list_res = client.get("/api/v1/aois", headers=hydrologist_user["headers"])
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(item["id"] == aoi_id for item in items)

    def test_step_5_complete_analysis_to_report_pipeline(self, hydrologist_user):
        """Full end-to-end pipeline: Dispatch -> Status -> Metrics -> Artifacts -> PDF/CSV Downloads."""
        # 1. Create AOI
        aoi_res = client.post(
            "/api/v1/aois",
            json={"name": "End-to-End Study Reach", "geometry": LUCKNOW_GOMTI_GEOMETRY},
            headers=hydrologist_user["headers"],
        )
        aoi_id = aoi_res.json()["id"]

        # 2. Launch Analysis (synchronous execution for deterministic end-to-end verification)
        analysis_payload = {
            "aoi_id": aoi_id,
            "ndwi_threshold": 0.00,
            "max_cloud_cover": 10.0,
            "datetime_range": "2023-10-01T00:00:00Z/2024-05-31T23:59:59Z",
            "data_source": "synthetic",
        }
        dispatch_res = client.post(
            "/api/v1/analyses?sync=true",
            json=analysis_payload,
            headers=hydrologist_user["headers"],
        )
        assert dispatch_res.status_code == 201
        run_data = dispatch_res.json()
        analysis_id = run_data["id"]

        # 3. Verify status polling endpoint (GET /api/v1/analyses/{id})
        status_res = client.get(f"/api/v1/analyses/{analysis_id}", headers=hydrologist_user["headers"])
        assert status_res.status_code == 200
        run_status = status_res.json()
        assert run_status["status"] == "SUCCESS"
        assert run_status["execution_duration_sec"] is not None
        assert run_status["execution_duration_sec"] > 0
        assert "t1_scene_id" in run_status
        assert "t2_scene_id" in run_status

        # 4. Verify Quantitative Metrics (GET /api/v1/analyses/{id}/metrics)
        metrics_res = client.get(
            f"/api/v1/analyses/{analysis_id}/metrics",
            headers=hydrologist_user["headers"],
        )
        assert metrics_res.status_code == 200
        m = metrics_res.json()
        assert m["common_valid_pixels"] > 0
        assert m["t1_water_area_ha"] > 0
        assert m["t2_water_area_ha"] > 0
        assert m["apparent_loss_ha"] >= 0
        assert m["apparent_gain_ha"] >= 0
        assert m["persistent_water_ha"] >= 0
        assert m["limitation_statement"] != ""

        # 5. Verify Generated Artifacts (GET /api/v1/analyses/{id}/artifacts)
        artifacts_res = client.get(
            f"/api/v1/analyses/{analysis_id}/artifacts",
            headers=hydrologist_user["headers"],
        )
        assert artifacts_res.status_code == 200
        artifacts = artifacts_res.json()["items"]
        assert len(artifacts) >= 5

        # Verify no system paths leaked in artifact metadata
        for art in artifacts:
            assert "C:" not in art["download_url"]
            assert "/api/v1/artifacts/" in art["download_url"]

        # 6. Verify Authenticated PDF Report Download (GET /api/v1/analyses/{id}/reports/pdf)
        pdf_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/pdf",
            headers=hydrologist_user["headers"],
        )
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers["content-type"]
        assert pdf_res.content.startswith(b"%PDF")

        # 7. Verify Authenticated CSV Report Download (GET /api/v1/analyses/{id}/reports/csv)
        csv_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/csv",
            headers=hydrologist_user["headers"],
        )
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert b"DharaScope Satellite Surface Water Feasibility Report" in csv_res.content

        # 8. Verify Map Image Artifact Download (GET /api/v1/artifacts/{id}/download)
        panel_art = next(a for a in artifacts if a["artifact_type"] == "PANEL_PNG")
        art_download_res = client.get(
            panel_art["download_url"],
            headers=hydrologist_user["headers"],
        )
        assert art_download_res.status_code == 200
        assert art_download_res.headers["content-type"] == "image/png"
        assert art_download_res.content.startswith(b"\x89PNG")

    def test_step_6_cross_user_isolation(self, hydrologist_user, other_user):
        """Verify strict tenant authorization: User B cannot download User A's reports or access private AOIs."""
        # User A creates private AOI and analysis
        aoi_res = client.post(
            "/api/v1/aois",
            json={"name": "User A Reach", "geometry": LUCKNOW_GOMTI_GEOMETRY, "is_public": False},
            headers=hydrologist_user["headers"],
        )
        aoi_id = aoi_res.json()["id"]

        analysis_res = client.post(
            "/api/v1/analyses?sync=true",
            json={"aoi_id": aoi_id, "data_source": "synthetic"},
            headers=hydrologist_user["headers"],
        )
        analysis_id = analysis_res.json()["id"]

        # User B attempts to access User A's private AOI -> 404
        aoi_b_res = client.get(f"/api/v1/aois/{aoi_id}", headers=other_user["headers"])
        assert aoi_b_res.status_code == 404

        # User B attempts to access User A's analysis -> 404
        analysis_b_res = client.get(f"/api/v1/analyses/{analysis_id}", headers=other_user["headers"])
        assert analysis_b_res.status_code == 404

        # User B attempts to download User A's PDF report -> 404
        pdf_b_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/pdf",
            headers=other_user["headers"],
        )
        assert pdf_b_res.status_code == 404
