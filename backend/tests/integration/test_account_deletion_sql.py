"""Opt-in: real PostgreSQL behaviour of migration 0021 and the deletion repository.

Set ACCOUNT_DELETION_TEST_DB to a DISPOSABLE localhost database URL, e.g.
postgresql+asyncpg://postgres:postgres@localhost:5432/scratch . Everything is created
inside a throwaway schema (plus an ``auth.uid()`` stub) and dropped afterwards.
"""

import importlib.util
import os
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.exceptions import DeletionBlockedError, InvalidVerificationCodeError
from app.core.tokens import digest
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)

TEST_DB = os.environ.get("ACCOUNT_DELETION_TEST_DB")
pytestmark = pytest.mark.skipif(
    not TEST_DB, reason="Requires disposable localhost PostgreSQL via ACCOUNT_DELETION_TEST_DB"
)

SCHEMA_SQL = """
create table profiles (
  id uuid primary key, role text not null default 'customer', full_name text, email text,
  phone text, phone_verified boolean not null default false, avatar_url text,
  is_active boolean not null default true,
  created_by uuid references profiles(id), updated_by uuid references profiles(id));
create table salons (
  id uuid primary key default gen_random_uuid(), owner_id uuid not null references profiles(id),
  name text not null, description text, address text, city text, lat double precision,
  lng double precision, qr_token text unique not null default md5(random()::text),
  qr_image_url text, working_hours jsonb not null default '{}', is_active boolean default true,
  created_by uuid references profiles(id), updated_by uuid references profiles(id),
  created_at timestamptz not null default now());
create table salon_images (id uuid primary key default gen_random_uuid(),
  salon_id uuid references salons(id) on delete cascade, url text);
create table staff (id uuid primary key default gen_random_uuid(), salon_id uuid references salons(id),
  profile_id uuid references profiles(id), name text not null, photo_url text,
  specialization text, is_active boolean default true);
create table services (id uuid primary key default gen_random_uuid(),
  salon_id uuid references salons(id), photo_url text);
create table blocked_slots (id uuid primary key default gen_random_uuid(),
  salon_id uuid references salons(id) on delete cascade,
  staff_id uuid references staff(id) on delete cascade);
create table bookings (id uuid primary key default gen_random_uuid(),
  salon_id uuid not null references salons(id), customer_id uuid references profiles(id),
  customer_name text not null, customer_phone text, notes text, status text not null,
  source text not null default 'app',
  check (customer_id is not null or source = 'manual_walkin'),
  end_datetime timestamptz not null, approved_by uuid references profiles(id),
  created_by uuid references profiles(id), updated_by uuid references profiles(id));
create table booking_action_requests (id uuid primary key default gen_random_uuid(),
  booking_id uuid references bookings(id) on delete cascade, status text not null default 'pending',
  reason text, requested_by uuid not null references profiles(id),
  created_by uuid references profiles(id), updated_by uuid references profiles(id));
create table notifications (id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade);
create table device_tokens (id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade);
create table salon_reports (id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references profiles(id), salon_id uuid references salons(id));
create table salon_subscriptions (id uuid primary key default gen_random_uuid(),
  salon_id uuid references salons(id), status text);
create or replace function set_audit_actor() returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    new.created_by := coalesce(new.created_by, auth.uid());
    new.updated_by := coalesce(new.updated_by, auth.uid());
  else
    new.updated_by := coalesce(auth.uid(), old.updated_by);
    new.created_by := old.created_by;
  end if;
  return new;
end $$;
create trigger t_profiles_audit before insert or update on profiles
  for each row execute function set_audit_actor();
create trigger t_salons_audit before insert or update on salons
  for each row execute function set_audit_actor();
create trigger t_bookings_audit before insert or update on bookings
  for each row execute function set_audit_actor();
"""


