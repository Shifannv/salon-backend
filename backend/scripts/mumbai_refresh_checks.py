"""Real Mumbai DB/JWT/API + isolated Redis checks with rollback-only business data.

Auth fixtures are created with confirmed synthetic emails (no mail sent), and
deleted in finally. Business writes share an outer rollback transaction. This
cannot prove independent-connection booking concurrency; report that separately.
"""

import asyncio
import json
import logging
import os
import re
import secrets
import sys
import time
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from mumbai_local import ARTIFACTS, BASE, REF, bind, percentiles


async def main(browser=False):
    targets = bind()
    from sqlalchemy import event, text
    from sqlalchemy.engine import make_url
    os.environ["DATABASE_URL"] = make_url(os.environ["DATABASE_URL"]).set(
        host="aws-0-ap-south-1.pooler.supabase.com", port=5432,
        username=f"postgres.{REF}").render_as_string(hide_password=False)
    targets["database_host"] = "aws-0-ap-south-1.pooler.supabase.com"
    logging.disable(logging.CRITICAL)
    import uvicorn
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.infrastructure.cache.redis import get_redis_cache, init_redis_cache
    from app.infrastructure.db.session import MeasuredAsyncSession, engine, get_session
    from app.main import app

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def no_schema_change(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(None, 1)[0].upper() in {"CREATE", "ALTER", "DROP", "GRANT", "REVOKE", "TRUNCATE"}:
            raise RuntimeError("Schema and grant SQL prohibited")

    report = {"targets": targets, "checks": [], "cleanup": {}, "latency_ms": {}}
    ids = {key: str(uuid4()) for key in ("salon", "staff", "category", "subcategory", "service")}
    users, sessions, durations = {}, {}, {}
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    private = ARTIFACTS / "synthetic-sessions.json"
    ledger = ARTIFACTS / "synthetic-users.json"
    admin_headers = {"apikey": os.environ["SUPABASE_ANON_KEY"], "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_ROLE_KEY"]}
    server = None
    server_task = None
    connection = None
    outer = None
    phase = "create_synthetic_auth"

    def passed(name, **facts):
        report["checks"].append({"check": name, "status": "passed", **facts})

    async with httpx.AsyncClient(base_url=BASE, timeout=30) as auth:
        try:
            for role in ("owner", "customer", "outsider"):
                password = secrets.token_urlsafe(32)
                email = f"mumbai-refresh-{uuid4().hex}@example.com"
                created = await auth.post("/auth/v1/admin/users", headers=admin_headers,
                    json={"email": email, "password": password, "email_confirm": True,
                          "app_metadata": {"role": "owner" if role == "owner" else "customer"}})
                if created.status_code not in {200, 201}:
                    raise RuntimeError("Synthetic Auth creation failed")
                users[role] = created.json()["id"]
                ledger.write_text(json.dumps({"users": users, "project": REF}), encoding="utf-8")
                login = await auth.post("/auth/v1/token?grant_type=password",
                    headers={"apikey": os.environ["SUPABASE_ANON_KEY"]}, json={"email": email, "password": password})
                if login.status_code != 200:
                    raise RuntimeError("Synthetic Auth login failed")
                sessions[role] = login.json()
            passed("real_supabase_synthetic_auth", count=3)
            phase = "rollback_business_fixtures"
            connection = await engine.connect()
            outer = await connection.begin()
            factory = async_sessionmaker(connection, class_=MeasuredAsyncSession,
                expire_on_commit=False, join_transaction_mode="create_savepoint")
            lock = asyncio.Lock()

            async def isolated_session():
                async with lock, factory() as session:
                    yield session

            app.dependency_overrides[get_session] = isolated_session
            for role, user in users.items():
                await connection.execute(text("update public.profiles set role=cast(:role as user_role),full_name=:name,phone=:phone,phone_verified=true where id=:id"),
                    {"role": "owner" if role == "owner" else "customer", "name": f"Synthetic {role}",
                     "phone": f"+1555555010{list(users).index(role)}", "id": user})
            hours = {day: {"open": "09:00", "close": "18:00"} for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
            await connection.execute(text("""insert into public.salons
                (id,owner_id,name,profile_completed,approval_status,approval_mode,timezone,working_hours)
                values(:salon,:owner,'Mumbai synthetic refresh salon',true,'approved','auto','Asia/Kolkata',cast(:hours as jsonb))"""),
                {**ids, "owner": users["owner"], "hours": json.dumps(hours)})
            await connection.execute(text("insert into public.staff(id,salon_id,name) values(:staff,:salon,'Synthetic refresh staff')"), ids)
            await connection.execute(text("insert into public.service_categories(id,name,slug) values(:category,'Synthetic refresh category',:slug)"), {**ids, "slug": ids["category"]})
            await connection.execute(text("insert into public.service_subcategories(id,category_id,name,slug) values(:subcategory,:category,'Synthetic refresh subcategory',:slug)"), {**ids, "slug": ids["subcategory"]})
            await connection.execute(text("insert into public.services(id,salon_id,subcategory_id,name,duration_minutes,price) values(:service,:salon,:subcategory,'Synthetic refresh service',30,250)"), ids)
            await connection.execute(text("insert into public.staff_services(staff_id,service_id) values(:staff,:service)"), ids)
            await connection.execute(text("select public.start_salon_trial(:salon, now())"), ids)
            start = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
            params = {"staff_id": ids["staff"], "date": start.date().isoformat(), "service_ids": ids["service"]}
            payload = {"salon_id": ids["salon"], "staff_id": ids["staff"], "service_ids": [ids["service"]],
                       "start_datetime": start.isoformat(), "customer_name": "Synthetic customer", "source": "app", "payment_preference": "pay_at_salon"}
            headers = {role: {"Authorization": "Bearer " + session["access_token"]} for role, session in sessions.items()}
            await init_redis_cache(os.environ["REDIS_URL"])
            config = uvicorn.Config(app, host="127.0.0.1", port=8056, log_config=None, access_log=False, lifespan="off")
            server = uvicorn.Server(config)
            server_task = asyncio.create_task(server.serve())
            while not server.started and not server_task.done():
                await asyncio.sleep(.05)
            assert server.started
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8056", timeout=40) as api:
                async def request(method, path, role=None, **kwargs):
                    started = time.perf_counter()
                    response = await api.request(method, path, headers=headers.get(role, {}), **kwargs)
                    metric_path = re.sub(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", "{id}", path.split("?")[0])
                    durations.setdefault(metric_path, []).append((time.perf_counter()-started)*1000)
                    assert response.status_code < 500, f"API server error at {path.split('?')[0]}"
                    return response

                phase = "salon_service_refresh"
                for _ in range(2):
                    assert (await request("GET", f"/v1/salons/{ids['salon']}")).status_code == 200
                    assert (await request("GET", f"/v1/salons/{ids['salon']}/services")).status_code == 200
                updated = await request("PATCH", "/v1/salons/me", "owner", json={"name": "Mumbai synthetic updated salon"})
                assert updated.status_code == 200
                assert (await request("GET", f"/v1/salons/{ids['salon']}")).json()["name"] == "Mumbai synthetic updated salon"
                assert any(s["name"] == "Mumbai synthetic updated salon" for s in (await request("GET", "/v1/salons", params={"ids": ids["salon"]})).json())
                passed("customer_salon_refresh_after_owner_mutation")
                updated = await request("PATCH", f"/v1/salons/me/services/{ids['service']}", "owner", json={"price": "275"})
                assert updated.status_code == 200
                assert str((await request("GET", f"/v1/salons/{ids['salon']}/services")).json()[0]["price"]) in {"275.00", "275", "275.0"}
                passed("customer_service_refresh_and_redis_invalidation")
                phase = "booking_revalidation_idempotency"
                available = await request("GET", "/v1/availability", params=params)
                assert available.status_code == 200 and available.json()
                key = str(uuid4())
                created = await api.post("/v1/bookings", json=payload, headers={**headers["customer"], "Idempotency-Key": key})
                assert created.status_code == 201
                booking = created.json()["id"]
                replay = await api.post("/v1/bookings", json=payload, headers={**headers["customer"], "Idempotency-Key": key})
                assert replay.status_code == 201 and replay.json()["id"] == booking
                passed("duplicate_request_preserves_idempotency")
                conflict = await api.post("/v1/bookings", json=payload, headers={**headers["customer"], "Idempotency-Key": str(uuid4())})
                assert conflict.status_code == 409
                passed("stale_slot_submission_revalidated_by_postgres")
                for role in ("customer", "owner"):
                    visible = await request("GET", "/v1/bookings", role)
                    assert visible.status_code == 200 and any(row["id"] == booking for row in visible.json())
                passed("customer_booking_visible_to_owner_api")
                hidden = await request("GET", f"/v1/bookings/{booking}", "outsider")
                assert hidden.status_code in {403, 404}
                passed("cross_customer_booking_isolation")
                phase = "owner_availability_mutation"
                pause = await request("PATCH", "/v1/salons/me/settings", "owner", json={"accepting_bookings": False})
                assert pause.status_code == 200
                assert (await request("GET", "/v1/availability", params=params)).json() == []
                assert (await request("GET", "/v1/salons/me", "owner")).json()["accepting_bookings"] is False
                assert (await request("GET", f"/v1/salons/{ids['salon']}")).json()["accepting_bookings"] is False
                passed("owner_mutation_refreshes_customer_and_owner_availability_and_salon")
                await request("PATCH", "/v1/salons/me/settings", "owner", json={"accepting_bookings": True})
                phase = "redis_races"
                cache = get_redis_cache()
                cache_key = f"salon:{ids['salon']}:race"
                assert await cache.get(cache_key) is None
                await cache.invalidate_read_models()
                await cache.set(cache_key, {"outdated": True})
                assert await cache.get(cache_key) is None
                await cache.set(cache_key, {"current": True})
                assert await cache.get(cache_key) == {"current": True}
                await cache.set_idempotency("idempotency:synthetic-refresh", {"booking": booking})
                await cache.invalidate_read_models()
                assert await cache.get(cache_key) is None
                assert (await cache.get_idempotency("idempotency:synthetic-refresh"))["booking"] == booking
                passed("real_redis_late_fill_rejected_and_replay_key_preserved")
                report["checks"].append({"check": "independent_connection_concurrent_booking", "status": "blocked", "reason": "Rollback fixture serializes one database connection; committed booking audits are immutable and cannot be cleaned without changing protections."})
                if browser:
                    phase = "browser"
                    private.write_text(json.dumps({"sessions": sessions, "ids": ids, "params": params, "headers": headers, "project": REF}), encoding="utf-8")
                    child = await asyncio.create_subprocess_exec("node", str(__import__('pathlib').Path(__file__).with_name("mumbai_browser.cjs")), cwd=str(ARTIFACTS))
                    assert await child.wait() == 0
                    passed("playwright_local_flow")
        except Exception as error:
            report["checks"].append({"check": phase, "status": "failed", "error_type": type(error).__name__,
                "sqlstate": getattr(getattr(error, "orig", None), "sqlstate", None)})
        finally:
            if server:
                server.should_exit = True
            if server_task:
                await server_task
            app.dependency_overrides.pop(get_session, None)
            if outer:
                await outer.rollback()
            if connection:
                await connection.close()
            async with engine.connect() as verify:
                remaining = (await verify.execute(text("select count(*) from public.salons where id=:salon"), ids)).scalar_one()
                report["cleanup"]["business_fixture_rows_remaining"] = remaining
            for role, user in users.items():
                deleted = await auth.delete(f"/auth/v1/admin/users/{user}", headers=admin_headers)
                missing = await auth.get(f"/auth/v1/admin/users/{user}", headers=admin_headers)
                report["cleanup"][role] = deleted.status_code in {200, 204} and missing.status_code == 404
            if private.exists():
                private.unlink()
            report["cleanup"]["private_sessions_removed"] = not private.exists()
            await get_redis_cache().delete("idempotency:synthetic-refresh")
            await get_redis_cache().invalidate_read_models()
            await get_redis_cache().close()
            await engine.dispose()
            report["latency_ms"] = {path: {"samples": len(values), **percentiles(values)} for path, values in durations.items()}
            (ARTIFACTS / "staging-checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
    return not any(item["status"] == "failed" for item in report["checks"])


if __name__ == "__main__":
    try:
        success = asyncio.run(main("--browser" in sys.argv))
    except Exception as error:
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__}))
        success = False
    sys.exit(0 if success else 1)
