from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import BlockedSlot, Booking, BookingStatus, SalonHoliday, Staff

ACTIVE_BOOKING_STATUSES = {BookingStatus.pending, BookingStatus.confirmed}


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _day_key(value: date) -> str:
    return value.strftime("%a").lower()[:3]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_available_slots(
    db: Session,
    *,
    staff_id: str,
    booking_date: date,
    duration_minutes: int,
) -> list[tuple[datetime, datetime]]:
    staff = db.get(Staff, staff_id)
    if not staff or not staff.is_active or not staff.salon.is_active or not staff.salon.profile_completed:
        return []

    salon = staff.salon
    is_holiday = db.scalar(
        select(SalonHoliday.id).where(
            SalonHoliday.salon_id == salon.id,
            SalonHoliday.holiday_date == booking_date,
        )
    )
    if is_holiday:
        return []

    hours = staff.working_hours or salon.working_hours or {}
    day_hours = hours.get(_day_key(booking_date))
    if not day_hours:
        return []

    tz = ZoneInfo(salon.timezone)
    open_at = time.fromisoformat(day_hours["open"])
    close_at = time.fromisoformat(day_hours["close"])
    cursor = datetime.combine(booking_date, open_at, tzinfo=tz).astimezone(timezone.utc)
    day_end = datetime.combine(booking_date, close_at, tzinfo=tz).astimezone(timezone.utc)
    interval = timedelta(minutes=salon.slot_interval_minutes)
    duration = timedelta(minutes=duration_minutes)
    now = datetime.now(timezone.utc)

    bookings = db.scalars(
        select(Booking).where(
            Booking.staff_id == staff_id,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.start_datetime < day_end,
            Booking.end_datetime > cursor,
        )
    ).all()
    blocks = db.scalars(
        select(BlockedSlot).where(
            or_(BlockedSlot.staff_id == staff_id, and_(BlockedSlot.staff_id.is_(None), BlockedSlot.salon_id == salon.id)),
            BlockedSlot.start_datetime < day_end,
            BlockedSlot.end_datetime > cursor,
        )
    ).all()

    slots: list[tuple[datetime, datetime]] = []
    while cursor + duration <= day_end:
        slot_end = cursor + duration
        if cursor > now:
            has_booking = any(
                overlaps(cursor, slot_end, _as_utc(b.start_datetime), _as_utc(b.end_datetime))
                for b in bookings
            )
            has_block = any(
                overlaps(cursor, slot_end, _as_utc(block.start_datetime), _as_utc(block.end_datetime))
                for block in blocks
            )
            if not has_booking and not has_block:
                slots.append((cursor, slot_end))
        cursor += interval
    return slots

