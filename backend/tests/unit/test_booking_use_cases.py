"""Unit tests for BookingUseCases."""


import pytest

from app.application.use_cases.platform import BookingUseCases
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.entities.profile import Role
from tests.conftest import make_booking, make_mock_repo, make_owner, make_profile

# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_availability_delegates_to_repo():
    repo = make_mock_repo()
    repo.get_available_slots.return_value = [
        {"slot_start": "2025-06-01T10:00:00", "slot_end": "2025-06-01T10:30:00"}
    ]
    uc = BookingUseCases(repo)

    from datetime import date
    slots = await uc.availability("staff-001", date(2025, 6, 1), ["service-001"])

    repo.get_available_slots.assert_awaited_once_with(
        "staff-001", date(2025, 6, 1), ["service-001"]
    )
    assert len(slots) == 1


# ---------------------------------------------------------------------------
# Create booking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_booking_customer_app():
    repo = make_mock_repo()
    repo.create_booking.return_value = make_booking()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    payload = {
        "salon_id": "salon-001",
        "staff_id": "staff-001",
        "service_ids": ["service-001"],
        "start_datetime": "2025-06-01T10:00:00",
        "customer_name": "Test",
        "source": "app",
    }
    booking = await uc.create_booking(actor, payload)

    assert booking["status"] == "pending"
    repo.create_booking.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_booking_manual_walkin_requires_owner():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    payload = {"source": "manual_walkin", "staff_id": "s1", "service_ids": ["sv1"]}
    with pytest.raises(ForbiddenError):
        await uc.create_booking(actor, payload)


@pytest.mark.asyncio
async def test_create_booking_app_source_requires_customer():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_owner()

    payload = {"source": "app", "staff_id": "s1", "service_ids": ["sv1"]}
    with pytest.raises(ForbiddenError):
        await uc.create_booking(actor, payload)


# ---------------------------------------------------------------------------
# Get booking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_booking_found():
    repo = make_mock_repo()
    repo.get_booking.return_value = make_booking()
    uc = BookingUseCases(repo)
    actor = make_profile()

    booking = await uc.get_booking(actor, "booking-001")
    assert booking["id"] == "booking-001"


@pytest.mark.asyncio
async def test_get_booking_not_found():
    repo = make_mock_repo()
    repo.get_booking.return_value = None
    uc = BookingUseCases(repo)
    actor = make_profile()

    with pytest.raises(NotFoundError):
        await uc.get_booking(actor, "nonexistent")


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_requires_owner():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.approve(actor, "booking-001")


@pytest.mark.asyncio
async def test_approve_as_owner():
    repo = make_mock_repo()
    confirmed = make_booking(status="confirmed")
    repo.update_booking_status.return_value = confirmed
    uc = BookingUseCases(repo)
    actor = make_owner()

    booking = await uc.approve(actor, "booking-001")
    assert booking["status"] == "confirmed"
    repo.update_booking_status.assert_awaited_once_with(
        actor.id, "booking-001", "confirmed"
    )


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reject_as_owner_sends_reason():
    repo = make_mock_repo()
    rejected = make_booking(status="rejected")
    repo.update_booking_status.return_value = rejected
    uc = BookingUseCases(repo)
    actor = make_owner()

    booking = await uc.reject(actor, "booking-001", "Fully booked that day")
    assert booking["status"] == "rejected"
    repo.update_booking_status.assert_awaited_once_with(
        actor.id, "booking-001", "rejected", rejection_reason="Fully booked that day"
    )


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_by_customer_uses_customer_only_flag():
    repo = make_mock_repo()
    cancelled = make_booking(status="cancelled")
    repo.update_booking_status.return_value = cancelled
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    await uc.cancel(actor, "booking-001")
    _, call_kwargs = repo.update_booking_status.call_args
    assert call_kwargs.get("customer_only") is True


@pytest.mark.asyncio
async def test_cancel_by_owner_not_customer_only():
    repo = make_mock_repo()
    cancelled = make_booking(status="cancelled")
    repo.update_booking_status.return_value = cancelled
    uc = BookingUseCases(repo)
    actor = make_owner()

    await uc.cancel(actor, "booking-001")
    _, call_kwargs = repo.update_booking_status.call_args
    assert call_kwargs.get("customer_only") is False


# ---------------------------------------------------------------------------
# Record payment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_payment_requires_owner():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    with pytest.raises(ForbiddenError):
        await uc.record_payment(actor, "booking-001", "cash")
