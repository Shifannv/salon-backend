"""Repository state-machine tests without a live database."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


class _Result:
    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self._row

    def scalar_one_or_none(self):
        return self._scalar


def _repository(*results: _Result) -> tuple[PlatformRepository, MagicMock]:
    session = MagicMock()
    session.execute = AsyncMock(side_effect=results)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return PlatformRepository(session), session


@pytest.mark.asyncio
async def test_payment_claim_rejects_cancelled_booking() -> None:
    now = datetime.now(UTC)
    repository, _ = _repository(
        _Result(
            {
                "id": "booking-1",
                "status": "cancelled",
                "payment_status": "unpaid",
                "payment_preference": "pay_at_salon",
                "start_datetime": now - timedelta(hours=1),
                "end_datetime": now,
                "customer_name": "Customer",
                "owner_id": "owner-1",
                "database_now": now,
            }
        )
    )

    with pytest.raises(ConflictError, match="confirmed or completed"):
        await repository.create_booking_action_request(
            "customer-1",
            "booking-1",
            "payment_confirmation",
            None,
            cancellation_cutoff_minutes=120,
            allow_late_cancellation_requests=True,
        )


@pytest.mark.asyncio
async def test_duplicate_pending_request_is_rejected() -> None:
    now = datetime.now(UTC)
    repository, _ = _repository(
        _Result(
            {
                "id": "booking-1",
                "status": "confirmed",
                "payment_status": "unpaid",
                "payment_preference": "pay_at_salon",
                "start_datetime": now - timedelta(minutes=5),
                "end_datetime": now + timedelta(minutes=25),
                "customer_name": "Customer",
                "owner_id": "owner-1",
                "database_now": now,
            }
        ),
        _Result(scalar="existing-request"),
    )

    with pytest.raises(ConflictError, match="pending request"):
        await repository.create_booking_action_request(
            "customer-1",
            "booking-1",
            "payment_confirmation",
            None,
            cancellation_cutoff_minutes=120,
            allow_late_cancellation_requests=True,
        )


@pytest.mark.asyncio
async def test_second_owner_decision_is_stale() -> None:
    repository, _ = _repository(
        _Result(
            {
                "id": "request-1",
                "kind": "payment_confirmation",
                "request_status": "resolved",
            }
        )
    )

    with pytest.raises(ConflictError, match="already been resolved"):
        await repository.respond_booking_action_request(
            "owner-1", "request-1", "received", None
        )


@pytest.mark.asyncio
async def test_cross_salon_decision_is_hidden() -> None:
    repository, _ = _repository(_Result())

    with pytest.raises(NotFoundError):
        await repository.respond_booking_action_request(
            "other-owner", "request-1", "received", None
        )


@pytest.mark.asyncio
async def test_direct_payment_rejects_cancelled_booking() -> None:
    repository, _ = _repository(
        _Result(
            {
                "id": "booking-1",
                "status": "cancelled",
                "payment_status": "unpaid",
            }
        )
    )

    with pytest.raises(ConflictError, match="confirmed, checked-in or completed"):
        await repository.record_payment("owner-1", "booking-1", "cash")


@pytest.mark.asyncio
async def test_invalid_owner_transition_does_not_write() -> None:
    repository, session = _repository(_Result({"id": "booking-1", "status": "cancelled"}))

    with pytest.raises(ConflictError, match="state changed"):
        await repository.update_booking_status("owner-1", "booking-1", "confirmed")

    assert session.execute.await_count == 1
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_immediate_cancel_rejects_started_booking() -> None:
    now = datetime.now(UTC)
    repository, session = _repository(
        _Result(
            {
                "id": "booking-1",
                "status": "confirmed",
                "start_datetime": now - timedelta(minutes=1),
                "database_now": now,
            }
        )
    )

    with pytest.raises(ConflictError, match="started"):
        await repository.cancel_customer_booking("customer-1", "booking-1", None, 120)

    assert session.execute.await_count == 1
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected_write", "method"),
    [("received", True, "cash"), ("received", True, "online"), ("not_received", False, "cash")],
)
async def test_payment_owner_decision_changes_money_only_when_received(
    decision: str, expected_write: bool, method: str
) -> None:
    now = datetime.now(UTC)
    repository, session = _repository(
        _Result(
            {
                "id": "request-1",
                "kind": "payment_confirmation",
                "request_status": "pending",
                "booking_id": "booking-1",
                "booking_status": "confirmed",
                "payment_status": "unpaid",
                "customer_id": "customer-1",
                "end_datetime": now + timedelta(minutes=30),
                "database_now": now,
            }
        ),
        _Result({"status": "pending"}),
        _Result(),
    )
    repository._insert_manual_payment = AsyncMock()  # type: ignore[method-assign]
    repository._insert_notification_outbox = AsyncMock(return_value="outbox-1")
    repository._get_booking_action_request_row = AsyncMock(  # type: ignore[method-assign]
        return_value={"id": "request-1", "status": "resolved"}
    )
    repository.get_booking = AsyncMock(return_value={"id": "booking-1"})

    result = await repository.respond_booking_action_request(
        "owner-1", "request-1", decision, None, payment_method=method
    )

    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    # Nothing writes payment_status directly any more: money moves only as a ledger row.
    assert not any("set payment_status" in sql for sql in statements)
    if expected_write:
        # The salon's stated method is recorded, not a hardcoded 'cash'.
        repository._insert_manual_payment.assert_awaited_once_with(
            booking_id="booking-1", actor_id="owner-1", method=method
        )
    else:
        repository._insert_manual_payment.assert_not_awaited()
    resolved_write = next(
        call for call in session.execute.await_args_list
        if "decision_reason = :reason, resolved_by" in str(call.args[0])
    )
    assert resolved_write.args[1]["reason"]
    assert result["status"] == "resolved"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "reason", "expected_cancel"),
    [("approve", None, True), ("decline", "Keep the booking", False)],
)
async def test_cancellation_owner_decision_releases_slot_only_when_approved(
    decision: str, reason: str | None, expected_cancel: bool
) -> None:
    now = datetime.now(UTC)
    repository, session = _repository(
        _Result(
            {
                "id": "request-1",
                "kind": "cancellation",
                "request_status": "pending",
                "reason": "Change of plans",
                "booking_id": "booking-1",
                "booking_status": "confirmed",
                "payment_status": "unpaid",
                "customer_id": "customer-1",
                "end_datetime": now + timedelta(minutes=30),
                "database_now": now,
            }
        ),
        _Result({"status": "pending"}),
        *([_Result(), _Result()] if expected_cancel else []),
        _Result(),
    )
    repository._insert_notification_outbox = AsyncMock(return_value="outbox-1")
    repository._get_booking_action_request_row = AsyncMock(
        return_value={"id": "request-1", "status": "resolved"}
    )
    repository.get_booking = AsyncMock(return_value={"id": "booking-1"})

    await repository.respond_booking_action_request(
        "owner-1", "request-1", decision, reason
    )

    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert any("set status = 'cancelled'" in sql for sql in statements) is expected_cancel
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_closure_rejects_changed_impact_set() -> None:
    repository, session = _repository(_Result(scalar=True))
    repository.get_owner_salon = AsyncMock(return_value={"id": "salon-1"})
    repository._closure_affected_bookings = AsyncMock(
        return_value=[{"booking_id": "booking-new"}]
    )

    with pytest.raises(ConflictError, match="changed after preview"):
        await repository.apply_closure(
            "owner-1",
            {
                "kind": "holiday",
                "holiday_date": datetime.now(UTC).date(),
                "reason": "Emergency",
                "affected_booking_ids": ["booking-old"],
            },
        )

    session.commit.assert_not_awaited()
