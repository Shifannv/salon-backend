"""Additional synthetic acceptance checks within the guarded rollback fixture."""

import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

CONTAINER = "salon-mumbai-refresh-redis"
CONTAINER_ID = "175ce66784838b78fae6cb0c2dab2b1a85213346c0cd9588a66c44dee6757701"


async def redis_control(action):
    process = await asyncio.create_subprocess_exec(
        "docker", "inspect", CONTAINER, "--format", "{{.Id}}",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    output, _ = await process.communicate()
    if process.returncode or output.decode().strip() != CONTAINER_ID:
        raise RuntimeError("Isolated Redis identity mismatch")
    if action is None:
        return
    process = await asyncio.create_subprocess_exec(
        "docker", action, CONTAINER,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    if await process.wait():
        raise RuntimeError("Isolated Redis control failed")


async def lifecycle_checks(api, connection, ids, headers, payload, first_booking, report):
    """Real HTTP/JWT/DB, with no provider calls and no schema changes."""
    phase = "lifecycle_setup"

    async def call(method, path, role="owner", expected=200, key=None, **kwargs):
        auth = dict(headers[role])
        if method == "POST":
            auth["Idempotency-Key"] = key or str(uuid4())
        response = await api.request(method, path, headers=auth, **kwargs)
        if response.status_code != expected:
            report["checks"].append({"check": phase, "status": "failed",
                "http_status": response.status_code, "expected": expected,
                "error_code": response.json().get("error", {}).get("code")})
            raise AssertionError("Unexpected acceptance HTTP status")
        return response.json()

    def passed(name, **facts):
        report["checks"].append({"check": name, "status": "passed", **facts})

    async def create(days, *, key=None):
        date = (datetime.fromisoformat(payload["start_datetime"]) + timedelta(days=days)).date()
        slots = await call("GET", "/v1/availability", role="customer", params={
            "staff_id": ids["staff"], "date": date.isoformat(), "service_ids": ids["service"],
        })
        assert slots, "Synthetic availability missing"
        body = {**payload, "start_datetime": slots[0]["slot_start"]}
        row = await call("POST", "/v1/bookings", "customer", 201, key=key, json=body)
        return row, body

    try:
        # Finish the existing fixture before testing a new pending booking.
        await call("POST", f"/v1/bookings/{first_booking}/check-in")
        await call("POST", f"/v1/bookings/{first_booking}/payment", json={"payment_method": "cash"})
        await call("POST", f"/v1/bookings/{first_booking}/complete")
        await call("PATCH", "/v1/salons/me/settings", json={"approval_mode": "manual"})
        phase = "full_booking_lifecycle"
        pending, _ = await create(1)
        assert pending["status"] == "pending"
        booking = pending["id"]
        states = [pending["status"]]
        for endpoint, expected in (("approve", "confirmed"), ("check-in", "checked_in")):
            row = await call("POST", f"/v1/bookings/{booking}/{endpoint}")
            assert row["status"] == expected
            states.append(row["status"])
            customer = await call("GET", f"/v1/bookings/{booking}", "customer")
            assert customer["status"] == expected
        await call("POST", f"/v1/bookings/{booking}/complete", expected=409)
        receipt_key = str(uuid4())
        paid = await call("POST", f"/v1/bookings/{booking}/payment", key=receipt_key,
            json={"payment_method": "cash"})
        assert paid["payment_status"] == "paid"
        paid_again = await call("POST", f"/v1/bookings/{booking}/payment", key=receipt_key,
            json={"payment_method": "cash"})
        assert paid_again["payment_status"] == "paid"
        states.append("collected")
        completed = await call("POST", f"/v1/bookings/{booking}/complete")
        assert completed["status"] == "completed"
        states.append("completed")
        customer = await call("GET", f"/v1/bookings/{booking}", "customer")
        assert customer["status"] == "completed" and customer["payment_status"] == "paid"
        receipts = (await connection.execute(text(
            "select count(*) from public.booking_payments where booking_id=:id and channel='manual'"
        ), {"id": booking})).scalar_one()
        assert receipts == 1
        passed(phase, states=states, manual_receipts=receipts,
            collection_semantics="paid payment state, not a booking-status enum")

        phase = "customer_cancellation_lifecycle"
        pending, _ = await create(2)
        cancelled = await call("POST", f"/v1/bookings/{pending['id']}/cancel", "customer", json={})
        assert cancelled["status"] == "cancelled"
        passed(phase)

        phase = "no_show_lifecycle"
        pending, _ = await create(3)
        booking = pending["id"]
        await call("POST", f"/v1/bookings/{booking}/approve")
        await call("POST", f"/v1/bookings/{booking}/no-show", expected=422)
        # Only move this synthetic appointment's clock; status must change via API.
        await connection.execute(text("update public.bookings set "
            "start_datetime=now()-interval '2 hours',end_datetime=now()-interval '1 hour' "
            "where id=:id and salon_id=:salon"), {"id": booking, "salon": ids["salon"]})
        missed = await call("POST", f"/v1/bookings/{booking}/no-show")
        assert missed["status"] == "no_show"
        passed(phase, early_no_show_rejected=True, synthetic_clock_adjustment=True)

        phase = "provider_disabled_payment_refund_boundaries"
        config = await call("GET", "/v1/payments/config", "customer")
        assert config["enabled"] is False
        await call("POST", f"/v1/bookings/{booking}/payments/intent", "customer", expected=503, json={})
        await call("POST", f"/v1/bookings/{booking}/payments/{uuid4()}/refund", expected=503, json={})
        passed(phase, provider_calls=0)
        report["checks"].append({"check": "provider_payment_failure_and_refund_settlement",
            "status": "blocked", "reason": "No configured synthetic payment sandbox; providers remain disabled. HTTP 503 boundaries do not verify payment failure/refund settlement."})
    except Exception as error:
        if not any(item["check"] == phase and item["status"] == "failed" for item in report["checks"]):
            report["checks"].append({"check": phase, "status": "failed", "error_type": type(error).__name__})

    phase = "simultaneous_http_same_slot"
    try:
        date = (datetime.fromisoformat(payload["start_datetime"]) + timedelta(days=5)).date()
        slots = await call("GET", "/v1/availability", "customer", params={
            "staff_id": ids["staff"], "date": date.isoformat(), "service_ids": ids["service"],
        })
        assert slots
        body = {**payload, "start_datetime": slots[0]["slot_start"]}
        responses = await asyncio.gather(*(
            api.post("/v1/bookings", json=body, headers={**headers[role], "Idempotency-Key": str(uuid4())})
            for role in ("customer", "outsider")
        ))
        statuses = sorted(response.status_code for response in responses)
        count = (await connection.execute(text(
            "select count(*) from public.bookings where salon_id=:salon and staff_id=:staff "
            "and start_datetime=cast(:start as timestamptz)"
        ), {**ids, "start": datetime.fromisoformat(body["start_datetime"])})).scalar_one()
        assert statuses == [201, 409] and count == 1
        passed(phase, response_statuses=statuses, rows_for_slot=count,
            limitation="HTTP requests overlap; rollback fixture serializes DB sessions. Does not pass independent-connection race gate.")
    except Exception as error:
        report["checks"].append({"check": phase, "status": "failed", "error_type": type(error).__name__})

    phase = "duplicate_booking_without_redis"
    paused = False
    try:
        await redis_control("pause")
        paused = True
        key = str(uuid4())
        created, body = await create(4, key=key)
        replay = await call("POST", "/v1/bookings", "customer", 201, key=key, json=body)
        assert replay["id"] == created["id"]
        count = (await connection.execute(text(
            "select count(*) from public.bookings where salon_id=:salon and staff_id=:staff "
            "and start_datetime=cast(:start as timestamptz)"
        ), {**ids, "start": datetime.fromisoformat(body["start_datetime"])})).scalar_one()
        assert count == 1
        passed(phase, requests=2, distinct_booking_ids=1, rows_for_slot=count,
            redis_fault="real isolated container paused; Redis commands timed out")
    except Exception as error:
        if not any(item["check"] == phase and item["status"] == "failed" for item in report["checks"]):
            report["checks"].append({"check": phase, "status": "failed", "error_type": type(error).__name__})
    finally:
        if paused:
            await redis_control("unpause")
    report["lifecycle_fixture"] = {"business_changes": "outer transaction rollback", "schema_changes": False}


if __name__ == "__main__":
    print(json.dumps({"usage": "Run mumbai_refresh_checks.py --acceptance; this module does not bind an environment."}))
