"""Opt-in: account erasure against the REAL migrated schema (0001..0028).

The previous version of this file built a hand-written mini schema and replayed only
migration 0021 into it. It never ran: its fixture split dollar-quoted SQL and 0021 addresses
``public.bookings`` directly. Real behaviour needs the real schema, so this suite uses it.

Set ACCOUNT_DELETION_TEST_DB to a DISPOSABLE localhost database that has the whole
migration chain applied (``alembic upgrade head``) and a Supabase-like ``auth`` schema:
``auth.users(id, email, phone, raw_user_meta_data, raw_app_meta_data)`` plus ``auth.uid()``,
and the ``anon``/``authenticated``/``service_role`` roles. Rows are written with unique
markers and left behind, so never point this at anything you care about.

    ACCOUNT_DELETION_TEST_DB=postgresql+asyncpg://postgres:<pw>@127.0.0.1:55432/scratch \\
      python -m pytest tests/integration/test_account_deletion_sql.py

What it proves that the mini-schema suite (test_account_deletion_sql.py) cannot:

* a TABLE-WIDE residual sweep: after erasure no text/varchar/jsonb column in any public
  table contains the erased people's seeded markers, and no uuid column holds their ids;
* every text/jsonb column in the schema is classified (new columns fail the build);
* every ``on delete cascade`` FK to ``salons(id`` is emptied by the owner scrub;
* the real worker steps (cancel, notify, refund exactly once, settle, erase) on real SQL.
"""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.application.ports.auth_admin_gateway import AuthUserContacts
from app.application.ports.payment_gateway import RefundRequest, RefundResult
from app.application.use_cases.account_erasure import AccountErasureService
from app.core.exceptions import DeletionBlockedError, InvalidVerificationCodeError
from app.core.tokens import digest
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.infrastructure.db.repositories.account_deletion_repository import (
    SALON_CASCADE_TABLES,
    SQLAccountDeletionRepository,
)
from app.infrastructure.payments.null import NullPaymentGateway

TEST_DB = os.environ.get("ACCOUNT_DELETION_TEST_DB")
pytestmark = pytest.mark.skipif(
    not TEST_DB, reason="Requires a disposable migrated PostgreSQL via ACCOUNT_DELETION_TEST_DB"
)

TEXT_TYPES = ("text", "character varying", "jsonb", "json", "ARRAY")

# Every text/varchar/jsonb column in the schema and what erasure does with it. A column that
# is missing here fails test_every_text_column_is_classified: whoever adds a column must
# decide, in review, whether it can hold personal data and how it is erased.
D, S, K, N = "deleted", "scrubbed", "retained", "not-personal"
COLUMN_TREATMENT: dict[str, str] = {
    "account_deletion_challenges.contact_hash": D, "account_deletion_challenges.channel": N,
    "account_deletion_challenges.confirmation_hash": D, "account_deletion_challenges.purpose": N,
    "account_deletion_challenges.status": N,
    "account_deletion_requests.step_state": S, "account_deletion_requests.last_error_code": N,
    "account_deletion_requests.media_keys": S, "account_deletion_requests.role": N,
    "account_deletion_requests.salon_name": S, "account_deletion_requests.salon_city": S,
    "account_deletion_requests.status": N,
    "blocked_slots.reason": D, "blocked_slots.recurrence_rule": D, "blocked_slots.block_type": D,
    "booking_action_requests.reason": K,  # the OTHER customer's own words, on their own history
    "booking_action_requests.decision_reason": S, "booking_action_requests.kind": N,
    "booking_action_requests.decision": N, "booking_action_requests.status": N,
    "booking_payments.purpose": N, "booking_payments.failure_code": N,
    "booking_payments.payment_ref": K, "booking_payments.order_ref": K,  # financial record
    "booking_payments.intent_reference": K, "booking_payments.status": N,
    "booking_payments.currency": N, "booking_payments.instrument": N, "booking_payments.method": N,
    "booking_payments.provider": N, "booking_payments.settlement_model": N,
    "booking_payments.channel": N,
    "booking_services.service_name": N,
    "bookings.customer_phone": S, "bookings.rejection_reason": S, "bookings.notes": S,
    "bookings.cancellation_reason": S, "bookings.payment_preference": N,
    "bookings.cancellation_reason_code": S, "bookings.cancellation_reason_text": S,
    "bookings.customer_name": S, "bookings.currency": N,
    "device_tokens.token": D, "device_tokens.platform": D, "device_tokens.device_name": D,
    "languages.code": N, "languages.name": N,
    "notification_deliveries.error": S, "notification_outbox.status": N,
    "notification_outbox.last_error": S,
    "notifications.data": S, "notifications.body": S, "notifications.title": S,
    "notifications.type": N,
    "payment_idempotency_keys.scope": D, "payment_idempotency_keys.idempotency_key": D,
    "payment_idempotency_keys.request_fingerprint": D, "payment_idempotency_keys.response_body": D,
    "payment_provider_accounts.onboarding_status": N, "payment_provider_accounts.provider_account_ref": D,
    "payment_provider_accounts.provider": D, "payment_provider_accounts.requirements": D,
    "payment_refunds.reason": S, "payment_refunds.provider": N, "payment_refunds.refund_ref": K,
    "payment_refunds.status": N, "payment_refunds.idempotency_key": N,
    "payment_refunds.failure_code": N,
    "payment_webhook_events.provider_name": N, "payment_webhook_events.last_error_code": N,
    "payment_webhook_events.processing_status": N,
    "payment_webhook_events.normalized": K,  # identifiers and amounts only, by contract
    "payment_webhook_events.payload_hash": N, "payment_webhook_events.event_type": N,
    "payment_webhook_events.provider_event_reference": N,
    "profiles.avatar_url": D, "profiles.email": D, "profiles.phone": D, "profiles.full_name": D,
    "salon_holidays.reason": D, "salon_holidays.title": D,
    "salon_images.caption": D, "salon_images.url": D,
    "salon_payout_account_history.before_state": D, "salon_payout_account_history.action": D,
    "salon_payout_account_history.after_state": D, "salon_payout_account_history.changed_fields": D,
    "salon_payout_accounts.bank_account_fingerprint": D, "salon_payout_accounts.bank_name": D,
    "salon_payout_accounts.bank_account_number": D, "salon_payout_accounts.ifsc": D,
    "salon_payout_accounts.account_holder_name": D, "salon_payout_accounts.upi_id": D,
    "salon_reports.status": N, "salon_reports.details": S,
    "salon_reports.reason": K,  # the reporter's stated reason; reports BY the erased user are deleted
    "salons.address": S, "salons.home_placement": N, "salons.discovery_visibility": N,
    "salons.rejection_reason": S, "salons.timezone": N, "salons.city": S, "salons.name": S,
    "salons.category": N, "salons.description": S, "salons.qr_image_url": S, "salons.qr_token": S,
    "salons.working_hours": S,
    "service_categories.slug": N, "service_categories.image_url": N,
    "service_categories.description": N, "service_categories.name": N,
    "service_subcategories.name": N, "service_subcategories.image_url": N,
    "service_subcategories.description": N, "service_subcategories.slug": N,
    "services.description": S, "services.category_name": N, "services.photo_url": S,
    "services.subcategory_name": N,
    "services.name": K,  # kept: other customers' booking history refers to it
    "staff.experience": S, "staff.working_hours": N, "staff.name": S, "staff.photo_url": S,
    "staff.specialization": S,
    "staff_service_languages.language_code": N, "staff_services.specialization": S,
    "subscription_events.event_type": N, "subscription_events.provider_name": N,
    "subscription_events.provider_event_reference": N, "subscription_events.error_message": S,
    "subscription_events.payload_hash": N,
    "subscription_plans.currency": N, "subscription_plans.code": N, "subscription_plans.name": N,
    "subscription_plans.description": N, "subscription_plans.billing_interval": N,
    "subscription_provider_accounts.provider_name": D,
    "subscription_provider_accounts.provider_subscription_reference": D,
    "subscription_provider_accounts.provider_customer_reference": D,
}


