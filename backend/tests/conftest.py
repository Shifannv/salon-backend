"""Shared test fixtures and mock builders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities.profile import Profile, Role

# ---------------------------------------------------------------------------
# Profile factories
# ---------------------------------------------------------------------------


def make_profile(
    id: str = "user-001",
    role: Role = Role.customer,
    is_active: bool = True,
) -> Profile:
    return Profile(
        id=id,
        role=role,
        full_name="Test User",
        email="test@example.com",
        phone="+919876543210",
        phone_verified=True,
        avatar_url=None,
        is_active=is_active,
    )


def make_owner(id: str = "owner-001") -> Profile:
    return make_profile(id=id, role=Role.owner)


def make_super_admin(id: str = "admin-001") -> Profile:
    return make_profile(id=id, role=Role.super_admin)


# ---------------------------------------------------------------------------
# Booking dict factory
# ---------------------------------------------------------------------------


def make_booking(
    booking_id: str = "booking-001",
    salon_id: str = "salon-001",
    staff_id: str = "staff-001",
    customer_id: str | None = "user-001",
    status: str = "pending",
) -> dict:
    return {
        "id": booking_id,
        "salon_id": salon_id,
        "staff_id": staff_id,
        "customer_id": customer_id,
        "customer_name": "Walk-In Customer",
        "customer_phone": "+919876543210",
        "phone_verified": False,
        "source": "app",
        "status": status,
        "start_datetime": datetime(2025, 6, 1, 10, 0),
        "end_datetime": datetime(2025, 6, 1, 10, 30),
        "total_duration_minutes": 30,
        "total_price": Decimal("500.00"),
        "payment_status": "unpaid",
        "payment_method": None,
        "rejection_reason": None,
        "notes": None,
        "services": [],
        "created_at": datetime(2025, 6, 1, 9, 0),
        "updated_at": datetime(2025, 6, 1, 9, 0),
    }


# ---------------------------------------------------------------------------
# Mock repository builder
# ---------------------------------------------------------------------------


def make_mock_repo() -> MagicMock:
    """Return an AsyncMock of PlatformRepository with sensible defaults."""

    repo = MagicMock()
    # Make all async methods return awaitable mocks
    for attr in [
        "update_profile",
        "get_profile",
        "list_salons",
        "get_public_salon",
        "list_public_services",
        "get_owner_salon",
        "update_owner_salon",
        "complete_owner_salon",
        "list_salon_images",
        "create_salon_image",
        "update_salon_image",
        "list_holidays",
        "create_holiday",
        "delete_holiday",
        "list_owner_services",
        "create_owner_service",
        "update_owner_service",
        "deactivate_owner_service",
        "list_owner_staff",
        "create_owner_staff",
        "update_owner_staff",
        "deactivate_owner_staff",
        "assign_staff_service",
        "list_staff_services",
        "list_staff_service_languages",
        "set_staff_service_languages",
        "list_blocked_slots",
        "create_blocked_slot",
        "delete_blocked_slot",
        "get_available_slots",
        "create_booking",
        "list_bookings",
        "get_booking",
        "update_booking_status",
        "delay_booking",
        "list_delay_affected_bookings",
        "record_payment",
        "list_notifications",
        "mark_notification_read",
        "mark_all_notifications_read",
        "create_notification",
        "register_device",
        "deactivate_device_for_actor",
        # Admin repo methods
        "admin_list_salons",
        "admin_get_salon",
        "admin_create_salon",
        "admin_update_salon",
        "admin_deactivate_salon",
        "list_categories",
        "get_category",
        "create_category",
        "update_category",
        "deactivate_category",
        "list_subcategories",
        "get_subcategory",
        "create_subcategory",
        "update_subcategory",
        "deactivate_subcategory",
        "list_available_languages",
        # Walk-in
        "get_salon_by_qr",
    ]:
        setattr(repo, attr, AsyncMock())

    return repo
