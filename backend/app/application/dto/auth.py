"""Authentication DTOs."""

from dataclasses import dataclass

from app.domain.entities.profile import Profile


@dataclass(frozen=True, slots=True)
class AuthTokens:
    """Tokens issued by Supabase Auth."""

    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None


@dataclass(frozen=True, slots=True)
class LoginInput:
    """Email-password login input."""

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RefreshInput:
    """Refresh-token input."""

    refresh_token: str


@dataclass(frozen=True, slots=True)
class MeOutput:
    """Current profile output."""

    profile: Profile
