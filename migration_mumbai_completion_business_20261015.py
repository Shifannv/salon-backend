"""Real Mumbai API/SQL tests within the caller's rollback-only fixture."""

import time
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text


async def business_checks(api, factory, headers, ids, payload, first_booking, *,
                          customer_id="81163183-2757-464e-8f92-b7f5dafe61fa"):
    results = []

    async def request(label, method, path, *, role="customer", expected=200, body=None, key=None, params=None):
        auth = dict(headers[role]) if role else {}
        if method == "POST":
            auth["Idempotency-Key"] = key or str(uuid4())
        started = time.perf_counter()
        response = await api.request(method, path, headers=auth, json=body, params=params)
        item = {"check": label, "status": response.status_code, "expected": expected,
                "elapsed_ms": round((time.perf_counter()-started)*1000, 3)}
        data = response.json()
        if response.status_code >= 400 and isinstance(data, dict):
            item["error_code"] = data.get("error", {}).get("code")
        results.append(item)
        if response.status_code != expected:
            raise RuntimeError(label + ": unexpected HTTP status")
        return data

    async def sql(statement, values=None):
        async with factory() as session:
            response = await session.execute(text(statement), values or {})
            value = response.scalar_one_or_none() if response.returns_rows else None
            await session.commit()
            return value

    async def create(label, delta):
        body = {**payload, "start_datetime": (datetime.fromisoformat(payload["start_datetime"])
                + timedelta(minutes=delta)).isoformat()}
        return await request(label, "POST", "/v1/bookings", expected=201, body=body)

    try:
        await request("openapi_contract", "GET", "/openapi.json", role=None)
        await request("owner_access_api", "POST", "/v1/auth/owner-access", role="owner")
        await request("create_owner_service_via_api", "POST", "/v1/salons/me/services", role="owner", expected=201,
            body={"subcategory_id": ids["subcategory"], "name": "Synthetic second service", "duration_minutes": 30, "price": "200.00"})
        await request("create_owner_staff_via_api", "POST", "/v1/salons/me/staff", role="owner", expected=201,
            body={"name": "Synthetic second staff"})
        public = await request("public_synthetic_salon", "GET", "/v1/salons", role=None,
                               params={"ids": ids["salon"]})
        assert any(row["id"] == ids["salon"] for row in public)
        await request("public_service_listing", "GET", f"/v1/salons/{ids['salon']}/services", role=None)
        await request("public_staff_listing", "GET", f"/v1/salons/{ids['salon']}/staff", role=None)
        quote_body = {key: payload[key] for key in ("salon_id", "staff_id", "service_ids")}
        quote_body.update(start_datetime=(datetime.fromisoformat(payload["start_datetime"])
            + timedelta(minutes=60)).isoformat(), payment_mode="PAY_ONLINE")
        quote = await request("server_quote_with_online_disabled", "POST", "/v1/bookings/quote", body=quote_body)
        assert quote["online_payment_available"] is False
        daily_body = {**payload, "start_datetime": quote_body["start_datetime"]}
        daily = await request("pay_at_salon_daily_limit", "POST", "/v1/bookings", expected=409, body=daily_body)
        assert daily["error"]["code"] == "pay_at_salon_daily_limit"
        await request("customer_cannot_collect", "POST", f"/v1/bookings/{first_booking}/payment",
                      expected=403, body={"payment_method": "cash"})
        await request("completion_requires_collection", "POST", f"/v1/bookings/{first_booking}/complete",
                      role="owner", expected=409)
        cash = await request("owner_cash_collection", "POST", f"/v1/bookings/{first_booking}/payment",
                             role="owner", body={"payment_method": "cash"})
        assert cash["payment_status"] == "paid"
        completed = await request("complete_after_cash_collection", "POST",
                                  f"/v1/bookings/{first_booking}/complete", role="owner")
        assert completed["status"] == "completed"
        upi_booking = await create("new_booking_after_completed_frees_daily_limit", 60)
        upi = await request("owner_upi_direct_collection", "POST", f"/v1/bookings/{upi_booking['id']}/payment",
                            role="owner", body={"payment_method": "upi_direct"})
        assert upi["payment_status"] == "paid"
        await request("complete_after_upi_collection", "POST", f"/v1/bookings/{upi_booking['id']}/complete", role="owner")
        cancellation = await create("cancellable_future_booking", 120)
        cancelled = await request("customer_cancellation_before_cutoff", "POST",
                                  f"/v1/bookings/{cancellation['id']}/cancel", body={})
        assert cancelled["status"] == "cancelled"
        for offset in (180, 240):
            no_show = await create("no_show_fixture_booking", offset)
            if offset == 180:
                await request("no_show_before_appointment_rejected", "POST",
                    f"/v1/bookings/{no_show['id']}/no-show", role="owner", expected=422)
            # Time-only fixture change; the actual no-show transition goes through API/SQL guards.
            await sql("update public.bookings set start_datetime=now()-interval '2 hours',end_datetime=now()-interval '1 hour' where id=:id", {"id": no_show["id"]})
            marked = await request("owner_marks_past_appointment_no_show", "POST",
                                   f"/v1/bookings/{no_show['id']}/no-show", role="owner")
            assert marked["status"] == "no_show"
        blocked_body = {**payload, "start_datetime": (datetime.fromisoformat(payload["start_datetime"])
                        + timedelta(minutes=300)).isoformat()}
        await request("repeated_no_shows_block_pay_at_salon", "POST", "/v1/bookings", expected=409, body=blocked_body)

        # A different synthetic salon is not owned by the authenticated owner.
        foreign_salon = str(uuid4())
        await sql("select set_config('request.jwt.claims','{}',true),set_config('request.jwt.claim.sub','',true)")
        await sql("insert into public.salons(id,name,owner_id) values(:id,'Foreign rollback fixture',null)", {"id": foreign_salon})
        support = await request("support_ticket_create", "POST", "/v1/support/tickets", expected=201,
            body={"subject": "Synthetic Mumbai staging check", "body": "Synthetic support request", "salon_id": ids["salon"]})
        await request("owner_support_reply", "POST", f"/v1/support/tickets/{support['id']}/reply",
            role="owner", body={"body": "Synthetic staging reply"})
        foreign_support = await request("foreign_salon_support_fixture", "POST", "/v1/support/tickets", expected=201,
            body={"subject": "Synthetic foreign salon check", "body": "Synthetic request", "salon_id": foreign_salon})
        await request("owner_cannot_read_foreign_salon_ticket", "GET",
                      f"/v1/support/tickets/{foreign_support['id']}", role="owner", expected=404)

        from app.infrastructure.email.worker import deliver_once

        class FakeEmail:
            enabled = True

            async def send(self, **kwargs):
                return "synthetic-provider-response"

        worked = await deliver_once(session_factory=factory, gateway=FakeEmail())
        assert worked
        sent = await sql("select count(*) from public.email_events where status='sent'")
        results.append({"check": "email_worker_database_claim_and_ack", "sent_rows": sent,
                        "external_provider": "fake", "actual_delivery_verified": False})

        from app.infrastructure.db.repositories.platform_repository import (
            PlatformRepository,
        )
        from app.infrastructure.push import outbox_worker

        async with factory() as session:
            await PlatformRepository(session).enqueue_notification(user_id=customer_id,
                booking_id=first_booking, notification_type="staging_audit", title="Synthetic test", body="Synthetic test")

        class FakePush:
            def __init__(self, *args):
                pass

            async def fan_out(self, *args):
                pass

        with patch.object(outbox_worker, "AsyncSessionLocal", factory), patch.object(outbox_worker, "FCMGateway", FakePush):
            drained = await outbox_worker.drain_notification_outbox()
        results.append({"check": "notification_worker_database_drain", "events_attempted": drained,
                        "external_provider": "fake"})
        assert drained >= 1
        audit_count = await sql("select count(*) from public.booking_audit_events")
        manual_methods = []
        async with factory() as session:
            rows = await session.execute(text("select collection_method,count(*) n from public.booking_payments group by collection_method"))
            manual_methods = [{"method": row[0], "rows": row[1]} for row in rows]
        results.append({"check": "audit_and_collection_snapshots", "audit_rows": audit_count,
                        "methods": manual_methods})
        assert audit_count > 0 and {row["method"] for row in manual_methods} == {"CASH", "UPI_DIRECT"}

        await sql("update public.salon_access set trial_started_at=now()-interval '3 months',trial_ends_at=now()-interval '1 second' where salon_id=:id", {"id": ids["salon"]})
        hidden = await request("expired_trial_hidden_from_public_discovery", "GET", "/v1/salons",
                               role=None, params={"ids": ids["salon"]})
        assert not hidden
        slots = await request("expired_trial_has_no_slots", "GET", "/v1/availability", role=None,
                              params={"staff_id": ids["staff"], "date": datetime.fromisoformat(payload["start_datetime"]).date().isoformat(), "service_ids": [ids["service"]]})
        assert not slots
        await request("existing_history_readable_after_trial_expiry", "GET", f"/v1/bookings/{first_booking}")
        await sql("select public.sweep_lapsed_subscriptions()")
        results.append({"check": "subscription_database_sweep", "status": "completed in rollback transaction"})
        return results
    except Exception:
        import json
        print(json.dumps({"completion_business_results_before_failure": results}))
        raise
