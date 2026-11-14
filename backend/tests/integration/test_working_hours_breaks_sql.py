"""Real PostgreSQL: salon and staff break windows in availability and booking creation.

Only uses MIGRATION_TEST_DB, creates a uniquely named local disposable database.
"""

import asyncio
import json
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.exceptions import AppError, BreakConflictError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.integration.salon_erasure_support import prepared_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = [
    pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL"),
    # Every migration through 0066, so the visit functions and the 60-day window are real.
    pytest.mark.parametrize("prepared_db", [66], indirect=True, scope="module"),
]

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
LUNCH = {"id": "lunch", "start": "13:00", "end": "14:00"}
TEA = {"id": "tea", "start": "16:30", "end": "17:00"}
IST = ZoneInfo("Asia/Kolkata")
LUNCH_START, LUNCH_END = time(13, 0), time(14, 0)


def hours(breaks=None):
    day = {"open": "09:00", "close": "18:00"}
    if breaks:
        day["breaks"] = breaks
    return {name: dict(day) for name in DAYS}


async def _install_breaks(url: str) -> None:
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    migrations = Path(__file__).parents[2] / "migrations"
    try:
        async with engine.begin() as connection:
            source = migrations / "sql" / "0067_working_hours_breaks.sql"
            for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
                if statement.strip():
                    await connection.execute(text(statement))

            # Recreate the observed production drift: the revision history is advanced, but
            # the break helper is absent and the segmented conflict function is stale.
            await connection.execute(text(
                "DROP FUNCTION public.staff_break_overlaps(uuid, timestamptz, timestamptz)"
            ))
            await connection.execute(text("""
                CREATE OR REPLACE FUNCTION public.visit_break_conflict(
                    p_start timestamptz, p_segments jsonb
                ) RETURNS boolean LANGUAGE sql STABLE
                SET search_path = pg_catalog, public AS $fn$ SELECT false $fn$;
            """))

            repair = migrations / "sql" / "0071_restore_working_hours_break_functions.sql"
            for statement in repair.read_text(encoding="utf-8").split("\n-- statement --\n"):
                if statement.strip():
                    await connection.execute(text(statement))
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def breaks_db(prepared_db):  # noqa: F811
    asyncio.run(_install_breaks(prepared_db))
    return prepared_db


@pytest.fixture
async def env(breaks_db):
    safety = SafetyEnv(breaks_db)
    yield safety
    await safety.engine.dispose()


async def _configure(env, fixture, *, salon=None, staff=None, duration=None):
    await env.sql(
        "update salons set working_hours = cast(:h as jsonb) where id = :id",
        h=json.dumps(hours(salon)), id=fixture["salon"],
    )
    if staff is not None:
        await env.sql(
            "update staff set working_hours = cast(:h as jsonb) where id = :id",
            h=json.dumps(hours(staff)), id=fixture["staff"],
        )
    if duration is not None:
        await env.sql("update services set duration_minutes = :d where id = :id", d=duration, id=fixture["service"])


async def _slots(env, fixture):
    async with env.session() as session:
        repo = PlatformRepository(session)
        return await repo.get_available_slots(fixture["staff"], fixture["start"].date(), [fixture["service"]])


async def _breaks(env, fixture):
    async with env.session() as session:
        return await PlatformRepository(session).get_break_windows(fixture["staff"], fixture["start"].date())


def _labels(slots):
    return {row["time"] for row in slots}


def _local(slot):
    return slot["slot_start"].astimezone(IST), slot["slot_end"].astimezone(IST)


async def test_get_available_slots_excludes_salon_breaks(env):
    f = await env.seed()
    await _configure(env, f, salon=[LUNCH])
    times = _labels(await _slots(env, f))
    assert {"01:00 PM", "01:30 PM"}.isdisjoint(times)
    assert {"12:30 PM", "02:00 PM"} <= times


async def test_get_available_slots_excludes_staff_multiple_breaks(env):
    f = await env.seed()
    await _configure(env, f, staff=[LUNCH, TEA])
    times = _labels(await _slots(env, f))
    assert {"01:00 PM", "01:30 PM", "04:30 PM"}.isdisjoint(times)
    assert {"12:30 PM", "02:00 PM", "04:00 PM", "05:00 PM"} <= times
    assert await _breaks(env, f) == [
        {"start": "01:00 PM", "end": "02:00 PM", "reason": "Break"},
        {"start": "04:30 PM", "end": "05:00 PM", "reason": "Break"},
    ]


async def test_salon_break_applies_when_staff_has_own_hours_without_breaks(env):
    f = await env.seed()
    await _configure(env, f, salon=[LUNCH], staff=[])
    assert {"01:00 PM", "01:30 PM"}.isdisjoint(_labels(await _slots(env, f)))


async def test_create_booking_during_break_is_a_break_conflict(env):
    f = await env.seed()
    await _configure(env, f, salon=[LUNCH])
    for delta in (180, 195):
        result = await env.book(f, delta=delta)
        assert isinstance(result, BreakConflictError)
        assert result.status_code == 409 and result.code == "break_conflict"
    assert (await env.sql("select count(*) as n from bookings where salon_id = :id", id=f["salon"]))[0]["n"] == 0


async def test_segmented_booking_during_break_is_a_break_conflict(env):
    f = await env.seed()
    await _configure(env, f, staff=[LUNCH])
    values = {
        **env.values(f, delta=195),
        "segments": [{"staff_id": f["staff"], "service_ids": [f["service"]]}],
    }
    async with env.session() as session:
        await set_actor_context(session, f["customer"])
        with pytest.raises(AppError) as raised:
            await PlatformRepository(session).create_booking(values)
    assert raised.value.code == "break_conflict"


async def test_multi_service_duration_spanning_into_break_blocked(env):
    f = await env.seed()
    await _configure(env, f, salon=[LUNCH], duration=45)
    for slot in await _slots(env, f):
        start, end = _local(slot)
        assert end.time() <= LUNCH_START or start.time() >= LUNCH_END
    result = await env.book(f, delta=150)
    assert isinstance(result, BreakConflictError)


async def test_booking_outside_breaks_still_succeeds(env):
    f = await env.seed()
    await _configure(env, f, salon=[LUNCH], staff=[TEA])
    assert isinstance(await env.book(f, delta=60), dict)


async def test_backward_compatibility_empty_breaks(env):
    f = await env.seed()
    await _configure(env, f)
    assert len(await _slots(env, f)) == 18
    assert await _breaks(env, f) == []
    await _configure(env, f, salon=[], staff=[])
    assert len(await _slots(env, f)) == 18
