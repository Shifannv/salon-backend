"""Prepared-schema erasure, including populated retained audit tables, on local PG."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.api.deps import get_authenticated_session, get_current_actor
from app.application.use_cases.support import SupportUseCases
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.domain.entities.profile import Role
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.repositories.support_repository import SupportRepository
from app.infrastructure.db.session import set_actor_context
from app.infrastructure.email.worker import deliver_once
from app.main import create_app
from tests.integration.test_account_deletion_sql import COLUMN_TREATMENT
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

# The historical 0028 matrix remains unchanged. These decisions cover later fields
# on the prepared head; machine codes are server-generated, not arbitrary user text.
POST_BASELINE_COLUMN_TREATMENT = {
    "api_rate_limits.bucket_hash": "pseudonymous-rate-counter",
    "booking_audit_events.event_type": "machine-code",
    "booking_audit_events.new_state": "machine-code",
    "booking_audit_events.old_state": "machine-code",
    "booking_finance_reconciliations.reason": "machine-code",
    "booking_financial_outcomes.kind": "machine-code",
    "booking_financial_outcomes.policy_version": "policy-code",
    "booking_payments.collection_method": "machine-code",
    "booking_payments.commission_base": "machine-code",
    "booking_payments.commission_policy_version": "policy-code",
    "booking_payments.provider_session_id": "retained-provider-reference",
    "booking_policy_refund_jobs.status": "machine-code",
    "bookings.checkout_policy_version": "policy-code",
    "device_tokens.app": "machine-code",
    "email_events.body": "removed-with-subject-or-copy",
    "email_events.event_key": "removed-with-subject-or-copy",
    "email_events.event_type": "machine-code",
    "email_events.last_error_code": "machine-code",
    "email_events.provider_message_id": "removed-with-subject-or-copy",
    "email_events.recipient": "removed-with-subject-or-copy",
    "email_events.status": "machine-code",
    "email_events.subject": "removed-with-subject-or-copy",
    "payment_anomalies.detail": "scrubbed",
    "payment_anomalies.kind": "machine-code",
    "payment_anomalies.provider": "provider-code",
    "payment_anomalies.provider_ref": "retained-financial-reference",
    "payment_provider_account_audit.action": "machine-code",
    "payment_provider_account_audit.detail": "scrubbed",
    "payment_provider_account_audit.new_status": "machine-code",
    "payment_provider_account_audit.previous_status": "machine-code",
    "payment_provider_account_audit.provider": "provider-code",
    "payment_provider_account_audit.vendor_ref": "retained-provider-reference",
    "payment_refunds.kind": "machine-code",
    "salon_access.trial_ended_reason": "machine-code",
    "subscription_billing_records.benefits": "numeric-boolean-tree",
    "subscription_billing_records.benefits_erasure_policy": "policy-code",
    "subscription_billing_records.billing_interval": "machine-code",
    "subscription_billing_records.currency": "currency-code",
    "subscription_billing_records.failure_code": "scrubbed",
    "subscription_billing_records.plan_code": "retained-shared-plan-reference",
    "subscription_billing_records.provider": "provider-code",
    "subscription_billing_records.provider_order_ref": "retained-financial-reference",
    "subscription_billing_records.provider_payment_ref": "retained-financial-reference",
    "subscription_billing_records.receipt": "retained-financial-reference",
    "subscription_billing_records.status": "machine-code",
    "subscription_plans.features": "shared-public-catalog",
    "support_messages.body": "selectively-scrubbed",
    "support_tickets.status": "machine-code",
    "support_tickets.subject": "selectively-scrubbed",
    "support_tickets.erasure_policy_version": "policy-code",
    "support_tickets.erasure_retention_reason": "retention-code",
    "support_erasure_events.actor_pseudonym": "case-specific-pseudonym",
    "support_erasure_events.actor_role": "role-code",
    "support_erasure_events.case_type": "machine-code",
    "support_erasure_events.policy_version": "policy-code",
    "support_erasure_events.retention_reason": "retention-code",
    # booking_no_show_warnings (migration 0070) — cascade-deleted with the booking row;
    # response_reason_text is free customer text and must be scrubbed if it survives erasure.
    "booking_no_show_warnings.customer_response": "machine-code",
    "booking_no_show_warnings.resolution": "machine-code",
    "booking_no_show_warnings.response_reason_code": "machine-code",
    "booking_no_show_warnings.response_reason_text": "scrubbed",
}

REMOVED_COLUMN_TREATMENT = {"salons.category", "salons.description", "services.description"}


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
            for number in range(38, getattr(request, "param", 48) + 1):
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


async def test_full_prepared_schema_has_no_unclassified_personal_data_columns(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        columns = await env.sql("""select c.table_name || '.' || c.column_name as name
            from information_schema.columns c join information_schema.tables t
              on t.table_schema=c.table_schema and t.table_name=c.table_name
            where c.table_schema='public' and t.table_type='BASE TABLE' and c.table_name<>'alembic_version'
              and c.data_type in ('text','character varying','jsonb','json','ARRAY')""")
        live = {column["name"] for column in columns}
        known = (set(COLUMN_TREATMENT) - REMOVED_COLUMN_TREATMENT) | set(AUDIT_COLUMN_TREATMENT) | set(POST_BASELINE_COLUMN_TREATMENT)
        assert live == known, f"Unclassified: {sorted(live - known)}; stale decisions: {sorted(known - live)}"
    finally:
        await env.engine.dispose()


async def create_support_thread(env, fixture, marker, owner_marker=None):
    customer = SimpleNamespace(id=fixture["customer"], role=Role.customer, email="customer@example.test")
    owner = SimpleNamespace(id=fixture["owner"], role=Role.owner, email="owner@example.test")
    async with env.session() as session:
        await set_actor_context(session, customer.id)
        use_cases = SupportUseCases(SupportRepository(session), SimpleNamespace(support_email=None))
        ticket = await use_cases.create(customer, {"subject": marker, "body": marker, "salon_id": fixture["salon"]}, "support-create-key")
        await set_actor_context(session, owner.id)
        await use_cases.reply(owner, str(ticket["id"]), owner_marker or marker, "support-reply-key")
    return str(ticket["id"])


@pytest.mark.parametrize("role", ["owner", "customer"])
async def test_erasure_removes_cross_actor_support_email_and_replay_copies(prepared_erasure_db, role):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture, unrelated = await env.seed(), await env.seed()
        marker = "private-marker-" + uuid4().hex
        ticket = await create_support_thread(env, fixture, marker if role == "customer" else "Customer report",
                                             owner_marker=marker if role == "owner" else "Owner response")
        other = await create_support_thread(env, unrelated, "Unrelated support content")
        before_other = await env.sql("select * from support_messages where ticket_id=:tid", tid=other)
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,:role,'processing')", uid=fixture[role], role=role)
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture[role], role)
        for table in ("support_messages", "support_tickets", "email_events", "payment_idempotency_keys"):
            assert not await env.sql(f"select 1 from {table} row where strpos(to_jsonb(row)::text,:marker)>0", marker=marker), f"Personal text retained in {table} after {role} erasure"
        assert await env.sql("select * from support_messages where ticket_id=:tid", tid=other) == before_other
        if role == "customer":
            assert not await env.sql("select id from support_tickets where id=:tid", tid=ticket)
        else:
            assert await env.sql("select id from support_tickets where id=:tid", tid=ticket)
    finally:
        await env.engine.dispose()


@pytest.mark.parametrize("role", ["owner", "customer"])
async def test_erasure_scrubs_diagnostic_text_without_removing_financial_values(prepared_erasure_db, role):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        booking = await seed_audits(env, fixture)
        marker = "private-diagnostic-" + uuid4().hex
        async with env.session() as session:
            await set_actor_context(session, fixture[role])
            await session.execute(text("update profiles set full_name=:marker where id=:uid"), {"marker": marker, "uid": fixture[role]})
            await session.commit()
        await env.sql("""insert into payment_anomalies(kind,salon_id,booking_id,amount,detail)
            values('amount_mismatch',:salon,:bid,250,:marker)""", salon=fixture["salon"], bid=booking["id"], marker="Settlement evidence; " + marker)
        if role == "owner":
            await env.sql("""insert into payment_provider_account_audit(salon_id,provider,action,vendor_ref,actor_id,detail)
                values(:salon,'none','registered','synthetic-vendor',:uid,:marker)""",
                salon=fixture["salon"], uid=fixture["owner"], marker=marker)
            async with env.session() as session:
                await set_actor_context(session, fixture["owner"])
                await session.execute(text("""insert into subscription_billing_records
                    (salon_id,plan_id,plan_code,provider,receipt,status,amount,currency,billing_interval,benefits,expires_at,failure_code)
                    select :salon,id,code,'none',:receipt,'failed',100,'INR','monthly',
                        cast(:benefits as jsonb),now()+interval '1 hour',:marker
                      from subscription_plans order by id limit 1"""),
                    {"salon": fixture["salon"], "receipt": "fixture-" + uuid4().hex[:20], "marker": marker,
                     "benefits": json.dumps({"monthly_alert_cap": 10, "label": "Shared benefit", "unlimited_bookings": True})})
                await session.commit()
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,:role,'processing')", uid=fixture[role], role=role)
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture[role], role)
        anomalies = await env.sql("select detail,amount from payment_anomalies where booking_id=:bid", bid=booking["id"])
        assert len(anomalies) == 1 and anomalies[0]["detail"] == "Settlement evidence; █" and anomalies[0]["amount"] == 250
        if role == "owner":
            assert (await env.sql("select detail from payment_provider_account_audit where salon_id=:salon", salon=fixture["salon"]))[0]["detail"] == "█"
            billing = (await env.sql("select failure_code,amount,benefits from subscription_billing_records where salon_id=:salon", salon=fixture["salon"]))[0]
            assert billing["failure_code"] == "█" and billing["amount"] == 100
            assert billing["benefits"] == {"monthly_alert_cap": 10, "unlimited_bookings": True}
    finally:
        await env.engine.dispose()


async def test_support_email_in_flight_finishes_before_erasure_can_commit(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    entered, release = asyncio.Event(), asyncio.Event()
    tasks = []

    class Gateway:
        enabled = True

        async def send(self, **values):
            entered.set()
            await release.wait()
            return "synthetic-provider-message"

    try:
        fixture = await env.seed()
        ticket = await create_support_thread(env, fixture, "Customer report", owner_marker="Private owner reply")
        target = (await env.sql("""select e.id from email_events e join support_messages m
            on e.event_key='support_reply:'||m.id::text where m.ticket_id=:tid and m.author_id=:uid""",
            tid=ticket, uid=fixture["owner"]))[0]["id"]
        await env.sql("update email_events set status='sent' where id<>:id", id=target)
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        sender = asyncio.create_task(deliver_once(env.session, Gateway()))
        tasks.append(sender)
        await asyncio.wait_for(entered.wait(), 3)
        async with env.session() as session:
            pid = (await session.execute(text("select pg_backend_pid()"))).scalar_one()
            eraser = asyncio.create_task(SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner"))
            tasks.append(eraser)
            blocked = False
            for _ in range(100):
                if eraser.done():
                    break
                blocked = bool((await env.sql("select cardinality(pg_blocking_pids(:pid))>0 as blocked", pid=pid))[0]["blocked"])
                if blocked:
                    break
                await asyncio.sleep(.02)
            try:
                assert blocked and not eraser.done(), "Erasure committed while a personal email was still in flight"
            finally:
                release.set()
                await asyncio.gather(sender, eraser)
        assert not await env.sql("select id from email_events where id=:id", id=target)
    finally:
        release.set()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await env.engine.dispose()


async def test_owner_erasure_selectively_redacts_quotes_and_restricts_retained_case(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture, unrelated = await env.seed(), await env.seed()
        name, email, phone = "Example Owner", "owner.privacy+test@example.test", "+919876543210"
        async with env.session() as session:
            await set_actor_context(session, fixture["owner"])
            await session.execute(text("update profiles set full_name=:name,email=:email,phone=:phone where id=:id"),
                                  {"name": name, "email": email, "phone": phone, "id": fixture["owner"]})
            await session.commit()
        customer_text = f"Keep invoice amount 100. Contact {name} at {email}, +91 98765-43210. Keep this customer's words."
        ticket = await create_support_thread(env, fixture, customer_text, owner_marker="Owner's direct private message")
        # Deliberately identical quoted text in an unrelated salon must stay untouched.
        other = await create_support_thread(env, unrelated, customer_text)
        before_other = await env.sql("select * from support_messages where ticket_id=:tid", tid=other)
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner")
        case = (await env.sql("select * from support_tickets where id=:tid", tid=ticket))[0]
        assert case["retained_restricted"] and case["erasure_policy_version"] == "support-erasure-v1"
        assert case["erasure_retention_reason"] == "operational_review_pending"
        messages = await env.sql("select author_id,body from support_messages where ticket_id=:tid order by created_at,id", tid=ticket)
        customer_message = next(message for message in messages if str(message["author_id"]) == fixture["customer"])
        assert "Keep invoice amount 100." in customer_message["body"] and "Keep this customer's words." in customer_message["body"]
        for secret in (name, email, "98765-43210", fixture["owner"], "direct private"):
            assert secret not in str(messages) + str(case)
        assert next(message for message in messages if message["author_id"] is None)["body"] == "Removed"
        assert await env.sql("select * from support_messages where ticket_id=:tid", tid=other) == before_other
        events = await env.sql("select * from support_erasure_events where ticket_id=:tid", tid=ticket)
        assert len(events) == 1 and fixture["owner"] not in str(events)
        assert not await env.sql("select id from payment_idempotency_keys where scope='support:create' and response_body->>'id'=:tid", tid=ticket)
        async with env.session() as session:
            use_cases = SupportUseCases(SupportRepository(session), SimpleNamespace(support_email=None))
            customer = SimpleNamespace(id=fixture["customer"], role=Role.customer)
            with pytest.raises(NotFoundError):
                await use_cases.read(customer, ticket)
            await session.rollback()
            admin = SimpleNamespace(id=unrelated["owner"], role=Role.super_admin)
            assert (await use_cases.read(admin, ticket))["id"] == case["id"]
            await session.rollback()
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner")
        assert await env.sql("select * from support_erasure_events where ticket_id=:tid", tid=ticket) == events
        # A later customer's deletion detaches the retained case instead of cascading its evidence.
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'customer','processing')", uid=fixture["customer"])
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["customer"], "customer")
        assert (await env.sql("select customer_id from support_tickets where id=:tid", tid=ticket))[0]["customer_id"] is None
        assert len(await env.sql("select id from support_erasure_events where ticket_id=:tid", tid=ticket)) == 2
    finally:
        await env.engine.dispose()


async def test_benefit_redaction_is_recursive_and_does_not_relax_billing_immutability(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        assert (await env.sql("select retained_benefit_values(cast(:value as jsonb)) as value",
                            value=json.dumps({"monthly_alert_cap": 10, "unlimited_bookings": True, "note": "Private text"})))[0]["value"] == {
            "monthly_alert_cap": 10, "unlimited_bookings": True}
        fixture = await env.seed()
        async with env.session() as session:
            await set_actor_context(session, fixture["owner"])
            billing = (await session.execute(text("""insert into subscription_billing_records
                (salon_id,plan_id,plan_code,provider,receipt,status,amount,currency,billing_interval,benefits,expires_at)
                select :salon,id,code,'none',:receipt,'failed',100,'INR','monthly',cast(:benefits as jsonb),now()+interval '1 hour'
                  from subscription_plans order by id limit 1 returning *"""),
                {"salon": fixture["salon"], "receipt": "fixture-" + uuid4().hex[:20],
                 "benefits": json.dumps({"monthly_alert_cap": 10, "label": "Private text", "unlimited_bookings": True})})).mappings().one()
            await session.commit()
        with pytest.raises(DBAPIError, match="immutable"):
            await env.sql("update subscription_billing_records set benefits='{}' where id=:id", id=billing["id"])
        async with env.session() as session:
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            with pytest.raises(DBAPIError, match="verified_erasure_required"):
                await session.execute(text("select erase_subscription_benefit_text(:uid)"), {"uid": fixture["owner"]})
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        async with env.session() as session:
            await session.execute(text("set local role service_role"))
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            await session.execute(text("select erase_subscription_benefit_text(:uid)"), {"uid": fixture["owner"]})
            await session.commit()
        after = (await env.sql("select * from subscription_billing_records where id=:id", id=billing["id"]))[0]
        assert after["benefits"] == {"monthly_alert_cap": 10, "unlimited_bookings": True}
        for field in billing:
            if field not in {"benefits", "benefits_erased_at", "benefits_erasure_policy", "updated_at"}:
                assert after[field] == billing[field]
        with pytest.raises(DBAPIError, match="immutable"):
            await env.sql("update subscription_billing_records set amount=99 where id=:id", id=billing["id"])
        async with env.session() as session:
            await session.execute(text("select set_config('app.account_erasure','on',true)"))
            await session.execute(text("select erase_subscription_benefit_text(:uid)"), {"uid": fixture["owner"]})
            await session.commit()
        assert (await env.sql("select benefits_erased_at from subscription_billing_records where id=:id", id=billing["id"]))[0]["benefits_erased_at"] == after["benefits_erased_at"]
    finally:
        await env.engine.dispose()


async def test_benefit_object_keys_cannot_retain_personal_free_text(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        source = {"private-mail@example.test": True, "private-name": {"count": 2}, "unlimited_bookings": True}
        retained = (await env.sql("select retained_benefit_values(cast(:value as jsonb)) as value", value=json.dumps(source)))[0]["value"]
        assert "private-mail" not in json.dumps(retained) and "private-name" not in json.dumps(retained)
        assert retained["unlimited_bookings"] is True
        custom = {key: value for key, value in retained.items() if key != "unlimited_bookings"}
        assert len(custom) == 2 and all(key.startswith("_retained_") for key in custom)
        assert any(value is True for value in custom.values())
        assert any(isinstance(value, dict) and list(value.values()) == [2] for value in custom.values())
        other = (await env.sql("select retained_benefit_values(cast(:value as jsonb),'different-row') as value", value=json.dumps(source)))[0]["value"]
        assert set(retained) & set(other) == {"unlimited_bookings"}
    finally:
        await env.engine.dispose()


async def test_support_creation_rechecks_publication_after_concurrent_closure(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    task = None
    try:
        fixture = await env.seed()
        customer = SimpleNamespace(id=fixture["customer"], role=Role.customer, email="customer@example.test")
        async with env.session() as closure, env.session() as request:
            await closure.execute(text("select id from salons where id=:id for update"), {"id": fixture["salon"]})
            await set_actor_context(closure, fixture["owner"])
            await closure.execute(text("update salons set is_active=false where id=:id"), {"id": fixture["salon"]})
            await set_actor_context(request, customer.id)
            pid = (await request.execute(text("select pg_backend_pid()"))).scalar_one()
            task = asyncio.create_task(SupportUseCases(SupportRepository(request), SimpleNamespace(support_email=None)).create(
                customer, {"salon_id": fixture["salon"], "subject": "Late private request", "body": "Late private request"}, "late-support-key"))
            blocked = False
            for _ in range(100):
                blocked = bool((await env.sql("select cardinality(pg_blocking_pids(:pid))>0 as blocked", pid=pid))[0]["blocked"])
                if blocked or task.done():
                    break
                await asyncio.sleep(.02)
            assert blocked
            await closure.commit()
            with pytest.raises(NotFoundError):
                await task
        assert not await env.sql("select id from support_tickets where salon_id=:id", id=fixture["salon"])
        assert not await env.sql("select id from payment_idempotency_keys where actor_id=:uid and idempotency_key='late-support-key'", uid=customer.id)
    finally:
        if task:
            await asyncio.gather(task, return_exceptions=True)
        await env.engine.dispose()


async def test_quoted_owner_message_and_local_email_copy_are_redacted(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        private = "The private bank reference is ACCT987654321."
        ticket = await create_support_thread(env, fixture, "Unchanged customer invoice discussion", owner_marker=private)
        async with env.session() as session:
            repository = SupportRepository(session)
            message = await repository.add_message(ticket, fixture["customer"], "Customer quoted: " + private + " Keep invoice amount 250.")
            await repository.enqueue_email(fixture["customer"], "support_reply:" + message, "support_reply", "customer@example.test", "Quoted response", "Quoted: " + private)
            await session.commit()
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner")
        messages = await env.sql("select body from support_messages where ticket_id=:id", id=ticket)
        assert "ACCT987654321" not in str(messages)
        assert any("Keep invoice amount 250." in item["body"] for item in messages)
        assert not await env.sql("select id from email_events where event_key=:key", key="support_reply:" + message)
        for operation in ("update support_erasure_events set retention_reason='operational_review_pending' where ticket_id=:id",
                          "delete from support_erasure_events where ticket_id=:id"):
            with pytest.raises(DBAPIError, match="immutable"):
                await env.sql(operation, id=ticket)
    finally:
        await env.engine.dispose()


async def test_short_generic_owner_messages_do_not_erase_other_participants_evidence(prepared_erasure_db):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        original = "Keep invoice amount 100. OK. This punctuation must stay."
        ticket = await create_support_thread(env, fixture, original, owner_marker=".")
        async with env.session() as session:
            repository = SupportRepository(session)
            await repository.add_message(ticket, fixture["owner"], "OK")
            await repository.add_message(ticket, fixture["owner"], "100")
            await session.commit()
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner")
        message = (await env.sql("select body from support_messages where ticket_id=:tid and author_id=:uid", tid=ticket, uid=fixture["customer"]))[0]
        assert message["body"] == original
    finally:
        await env.engine.dispose()


async def test_retained_case_http_access_requires_admin_mfa_and_does_not_email_participants(prepared_erasure_db, monkeypatch):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture, unrelated = await env.seed(), await env.seed()
        ticket = await create_support_thread(env, fixture, "Customer evidence", owner_marker="Private owner response")
        admin_id = str(uuid4())
        async with env.session() as session:
            await session.execute(text("set local session_replication_role=replica"))
            await session.execute(text("insert into auth.users(id,email) values(:id,'admin-privacy@example.test')"), {"id": admin_id})
            await session.execute(text("insert into profiles(id,role,email) values(:id,'super_admin','admin-privacy@example.test')"), {"id": admin_id})
            await session.commit()
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'owner','processing')", uid=fixture["owner"])
        async with env.session() as session:
            await SQLAccountDeletionRepository(session).erase_database(fixture["owner"], "owner")
        monkeypatch.setattr(settings, "admin_require_mfa", True)
        app = create_app()
        actor = SimpleNamespace(id=fixture["customer"], role=Role.customer)
        aal = "aal1"

        async def current(request: Request):
            request.state.verified_auth_claims = {"aal": aal}
            return actor

        async def session_dependency():
            async with env.session() as session:
                await set_actor_context(session, actor.id)
                yield session

        app.dependency_overrides[get_current_actor] = current
        app.dependency_overrides[get_authenticated_session] = session_dependency
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get(f"/v1/support/tickets/{ticket}")).status_code == 404
            actor = SimpleNamespace(id=unrelated["owner"], role=Role.owner)
            assert (await client.get(f"/v1/support/tickets/{ticket}")).status_code == 404
            actor = SimpleNamespace(id=admin_id, role=Role.super_admin)
            assert (await client.get(f"/v1/support/tickets/{ticket}")).status_code == 403
            aal = "aal2"
            response = await client.get(f"/v1/support/tickets/{ticket}")
            assert response.status_code == 200 and response.json()["erasure_policy_version"] == "support-erasure-v1"
            response = await client.post(f"/v1/support/tickets/{ticket}/reply", json={"body": "Internal retention review"}, headers={"Idempotency-Key": "retained-case-review"})
            assert response.status_code == 200
        assert not await env.sql("""select e.id from email_events e join support_messages m
            on e.event_key='support_reply:'||m.id::text where m.ticket_id=:id""", id=ticket)
    finally:
        await env.engine.dispose()


@pytest.mark.parametrize(
    ("prepared_erasure_db", "required_migration"),
    [(46, "booking_audit_privacy_migration_required"), (47, "support_billing_privacy_migration_required")],
    indirect=["prepared_erasure_db"],
)
async def test_erasure_fails_closed_when_privacy_migration_is_missing(prepared_erasure_db, required_migration):
    env = SafetyEnv(prepared_erasure_db)
    try:
        fixture = await env.seed()
        await env.sql("insert into account_deletion_requests(user_id,role,status) values(:uid,'customer','processing')",
                      uid=fixture["customer"])
        async with env.session() as session:
            with pytest.raises(RuntimeError, match=required_migration):
                await SQLAccountDeletionRepository(session).erase_database(fixture["customer"], "customer")
        assert await env.sql("select id from profiles where id=:id", id=fixture["customer"])
    finally:
        await env.engine.dispose()
