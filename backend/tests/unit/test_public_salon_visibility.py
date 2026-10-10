"""Public API regression tests using repository SQL and an in-memory database.

SQLite executes the production visibility predicates. The image LATERAL join is
replaced with an ordinary join against an empty image table and ILIKE with
SQLite's case-insensitive LIKE for compatibility.
Postgres functions remain covered by the opt-in approval migration tests.
"""

import hashlib
import json
import math
import re
import sqlite3
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects.sqlite import dialect

from app.api.deps import get_cache, get_session
from app.core.exceptions import NotFoundError
from app.main import app
from tests.unit.test_cache_integration import InMemoryCache


class Rows:
    def __init__(self, records):
        self.records = records

    def mappings(self):
        return self

    def all(self):
        return self.records

    def one_or_none(self):
        assert len(self.records) <= 1
        return self.records[0] if self.records else None


class SQLiteSession:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.create_function("least", 2, min)
        self.db.create_function("greatest", 2, max)
        self.db.create_function("md5", 1, lambda value: hashlib.md5(value.encode()).hexdigest())
        for name in ("acos", "cos", "sin", "radians"):
            self.db.create_function(name, 1, getattr(math, name))
        self.db.executescript("""
            create table salons (
                id text primary key, name text, description text, category text,
                address text, city text, lat real, lng real, timezone text,
                working_hours text, approval_mode text, slot_interval_minutes int,
                approval_status text, is_active bool, profile_completed bool,
                display_priority int not null default 0, qr_token text,
                discovery_visibility text not null default 'listed',
                home_placement text not null default 'normal'
            );
            create table salon_images (
                id text, salon_id text, url text, caption text, is_main bool,
                sort_order int, created_at text, updated_at text, is_active bool
            );
            create table services (
                id text, salon_id text, price real, is_active bool, subcategory_id text,
                name text, description text, duration_minutes int, category_name text,
                subcategory_name text, photo_url text
            );
            create table staff (
                id text, salon_id text, name text, photo_url text,
                specialization text, is_active bool
            );
            create table staff_services (staff_id text, service_id text, is_active bool);
            create table service_categories (id text, name text, sort_order int, is_active bool);
            create table service_subcategories (
                id text, category_id text, name text, sort_order int, is_active bool
            );
            create table subscription_plans (
                id text primary key, code text, name text, tier int, ranking_weight int,
                is_active bool
            );
            create table salon_subscriptions (
                id text primary key, salon_id text, plan_id text, status text,
                current_period_start text, current_period_end text, grace_period_end text
            );
        """)
        self.db.execute("insert into service_categories values ('category','Hair',0,1)")
        self.db.execute("insert into service_subcategories values ('subcategory','category','Cut',0,1)")
        self.ids = []
        for number, (status, active, complete) in enumerate([
            ("approved", True, True), ("pending", True, True),
            ("rejected", True, True), ("approved", False, True),
            ("approved", True, False), (None, True, True), ("unknown", True, True),
        ], start=1):
            salon_id = str(UUID(int=number))
            self.ids.append(salon_id)
            self.db.execute(
                "insert into salons (id,name,timezone,working_hours,approval_mode,"
                "slot_interval_minutes,approval_status,is_active,profile_completed) "
                "values (?, 'Salon', 'UTC', '{}', 'automatic', 30, ?, ?, ?)",
                (salon_id, status, active, complete),
            )
            self.db.execute(
                "insert into services (id,salon_id,price,is_active,subcategory_id,name,duration_minutes) "
                "values (?, ?, 100, 1, 'subcategory', 'Haircut', 30)", (salon_id, salon_id),
            )
            self.db.execute("insert into staff (id,salon_id,is_active,name) values (?,?,1,'Barber')",
                            (salon_id, salon_id))
            self.db.execute("insert into staff_services values (?,?,1)", (salon_id, salon_id))

    async def execute(self, statement, values=None):
        # ``compiled.params`` cannot be read after ``render_postcompile=True``
        # on SQLAlchemy 2.0. Use the compiler's expanded state instead.
        compiled = statement.compile(dialect=dialect())
        expanded = compiled.construct_expanded_state(values or {})
        raw = expanded.statement
        # Replace Postgres LATERAL joins with SQLite-compatible equivalents.
        sql = re.sub(
            r"left join lateral \(.*?\) img on true",
            "left join salon_images img on img.salon_id = s.id", raw, flags=re.DOTALL,
        )
        # Replace the subscription promotion LATERAL with a simple left join.
        sql = re.sub(
            r"left join lateral \(.*?is_subscription_promotion_active.*?\) promo on true",
            "left join (select ss2.salon_id, max(sp2.ranking_weight) as weight "
            "from salon_subscriptions ss2 join subscription_plans sp2 on sp2.id = ss2.plan_id "
            "where ss2.status in ('active','trialing') group by ss2.salon_id"
            ") promo on promo.salon_id = s.id",
            sql, flags=re.DOTALL,
        )
        sql = sql.replace(" ilike ", " like ")
        # render_postcompile expands expanding bindparams (`:ids` → `:ids_1,
        # :ids_2, …`) and rewrites the SQL to use positional `?` markers.
        # The expanded state keeps the rendered parameter names in position order.
        positional = [expanded.parameters[name] for name in expanded.positiontup]
        records = []
        for row in self.db.execute(sql, positional):
            record = dict(row)
            if "working_hours" in record:
                record["working_hours"] = json.loads(record["working_hours"])
            records.append(record)
        return Rows(records)