# --------------------------------------------------------------------------- helpers
@pytest.fixture
async def engine():
    assert urlsplit(TEST_DB).hostname in {"localhost", "127.0.0.1", "::1"}
    eng = create_async_engine(TEST_DB, connect_args={"statement_cache_size": 0})
    async with eng.connect() as conn:
        assert (await conn.execute(
            text("select to_regclass('public.idx_account_deletion_requests_open_age')")
        )).scalar() is not None, "database is not migrated to 0028_account_erasure_hardening"
        # The worker claims ANY due request: start from an empty queue (disposable DB only).
        await conn.execute(text("delete from account_deletion_requests where status <> 'completed'"))
        await conn.commit()
    try:
        yield eng
    finally:
        await eng.dispose()


async def run(engine, sql, **params):
    async with AsyncSession(engine) as session:
        result = await session.execute(text(sql), params)
        await session.commit()
        return result.mappings().all() if result.returns_rows else None


async def run_unaudited(engine, sql, **params):
    """Insert with the audit trigger's erasure escape hatch on.

    Migration 0018 attached set_audit_actor() to subscription_plans / salon_subscriptions,
    which have no created_by column, so a plain INSERT into them fails on any database.
    That is a pre-existing defect unrelated to erasure; the tests only need the rows.
    """

    async with AsyncSession(engine) as session:
        await session.execute(text("select set_config('app.account_erasure', 'on', true)"))
        result = await session.execute(text(sql), params)
        await session.commit()
        return result.mappings().all() if result.returns_rows else None


async def one(engine, sql, **params):
    rows = await run(engine, sql, **params)
    return rows[0] if rows else None


async def new_user(engine, role: str, name: str, email: str, phone: str) -> str:
    uid = str(uuid4())
    await run(
        engine,
        "insert into auth.users (id, email, phone, raw_user_meta_data, raw_app_meta_data) "
        "values (:i, :e, :p, cast(:m as jsonb), cast(:a as jsonb))",
        i=uid, e=email, p=phone, m=f'{{"full_name": "{name}"}}', a=f'{{"role": "{role}"}}',
    )
    await run(engine, "update profiles set phone = :p, phone_verified = true where id = :i",
              i=uid, p=phone)
    return uid


def tag() -> str:
    return str(uuid4().int % 10**8).zfill(8)


