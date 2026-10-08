"""Profile domain entities."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    """Supported platform roles."""

    super_admin = "super_admin"
    owner = "owner"
    staff = "staff"
    customer = "customer"


@dataclass(frozen=True, slots=True)
class Profile:
    """Authenticated platform profile."""

    id: str
    role: Role
    full_name: str | None
    email: str | None
    phone: str | None
    phone_verified: bool
    avatar_url: str | None
    is_active: bool
