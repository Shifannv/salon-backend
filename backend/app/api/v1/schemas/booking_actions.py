"""Booking action-request and salon-closure API schemas."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.api.v1.schemas.platform import BookingResponse

BookingActionKind = Literal["payment_confirmation", "cancellation"]
BookingActionStatus = Literal["pending", "resolved"]
BookingActionDecision = Literal["received", "not_received", "approve", "decline"]


class BookingActionCreateRequest(BaseModel):
    """Optional customer context attached to an action request."""

    reason: str | None = Field(default=None, max_length=500)


class BookingActionRespondRequest(BaseModel):
    """Owner/staff decision for one pending request."""

    decision: BookingActionDecision
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_decline_reason(self) -> "BookingActionRespondRequest":
        if self.decision == "decline" and not (self.reason or "").strip():
            raise ValueError("reason is required when declining a cancellation request")
        return self


class BookingActionRequestResponse(BaseModel):
    """Persisted customer request shown by both apps."""

    id: str
    booking_id: str
    kind: BookingActionKind
    status: BookingActionStatus
    customer_name: str
    service_names: list[str] = Field(default_factory=list)
    start_datetime: datetime
    total_price: float = Field(ge=0)
    reason: str | None = None
    decision: str | None = None
    decision_reason: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    booking: BookingResponse | None = None


class ClosurePreviewRequest(BaseModel):
    """Describe a holiday or staff/salon leave before it is applied."""

    kind: Literal["holiday", "leave"]
    holiday_date: date | None = None
    staff_id: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "ClosurePreviewRequest":
        if self.kind == "holiday":
            if self.holiday_date is None:
                raise ValueError("holiday_date is required for a holiday closure")
            if self.staff_id is not None:
                raise ValueError("holiday closures affect the whole salon")
            if self.start_datetime is not None or self.end_datetime is not None:
                raise ValueError("holiday closures use holiday_date, not datetime bounds")
        else:
            if self.start_datetime is None or self.end_datetime is None:
                raise ValueError("start_datetime and end_datetime are required for leave")
            if self.end_datetime <= self.start_datetime:
                raise ValueError("end_datetime must be later than start_datetime")
            for value in (self.start_datetime, self.end_datetime):
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError("leave datetimes must include a timezone offset")
        return self


class ClosureApplyRequest(ClosurePreviewRequest):
    """Confirmed closure with the exact previewed bookings and owner reason."""

    reason: str = Field(min_length=1, max_length=500)
    affected_booking_ids: list[str] = Field(default_factory=list)
    resolution: Literal["cancel"] = "cancel"
    title: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def require_nonblank_reason(self) -> "ClosureApplyRequest":
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("reason is required when applying a closure")
        return self


class ClosureAffectedBookingResponse(BaseModel):
    """Booking whose reserved interval overlaps a proposed closure."""

    booking_id: str
    customer_id: str | None = None
    customer_name: str
    staff_id: str
    service_names: list[str] = Field(default_factory=list)
    start_datetime: datetime
    end_datetime: datetime
    status: str


class ClosurePreviewResponse(BaseModel):
    """Current server-owned impact set for a proposed closure."""

    affected_count: int = Field(ge=0)
    affected_bookings: list[ClosureAffectedBookingResponse]


class ClosureApplyResponse(ClosurePreviewResponse):
    """Applied closure and bookings cancelled in the same transaction."""

    closure_kind: Literal["holiday", "leave"]
    closure_id: str
    reason: str