async def seed_world(engine) -> dict:
    """An approved salon with every kind of owner/customer/staff text we know of."""

    t = tag()
    w: dict = {"tag": t, "own": f"OWN{t}", "stf": f"STF{t}", "wlk": f"WLK{t}",
               "cb": f"CUSTB{t}", "ca": f"CUSTA{t}"}
    own, stf, wlk, cb, ca = w["own"], w["stf"], w["wlk"], w["cb"], w["ca"]
    w["owner"] = await new_user(engine, "owner", f"Ravi {own}", f"ravi.{own}@owner.example", f"+9188{t}")
    w["staff_user"] = await new_user(engine, "staff", f"Dee {stf}", f"dee.{stf}@staff.example", f"+9177{t}")
    w["cust_a"] = await new_user(engine, "customer", f"Alice {ca}", f"alice.{ca}@c.example", f"+9166{t}")
    w["cust_b"] = await new_user(engine, "customer", f"Bob {cb}", f"bob.{cb}@c.example", f"+9155{t}")
    await run(engine, "update profiles set avatar_url = :u where id = :i",
              u=f"https://media.example/avatars/{w['owner']}/{own}.jpg", i=w["owner"])

    cat = (await one(engine, "insert into service_categories (name, slug) values (:n, :s) returning id",
                     n=f"Hair {t}", s=f"hair-{t}"))["id"]
    sub = (await one(engine, "insert into service_subcategories (category_id, name, slug) "
                             "values (:c, :n, :s) returning id", c=cat, n=f"Cut {t}", s=f"cut-{t}"))["id"]
    w["salon"] = str((await one(engine, """
        insert into salons (owner_id, name, description, address, city, lat, lng, qr_image_url,
                            working_hours, approval_status, profile_completed, rejection_reason,
                            created_by)
        values (:o, :n, :d, :a, :c, 9.9, 76.2, :q, cast(:wh as jsonb), 'approved', true, :rr, :o)
        returning id""",
        o=w["owner"], n=f"{own} Salon", d=f"{own} description", a=f"1 {own} Street",
        c=f"Kochi {own}", q=f"https://media.example/salon-images/{own}/qr.png",
        wh=f'{{"mon": {{"open": "09:00", "label": "{own}"}}}}', rr=f"{own} fix photos"))["id"])
    for i in range(2):
        await run(engine, "insert into salon_images (salon_id, url, caption) values (:s, :u, :c)",
                  s=w["salon"], u=f"https://media.example/salon-images/{w['salon']}/{i}.jpg",
                  c=f"{own} caption {i}")
    await run(engine, "insert into salon_holidays (salon_id, holiday_date, title, reason) "
                      "values (:s, current_date + 30, :t, :r)",
              s=w["salon"], t=f"{own} Holiday", r=f"{own} family function")
    w["staff"] = str((await one(engine, """
        insert into staff (salon_id, profile_id, name, photo_url, specialization, experience)
        values (:s, :p, :n, :u, :sp, :ex) returning id""",
        s=w["salon"], p=w["staff_user"], n=f"Dee {stf}",
        u=f"https://media.example/staff-photos/{stf}.jpg", sp=f"{stf} colour", ex=f"{stf} 7 years"))["id"])
    w["staff2"] = str((await one(engine, "insert into staff (salon_id, name) values (:s, 'Sam') "
                                         "returning id", s=w["salon"]))["id"])
    await run(engine, "insert into blocked_slots (salon_id, staff_id, start_datetime, end_datetime, reason) "
                      "values (:s, :st, now() + interval '40 days', now() + interval '40 days 1 hour', :r)",
              s=w["salon"], st=w["staff"], r=f"{own} lunch")
    w["service"] = str((await one(engine, """
        insert into services (salon_id, subcategory_id, name, description, duration_minutes, price,
                              photo_url)
        values (:s, :sub, 'Haircut', :d, 60, 500, :u) returning id""",
        s=w["salon"], sub=sub, d=f"{own} signature cut",
        u=f"https://media.example/salon-images/{own}/svc.jpg"))["id"])
    await run(engine, "insert into staff_services (staff_id, service_id, specialization) values (:st, :sv, :sp)",
              st=w["staff"], sv=w["service"], sp=f"{stf} fades")
    await run(engine, """
        insert into salon_payout_accounts (salon_id, account_holder_name, upi_id, bank_name,
                                           bank_account_number, ifsc)
        values (:s, :h, :u, 'Federal', :n, 'FDRL0001234')""",
        s=w["salon"], h=f"Ravi {own}", u=f"{own}@okbank", n=f"{t}0099887766")
    plan = (await run_unaudited(
        engine, "insert into subscription_plans (code, name) values (:c, 'Gold') returning id",
        c=f"gold-{t}"))[0]["id"]
    sub_id = (await run_unaudited(
        engine, "insert into salon_subscriptions (salon_id, plan_id, status) "
                "values (:s, :p, 'cancelled') returning id", s=w["salon"], p=plan))[0]["id"]
    await run(engine, "insert into subscription_provider_accounts (salon_id, provider_name, "
                      "provider_customer_reference) values (:s, 'stripe', :c)",
              s=w["salon"], c=f"cus_{own}")
    await run(engine, "insert into subscription_events (salon_subscription_id, event_type, error_message) "
                      "values (:s, 'invoice.failed', :e)", s=sub_id, e=f"card of {own} declined")
    await run(engine, "insert into payment_provider_accounts (salon_id, provider, provider_account_ref) "
                      "values (:s, 'fakepay', :r)", s=w["salon"], r=f"acc_{own}")
    await run(engine, "insert into salon_reports (reporter_id, salon_id, reason, details) "
                      "values (:r, :s, 'misleading', :d)", r=w["cust_b"], s=w["salon"],
              d=f"{cb} says the owner {own} was rude")

    async def booking(name, customer, days, status="confirmed", source="app", **extra):
        start = datetime.now(UTC) + timedelta(days=days)
        row = await one(engine, """
            insert into bookings (salon_id, staff_id, customer_id, customer_name, customer_phone,
                                  notes, source, status, start_datetime, end_datetime,
                                  total_duration_minutes, total_price, rejection_reason,
                                  cancellation_reason)
            values (:s, :st, :c, :n, :ph, :no, cast(:src as booking_source),
                    cast(:status as booking_status), :a, :b, 60, 500, :rr, :cr) returning id""",
            s=w["salon"], st=w["staff"], c=customer, n=name, ph=extra.get("phone"),
            no=extra.get("notes"), src=source, status=status, a=start,
            b=start + timedelta(hours=1), rr=extra.get("rejection"), cr=extra.get("cancellation"))
        bid = str(row["id"])
        await run(engine, "insert into booking_services (booking_id, service_id, service_name, "
                          "duration_minutes, price) values (:b, :sv, 'Haircut', 60, 500)",
                  b=bid, sv=w["service"])
        return bid

    w["b_online"] = await booking(f"Bob {cb}", w["cust_b"], 2, phone=f"+9155{t}")
    w["b_cash"] = await booking(f"Bob {cb}", w["cust_b"], 3, "pending", phone=f"+9155{t}")
    w["b_walkin"] = await booking(f"Walk {wlk}", None, 4, source="manual_walkin",
                                  phone=f"+9144{t}", notes=f"{wlk} allergic")
    w["b_rejected"] = await booking(f"Bob {cb}", w["cust_b"], -5, "rejected",
                                    rejection=f"{own} could not take it")
    w["b_done"] = await booking(f"Bob {cb}", w["cust_b"], -6, "completed")
    w["b_cancelled"] = await booking(f"Bob {cb}", w["cust_b"], -7, "cancelled",
                                     cancellation=f"call {own} first")
    w["b_alice"] = await booking(f"Alice {ca}", w["cust_a"], -8, "completed", phone=f"+9166{t}",
                                 notes=f"{ca} note")
    w["b_alice_future"] = await booking(f"Alice {ca}", w["cust_a"], 6, "confirmed", phone=f"+9166{t}")
    w["b_alice_rejected"] = await booking(f"Alice {ca}", w["cust_a"], -9, "rejected",
                                          rejection=f"{ca} no show history")
    await run(engine, """
        insert into booking_payments (booking_id, salon_id, payer_id, channel, purpose,
                                      settlement_model, provider, amount, status, intent_reference,
                                      order_ref, payment_ref, captured_at)
        values (:b, :s, :p, 'gateway', 'full', 'platform_collect', 'fakepay', 500, 'captured',
                :i, :o, :r, now())""",
        b=w["b_online"], s=w["salon"], p=w["cust_b"], i=f"int-{t}", o=f"order_{t}", r=f"pay_{t}")
    await run(engine, """
        insert into booking_payments (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                                      amount, status, method, intent_reference, captured_at)
        values (:b, :s, :p, :o, 'manual', 'full', 500, 'captured', 'cash', :i, now())""",
        b=w["b_cash"], s=w["salon"], p=w["cust_b"], o=w["owner"], i=f"cash-{t}")
    await run(engine, """
        insert into booking_payments (booking_id, salon_id, payer_id, recorded_by, channel, purpose,
                                      amount, status, method, intent_reference, captured_at)
        values (:b, :s, :p, :o, 'manual', 'full', 500, 'captured', 'cash', :i, now())""",
        b=w["b_alice"], s=w["salon"], p=w["cust_a"], o=w["staff_user"], i=f"cash-a-{t}")

    await run(engine, "insert into booking_action_requests (booking_id, kind, status, reason, requested_by) "
                      "values (:b, 'payment_confirmation', 'pending', :r, :c)",
              b=w["b_cash"], r=f"{cb} paid", c=w["cust_b"])
    await run(engine, "insert into booking_action_requests (booking_id, kind, status, reason, requested_by, "
                      "decision, decision_reason, resolved_at) values "
                      "(:b, 'cancellation', 'resolved', :r, :c, 'decline', :d, now())",
              b=w["b_done"], r=f"{cb} wants out", c=w["cust_b"], d=f"{own} says no to {cb}")
    await run(engine, "insert into booking_action_requests (booking_id, kind, status, reason, requested_by, "
                      "decision, decision_reason, resolved_at) values "
                      "(:b, 'cancellation', 'resolved', :r, :c, 'decline', :d, now())",
              b=w["b_alice"], r=f"{ca} wants out", c=w["cust_a"], d=f"declined {ca} twice")

    async def note(user, booking, title, body):
        await run(engine, """
            insert into notifications (user_id, booking_id, type, title, body, data)
            values (:u, :b, 'booking_x', :t, :bd, cast(:d as jsonb))""",
                  u=user, b=booking, t=title, bd=body, d=f'{{"who": "{body}"}}')

    await note(w["owner"], w["b_alice"], f"{ca} booked", f"{ca} booked with {own}")
    await note(w["staff_user"], w["b_alice"], f"{ca} booked", f"{ca} booked Dee {stf}")
    await note(w["cust_b"], w["b_done"], "Confirmed", f"Your booking at {own} Salon is confirmed")
    await note(w["cust_b"], w["b_rejected"], f"{own} declined", f"{own} could not take it")
    token = (await one(engine, "insert into device_tokens (user_id, token) values (:u, :t) returning id",
                       u=w["cust_b"], t=f"tok-{t}"))["id"]
    notif = (await one(engine, "select id from notifications where user_id = :u limit 1", u=w["cust_b"]))["id"]
    await run(engine, "insert into notification_deliveries (notification_id, device_token_id, error) "
                      "values (:n, :d, :e)", n=notif, d=token, e=f"push for {own} failed")
    await run(engine, "insert into device_tokens (user_id, token, device_name) values (:u, :t, :n)",
              u=w["owner"], t=f"owner-tok-{t}", n=f"{own} phone")
    await run(engine, "insert into payment_idempotency_keys (actor_id, scope, idempotency_key, "
                      "request_fingerprint, response_body, expires_at) values "
                      "(:a, 'refund:x', :k, 'fp', cast(:r as jsonb), now() + interval '1 day')",
              a=w["owner"], k="k" * 12, r=f'{{"holder": "{own}"}}')
    await run(engine, "insert into payment_idempotency_keys (actor_id, scope, idempotency_key, "
                      "request_fingerprint, response_body, expires_at) values "
                      "(:a, 'intent:x', :k, 'fp', cast(:r as jsonb), now() + interval '1 day')",
              a=w["cust_a"], k="a" * 12, r=f'{{"payer": "{ca}"}}')
    # Exercise both compatibility fields as arbitrary personal text, not trusted codes.
    # Existing customer/owner erasure tests below also retry and sweep residual markers.
    for key, booking_id in w.items():
        if key.startswith("b_"):
            marker = w["ca"] if key.startswith("b_alice") else w["own"]
            await run(engine, "update bookings set cancellation_reason_code=:code, "
                              "cancellation_reason_text=:reason where id=:id",
                      code=f"{marker}_reason", reason=f"{marker} private cancellation text", id=booking_id)
    return w


