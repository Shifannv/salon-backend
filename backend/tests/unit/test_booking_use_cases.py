"""Unit tests for BookingUseCases."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.api.v1.schemas.platform import BookingResponse
from app.application.use_cases.platform import BookingUseCases
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.entities.profile import Role
from tests.conftest import make_booking, make_mock_repo, make_owner, make_profile


def test_booking_response_can_cancel_only_before_start_time():
    future = datetime.now(UTC) + timedelta(
        minutes=settings.customer_cancellation_cutoff_minutes + 60
    )
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
            "start_datetime": datetime.now(UTC) - timedelta(minutes=1),
            "end_datetime": future - timedelta(hours=1, minutes=30),
        }
    )

    assert future_response.can_cancel is True
    assert past_response.can_cancel is False


def test_booking_response_exposes_late_cancellation_and_cash_claim_eligibility(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "customer_cancellation_cutoff_minutes", 120)
    monkeypatch.setattr(settings, "allow_late_cancellation_requests", True)
    now = datetime.now(UTC)
    booking = make_booking(status="confirmed")
    response = BookingResponse(
        **{
            **booking,
            "start_datetime": now + timedelta(minutes=30),
            "end_datetime": now + timedelta(hours=1),
            "payment_preference": "pay_at_salon",
        }
    )
    assert response.can_cancel is True
    assert response.can_request_cancellation is False
    assert response.can_confirm_payment is False

    after_start = BookingResponse(
        **{
            **booking,
            "start_datetime": now - timedelta(minutes=5),
            "end_datetime": now + timedelta(minutes=25),
            "payment_preference": "pay_at_salon",
        }
    )
    assert after_start.can_confirm_payment is True
    assert after_start.can_request_cancellation is False

    pending_claim = after_start.model_copy(
        update={"latest_payment_request_status": "pending"}
    )
    assert BookingResponse(**pending_claim.model_dump()).can_confirm_payment is False

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
@pytest.mark.parametrize(
    ("status", "title", "kind"),
    [
        ("pending", "Booking Requested", "booking_requested"),
        ("confirmed", "Booking Confirmed", "booking_confirmed"),
    ],
)
async def test_create_booking_notifies_customer_and_owner(status, title, kind):
    from unittest.mock import AsyncMock

    from fastapi import BackgroundTasks

    repo = make_mock_repo()
    repo.create_booking.return_value = make_booking(status=status)
    uc = BookingUseCases(repo)
    uc._notify_user = AsyncMock()
    tasks = BackgroundTasks()
    actor = make_profile(role=Role.customer)

    booking = await uc.create_booking(
        actor,
        {
            "salon_id": "salon-001",
            "staff_id": "staff-001",
            "service_ids": ["service-001"],
            "start_datetime": "2025-06-01T10:00:00",
            "customer_name": "Test",
            "source": "app",
        },
        tasks,
    )
    for task in tasks.tasks:
        await task.func(*task.args, **task.kwargs)

    sent = {call.args[2]: call.args for call in uc._notify_user.await_args_list}
    assert kind in sent and sent[kind][3] == title
    assert sent[kind][0] == str(booking["customer_id"])


@pytest.mark.asyncio
async def test_create_booking_customer_app_allows_owner_as_customer():
    repo = make_mock_repo()
    repo.create_booking.return_value = make_booking()
    uc = BookingUseCases(repo)
    actor = make_owner()

    payload = {"salon_id": "salon-001", "source": "app", "staff_id": "s1", "service_ids": ["sv1"]}
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
        "salon_id": "salon-001",
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

    payload = {"salon_id": "salon-001", "source": "app", "staff_id": "s1", "service_ids": ["sv1"]}
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
        booking_statuses=["confirmed", "completed"],
        include_archived=True,
        source="app",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 30),
        limit=25,
        offset=10,
    )

    repo.list_bookings.assert_awaited_once_with(
        actor.id,
        actor.role.value,
        booking_statuses=["confirmed", "completed"],
        include_archived=True,
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
    repo.cancel_customer_booking.return_value = cancelled
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    await uc.cancel(
        actor,
        "booking-001",
        reason_code="schedule_conflict",
        reason_text="Work meeting",
    )
    repo.cancel_customer_booking.assert_awaited_once_with(
        actor.id,
        "booking-001",
        "Schedule conflict — Work meeting",
        settings.customer_cancellation_cutoff_minutes,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("reason_text", [None, "", "   ", "schedule_conflict", "Schedule_Conflict", "Schedule conflict", "schedule-conflict"])
async def test_cancel_by_customer_does_not_repeat_the_reason_label(reason_text):
    repo = make_mock_repo()
    repo.cancel_customer_booking.return_value = make_booking(status="cancelled")
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    await uc.cancel(actor, "booking-001", reason_code="schedule_conflict", reason_text=reason_text)

    repo.cancel_customer_booking.assert_awaited_once_with(
        actor.id, "booking-001", "Schedule conflict", settings.customer_cancellation_cutoff_minutes
    )


@pytest.mark.asyncio
async def test_cancel_by_customer_keeps_free_text_without_a_code():
    repo = make_mock_repo()
    repo.cancel_customer_booking.return_value = make_booking(status="cancelled")
    uc = BookingUseCases(repo)
    actor = make_profile(role=Role.customer)

    await uc.cancel(actor, "booking-001", reason_text="Moved cities")

    repo.cancel_customer_booking.assert_awaited_once_with(
        actor.id, "booking-001", "Moved cities", settings.customer_cancellation_cutoff_minutes
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("reason_text", [None, "equipment_issue", "Equipment issue"])
async def test_barber_cancel_does_not_repeat_the_reason_label(reason_text):
    repo = make_mock_repo()
    repo.update_booking_status.return_value = make_booking(status="cancelled")
    uc = BookingUseCases(repo)
    actor = make_owner()

    await uc.barber_cancel(actor, "booking-001", reason_code="equipment_issue", reason_text=reason_text)

    repo.update_booking_status.assert_awaited_once_with(
        actor.id, "booking-001", "cancelled", cancellation_reason="Equipment issue"
    )


@pytest.mark.asyncio
async def test_barber_cancel_keeps_real_free_text():
    repo = make_mock_repo()
    repo.update_booking_status.return_value = make_booking(status="cancelled")
    uc = BookingUseCases(repo)
    actor = make_owner()

    await uc.barber_cancel(actor, "booking-001", reason_code="equipment_issue", reason_text="Dryer broke")

    repo.update_booking_status.assert_awaited_once_with(
        actor.id, "booking-001", "cancelled", cancellation_reason="Equipment issue — Dryer broke"
    )


@pytest.mark.asyncio
async def test_cancel_by_owner_not_customer_only():
    repo = make_mock_repo()
    cancelled = make_booking(status="cancelled")
    repo.cancel_customer_booking.return_value = cancelled
    uc = BookingUseCases(repo)
    actor = make_owner()

    await uc.cancel(actor, "booking-001")
    repo.cancel_customer_booking.assert_awaited_once_with(
        actor.id,
        "booking-001",
        None,
        settings.customer_cancellation_cutoff_minutes,
    )


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


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("archived", [True, False])
async def test_owner_archives_and_restores_through_the_repository(archived):
    repo = make_mock_repo()
    repo.set_booking_archived.return_value = make_booking(status="cancelled")
    actor = make_owner()

    await BookingUseCases(repo).set_archived(actor, "booking-001", archived)

    repo.set_booking_archived.assert_awaited_once_with(actor.id, "booking-001", archived)


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [Role.customer, Role.staff, Role.super_admin])
async def test_only_the_salon_owner_can_archive(role):
    repo = make_mock_repo()

    with pytest.raises(ForbiddenError):
        await BookingUseCases(repo).set_archived(make_profile(role=role), "booking-001", True)

    repo.set_booking_archived.assert_not_awaited()