def migration_statements() -> list[str]:
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0021_account_deletion.py"
    spec = importlib.util.spec_from_file_location("account_deletion_sql_revision", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    with patch.object(migration.op, "execute", side_effect=statements.append):
        migration.upgrade()
    return statements


@pytest.fixture
async def db():
    assert urlsplit(TEST_DB).hostname in {"localhost", "127.0.0.1", "::1"}
    schema = "acct_del_" + uuid4().hex
    admin = create_async_engine(TEST_DB)
    async with admin.begin() as conn:
        await conn.execute(text(f'create schema "{schema}"'))
        await conn.execute(text("create schema if not exists auth"))
        await conn.execute(text(
            "create or replace function auth.uid() returns uuid language sql stable as "
            "$$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$"))
    engine = create_async_engine(
        TEST_DB, connect_args={"server_settings": {"search_path": f'"{schema}",public'},
                               "statement_cache_size": 0})
    async with engine.begin() as conn:
        for statement in SCHEMA_SQL.split(";\n"):
            if statement.strip():
                await conn.execute(text(statement))
        for statement in migration_statements():
            await conn.execute(text(statement))
    try:
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'drop schema if exists "{schema}" cascade'))
        await admin.dispose()


async def run(engine, sql, **params):
    async with AsyncSession(engine) as session:
        result = await session.execute(text(sql), params)
        await session.commit()
        return result.mappings().all() if result.returns_rows else None


async def verified_challenge(engine, user_id: str) -> tuple[str, str]:
    token = "confirm-token-" + uuid4().hex
    async with AsyncSession(engine) as session:
        repo = SQLAccountDeletionRepository(session)
        challenge = await repo.create_challenge(user_id, "email", "hash", 600, 5)
        await repo.mark_verified(str(challenge["id"]), user_id, digest("s" * 32, "confirm", token), 600)
    return str(challenge["id"]), digest("s" * 32, "confirm", token)


async def confirm_and_erase(engine, user_id: str, role: str):
    challenge_id, token_hash = await verified_challenge(engine, user_id)
    async with AsyncSession(engine) as session:
        request = await SQLAccountDeletionRepository(session).confirm_deletion(
            user_id, challenge_id, token_hash)
    async with AsyncSession(engine) as session:
        await SQLAccountDeletionRepository(session).erase_database(user_id, role)
    return request, challenge_id, token_hash


async def test_customer_erasure_keeps_bookings_anonymized_and_removes_profile(db):
    customer, owner, salon, booking = (str(uuid4()) for _ in range(4))
    await run(db, "insert into profiles (id, role, full_name) values (:c,'customer','Alice'),(:o,'owner','Bob')",
              c=customer, o=owner)
    await run(db, "insert into salons (id, owner_id, name) values (:s,:o,'Cuts')", s=salon, o=owner)
    await run(db, """insert into bookings (id, salon_id, customer_id, customer_name, customer_phone, notes,
                     status, end_datetime, approved_by, created_by, updated_by)
                     values (:b,:s,:c,'Alice','+911','allergy','completed', now() - interval '1 day',:c,:c,:c)""",
              b=booking, s=salon, c=customer)
    await run(db, "insert into notifications (user_id) values (:c)", c=customer)
    await run(db, "insert into device_tokens (user_id) values (:c)", c=customer)
    await run(db, "insert into salon_reports (reporter_id, salon_id) values (:c,:s)", c=customer, s=salon)
    await run(db, "insert into booking_action_requests (booking_id, status, reason, requested_by) "
                  "values (:b,'resolved','private',:c)", b=booking, c=customer)

    request, *_ = await confirm_and_erase(db, customer, "customer")

    assert request["status"] == "pending"
    assert await run(db, "select 1 from profiles where id = :c", c=customer) == []
    row = (await run(db, "select * from bookings where id = :b", b=booking))[0]
    assert row["customer_id"] is None and row["customer_name"] == "Deleted customer"
    assert row["customer_phone"] is None and row["notes"] is None
    assert row["created_by"] is None and row["updated_by"] is None and row["approved_by"] is None
    assert (await run(db, "select requested_by, reason from booking_action_requests"))[0]["requested_by"] is None
    assert await run(db, "select 1 from salon_reports") == []
    assert await run(db, "select 1 from notifications") == []
    assert await run(db, "select 1 from device_tokens") == []
    ledger = (await run(db, "select user_id, role, status from account_deletion_requests"))[0]
    assert ledger["role"] == "customer" and ledger["status"] == "pending"


