"""Unit tests for BookingUseCases."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.api.v1.schemas.platform import BookingResponse
from app.application.use_cases.platform import BookingUseCases
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.entities.profile import Role
from tests.conftest import make_booking, make_mock_repo, make_owner, make_profile


def test_booking_response_can_cancel_only_before_start_time():
    future = datetime.now(UTC) + timedelta(hours=1)
    booking = make_booking()

    future_response = BookingResponse(
        **{
            **booking,
            "start_datetime": future,
            "end_datetime": future + timedelta(minutes=30),
        }
    )
    past_response = BookingResponse(
        **{
            **booking,
            "start_datetime": future - timedelta(hours=2),
            "end_datetime": future - timedelta(hours=1, minutes=30),
        }
    )

    assert future_response.can_cancel is True
    assert past_response.can_cancel is False

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
async def test_create_booking_customer_app_allows_owner_as_customer():
    repo = make_mock_repo()
    repo.create_booking.return_value = make_booking()
    uc = BookingUseCases(repo)
    actor = make_owner()

    payload = {"source": "app", "staff_id": "s1", "service_ids": ["sv1"]}
    booking = await uc.create_booking(actor, payload)

    assert booking["status"] == "pending"
    repo.create_booking.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_booking_customer_app_allows_multiple_separate_bookings():
    repo = make_mock_repo()
    repo.create_booking.side_effect = [
        {**make_booking(), "id": "booking-001", "start_datetime": "2025-06-01T10:00:00"},
        {**make_booking(), "id": "booking-002", "start_datetime": "2025-06-01T11:00:00"},
    ]
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    first_payload = {
        "source": "app",
        "staff_id": "s1",
        "service_ids": ["sv1"],
        "start_datetime": "2025-06-01T10:00:00",
    }
    second_payload = {
        **first_payload,
        "start_datetime": "2025-06-01T11:00:00",
    }

    first_booking = await uc.create_booking(actor, first_payload)
    second_booking = await uc.create_booking(actor, second_payload)

    assert first_booking["id"] == "booking-001"
    assert second_booking["id"] == "booking-002"
    assert repo.create_booking.await_count == 2


@pytest.mark.asyncio
async def test_create_booking_manual_walkin_requires_owner():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    payload = {"source": "manual_walkin", "staff_id": "s1", "service_ids": ["sv1"]}
    with pytest.raises(ForbiddenError):
        await uc.create_booking(actor, payload)


@pytest.mark.asyncio
async def test_create_booking_app_source_rejects_staff():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.staff)

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


@pytest.mark.asyncio
async def test_list_bookings_passes_optional_filters():
    repo = make_mock_repo()
    repo.list_bookings.return_value = []
    uc = BookingUseCases(repo)
    actor = make_owner()

    await uc.list_bookings(
        actor,
        booking_status="confirmed",
        source="app",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 30),
        limit=25,
        offset=10,
    )

    repo.list_bookings.assert_awaited_once_with(
        actor.id,
        actor.role.value,
        booking_status="confirmed",
        source="app",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 30),
        limit=25,
        offset=10,
    )


@pytest.mark.asyncio
async def test_list_bookings_rejects_reversed_date_range():
    from app.core.exceptions import ValidationError

    repo = make_mock_repo()
    uc = BookingUseCases(repo)

    with pytest.raises(ValidationError, match="date_from"):
        await uc.list_bookings(
            make_owner(),
            date_from=date(2026, 10, 1),
            date_to=date(2026, 9, 1),
        )


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

    await uc.cancel(
        actor,
        "booking-001",
        reason_code="schedule_conflict",
        reason_text="Work meeting",
    )
    _, call_kwargs = repo.update_booking_status.call_args
    assert call_kwargs.get("customer_only") is True
    assert call_kwargs.get("cancellation_reason") == "Schedule conflict — Work meeting"


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


@pytest.mark.asyncio
async def test_delay_booking_requires_owner_or_staff():
    repo = make_mock_repo()
    uc = BookingUseCases(repo)

    with pytest.raises(ForbiddenError):
        await uc.delay(
            make_profile(role=Role.customer),
            "booking-001",
            datetime.now(UTC) + timedelta(hours=2),
            True,
        )


@pytest.mark.asyncio
async def test_delay_booking_updates_estimate():
    repo = make_mock_repo()
    end = datetime.now(UTC) + timedelta(hours=1)
    estimate = end + timedelta(minutes=30)
    current = {**make_booking(), "end_datetime": end}
    delayed = {**current, "estimated_end_datetime": estimate}
    repo.get_booking.return_value = current
    repo.delay_booking.return_value = delayed
    uc = BookingUseCases(repo)
    owner = make_owner()

    result = await uc.delay(owner, "booking-001", estimate, False)

    assert result["estimated_end_datetime"] == estimate
    repo.delay_booking.assert_awaited_once_with(owner.id, "booking-001", estimate)


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