async def residual_hits(engine, needles: list[str], ids: list[str]) -> list[tuple[str, str, int]]:
    """Every (table, column, rows) in the public schema still holding a needle or an id."""

    cols = await run(engine, """
        select c.table_name, c.column_name, c.data_type
        from information_schema.columns c
        join information_schema.tables t
          on t.table_schema = c.table_schema and t.table_name = c.table_name
        where c.table_schema = 'public' and t.table_type = 'BASE TABLE'
          and (c.data_type in ('text', 'character varying', 'jsonb', 'json', 'ARRAY', 'uuid'))
    """)
    patterns = [f"%{n}%" for n in [*needles, *ids]]  # an id may sit inside jsonb/text too
    hits = []
    for col in cols:
        table, name = col["table_name"], col["column_name"]
        if col["data_type"] == "uuid":
            sql = f'select count(*) as n from "{table}" where "{name}" = any(cast(:ids as uuid[]))'
            args = {"ids": ids}
        else:
            sql = (f'select count(*) as n from "{table}" '
                   f'where cast("{name}" as text) ilike any(cast(:p as text[]))')
            args = {"p": patterns}
        n = (await one(engine, sql, **args))["n"]
        if n:
            hits.append((table, name, n))
    return hits


async def verified_challenge(engine, user_id: str) -> tuple[str, str]:
    token = "confirm-token-" + uuid4().hex
    async with AsyncSession(engine) as session:
        repo = SQLAccountDeletionRepository(session)
        challenge = await repo.create_challenge(user_id, "email", "hash", 600, 5)
        await repo.mark_verified(str(challenge["id"]), user_id, digest("s" * 32, "confirm", token), 600)
    return str(challenge["id"]), digest("s" * 32, "confirm", token)


