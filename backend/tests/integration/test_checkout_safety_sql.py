"""Real PostgreSQL, actual create_booking, triggers, API flows and concurrent transactions.

Only uses MIGRATION_TEST_DB, creates a uniquely named local disposable database.
Never reads the runtime database URL for test operations.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_authenticated_session, get_current_actor
from app.core.exceptions import AppError, PaymentCollectionRequiredError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import get_session, set_actor_context
from app.main import create_app
from tests.conftest import make_owner, make_profile
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")
D = Decimal


async def _install_booking_window(database: str) -> None:
    url = make_url(TEST_DB).set(
        database=database, drivername="postgresql+asyncpg"
    ).render_as_string(hide_password=False)
    engine = create_async_engine(url, connect_args={"statement_cache_size": 0})
    source = (
        Path(__file__).parents[2]
        / "migrations"
        / "sql"
        / "0052_booking_window_30_days.sql"
    )
    try:
        async with engine.begin() as connection:
            for statement in source.read_text(encoding="utf-8").split(
                "\n-- statement --\n"
            ):
                if statement.strip():
                    await connection.execute(text(statement))
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def safety_db():
    database = "checkout_safety_" + uuid4().hex
    asyncio.run(_build(database))
    asyncio.run(_install_booking_window(database))
    yield make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    asyncio.run(_drop(database))


class SafetyEnv:
    def __init__(self, url):
        self.engine = create_async_engine(url, connect_args={"statement_cache_size": 0})

    def session(self):
        return AsyncSession(self.engine, expire_on_commit=False)

    async def seed(self):
        owner, customer, salon, staff, category, subcategory, service = [str(uuid4()) for _ in range(7)]
        hours = {day: {"open": "09:00", "close": "18:00"} for day in ("mon","tue","wed","thu","fri","sat","sun")}
        async with self.session() as session:
            # Fixture identities/catalog only. Every booking below uses real triggers/functions.
            await session.execute(text("set local session_replication_role=replica"))
            for uid, role in ((owner, "owner"), (customer, "customer")):
                await session.execute(text("insert into auth.users(id,email) values(:id,:email)"), {"id":uid,"email":uid+"@example.test"})
                await session.execute(text("insert into profiles(id,role,email) values(:id,cast(:role as user_role),:email)"), {"id":uid,"role":role,"email":uid+"@example.test"})
            await session.execute(text("""
                insert into salons(id,owner_id,name,profile_completed,approval_status,approval_mode,timezone,working_hours)
                values(:id,:owner,'Local test salon',true,'pending','auto','Asia/Kolkata',cast(:hours as jsonb))
            """), {"id":salon,"owner":owner,"hours":json.dumps(hours)})
            await session.execute(text("insert into staff(id,salon_id,name) values(:id,:salon,'Local test staff')"), {"id":staff,"salon":salon})
            await session.execute(text("insert into service_categories(id,name,slug) values(:id,'Test category',:slug)"), {"id":category,"slug":category})
            await session.execute(text("insert into service_subcategories(id,category_id,name,slug) values(:id,:cat,'Test service',:slug)"), {"id":subcategory,"cat":category,"slug":subcategory})
            await session.execute(text("insert into services(id,salon_id,subcategory_id,name,duration_minutes,price) values(:id,:salon,:sub,'Haircut',30,250)"), {"id":service,"salon":salon,"sub":subcategory})
            await session.execute(text("insert into staff_services(staff_id,service_id) values(:staff,:service)"), {"staff":staff,"service":service})
            await session.execute(text("set local session_replication_role=origin"))
            await session.execute(text("update salons set approval_status='approved' where id=:id"), {"id":salon})
            await session.commit()
        start = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=3)).replace(hour=10,minute=0,second=0,microsecond=0)
        return {"owner": owner,"customer": customer,"salon":salon,"staff":staff,"service":service,"start":start}

    def values(self, fixture, *, delta=0, key=None, preference="pay_at_salon"):
        return {"actor_id":fixture["customer"],"salon_id":fixture["salon"],"staff_id":fixture["staff"],
                "service_ids":[fixture["service"]],"start_datetime":fixture["start"]+timedelta(minutes=delta),
                "customer_name":"Local test customer","customer_phone":None,"source":"app","notes":None,
                "payment_preference":preference,"_idempotency_key":key}

    async def book(self, fixture, **kw):
        async with self.session() as session:
            await set_actor_context(session,fixture["customer"])
            try:
                return await PlatformRepository(session).create_booking(self.values(fixture, **kw))
            except AppError as exc:
                return exc

    async def sql(self, statement, **params):
        async with self.session() as session:
            result = await session.execute(text(statement),params)
            rows = list(result.mappings()) if result.returns_rows else []
            await session.commit()
            return rows

    async def collect(self, fixture, booking, key=None, method="cash"):
        async with self.session() as session:
            await set_actor_context(session, fixture["owner"])
            try:
                return await PlatformRepository(session).record_payment(fixture["owner"],booking["id"],method,idempotency_key=key)
            except AppError as exc:
                return exc

    async def complete(self, fixture, booking, key=None):
        async with self.session() as session:
            await set_actor_context(session, fixture["owner"])
            try:
                return await PlatformRepository(session).update_booking_status(fixture["owner"],booking["id"],"completed",idempotency_key=key)
            except AppError as exc:
                return exc


@pytest.fixture
async def safety(safety_db):
    env = SafetyEnv(safety_db)
    yield env
    await env.engine.dispose()


async def test_two_simultaneous_bookings_only_one_active_per_customer_day(safety):
    f = await safety.seed()
    results = await asyncio.gather(safety.book(f),safety.book(f,delta=30))
    assert sum(isinstance(r,dict) for r in results) == 1
    assert next(r for r in results if isinstance(r,AppError)).code == "pay_at_salon_daily_limit"
    assert (await safety.sql("select count(*) as n from bookings where customer_id=:id",id=f["customer"]))[0]["n"] == 1
    assert (await safety.sql("select count(*) as n from booking_audit_events e join bookings b on b.id=e.booking_id where b.customer_id=:id",id=f["customer"]))[0]["n"] == 1


async def test_booking_same_key_replays_and_different_payload_rejects(safety):
    f = await safety.seed()
    a,b = await asyncio.gather(safety.book(f,key="booking-key-1"),safety.book(f,key="booking-key-1"))
    assert a["id"] == b["id"]
    mismatch = await safety.book(f,key="booking-key-1",delta=30)
    assert mismatch.code == "idempotency_key_reused"
    assert (await safety.sql("select count(*) as n from email_events where user_id=:id",id=f["customer"]))[0]["n"] == 1


async def test_collection_required_then_collection_and_completion_races(safety):
    f = await safety.seed()
    booking = await safety.book(f)
    rejected = await safety.complete(f,booking)
    assert isinstance(rejected,PaymentCollectionRequiredError)
    results = await asyncio.gather(safety.collect(f,booking),safety.collect(f,booking))
    assert sum(isinstance(r,dict) for r in results) == 1
    ledger = (await safety.sql("select * from booking_payments where booking_id=:id",id=booking["id"]))
    assert len(ledger)==1 and ledger[0]["amount"]==D("250") and ledger[0]["collection_method"]=="CASH"
    assert ledger[0]["collected_by_owner"] and ledger[0]["order_ref"] is None and ledger[0]["online_processing_charge"]==0
    results = await asyncio.gather(safety.complete(f,booking),safety.complete(f,booking))
    assert sum(isinstance(r,dict) for r in results) == 1
    assert (await safety.sql("select count(*) as n from booking_audit_events where booking_id=:id and new_state='completed'",id=booking["id"]))[0]["n"] == 1


async def test_direct_sql_completion_is_guarded_and_audit_is_immutable(safety):
    from sqlalchemy.exc import DBAPIError
    f = await safety.seed()
    booking = await safety.book(f)
    with pytest.raises(DBAPIError,match="payment_collection_required"):
        await safety.sql("update bookings set status='completed' where id=:id",id=booking["id"])
    with pytest.raises(DBAPIError,match="audit_event_is_immutable"):
        await safety.sql("delete from booking_audit_events where booking_id=:id",id=booking["id"])


async def test_same_collection_completion_keys_replay_without_duplicate_money(safety):
    f = await safety.seed()
    b = await safety.book(f)
    results = await asyncio.gather(safety.collect(f,b,"collect-key-1",method="upi_direct"),safety.collect(f,b,"collect-key-1",method="upi_direct"))
    assert all(r["payment_status"]=="paid" for r in results)
    results = await asyncio.gather(safety.complete(f,b,"complete-key-1"),safety.complete(f,b,"complete-key-1"))
    assert all(r["status"]=="completed" for r in results)
    assert (await safety.sql("select count(*) as n from booking_payments where booking_id=:id",id=b["id"]))[0]["n"] == 1


async def test_completed_cancelled_no_show_do_not_consume_daily_limit(safety):
    f=await safety.seed()
    b=await safety.book(f)
    await safety.collect(f,b)
    await safety.complete(f,b)
    second=await safety.book(f,delta=30)
    assert isinstance(second,dict)
    await safety.sql("update bookings set status='cancelled' where id=:id",id=second["id"])
    assert isinstance(await safety.book(f,delta=60),dict)


async def test_two_no_shows_block_only_pay_at_salon_for_seven_days(safety):
    f=await safety.seed()
    for delta in (0,30):
        booking=await safety.book(f,delta=delta)
        # Move a fixture appointment into the past to exercise the real no-show transition.
        await safety.sql("update bookings set start_datetime=now()-interval '1 hour',end_datetime=now()-interval '30 minutes' where id=:id",id=booking["id"])
        await safety.sql("update bookings set status='no_show' where id=:id",id=booking["id"])
    block=(await safety.sql("select * from customer_booking_restrictions where customer_id=:id",id=f["customer"]))[0]
    assert block["no_show_count"]==2
    assert timedelta(days=6,hours=23) < block["pay_at_salon_blocked_until"]-datetime.now(UTC) <= timedelta(days=7)
    assert (await safety.book(f,delta=60)).code == "pay_at_salon_temporarily_blocked"
    assert isinstance(await safety.book(f,delta=60,preference="pay_full"),dict)


async def test_trial_expiry_hides_all_surfaces_but_existing_bookings_remain(safety):
    f=await safety.seed()
    booking=await safety.book(f)
    await safety.sql("update salon_access set trial_ends_at=now()-interval '1 second',trial_started_at=now()-interval '3 months' where salon_id=:id",id=f["salon"])
    async with safety.session() as session:
        repo=PlatformRepository(session)
        for surface in ("home","search"):
            rows=await repo.list_salons(search=None,city=None,lat=None,lng=None,limit=200,offset=0,ids=[f["salon"]],surface=surface)
            assert rows==[]
        assert await repo.get_available_slots(f["staff"],f["start"].date(),[f["service"]])==[]
        assert (await repo.get_booking(booking["id"],f["customer"]))["id"]==booking["id"]
    assert isinstance(await safety.collect(f,booking),dict)
    assert isinstance(await safety.complete(f,booking),dict)


async def test_trial_cap_serializes_different_customers(safety):
    f=await safety.seed()
    other=await safety.seed()
    await safety.sql("update salon_access set trial_booking_limit=1 where salon_id=:id",id=f["salon"])
    results=await asyncio.gather(safety.book(f),safety.book({**f,"customer":other["customer"]},delta=30))
    assert sum(isinstance(r,dict) for r in results)==1
    row=(await safety.sql("select bookings_counted,trial_limit_reached_at from salon_access where salon_id=:id",id=f["salon"]))[0]
    assert row["bookings_counted"]==1 and row["trial_limit_reached_at"] is not None


async def test_api_quote_auth_ownership_support_idempotency_and_safe_disabled_config(safety, monkeypatch):
    from app.infrastructure.db import session as session_module
    from app.infrastructure.push import outbox_worker
    monkeypatch.setattr(session_module,"AsyncSessionLocal",safety.session)
    monkeypatch.setattr(outbox_worker,"AsyncSessionLocal",safety.session)
    f=await safety.seed()
    app=create_app()
    current_actor=make_profile(f["customer"])
    async def actor():
        return current_actor
    async def session():
        async with safety.session() as s:
            await set_actor_context(s,current_actor.id)
            yield s
    app.dependency_overrides[get_current_actor]=actor
    app.dependency_overrides[get_authenticated_session]=session
    app.dependency_overrides[get_session]=session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://local.test") as client:
        quote=await client.post("/v1/bookings/quote",json={k:v for k,v in safety.values(f).items() if k in {"salon_id","staff_id","service_ids"}} | {"start_datetime":f["start"].isoformat(),"payment_mode":"PAY_ONLINE"})
        assert quote.status_code==200,quote.text
        assert quote.json()["online_processing_charge"]=="12.50" and quote.json()["total_payable"]=="262.50"
        assert quote.json()["online_payment_available"] is False
        body={k:v for k,v in safety.values(f).items() if k not in {"actor_id","_idempotency_key"}}
        body["start_datetime"]=f["start"].isoformat()
        created=await client.post("/v1/bookings",json=body,headers={"Idempotency-Key":"api-booking-1"})
        assert created.status_code==201,created.text
        bid=created.json()["id"]
        denied=await client.post(f"/v1/bookings/{bid}/complete")
        assert denied.status_code==403
        current_actor=make_owner(f["owner"])
        unpaid=await client.post(f"/v1/bookings/{bid}/complete")
        assert unpaid.status_code==409 and unpaid.json()["error"]["code"]=="payment_collection_required"
        collected=await client.post(f"/v1/bookings/{bid}/payment",json={"payment_method":"upi_direct"},headers={"Idempotency-Key":"api-collect-1"})
        assert collected.status_code==200,collected.text
        completed=await client.post(f"/v1/bookings/{bid}/complete",headers={"Idempotency-Key":"api-complete-1"})
        assert completed.status_code==200
        current_actor=make_profile(f["customer"])
        ticket=await client.post("/v1/support/tickets",json={"subject":"Local support test","body":"Please help","salon_id":f["salon"]},headers={"Idempotency-Key":"api-support-1"})
        assert ticket.status_code==201,ticket.text
        replay=await client.post("/v1/support/tickets",json={"subject":"Local support test","body":"Please help","salon_id":f["salon"]},headers={"Idempotency-Key":"api-support-1"})
        assert replay.json()["id"]==ticket.json()["id"]
        current_actor=make_owner(f["owner"])
        reply=await client.post(f"/v1/support/tickets/{ticket.json()['id']}/reply",json={"body":"Test reply"},headers={"Idempotency-Key":"api-support-reply-1"})
        assert reply.status_code==200,reply.text
        assert "customer_email" not in reply.text
        config=await client.get("/v1/payments/config")
        assert config.json()["enabled"] is False
        for secret in ("secret_key","service_role","RESEND_API_KEY","cashfree_client_secret"):
            assert secret not in (config.text+quote.text+reply.text)


async def test_backend_only_tables_and_booking_function_are_not_data_api_writable(safety):
    f=await safety.seed()
    rows=await safety.sql("""select c.relname,c.relrowsecurity,
      has_table_privilege('authenticated',c.oid,'INSERT') as can_insert
      from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'
      and c.relname in ('email_events','support_tickets','support_messages','booking_audit_events','customer_booking_restrictions')""")
    assert len(rows)==5 and all(r["relrowsecurity"] and not r["can_insert"] for r in rows)
    assert (await safety.sql("select has_function_privilege('anon','public.create_booking(uuid,uuid,uuid[],timestamptz,text,text,booking_source,text)','EXECUTE') as allowed"))[0]["allowed"] is False
    access=(await safety.sql("select trial_booking_limit,trial_ends_at=trial_started_at+interval '2 months' as calendar_months from salon_access where salon_id=:id",id=f["salon"]))[0]
    assert access["trial_booking_limit"]==120 and access["calendar_months"]


async def test_processing_charge_is_not_overcollection_and_full_refund_returns_service_balance(safety):
    from app.infrastructure.db.repositories.payment_repository import PaymentRepository
    f=await safety.seed()
    booking=await safety.book(f,preference="pay_full")
    async with safety.session() as session:
        await set_actor_context(session,f["customer"])
        repo=PaymentRepository(session)
        pid=await repo.insert_intent(booking=booking,actor_id=f["customer"],purpose="full",amount=D("262.50"),
            online_processing_charge=D("12.50"),commission_amount=D("0"),commission_rate_percent=D("0"),
            commission_base="online_amount",commission_policy_version="test",provider="cashfree",settlement_model="platform_collect",
            intent_reference="test_"+uuid4().hex,order_ref="test_order_"+uuid4().hex,expires_in_seconds=900)
        await repo.commit()
        # A pending/resumable intent must not consume the fee a retry still owes.
        assert await repo.processing_charge_allocated(booking["id"]) == D("0")
        payment=(await session.execute(text("select * from booking_payments where id=:id"),{"id":pid})).mappings().one()
        outcome=await repo.apply_payment_observation(provider="cashfree",order_ref=payment["order_ref"],payment_ref="test_payment_"+uuid4().hex,
            status="captured",amount=D("262.50"),currency="INR",instrument="upi",failure_code=None)
        await repo.commit()
        assert outcome=="applied"
        assert await repo.processing_charge_allocated(booking["id"]) == D("12.50")
    row=(await safety.sql("select paid_amount,payment_status from bookings where id=:id",id=booking["id"]))[0]
    assert row["paid_amount"]==D("250") and row["payment_status"]=="paid"
    await safety.sql("insert into payment_refunds(payment_id,booking_id,provider,amount,status,idempotency_key,processed_at) values(:pid,:bid,'cashfree',262.50,'processed','test-refund',now())",pid=pid,bid=booking["id"])
    row=(await safety.sql("select paid_amount,refunded_amount from bookings where id=:id",id=booking["id"]))[0]
    assert row["paid_amount"]==row["refunded_amount"]==D("250")
    async with safety.session() as session:
        assert await PaymentRepository(session).processing_charge_allocated(booking["id"]) == D("0")


async def test_collection_actor_can_only_be_anonymized_by_account_erasure(safety):
    from sqlalchemy.exc import DBAPIError
    f=await safety.seed()
    b=await safety.book(f)
    await safety.collect(f,b)
    with pytest.raises(DBAPIError,match="payment_collection_snapshot_is_immutable"):
        await safety.sql("update booking_payments set recorded_by=null where booking_id=:id",id=b["id"])
    async with safety.session() as session:
        await session.execute(text("set local app.account_erasure='on'"))
        await session.execute(text("update booking_payments set recorded_by=null where booking_id=:id"),{"id":b["id"]})
        await session.commit()


async def test_shared_pool_keeps_business_transactions_and_probe_autocommit(safety):
    from app.core.config import Settings
    from app.infrastructure.db.session import build_engines
    f = await safety.seed()
    pool, business = build_engines(Settings(_env_file=None, environment="test",
        # URL.__str__ redacts the password; connection configuration must retain it.
        database_url=safety.engine.url.render_as_string(hide_password=False),
        db_pool_size=1, db_max_overflow=0))
    assert business.pool is pool.pool
    try:
        async with AsyncSession(business) as session:
            await set_actor_context(session, f["customer"])
            await session.execute(text("update salons set name='Uncommitted test' where id=:id"),{"id":f["salon"]})
            conn = await session.connection()
            assert (await conn.get_raw_connection()).driver_connection.is_in_transaction()
            assert (await session.execute(text("select current_setting('request.jwt.claim.sub')"))).scalar_one() == f["customer"]
            # Closing without commit must roll back both data and transaction-local actor.
        async with pool.connect() as probe:
            assert (await probe.execute(text("select name from salons where id=:id"),{"id":f["salon"]})).scalar_one() == "Local test salon"
            assert not (await probe.get_raw_connection()).driver_connection.is_in_transaction()
        async with AsyncSession(business) as session:
            await session.execute(text("select 1"))
            assert (await (await session.connection()).get_raw_connection()).driver_connection.is_in_transaction()
    finally:
        await pool.dispose()


async def test_email_claim_concurrency_and_retry_use_stable_event_key(safety):
    from app.infrastructure.email.worker import deliver_once
    # All rows are synthetic in this disposable database. Isolate the worker queue.
    await safety.sql("update email_events set status='sent' where status in ('pending','processing')")
    key = "worker-test-" + uuid4().hex
    await safety.sql("insert into email_events(event_key,event_type,recipient,subject,body) values(:key,'test','customer@example.com','Test','Test')", key=key)
    class Gateway:
        enabled = True
        fail = True
        def __init__(self):
            self.calls = []
        async def send(self, **payload):
            self.calls.append(payload["event_key"])
            if self.fail:
                raise TimeoutError("synthetic provider timeout")
            return "synthetic-email-id"
    gateway = Gateway()
    await asyncio.gather(deliver_once(safety.session,gateway),deliver_once(safety.session,gateway))
    assert gateway.calls == [key]
    row = (await safety.sql("select status,attempts from email_events where event_key=:key",key=key))[0]
    assert row["status"] == "pending" and row["attempts"] == 1
    await safety.sql("update email_events set next_attempt_at=now() where event_key=:key",key=key)
    gateway.fail = False
    await deliver_once(safety.session,gateway)
    assert gateway.calls == [key,key]
    row = (await safety.sql("select status,attempts,provider_message_id from email_events where event_key=:key",key=key))[0]
    assert row["status"] == "sent" and row["attempts"] == 2
    assert row["provider_message_id"] == "synthetic-email-id"
