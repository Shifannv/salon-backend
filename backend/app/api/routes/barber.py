from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_owner_or_staff
from app.db.session import get_db
from app.models import (
    BlockedSlot,
    Booking,
    BookingStatus,
    Notification,
    PaymentStatus,
    Profile,
    Salon,
    SalonHoliday,
    SalonImage,
    Service,
    ServiceCategory,
    ServiceSubcategory,
    Staff,
    StaffService,
    StaffServiceLanguage,
    UserRole,
)
from app.schemas.barber import (
    BlockedSlotCreate,
    BlockedSlotOut,
    StaffCreate,
    StaffOut,
    StaffServiceCreate,
    StaffServiceOut,
)
from app.schemas.booking import BookingCreate, BookingOut, BookingStatusUpdate, PaymentUpdate
from app.schemas.salon import (
    CategoryCreate,
    CategoryOut,
    SalonCreate,
    SalonHolidayCreate,
    SalonHolidayOut,
    SalonImageCreate,
    SalonImageOut,
    SalonOut,
    SalonUpdate,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    SubcategoryCreate,
    SubcategoryOut,
)
from app.services.bookings import create_booking
from app.services.permissions import require_salon_owner

router = APIRouter()


@router.post("/salons", response_model=SalonOut)
def create_salon(
    payload: SalonCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Salon:
    if user.role not in {UserRole.owner, UserRole.super_admin}:
        raise HTTPException(status_code=403, detail="Only owners can create salons")
    salon = Salon(owner_id=user.id, **payload.model_dump())
    db.add(salon)
    db.commit()
    db.refresh(salon)
    return salon


@router.get("/salons", response_model=list[SalonOut])
def my_salons(
    user: Profile = Depends(require_owner_or_staff), db: Session = Depends(get_db)
) -> list[Salon]:
    stmt = select(Salon).options(selectinload(Salon.images))
    if user.role != UserRole.super_admin:
        stmt = stmt.where(Salon.owner_id == user.id)
    return db.scalars(stmt).all()


@router.patch("/salons/{salon_id}", response_model=SalonOut)
def update_salon(
    salon_id: str,
    payload: SalonUpdate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Salon:
    require_salon_owner(db, user, salon_id)
    salon = db.get(Salon, salon_id)
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(salon, field, value)
    db.commit()
    db.refresh(salon)
    return salon


@router.post("/salons/{salon_id}/images", response_model=SalonImageOut)
def add_salon_image(
    salon_id: str,
    payload: SalonImageCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> SalonImage:
    require_salon_owner(db, user, salon_id)
    if payload.is_main:
        db.query(SalonImage).filter(SalonImage.salon_id == salon_id).update({"is_main": False})
    image = SalonImage(salon_id=salon_id, **payload.model_dump())
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.post("/salons/{salon_id}/holidays", response_model=SalonHolidayOut)
def add_holiday(
    salon_id: str,
    payload: SalonHolidayCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> SalonHoliday:
    require_salon_owner(db, user, salon_id)
    holiday = SalonHoliday(salon_id=salon_id, **payload.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.post("/categories", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> ServiceCategory:
    if user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Only super admin can manage global categories")
    category = ServiceCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.post("/subcategories", response_model=SubcategoryOut)
def create_subcategory(
    payload: SubcategoryCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> ServiceSubcategory:
    if user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Only super admin can manage global categories")
    subcategory = ServiceSubcategory(**payload.model_dump())
    db.add(subcategory)
    db.commit()
    db.refresh(subcategory)
    return subcategory


@router.post("/services", response_model=ServiceOut)
def create_service(
    payload: ServiceCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Service:
    require_salon_owner(db, user, payload.salon_id)
    service = Service(**payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/services/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Service:
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    require_salon_owner(db, user, service.salon_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


@router.post("/staff", response_model=StaffOut)
def create_staff(
    payload: StaffCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Staff:
    require_salon_owner(db, user, payload.salon_id)
    staff = Staff(**payload.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/salons/{salon_id}/staff", response_model=list[StaffOut])
def list_staff(
    salon_id: str,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> list[Staff]:
    require_salon_owner(db, user, salon_id)
    return db.scalars(select(Staff).where(Staff.salon_id == salon_id)).all()


@router.post("/staff-services", response_model=StaffServiceOut)
def create_staff_service(
    payload: StaffServiceCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> StaffService:
    staff = db.get(Staff, payload.staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    require_salon_owner(db, user, staff.salon_id)
    language_codes = payload.language_codes
    data = payload.model_dump(exclude={"language_codes"})
    row = StaffService(**data)
    db.add(row)
    db.flush()
    for code in language_codes:
        db.add(StaffServiceLanguage(staff_service_id=row.id, language_code=code))
    db.commit()
    db.refresh(row)
    return row


@router.post("/blocked-slots", response_model=BlockedSlotOut)
def create_blocked_slot(
    payload: BlockedSlotCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> BlockedSlot:
    if not payload.staff_id and not payload.salon_id:
        raise HTTPException(status_code=400, detail="staff_id or salon_id is required")
    salon_id = payload.salon_id
    if payload.staff_id:
        staff = db.get(Staff, payload.staff_id)
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")
        salon_id = staff.salon_id
    require_salon_owner(db, user, salon_id)
    if payload.end_datetime <= payload.start_datetime:
        raise HTTPException(status_code=400, detail="end_datetime must be after start_datetime")
    block = BlockedSlot(**payload.model_dump())
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.post("/walk-ins", response_model=BookingOut)
def create_walk_in(
    payload: BookingCreate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Booking:
    require_salon_owner(db, user, payload.salon_id)
    data = payload.model_dump()
    data["source"] = payload.source
    return create_booking(db, actor=user, **data)


@router.get("/bookings", response_model=list[BookingOut])
def salon_bookings(
    salon_id: str,
    status: BookingStatus | None = Query(default=None),
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> list[Booking]:
    require_salon_owner(db, user, salon_id)
    stmt = (
        select(Booking)
        .where(Booking.salon_id == salon_id)
        .options(selectinload(Booking.services))
        .order_by(Booking.start_datetime.desc())
    )
    if status:
        stmt = stmt.where(Booking.status == status)
    return db.scalars(stmt).all()


@router.patch("/bookings/{booking_id}/status", response_model=BookingOut)
def update_booking_status(
    booking_id: str,
    payload: BookingStatusUpdate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.services))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    require_salon_owner(db, user, booking.salon_id)
    if payload.status == BookingStatus.rejected and not payload.rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason is required")

    now = datetime.now(timezone.utc)
    booking.status = payload.status
    booking.rejection_reason = payload.rejection_reason
    if payload.status == BookingStatus.confirmed:
        booking.approved_by = user.id
        booking.approved_at = now
    elif payload.status == BookingStatus.rejected:
        booking.rejected_by = user.id
        booking.rejected_at = now
    elif payload.status == BookingStatus.completed:
        booking.completed_by = user.id
        booking.completed_at = now
    elif payload.status == BookingStatus.cancelled:
        booking.cancelled_by = user.id
        booking.cancelled_at = now

    if booking.customer_id:
        db.add(
            Notification(
                user_id=booking.customer_id,
                booking_id=booking.id,
                type=f"booking_{payload.status.value}",
                title=f"Booking {payload.status.value}",
                body=f"Your booking status is now {payload.status.value}.",
            )
        )
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/bookings/{booking_id}/payment", response_model=BookingOut)
def update_payment(
    booking_id: str,
    payload: PaymentUpdate,
    user: Profile = Depends(require_owner_or_staff),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.services))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    require_salon_owner(db, user, booking.salon_id)
    booking.payment_status = payload.payment_status
    booking.payment_method = payload.payment_method
    if payload.payment_status == PaymentStatus.paid:
        booking.payment_recorded_by = user.id
        booking.payment_recorded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking

