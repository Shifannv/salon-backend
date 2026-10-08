"""Opt-in service migration/API round trip on an explicitly disposable local DB.

SERVICE_PRESENTATION_TEST_DB must point to localhost; no runtime database is used.
All fixtures and migration changes are rolled back in an isolated schema.
"""

import importlib.util
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_authenticated_session, get_cache, get_current_actor, get_session
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.main import app
from tests.conftest import make_owner
from tests.unit.test_cache_integration import InMemoryCache

TEST_DB = os.environ.get("SERVICE_PRESENTATION_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.mark.asyncio
async def test_migration_and_service_api_round_trip():
    assert urlsplit(TEST_DB).hostname in {"localhost", "127.0.0.1", "::1"}
    engine = create_async_engine(TEST_DB)
    schema = "service_test_" + uuid4().hex
    salon_id, other_salon, category_id, subcategory_id, old_id = [str(uuid4()) for _ in range(5)]
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0016_service_presentation.py"
    spec = importlib.util.spec_from_file_location("service_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements = []
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.upgrade()
    cache = InMemoryCache()
    actor = make_owner()
    original_overrides = app.dependency_overrides.copy()
    try:
        async with engine.connect() as conn:
            transaction = await conn.begin()
            await conn.execute(text(f'create schema "{schema}"'))
            await conn.execute(text(f'set local search_path to "{schema}"'))
            fixtures = [
                "create table service_categories (id uuid primary key, name text, sort_order int, is_active bool)",
                "create table service_subcategories (id uuid primary key, category_id uuid references service_categories, name text, sort_order int, is_active bool)",
                "create table salons (id uuid primary key, is_active bool, profile_completed bool, approval_status text)",
                "create table services (id uuid primary key default gen_random_uuid(), salon_id uuid references salons, subcategory_id uuid references service_subcategories, name text not null, description text, duration_minutes int not null, price numeric not null, is_active bool not null, created_at timestamptz default now(), updated_at timestamptz default now())",
                "create table staff (id uuid primary key, salon_id uuid, is_active bool)",
                "create table staff_services (staff_id uuid, service_id uuid, is_active bool)",
                f"insert into service_categories values ('{category_id}', 'Catalog category', 0, true)",
                f"insert into service_subcategories values ('{subcategory_id}', '{category_id}', 'Catalog subcategory', 0, true)",
                f"insert into salons values ('{salon_id}', true, true, 'approved'), ('{other_salon}', true, true, 'approved')",
                f"insert into services (id, salon_id, subcategory_id, name, duration_minutes, price, is_active) values ('{old_id}', '{salon_id}', '{subcategory_id}', 'Old service', 30, 100, true)",
                f"insert into staff values ('{salon_id}', '{salon_id}', true)",
                f"insert into staff_services values ('{salon_id}', '{old_id}', true)",
            ]
            for sql in [*fixtures, *statements]:
                await conn.execute(text(sql))
            async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as session:
                repo = PlatformRepository(session)

                async def session_dependency():
                    yield session

                async def owned_salon(_repo, actor_id):
                    return {"id": salon_id if actor_id == actor.id else other_salon}

                async def qr_salon(_repo, token):
                    return {"id": salon_id, "name": "Salon", "timezone": "Asia/Kolkata",
                            "approval_mode": "auto", "services": await repo.list_public_services(salon_id)}

                app.dependency_overrides.update({
                    get_authenticated_session: session_dependency, get_session: session_dependency,
                    get_current_actor: lambda: actor, get_cache: lambda: cache,
                })
                with (
                    patch.object(PlatformRepository, "get_owner_salon", owned_salon),
                    patch.object(PlatformRepository, "get_public_salon", AsyncMock()),
                    patch.object(PlatformRepository, "get_salon_by_qr", qr_salon),
                    patch.object(PlatformRepository, "_default_service_subcategory_id", AsyncMock(return_value=subcategory_id)),
                    patch.object(settings, "r2_public_url", "https://media.example.com"),
                ):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        owner_path = "/v1/salons/me/services"
                        public_path = f"/v1/salons/{salon_id}/services"
                        for invalid in ({"category_name": " "}, {"photo_url": "file:///photo.jpg"},
                                        {"unknown": True}):
                            response = await client.post(owner_path, json={
                                "name": "Invalid", "duration_minutes": 30, "price": 100, **invalid,
                            })
                            assert response.status_code == 422, response.text
                        old = (await client.get(owner_path)).json()[0]
                        assert old["category_name"] == "Catalog category" and old["photo_url"] is None
                        payload = {"name": "Nails", "duration_minutes": 30, "price": 250,
                                   "description": "Polish", "category_name": " Nail care ",
                                   "subcategory_name": "Manicure",
                                   "photo_url": f"https://media.example.com/salon-images/{salon_id}/one.jpg"}
                        response = await client.post(owner_path, json=payload)
                        assert response.status_code == 201, response.text
                        created = response.json()
                        service_id = created["id"]
                        assert created["category_name"] == "Nail care"
                        assert created["photo_url"] == payload["photo_url"]
                        await session.execute(text("insert into staff_services values (:staff, :service, true)"), {"staff": salon_id, "service": service_id})
                        await session.commit()

                        async def assert_reads(category, photo):
                            for path in (owner_path, public_path, "/v1/walkin/test-qr"):
                                response = await client.get(path)
                                assert response.status_code == 200, response.text
                                rows = response.json()
                                if isinstance(rows, dict):
                                    rows = rows["services"]
                                service = next(row for row in rows if row["id"] == service_id)
                                assert service["category_name"] == category
                                assert service["photo_url"] == photo

                        await assert_reads("Nail care", payload["photo_url"])
                        changes = {"category_name": "Custom nails", "subcategory_name": "Custom manicure",
                                   "photo_url": payload["photo_url"].replace("one.jpg", "two.jpg")}
                        response = await client.patch(f"{owner_path}/{service_id}", json=changes)
                        assert response.status_code == 200
                        assert all(response.json()[key] == value for key, value in changes.items())
                        await assert_reads(changes["category_name"], changes["photo_url"])
                        response = await client.patch(f"{owner_path}/{service_id}", json={"photo_url": None, "description": None})
                        assert response.status_code == 200 and response.json()["description"] is None
                        await assert_reads("Custom nails", None)
                        response = await client.patch(f"{owner_path}/{service_id}", json={"price": 300})
                        assert response.status_code == 200 and response.json()["subcategory_name"] == "Custom manicure"
                        await assert_reads("Custom nails", None)
                        response = await client.patch(f"{owner_path}/{service_id}", json={"category_name": None, "subcategory_name": None})
                        assert response.status_code == 200 and response.json()["subcategory_name"] == "Catalog subcategory"
                        await assert_reads("Catalog category", None)
                        app.dependency_overrides[get_current_actor] = lambda: make_owner(id="other-owner")
                        response = await client.patch(f"{owner_path}/{service_id}", json={"name": "Stolen"})
                        assert response.status_code == 404
                        app.dependency_overrides[get_current_actor] = lambda: actor
                        with pytest.raises(ValidationError):
                            await repo.update_owner_service(actor.id, service_id, {"salon_id": other_salon})
                        bulk = await repo.list_public_services_for_salons([salon_id])
                        assert next(row for row in bulk[salon_id] if row["id"] == service_id)["category_name"] == "Catalog category"
                        response = await client.delete(f"{owner_path}/{service_id}")
                        assert response.status_code == 200
                        assert all(row["id"] != service_id for row in (await client.get(public_path)).json())
                        assert all(row["id"] != service_id for row in (await client.get("/v1/walkin/test-qr")).json()["services"])
                        assert (await session.execute(text("select name from service_categories"))).scalar_one() == "Catalog category"
                statements.clear()
                with patch.object(migration.op, "execute", side_effect=statements.append):
                    migration.downgrade()
                for sql in statements:
                    await session.execute(text(sql))
                assert (await session.execute(text("select name from services where id = :id"), {"id": old_id})).scalar_one() == "Old service"
            await transaction.rollback()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        await engine.dispose()
