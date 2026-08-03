from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import BookingSource, BookingStatus, PaymentMethod, PaymentStatus
from app.schemas.common import APIModel


class SlotQuery(APIModel):
    staff_id: str
    service_ids: list[str] = Field(min_length=1)
    booking_date: date


class BookingCreate(APIModel):
    salon_id: str
    staff_id: str
    service_ids: list[str] = Field(min_length=1)
    start_datetime: datetime
    customer_name: str
    customer_phone: str | None = None
    source: BookingSource = BookingSource.app
    notes: str | None = None


class BookingStatusUpdate(APIModel):
    status: BookingStatus
    rejection_reason: str | None = None


class PaymentUpdate(APIModel):
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None = None


class BookingServiceOut(APIModel):
    service_id: str
    service_name: str
    duration_minutes: int
    price: Decimal


class BookingOut(APIModel):
    id: str
    salon_id: str
    staff_id: str
    customer_id: str | None
    customer_name: str
    customer_phone: str | None
    source: BookingSource
    status: BookingStatus
    start_datetime: datetime
    end_datetime: datetime
    total_duration_minutes: int
    total_price: Decimal
    payment_status: PaymentStatus
    payment_method: PaymentMethod | None
    rejection_reason: str | None
    notes: str | None
    services: list[BookingServiceOut] = Field(default_factory=list)
