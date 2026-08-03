from decimal import Decimal

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    ApprovalMode,
    Language,
    Profile,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    ServiceSubcategory,
    Staff,
    StaffService,
    UserRole,
)

DEFAULT_HOURS = {
    "mon": {"open": "09:00", "close": "21:00"},
    "tue": {"open": "09:00", "close": "21:00"},
    "wed": {"open": "09:00", "close": "21:00"},
    "thu": {"open": "09:00", "close": "21:00"},
    "fri": {"open": "09:00", "close": "21:00"},
    "sat": {"open": "09:00", "close": "21:00"},
    "sun": None,
}


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for code, name in [
            ("en", "English"),
            ("ml", "Malayalam"),
            ("hi", "Hindi"),
            ("ta", "Tamil"),
            ("ar", "Arabic"),
            ("kn", "Kannada"),
        ]:
            if not db.get(Language, code):
                db.add(Language(code=code, name=name))

        owner = db.scalar(select(Profile).where(Profile.email == "owner@example.com"))
        if not owner:
            owner = Profile(
                role=UserRole.owner,
                full_name="Demo Owner",
                email="owner@example.com",
                phone="+919999999001",
                hashed_password=get_password_hash("password123"),
            )
            db.add(owner)
            db.flush()

        customer = db.scalar(select(Profile).where(Profile.email == "customer@example.com"))
        if not customer:
            db.add(
                Profile(
                    role=UserRole.customer,
                    full_name="Demo Customer",
                    email="customer@example.com",
                    phone="+919999999002",
                    hashed_password=get_password_hash("password123"),
                )
            )

        category = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == "hair"))
        if not category:
            category = ServiceCategory(name="Hair", slug="hair", sort_order=1)
            db.add(category)
            db.flush()

        subcategory = db.scalar(
            select(ServiceSubcategory).where(ServiceSubcategory.slug == "haircut")
        )
        if not subcategory:
            subcategory = ServiceSubcategory(
                category_id=category.id,
                name="Haircut",
                slug="haircut",
                sort_order=1,
            )
            db.add(subcategory)
            db.flush()

        salon = db.scalar(select(Salon).where(Salon.name == "Urban Trim Studio"))
        if not salon:
            salon = Salon(
                owner_id=owner.id,
                name="Urban Trim Studio",
                description="A clean demo salon for customer and barber app testing.",
                category="unisex",
                address="MG Road",
                city="Kochi",
                lat=9.9816,
                lng=76.2999,
                working_hours=DEFAULT_HOURS,
                approval_mode=ApprovalMode.manual,
                slot_interval_minutes=15,
                profile_completed=True,
            )
            db.add(salon)
            db.flush()
            db.add(
                SalonImage(
                    salon_id=salon.id,
                    url="https://images.unsplash.com/photo-1560066984-138dadb4c035",
                    caption="Main floor",
                    is_main=True,
                )
            )

        service = db.scalar(select(Service).where(Service.name == "Classic Haircut"))
        if not service:
            service = Service(
                salon_id=salon.id,
                subcategory_id=subcategory.id,
                name="Classic Haircut",
                description="Wash, cut, and basic styling.",
                duration_minutes=30,
                price=Decimal("350.00"),
            )
            db.add(service)
            db.flush()

        staff = db.scalar(select(Staff).where(Staff.name == "Arjun"))
        if not staff:
            staff = Staff(
                salon_id=salon.id,
                name="Arjun",
                specialization="Hair stylist",
                working_hours=None,
            )
            db.add(staff)
            db.flush()

        if not db.scalar(
            select(StaffService).where(
                StaffService.staff_id == staff.id,
                StaffService.service_id == service.id,
            )
        ):
            db.add(StaffService(staff_id=staff.id, service_id=service.id, is_active=True))

        db.commit()
        print("Seed complete")
        print("Owner: owner@example.com / password123")
        print("Customer: customer@example.com / password123")
        print(f"Salon ID: {salon.id}")
        print(f"Staff ID: {staff.id}")
        print(f"Service ID: {service.id}")
    finally:
        db.close()


if __name__ == "__main__":
    run()

