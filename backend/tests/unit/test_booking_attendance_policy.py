"""No-show operational guards, including the legacy salon cancellation entry point."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ConflictError, ValidationError
from tests.unit.test_booking_action_repository import _repository, _Result

NOW = datetime(2026, 10, 23, 10, tzinfo=UTC)


def repository_at(start, status="confirmed"):
    current = {
        "id": "booking-1", "status": status, "customer_id": "customer-1",
        "customer_name": "Test", "payment_status": "unpaid", "payment_preference": "pay_at_salon",
        "start_datetime": start, "database_now": NOW,
    }
    repository, session = _repository(_Result(current), *[_Result() for _ in range(5)])
    repository.get_booking = AsyncMock(return_value={**current, "status": "no_show"})
    repository._insert_notification_outbox = AsyncMock(return_value="outbox-1")
    return repository, session


@pytest.mark.parametrize("status", ["no_show", "cancelled"])
async def test_both_no_show_entry_points_block_before_ten_minute_grace(status):
    repository, session = repository_at(NOW - timedelta(minutes=9, seconds=59))
    with pytest.raises(ValidationError, match="10 minutes"):
        await repository.update_booking_status(
            "owner-1", "booking-1", status, cancellation_reason="Customer no-show — Did not arrive"
        )
    session.commit.assert_not_awaited()


async def test_no_show_without_explicit_reason_is_rejected():
    repository, session = repository_at(NOW - timedelta(minutes=10))
    with pytest.raises(ValidationError, match="reason"):
        await repository.update_booking_status("owner-1", "booking-1", "no_show")
    session.commit.assert_not_awaited()


async def test_no_show_at_exact_grace_persists_customer_notification():
    repository, session = repository_at(NOW - timedelta(minutes=10))
    booking = await repository.update_booking_status(
        "owner-1", "booking-1", "no_show", cancellation_reason="Customer no-show — Did not arrive"
    )
    assert booking["_outbox_ids"] == ["outbox-1"]
    assert repository._insert_notification_outbox.await_args.kwargs["user_id"] == "customer-1"
    assert repository._insert_notification_outbox.await_args.kwargs["notification_type"] == "booking_no_show"
    session.commit.assert_awaited_once()


@pytest.mark.parametrize("target", ["no_show", "cancelled"])
async def test_checked_in_customer_cannot_be_reclassified_as_absent(target):
    repository, session = repository_at(NOW - timedelta(minutes=30), status="checked_in")
    with pytest.raises(ConflictError):
        await repository.update_booking_status(
            "owner-1", "booking-1", target, cancellation_reason="Customer no-show — Did not arrive"
        )
    session.commit.assert_not_awaited()
