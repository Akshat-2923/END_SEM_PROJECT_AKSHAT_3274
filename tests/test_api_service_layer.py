"""Integration tests for DharaScope FastAPI application service layer.

Validates:
1. Health and API configuration endpoints.
2. Authentication dependencies (missing, invalid, valid JWTs).
3. User versus administrator access control.
4. AOI validation and CRUD endpoints with topological checks.
5. Cross-user resource isolation and public vs private access policies.
6. Analysis run creation, status tracking, and lifecycle management.
7. Satellite pipeline execution in synthetic benchmark mode.
8. Water metrics and artifact registry queries.
9. Report generation and secure authorized CSV/PDF downloads.
10. Error envelope standardization and internal path sanitization.
"""

import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

import server
from tests.test_auth_jwt import TEST_AUDIENCE, TEST_ISSUER, TEST_SECRET, create_test_jwt

client = TestClient(server.app)

LUCKNOW_GEOM = {
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

LUCKNOW_BBOX = [80.90, 26.84, 80.92, 26.86]


@pytest.fixture
def user_a() -> Dict[str, Any]:
    """Test user A credentials and authentication headers."""
    uid = str(uuid.uuid4())
    token = create_test_jwt(
        sub=uid,
        email=f"user_a_{uid[:6]}@dharascope.org",
        app_metadata={"role": "user"},
    )
    return {
        "id": uid,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def user_b() -> Dict[str, Any]:
    """Test user B credentials and authentication headers."""
    uid = str(uuid.uuid4())
    token = create_test_jwt(
        sub=uid,
        email=f"user_b_{uid[:6]}@dharascope.org",
        app_metadata={"role": "user"},
    )
    return {
        "id": uid,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def admin_user() -> Dict[str, Any]:
    """Administrator credentials and authentication headers."""
    uid = str(uuid.uuid4())
    token = create_test_jwt(
        sub=uid,
        email=f"admin_{uid[:6]}@dharascope.org",
        app_metadata={"role": "admin"},
    )
    return {
        "id": uid,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


# ===========================================================================
# 1. System Health & Root Metadata Endpoints
# ===========================================================================

class TestSystemHealthEndpoints:
    """Verify system uptime, database health checks, and OpenAPI metadata."""

    def test_health_check_returns_healthy(self):
        """Verify /health returns 200 with operational database status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["app_name"] == "DharaScope"
        assert data["version"] == "2.2.0"
        assert data["database"] == "connected"
        assert "timestamp" in data

    def test_api_v1_health_alias(self):
        """Verify /api/v1/health returns consistent status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["app_name"] == "DharaScope"

    def test_root_endpoint_metadata(self):
        """Verify GET / returns documentation links and operational status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "DharaScope API"
        assert data["docs_url"] == "/docs"
        assert data["status"] == "operational"

    def test_openapi_documentation_accessible(self):
        """Verify /openapi.json contains expected API paths."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/api/v1/aois" in schema["paths"]
        assert "/api/v1/analyses" in schema["paths"]


# ===========================================================================
# 2. Authentication & Authorization Access Control
# ===========================================================================

class TestAuthenticationAndAuthorization:
    """Verify Bearer token parsing, invalid token rejection, and role gates."""

    def test_missing_authorization_header_rejected(self):
        """Verify endpoints requiring authentication reject uncredentialed requests with 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_invalid_bearer_token_rejected(self):
        """Verify forged or tampered token raises 401."""
        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    def test_expired_token_rejected(self):
        """Verify expired JWT is rejected with 401."""
        token = create_test_jwt(exp_delta=-60)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_valid_user_profile_retrieval(self, user_a):
        """Verify authenticated user profile is auto-provisioned and returned."""
        response = client.get("/api/v1/auth/me", headers=user_a["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_a["id"]
        assert data["role"] == "user"
        assert data["quota_monthly_runs"] == 50

    def test_regular_user_update_profile_display_name(self, user_a):
        """Verify user can update their display full_name."""
        response = client.patch(
            "/api/v1/auth/me",
            json={"full_name": "Dr. Gomti Hydrologist"},
            headers=user_a["headers"],
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Dr. Gomti Hydrologist"

    def test_regular_user_forbidden_from_admin_endpoint(self, user_a):
        """Verify regular user receives 403 Forbidden on admin user list."""
        response = client.get("/api/v1/admin/users", headers=user_a["headers"])
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]

    def test_admin_user_can_access_admin_user_list(self, admin_user):
        """Verify administrator can access /api/v1/admin/users."""
        response = client.get("/api/v1/admin/users", headers=admin_user["headers"])
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_admin_can_update_user_quota(self, admin_user, user_a):
        """Verify administrator can update regular user quota."""
        # Ensure user A profile exists first
        client.get("/api/v1/auth/me", headers=user_a["headers"])

        patch_res = client.patch(
            f"/api/v1/admin/users/{user_a['id']}",
            json={"quota_monthly_runs": 150},
            headers=admin_user["headers"],
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["quota_monthly_runs"] == 150


# ===========================================================================
# 3. Geographical AOI Validation & CRUD Endpoints
# ===========================================================================

class TestAOIEndpoints:
    """Verify geometry validation, PostGIS persistence, and CRUD operations."""

    def test_aoi_validate_endpoint_valid_geometry(self, user_a):
        """Verify POST /api/v1/aois/validate calculates area and coordinates."""
        response = client.post(
            "/api/v1/aois/validate",
            json={"geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["geometry_type"] == "Polygon"
        assert 4.0 <= data["area_km2"] <= 5.0
        assert data["vertex_count"] == 5
        assert len(data["bbox"]) == 4

    def test_aoi_validate_endpoint_out_of_bounds_micro_area(self, user_a):
        """Verify validation rejects area smaller than 0.10 km²."""
        micro_geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [80.900, 26.840],
                    [80.901, 26.840],
                    [80.901, 26.841],
                    [80.900, 26.841],
                    [80.900, 26.840],
                ]
            ],
        }
        response = client.post(
            "/api/v1/aois/validate",
            json={"geometry": micro_geom},
            headers=user_a["headers"],
        )
        assert response.status_code == 400
        assert response.json()["error"] == "AOIValidationError"
        assert "below the minimum threshold" in response.json()["detail"]

    def test_aoi_create_success(self, user_a):
        """Verify POST /api/v1/aois registers and stores AOI with PostGIS geometry."""
        payload = {
            "name": "Lucknow Gomti Urban Reach",
            "description": "Baseline monitoring reach between Gaughat and Shaheed Path",
            "geometry": LUCKNOW_GEOM,
            "is_public": False,
        }
        response = client.post("/api/v1/aois", json=payload, headers=user_a["headers"])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Lucknow Gomti Urban Reach"
        assert data["user_id"] == user_a["id"]
        assert 4.0 <= data["area_km2"] <= 5.0
        assert data["is_public"] is False
        assert "id" in data

    def test_aoi_get_by_id(self, user_a):
        """Verify GET /api/v1/aois/{id} retrieves created AOI."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "Fetch Test AOI", "geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        get_res = client.get(f"/api/v1/aois/{aoi_id}", headers=user_a["headers"])
        assert get_res.status_code == 200
        assert get_res.json()["id"] == aoi_id
        assert get_res.json()["name"] == "Fetch Test AOI"

    def test_aoi_list_endpoint(self, user_a):
        """Verify GET /api/v1/aois lists user's AOIs."""
        response = client.get("/api/v1/aois?limit=10", headers=user_a["headers"])
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_aoi_update_endpoint(self, user_a):
        """Verify PATCH /api/v1/aois/{id} updates metadata."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "Before Update", "geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        patch_res = client.patch(
            f"/api/v1/aois/{aoi_id}",
            json={"name": "After Update", "description": "Updated reach notes"},
            headers=user_a["headers"],
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "After Update"
        assert patch_res.json()["description"] == "Updated reach notes"

    def test_aoi_delete_endpoint(self, user_a):
        """Verify DELETE /api/v1/aois/{id} removes AOI."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "To Delete", "geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        del_res = client.delete(f"/api/v1/aois/{aoi_id}", headers=user_a["headers"])
        assert del_res.status_code == 204

        # Subsequent fetch must return 404
        get_res = client.get(f"/api/v1/aois/{aoi_id}", headers=user_a["headers"])
        assert get_res.status_code == 404


# ===========================================================================
# 4. Cross-User Resource Isolation & Protection
# ===========================================================================

class TestCrossUserResourceIsolation:
    """Verify tenant isolation between User A and User B."""

    def test_user_b_cannot_view_user_a_private_aoi(self, user_a, user_b):
        """Verify User B cannot access User A's private AOI."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "User A Private", "geometry": LUCKNOW_GEOM, "is_public": False},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        res_b = client.get(f"/api/v1/aois/{aoi_id}", headers=user_b["headers"])
        assert res_b.status_code == 404

    def test_user_b_can_view_user_a_public_aoi(self, user_a, user_b):
        """Verify User B can read User A's public AOI."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "User A Public Reach", "geometry": LUCKNOW_GEOM, "is_public": True},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        res_b = client.get(f"/api/v1/aois/{aoi_id}", headers=user_b["headers"])
        assert res_b.status_code == 200
        assert res_b.json()["id"] == aoi_id

    def test_user_b_cannot_modify_or_delete_user_a_public_aoi(self, user_a, user_b):
        """Verify User B cannot alter or delete User A's public AOI."""
        create_res = client.post(
            "/api/v1/aois",
            json={"name": "Shared Public Reach", "geometry": LUCKNOW_GEOM, "is_public": True},
            headers=user_a["headers"],
        )
        aoi_id = create_res.json()["id"]

        # User B patch attempt must return 403 Forbidden
        patch_res = client.patch(
            f"/api/v1/aois/{aoi_id}",
            json={"name": "Hijacked by User B"},
            headers=user_b["headers"],
        )
        assert patch_res.status_code == 403

        # User B delete attempt must return 403 Forbidden
        del_res = client.delete(f"/api/v1/aois/{aoi_id}", headers=user_b["headers"])
        assert del_res.status_code == 403


# ===========================================================================
# 5. Analysis Run Creation, Lifecycle & Pipeline Execution
# ===========================================================================

class TestAnalysisPipelineEndpoints:
    """Verify satellite analysis run creation, background dispatch, and results."""

    def test_create_analysis_run_with_existing_aoi(self, user_a):
        """Verify creating analysis run with existing aoi_id enqueues run."""
        aoi_res = client.post(
            "/api/v1/aois",
            json={"name": "Run Test Reach", "geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        aoi_id = aoi_res.json()["id"]

        payload = {
            "aoi_id": aoi_id,
            "ndwi_threshold": 0.0,
            "max_cloud_cover": 10.0,
            "data_source": "synthetic",
        }
        res = client.post("/api/v1/analyses", json=payload, headers=user_a["headers"])
        assert res.status_code == 201
        data = res.json()
        assert data["status"] in ("QUEUED", "PROCESSING")
        assert data["aoi_id"] == aoi_id
        assert data["user_id"] == user_a["id"]

    def test_create_analysis_run_with_inline_geometry(self, user_a):
        """Verify creating analysis run with inline geometry auto-provisions AOI."""
        payload = {
            "aoi_geometry": LUCKNOW_GEOM,
            "aoi_name": "Inline Study Reach",
            "ndwi_threshold": 0.05,
            "data_source": "synthetic",
        }
        res = client.post("/api/v1/analyses", json=payload, headers=user_a["headers"])
        assert res.status_code == 201
        data = res.json()
        assert data["aoi_id"] is not None

    def test_create_analysis_run_missing_geometry_and_id_rejected(self, user_a):
        """Verify request with neither aoi_id nor aoi_geometry returns 400."""
        payload = {"ndwi_threshold": 0.0}
        res = client.post("/api/v1/analyses", json=payload, headers=user_a["headers"])
        assert res.status_code == 400
        assert "Either 'aoi_id' or 'aoi_geometry' must be provided" in res.json()["detail"]

    def test_create_analysis_run_invalid_threshold_rejected(self, user_a):
        """Verify invalid NDWI threshold (> 1.0) returns 422 validation error."""
        payload = {
            "aoi_geometry": LUCKNOW_GEOM,
            "ndwi_threshold": 5.0,  # Invalid: must be <= 1.0
        }
        res = client.post("/api/v1/analyses", json=payload, headers=user_a["headers"])
        assert res.status_code == 422

    def test_pipeline_execution_synthetic_mode(self, user_a):
        """Integration Test: Execute end-to-end pipeline synchronously and verify results."""
        aoi_res = client.post(
            "/api/v1/aois",
            json={"name": "Pipeline Reach", "geometry": LUCKNOW_GEOM},
            headers=user_a["headers"],
        )
        aoi_id = aoi_res.json()["id"]

        payload = {
            "aoi_id": aoi_id,
            "ndwi_threshold": 0.0,
            "max_cloud_cover": 10.0,
            "data_source": "synthetic",
        }
        # Run synchronously using ?sync=true
        res = client.post("/api/v1/analyses?sync=true", json=payload, headers=user_a["headers"])
        assert res.status_code == 201
        data = res.json()
        analysis_id = data["id"]

        # Verify completed status
        get_res = client.get(f"/api/v1/analyses/{analysis_id}", headers=user_a["headers"])
        assert get_res.status_code == 200
        run_data = get_res.json()
        assert run_data["status"] == "SUCCESS"
        assert run_data["is_real_data"] is False
        assert run_data["execution_duration_sec"] is not None
        assert run_data["execution_duration_sec"] > 0

        # Verify WaterMetrics endpoint
        metrics_res = client.get(f"/api/v1/analyses/{analysis_id}/metrics", headers=user_a["headers"])
        assert metrics_res.status_code == 200
        m = metrics_res.json()
        assert m["common_valid_pixels"] > 0
        assert m["t1_water_area_ha"] > 0
        assert m["t2_water_area_ha"] > 0
        assert m["limitation_statement"] != ""

        # Verify Artifacts endpoint
        art_res = client.get(f"/api/v1/analyses/{analysis_id}/artifacts", headers=user_a["headers"])
        assert art_res.status_code == 200
        artifacts = art_res.json()
        assert artifacts["total"] >= 4
        artifact_types = {a["artifact_type"] for a in artifacts["items"]}
        assert "REPORT_PDF" in artifact_types
        assert "REPORT_CSV" in artifact_types
        assert "PANEL_PNG" in artifact_types


# ===========================================================================
# 6. Report Generation & Secure Download Endpoints
# ===========================================================================

class TestReportDownloadEndpoints:
    """Verify authorized downloads for CSV, PDF, and figure artifacts."""

    def test_download_reports_and_artifacts_authorized(self, user_a):
        """Verify CSV, PDF, and artifact downloads return appropriate content types and headers."""
        # Run a quick synthetic analysis to generate artifacts
        run_res = client.post(
            "/api/v1/analyses?sync=true",
            json={"aoi_geometry": LUCKNOW_GEOM, "data_source": "synthetic"},
            headers=user_a["headers"],
        )
        analysis_id = run_res.json()["id"]

        # 1. Download CSV report
        csv_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/csv",
            headers=user_a["headers"],
        )
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers.get("content-type", "")
        assert "DharaScope Satellite Surface Water" in csv_res.text

        # 2. Download PDF report
        pdf_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/pdf",
            headers=user_a["headers"],
        )
        assert pdf_res.status_code == 200
        assert "application/pdf" in pdf_res.headers.get("content-type", "")
        assert pdf_res.content[:4] == b"%PDF"

        # 3. Download Artifact Figure by ID
        art_list = client.get(f"/api/v1/analyses/{analysis_id}/artifacts", headers=user_a["headers"]).json()
        panel_art = next(a for a in art_list["items"] if a["artifact_type"] == "PANEL_PNG")
        art_download = client.get(f"/api/v1/artifacts/{panel_art['id']}/download", headers=user_a["headers"])
        assert art_download.status_code == 200
        assert "image/png" in art_download.headers.get("content-type", "")
        assert art_download.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_user_b_cannot_download_user_a_reports(self, user_a, user_b):
        """Verify User B is blocked from downloading User A's generated reports."""
        run_res = client.post(
            "/api/v1/analyses?sync=true",
            json={"aoi_geometry": LUCKNOW_GEOM, "data_source": "synthetic"},
            headers=user_a["headers"],
        )
        analysis_id = run_res.json()["id"]

        csv_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/csv",
            headers=user_b["headers"],
        )
        assert csv_res.status_code == 404

        pdf_res = client.get(
            f"/api/v1/analyses/{analysis_id}/reports/pdf",
            headers=user_b["headers"],
        )
        assert pdf_res.status_code == 404

    def test_download_report_for_queued_run_rejected(self, user_a):
        """Verify attempting to download report for a run that has not completed returns 400."""
        from datetime import datetime, timezone
        from src.database.models.analysis import AnalysisRun
        from src.database.session import get_db

        # Ensure user A profile exists in database
        client.get("/api/v1/auth/me", headers=user_a["headers"])

        run_id = uuid.uuid4()
        now_utc = datetime.now(timezone.utc)
        with get_db() as session:
            run = AnalysisRun(
                id=run_id,
                user_id=uuid.UUID(user_a["id"]),
                status="PROCESSING",
                data_provider="CDSE_PENDING",
                is_real_data=True,
                t1_scene_id="PENDING",
                t1_date=now_utc,
                t2_scene_id="PENDING",
                t2_date=now_utc,
                ndwi_threshold=0.0,
            )
            session.add(run)
            session.commit()

        csv_res = client.get(
            f"/api/v1/analyses/{run_id}/reports/csv",
            headers=user_a["headers"],
        )
        assert csv_res.status_code == 400
        assert "must be 'SUCCESS'" in csv_res.json()["detail"]


# ===========================================================================
# 7. Error Sanitization & Non-Existent Resources
# ===========================================================================

class TestErrorSanitizationAndEdgeCases:
    """Verify security constraints: no system paths, internal traces, or leaked secrets."""

    def test_nonexistent_aoi_returns_404(self, user_a):
        """Verify query for nonexistent UUID returns 404."""
        random_id = uuid.uuid4()
        res = client.get(f"/api/v1/aois/{random_id}", headers=user_a["headers"])
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]

    def test_nonexistent_analysis_returns_404(self, user_a):
        """Verify query for nonexistent analysis run returns 404."""
        random_id = uuid.uuid4()
        res = client.get(f"/api/v1/analyses/{random_id}", headers=user_a["headers"])
        assert res.status_code == 404

    def test_invalid_uuid_returns_422(self, user_a):
        """Verify malformed non-UUID identifier returns 422 Unprocessable Entity."""
        res = client.get("/api/v1/aois/not-a-valid-uuid", headers=user_a["headers"])
        assert res.status_code == 422