async def confirm(engine, user_id: str) -> dict:
    challenge_id, token_hash = await verified_challenge(engine, user_id)
    async with AsyncSession(engine) as session:
        return await SQLAccountDeletionRepository(session).confirm_deletion(
            user_id, challenge_id, token_hash)


class FakeGateway(NullPaymentGateway):
    """Refund-capable fake: records calls, answers with a configurable status."""

    def __init__(self, status: RefundStatus = RefundStatus.processed, fail_calls: int = 0) -> None:
        self.calls: list[RefundRequest] = []
        self.status = status
        self.fail_calls = fail_calls

    @property
    def provider_name(self) -> str:
        return "fakepay"

    def supports(self, capability: GatewayCapability) -> bool:
        return capability == GatewayCapability.refunds

    async def refund(self, request: RefundRequest) -> RefundResult:
        self.calls.append(request)
        if self.fail_calls:
            self.fail_calls -= 1
            raise RuntimeError("provider unreachable")
        return RefundResult(provider="fakepay", refund_ref=f"rfnd_{request.payment_ref}",
                            status=self.status, amount=request.amount,
                            payment_ref=request.payment_ref)


class FakeAdmin:
    def __init__(self, *ids: str) -> None:
        self.users = set(ids)
        self.deleted: list[str] = []
        self.banned: list[str] = []

    async def get_user(self, user_id):
        return AuthUserContacts(user_id, None, False, "+910000000000", True) if user_id in self.users else None

    async def ban_user(self, user_id):
        self.banned.append(user_id)

    async def delete_user(self, user_id):
        self.users.discard(user_id)
        self.deleted.append(user_id)


def make_service(session, gateway, admin, *, refund_max_attempts=3):
    refs = MagicMock()
    refs.lock_media_url = AsyncMock()
    refs.media_url_is_referenced = AsyncMock(return_value=False)
    storage = MagicMock()
    storage.get_public_url = lambda bucket, path: f"https://media.example/{path}"
    storage.delete_object = AsyncMock()
    cache = MagicMock()
    cache.delete_prefix = AsyncMock()
    cache.available = True
    service = AccountErasureService(
        SQLAccountDeletionRepository(session), admin, storage, cache, refs, AsyncMock(), "bucket", 600,
        payment_gateway=gateway, refund_max_attempts=refund_max_attempts,
        storage_required=True, cache_required=True)
    return service, storage, cache


async def drain(engine, gateway, admin, *, rounds=10, **kw):
    """Run the worker loop until the request completes; return the cache mock too."""

    cache = None
    for _ in range(rounds):
        async with AsyncSession(engine) as session:
            service, _, cache = make_service(session, gateway, admin, **kw)
            if not await service.process_next():
                break
    return cache


