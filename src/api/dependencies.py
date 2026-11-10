"""FastAPI dependencies for authentication, authorization, and database sessions."""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth import (
    AuthenticatedUser,
    get_authenticated_db,
    get_current_user,
    get_or_create_profile,
    require_admin,
)
from src.database.session import get_db


def get_db_session(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Generator[Session, None, None]:
    """Dependency yielding a database session bound to the user's RLS security context.

    Automatically auto-provisions or retrieves the user's profile in the profiles table.
    """
    with get_authenticated_db(current_user) as session:
        get_or_create_profile(session, current_user)
        yield session


def get_admin_db_session(
    admin_user: AuthenticatedUser = Depends(require_admin),
) -> Generator[Session, None, None]:
    """Dependency yielding a database session bound to an authenticated administrator."""
    with get_authenticated_db(admin_user) as session:
        get_or_create_profile(session, admin_user)
        yield session


def get_anonymous_db_session() -> Generator[Session, None, None]:
    """Dependency yielding an anonymous database session for public health checks."""
    with get_db() as session:
        yield session
