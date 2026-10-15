"""Real Alembic/asyncpg deployment from 0014 on a disposable localhost database.

Set MIGRATION_TEST_DB to a local PostgreSQL admin URL with CREATEDB/CREATEROLE.
Never uses runtime DATABASE_URL. Creates and drops only a uniquely named test DB.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

TEST_DB = os.environ.get("MIGRATION_TEST_DB")
BACKEND = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

# 0038–0040 are prepared-only Mumbai migrations with production-specific review guards
# (Supabase-managed privileges that do not exist on a fresh CI postgres).
# The deployable head for automated tests stops here; Mumbai migrations are validated
# separately against a server with the correct pre-conditions.
_TEST_HEAD = "0037_customer_processing_charge"
MIGRATION_HEAD = ScriptDirectory(str(BACKEND / "migrations")).get_current_head()


async def alembic(url, *args):
    env = dict(os.environ, DATABASE_URL=url, ENVIRONMENT="local", PYTHONIOENCODING="utf-8")
    result = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.asyncio
async def test_upgrade_from_0014_to_head_and_account_deletion_downgrade():
    admin_url = make_url(TEST_DB)
    assert admin_url.host in {"localhost", "127.0.0.1", "::1"}
    database = "migration_chain_" + uuid4().hex
    admin = await asyncpg.connect(
        admin_url.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    conn = None
    try:
        # Roles are cluster-wide Supabase prerequisites in this disposable server.
        for role in ("postgres", "anon", "authenticated", "service_role"):
            if not await admin.fetchval("select 1 from pg_roles where rolname=$1", role):
                await admin.execute(f'create role "{role}" nologin')
        await admin.execute(f'create database "{database}"')
        url = admin_url.set(database=database, drivername="postgresql+asyncpg")
        conn = await asyncpg.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False)
        )
        await conn.execute("""
            create schema auth;
            create table auth.users (
                id uuid primary key, email text, phone text,
                raw_user_meta_data jsonb not null default '{}',
                raw_app_meta_data jsonb not null default '{}'
            );
            create function auth.uid() returns uuid language sql stable as $$
                select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
            $$;
            create publication supabase_realtime;
        """)
        # Restore the existing 0014 state as SQL; the path under test is the real
        # online Alembic upgrade from that deployed revision, with asyncpg prepares.
        sql = await alembic(
            url.render_as_string(hide_password=False),
            "upgrade",
            "0004_service_duration_slot_steps",
            "--sql",
        )
        await conn.execute(sql)
        # The consolidated baseline already includes 0005's experience column.
        # Reconstruct its historical pre-0005 state only in this fixture database.
        await conn.execute("alter table staff drop column experience")
        sql = await alembic(
            url.render_as_string(hide_password=False),
            "upgrade",
            "0004_service_duration_slot_steps:0014_repair_cancel_reason",
            "--sql",
        )
        await conn.execute(sql)
        assert await conn.fetchval("select version_num from alembic_version") == (
            "0014_repair_cancel_reason"
        )
        user_id = uuid4()
        await conn.execute(
            "insert into auth.users (id, email) values ($1, 'migration@example.test')", user_id
        )

        await alembic(url.render_as_string(hide_password=False), "upgrade", _TEST_HEAD)
        assert await conn.fetchval("select version_num from alembic_version") == _TEST_HEAD
        assert await conn.fetchval("select email from profiles where id=$1", user_id) == (
            "migration@example.test"
        )
        untrusted_id = uuid4()
        await conn.execute(
            """insert into auth.users (id, email, raw_user_meta_data)
               values ($1, 'untrusted-role@example.test', '{"role":"super_admin"}'::jsonb)""",
            untrusted_id,
        )
        assert (
            await conn.fetchval("select role::text from profiles where id=$1", untrusted_id)
            == "customer"
        )
        trusted_id = uuid4()
        await conn.execute(
            """insert into auth.users (id, email, raw_app_meta_data)
               values ($1, 'trusted-role@example.test', '{"role":"owner"}'::jsonb)""",
            trusted_id,
        )
        assert (
            await conn.fetchval("select role::text from profiles where id=$1", trusted_id)
            == "owner"
        )
        for table in (
            "subscription_plans",
            "salon_subscriptions",
            "account_deletion_challenges",
            "account_deletion_requests",
        ):
            assert await conn.fetchval("select to_regclass($1)::text", table) == table
        for table in ("account_deletion_challenges", "account_deletion_requests"):
            assert await conn.fetchval(
                "select relrowsecurity from pg_class where oid=to_regclass($1)", table
            )
        assert (
            await conn.fetchval("""
            select count(*) from information_schema.columns
            where table_schema='public' and table_name='salons'
              and column_name in ('discovery_visibility', 'home_placement')
        """)
            == 2
        )
        assert (
            await conn.fetchval("""
            select count(*) from pg_trigger
            where tgname='media_reference_guard' and not tgisinternal
        """)
            == 7
        )

        # A repeat deploy is a no-op. A rollback without erased data restores the
        # previous schema; reapplying must work with the same online driver too.
        await alembic(url.render_as_string(hide_password=False), "upgrade", _TEST_HEAD)
        await alembic(
            url.render_as_string(hide_password=False), "downgrade", "0020_media_reference_guards"
        )
        assert await conn.fetchval("select to_regclass('account_deletion_requests')") is None
        assert (
            await conn.fetchval("""
            select is_nullable from information_schema.columns
            where table_schema='public' and table_name='salons' and column_name='owner_id'
        """)
            == "NO"
        )
        await alembic(url.render_as_string(hide_password=False), "upgrade", _TEST_HEAD)
        assert await conn.fetchval("select version_num from alembic_version") == _TEST_HEAD
    finally:
        if conn is not None:
            await conn.close()
        await admin.execute(f'drop database if exists "{database}"')
        await admin.close()