async def finish_ledger(engine, request_id) -> None:
    """What the worker's last step does once erasure verified: close the ledger row."""

    await run(engine, "update account_deletion_requests set status = 'processing' where id = :i",
              i=str(request_id))
    async with AsyncSession(engine) as session:
        await SQLAccountDeletionRepository(session).complete_request(str(request_id))


async def make_due(engine, request_id):
    await run(engine, "update account_deletion_requests set next_attempt_at = now() - interval '1 second' "
                      "where id = :i", i=request_id)


# ---------------------------------------------------------------------------- schema
async def test_every_text_column_is_classified(engine):
    cols = await run(engine, """
        select c.table_name || '.' || c.column_name as key
        from information_schema.columns c
        join information_schema.tables t
          on t.table_schema = c.table_schema and t.table_name = c.table_name
        where c.table_schema = 'public' and t.table_type = 'BASE TABLE'
          and c.table_name <> 'alembic_version'
          and c.data_type in ('text', 'character varying', 'jsonb', 'json', 'ARRAY')
    """)
    live = {r["key"] for r in cols}
    assert live - set(COLUMN_TREATMENT) == set(), (
        "Unclassified text/jsonb columns: decide whether they can hold personal data and how "
        "account erasure handles them, then add them to COLUMN_TREATMENT (and to the owner scrub "
        "if they need one)")
    assert set(COLUMN_TREATMENT) - live == set(), "COLUMN_TREATMENT lists columns that no longer exist"


async def test_every_cascade_fk_to_salons_is_emptied_by_the_owner_scrub(engine):
    rows = await run(engine, """
        select distinct c.conrelid::regclass::text as tbl
        from pg_constraint c
        where c.contype = 'f' and c.confrelid = 'public.salons'::regclass and c.confdeltype = 'c'
    """)
    assert {r["tbl"] for r in rows} <= set(SALON_CASCADE_TABLES)


# ------------------------------------------------------------------- owner erasure
async def test_owner_erasure_leaves_no_residual_personal_data_anywhere(engine):
    w = await seed_world(engine)
    request = await confirm(engine, w["owner"])
    state = (await one(engine, "select step_state from account_deletion_requests where id = :i",
                       i=request["id"]))["step_state"]
    assert state["salon_ids"] == [w["salon"]] and state["staff_profile_ids"] == [w["staff_user"]]

    for _ in range(2):  # the second pass proves the erasure is re-runnable
        async with AsyncSession(engine) as session:
            await SQLAccountDeletionRepository(session).erase_database(
                w["owner"], "owner", [w["staff_user"]])
    await finish_ledger(engine, request["id"])

    hits = await residual_hits(
        engine, [w["own"], w["stf"], w["wlk"]], [w["owner"], w["staff_user"]])
    assert hits == [], f"residual personal data: {hits}"

    # Deliberate retention: the other customers' history and the financial ledger.
    assert (await one(engine, "select count(*) n from bookings where salon_id = :s and customer_id = :c",
                      s=w["salon"], c=w["cust_b"]))["n"] >= 4
    shell = await one(engine, "select name, city, owner_id, is_active, address, working_hours "
                              "from salons where id = :s", s=w["salon"])
    assert shell["name"] == "Closed salon" and shell["city"] is None and shell["owner_id"] is None
    assert shell["is_active"] is False and shell["address"] is None
    payments = await run(engine, "select amount, recorded_by, payer_id, payment_ref from booking_payments "
                                 "where salon_id = :s order by amount", s=w["salon"])
    assert len(payments) == 3 and all(p["recorded_by"] is None for p in payments)
    legacy = await run(engine, "select cancellation_reason_code,cancellation_reason_text "
                               "from bookings where salon_id=:s", s=w["salon"])
    assert legacy and all(r["cancellation_reason_code"] is None
                          and r["cancellation_reason_text"] is None for r in legacy)
    assert {str(p["payer_id"]) for p in payments if p["payer_id"]} == {w["cust_b"], w["cust_a"]}
    assert (await one(engine, "select reason, details from salon_reports where salon_id = :s", s=w["salon"])
            ) == {"reason": "misleading", "details": ""}
    rejected = await one(engine, "select rejection_reason, status from bookings where id = :b", b=w["b_rejected"])
    assert rejected["rejection_reason"] == "Removed"  # CHECK requires some text on a rejected booking
    walkin = await one(engine, "select customer_name, customer_phone, notes from bookings where id = :b",
                       b=w["b_walkin"])
    assert walkin == {"customer_name": "Deleted customer", "customer_phone": None, "notes": None}
    assert await run(engine, "select 1 from profiles where id = any(cast(:i as uuid[]))",
                     i=[w["owner"], w["staff_user"]]) == []
    for table in SALON_CASCADE_TABLES:
        assert (await one(engine, f"select count(*) n from {table} where salon_id = :s", s=w["salon"]))["n"] == 0
    # The customer's inbox lost the names but kept the row.
    inbox = await run(engine, "select title, body, data from notifications where user_id = :u", u=w["cust_b"])
    assert inbox and all(r["body"] is None and r["data"] is None for r in inbox)


