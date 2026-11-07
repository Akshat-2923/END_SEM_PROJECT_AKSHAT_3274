"""Authentication, authorization, and database security layer for Supabase & FastAPI."""

import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.database.models.profile import Profile
from src.database.session import get_db

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

        # Role extraction hierarchy:
        # 1. app_metadata.role (Supabase canonical custom role claim)
        # 2. user_metadata.role
        # 3. top-level role claim (if explicitly set to 'admin')
        app_metadata = claims.get("app_metadata", {})
        user_metadata = claims.get("user_metadata", {})

        claimed_role = (
            app_metadata.get("role")
            or user_metadata.get("role")
            or (claims.get("role") if claims.get("role") == "admin" else None)
            or "user"
        )
        normalized_role = "admin" if claimed_role == "admin" else "user"

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
    if not secret:
        # Default fallback for testing or development only
        return "dharascope_test_jwt_secret_key_minimum_32_bytes_long"
    return secret


def get_jwt_audience() -> Optional[str]:
    """Retrieve expected JWT audience."""
    return os.getenv("SUPABASE_AUDIENCE", "authenticated")


def get_jwt_issuer() -> Optional[str]:
    """Retrieve expected JWT issuer, if configured."""
    return os.getenv("SUPABASE_ISSUER") or (
        f"{os.getenv('SUPABASE_URL')}/auth/v1" if os.getenv("SUPABASE_URL") else None
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


def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """FastAPI dependency: Enforces that the current authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required",
        )
    return current_user


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
