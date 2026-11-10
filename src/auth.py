"""Authentication, authorization, and database security layer for Supabase & FastAPI."""

import os
import uuid
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.database.models.profile import Profile
from src.database.session import get_db

logger = logging.getLogger("dhara_scope.auth")

# Security scheme for FastAPI documentation and Bearer token extraction
security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents a cryptographically validated user identity from Supabase Auth."""

    id: uuid.UUID
    email: str
    role: str
    is_admin: bool
    claims: Dict[str, Any]

    @classmethod
    def from_claims(cls, claims: Dict[str, Any]) -> "AuthenticatedUser":
        """Build AuthenticatedUser instance from verified JWT claims.

        Args:
            claims: Verified JWT payload dictionary.

        Returns:
            AuthenticatedUser instance.

        Raises:
            ValueError: If user id is missing or not a valid UUID.
        """
        sub = claims.get("sub")
        if not sub:
            raise ValueError("Token subject ('sub') claim is missing")
        try:
            user_uuid = uuid.UUID(str(sub))
        except ValueError as err:
            raise ValueError(f"Token subject '{sub}' is not a valid UUID") from err

        email = claims.get("email", "")

        # Security Hardening (Phase 2.2B2 Audit):
        # Application authorization roles MUST be derived exclusively from trusted
        # `app_metadata.role`. The `user_metadata` claim in Supabase is completely
        # user-writable via client SDKs and MUST NEVER be used for authorization
        # or privilege assignment.
        # Furthermore, Supabase's standard top-level `role` claim defaults to
        # 'authenticated' (indicating token type/audience) and MUST NEVER be
        # interpreted as an application administrator role.
        app_metadata = claims.get("app_metadata")
        if not isinstance(app_metadata, dict):
            app_metadata = {}

        raw_role = app_metadata.get("role")
        if isinstance(raw_role, str):
            candidate_role = raw_role.strip().lower()
        else:
            candidate_role = ""

        # Only explicitly authorized application roles are recognized;
        # missing, malformed, non-string, or unknown roles strictly default to 'user'.
        normalized_role = "admin" if candidate_role == "admin" else "user"

        return cls(
            id=user_uuid,
            email=email,
            role=normalized_role,
            is_admin=(normalized_role == "admin"),
            claims=claims,
        )


def get_jwt_secret() -> str:
    """Retrieve Supabase JWT secret from environment variables."""
    secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET")
    env = (os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "").lower()
    if not secret:
        if env in ("production", "prod"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security misconfiguration: SUPABASE_JWT_SECRET must be configured in production",
            )
        # Default fallback for testing or development only
        return "dharascope_test_jwt_secret_key_minimum_32_bytes_long"
    return secret


def get_jwt_audience() -> Optional[str]:
    """Retrieve expected JWT audience."""
    return os.getenv("SUPABASE_AUDIENCE", "authenticated")


def get_jwt_issuer() -> Optional[str]:
    """Retrieve expected JWT issuer, if configured."""
    issuer = os.getenv("SUPABASE_ISSUER") or (
        f"{os.getenv('SUPABASE_URL')}/auth/v1" if os.getenv("SUPABASE_URL") else None
    )
    env = (os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "").lower()
    if not issuer and env in ("production", "prod"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security misconfiguration: SUPABASE_ISSUER or SUPABASE_URL must be configured in production",
        )
    return issuer


def get_supabase_service_role_key() -> str:
    """Retrieve Supabase service-role key from environment.

    Must NEVER be returned in API responses, logs, or client configurations.
    """
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    env = (os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "").lower()
    if not key and env in ("production", "prod"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security misconfiguration: SUPABASE_SERVICE_ROLE_KEY must be configured in production",
        )
    return key


def sync_user_role_to_supabase(
    user_id: uuid.UUID,
    new_role: str,
    timeout: float = 10.0,
    service_role_key: Optional[str] = None,
    supabase_url: Optional[str] = None,
) -> dict:
    """Synchronize user authorization role to authoritative Supabase Auth GoTrue Admin API.

    Updates trusted 'app_metadata.role' via PUT /auth/v1/admin/users/{user_id}.
    The service role key is kept strictly on the backend.

    Raises:
        HTTPException(400): If new_role is invalid.
        HTTPException(404): If user does not exist in Supabase Auth.
        HTTPException(500): If missing service role key in production.
        HTTPException(502): If Supabase Admin API communication or synchronization fails.
    """
    if new_role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid application role '{new_role}'. Allowed roles: 'admin', 'user'.",
        )

    key = service_role_key if service_role_key is not None else get_supabase_service_role_key()
    url_base = (supabase_url or os.getenv("SUPABASE_URL", "")).strip().rstrip("/")

    # If in development/test and neither key nor URL is configured, support safe mock bypass
    if not key or not url_base:
        env = (os.getenv("ENVIRONMENT") or os.getenv("DHARASCOPE_ENV") or "").lower()
        if env in ("production", "prod"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security misconfiguration: Supabase Admin API credentials missing in production",
            )
        logger.warning(
            "Supabase Admin API credentials not configured; skipping remote IdP sync for user %s in dev/test",
            user_id,
        )
        return {"id": str(user_id), "app_metadata": {"role": new_role}}

    admin_url = f"{url_base}/auth/v1/admin/users/{user_id}"
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": "application/json",
    }
    payload = {"app_metadata": {"role": new_role}}

    try:
        with httpx.Client(timeout=timeout) as client:
            res = client.put(admin_url, headers=headers, json=payload)
    except Exception as exc:
        logger.error("Supabase Admin API network failure updating user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Supabase Auth Admin API: {str(exc)}",
        ) from exc

    if res.status_code in (200, 204):
        logger.info("Successfully updated Supabase app_metadata.role to '%s' for user %s", new_role, user_id)
        return res.json() if res.content else {"id": str(user_id), "app_metadata": {"role": new_role}}

    if res.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found in Supabase Auth",
        )

    if res.status_code in (401, 403):
        logger.error("Supabase Admin API authorization failed with status %d", res.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase Admin API credentials rejected by identity provider",
        )

    logger.error("Supabase Admin API failed with status %d: %s", res.status_code, res.text[:200])
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Supabase Auth synchronization failed with status code {res.status_code}",
    )


def verify_supabase_jwt(
    token: str,
    secret: Optional[str] = None,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
    jwks_url: Optional[str] = None,
) -> AuthenticatedUser:
    """Cryptographically verify and decode a Supabase JWT Bearer token.

    Supports HMAC (HS256) symmetric signatures as well as RSA/ECDSA (RS256/ES256)
    via Supabase JWKS public keys. Never trusts unverified payloads.

    Args:
        token: Raw JWT string.
        secret: Optional explicit secret for HMAC tokens (defaults to env).
        audience: Optional expected audience (defaults to 'authenticated').
        issuer: Optional expected issuer URL.
        jwks_url: Optional JWKS URL for asymmetric keys.

    Returns:
        AuthenticatedUser with verified identity and role.

    Raises:
        HTTPException: 401 Unauthorized on invalid, expired, or tampered tokens.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Inspect unverified header to determine signing algorithm
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed JWT header: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    alg = unverified_header.get("alg", "HS256")
    expected_aud = audience if audience is not None else get_jwt_audience()
    expected_iss = issuer if issuer is not None else get_jwt_issuer()

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": bool(expected_aud),
        "verify_iss": bool(expected_iss),
    }

    try:
        if alg in ("RS256", "ES256"):
            # Asymmetric key verification via Supabase JWKS
            resolved_jwks = jwks_url or os.getenv("SUPABASE_JWKS_URL")
            if not resolved_jwks and os.getenv("SUPABASE_URL"):
                resolved_jwks = f"{os.getenv('SUPABASE_URL')}/auth/v1/.well-known/jwks.json"

            if not resolved_jwks:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="JWKS URL not configured for asymmetric token verification",
                )

            jwks_client = jwt.PyJWKClient(resolved_jwks, cache_keys=True)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience=expected_aud,
                issuer=expected_iss,
                options=options,
            )
        else:
            # Symmetric HMAC verification
            signing_secret = secret or get_jwt_secret()
            payload = jwt.decode(
                token,
                signing_secret,
                algorithms=["HS256"],
                audience=expected_aud,
                issuer=expected_iss,
                options=options,
            )

        return AuthenticatedUser.from_claims(payload)

    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""},
        ) from err
    except jwt.InvalidIssuerError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Invalid issuer\""},
        ) from err
    except jwt.InvalidAudienceError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Invalid audience\""},
        ) from err
    except jwt.InvalidSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Invalid signature\""},
        ) from err
    except (jwt.PyJWTError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(err)}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from err


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """FastAPI dependency: Extracts and verifies JWT from the HTTP Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_supabase_jwt(credentials.credentials)


# ---------------------------------------------------------------------------
# Database Session Context & Row-Level Security (RLS) Propagation
# ---------------------------------------------------------------------------

def apply_rls_context(session: Session, user: AuthenticatedUser, app_role: str = "dharascope_app") -> None:
    """Propagate verified user identity into PostgreSQL session context for RLS evaluation.

    Executes transaction-local parameter bindings:
    1. Switches to non-superuser role so RLS is evaluated unconditionally.
    2. Sets 'request.jwt.claim.sub' to the user's UUID.
    3. Sets 'request.jwt.claim.role' to the user's role.
    """
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        # Switch to non-superuser application role so table owners/superusers do not bypass RLS
        session.execute(text(f"SET LOCAL ROLE {app_role};"))
        session.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true);"),
            {"sub": str(user.id)},
        )
        session.execute(
            text("SELECT set_config('request.jwt.claim.role', :role, true);"),
            {"role": user.role},
        )


@contextmanager
def get_authenticated_db(
    user: AuthenticatedUser,
    db_session: Optional[Session] = None,
    url: Optional[str] = None,
    app_role: str = "dharascope_app",
) -> Generator[Session, None, None]:
    """Context manager yielding a database session bound to the user's RLS security context.

    If db_session is provided, sets transaction-local RLS claims within the existing session.
    Otherwise, borrows a session from get_db() with automatic commit/rollback.
    """
    if db_session is not None:
        apply_rls_context(db_session, user, app_role)
        yield db_session
    else:
        with get_db(url) as session:
            apply_rls_context(session, user, app_role)
            yield session


# ---------------------------------------------------------------------------
# Profile Synchronization & Anti-Privilege Escalation
# ---------------------------------------------------------------------------

def get_or_create_profile(session: Session, user: AuthenticatedUser) -> Profile:
    """Retrieve or automatically synchronize user profile in the database.

    Guards against unauthorized role escalation: non-admin users cannot promote
    themselves or alter quotas.
    """
    profile = session.scalar(select(Profile).where(Profile.id == user.id))
    if profile is None:
        profile = Profile(
            id=user.id,
            email=user.email,
            role=user.role,
            quota_monthly_runs=50,
        )
        session.add(profile)
        session.flush()
    return profile


def update_user_profile(
    session: Session,
    user: AuthenticatedUser,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    quota_monthly_runs: Optional[int] = None,
) -> Profile:
    """Safely update user profile attributes with anti-privilege escalation checks.

    Normal users may update their full_name, but CANNOT modify role or quota.
    Attempts by non-admins to alter role or quota raise HTTP 403 Forbidden.
    """
    profile = get_or_create_profile(session, user)

    if (role is not None and role != profile.role) or (
        quota_monthly_runs is not None and quota_monthly_runs != profile.quota_monthly_runs
    ):
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Only administrators can modify roles or analysis quotas",
            )
        if role is not None:
            profile.role = role
        if quota_monthly_runs is not None:
            profile.quota_monthly_runs = quota_monthly_runs

    if full_name is not None:
        profile.full_name = full_name

    session.flush()
    return profile


def verify_admin_privileges(
    user: AuthenticatedUser,
    session: Optional[Session] = None,
) -> AuthenticatedUser:
    """Verifies that user has admin claim and active admin role in profiles table.

    1. Cryptographic/Claim Check: Confirms the JWT contains trusted app_metadata.role == 'admin'.
       Any non-admin role or missing claim is rejected immediately with 403 Forbidden.
    2. Authoritative Database Check: Queries the user's UUID in the profiles table using
       the restricted RLS-aware database session.
       - A revoked admin with an unexpired JWT is immediately rejected with 403 Forbidden.
       - Database connection or query errors fail closed with 500 Internal Server Error.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required",
        )

    def _verify_profile_role(s: Session) -> None:
        try:
            profile = s.scalar(select(Profile).where(Profile.id == user.id))
            if profile is None:
                profile = get_or_create_profile(s, user)
        except Exception as exc:
            logger.error(
                "Authoritative admin role verification failed due to database query error: %s",
                exc,
            )
            # Database failures must fail closed for admin endpoints
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization verification failed due to database error",
            ) from exc

        if profile.role != "admin":
            logger.warning(
                "Revoked or unauthorized admin access attempt: User %s presented admin credentials but database role is '%s'",
                user.id,
                profile.role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Admin privileges revoked or not granted",
            )

    if session is not None:
        _verify_profile_role(session)
    else:
        try:
            with get_authenticated_db(user) as auth_session:
                _verify_profile_role(auth_session)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Database connection failure in verify_admin_privileges: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization verification failed due to database connection error",
            ) from exc

    return user


def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """FastAPI dependency: Enforces that the current authenticated user has admin privileges.

    Performs authoritative database role check using restricted RLS-aware session.
    """
    return verify_admin_privileges(current_user)


def __getattr__(name: str):
    """Lazy export of role synchronization utilities to prevent circular imports."""
    if name in (
        "execute_reliable_role_update",
        "reconcile_user_role",
        "RoleSyncJournal",
        "RoleSyncJournalEntry",
        "SyncState",
        "get_role_sync_journal",
    ):
        from src.services import role_sync_service
        return getattr(role_sync_service, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
