"""Tests for Admin Role Synchronization with Supabase Auth Admin API."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

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

    def test_cross_system_sync_postgres_failure_compensating_rollback_succeeds(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Verify that when Supabase succeeds but PostgreSQL flush fails, compensating rollback restores Supabase role."""
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {"id": str(target_user), "app_metadata": kwargs.get("json", {}).get("app_metadata", {})}
            return mock_res

        from sqlalchemy.orm import Session
        original_flush = Session.flush

        def failing_flush(self):
            for obj in list(self.dirty) + list(self.new):
                if isinstance(obj, Profile) and obj.id == target_user and obj.role == "admin":
                    raise SQLAlchemyError("Simulated database failure during flush")
            return original_flush(self)

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "flush", failing_flush)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        # Should return 500 indicating DB failure and compensating rollback
        assert res.status_code == 500
        assert "Compensating rollback" in res.json()["detail"]

        # Verify Supabase was called TWICE:
        # 1. Forward promotion to 'admin'
        # 2. Compensating rollback back to 'user'
        assert len(mock_supabase_calls) == 2
        assert mock_supabase_calls[0]["payload"]["app_metadata"]["role"] == "admin"
        assert mock_supabase_calls[1]["payload"]["app_metadata"]["role"] == "user"

        # Verify PostgreSQL role remains 'user'
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "user"

    def test_cross_system_sync_postgres_failure_and_compensation_failure_records_desynchronization(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Verify that if DB flush fails and compensating update ALSO fails, critical 502 and DESYNCHRONIZED are recorded."""
        call_count = 0

        def fake_put(self, url, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call (forward sync to admin) succeeds
                mock_res = MagicMock()
                mock_res.status_code = 200
                mock_res.content = b'{"status": "ok"}'
                mock_res.json.return_value = {"id": str(target_user), "app_metadata": kwargs.get("json", {}).get("app_metadata", {})}
                return mock_res
            else:
                # Second call (compensating rollback) fails
                raise RuntimeError("Network partition: Supabase Auth unreachable during compensation")

        from sqlalchemy.orm import Session
        original_flush = Session.flush

        def failing_flush(self):
            for obj in list(self.dirty) + list(self.new):
                if isinstance(obj, Profile) and obj.id == target_user and obj.role == "admin":
                    raise SQLAlchemyError("Simulated database failure during flush")
            return original_flush(self)

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "flush", failing_flush)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        # Should return 502 with desynchronization alert
        assert res.status_code == 502
        assert "desynchronization" in res.json()["detail"].lower()

    def test_idempotent_role_update_retries(self, client, admin_headers, target_user):
        """Verify retrying role update with same target role is idempotent and avoids redundant operations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "123"}'
        mock_response.json.return_value = {"id": str(target_user), "app_metadata": {"role": "admin"}}

        with patch("httpx.Client.put", return_value=mock_response) as mock_put:
            # First promotion
            res1 = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"role": "admin"},
            )
            assert res1.status_code == 200
            assert res1.json()["role"] == "admin"
            assert mock_put.call_count == 1

            # Second identical promotion retry
            res2 = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"role": "admin"},
            )
            assert res2.status_code == 200
            assert res2.json()["role"] == "admin"
            # Idempotent: Did not dispatch redundant external call
            assert mock_put.call_count == 1

    def test_role_reconciliation_endpoint(self, client, admin_headers, target_user):
        """Verify POST /api/v1/admin/users/{id}/reconcile pushes authoritative PostgreSQL role to Supabase."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"status": "ok"}'
        mock_response.json.return_value = {"id": str(target_user), "app_metadata": {"role": "user"}}

        with patch("httpx.Client.put", return_value=mock_response) as mock_put:
            res = client.post(
                f"/api/v1/admin/users/{target_user}/reconcile",
                headers=admin_headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "reconciled"
            assert data["authoritative_role"] == "user"
            mock_put.assert_called_once()

    def test_immediate_revocation_stale_jwt_rejected(self, client, admin_headers, target_user):
        """Security Proof: An unexpired JWT minted for an admin is immediately rejected once revoked in DB."""
        import jwt

        # 1. Promote target_user to admin in DB
        with get_db() as session:
            p = session.get(Profile, target_user)
            p.role = "admin"
            session.commit()

        # 2. Issue an unexpired admin JWT for target_user
        secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
        payload = {
            "sub": str(target_user),
            "email": f"target_{target_user.hex[:6]}@dharascope.org",
            "aud": "authenticated",
            "iss": "https://testproject.supabase.co/auth/v1",
            "app_metadata": {"role": "admin"},
            "exp": 9999999999,  # Unexpired
        }
        stale_admin_token = jwt.encode(payload, secret, algorithm="HS256")
        stale_admin_headers = {"Authorization": f"Bearer {stale_admin_token}"}

        # Verify user can access admin endpoint while DB says admin
        check_before = client.get("/api/v1/admin/users", headers=stale_admin_headers)
        assert check_before.status_code == 200

        # 3. Revoke target_user: Lead admin sets target_user role to 'user'
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = b'{"status": "ok"}'
        mock_res.json.return_value = {"id": str(target_user), "app_metadata": {"role": "user"}}
        with patch("httpx.Client.put", return_value=mock_res):
            revocation_res = client.patch(
                f"/api/v1/admin/users/{target_user}",
                headers=admin_headers,
                json={"role": "user"},
            )
            assert revocation_res.status_code == 200
            assert revocation_res.json()["role"] == "user"

        # 4. Target user attempts to access admin endpoint with their OLD unexpired JWT
        check_after = client.get("/api/v1/admin/users", headers=stale_admin_headers)
        # Immediate Revocation: MUST be rejected with 403 Forbidden!
        assert check_after.status_code == 403
        assert "Admin privileges revoked or not granted" in check_after.json()["detail"]

    def test_immediate_revocation_regular_access_preserved(self, client, admin_headers, target_user):
        """Verify that after admin revocation, user can still access normal user endpoints."""
        import jwt

        # Revoke user
        with get_db() as session:
            p = session.get(Profile, target_user)
            p.role = "user"
            session.commit()

        secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
        payload = {
            "sub": str(target_user),
            "email": f"target_{target_user.hex[:6]}@dharascope.org",
            "aud": "authenticated",
            "iss": "https://testproject.supabase.co/auth/v1",
            "app_metadata": {"role": "user"},
            "exp": 9999999999,
        }
        user_token = jwt.encode(payload, secret, algorithm="HS256")
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # Access regular endpoint
        res = client.get("/api/v1/auth/me", headers=user_headers)
        assert res.status_code == 200
        assert res.json()["id"] == str(target_user)
        assert res.json()["role"] == "user"

    def test_admin_endpoint_database_failure_fails_closed(self, client, admin_headers, monkeypatch):
        """Security Proof: Database failure during admin authorization fails closed (500), never allows bypass."""
        from sqlalchemy.orm import Session
        original_scalar = Session.scalar

        def failing_scalar(self, *args, **kwargs):
            raise SQLAlchemyError("Simulated database connection loss during admin check")

        monkeypatch.setattr(Session, "scalar", failing_scalar)

        res = client.get("/api/v1/admin/users", headers=admin_headers)
        assert res.status_code == 500
        assert "database error" in res.json()["detail"].lower()

    def test_cross_system_sync_postgres_commit_failure_compensating_rollback_succeeds(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Simulation Test: Supabase succeeds, flush succeeds, commit fails -> compensating rollback executed."""
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {"id": str(target_user), "app_metadata": kwargs.get("json", {}).get("app_metadata", {})}
            return mock_res

        from sqlalchemy.orm import Session
        original_commit = Session.commit
        commit_called = False

        def failing_commit(self):
            nonlocal commit_called
            if len(mock_supabase_calls) == 1 and not commit_called:
                commit_called = True
                raise SQLAlchemyError("Simulated database failure during commit (e.g. disk full / deferred constraint)")
            return original_commit(self)

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "commit", failing_commit)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 500
        assert "Compensating rollback" in res.json()["detail"]

        # Verify Supabase was called for forward update then compensating update
        assert len(mock_supabase_calls) == 2
        assert mock_supabase_calls[0]["payload"]["app_metadata"]["role"] == "admin"
        assert mock_supabase_calls[1]["payload"]["app_metadata"]["role"] == "user"

        # Verify database retained original role
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "user"

        # Verify journal recorded COMPENSATED
        from src.services.role_sync_service import get_role_sync_journal
        j = get_role_sync_journal()
        entries = j.get_user_entries(target_user)
        assert len(entries) > 0
        assert entries[-1].state == "COMPENSATED"

    def test_reconciliation_of_desynchronized_state(self, client, admin_headers, target_user):
        """Verify reconciling a desynchronized state re-applies authoritative PostgreSQL role to Supabase."""
        mock_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_calls.append(kwargs.get("json", {}))
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {"id": str(target_user), "app_metadata": {"role": "user"}}
            return mock_res

        with patch("httpx.Client.put", fake_put):
            res = client.post(
                f"/api/v1/admin/users/{target_user}/reconcile",
                headers=admin_headers,
            )
            assert res.status_code == 200
            assert res.json()["status"] == "reconciled"
            assert res.json()["authoritative_role"] == "user"
            assert len(mock_calls) == 1
            assert mock_calls[0]["app_metadata"]["role"] == "user"

    def test_reconciliation_failure_when_supabase_unreachable(self, client, admin_headers, target_user):
        """Verify reconciliation returns 502 and does not claim success when Supabase is unreachable."""
        with patch("httpx.Client.put", side_effect=RuntimeError("Supabase API gateway timeout")):
            res = client.post(
                f"/api/v1/admin/users/{target_user}/reconcile",
                headers=admin_headers,
            )
            assert res.status_code == 502
            assert "Failed to communicate with Supabase Auth" in res.json()["detail"]

    def test_reconciliation_repeated_idempotency(self, client, admin_headers, target_user):
        """Verify calling reconciliation multiple times produces identical consistent results."""
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.content = b'{"status": "ok"}'
        mock_res.json.return_value = {"id": str(target_user), "app_metadata": {"role": "user"}}

        with patch("httpx.Client.put", return_value=mock_res):
            res1 = client.post(f"/api/v1/admin/users/{target_user}/reconcile", headers=admin_headers)
            res2 = client.post(f"/api/v1/admin/users/{target_user}/reconcile", headers=admin_headers)
            assert res1.status_code == 200
            assert res2.status_code == 200
            assert res1.json()["authoritative_role"] == res2.json()["authoritative_role"] == "user"

    def test_unauthorized_reconciliation_rejected(self, client, regular_user_headers, target_user):
        """Verify unauthenticated or regular users cannot trigger reconciliation."""
        # Unauthenticated
        res_unauth = client.post(f"/api/v1/admin/users/{target_user}/reconcile")
        assert res_unauth.status_code == 401

        # Regular user
        res_forbidden = client.post(
            f"/api/v1/admin/users/{target_user}/reconcile",
            headers=regular_user_headers,
        )
        assert res_forbidden.status_code == 403

    def test_reconciliation_never_elevates_from_user_metadata(self, client, admin_headers):
        """Security Proof: Reconciling a user with user_metadata.role='admin' sets Supabase to 'user', never admin."""
        import jwt

        rogue_uid = uuid.uuid4()
        secret = "super_secret_test_key_for_dharascope_verification_32_bytes"
        rogue_token = jwt.encode(
            {
                "sub": str(rogue_uid),
                "email": f"rogue_{rogue_uid.hex[:6]}@dharascope.org",
                "aud": "authenticated",
                "iss": "https://testproject.supabase.co/auth/v1",
                "app_metadata": {"role": "user"},
                "user_metadata": {"role": "admin", "full_name": "Rogue Attacker"},
                "exp": 9999999999,
            },
            secret,
            algorithm="HS256",
        )
        # Rogue user logs in, provisioning profile
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {rogue_token}"})

        # Ensure database profile has role='user'
        with get_db() as session:
            p = session.get(Profile, rogue_uid)
            assert p.role == "user"

        mock_payloads = []

        def fake_put(self, url, *args, **kwargs):
            mock_payloads.append(kwargs.get("json", {}))
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {"id": str(rogue_uid), "app_metadata": {"role": "user"}}
            return mock_res

        with patch("httpx.Client.put", fake_put):
            res = client.post(
                f"/api/v1/admin/users/{rogue_uid}/reconcile",
                headers=admin_headers,
            )
            assert res.status_code == 200
            assert res.json()["authoritative_role"] == "user"
            assert mock_payloads[0]["app_metadata"]["role"] == "user"
            assert mock_payloads[0]["app_metadata"]["role"] != "admin"

    def test_ambiguous_commit_outcome_commit_succeeded_reconciles_supabase(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Ambiguous Commit Scenario: PostgreSQL commit actually succeeded, but client
        received an exception (e.g. connection reset right as ACK was sent).
        Verify system queries fresh session, discovers new_role in DB, reconciles
        Supabase to new_role, does NOT blindly compensate to old_role, sets journal
        to RECONCILED, and returns HTTP 200 with the new role.
        """
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {
                "id": str(target_user),
                "app_metadata": kwargs.get("json", {}).get("app_metadata", {}),
            }
            return mock_res

        from sqlalchemy.orm import Session
        original_commit = Session.commit
        lost_ack_triggered = False

        def commit_with_lost_ack(self):
            nonlocal lost_ack_triggered
            # Execute the real commit first (data is persisted to DB!)
            original_commit(self)
            # If this is the update commit during our PATCH call, simulate lost connection ACK
            if len(mock_supabase_calls) == 1 and not lost_ack_triggered:
                lost_ack_triggered = True
                raise SQLAlchemyError("Connection reset by peer after COMMIT")

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "commit", commit_with_lost_ack)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 200
        assert res.json()["role"] == "admin"

        # Verify Supabase was called for forward update (admin) and reconciliation (admin)
        # It must NEVER have been called with "user" (no blind compensation!)
        assert len(mock_supabase_calls) == 2
        assert mock_supabase_calls[0]["payload"]["app_metadata"]["role"] == "admin"
        assert mock_supabase_calls[1]["payload"]["app_metadata"]["role"] == "admin"

        # Verify database has "admin"
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "admin"

        # Verify journal recorded RECONCILED
        from src.services.role_sync_service import get_role_sync_journal
        j = get_role_sync_journal()
        entries = j.get_user_entries(target_user)
        assert len(entries) > 0
        assert entries[-1].state == "RECONCILED"

    def test_ambiguous_commit_outcome_commit_definitely_fails_compensates_supabase(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Ambiguous Commit Scenario: PostgreSQL commit definitely fails (e.g. disk full / constraint error).
        Verify fresh session discovers old_role in DB, restores Supabase to old_role,
        confirms both systems have old_role, sets journal to COMPENSATED, and returns HTTP 500.
        """
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {
                "id": str(target_user),
                "app_metadata": kwargs.get("json", {}).get("app_metadata", {}),
            }
            return mock_res

        from sqlalchemy.orm import Session
        original_commit = Session.commit
        failure_triggered = False

        def failing_commit(self):
            nonlocal failure_triggered
            # Fail BEFORE commit executes
            if len(mock_supabase_calls) == 1 and not failure_triggered:
                failure_triggered = True
                raise SQLAlchemyError("Simulated database failure during commit (e.g. disk full)")
            return original_commit(self)

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "commit", failing_commit)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 500
        assert "Compensating rollback" in res.json()["detail"]

        # Verify Supabase was called for forward update (admin) then compensating rollback (user)
        assert len(mock_supabase_calls) == 2
        assert mock_supabase_calls[0]["payload"]["app_metadata"]["role"] == "admin"
        assert mock_supabase_calls[1]["payload"]["app_metadata"]["role"] == "user"

        # Verify database retained "user"
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "user"

        # Verify journal recorded COMPENSATED
        from src.services.role_sync_service import get_role_sync_journal
        j = get_role_sync_journal()
        entries = j.get_user_entries(target_user)
        assert len(entries) > 0
        assert entries[-1].state == "COMPENSATED"

    def test_ambiguous_commit_outcome_database_unavailable_during_verification(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Ambiguous Commit Scenario: PostgreSQL commit fails, and database is unavailable
        during authoritative outcome verification.
        Verify system records DESYNCHRONIZED, does NOT claim compensation succeeded (does NOT call Supabase to revert),
        and returns HTTP 502 Bad Gateway.
        """
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.content = b'{"status": "ok"}'
            mock_res.json.return_value = {
                "id": str(target_user),
                "app_metadata": kwargs.get("json", {}).get("app_metadata", {}),
            }
            return mock_res

        from sqlalchemy.orm import Session
        original_commit = Session.commit
        original_scalar = Session.scalar

        def failing_commit(self):
            if len(mock_supabase_calls) == 1:
                raise SQLAlchemyError("Connection reset during commit")
            return original_commit(self)

        def failing_scalar(self, *args, **kwargs):
            # If commit already failed and we are verifying in fresh session:
            if len(mock_supabase_calls) == 1:
                raise SQLAlchemyError("Database server unreachable during outcome verification")
            return original_scalar(self, *args, **kwargs)

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "commit", failing_commit)
        monkeypatch.setattr(Session, "scalar", failing_scalar)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 502
        assert "database is unavailable for verification" in res.json()["detail"].lower()

        # Critical: Only the initial forward call occurred!
        # System did NOT blindly call Supabase to compensate!
        assert len(mock_supabase_calls) == 1
        assert mock_supabase_calls[0]["payload"]["app_metadata"]["role"] == "admin"

        # Verify journal recorded DESYNCHRONIZED
        from src.services.role_sync_service import get_role_sync_journal
        j = get_role_sync_journal()
        entries = j.get_user_entries(target_user)
        assert len(entries) > 0
        assert entries[-1].state == "DESYNCHRONIZED"

    def test_ambiguous_commit_outcome_supabase_unavailable_during_reconciliation(
        self, client, admin_headers, target_user, monkeypatch
    ):
        """Ambiguous Commit Scenario: PostgreSQL committed new_role, but Supabase is unavailable
        during the subsequent reconciliation step.
        Verify system records DESYNCHRONIZED and returns HTTP 502 Bad Gateway.
        """
        mock_supabase_calls = []

        def fake_put(self, url, *args, **kwargs):
            mock_supabase_calls.append({"url": url, "payload": kwargs.get("json", {})})
            if len(mock_supabase_calls) == 1:
                # Forward update succeeds
                mock_res = MagicMock()
                mock_res.status_code = 200
                mock_res.content = b'{"status": "ok"}'
                mock_res.json.return_value = {
                    "id": str(target_user),
                    "app_metadata": {"role": "admin"},
                }
                return mock_res
            else:
                # Reconciliation call to Supabase fails!
                raise RuntimeError("Supabase gateway unreachable during reconciliation")

        from sqlalchemy.orm import Session
        original_commit = Session.commit
        lost_ack = False

        def commit_with_lost_ack(self):
            nonlocal lost_ack
            original_commit(self)
            if len(mock_supabase_calls) == 1 and not lost_ack:
                lost_ack = True
                raise SQLAlchemyError("Connection reset after COMMIT")

        monkeypatch.setattr("httpx.Client.put", fake_put)
        monkeypatch.setattr(Session, "commit", commit_with_lost_ack)

        res = client.patch(
            f"/api/v1/admin/users/{target_user}",
            headers=admin_headers,
            json={"role": "admin"},
        )
        assert res.status_code == 502
        assert "identity provider reconciliation failed" in res.json()["detail"].lower()

        # Two calls were attempted: forward update and reconciliation
        assert len(mock_supabase_calls) == 2

        # Verify database actually contains "admin"
        with get_db() as session:
            profile = session.get(Profile, target_user)
            assert profile.role == "admin"

        # Verify journal recorded DESYNCHRONIZED
        from src.services.role_sync_service import get_role_sync_journal
        j = get_role_sync_journal()
        entries = j.get_user_entries(target_user)
        assert len(entries) > 0
        assert entries[-1].state == "DESYNCHRONIZED"



