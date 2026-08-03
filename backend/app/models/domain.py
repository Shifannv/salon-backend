import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.enums import (
    ApprovalMode,
    BookingSource,
    BookingStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


def uuid_pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[str] = uuid_pk()
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.customer, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owned_salons: Mapped[list["Salon"]] = relationship(back_populates="owner")
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="customer", foreign_keys="Booking.customer_id"
    )


class Salon(Base, TimestampMixin):
    __tablename__ = "salons"

    id: Mapped[str] = uuid_pk()
    owner_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(80), index=True)
    lat: Mapped[float | None]
    lng: Mapped[float | None]
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Kolkata")
    working_hours: Mapped[dict] = mapped_column(JSON, default=dict)
    approval_mode: Mapped[ApprovalMode] = mapped_column(
        Enum(ApprovalMode), default=ApprovalMode.manual
    )
    slot_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: uuid.uuid4().hex)
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped[Profile] = relationship(back_populates="owned_salons")
    images: Mapped[list["SalonImage"]] = relationship(
        back_populates="salon", cascade="all, delete-orphan"
    )
    holidays: Mapped[list["SalonHoliday"]] = relationship(
        back_populates="salon", cascade="all, delete-orphan"
    )
    services: Mapped[list["Service"]] = relationship(back_populates="salon")
    staff: Mapped[list["Staff"]] = relationship(back_populates="salon")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="salon")

    __table_args__ = (Index("idx_salons_active_city", "is_active", "profile_completed", "city"),)


class SalonImage(Base, TimestampMixin):
    __tablename__ = "salon_images"

    id: Mapped[str] = uuid_pk()
    salon_id: Mapped[str] = mapped_column(ForeignKey("salons.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(String(200))
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    salon: Mapped[Salon] = relationship(back_populates="images")


class SalonHoliday(Base, TimestampMixin):
    __tablename__ = "salon_holidays"

    id: Mapped[str] = uuid_pk()
    salon_id: Mapped[str] = mapped_column(ForeignKey("salons.id", ondelete="CASCADE"), index=True)
    holiday_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str | None] = mapped_column(String(120))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    salon: Mapped[Salon] = relationship(back_populates="holidays")
    __table_args__ = (UniqueConstraint("salon_id", "holiday_date", name="uq_salon_holiday"),)


class ServiceCategory(Base, TimestampMixin):
    __tablename__ = "service_categories"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subcategories: Mapped[list["ServiceSubcategory"]] = relationship(back_populates="category")


class ServiceSubcategory(Base, TimestampMixin):
    __tablename__ = "service_subcategories"

    id: Mapped[str] = uuid_pk()
    category_id: Mapped[str] = mapped_column(ForeignKey("service_categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140))
    image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped[ServiceCategory] = relationship(back_populates="subcategories")
    services: Mapped[list["Service"]] = relationship(back_populates="subcategory")
    __table_args__ = (UniqueConstraint("category_id", "slug", name="uq_subcategory_slug"),)


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[str] = uuid_pk()
    salon_id: Mapped[str] = mapped_column(ForeignKey("salons.id"), index=True)
    subcategory_id: Mapped[str] = mapped_column(ForeignKey("service_subcategories.id"), index=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    salon: Mapped[Salon] = relationship(back_populates="services")
    subcategory: Mapped[ServiceSubcategory] = relationship(back_populates="services")
    staff_services: Mapped[list["StaffService"]] = relationship(back_populates="service")


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    id: Mapped[str] = uuid_pk()
    salon_id: Mapped[str] = mapped_column(ForeignKey("salons.id"), index=True)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    photo_url: Mapped[str | None] = mapped_column(Text)
    specialization: Mapped[str | None] = mapped_column(String(160))
    working_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    salon: Mapped[Salon] = relationship(back_populates="staff")
    staff_services: Mapped[list["StaffService"]] = relationship(
        back_populates="staff", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="staff")


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))


class StaffService(Base, TimestampMixin):
    __tablename__ = "staff_services"

    id: Mapped[str] = uuid_pk()
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), index=True)
    service_id: Mapped[str] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    specialization: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    staff: Mapped[Staff] = relationship(back_populates="staff_services")
    service: Mapped[Service] = relationship(back_populates="staff_services")
    languages: Mapped[list["StaffServiceLanguage"]] = relationship(cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("staff_id", "service_id", name="uq_staff_service"),)


class StaffServiceLanguage(Base):
    __tablename__ = "staff_service_languages"

    staff_service_id: Mapped[str] = mapped_column(
        ForeignKey("staff_services.id", ondelete="CASCADE"), primary_key=True
    )
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"), primary_key=True)


class BlockedSlot(Base, TimestampMixin):
    __tablename__ = "blocked_slots"

    id: Mapped[str] = uuid_pk()
    staff_id: Mapped[str | None] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"))
    salon_id: Mapped[str | None] = mapped_column(ForeignKey("salons.id", ondelete="CASCADE"))
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    block_type: Mapped[str] = mapped_column(String(40), default="other")
    reason: Mapped[str | None] = mapped_column(Text)
    is_full_day: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(Text)
    recurrence_end: Mapped[date | None] = mapped_column(Date)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[str] = uuid_pk()
    salon_id: Mapped[str] = mapped_column(ForeignKey("salons.id"), index=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str | None] = mapped_column(String(30))
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource), default=BookingSource.app)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.pending, index=True
    )
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    total_duration_minutes: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.unpaid
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    approved_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_recorded_by: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"))
    payment_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    salon: Mapped[Salon] = relationship(back_populates="bookings")
    staff: Mapped[Staff] = relationship(back_populates="bookings")
    customer: Mapped[Profile | None] = relationship(back_populates="bookings", foreign_keys=[customer_id])
    services: Mapped[list["BookingService"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_bookings_active_time", "staff_id", "status", "start_datetime"),)


class BookingService(Base):
    __tablename__ = "booking_services"

    booking_id: Mapped[str] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[str] = mapped_column(ForeignKey("services.id"), primary_key=True)
    service_name: Mapped[str] = mapped_column(String(140))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    booking: Mapped[Booking] = relationship(back_populates="services")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    booking_id: Mapped[str | None] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    type: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(Text, unique=True)
    platform: Mapped[str | None] = mapped_column(String(30))
    device_name: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