async def test_customer_erasure_leaves_no_residual_personal_data_anywhere(engine):
    w = await seed_world(engine)
    challenge_id, token_hash = await verified_challenge(engine, w["cust_a"])
    async with AsyncSession(engine) as session:
        with pytest.raises(DeletionBlockedError):  # customers still resolve their own bookings
            await SQLAccountDeletionRepository(session).confirm_deletion(
                w["cust_a"], challenge_id, token_hash)
    await run(engine, "update bookings set status = 'cancelled' where id = :b", b=w["b_alice_future"])
    async with AsyncSession(engine) as session:
        request = await SQLAccountDeletionRepository(session).confirm_deletion(
            w["cust_a"], challenge_id, token_hash)
    for _ in range(2):
        async with AsyncSession(engine) as session:
            await SQLAccountDeletionRepository(session).erase_database(w["cust_a"], "customer")
    await finish_ledger(engine, request["id"])
    hits = await residual_hits(engine, [w["ca"]], [w["cust_a"]])
    erased = await one(engine, "select cancellation_reason_code,cancellation_reason_text "
                              "from bookings where id=:id", id=w["b_alice"])
    assert erased == {"cancellation_reason_code": None, "cancellation_reason_text": None}
    unrelated = await one(engine, "select cancellation_reason_code,cancellation_reason_text "
                                 "from bookings where id=:id", id=w["b_done"])
    assert unrelated["cancellation_reason_code"] == f"{w['own']}_reason"
    assert unrelated["cancellation_reason_text"] == f"{w['own']} private cancellation text"
    assert hits == [], f"residual personal data: {hits}"
    kept = await one(engine, "select customer_name, customer_phone, notes, rejection_reason "
                             "from bookings where id = :b", b=w["b_alice"])
    assert kept == {"customer_name": "Deleted customer", "customer_phone": None, "notes": None,
                    "rejection_reason": None}
    assert (await one(engine, "select rejection_reason from bookings where id = :b",
                      b=w["b_alice_rejected"]))["rejection_reason"] == "Removed"
    owner_inbox = await run(engine, "select title, body, data from notifications where user_id = :u",
                            u=w["owner"])
    assert owner_inbox and all(r["body"] is None and r["data"] is None for r in owner_inbox)
    assert (await one(engine, "select payer_id from booking_payments where intent_reference = :i",
                      i=f"cash-a-{w['tag']}"))["payer_id"] is None
    assert (await one(engine, "select count(*) n from payment_idempotency_keys where actor_id = :a",
                      a=w["cust_a"]))["n"] == 0


# ------------------------------------------------------------- the real worker loop
async def test_worker_cancels_notifies_refunds_once_and_erases(engine):
    w = await seed_world(engine)
    request = await confirm(engine, w["owner"])
    rid = str(request["id"])
    gateway = FakeGateway(status=RefundStatus.processed)
    admin = FakeAdmin(w["owner"], w["staff_user"])

    # Run 1 dies at the provider (network): nothing destructive may have happened.
    gateway.fail_calls = 1
    await drain(engine, gateway, admin, rounds=1)
    row = await one(engine, "select status, step_state, last_error_code from account_deletion_requests "
                            "where id = :i", i=rid)
    assert row["status"] == "failed" and row["last_error_code"] == "RuntimeError"
    assert row["step_state"].get("bookings_cancelled") is True and "auth_banned" not in row["step_state"]
    assert await one(engine, "select 1 as x from profiles where id = :o", o=w["owner"])
    cancelled = await run(engine, "select id, status, cancellation_reason from bookings where salon_id = :s "
                                  "and cancellation_reason = 'salon_closed'", s=w["salon"])
    assert {str(r["id"]) for r in cancelled} == {w["b_online"], w["b_cash"], w["b_walkin"], w["b_alice_future"]}
    assert all(r["status"] == "cancelled" for r in cancelled)
    assert (await one(engine, "select count(*) n from booking_action_requests where booking_id = :b "
                              "and status = 'pending'", b=w["b_cash"]))["n"] == 0

    # Run 2 retries: the refund is issued exactly once and the erasure completes.
    await make_due(engine, rid)
    await drain(engine, gateway, admin)
    done = await one(engine, "select status, step_state, user_id, salon_name, salon_city, media_keys, "
                             "last_error_code from account_deletion_requests where id = :i", i=rid)
    assert done["status"] == "completed" and done["step_state"] == {} and done["user_id"] is None
    assert done["salon_name"] == "Closed salon" and done["salon_city"] is None
    assert len(gateway.calls) == 2  # run 1 (failed in flight) + run 2; same provider key both times
    assert len({c.idempotency_key for c in gateway.calls}) == 1
    refunds = await run(engine, "select status, amount, idempotency_key from payment_refunds "
                                "where booking_id = :b", b=w["b_online"])
    assert refunds == [{"status": "processed", "amount": Decimal("500.00"), "idempotency_key": "salon_closed"}]
    assert (await one(engine, "select status from booking_payments where intent_reference = :i",
                      i=f"int-{w['tag']}"))["status"] == "refunded"
    # No refund for the cash receipt: the platform never held that money.
    assert (await one(engine, "select count(*) n from payment_refunds where booking_id = :b", b=w["b_cash"]))["n"] == 0

    notes = await run(engine, "select user_id, body, data from notifications where booking_id = any(cast(:b as uuid[])) "
                              "and data ->> 'reason' = 'salon_closed'",
                      b=[w["b_online"], w["b_cash"], w["b_walkin"], w["b_alice_future"]])
    assert len(notes) == 3  # the walk-in has no account to notify
    bodies = [n["body"] for n in notes]
    assert any("will be refunded" in b for b in bodies)  # the online payment
    assert any("not refunded by the platform" in b for b in bodies)  # the cash receipt
    assert all(b.startswith("This salon has closed") and w["own"] not in b for b in bodies)
    assert (await one(engine, "select count(*) n from notification_outbox o join notifications n "
                              "on n.id = o.notification_id where n.data ->> 'reason' = 'salon_closed' "
                              "and n.booking_id = any(cast(:b as uuid[]))",
                      b=[w["b_online"], w["b_cash"], w["b_alice_future"]]))["n"] == 3
    assert w["staff_user"] in admin.deleted and w["owner"] in admin.deleted
    hits = await residual_hits(engine, [w["own"], w["stf"], w["wlk"]], [w["owner"], w["staff_user"]])
    assert hits == [], f"residual personal data: {hits}"


