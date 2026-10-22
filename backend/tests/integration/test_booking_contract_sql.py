"""Real PostgreSQL: booking source, server-owned pricing, overlap and customer-isolated idempotency.

Runs the actual create_booking function and the payment_idempotency_keys table. Opt-in through
MIGRATION_TEST_DB (a disposable local PostgreSQL admin URL); reuses the seeded fixture from
test_checkout_safety_sql. Never touches any other database.
"""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.use_cases.platform import BookingUseCases
from app.application.use_cases.walkin import WalkInUseCases
from app.core.exceptions import AppError, OnlinePaymentUnavailableError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.integration.test_checkout_safety_sql import safety, safety_db  # noqa: F401  (fixtures)
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


def _customer(profile_id: str) -> Profile:
    return Profile(id=profile_id, role=Role.customer, full_name="Test", email=profile_id + "@example.test",
                   phone="+919876543210", phone_verified=True, avatar_url=None, is_active=True)


async def _second_customer(env) -> str:
    customer = str(uuid4())
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(text("insert into auth.users(id,email) values(:id,:e)"),
                              {"id": customer, "e": customer + "@example.test"})
        await session.execute(text("insert into profiles(id,role,email) values(:id,'customer',:e)"),
                              {"id": customer, "e": customer + "@example.test"})
        await session.commit()
    return customer


def _body(fixture, **extra):
    return {"salon_id": fixture["salon"], "staff_id": fixture["staff"], "service_ids": [fixture["service"]],
            "start_datetime": fixture["start"], "customer_name": "Contract test", "customer_phone": None,
            "notes": None, "payment_preference": None, **extra}


async def _qr_book(env, fixture, customer_id, qr_token, key=None, **extra):
    async with env.session() as session:
        await set_actor_context(session, customer_id)
        try:
            return await WalkInUseCases(PlatformRepository(session)).create_walkin_booking(
                _customer(customer_id), qr_token, {**_body(fixture, **extra), "source": "app", "_idempotency_key": key})
        except AppError as exc:
            return exc


async def _direct_book(env, fixture, customer_id, key=None, **extra):
    async with env.session() as session:
        await set_actor_context(session, customer_id)
        try:
            return await BookingUseCases(PlatformRepository(session)).create_booking(
                _customer(customer_id), {**_body(fixture, **extra), "source": "app", "_idempotency_key": key})
        except AppError as exc:
            return exc


async def _token(env, fixture) -> str:
    return (await env.sql("select qr_token from salons where id=:id", id=fixture["salon"]))[0]["qr_token"]


async def _count(env, salon) -> int:
    return (await env.sql("select count(*) as n from bookings where salon_id=:id", id=salon))[0]["n"]


async def test_qr_booking_persists_qr_walkin_and_ignores_client_money_and_time(safety):  # noqa: F811
    f = await safety.seed()
    token = await _token(safety, f)
    booking = await _qr_book(safety, f, f["customer"], token, total_price=1, price=1,
                             end_datetime=f["start"] + timedelta(minutes=1), total_duration_minutes=1)
    assert isinstance(booking, dict), booking
    row = (await safety.sql("select source::text as source, total_price, total_duration_minutes, "
                            "start_datetime, end_datetime from bookings where id=:id", id=booking["id"]))[0]
    assert row["source"] == "qr_walkin"
    assert float(row["total_price"]) == 250.0 and row["total_duration_minutes"] == 30
    assert row["end_datetime"] - row["start_datetime"] == timedelta(minutes=30)


async def test_direct_booking_persists_source_app(safety):  # noqa: F811
    f = await safety.seed()
    booking = await _direct_book(safety, f, f["customer"])
    assert isinstance(booking, dict), booking
    assert (await safety.sql("select source::text as s from bookings where id=:id", id=booking["id"]))[0]["s"] == "app"


async def test_direct_route_cannot_claim_qr_walkin(safety):  # noqa: F811
    f = await safety.seed()
    async with safety.session() as session:
        await set_actor_context(session, f["customer"])
        with pytest.raises(AppError) as raised:
            await BookingUseCases(PlatformRepository(session)).create_booking(
                _customer(f["customer"]), {**_body(f), "source": "qr_walkin"})
    assert raised.value.code == "booking_source_not_allowed"
    assert await _count(safety, f["salon"]) == 0


async def test_overlapping_attempts_give_one_booking_and_one_slot_unavailable(safety):  # noqa: F811
    f = await safety.seed()
    other = await _second_customer(safety)
    results = await asyncio.gather(_direct_book(safety, f, f["customer"]), _direct_book(safety, f, other))
    winners = [r for r in results if isinstance(r, dict)]
    losers = [r for r in results if isinstance(r, AppError)]
    assert len(winners) == 1 and len(losers) == 1
    assert losers[0].code == "slot_unavailable" and losers[0].status_code == 409
    assert await _count(safety, f["salon"]) == 1


async def test_same_customer_same_key_same_request_replays_one_booking(safety):  # noqa: F811
    f = await safety.seed()
    token = await _token(safety, f)
    first = await _qr_book(safety, f, f["customer"], token, key="qr-key-same-1")
    again = await _qr_book(safety, f, f["customer"], token, key="qr-key-same-1")
    assert first["id"] == again["id"] and again.get("_idempotency_replay") is True
    assert await _count(safety, f["salon"]) == 1


async def test_two_customers_with_the_same_key_never_share_a_booking(safety):  # noqa: F811
    f = await safety.seed()
    token = await _token(safety, f)
    other = await _second_customer(safety)
    first = await _qr_book(safety, f, f["customer"], token, key="shared-key-1")
    second = await _qr_book(safety, f, other, token, key="shared-key-1")
    assert isinstance(first, dict)
    # The second customer asks for the same slot: it is a fresh attempt (slot conflict), never a replay.
    assert isinstance(second, AppError) and second.code == "slot_unavailable"
    assert "_idempotency_replay" not in (second if isinstance(second, dict) else {})
    later = {**f, "start": f["start"] + timedelta(hours=2)}
    third = await _qr_book(safety, later, other, token, key="shared-key-1")
    assert isinstance(third, dict) and third["id"] != first["id"] and third["customer_id"] == other
    assert await _count(safety, f["salon"]) == 2


async def test_same_key_with_a_different_booking_is_a_422(safety):  # noqa: F811
    f = await safety.seed()
    token = await _token(safety, f)
    assert isinstance(await _qr_book(safety, f, f["customer"], token, key="reuse-key-1"), dict)
    changed = await _qr_book(safety, {**f, "start": f["start"] + timedelta(hours=1)}, f["customer"], token,
                             key="reuse-key-1")
    assert isinstance(changed, AppError)
    assert (changed.status_code, changed.code) == (422, "idempotency_key_reused")
    assert await _count(safety, f["salon"]) == 1


async def test_online_payment_is_refused_without_any_side_effect(safety):  # noqa: F811
    f = await safety.seed()
    token = await _token(safety, f)
    for call in (_direct_book(safety, f, f["customer"], payment_preference="pay_full", key="online-key-1"),
                 _qr_book(safety, f, f["customer"], token, payment_preference="pay_advance", key="online-key-2")):
        result = await call
        assert isinstance(result, OnlinePaymentUnavailableError)
        assert (result.status_code, result.code) == (422, "online_payment_unavailable")
    assert await _count(safety, f["salon"]) == 0
    keys = await safety.sql("select count(*) as n from payment_idempotency_keys where actor_id=:id", id=f["customer"])
    assert keys[0]["n"] == 0
    assert isinstance(await _direct_book(safety, f, f["customer"], payment_preference="pay_at_salon"), dict)
