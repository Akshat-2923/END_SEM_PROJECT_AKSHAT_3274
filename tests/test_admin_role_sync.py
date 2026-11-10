"""Tests for Admin Role Synchronization with Supabase Auth Admin API."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.auth import (
    AuthenticatedUser,
    get_supabase_service_role_key,
    sync_user_role_to_supabase,
)
from src.database.models.profile import Profile
from src.database.session import get_db


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_headers():
    import jwt

    secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "email": f"lead_admin_{user_id.hex[:6]}@dharascope.org",
        "aud": "authenticated",
        "iss": "https://testproject.supabase.co/auth/v1",
        "app_metadata": {"role": "admin"},
        "exp": 9999999999,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_user_headers():
    import jwt

    secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "email": f"regular_{user_id.hex[:6]}@dharascope.org",
        "aud": "authenticated",
        "iss": "https://testproject.supabase.co/auth/v1",
        "app_metadata": {"role": "user"},
        "exp": 9999999999,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def target_user(client):
    """Create a target user profile in PostgreSQL database."""
    target_id = uuid.uuid4()
    with get_db() as session:
        profile = Profile(
            id=target_id,
            email=f"target_{target_id.hex[:6]}@dharascope.org",
            role="user",
            quota_monthly_runs=50,
        )
        session.add(profile)
        session.commit()
    return target_id


class TestAdminRoleSynchronization:
    """Test suite for admin role synchronization between PostgreSQL and Supabase Auth."""

    def test_sync_user_role_to_supabase_promotion_success(self, target_user):
        """Verify promoting a user to admin calls Supabase PUT endpoint with app_metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "123"}'
        mock_response.json.return_value = {
            "id": str(target_user),
            "app_metadata": {"role": "admin"},
        }

        with patch("httpx.Client.put", return_value=mock_response) as mock_put:
            res = sync_user_role_to_supabase(
                user_id=target_user,
                new_role="admin",
                service_role_key="test_service_key",
                supabase_url="https://testproject.supabase.co",
            )
            assert res["app_metadata"]["role"] == "admin"
            mock_put.assert_called_once()
            called_url = mock_put.call_args[0][0]
            assert str(target_user) in called_url
            called_json = mock_put.call_args[1]["json"]
            assert called_json == {"app_metadata": {"role": "admin"}}
            headers = mock_put.call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_service_key"

    def test_sync_user_role_to_supabase_revocation_success(self, target_user):
        """Verify revoking admin access sets role='user' in Supabase."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "123"}'
        mock_response.json.return_value = {
            "id": str(target_user),
            "app_metadata": {"role": "user"},
        }

        with patch("httpx.Client.put", return_value=mock_response) as mock_put:
            res = sync_user_role_to_supabase(
                user_id=target_user,
                new_role="user",
                service_role_key="test_service_key",
                supabase_url="https://testproject.supabase.co",
            )
            assert res["app_metadata"]["role"] == "user"
            called_json = mock_put.call_args[1]["json"]
            assert called_json == {"app_metadata": {"role": "user"}}

    def test_sync_user_role_invalid_role_rejected(self, target_user):
        """Verify invalid roles are rejected immediately."""
        with pytest.raises(HTTPException) as exc_info:
            sync_user_role_to_supabase(user_id=target_user, new_role="superuser")
        assert exc_info.value.status_code == 400

    def test_sync_user_role_user_not_found_in_supabase(self, target_user):
        """Verify 404 from Supabase translates to HTTP 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "User not found"

        with patch("httpx.Client.put", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                sync_user_role_to_supabase(
                    user_id=target_user,
                    new_role="admin",
                    service_role_key="test_key",
                    supabase_url="https://testproject.supabase.co",
                )
            assert exc_info.value.status_code == 404

    def test_sync_user_role_supabase_failure_rolls_back_postgres(self, client, admin_headers, target_user):
        """Verify that when Supabase Admin API fails (502/network), PostgreSQL role is NOT updated."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error in GoTrue"

        with patch("httpx.Client.put", return_value=mock_response):
            res = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"role": "admin"},
            )
            # Should fail with 502 Bad Gateway
            assert res.status_code == 502

        # Verify PostgreSQL database role remained 'user'
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "user"

    def test_admin_endpoint_promotion_updates_both_systems(self, client, admin_headers, target_user):
        """Verify PATCH /api/v1/admin/users/{id} updates Supabase and PostgreSQL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "123"}'
        mock_response.json.return_value = {
            "id": str(target_user),
            "app_metadata": {"role": "admin"},
        }

        with patch("httpx.Client.put", return_value=mock_response) as mock_put:
            res = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"role": "admin", "quota_monthly_runs": 100},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["role"] == "admin"
            assert data["quota_monthly_runs"] == 100
            mock_put.assert_called_once()

        # Verify PostgreSQL database updated
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "admin"
            assert profile.quota_monthly_runs == 100

    def test_admin_endpoint_quota_only_update_skips_idp_sync(self, client, admin_headers, target_user):
        """Verify updating quota or name only does NOT trigger Supabase IdP sync."""
        with patch("httpx.Client.put") as mock_put:
            res = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"quota_monthly_runs": 150, "full_name": "Updated Name"},
            )
            assert res.status_code == 200
            assert res.json()["quota_monthly_runs"] == 150
            assert res.json()["full_name"] == "Updated Name"
            mock_put.assert_not_called()

    def test_regular_user_forbidden_from_admin_update(self, client, regular_user_headers, target_user):
        """Verify non-admin users cannot call admin role-update endpoint."""
        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=regular_user_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 403

    def test_unauthenticated_request_rejected(self, client, target_user):
        """Verify unauthenticated request is rejected with 401."""
        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            json={"role": "admin"},
        )
        assert res.status_code == 401

    def test_production_missing_service_role_key_fails_closed(self, monkeypatch):
        """Verify that in production, missing service-role key raises HTTP 500 fail-closed."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            get_supabase_service_role_key()
        assert exc_info.value.status_code == 500
        assert "SUPABASE_SERVICE_ROLE_KEY" in exc_info.value.detail
