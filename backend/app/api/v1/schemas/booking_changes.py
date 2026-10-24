"""The server prices services and validates the slot; clients submit no money values."""

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class BookingChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID
    service_ids: list[UUID] = Field(min_length=1, max_length=30)
    start_datetime: AwareDatetime
    expected_version: int = Field(ge=0)

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
    quote_fingerprint: str


class BookingChangeCommitRequest(BookingChangeRequest):
    quote_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
