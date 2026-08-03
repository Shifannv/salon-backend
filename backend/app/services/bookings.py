from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ApprovalMode,
    Booking,
    BookingService,
    BookingSource,
    BookingStatus,
    Notification,
    Profile,
    Service,
    Staff,
    StaffService,
)
from app.services.slots import ACTIVE_BOOKING_STATUSES, get_available_slots, overlaps


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _load_services_for_staff(
    db: Session, staff_id: str, service_ids: list[str]
) -> list[tuple[Service, StaffService | None]]:
    rows: list[tuple[Service, StaffService | None]] = []
    for service_id in service_ids:
        service = db.get(Service, service_id)
        if not service or not service.is_active:
            raise HTTPException(status_code=400, detail="One or more services are unavailable")
        staff_service = db.scalar(
            select(StaffService).where(
                StaffService.staff_id == staff_id,
                StaffService.service_id == service_id,
                StaffService.is_active.is_(True),
            )
        )
        if not staff_service:
            raise HTTPException(status_code=400, detail="Staff member does not offer all services")
        rows.append((service, staff_service))
    return rows


def calculate_booking_totals(
    db: Session, staff_id: str, service_ids: list[str]
) -> tuple[int, Decimal, list[tuple[Service, int, Decimal]]]:
    rows = _load_services_for_staff(db, staff_id, service_ids)
    snapshots: list[tuple[Service, int, Decimal]] = []
    total_duration = 0
    total_price = Decimal("0")
    for service, staff_service in rows:
        duration = staff_service.duration_minutes or service.duration_minutes
        price = staff_service.price_override or service.price
        total_duration += duration
        total_price += price
        snapshots.append((service, duration, price))
    return total_duration, total_price, snapshots


def assert_no_overlap(db: Session, staff_id: str, start: datetime, end: datetime) -> None:
    candidates = db.scalars(
        select(Booking).where(
            Booking.staff_id == staff_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_datetime < end,
            Booking.end_datetime > start,
        )
    ).all()
    if any(overlaps(start, end, _utc(row.start_datetime), _utc(row.end_datetime)) for row in candidates):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That slot is already booked")


def create_booking(
    db: Session,
    *,
    actor: Profile | None,
    salon_id: str,
    staff_id: str,
    service_ids: list[str],
    start_datetime: datetime,
    customer_name: str,
    customer_phone: str | None,
    source: BookingSource,
    notes: str | None = None,
) -> Booking:
    staff = db.get(Staff, staff_id)
    if not staff or not staff.is_active or staff.salon_id != salon_id:
        raise HTTPException(status_code=404, detail="Staff member not found for salon")

    if not staff.salon.is_active or not staff.salon.profile_completed:
        raise HTTPException(status_code=404, detail="Salon not available")

    start = _utc(start_datetime)
    if start <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot book a slot in the past")

    duration, total_price, snapshots = calculate_booking_totals(db, staff_id, service_ids)
    end = start + timedelta(minutes=duration)

    available = get_available_slots(
        db,
        staff_id=staff_id,
            booking_date=start.astimezone(ZoneInfo(staff.salon.timezone)).date(),
        duration_minutes=duration,
    )
    if not any(slot_start == start for slot_start, _ in available):
        raise HTTPException(status_code=409, detail="Selected slot is no longer available")
    assert_no_overlap(db, staff_id, start, end)

    booking_status = (
        BookingStatus.confirmed
        if source in {BookingSource.manual_walkin, BookingSource.qr_walkin}
        or staff.salon.approval_mode == ApprovalMode.auto
        else BookingStatus.pending
    )
    customer_id = None if source == BookingSource.manual_walkin else actor.id if actor else None

    booking = Booking(
        salon_id=salon_id,
        staff_id=staff_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        phone_verified=source == BookingSource.qr_walkin and actor is not None,
        source=source,
        status=booking_status,
        start_datetime=start,
        end_datetime=end,
        total_duration_minutes=duration,
        total_price=total_price,
        notes=notes,
    )
    db.add(booking)
    db.flush()

    for service, service_duration, price in snapshots:
        db.add(
            BookingService(
                booking_id=booking.id,
                service_id=service.id,
                service_name=service.name,
                duration_minutes=service_duration,
                price=price,
            )
        )

    if customer_id:
        db.add(
            Notification(
                user_id=customer_id,
                booking_id=booking.id,
                type="booking_created",
                title="Booking created",
                body=f"Your booking at {staff.salon.name} is {booking_status.value}.",
            )
        )
    db.commit()
    return db.scalar(
        select(Booking)
        .where(Booking.id == booking.id)
        .options(selectinload(Booking.services))
    )
