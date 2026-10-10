"""Website contract against disposable localhost Postgres; never runtime DATABASE_URL."""

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.schemas.admin import AdminSalonOnboardingResponse, AdminSalonResponse
from app.api.v1.schemas.walkin import WalkInSalonResponse
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

TEST_DB = os.environ.get("WEBSITE_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.mark.asyncio
async def test_discovery_migration_review_and_qr_round_trip():
    assert urlsplit(TEST_DB).hostname in {"localhost", "127.0.0.1", "::1"}
    engine = create_async_engine(TEST_DB)
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0019_discovery_placement.py"
    spec = importlib.util.spec_from_file_location("placement_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    schema = "website_test_" + uuid4().hex
    owner_id, admin_id, salon_id, staff_id, service_id = [str(uuid4()) for _ in range(5)]
    statements = []
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.upgrade()
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            await conn.execute(text(f'create schema "{schema}"'))
            await conn.execute(text(f'set local search_path to "{schema}"'))
            fixtures = [
                "create schema auth",
                "create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$",
                "create type salon_approval_status as enum ('pending','approved','rejected')",
                "create table profiles (id uuid primary key, role text, email text, full_name text, phone text, avatar_url text, phone_verified bool, is_active bool)",
                "create function is_super_admin() returns bool language sql as $$ select exists(select 1 from profiles where id=auth.uid() and role='super_admin' and is_active) $$",
                "create table salons (id uuid primary key, owner_id uuid, name text, description text, category text, address text, city text, lat float, lng float, timezone text, working_hours jsonb default '{}', approval_mode text, slot_interval_minutes int default 30, qr_token text unique, profile_completed bool, approval_status salon_approval_status, approved_at timestamptz, approved_by uuid, rejection_reason text, display_priority int default 0, is_active bool, created_at timestamptz default now(), updated_at timestamptz default now(), updated_by uuid)",
                "create table salon_images (id uuid, salon_id uuid, url text, caption text, is_main bool, sort_order int, created_at timestamptz, updated_at timestamptz, is_active bool)",
                "create table service_categories (id uuid, name text, sort_order int, is_active bool)",
                "create table service_subcategories (id uuid, category_id uuid, name text, sort_order int, is_active bool)",
                "create table services (id uuid, salon_id uuid, subcategory_id uuid, name text, description text, duration_minutes int, price numeric, is_active bool, category_name text, subcategory_name text, photo_url text, created_at timestamptz default now(), updated_at timestamptz default now())",
                "create table staff (id uuid, salon_id uuid, profile_id uuid, name text, photo_url text, specialization text, experience text, working_hours jsonb, is_active bool, created_at timestamptz default now(), updated_at timestamptz default now())",
                "create table staff_services (staff_id uuid, service_id uuid, is_active bool)",
                "create table subscription_plans (id uuid, ranking_weight int)",
                "create table salon_subscriptions (salon_id uuid, plan_id uuid, status text, current_period_start timestamptz, current_period_end timestamptz, grace_period_end timestamptz)",
                "create function is_subscription_promotion_active(text,timestamptz,timestamptz,timestamptz) returns bool language sql as $$ select false $$",
                "create function get_salon_by_qr(token text) returns table(id uuid,name text,description text,city text,timezone text,approval_mode text) language sql as $$ select id,name,description,city,timezone,approval_mode from salons where qr_token=token and is_active and profile_completed and approval_status='approved' $$",
            ]
            for sql in fixtures:
                await conn.execute(text(sql))
            for sql in statements:
                await conn.execute(text(sql.replace("search_path = public", f'search_path = "{schema}"')))
            async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as session:
                repo = PlatformRepository(session)
                await session.execute(text("insert into profiles values (:owner,'owner','owner@example.com','Owner','123',null,true,true),(:admin,'super_admin','admin@example.com','Admin',null,null,false,true)"),
                                      {"owner": owner_id, "admin": admin_id})
                await session.execute(text("insert into salons (id,owner_id,name,timezone,approval_mode,qr_token,profile_completed,approval_status,is_active) values (:id,:owner,'Shop','UTC','auto','qr-a',true,'pending',true)"),
                                      {"id": salon_id, "owner": owner_id})
                await session.execute(text("insert into services (id,salon_id,subcategory_id,name,duration_minutes,price,is_active) values (:id,:salon,:id,'Cut',30,100,true)"),
                                      {"id": service_id, "salon": salon_id})
                await session.execute(text("insert into service_categories values (:id,'Hair',0,true)"), {"id": service_id})
                await session.execute(text("insert into service_subcategories values (:id,:id,'Cut',0,true)"), {"id": service_id})
                await session.execute(text("insert into staff (id,salon_id,name,is_active) values (:id,:salon,'Barber',true)"), {"id": staff_id, "salon": salon_id})
                await session.execute(text("insert into staff_services values (:staff,:service,true)"), {"staff": staff_id, "service": service_id})
                review = AdminSalonResponse(**(await repo.admin_list_salons(None, 20, 0, "pending"))[0])
                assert review.owner_phone == "123" and review.approval_status == "pending"
                submission = AdminSalonOnboardingResponse(**await repo.admin_get_onboarding(salon_id))
                assert submission.services[0].id == service_id
                assert submission.staff[0].id == staff_id
                await session.execute(text("select set_config('request.jwt.claim.sub', :actor, true)"), {"actor": owner_id})
                with pytest.raises(DBAPIError):
                    async with session.begin_nested():
                        await session.execute(text("update salons set home_placement='top' where id=:id"), {"id": salon_id})
                await session.execute(text("select set_config('request.jwt.claim.sub', :actor, true)"), {"actor": admin_id})
                await repo.admin_set_salon_approval(salon_id, "approved", admin_id, None)
                await session.execute(text("select set_config('request.jwt.claim.sub', :actor, true)"), {"actor": admin_id})
                updated = await repo.admin_update_salon(salon_id, {"home_placement": "top", "discovery_visibility": "search_only"})
                assert updated["home_placement"] == "top"
                filters = {"search": None, "city": None, "lat": None, "lng": None,
                           "limit": 20, "offset": 0}
                assert await repo.list_salons(**filters, surface="home") == []
                assert (await repo.list_salons(**filters, surface="search"))[0]["id"] == salon_id
                walkin = WalkInSalonResponse(**await repo.get_salon_by_qr("qr-a"))
                assert walkin.id == salon_id and walkin.staff[0].service_ids == [service_id]
                statements.clear()
                with patch.object(migration.op, "execute", side_effect=statements.append):
                    migration.downgrade()
                for sql in statements:
                    await session.execute(text(sql))
                assert (await session.execute(text("select name from salons"))).scalar_one() == "Shop"
            await transaction.rollback()
    finally:
        await engine.dispose()
