"""Synthetic Mumbai booking/RLS fixtures live only in a rolled-back transaction."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def rollback_checks(api, app, database, headers_by_role, *, completion=False,
                          actors=None, runtime_setup=None, runtime_probe=None):
    from app.infrastructure.db.session import get_session

    owner = "cd974685-f3ba-43f6-b00e-cd103935fc28"
    customer = "81163183-2757-464e-8f92-b7f5dafe61fa"
    if actors:
        owner, customer = actors["owner"], actors["customer"]
    ids = {name: str(uuid4()) for name in ("salon", "staff", "category", "subcategory", "service")}
    hours = {day: {"open": "09:00", "close": "18:00"}
             for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}
    start = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    results = []
    async with database.engine.connect() as connection:
        outer = await connection.begin()
        factory = async_sessionmaker(bind=connection, class_=AsyncSession,
            expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            if runtime_setup:
                results.extend(await runtime_setup(connection))
            if completion:
                async def onboarding_session():
                    async with factory() as session:
                        yield session
                app.dependency_overrides[get_session] = onboarding_session
                created_salon = await api.post("/v1/salons/me/complete-profile", headers=headers_by_role["owner"],
                    json={"name": "Mumbai rollback test salon", "address": "Synthetic staging fixture",
                          "city": "Mumbai", "lat": 19.076, "lng": 72.8777,
                          "timezone": "Asia/Kolkata", "working_hours": hours, "approval_mode": "auto"})
                results.append({"check": "create_salon_via_owner_onboarding_api", "status": created_salon.status_code})
                assert created_salon.status_code == 200
                ids["salon"] = created_salon.json()["id"]
            async with factory() as session:
                await session.execute(text("select set_config('request.jwt.claims','{}',true),set_config('request.jwt.claim.sub','',true)"))
                if completion:
                    # Approval is a trusted fixture operation; no admin identity is created.
                    await session.execute(text("update public.salons set approval_status='approved' where id=:salon"), ids)
                else:
                    await session.execute(text("""insert into public.salons
                        (id,owner_id,name,profile_completed,approval_status,approval_mode,timezone,working_hours)
                        values(:salon,:owner,'Mumbai rollback test salon',true,'approved','auto','Asia/Kolkata',cast(:hours as jsonb))"""),
                        {**ids, "owner": owner, "hours": json.dumps(hours)})
                await session.execute(text("insert into public.staff(id,salon_id,name) values(:staff,:salon,'Rollback test staff')"), ids)
                await session.execute(text("insert into public.service_categories(id,name,slug) values(:category,'Rollback test category',:slug)"), {**ids, "slug": ids["category"]})
                await session.execute(text("insert into public.service_subcategories(id,category_id,name,slug) values(:subcategory,:category,'Rollback test subcategory',:slug)"), {**ids, "slug": ids["subcategory"]})
                await session.execute(text("""insert into public.services
                    (id,salon_id,subcategory_id,name,duration_minutes,price)
                    values(:service,:salon,:subcategory,'Rollback test service',30,250)"""), ids)
                await session.execute(text("insert into public.staff_services(staff_id,service_id) values(:staff,:service)"), ids)
                await session.commit()

            async def test_session():
                async with factory() as session:
                    yield session

            app.dependency_overrides[get_session] = test_session
            params = {"staff_id": ids["staff"], "date": start.date().isoformat(),
                      "service_ids": [ids["service"]]}
            availability = await api.get("/v1/availability", params=params)
            results.append({"check": "availability_before_booking", "status": availability.status_code,
                            "slots": len(availability.json()) if availability.status_code == 200 else None})
            assert availability.status_code == 200 and availability.json()
            payload = {"salon_id": ids["salon"], "staff_id": ids["staff"],
                       "service_ids": [ids["service"]], "start_datetime": start.isoformat(),
                       "customer_name": "Mumbai rollback test customer", "source": "app",
                       "payment_preference": "pay_at_salon"}
            key = str(uuid4())
            # External push delivery is stubbed; all booking SQL, guards and audit
            # triggers are real. No background connection can outlive the fixture.
            with patch("app.infrastructure.push.outbox_worker.enqueue_and_deliver_notification", new=AsyncMock()):
                created = await api.post("/v1/bookings", json=payload,
                    headers={**headers_by_role["customer"], "Idempotency-Key": key})
                item = {"check": "create_booking_via_api", "status": created.status_code}
                if created.status_code != 201:
                    item["error_code"] = created.json().get("error", {}).get("code")
                results.append(item)
                assert created.status_code == 201
                booking_id = created.json()["id"]
                replay = await api.post("/v1/bookings", json=payload,
                    headers={**headers_by_role["customer"], "Idempotency-Key": key})
                results.append({"check": "idempotent_booking_replay", "status": replay.status_code,
                                "same_booking": replay.json().get("id") == booking_id})
                assert replay.status_code == 201 and replay.json()["id"] == booking_id
                duplicate = await api.post("/v1/bookings", json=payload,
                    headers={**headers_by_role["customer"], "Idempotency-Key": str(uuid4())})
                results.append({"check": "duplicate_booking_rejected", "status": duplicate.status_code})
                assert duplicate.status_code == 409
            for role in ("customer", "owner"):
                response = await api.get("/v1/bookings", headers=headers_by_role[role])
                results.append({"check": "booking_visible_to_party", "role": role,
                                "status": response.status_code,
                                "found": any(row["id"] == booking_id for row in response.json()) if response.status_code == 200 else False})
                assert response.status_code == 200 and any(row["id"] == booking_id for row in response.json())

            if completion:
                from migration_mumbai_completion_business_20261015 import (
                    business_checks,
                )
                if runtime_probe:
                    results.extend(await runtime_probe(connection, ids, payload, booking_id))
                with patch("app.infrastructure.push.outbox_worker.enqueue_and_deliver_notification", new=AsyncMock()):
                    results.extend(await business_checks(api, factory, headers_by_role, ids, payload, booking_id,
                                                          customer_id=customer))
                return results

            # Test grants are uncommitted and roll back with the outer transaction.
            # They allow RLS ownership tests without changing persistent client ACLs.
            # bookings_staff_read queries staff; staff's restrictive policy queries
            # salons. Include those reviewed SELECT dependencies only for this test.
            await connection.execute(text("GRANT SELECT ON public.profiles,public.bookings,public.booking_services,public.staff,public.salons TO authenticated"))
            await connection.execute(text("GRANT EXECUTE ON FUNCTION public.is_super_admin(),public.owns_salon(uuid) TO authenticated"))
            for role, actor, expected in (("customer", customer, 1), ("owner", owner, 1),
                                           ("unrelated_subject", str(uuid4()), 0)):
                await connection.execute(text("select set_config('request.jwt.claim.sub',:actor,true),set_config('request.jwt.claims',:claims,true)"),
                                         {"actor": actor, "claims": json.dumps({"sub": actor})})
                role_savepoint = await connection.begin_nested()
                try:
                    await connection.execute(text("SET LOCAL ROLE authenticated"))
                    visible = (await connection.execute(text("select count(*) from public.bookings where id=:id"), {"id": booking_id})).scalar_one()
                    own_profiles = (await connection.execute(text("select count(*) from public.profiles"))).scalar_one()
                    results.append({"check": "RLS_scoped_reads", "role": role,
                                    "booking_rows": visible, "profile_rows": own_profiles})
                    assert visible == expected and own_profiles == expected
                except Exception:
                    await role_savepoint.rollback()
                    raise
                else:
                    await connection.execute(text("RESET ROLE"))
                    await role_savepoint.commit()
        except Exception as exc:
            print(json.dumps({"rollback_booking_results_before_failure": results,
                              "error_type": type(exc).__name__,
                              "sqlstate": getattr(getattr(exc, "orig", exc), "sqlstate", None)}))
            raise
        finally:
            app.dependency_overrides.pop(get_session, None)
            if outer.is_active:
                await outer.rollback()
    async with database.AsyncSessionLocal() as session:
        remaining = (await session.execute(text("select count(*) from public.salons where id=:id"), {"id": ids["salon"]})).scalar_one()
        grants = (await session.execute(text("select has_table_privilege('authenticated','public.bookings','SELECT')"))).scalar_one()
        results.append({"check": "fixtures_and_temporary_grants_rolled_back",
                        "remaining_fixture_salons": remaining, "persistent_client_booking_select": grants})
        assert remaining == 0 and grants is False
    return results
