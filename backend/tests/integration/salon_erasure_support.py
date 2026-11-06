"""Shared fixtures and seed helpers for the admin salon erasure suites (0058)."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

SQL_DIR = Path(__file__).parents[2] / "migrations/sql"
LAST_PREPARED = 62


@pytest.fixture(scope="module")
def prepared_db(request):
    name = "salon_erasure_" + uuid4().hex
    asyncio.run(_build(name))
    url = make_url(TEST_DB).set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    async def install():
        environment = SafetyEnv(url)
        try:
            await environment.sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role")
            for number in range(38, getattr(request, "param", LAST_PREPARED) + 1):
                files = list(SQL_DIR.glob(f"{number:04d}_*.sql"))
                assert len(files) == 1, number
                async with environment.session() as session:
                    for statement in files[0].read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                    await session.commit()
        finally:
            await environment.engine.dispose()

    try:
        asyncio.run(install())
        yield url
    finally:
        asyncio.run(_drop(name))


@pytest.fixture
async def env(prepared_db):
    environment = SafetyEnv(prepared_db)
    yield environment
    await environment.engine.dispose()


async def seed_money(env, f):
    """A booking with a payment and audit trail, a paid payout with its proof, and cash-book rows."""
    booking = await env.book(f)
    assert isinstance(booking, dict), booking
    assert isinstance(await env.collect(f, booking, key="collect-" + uuid4().hex), dict)
    request = (await env.sql(
        """insert into salon_payout_requests(salon_id, amount_paise, scheduled_for, idempotency_key, request_hash)
           values(:s, 10000, current_date, :k, repeat('a', 64)) returning id""",
        s=f["salon"], k="payout-" + uuid4().hex))[0]["id"]
    proof = (await env.sql(
        """insert into payout_proofs(mime_type, size_bytes, sha256, content)
           values('application/pdf', 3, repeat('b', 64), '\\x010203'::bytea) returning id"""))[0]["id"]
    utr = "UTR-" + uuid4().hex
    await env.sql(
        """insert into salon_payout_payments(payout_id, reference, method, paid_at, amount_paid_paise, proof_id)
           values(:p, :utr, 'upi', now(), 10000, :proof)""", p=request, proof=proof, utr=utr)
    await env.sql("update salon_payout_requests set status='paid', reference=:utr, processed_at=now() where id=:p", p=request, utr=utr)
    await env.sql("insert into payout_audit(payout_id, action) values(:p, 'pay')", p=request)
    first = (await env.sql(
        """insert into salon_expenses(salon_id, entry_type, category, amount_paise, payment_method, occurred_at,
                title, idempotency_key, request_hash)
           values(:s, 'expense', 'rent', 5000, 'cash', timestamptz '2026-11-01 10:00+00', 'Rent', :k, repeat('c', 64)) returning id""",
        s=f["salon"], k="e1-" + uuid4().hex))[0]["id"]
    await env.sql(
        """insert into salon_expenses(salon_id, entry_type, category, amount_paise, payment_method, occurred_at,
                title, idempotency_key, request_hash, reverses_id)
           values(:s, 'reversal', 'rent', 5000, 'cash', timestamptz '2026-11-01 10:00+00', 'Rent', :k, repeat('d', 64), :r)""",
        s=f["salon"], k="e2-" + uuid4().hex, r=first)
    ticket = (await env.sql(
        """insert into support_tickets(salon_id, customer_id, subject) values(:s, :c, 'Help') returning id""",
        s=f["salon"], c=f["customer"]))[0]["id"]
    await env.sql("insert into support_messages(ticket_id, body) values(:t, 'hello')", t=ticket)
    return {"booking": booking, "request": request, "proof": proof}


async def count(env, table, where="true", **params):
    return (await env.sql(f"select count(*) as n from {table} where {where}", **params))[0]["n"]
