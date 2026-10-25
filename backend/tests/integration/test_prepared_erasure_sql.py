"""Prepared-schema erasure, including populated retained audit tables, on local PG."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.session import set_actor_context
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

# Scope deliberately limited to the two newly introduced retained audit tables.
AUDIT_COLUMN_TREATMENT = {
    "booking_customer_changes.idempotency_key": "hashed",
    "booking_customer_changes.request": "scrubbed",
    "booking_customer_changes.previous_services": "numeric-only",
    "booking_customer_changes.committed_services": "numeric-only",
    "booking_finance_commands.idempotency_key": "hashed",
    "booking_finance_commands.request": "numeric-only",
    "booking_finance_commands.reference": "hashed",
    "booking_finance_commands.action": "machine-action",
}


@pytest.fixture(scope="module")
def prepared_erasure_db(request):
    name = "prepared_erasure_" + uuid4().hex
    asyncio.run(_build(name))
    url = make_url(TEST_DB).set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    async def install():
        env = SafetyEnv(url)
        try:
            # Explicit managed prerequisite, confined to this synthetic database.
            await env.sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role")
            for number in range(38, getattr(request, "param", 47) + 1):
                files = list((Path(__file__).parents[2] / "migrations/sql").glob(f"{number:04d}_*.sql"))
                assert len(files) == 1
                async with env.session() as session:
                    for statement in files[0].read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                    await session.commit()
        finally:
            await env.engine.dispose()

    try:
        asyncio.run(install())
        yield url
    finally:
        asyncio.run(_drop(name))


@pytest.mark.parametrize("role", ["customer", "owner"])
async def test_erasure_adapter_runs_after_removed_columns_on_prepared_head(prepared_erasure_db, role):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        unrelated = await env.seed()
        booking = await env.book(fixture)
        assert isinstance(booking, dict)
        async with env.session() as session:
            await set_actor_context(session, fixture["customer"])
            await session.execute(text("update bookings set status='cancelled', cancellation_reason='Synthetic cancellation' where id=:id"), {"id": booking["id"]})
            await session.commit()
        assert (await env.sql("""select count(*) n from information_schema.columns where table_schema='public'
            and table_name in ('salons','services') and column_name='description'"""))[0]["n"] == 0
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,:role,'processing')",
                      uid=fixture[role], role=role)
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture[role], role)
        assert not await env.sql("select id from profiles where id=:id", id=fixture[role])
        assert await env.sql("select id from profiles where id=:id", id=unrelated[role])
        retained = (await env.sql("select customer_id,total_price from bookings where id=:id", id=booking["id"]))[0]
        assert retained["total_price"] == booking["total_price"]
        if role == "customer":
            assert retained["customer_id"] is None
        else:
            shell = (await env.sql("select owner_id,is_active,name from salons where id=:id", id=fixture["salon"]))[0]
            assert shell["owner_id"] is None and not shell["is_active"] and shell["name"] == "Closed salon"
    finally:
        await env.engine.dispose()


async def seed_audits(env, fixture):
    booking = await env.book(fixture)
    assert isinstance(booking, dict)
    await env.sql("""insert into booking_customer_changes
        (booking_id,version,idempotency_key,request,old_start,new_start,old_staff_id,new_staff_id,
         previous_services,committed_services,previous_total,committed_total,fulfilment_amount)
        values(:bid,1,'private-person@example.test',cast(:request as jsonb),:start,:start,:staff,:staff,
         cast(:services as jsonb),cast(:services as jsonb),250,250,250)""",
        bid=booking["id"], start=fixture["start"], staff=fixture["staff"],
        request=json.dumps({"note": "private-person@example.test", "staff_id": fixture["staff"]}),
        services=json.dumps([{"name": "private-person@example.test", "service_id": fixture["service"],
                              "price": 250, "duration": 30}]))
    await env.sql("""insert into booking_financial_outcomes
        (booking_id,policy_version,kind,decision_at,appointment_start,captured_amount,
         customer_refund_promised,cancellation_penalty,previously_refunded,refund_due,retained_amount)
        values(:bid,'u08-2026-10-23-v1','customer_cancellation',now(),:start,250,230,20,0,230,20)""",
        bid=booking["id"], start=fixture["start"])
    await env.sql("""insert into booking_finance_commands(booking_id,idempotency_key,action,request,reference)
        values(:bid,'private-person@example.test','record_payout',cast(:request as jsonb),:reference)""",
        bid=booking["id"], reference="private-" + fixture["salon"],
        request=json.dumps({"amount": 14, "version": 1, "reference": "private-person@example.test",
                            "note": "private-person@example.test"}))
    async with env.session() as session:
        await set_actor_context(session, fixture["customer"])
        await session.execute(text("update bookings set status='cancelled' where id=:bid"), {"bid": booking["id"]})
        await session.commit()
    return booking


@pytest.mark.parametrize("role", ["customer", "owner"])
async def test_erasure_scrubs_populated_change_and_finance_audits(prepared_erasure_db, role):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture, unrelated = await env.seed(), await env.seed()
        booking, other = await seed_audits(env, fixture), await seed_audits(env, unrelated)
        before = (await env.sql("select * from booking_customer_changes where booking_id=:bid", bid=booking["id"]))[0]
        untouched = await env.sql("select * from booking_finance_commands where booking_id=:bid", bid=other["id"])
        money_before = await env.sql("select * from booking_financial_outcomes where booking_id=:bid", bid=booking["id"])
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,:role,'processing')",
                      uid=fixture[role], role=role)
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture[role], role)
        changes = (await env.sql("select * from booking_customer_changes where booking_id=:bid", bid=booking["id"]))[0]
        commands = (await env.sql("select * from booking_finance_commands where booking_id=:bid", bid=booking["id"]))[0]
        assert "private-person" not in str(changes) + str(commands)
        assert commands["reference"] != "private-" + fixture["salon"]
        assert changes["request"] == {}
        assert changes["previous_services"] == [{"price": 250, "duration": 30}]
        assert commands["request"] == {"amount": 14, "version": 1}
        assert str(changes["old_staff_id"]) != fixture["staff"]
        assert await env.sql("select * from booking_financial_outcomes where booking_id=:bid", bid=booking["id"]) == money_before
        for key in ("id", "booking_id", "version", "old_start", "new_start", "previous_total", "committed_total", "fulfilment_amount", "created_at"):
            assert changes[key] == before[key]
        assert await env.sql("select * from booking_finance_commands where booking_id=:bid", bid=other["id"]) == untouched
        # Re-running database erasure must not rehash the retained identifiers.
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture[role], role)
        assert (await env.sql("select * from booking_customer_changes where booking_id=:bid", bid=booking["id"]))[0] == changes
        assert (await env.sql("select * from booking_finance_commands where booking_id=:bid", bid=booking["id"]))[0] == commands
        # Raw pre-erasure keys/references cannot create a second financial command.
        for key, reference in (("new-command-key", "private-" + fixture["salon"]),
                               ("private-person@example.test", "new-reference")):
            with pytest.raises(DBAPIError, match="unique"):
                await env.sql("""insert into booking_finance_commands
                    (booking_id,idempotency_key,action,request,reference)
                    values(:bid,:key,'record_payout','{}',:ref)""", bid=booking["id"], key=key, ref=reference)
    finally:
        await env.engine.dispose()


async def test_audit_erasure_requires_real_processing_request_and_preserves_immutability(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        booking = await seed_audits(env, fixture)
        for status in (None, "pending", "failed", "completed"):
            if status:
                await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'customer',:status)",
                              uid=fixture["customer"], status=status)
            async with env.session() as session:
                await session.execute(text("select set_config('app.account_erasure','on',true)"))
                with pytest.raises(DBAPIError, match="verified_erasure_required"):
                    await session.execute(text("select erase_booking_audit_personal_data(:uid)"), {"uid": fixture["customer"]})
            await env.sql("delete from account_deletion_requests where user_id=:uid", uid=fixture["customer"])
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'customer','processing')", uid=fixture["customer"])
        # Even correct flags and a real request cannot authorize changing the money.
        async with env.session() as session:
            await session.execute(text("select set_config('app.account_erasure','on',true), set_config('app.booking_audit_erasure_subject',:uid,true)"), {"uid": fixture["customer"]})
            with pytest.raises(DBAPIError, match="immutable"):
                await session.execute(text("update booking_customer_changes set previous_total=0,anonymized_at=now() where booking_id=:bid"), {"bid": booking["id"]})
        for table in ("booking_customer_changes", "booking_finance_commands"):
            for operation in (f"delete from {table} where booking_id=:bid", f"truncate {table}"):
                with pytest.raises(DBAPIError, match="immutable"):
                    await env.sql(operation, bid=booking["id"])
        # A successful redaction followed by an error must roll back as one transaction.
        before = await env.sql("select * from booking_customer_changes where booking_id=:bid", bid=booking["id"])
        async with env.session() as session:
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            await session.execute(text("select erase_booking_audit_personal_data(:uid)"), {"uid": fixture["customer"]})
            await session.rollback()
        assert await env.sql("select * from booking_customer_changes where booking_id=:bid", bid=booking["id"]) == before
    finally:
        await env.engine.dispose()


@pytest.mark.parametrize("db_role", ["anon", "authenticated"])
async def test_client_roles_cannot_invoke_audit_erasure(prepared_erasure_db, db_role):
    env = SafetyEnv(prepared_erasure_db)
    try:
        async with env.session() as session:
            await session.execute(text(f"set local role {db_role}"))
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            with pytest.raises(DBAPIError, match="permission denied"):
                await session.execute(text("select erase_booking_audit_personal_data(:uid)"), {"uid": str(uuid4())})
    finally:
        await env.engine.dispose()


async def test_service_role_can_scrub_and_forged_redacted_inserts_are_rejected(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        booking = await seed_audits(env, fixture)
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'customer','processing')", uid=fixture["customer"])
        async with env.session() as session:
            await session.execute(text("set local role service_role"))
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            await session.execute(text("select erase_booking_audit_personal_data(:uid)"), {"uid": fixture["customer"]})
            await session.commit()
        assert (await env.sql("select anonymized_at from booking_customer_changes where booking_id=:bid", bid=booking["id"]))[0]["anonymized_at"] is not None
        with pytest.raises(DBAPIError, match="immutable"):
            await env.sql("""insert into booking_finance_commands
                (booking_id,idempotency_key,action,request,reference,anonymized_at)
                values(:bid,'forged-command-key','approve','{}','forged-reference',now())""", bid=booking["id"])
        for table in ("booking_customer_changes", "booking_finance_commands"):
            with pytest.raises(DBAPIError, match="immutable"):
                await env.sql(f"update {table} set request='{{}}' where booking_id=:bid", bid=booking["id"])
    finally:
        await env.engine.dispose()


async def test_redaction_drops_malformed_nested_json_instead_of_preserving_text(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        row = (await env.sql("""select public.redacted_booking_service_snapshot(cast(:snapshot as jsonb)) as snapshot,
            public.redacted_booking_audit_row('booking_finance_commands',cast(:audit as jsonb),now())->'request' as request""",
            snapshot=json.dumps([{"price": {"name": "private-person"}, "duration": "private-person"},
                                 {"price": 10, "duration": 20, "name": "private-person"}]),
            audit=json.dumps({"idempotency_key": "private-person", "reference": "private-person",
                              "request": {"amount": "private-person", "version": {"nested": "private-person"}}})))[0]
        assert row == {"snapshot": [{}, {"price": 10, "duration": 20}], "request": {}}
    finally:
        await env.engine.dispose()


async def test_retained_audit_text_columns_have_explicit_privacy_classification(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        columns = await env.sql("""select table_name || '.' || column_name as name from information_schema.columns
            where table_schema='public' and table_name in ('booking_customer_changes','booking_finance_commands')
              and data_type in ('text','character varying','jsonb','json','ARRAY')""")
        assert {column["name"] for column in columns} == set(AUDIT_COLUMN_TREATMENT)
    finally:
        await env.engine.dispose()


@pytest.mark.parametrize("prepared_erasure_db", [46], indirect=True)
async def test_erasure_fails_closed_when_audit_privacy_migration_is_missing(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        async with env.session() as session:
            with pytest.raises(RuntimeError, match="booking_audit_privacy_migration_required"):
                await SQLAccountDeletionRepository(session).erase_database(fixture["customer"], "customer")
        assert await env.sql("select id from profiles where id=:id", id=fixture["customer"])
    finally:
        await env.engine.dispose()
