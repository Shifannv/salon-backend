"""Arrival warning: barber warns a late customer, the customer replies, the clock auto no-shows."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError as SchemaError

from app.api.v1.schemas.booking import NoShowWarningReplyRequest, NoShowWarningRequest
from app.application.use_cases import booking_use_cases
from app.application.use_cases.platform import BookingUseCases
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.domain.entities.profile import Role
from app.domain.notification_audience import audience_for
from app.domain.services.booking_finance_policy import validate_no_show
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.conftest import make_mock_repo, make_owner, make_profile

NOW = datetime(2026, 11, 12, 10, tzinfo=UTC)
START = NOW - timedelta(minutes=2)


class _R:
    """Just enough of a SQLAlchemy result for the queries the mixin runs."""

    def __init__(self, row=None, rows=None, scalar=None):
        self._row, self._rows, self._scalar = row, rows or [], scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self._row

    def one(self):
        return self._row

    def all(self):
        return self._rows

    def first(self):
        return self._row

    def scalar_one(self):
        return self._scalar


def _repo(*results: _R) -> tuple[PlatformRepository, MagicMock]:
    session = MagicMock()
    session.execute = AsyncMock(side_effect=list(results))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    repo = PlatformRepository(session)
    repo._insert_notification_outbox = AsyncMock(side_effect=["outbox-1", "outbox-2", "outbox-3"])
    repo.get_booking = AsyncMock(return_value={"id": "b1", "customer_name": "Asha"})
    repo.begin_booking_operation = AsyncMock(return_value=None)
    repo.finish_booking_operation = AsyncMock()
    return repo, session


def _booking(**over):
    base = {
        "id": "b1", "status": "confirmed", "customer_id": "cust-1", "staff_id": "staff-1",
        "salon_id": "salon-1", "start_datetime": START, "database_now": NOW,
    }
    return {**base, **over}


# ── policy and schema ────────────────────────────────────────────────────────

def test_warning_deadline_lifts_the_ten_minute_grace():
    start = NOW - timedelta(minutes=6)
    with pytest.raises(ValueError, match="no_show_grace_period"):
        validate_no_show(start, NOW, "Did not arrive")
    with pytest.raises(ValueError, match="no_show_grace_period"):
        validate_no_show(start, NOW, "Did not arrive", warning_deadline=NOW + timedelta(seconds=1))
    assert validate_no_show(start, NOW, " Did not arrive ", warning_deadline=NOW) == "Did not arrive"


def test_warning_deadline_still_requires_a_reason():
    with pytest.raises(ValueError, match="no_show_reason_required"):
        validate_no_show(NOW, NOW, "  ", warning_deadline=NOW)


@pytest.mark.parametrize("minutes", [5, 10, 15])
def test_only_offered_wait_times_are_accepted(minutes):
    assert NoShowWarningRequest(grace_minutes=minutes).grace_minutes == minutes


@pytest.mark.parametrize("minutes", [0, 1, 7, 20, 60])
def test_other_wait_times_are_rejected(minutes):
    with pytest.raises(SchemaError):
        NoShowWarningRequest(grace_minutes=minutes)


def test_on_the_way_reply_cannot_carry_a_reason():
    NoShowWarningReplyRequest(response="not_coming", reason_code="personal_emergency")
    with pytest.raises(SchemaError):
        NoShowWarningReplyRequest(response="on_the_way", reason_text="traffic")


def test_reply_text_is_one_clean_line_and_cannot_fake_a_no_show():
    reply = NoShowWarningReplyRequest(response="not_coming", reason_text="  stuck\n in   traffic ")
    assert reply.reason_text == "stuck in traffic"
    assert NoShowWarningReplyRequest(response="not_coming", reason_text="   ").reason_text is None
    with pytest.raises(SchemaError):
        NoShowWarningReplyRequest(response="not_coming", reason_text="Customer no-show: oops")


def test_notification_audiences_route_to_the_right_app():
    assert audience_for("booking_no_show_warning") == "customer"
    assert audience_for("booking_no_show_warning_withdrawn") == "customer"
    for kind in ("booking_customer_on_the_way", "booking_customer_not_coming", "booking_no_show_auto"):
        assert audience_for(kind) == "owner"


# ── create ────────────────────────────────────────────────────────────────────

async def test_warning_opens_and_notifies_the_customer():
    repo, session = _repo(_R(_booking()), _R({"total": 0, "open": 0}), _R(scalar=NOW + timedelta(minutes=10)))
    booking = await repo.create_no_show_warning("owner-1", "b1", 10, "idem-key-1")
    assert booking["_outbox_ids"] == ["outbox-1"]
    sent = repo._insert_notification_outbox.await_args.kwargs
    assert sent["user_id"] == "cust-1" and sent["notification_type"] == "booking_no_show_warning"
    assert sent["data"]["grace_minutes"] == 10
    repo.finish_booking_operation.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("row", "error"),
    [
        (None, NotFoundError),
        (_booking(status="pending"), ConflictError),
        (_booking(status="checked_in"), ConflictError),
        (_booking(customer_id=None), ValidationError),
        (_booking(start_datetime=NOW + timedelta(minutes=1)), ValidationError),
    ],
)
async def test_warning_is_refused_when_the_booking_cannot_be_warned(row, error):
    repo, session = _repo(_R(row))
    with pytest.raises(error):
        await repo.create_no_show_warning("owner-1", "b1", 5, None)
    session.commit.assert_not_awaited()
    repo._insert_notification_outbox.assert_not_awaited()


async def test_second_warning_on_the_same_booking_is_refused():
    repo, session = _repo(_R(_booking()), _R({"total": 1, "open": 1}))
    with pytest.raises(ConflictError, match="already been warned"):
        await repo.create_no_show_warning("owner-1", "b1", 5, None)
    session.commit.assert_not_awaited()


async def test_third_warning_on_one_booking_is_refused():
    repo, session = _repo(_R(_booking()), _R({"total": 2, "open": 0}))
    with pytest.raises(ConflictError, match="twice"):
        await repo.create_no_show_warning("owner-1", "b1", 5, None)
    session.commit.assert_not_awaited()


async def test_replayed_warning_returns_the_stored_booking_without_new_work():
    repo, session = _repo()
    repo.begin_booking_operation = AsyncMock(return_value={"id": "b1"})
    booking = await repo.create_no_show_warning("owner-1", "b1", 5, "idem-key-1")
    assert booking["_idempotency_replay"] is True
    session.execute.assert_not_awaited()


# ── withdraw ──────────────────────────────────────────────────────────────────

async def test_withdrawing_tells_the_customer_the_booking_is_still_on():
    repo, session = _repo(_R({"id": "b1", "customer_id": "cust-1"}), _R(row=("w1",)))
    booking = await repo.withdraw_no_show_warning("owner-1", "b1")
    assert booking["_outbox_ids"] == ["outbox-1"]
    assert repo._insert_notification_outbox.await_args.kwargs["notification_type"] == "booking_no_show_warning_withdrawn"
    session.commit.assert_awaited_once()


async def test_withdrawing_without_an_open_warning_is_not_found():
    repo, session = _repo(_R({"id": "b1", "customer_id": "cust-1"}), _R(None))
    with pytest.raises(NotFoundError):
        await repo.withdraw_no_show_warning("owner-1", "b1")
    session.commit.assert_not_awaited()


# ── customer reply ────────────────────────────────────────────────────────────

def _reply_repo(*, status="confirmed", warning=None, recipients=("owner-1", "staff-9")):
    booking = {"id": "b1", "status": status, "customer_name": "Asha", "staff_id": "staff-1", "owner_id": "owner-1"}
    warning = {"id": "w1", "customer_response": None, "expired": False} if warning is None else warning
    results = [_R(booking), _R(warning) if warning else _R(None)]
    repo, session = _repo(*results, *[_R() for _ in range(5)])
    repo._booking_staff_recipients = AsyncMock(return_value=list(recipients))
    return repo, session


async def test_on_the_way_notifies_salon_and_keeps_the_booking():
    repo, session = _reply_repo()
    booking = await repo.respond_to_no_show_warning("cust-1", "b1", "on_the_way", None, None, None)
    types = [call.kwargs["notification_type"] for call in repo._insert_notification_outbox.await_args_list]
    assert types == ["booking_customer_on_the_way"] * 2
    assert booking["_outbox_ids"] == ["outbox-1", "outbox-2"]
    statements = " ".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "status = 'cancelled'" not in statements
    session.commit.assert_awaited_once()


async def test_repeating_on_the_way_does_not_notify_again():
    repo, _ = _reply_repo(warning={"id": "w1", "customer_response": "on_the_way", "expired": False})
    await repo.respond_to_no_show_warning("cust-1", "b1", "on_the_way", None, None, None)
    repo._insert_notification_outbox.assert_not_awaited()


async def test_not_coming_cancels_resolves_and_notifies_salon():
    repo, session = _reply_repo()
    await repo.respond_to_no_show_warning("cust-1", "b1", "not_coming", "Personal emergency", "personal_emergency", None)
    statements = " ".join(str(call.args[0]) for call in session.execute.await_args_list)
    assert "booking_cancel_origin" in statements and "status = 'cancelled'" in statements
    assert "resolution = 'customer_cancelled'" in statements
    kinds = {call.kwargs["notification_type"] for call in repo._insert_notification_outbox.await_args_list}
    assert kinds == {"booking_customer_not_coming"}
    session.commit.assert_awaited_once()


async def test_reply_after_the_deadline_is_refused():
    repo, session = _reply_repo(warning={"id": "w1", "customer_response": None, "expired": True})
    with pytest.raises(ConflictError, match="closed"):
        await repo.respond_to_no_show_warning("cust-1", "b1", "on_the_way", None, None, None)
    session.commit.assert_not_awaited()


async def test_reply_without_an_open_warning_is_refused():
    repo, _ = _repo(_R({"id": "b1", "status": "confirmed", "customer_name": "A", "staff_id": "s", "owner_id": "o"}), _R(None))
    with pytest.raises(ConflictError, match="no open warning"):
        await repo.respond_to_no_show_warning("cust-1", "b1", "on_the_way", None, None, None)


async def test_another_customer_cannot_reply():
    repo, _ = _repo(_R(None))
    with pytest.raises(NotFoundError):
        await repo.respond_to_no_show_warning("stranger", "b1", "not_coming", "x", None, None)


# ── expiry ────────────────────────────────────────────────────────────────────

async def test_expiry_marks_each_due_booking_no_show_and_tells_the_salon():
    due = [{"warning_id": "w1", "booking_id": "b1", "owner_id": "owner-1"}]
    repo, _ = _repo(_R(rows=due))
    repo.update_booking_status = AsyncMock(return_value={"customer_name": "Asha"})
    repo._notify_staff_of_auto_no_show = AsyncMock()
    assert await repo.expire_no_show_warnings() == 1
    args = repo.update_booking_status.await_args
    assert args.args == ("owner-1", "b1", "no_show")
    assert args.kwargs["cancellation_reason"].startswith("Customer no-show")
    assert args.kwargs["only_unanswered_warning"] is True
    repo._notify_staff_of_auto_no_show.assert_awaited_once_with("b1", "Asha")


async def test_expiry_closes_a_stale_warning_instead_of_retrying_forever():
    due = [{"warning_id": "w1", "booking_id": "b1", "owner_id": "owner-1"}]
    repo, _ = _repo(_R(rows=due))
    repo.update_booking_status = AsyncMock(side_effect=ConflictError("Booking state changed"))
    repo._close_stale_warning = AsyncMock()
    repo._notify_staff_of_auto_no_show = AsyncMock()
    assert await repo.expire_no_show_warnings() == 0
    repo._close_stale_warning.assert_awaited_once_with("w1", "b1")
    repo._notify_staff_of_auto_no_show.assert_not_awaited()


async def test_expiry_with_nothing_due_does_nothing():
    repo, _ = _repo(_R(rows=[]))
    repo.update_booking_status = AsyncMock()
    assert await repo.expire_no_show_warnings() == 0
    repo.update_booking_status.assert_not_awaited()


# ── booking status integration ────────────────────────────────────────────────

async def test_barber_can_mark_no_show_inside_ten_minutes_once_the_warning_ran_out():
    from tests.unit.test_booking_action_repository import _repository, _Result
    from tests.unit.test_booking_attendance_policy import NOW as BOOKING_NOW

    current = {
        "id": "b1", "status": "confirmed", "customer_id": "cust-1", "customer_name": "Asha",
        "payment_status": "unpaid", "payment_preference": "pay_at_salon",
        "start_datetime": BOOKING_NOW - timedelta(minutes=6), "database_now": BOOKING_NOW,
        "warning_deadline": BOOKING_NOW - timedelta(seconds=1),
    }
    repo, session = _repository(_Result(current), *[_Result() for _ in range(6)])
    repo.get_booking = AsyncMock(return_value={**current, "status": "no_show"})
    repo._insert_notification_outbox = AsyncMock(return_value="outbox-1")
    booking = await repo.update_booking_status("owner-1", "b1", "no_show", cancellation_reason="No reply")
    assert booking["_outbox_ids"] == ["outbox-1"]
    resolved = [c for c in session.execute.await_args_list if "set resolved_at" in str(c.args[0])]
    assert resolved and resolved[0].args[1]["resolution"] == "no_show"


async def test_barber_is_still_blocked_while_the_warning_is_running():
    from tests.unit.test_booking_action_repository import _repository, _Result
    from tests.unit.test_booking_attendance_policy import NOW as BOOKING_NOW

    current = {
        "id": "b1", "status": "confirmed", "customer_id": "cust-1", "customer_name": "Asha",
        "payment_status": "unpaid", "payment_preference": "pay_at_salon",
        "start_datetime": BOOKING_NOW - timedelta(minutes=6), "database_now": BOOKING_NOW,
        "warning_deadline": BOOKING_NOW + timedelta(minutes=4),
    }
    repo, session = _repository(_Result(current), *[_Result() for _ in range(6)])
    with pytest.raises(ValidationError):
        await repo.update_booking_status("owner-1", "b1", "no_show", cancellation_reason="No reply")
    session.commit.assert_not_awaited()


# ── use cases ─────────────────────────────────────────────────────────────────

@pytest.fixture
def approved(monkeypatch):
    monkeypatch.setattr(booking_use_cases, "assert_approved_workspace", AsyncMock())


async def test_warn_use_case_schedules_push_only_for_a_fresh_warning(approved):
    repo = make_mock_repo()
    repo.create_no_show_warning = AsyncMock(return_value={"_outbox_ids": ["o1"]})
    tasks = MagicMock()
    await BookingUseCases(repo).warn_no_show(make_owner(), "b1", 5, idempotency_key="k" * 8, background_tasks=tasks)
    assert tasks.add_task.call_count == 1
    repo.create_no_show_warning.return_value = {"_outbox_ids": ["o1"], "_idempotency_replay": True}
    tasks.reset_mock()
    await BookingUseCases(repo).warn_no_show(make_owner(), "b1", 5, idempotency_key="k" * 8, background_tasks=tasks)
    tasks.add_task.assert_not_called()


async def test_not_coming_reply_builds_a_readable_reason():
    repo = make_mock_repo()
    repo.respond_to_no_show_warning = AsyncMock(return_value={"_outbox_ids": []})
    customer = make_profile(role=Role.customer)
    await BookingUseCases(repo).reply_to_no_show_warning(
        customer, "b1", "not_coming", reason_code="personal_emergency", reason_text="Family issue"
    )
    reason = repo.respond_to_no_show_warning.await_args.args[3]
    assert reason == "Personal emergency — Family issue"
    assert not reason.startswith("Customer no-show")


async def test_staff_cannot_answer_for_the_customer():
    repo = make_mock_repo()
    with pytest.raises(ForbiddenError):
        await BookingUseCases(repo).reply_to_no_show_warning(
            make_profile(role=Role.staff), "b1", "on_the_way"
        )


async def test_ten_minute_floor_sets_the_deadline_and_the_message_states_the_real_time_left():
    repo, session = _repo(_R(_booking()), _R({"total": 0, "open": 0}), _R(scalar=NOW + timedelta(minutes=8)))
    await repo.create_no_show_warning("owner-1", "b1", 5, None)
    insert_sql = str(session.execute.await_args_list[2].args[0])
    assert "greatest(" in insert_sql and "interval '10 minutes'" in insert_sql
    assert session.execute.await_args_list[2].args[1]["start"] == START
    body = repo._insert_notification_outbox.await_args.kwargs["body"]
    assert "8 minutes" in body and "5 minutes" not in body


async def test_delay_tells_the_delayed_customer_only_when_asked(approved):
    end = NOW + timedelta(minutes=30)
    repo = make_mock_repo()
    repo.get_booking = AsyncMock(return_value={**_booking(), "end_datetime": end, "customer_id": "cust-1"})
    repo.delay_booking = AsyncMock(return_value={"id": "b1", "customer_id": "cust-1"})
    use_cases = BookingUseCases(repo)
    tasks = MagicMock()
    await use_cases.delay(
        make_owner(), "b1", end + timedelta(minutes=15), False, tasks, notify_booking_customer=True
    )
    task = tasks.add_task.call_args
    assert task.args[1:4] == ("cust-1", "b1", "booking_delayed")
    assert "15 minutes" in task.args[5] and "apologise" in task.args[5]

    tasks.reset_mock()
    await use_cases.delay(make_owner(), "b1", end + timedelta(minutes=15), False, tasks)
    tasks.add_task.assert_not_called()
