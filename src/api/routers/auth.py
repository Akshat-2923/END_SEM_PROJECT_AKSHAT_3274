"""Authentication, user profile, and administrative access control router."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import get_admin_db_session, get_db_session
from src.api.schemas.auth import (
    AdminUserUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from src.auth import (
    AuthenticatedUser,
    execute_reliable_role_update,
    get_current_user,
    get_or_create_profile,
    reconcile_user_role,
    sync_user_role_to_supabase,
    update_user_profile,
)
from src.database.models.profile import Profile

router = APIRouter(prefix="/api/v1", tags=["Authentication & User Profiles"])


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve verified user account metadata and analysis quotas from the database.",
)
def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> Profile:
    """Return the profile of the currently authenticated user."""
    return get_or_create_profile(session, current_user)


@router.patch(
    "/auth/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Current User Profile",
    description="Update display name. Regular users cannot elevate roles or increase quotas.",
)
def update_current_user_profile(
    payload: UserProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> Profile:
    """Update user's own display profile attributes."""
    return update_user_profile(
        session=session,
        user=current_user,
        full_name=payload.full_name,
    )


@router.get(
    "/admin/users",
    response_model=List[UserProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="List All User Profiles (Admin Only)",
    description="Administrative endpoint to inspect all user profiles and quotas.",
)
def admin_list_users(
    session: Session = Depends(get_admin_db_session),
) -> List[Profile]:
    """List all application users."""
    return list(session.scalars(select(Profile).order_by(Profile.created_at.desc())).all())


@router.patch(
    "/admin/users/{user_id}",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User Role or Quota (Admin Only)",
    description="Administrative endpoint to update user roles or monthly run quotas.",
)
def admin_update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    session: Session = Depends(get_admin_db_session),
) -> Profile:
    """Update any user profile role or quota."""
    target_profile = session.scalar(select(Profile).where(Profile.id == user_id))
    if target_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    if payload.role is not None and payload.role != target_profile.role:
        # Distributed two-phase role update with compensating recovery
        execute_reliable_role_update(
            session=session,
            target_profile=target_profile,
            new_role=payload.role,
        )
    if payload.quota_monthly_runs is not None:
        target_profile.quota_monthly_runs = payload.quota_monthly_runs
    if payload.full_name is not None:
        target_profile.full_name = payload.full_name.strip()

    session.flush()
    return target_profile


@router.post(
    "/admin/users/{user_id}/reconcile",
    status_code=status.HTTP_200_OK,
    summary="Reconcile User Role Consistency (Admin Only)",
    description="Administrative endpoint to reconcile role drift between PostgreSQL and Supabase Auth.",
)
def admin_reconcile_user_role(
    user_id: uuid.UUID,
    session: Session = Depends(get_admin_db_session),
) -> dict:
    """Reconcile authorization role state between database and identity provider."""
    return reconcile_user_role(session=session, user_id=user_id)
