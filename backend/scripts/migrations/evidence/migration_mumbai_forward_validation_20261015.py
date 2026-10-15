"""Rollback-only FastAPI authorization and new erasure behavior; no migration SQL."""

import asyncio
import contextlib
import io
import json
from datetime import datetime, timedelta
from uuid import uuid4

from backend.scripts.migrations.evidence import migration_mumbai_runtime_20261015 as runtime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def erasure_probe(api, connection, ids, payload, first_booking, actors):
    from app.infrastructure.db.repositories.account_deletion_repository import (
        SQLAccountDeletionRepository,
    )

    factory = async_sessionmaker(bind=connection, class_=AsyncSession,
        expire_on_commit=False, join_transaction_mode="create_savepoint")
    actors["other_owner"] = str(uuid4())
    other = actors["other_owner"]
    await connection.execute(text("SELECT set_config('request.jwt.claims','{}',true),set_config('request.jwt.claim.sub','',true)"))
    await connection.execute(text("""INSERT INTO auth.users(id,email,aud,role,raw_app_meta_data,raw_user_meta_data)
        VALUES(:id,:email,'authenticated','authenticated','{"role":"owner"}'::jsonb,'{}'::jsonb)"""),
        {"id": other, "email": f"synthetic-{other}@example.com"})

    async def call(method, path, role, body=None, expected=200):
        response = await api.request(method, path, json=body,
            headers={"x-runtime-role": role, "Idempotency-Key": str(uuid4())})
        if response.status_code != expected:
            runtime.record("erasure_fixture_api", "failed", path=path, actual=response.status_code, expected=expected)
            raise AssertionError("Synthetic fixture API result differs")
        return response.json()

    hours = {day: {"open": "09:00", "close": "18:00"}
             for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
    foreign = await call("POST", "/v1/salons/me/complete-profile", "other_owner",
        {"name": "Synthetic isolation salon", "address": "Synthetic fixture", "city": "Mumbai",
         "lat": 19.076, "lng": 72.8777, "timezone": "Asia/Kolkata", "working_hours": hours,
         "approval_mode": "auto"})
    await connection.execute(text("SELECT set_config('request.jwt.claims','{}',true),set_config('request.jwt.claim.sub','',true)"))
    await connection.execute(text("UPDATE public.salons SET approval_status='approved' WHERE id=:id"), {"id": foreign["id"]})
    service = await call("POST", "/v1/salons/me/services", "other_owner",
        {"subcategory_id": ids["subcategory"], "name": "Synthetic isolation service",
         "duration_minutes": 30, "price": "250.00"}, expected=201)
    staff = await call("POST", "/v1/salons/me/staff", "other_owner",
                       {"name": "Synthetic isolation staff"}, expected=201)
    await connection.execute(text("INSERT INTO public.staff_services(staff_id,service_id) VALUES(:staff,:service)"),
                              {"staff": staff["id"], "service": service["id"]})
    peer = await call("POST", "/v1/bookings", "outsider", {**payload,
        "salon_id": foreign["id"], "staff_id": staff["id"], "service_ids": [service["id"]],
        "start_datetime": (datetime.fromisoformat(payload["start_datetime"]) + timedelta(days=1)).isoformat()}, expected=201)
    await call("GET", f"/v1/bookings/{peer['id']}", "customer", expected=404)
    await call("GET", f"/v1/bookings/{first_booking}", "outsider", expected=404)
    await call("GET", f"/v1/bookings/{peer['id']}", "owner", expected=404)
    await call("GET", f"/v1/bookings/{first_booking}", "other_owner", expected=404)
    await call("GET", f"/v1/bookings/{peer['id']}", "other_owner")
    runtime.record("FastAPI_customer_and_two_owner_booking_isolation", negative_reads=4, expected_status=404)

    async def rows(session):
        result = await session.execute(text("""SELECT id,total_price,status,cancellation_reason_code,
            cancellation_reason_text FROM public.bookings WHERE id=ANY(cast(:ids as uuid[])) ORDER BY id"""),
            {"ids": [first_booking, peer["id"]]})
        return {str(r[0]): tuple(r[1:]) for r in result}

    # Separate savepoints restore the fixture after each full repository erasure.
    # No Auth admin API, R2 deletion or external worker delivery runs here.
    for role in ("customer", "owner"):
        scenario = await connection.begin_nested()
        try:
            async with factory() as session:
                await session.execute(text("SELECT set_config('request.jwt.claims','{}',true),set_config('request.jwt.claim.sub','',true)"))
                await session.execute(text("""UPDATE public.bookings SET cancellation_reason_code=:code,
                    cancellation_reason_text=:reason WHERE id=ANY(cast(:ids as uuid[]))"""),
                    {"code": "Synthetic personal code", "reason": "Synthetic private cancellation text",
                     "ids": [first_booking, peer["id"]]})
                await session.commit()
                before = await rows(session)
                repo = SQLAccountDeletionRepository(session)
                await repo.erase_database(actors[role], role)
                after = await rows(session)
                assert after[first_booking][2:] == (None, None)
                assert before[first_booking][:2] == after[first_booking][:2]
                assert before[peer["id"]] == after[peer["id"]]
                remaining = (await session.execute(text("SELECT count(*) FROM public.profiles WHERE id=:id"),
                                                  {"id": actors[role]})).scalar_one()
                assert remaining == 0
                await repo.erase_database(actors[role], role)
                assert await rows(session) == after
                runtime.record(f"{role}_account_deletion_cancellation_fields_erased",
                    fields_cleared=2, booking_and_amount_retained=True,
                    unrelated_salon_booking_unchanged=True, profile_removed_inside_rollback=True,
                    repeat_idempotent=True, auth_http_delete=False)
        finally:
            await scenario.rollback()


if __name__ == "__main__":
    failure = None
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        try:
            asyncio.run(runtime.main(probe_hook=erasure_probe, fastapi_only=True))
        except Exception as exc:
            failure = {"type": type(exc).__name__,
                       "sqlstate": getattr(getattr(exc, "orig", exc), "sqlstate", None)}
    if failure:
        for line in captured.getvalue().splitlines():
            try:
                partial = json.loads(line)
            except ValueError:
                continue
            for key in ("rollback_booking_results_before_failure", "completion_business_results_before_failure"):
                runtime.RESULTS.extend(partial.get(key, []))
    result = {"destination": runtime.REF, "results": runtime.RESULTS, "failure": failure,
        "sql_errors": runtime.ERRORS, "migrations_or_DDL_or_grants_or_stamp_executed": False,
        "providers": "disabled/fake; API identity injected, JWT not tested"}
    path = runtime.ROOT / "backend/migrations/reviews/migration-mumbai-forward-runtime-2026-10-15.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if failure else 0)
