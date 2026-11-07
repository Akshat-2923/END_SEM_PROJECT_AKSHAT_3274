"""Automated tests for Supabase JWT verification, FastAPI auth dependencies, and profile management."""

import time
import uuid
from typing import Any, Dict, Optional

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.auth import (
    AuthenticatedUser,
    get_current_user,
    get_or_create_profile,
    require_admin,
    update_user_profile,
    verify_supabase_jwt,
)
from src.database.base import Base
from src.database.models.profile import Profile
from src.database.session import get_db

TEST_SECRET = "super_secret_test_key_for_dharascope_verification_32_bytes"
TEST_ISSUER = "https://testproject.supabase.co/auth/v1"
TEST_AUDIENCE = "authenticated"


def create_test_jwt(
    sub: Optional[str] = None,
    email: str = "hydrologist@dharascope.org",
    role: str = "authenticated",
    app_metadata: Optional[Dict[str, Any]] = None,
    exp_delta: int = 3600,
    secret: str = TEST_SECRET,
    algorithm: str = "HS256",
    issuer: str = TEST_ISSUER,
    audience: str = TEST_AUDIENCE,
) -> str:
    """Helper to generate signed mock Supabase JWT tokens."""
    user_id = sub or str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "app_metadata": app_metadata or {"role": "user", "provider": "email"},
        "user_metadata": {"full_name": "Test Hydrologist"},
        "iss": issuer,
        "aud": audience,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_delta,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


class TestSupabaseJWTVerification:
    """Tests checking cryptographic JWT validation rules and error modes."""

    def test_valid_user_jwt(self):
        """Verify successful decode of valid user token."""
        user_uuid = uuid.uuid4()
        token = create_test_jwt(sub=str(user_uuid), email="user@dharascope.org")
        user = verify_supabase_jwt(
            token,
            secret=TEST_SECRET,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        assert user.id == user_uuid
        assert user.email == "user@dharascope.org"
        assert user.role == "user"
        assert user.is_admin is False

    def test_valid_admin_jwt(self):
        """Verify successful extraction of admin role from app_metadata."""
        admin_uuid = uuid.uuid4()
        token = create_test_jwt(
            sub=str(admin_uuid),
            email="admin@dharascope.org",
            app_metadata={"role": "admin", "provider": "email"},
        )
        user = verify_supabase_jwt(
            token,
            secret=TEST_SECRET,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        assert user.id == admin_uuid
        assert user.role == "admin"
        assert user.is_admin is True

    def test_missing_or_empty_jwt(self):
        """Verify missing token raises 401 Unauthorized."""
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt("", secret=TEST_SECRET)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "missing or empty" in exc_info.value.detail

    def test_invalid_signature_rejected(self):
        """Verify token signed with wrong secret is rejected."""
        token = create_test_jwt(secret="wrong_secret_key_that_does_not_match")
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(
                token,
                secret=TEST_SECRET,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token signature" in exc_info.value.detail

    def test_expired_token_rejected(self):
        """Verify expired token raises 401 with token expired message."""
        expired_token = create_test_jwt(exp_delta=-60)  # expired 60 seconds ago
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(
                expired_token,
                secret=TEST_SECRET,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_issuer_rejected(self):
        """Verify token with forged issuer is rejected."""
        forged_issuer_token = create_test_jwt(issuer="https://rogue-auth.malicious.io/auth/v1")
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(
                forged_issuer_token,
                secret=TEST_SECRET,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token issuer" in exc_info.value.detail

    def test_invalid_audience_rejected(self):
        """Verify token with invalid audience is rejected."""
        wrong_aud_token = create_test_jwt(audience="wrong_audience_service")
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(
                wrong_aud_token,
                secret=TEST_SECRET,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token audience" in exc_info.value.detail

    def test_invalid_uuid_subject_rejected(self):
        """Verify token with non-UUID subject claim is rejected."""
        invalid_sub_token = create_test_jwt(sub="not-a-valid-uuid-string")
        with pytest.raises(HTTPException) as exc_info:
            verify_supabase_jwt(
                invalid_sub_token,
                secret=TEST_SECRET,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "valid UUID" in exc_info.value.detail


class TestFastAPIAuthorizationDependencies:
    """Tests checking FastAPI dependency behavior."""

    def test_get_current_user_missing_credentials(self):
        """Test get_current_user with None credentials raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing Bearer token" in exc_info.value.detail

    def test_require_admin_success(self):
        """Test require_admin passes for admin user."""
        admin_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email="admin@dharascope.org",
            role="admin",
            is_admin=True,
            claims={},
        )
        assert require_admin(admin_user) == admin_user

    def test_require_admin_forbidden_for_regular_user(self):
        """Test require_admin raises 403 Forbidden for non-admin user."""
        regular_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email="regular@dharascope.org",
            role="user",
            is_admin=False,
            claims={},
        )
        with pytest.raises(HTTPException) as exc_info:
            require_admin(regular_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin privileges required" in exc_info.value.detail


class TestProfileManagementAndPrivilegeEscalation:
    """Tests verifying profile synchronization and anti-privilege escalation logic."""

    @pytest.fixture(autouse=True)
    def setup_isolated_db(self):
        """Use isolated test database session for profile testing."""
        from src.database.config import get_database_url
        from src.database.session import get_engine, get_session_factory
        url = get_database_url(is_test=True)
        engine = get_engine(url)
        factory = get_session_factory(engine)
        self.session = factory()
        yield
        self.session.rollback()
        self.session.close()

    def test_get_or_create_profile(self):
        """Verify profile is auto-created if it does not exist."""
        test_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"autocreate_{uuid.uuid4().hex[:6]}@example.com",
            role="user",
            is_admin=False,
            claims={},
        )
        profile = get_or_create_profile(self.session, test_user)
        assert profile.id == test_user.id
        assert profile.email == test_user.email
        assert profile.role == "user"
        assert profile.quota_monthly_runs == 50

    def test_regular_user_cannot_escalate_role(self):
        """Verify normal user cannot promote themselves to admin via profile update."""
        test_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"escalate_{uuid.uuid4().hex[:6]}@example.com",
            role="user",
            is_admin=False,
            claims={},
        )
        get_or_create_profile(self.session, test_user)

        # Attempt to escalate role to 'admin'
        with pytest.raises(HTTPException) as exc_info:
            update_user_profile(self.session, test_user, role="admin")
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Only administrators" in exc_info.value.detail

    def test_regular_user_cannot_alter_quota(self):
        """Verify normal user cannot increase analysis quota."""
        test_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"quota_{uuid.uuid4().hex[:6]}@example.com",
            role="user",
            is_admin=False,
            claims={},
        )
        get_or_create_profile(self.session, test_user)

        with pytest.raises(HTTPException) as exc_info:
            update_user_profile(self.session, test_user, quota_monthly_runs=5000)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_update_role_and_quota(self):
        """Verify genuine admin can update role and quotas."""
        admin_user = AuthenticatedUser(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
            role="admin",
            is_admin=True,
            claims={},
        )
        profile = update_user_profile(
            self.session,
            admin_user,
            role="admin",
            quota_monthly_runs=200,
            full_name="Lead Administrator",
        )
        assert profile.role == "admin"
        assert profile.quota_monthly_runs == 200
        assert profile.full_name == "Lead Administrator"