async def test_open_booking_blocks_deletion_and_leaves_account_untouched(db):
    customer, owner, salon = (str(uuid4()) for _ in range(3))
    await run(db, "insert into profiles (id, role) values (:c,'customer'),(:o,'owner')", c=customer, o=owner)
    await run(db, "insert into salons (id, owner_id, name) values (:s,:o,'Cuts')", s=salon, o=owner)
    await run(db, """insert into bookings (salon_id, customer_id, customer_name, status, end_datetime)
                     values (:s,:c,'Alice','confirmed', now() + interval '2 days')""", s=salon, c=customer)
    challenge_id, token_hash = await verified_challenge(db, customer)
    async with AsyncSession(db) as session:
        with pytest.raises(DeletionBlockedError):
            await SQLAccountDeletionRepository(session).confirm_deletion(customer, challenge_id, token_hash)
    assert (await run(db, "select is_active from profiles where id = :c", c=customer))[0]["is_active"]
    assert await run(db, "select 1 from account_deletion_requests") == []
    assert (await run(db, "select status from account_deletion_challenges"))[0]["status"] == "verified"


async def test_owner_erasure_hides_and_scrubs_salon_but_keeps_other_customers_history(db):
    owner, staff_user, customer, salon, booking = (str(uuid4()) for _ in range(5))
    await run(db, "insert into profiles (id, role) values (:o,'owner'),(:s,'staff'),(:c,'customer')",
              o=owner, s=staff_user, c=customer)
    await run(db, "insert into salons (id, owner_id, name, address, city, description, lat, lng, created_by) "
                  "values (:s,:o,'Cuts','1 Main St','Kochi','nice',1,2,:o)", s=salon, o=owner)
    await run(db, "insert into salon_images (salon_id, url) values (:s,'https://m.example/salon-images/a.jpg')", s=salon)
    await run(db, "insert into staff (salon_id, profile_id, name, photo_url) values (:s,:u,'Dee','https://m.example/staff-photos/d.jpg')",
              s=salon, u=staff_user)
    await run(db, "insert into services (salon_id, photo_url) values (:s,'https://m.example/salon-images/svc.jpg')", s=salon)
    await run(db, """insert into bookings (id, salon_id, customer_id, customer_name, status, end_datetime, approved_by)
                     values (:b,:s,:c,'Carol','completed', now() - interval '3 days', :o)""", b=booking, s=salon, c=customer, o=owner)

    request, *_ = await confirm_and_erase(db, owner, "owner")

    assert request["status"] == "pending"
    snapshot = (await run(db, "select salon_name, salon_city, media_keys, step_state from account_deletion_requests"))[0]
    assert snapshot["salon_name"] == "Cuts" and snapshot["salon_city"] == "Kochi"
    assert len(snapshot["media_keys"]) == 3
    assert snapshot["step_state"]["staff_profile_ids"] == [staff_user]
    salon_row = (await run(db, "select * from salons where id = :s", s=salon))[0]
    assert salon_row["owner_id"] is None and salon_row["is_active"] is False
    assert salon_row["address"] is None and salon_row["description"] is None and salon_row["lat"] is None
    assert salon_row["created_by"] is None
    assert await run(db, "select 1 from salon_images") == []
    staff = (await run(db, "select * from staff"))[0]
    assert staff["name"] == "Former staff" and staff["photo_url"] is None
    assert staff["profile_id"] is None and staff["is_active"] is False
    assert (await run(db, "select is_active from profiles where id = :u", u=staff_user))[0]["is_active"] is False
    kept = (await run(db, "select customer_id, customer_name, approved_by from bookings where id = :b", b=booking))[0]
    assert str(kept["customer_id"]) == customer and kept["customer_name"] == "Carol"
    assert kept["approved_by"] is None
    assert await run(db, "select 1 from profiles where id = :o", o=owner) == []


async def test_repeated_confirmation_is_idempotent_and_wrong_hash_is_rejected(db):
    customer = str(uuid4())
    await run(db, "insert into profiles (id, role) values (:c,'customer')", c=customer)
    challenge_id, token_hash = await verified_challenge(db, customer)
    async with AsyncSession(db) as session:
        first = await SQLAccountDeletionRepository(session).confirm_deletion(customer, challenge_id, token_hash)
    async with AsyncSession(db) as session:
        second = await SQLAccountDeletionRepository(session).confirm_deletion(customer, challenge_id, token_hash)
        assert second["id"] == first["id"]
    async with AsyncSession(db) as session:
        with pytest.raises(InvalidVerificationCodeError):
            await SQLAccountDeletionRepository(session).confirm_deletion(customer, challenge_id, "wrong")
    assert len(await run(db, "select 1 from account_deletion_requests")) == 1