@pytest.fixture
def public_api():
    session = SQLiteSession()
    cache = InMemoryCache()
    overrides = app.dependency_overrides.copy()

    async def database():
        yield session

    app.dependency_overrides[get_session] = database
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app), session, cache
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        session.db.close()


@pytest.mark.parametrize("path", [
    "/v1/salons", "/v1/salons?search=Salon", "/v1/salons?category=Hair",
    "/v1/salons/nearby?latitude=12&longitude=80", "/v1/salons/nearby?category=Hair",
])
def test_list_sources_only_return_approved_active_complete(public_api, path):
    client, session, _ = public_api
    response = client.get(path)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == session.ids[:1]


def test_favorite_ids_cannot_bypass_visibility(public_api):
    client, session, _ = public_api
    response = client.get("/v1/salons", params=[("ids", value) for value in session.ids])
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == session.ids[:1]


@pytest.mark.parametrize("index", range(7))
def test_detail_visibility_on_miss_and_stale_cache(public_api, index):
    client, session, cache = public_api
    salon_id = session.ids[index]
    response = client.get(f"/v1/salons/{salon_id}")
    assert response.status_code == (200 if index == 0 else 404)
    if index != 0:
        assert response.json()["error"]["message"] == "Salon not found"
    # Seed a payload produced while this salon was visible, including old cache keys.
    cache._store[f"salon:{salon_id}:detail"] = {
        "id": salon_id, "name": "Stale", "timezone": "UTC", "working_hours": {},
        "approval_mode": "automatic", "profile_completed": True, "is_active": True,
    }
    cached = client.get(f"/v1/salons/{salon_id}")
    assert cached.status_code == (200 if index == 0 else 404)


@pytest.mark.parametrize("suffix", ["", "/services", "/staff"])
@pytest.mark.parametrize("change", [
    "approval_status='pending'", "approval_status='rejected'", "approval_status=null",
    "approval_status='unknown'", "is_active=0", "profile_completed=0",
])
def test_revocation_blocks_existing_and_late_cache_fills(public_api, suffix, change):
    client, session, cache = public_api
    salon_id = session.ids[0]
    for endpoint in ("", "/services", "/staff"):
        assert client.get(f"/v1/salons/{salon_id}{endpoint}").status_code == 200
    session.db.execute(f"update salons set {change} where id=?", (salon_id,))
    response = client.get(f"/v1/salons/{salon_id}{suffix}")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Salon not found"
    # A cache write after invalidation cannot restore publication either.
    key = f"salon:{salon_id}:{suffix.lstrip('/') or 'detail'}"
    stale = cache._store.pop(key)
    cache._store[key] = stale
    assert client.get(f"/v1/salons/{salon_id}{suffix}").status_code == 404
    assert client.get("/v1/salons").json() == []


def test_cached_walkin_requires_current_database_qr_validation(public_api, monkeypatch):
    client, session, cache = public_api
    repo = AsyncMock()
    monkeypatch.setattr("app.api.v1.routes.walkin.PlatformRepository", lambda _: repo)
    repo.validate_qr_token.return_value = session.ids[0]
    cache._store["walkin:qr:token"] = {
        "id": session.ids[0], "name": "Salon", "timezone": "UTC", "approval_mode": "automatic",
    }
    assert client.get("/v1/walkin/token").status_code == 200
    repo.validate_qr_token.assert_awaited_once_with("token")
    repo.validate_qr_token.side_effect = NotFoundError("Salon not found or not accepting walk-ins")
    response = client.get("/v1/walkin/token")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Salon not found or not accepting walk-ins"
    repo.get_salon_by_qr.assert_not_awaited()


def test_public_openapi_contracts():
    paths = app.openapi()["paths"]
    for path in ["/v1/salons", "/v1/salons/nearby", "/v1/salons/{salon_id}",
                 "/v1/salons/{salon_id}/services", "/v1/salons/{salon_id}/staff",
                 "/v1/walkin/{qr_token}"]:
        operation = paths[path]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert not operation.get("security")
