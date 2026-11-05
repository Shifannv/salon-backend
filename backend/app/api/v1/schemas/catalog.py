"""Service, staff and language API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from urllib.parse import unquote, urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    field_validator,
)

from app.api.v1.schemas.common import UuidParam
from app.api.v1.schemas.media_urls import HostedMediaRequest

_MAX_DURATION_MINUTES = 24 * 60
# Money inputs: at most 10 digits with 2 decimals (numeric(10,2)); never NaN or Infinity.
_MONEY = {"max_digits": 10, "decimal_places": 2, "allow_inf_nan": False}


class ServiceResponse(BaseModel):
    """Service response."""

    id: str
    salon_id: str
    subcategory_id: str
    menu_category_id: str | None = None
    selection_group: str | None = "__category__"
    name: str
    duration_minutes: int
    price: Decimal
    is_active: bool
    category_name: str | None = None
    subcategory_name: str | None = None
    photo_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


ServiceDisplayName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
]


class ServicePresentationRequest(BaseModel):
    """Persisted salon-specific presentation; explicit null clears a value."""

    model_config = ConfigDict(extra="forbid")

    selection_group: ServiceDisplayName | None = "__category__"
    category_name: ServiceDisplayName | None = None
    subcategory_name: ServiceDisplayName | None = None
    photo_url: str | None = Field(default=None, max_length=2048)

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            TypeAdapter(HttpUrl).validate_python(value)
            parsed = urlsplit(value)
            valid = (
                parsed.scheme == "https" and parsed.hostname
                and "." in parsed.hostname and parsed.hostname != "localhost"
                and not parsed.username and not parsed.password
                and not any(c.isspace() or ord(c) < 32 for c in value)
                and "\\" not in value and parsed.port in (None, 443)
                and not any(part in {".", ".."} for part in unquote(parsed.path).split("/"))
                and "\\" not in unquote(parsed.path)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("photo_url must be a hosted HTTPS URL")
        return value


class ServiceCreateRequest(ServicePresentationRequest):
    """Create service request."""

    subcategory_id: str | None = None
    name: str
    duration_minutes: int = Field(gt=0, le=_MAX_DURATION_MINUTES)
    price: Decimal = Field(ge=0, **_MONEY)
    is_active: bool = True


class ServiceBatchCreateRequest(BaseModel):
    services: list[ServiceCreateRequest] = Field(min_length=1, max_length=30)


class ServiceUpdateRequest(ServicePresentationRequest):
    """Update service request; omitted fields retain their stored values."""

    subcategory_id: str | None = None
    name: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=_MAX_DURATION_MINUTES)
    price: Decimal | None = Field(default=None, ge=0, **_MONEY)
    is_active: bool | None = None

    @field_validator("subcategory_id", "name", "duration_minutes", "price", "is_active")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("This service field cannot be null")
        return value


class StaffCreateRequest(HostedMediaRequest):
    """Create staff request."""

    profile_id: str | None = None
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None


class StaffUpdateRequest(HostedMediaRequest):
    """Update staff request."""

    profile_id: str | None = None
    name: str | None = None
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None
    is_active: bool | None = None


class StaffResponse(BaseModel):
    languages: list[str] = Field(default_factory=list)
    """Staff response (owner-facing, includes full detail)."""

    id: str
    salon_id: str
    profile_id: str | None = None
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    working_hours: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PublicStaffServiceResponse(BaseModel):
    service_id: str
    duration_minutes: int
    price: Decimal


class PublicStaffResponse(BaseModel):
    """Customer-facing staff/barber summary for salon detail and booking flow."""

    id: str
    name: str
    photo_url: str | None = None
    specialization: str | None = None
    experience: str | None = None
    service_ids: list[str] = Field(default_factory=list)
    services: list[PublicStaffServiceResponse] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class StaffCapabilitiesRequest(BaseModel):
    service_ids: list[UuidParam] = Field(max_length=500)
    languages: list[ServiceDisplayName] = Field(default_factory=list, max_length=50)


class StaffServiceAssignRequest(BaseModel):
    """Assign service to staff request."""

    service_id: str
    duration_minutes: int | None = Field(default=None, gt=0, le=_MAX_DURATION_MINUTES)
    price_override: Decimal | None = Field(default=None, ge=0, **_MONEY)
    specialization: str | None = None


class StaffServiceResponse(BaseModel):
    """Staff service response."""

    id: str
    staff_id: str
    service_id: str
    duration_minutes: int | None = None
    price_override: Decimal | None = None
    specialization: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LanguageResponse(BaseModel):
    """Language reference data response."""

    # Pydantic qualifies colliding component names with the defining module. Keep the historical
    # ``...schemas__platform__`` OpenAPI name now that the model lives in its own module.
    __module__ = "app.api.v1.schemas.platform"

    code: str
    name: str


class StaffServiceLanguagesRequest(BaseModel):
    """Set language codes for a staff service assignment (idempotent PUT)."""

    language_codes: list[str] = Field(
        description="ISO 639-1 codes, e.g. ['en', 'ml']. Replaces the current list."
    )
