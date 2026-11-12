"""ERR-02: booking creation maps only database business errors to 4xx.

Business errors from the booking SQL functions arrive as SQLSTATE P0001 and keep their
codes. Any other failure (lost connection, pool or statement timeout) must be re-raised so
the global handler returns 500 instead of a misleading 409 ``slot_unavailable``.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayAtSalonBlockedError,
    PayAtSalonDailyLimitError,
    SalonClosedError,
    SalonNotAcceptingBookingsError,
    SlotUnavailableError,
    ValidationError,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.unit.db_errors import business_error, infrastructure_error

VALUES = {
    "salon_id": "00000000-0000-0000-0000-000000000001", "staff_id": "s", "service_ids": [],
    "start_datetime": None, "customer_name": "A", "customer_phone": None, "source": "app",
    "notes": None,
}


def _session(error: BaseException) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = error
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    ["Selected slot is no longer available", "That slot was just taken. Please pick another time."],
)
async def test_business_slot_error_maps_to_slot_unavailable(message):
    session = _session(business_error(message))
    with pytest.raises(SlotUnavailableError) as exc:
        await PlatformRepository(session).create_booking(VALUES)
    assert exc.value.code == "slot_unavailable"
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_business_not_accepting_error_keeps_its_code():
    session = _session(business_error("salon_not_accepting_bookings"))
    with pytest.raises(SalonNotAcceptingBookingsError):
        await PlatformRepository(session).create_booking(VALUES)
    session.rollback.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "error"),
    [
        ("salon_not_accepting_bookings", SalonNotAcceptingBookingsError),
        ("pay_at_salon_temporarily_blocked", PayAtSalonBlockedError),
        ("pay_at_salon_daily_limit", PayAtSalonDailyLimitError),
    ],
)
async def test_checkout_guard_trigger_errors_keep_their_codes(message, error):
    # guard_booking_checkout() raises these with errcode 23514 (migration 0035).
    session = _session(business_error(message, sqlstate="23514"))
    with pytest.raises(error):
        await PlatformRepository(session).create_booking(VALUES)
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_other_integrity_error_is_re_raised():
    # A unique violation is not a deliberate rejection, even with a business-looking message.
    session = _session(infrastructure_error("duplicate key: slot", sqlstate="23505"))
    with pytest.raises(DBAPIError):
        await PlatformRepository(session).create_booking(VALUES)


@pytest.mark.asyncio
async def test_unrecognised_business_error_stays_a_conflict_and_is_logged(caplog):
    session = _session(business_error("some_new_unmapped_rule"))
    with caplog.at_level("WARNING"), pytest.raises(ConflictError) as exc:
        await PlatformRepository(session).create_booking({**VALUES, "actor_id": "actor-1"})
    assert exc.value.code == "conflict"
    assert "some_new_unmapped_rule" in caplog.text
    assert "actor-1" in caplog.text
    assert "select create_booking" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "error", "code"),
    [
        ("Salon is closed on this date", SalonClosedError, "salon_closed"),
        ("No valid services selected", ValidationError, "validation_error"),
        ("Salon not found or inactive", NotFoundError, "not_found"),
    ],
)
async def test_closed_salon_and_catalog_errors_keep_specific_codes(message, error, code):
    session = _session(business_error(message))
    with pytest.raises(error) as exc:
        await PlatformRepository(session).create_booking(VALUES)
    assert exc.value.code == code


@pytest.mark.asyncio
async def test_customer_text_in_the_sql_cannot_spoof_a_rule():
    # str(exc) embeds the SQL and bound parameters; only the Postgres message may be matched.
    error = business_error("some_new_unmapped_rule")
    error.params = {"notes": "slot available break_conflict"}
    session = _session(error)
    with pytest.raises(ConflictError) as exc:
        await PlatformRepository(session).create_booking(VALUES)
    assert exc.value.code == "conflict"


@pytest.mark.asyncio
async def test_infrastructure_error_is_not_reported_as_slot_conflict():
    # The message contains "available", which the old substring match turned into 409.
    session = _session(infrastructure_error("connection is not available", sqlstate="08006"))
    with pytest.raises(DBAPIError):
        await PlatformRepository(session).create_booking(VALUES)
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_database_error_without_sqlstate_is_re_raised():
    session = _session(infrastructure_error("pool timeout: slot not available"))
    with pytest.raises(DBAPIError):
        await PlatformRepository(session).create_booking(VALUES)


@pytest.mark.asyncio
async def test_timeout_is_re_raised():
    session = _session(TimeoutError("statement timed out"))
    with pytest.raises(TimeoutError):
        await PlatformRepository(session).create_booking(VALUES)
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_actor_is_re_armed_right_before_the_booking_sql_runs():
    # The age check rolls back (customers only), which drops the transaction-local auth.uid();
    # the booking row would then have no customer_id and break bookings_customer_or_walkin_check.
    statements: list[str] = []

    async def record(statement, params=None):
        statements.append(str(statement))
        if "create_booking" in str(statement):
            raise business_error("stop after the booking call")

    session = AsyncMock()
    session.execute.side_effect = record
    with pytest.raises(ConflictError):
        await PlatformRepository(session).create_booking({**VALUES, "actor_id": "actor-1"})
    create_at = next(i for i, sql in enumerate(statements) if "create_booking" in sql)
    assert any("request.jwt.claim.sub" in sql for sql in statements[:create_at])
