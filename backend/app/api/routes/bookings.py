from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Booking, BookingStatus, Profile
from app.schemas.booking import BookingCreate, BookingOut, SlotQuery
from app.schemas.common import Slot
from app.services.bookings import calculate_booking_totals, create_booking
from app.services.slots import get_available_slots

router = APIRouter()


@router.post("/slots", response_model=list[Slot])
def available_slots(payload: SlotQuery, db: Session = Depends(get_db)) -> list[Slot]:
    duration, _, _ = calculate_booking_totals(db, payload.staff_id, payload.service_ids)
    return [
        Slot(slot_start=start, slot_end=end)
        for start, end in get_available_slots(
            db,
            staff_id=payload.staff_id,
            booking_date=payload.booking_date,
            duration_minutes=duration,
        )
    ]


@router.post("", response_model=BookingOut)
def create_customer_booking(
    payload: BookingCreate,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Booking:
    return create_booking(db, actor=user, **payload.model_dump())


@router.get("", response_model=list[BookingOut])
def list_my_bookings(
    status: BookingStatus | None = Query(default=None),
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Booking]:
    stmt = (
        select(Booking)
        .where(Booking.customer_id == user.id)
        .options(selectinload(Booking.services))
        .order_by(Booking.start_datetime.desc())
    )
    if status:
        stmt = stmt.where(Booking.status == status)
    return db.scalars(stmt).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: str,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.services))
    )
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: str,
    user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.services))
    )
    if not booking or booking.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status in {BookingStatus.completed, BookingStatus.cancelled, BookingStatus.rejected}:
        raise HTTPException(status_code=400, detail="Booking cannot be cancelled")
    booking.status = BookingStatus.cancelled
    booking.cancelled_by = user.id
    db.commit()
    db.refresh(booking)
    return booking

