"""Authentication and user profile schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileResponse(BaseModel):
    """User profile metadata response."""
    id: uuid.UUID = Field(..., description="Unique user UUID from Supabase Auth")
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User display name")
    role: str = Field(..., description="Application role ('user' or 'admin')")
    quota_monthly_runs: int = Field(..., description="Monthly analysis runs quota")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last account update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    """Payload for updating user profile display attributes."""
    full_name: Optional[str] = Field(None, max_length=255, description="Updated display name")


class AdminUserUpdateRequest(BaseModel):
    """Administrative payload for updating role, quota, or user details."""
    role: Optional[str] = Field(None, pattern="^(user|admin)$", description="Role ('user' or 'admin')")
    quota_monthly_runs: Optional[int] = Field(None, ge=0, le=10000, description="Monthly quota")
    full_name: Optional[str] = Field(None, max_length=255, description="Updated display name")