async def test_unsettled_refund_requeues_then_proceeds_after_the_cap(engine):
    w = await seed_world(engine)
    rid = str((await confirm(engine, w["owner"]))["id"])
    gateway = FakeGateway(status=RefundStatus.created)  # provider accepted, never settles
    admin = FakeAdmin(w["owner"], w["staff_user"])
    await drain(engine, gateway, admin, rounds=1, refund_max_attempts=3)
    row = await one(engine, "select status, last_error_code, attempts, step_state from "
                            "account_deletion_requests where id = :i", i=rid)
    assert row["status"] == "pending" and row["last_error_code"] == "refunds_pending"
    assert "auth_banned" not in row["step_state"] and "refunds_settled" not in row["step_state"]
    assert len(gateway.calls) == 1
    for _ in range(3):
        await make_due(engine, rid)
        await drain(engine, gateway, admin, rounds=1, refund_max_attempts=3)
    assert len(gateway.calls) == 1  # never re-sent: the refund row already has a provider ref
    done = await one(engine, "select status from account_deletion_requests where id = :i", i=rid)
    assert done["status"] == "completed"
    assert (await one(engine, "select status from payment_refunds where booking_id = :b",
                      b=w["b_online"]))["status"] == "created"  # left for the operator, logged ERROR


async def test_unissuable_refund_is_recorded_failed_and_erasure_proceeds(engine):
    w = await seed_world(engine)
    rid = str((await confirm(engine, w["owner"]))["id"])
    gateway = FakeGateway(fail_calls=99)
    admin = FakeAdmin(w["owner"], w["staff_user"])
    for _ in range(3):
        await drain(engine, gateway, admin, rounds=1, refund_max_attempts=3)
        await make_due(engine, rid)
    await drain(engine, gateway, admin, refund_max_attempts=3)
    assert (await one(engine, "select status from account_deletion_requests where id = :i", i=rid))["status"] == "completed"
    failed = await one(engine, "select status, failure_code from payment_refunds where booking_id = :b",
                       b=w["b_online"])
    assert failed == {"status": "failed", "failure_code": "refund_call_failed"}


async def test_no_provider_makes_the_refund_phase_a_clean_noop(engine):
    w = await seed_world(engine)
    await run(engine, "delete from payment_refunds where booking_id = :b", b=w["b_online"])
    # Simulate PAYMENT_PROVIDER=none: no online payment can exist.
    await run(engine, "update booking_payments set status = 'cancelled' where booking_id = :b", b=w["b_online"]) \
        if False else None
    await run(engine, "alter table booking_payments disable trigger user")
    try:
        await run(engine, "delete from booking_payments where booking_id = :b", b=w["b_online"])
    finally:
        await run(engine, "alter table booking_payments enable trigger user")
    rid = str((await confirm(engine, w["owner"]))["id"])
    await drain(engine, NullPaymentGateway(), FakeAdmin(w["owner"], w["staff_user"]))
    assert (await one(engine, "select status from account_deletion_requests where id = :i", i=rid))["status"] == "completed"
    assert (await one(engine, "select count(*) n from payment_refunds where booking_id = :b", b=w["b_online"]))["n"] == 0


async def test_repeated_confirmation_is_idempotent_and_wrong_hash_is_rejected(engine):
    w = await seed_world(engine)
    customer = w["cust_b"]
    # cust_b has upcoming bookings, so cancel them: this test is about the confirm handshake.
    await run(engine, "update bookings set status = 'cancelled' where customer_id = :c", c=customer)
    await run(engine, "update booking_action_requests set status = 'resolved', decision = 'invalidated', "
                      "resolved_at = now() where requested_by = :c and status = 'pending'", c=customer)
    challenge_id, token_hash = await verified_challenge(engine, customer)
    async with AsyncSession(engine) as session:
        first = await SQLAccountDeletionRepository(session).confirm_deletion(
            customer, challenge_id, token_hash)
    async with AsyncSession(engine) as session:
        second = await SQLAccountDeletionRepository(session).confirm_deletion(
            customer, challenge_id, token_hash)
    assert second["id"] == first["id"]
    async with AsyncSession(engine) as session:
        with pytest.raises(InvalidVerificationCodeError):
            await SQLAccountDeletionRepository(session).confirm_deletion(
                customer, challenge_id, "wrong")
    assert (await one(engine, "select count(*) n from account_deletion_requests where user_id = :u",
                      u=customer))["n"] == 1
    assert (await one(engine, "select is_active from profiles where id = :u", u=customer))["is_active"] is False


async def test_an_owner_with_open_bookings_is_not_blocked(engine):
    w = await seed_world(engine)
    request = await confirm(engine, w["owner"])  # b_online, b_cash, b_walkin are all upcoming
    assert request["status"] == "pending"
    impact = await run(engine, "select count(*) n from bookings where salon_id = :s "
                               "and status in ('pending', 'confirmed') and end_datetime > now()", s=w["salon"])
    assert impact[0]["n"] >= 3  # confirm locks and queues; the WORKER cancels them
    async with AsyncSession(engine) as session:
        blockers = await SQLAccountDeletionRepository(session).count_blockers(w["owner"], "owner")
    assert blockers["open_bookings"] == 0 and blockers["pending_requests"] == 0
