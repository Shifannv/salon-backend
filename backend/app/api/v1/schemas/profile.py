"""Profile API schemas."""

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from app.api.v1.schemas.media_urls import HostedMediaRequest


class ProfileUpdateRequest(HostedMediaRequest):
    """Shared profile update request (PATCH /profiles/me).

    Used by owners, staff, and customers — not customer-only despite the name.
    Fields are all optional; only explicitly sent fields are written.
    Sending ``null`` for a nullable field (e.g. ``phone``) clears it.
    """

    # These identifiers resolve to bundled assets in the customer and owner apps.
    # They are bounded metadata, never uploaded binaries or inline image payloads.
    avatar_references: ClassVar[frozenset[str]] = frozenset(
        {f"__char__char-{index}" for index in range(1, 16)}
        | {"avatar:curly", "avatar:beard", "avatar:geek"}
    )

    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    avatar_url: str | None = None

    @field_validator("full_name")
    @classmethod
    def full_name_cannot_be_cleared(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Name cannot be empty")
        return value.strip()

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, value: str | None) -> str | None:
        """Normalize and reject obvious fake customer phone numbers."""

        if value is None:
            return None

        raw = value.strip()
        if raw.startswith("+91"):
            digits = raw[3:]
        else:
            digits = raw

        sequential_runs = {
            "012345", "12345", "23456", "34567", "45678", "56789",
            "98765", "87654", "76543", "65432", "54321", "43210",
        }
        if (
            not digits.isdigit()
            or len(digits) != 10
            or digits[0] not in "6789"
            or len(set(digits)) == 1
            or digits[:2] * 5 == digits
            or any(sequence in digits for sequence in sequential_runs)
        ):
            raise ValueError("Enter a valid 10-digit Indian mobile number")

        return f"+91{digits}"


class ProfileResponse(BaseModel):
    """Profile response."""

    # Pydantic qualifies colliding component names with the defining module. Keep the historical
    # ``...schemas__platform__`` OpenAPI name now that the model lives in its own module.
    __module__ = "app.api.v1.schemas.platform"

    id: str
    role: str
    full_name: str | None
    email: str | None
    phone: str | None
    phone_verified: bool
    avatar_url: str | None
    is_active: bool
