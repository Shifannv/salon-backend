"""The server prices services and validates the slot; clients submit no money values."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.v1.schemas.booking import BookingSegmentResponse, VisitSegmentRequest


class BookingChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID
    service_ids: list[UUID] = Field(min_length=1, max_length=30)
    start_datetime: AwareDatetime
    expected_version: int = Field(ge=0)
    segments: list[VisitSegmentRequest] | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def match_segments(self):
        if self.segments is not None:
            ids = [sid for part in self.segments for sid in part.service_ids]
            if len(ids) != len(set(ids)) or set(ids) != set(self.service_ids) or self.segments[0].staff_id != self.staff_id:
                raise ValueError("Segments must match the selected staff and services")
        return self

    @field_validator("service_ids")
    @classmethod
    def distinct_services(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Select each service only once")
        return value


class BookingChangeQuote(BaseModel):
    booking_id: UUID
    version: int
    committed_reschedules: int
    duration_minutes: int
    service_amount: Decimal
    retained_paid_amount: Decimal
    additional_payment_required: Decimal
    total_payable: Decimal
    slot_available: bool
    can_commit: bool = False
    restriction_code: str | None = None
    quote_fingerprint: str
    segments: list[BookingSegmentResponse] = Field(default_factory=list)


class BookingChangeCommitRequest(BookingChangeRequest):
    quote_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class BookingVisitChangeAvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    segments: list[VisitSegmentRequest] = Field(min_length=1, max_length=30)
