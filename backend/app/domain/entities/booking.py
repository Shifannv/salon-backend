"""Booking domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class BookingStatus(StrEnum):
    """Lifecycle states a booking can occupy."""

    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"
    completed = "completed"
    cancelled = "cancelled"


class BookingSource(StrEnum):
    """How the booking was created."""

    app = "app"
    manual_walkin = "manual_walkin"
    qr_walkin = "qr_walkin"


class PaymentStatus(StrEnum):
    """Payment state."""

    unpaid = "unpaid"
    paid = "paid"


@dataclass(frozen=True, slots=True)
class BookingLine:
    """Immutable snapshot of one service within a booking."""

    service_id: str
    service_name: str
    duration_minutes: int
    price: object  # Decimal — avoid importing to stay pure


@dataclass(frozen=True, slots=True)
class Booking:
    """A salon appointment."""

    id: str
    salon_id: str
    staff_id: str
    customer_id: str | None
    customer_name: str
    customer_phone: str | None
    phone_verified: bool
    source: BookingSource
    status: BookingStatus
    start_datetime: datetime
    end_datetime: datetime
    total_duration_minutes: int
    total_price: object  # Decimal
    payment_status: PaymentStatus
    payment_method: str | None
    rejection_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    services: list[BookingLine] = field(default_factory=list)
