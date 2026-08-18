"""Authentication HTTP schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.domain.entities.profile import Role


class RefreshRequest(BaseModel):
    """Refresh-token request."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Supabase token response returned by the API."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class ProfileResponse(BaseModel):
    """Current profile response."""

    id: str
    role: Role
    full_name: str | None
    email: EmailStr | None
    phone: str | None
    phone_verified: bool
    avatar_url: str | None
    is_active: bool
