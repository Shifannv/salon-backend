"""Opt-in PostgreSQL checks in an isolated schema, always rolled back.

Run with SALON_APPROVAL_DB_TESTS=1. No shared table, auth trigger, publication,
or Alembic version is modified. Real Supabase auth.uid() is used with test IDs.
"""

import importlib.util
import json
import os
import re
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.dialects.postgresql.asyncpg import dialect

from app.api.v1.schemas.admin import AdminSalonResponse
from app.api.v1.schemas.platform import OwnerSalonResponse
from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

pytestmark = pytest.mark.skipif(
    os.environ.get("SALON_APPROVAL_DB_TESTS") != "1", reason="Opt-in isolated PostgreSQL test"
)
MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def isolate(sql: str, schema: str) -> str:
    sql = re.sub(r"alter publication[^;]+;", "", sql, flags=re.IGNORECASE)
    return re.sub(r"\bpublic\b", schema, sql)


def migration_sql(path: Path, direction: str) -> list[str]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    statements = []
    with patch.object(module.op, "execute", side_effect=statements.append):
        getattr(module, direction)()
    return statements


async def execute_revision(conn, sql: str, schema: str) -> None:
    """Use the same SQL parser and prepared-statement path as SQLAlchemy/asyncpg."""
    compiled = text(isolate(sql, schema)).compile(dialect=dialect())
    assert not compiled.params, "Migration SQL unexpectedly contains a bind parameter"
    statement = await conn.prepare(str(compiled))
    await statement.fetch()


class RollbackSession:
    """Execute actual repository SQL inside the test's outer rollback transaction."""

    def __init__(self, conn):
        self.conn = conn

    async def execute(self, statement, values=None):
        compiled = statement.compile(dialect=dialect())
        values = values or {}
        records = await self.conn.fetch(
            str(compiled), *(values[name] for name in compiled.positiontup or [])
        )
        return Rows(records)

    async def commit(self):
        # Repository commits stay inside the single rollback-only test transaction.
        pass


class Rows:
    def __init__(self, records):
        self.records = records

    def mappings(self):
        return self

    def all(self):
        return [dict(row) for row in self.records]

    def one_or_none(self):
        assert len(self.records) <= 1
        return dict(self.records[0]) if self.records else None

    def one(self):
        assert len(self.records) == 1
        return dict(self.records[0])

    def scalar_one(self):
        assert len(self.records) == 1
        return self.records[0][0]

    def scalar_one_or_none(self):
        assert len(self.records) <= 1
        return self.records[0][0] if self.records else None


@pytest.mark.asyncio
async def test_upgrade_business_gates_owner_protection_and_downgrade():
    schema = "approval_test_" + uuid4().hex
    conn = await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
        timeout=15, statement_cache_size=0,
    )
    # Match SQLAlchemy's JSON result decoding while keeping SQL parameter strings.
    await conn.set_type_codec(
        "jsonb", schema="pg_catalog", encoder=str, decoder=json.loads, format="text"
    )
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute(f'create schema "{schema}"')
        await conn.execute(f'set local search_path = "{schema}", public, extensions')
        baseline = (MIGRATIONS / "sql" / "001_supabase_schema.sql").read_text(encoding="utf-8")
        # Auth is shared: remove the FK and registration trigger in this fixture only.
        baseline = baseline.replace("references auth.users(id) on delete cascade", "")
        baseline = re.sub(r"create extension[^;]+;", "", baseline, flags=re.IGNORECASE)
        baseline = re.sub(
            r"create trigger t_on_auth_user_created\s+after insert on auth.users\s+"
            r"for each row execute function handle_new_user\(\);", "", baseline,
        )
        assert "after insert on auth.users" not in baseline
        await conn.execute(isolate(baseline, schema))
        # Replay schema history while excluding the shared Realtime publication.
        revisions = sorted((MIGRATIONS / "versions").glob("*.py"))
        approval = next(p for p in revisions if p.stem == "0015_salon_admin_approval")
        priority = next(p for p in revisions if p.stem == "0017_salon_display_priority")
        for path in revisions:
            # The current v3 baseline already contains 0005's experience column.
            if path.stem.startswith(("0001_", "0005_", "0006_", "0015_", "0017_", "0022_")):
                continue
            for sql in migration_sql(path, "upgrade"):
                await conn.execute(isolate(sql, schema))

        owner, admin, customer, legacy_owner = uuid4(), uuid4(), uuid4(), uuid4()
        for user_id, role in [(owner, "owner"), (admin, "super_admin"),
                              (customer, "customer"), (legacy_owner, "owner")]:
            await conn.execute("insert into profiles(id,role) values($1,$2)", user_id, role)
        legacy = await conn.fetchval(
            "insert into salons(owner_id,name,profile_completed) values($1,'Legacy',true) returning id",
            legacy_owner,
        )
        for sql in migration_sql(approval, "upgrade"):
            await execute_revision(conn, sql, schema)
        assert await conn.fetchval("select approval_status::text from salons where id=$1", legacy) == "approved"
        for sql in migration_sql(priority, "upgrade"):
            await execute_revision(conn, sql, schema)
        assert await conn.fetchval("select display_priority from salons where id=$1", legacy) == 0

        salon = await conn.fetchval(
            "insert into salons(owner_id,name,profile_completed,working_hours) "
            "values($1,'Pending',true,$2::jsonb) returning id", owner,
            '{"mon":{"open":"00:00","close":"23:59"},"tue":{"open":"00:00","close":"23:59"},'
            '"wed":{"open":"00:00","close":"23:59"},"thu":{"open":"00:00","close":"23:59"},'
            '"fri":{"open":"00:00","close":"23:59"},"sat":{"open":"00:00","close":"23:59"},'
            '"sun":{"open":"00:00","close":"23:59"}}',
        )
        staff = await conn.fetchval(
            "insert into staff(salon_id,name) values($1,'Barber') returning id", salon
        )
        category = await conn.fetchval(
            "insert into service_categories(name,slug) values('Hair','hair') returning id"
        )
        subcategory = await conn.fetchval(
            "insert into service_subcategories(category_id,name,slug) values($1,'Cut','cut') returning id",
            category,
        )
        service = await conn.fetchval(
            "insert into services(salon_id,subcategory_id,name,duration_minutes,price) "
            "values($1,$2,'Haircut',30,100) returning id", salon, subcategory,
        )
        await conn.execute("insert into staff_services(staff_id,service_id) values($1,$2)", staff, service)
        qr = await conn.fetchval("select qr_token from salons where id=$1", salon)
        repo = PlatformRepository(RollbackSession(conn))
        pending = await repo.admin_list_salons(None, 50, 0, "pending")
        assert [str(row["id"]) for row in pending] == [str(salon)]
        assert AdminSalonResponse(**pending[0]).approval_status == "pending"
        assert OwnerSalonResponse(**await repo.get_owner_salon(str(owner))).approval_status == "pending"

        async def actor(user_id):
            await conn.execute("select set_config('request.jwt.claim.sub',$1,true)", str(user_id))

        async def denied(sql, *args):
            # A savepoint lets subsequent assertions run after an expected SQL rejection.
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with conn.transaction():
                    await conn.execute(sql, *args)

        await actor(owner)
        await denied("update salons set approval_status='approved' where id=$1", salon)
        await denied("update salons set approved_by=$2 where id=$1", salon, owner)
        await denied("update salons set display_priority=5 where id=$1", salon)
        assert not await conn.fetch("select * from get_salon_by_qr($1)", qr)
        assert not await conn.fetch("select * from get_available_slots($1,current_date+1,30)", staff)

        # Exercise actual RLS under the Data API role, rather than bypassing as postgres.
        await conn.execute(f'grant usage on schema "{schema}" to authenticated')
        await conn.execute(f'grant select on all tables in schema "{schema}" to authenticated')
        await conn.execute(f'grant update on "{schema}".salons to authenticated')
        await actor(customer)
        await conn.execute("set local role authenticated")
        try:
            assert not await conn.fetchval("select exists(select 1 from salons where id=$1)", salon)
            assert not await conn.fetchval("select exists(select 1 from staff where id=$1)", staff)
            assert not await conn.fetchval("select exists(select 1 from services where id=$1)", service)
            await actor(owner)
            assert await conn.fetchval("select exists(select 1 from salons where id=$1)", salon)
            assert await conn.fetchval("select exists(select 1 from services where id=$1)", service)
            await denied("update salons set approval_status='approved' where id=$1", salon)
            await actor(admin)
            assert await conn.fetchval("select exists(select 1 from salons where id=$1)", salon)
        finally:
            await conn.execute("reset role")

        await actor(admin)
        updated = await repo.admin_update_salon(str(salon), {"display_priority": 40})
        assert AdminSalonResponse(**updated).display_priority == 40
        assert updated["updated_by"] == admin
        with pytest.raises(asyncpg.CheckViolationError):
            async with conn.transaction():
                await conn.execute("update salons set display_priority=-1 where id=$1", salon)
        approved = await repo.admin_set_salon_approval(str(salon), "approved", str(admin), None)
        assert AdminSalonResponse(**approved).approved_by == str(admin)
        repeated = await repo.admin_set_salon_approval(str(salon), "approved", str(admin), None)
        assert repeated["approved_at"] == approved["approved_at"]
        assert await conn.fetch("select * from get_salon_by_qr($1)", qr)
        slots = await conn.fetch("select * from get_available_slots($1,current_date+1,30)", staff)
        assert slots
        await actor(customer)
        booking = await conn.fetchval(
            f'select "{schema}".create_booking($1,$2,$3::uuid[],$4,\'Customer\',null,\'app\',null)',
            salon, staff, [service], slots[0]["slot_start"],
        )
        assert booking

        await actor(admin)
        await repo.admin_set_salon_approval(str(salon), "rejected", str(admin), "Fix address")
        await actor(owner)
        await denied("update salons set approval_status='approved' where id=$1", salon)
        resubmitted = await repo.complete_owner_salon(str(owner), {"address": "Corrected address"})
        assert resubmitted["approval_status"] == "pending"
        assert resubmitted["rejection_reason"] is None
        assert await conn.fetchval("select approval_status::text from salons where id=$1", salon) == "pending"
        with pytest.raises(asyncpg.PostgresError):
            async with conn.transaction():
                await conn.fetchval(
                    f'select "{schema}".create_booking($1,$2,$3::uuid[],$4,\'Customer\',null,\'app\',null)',
                    salon, staff, [service], slots[1]["slot_start"],
                )

        await actor(admin)
        for sql in migration_sql(approval, "downgrade"):
            await execute_revision(conn, sql, schema)
        assert await conn.fetch("select * from get_salon_by_qr($1)", qr)
        assert not await conn.fetchval(
            "select exists(select 1 from information_schema.columns "
            "where table_schema=$1 and table_name='salons' and column_name='approval_status')", schema
        )
        for sql in migration_sql(approval, "upgrade"):
            await execute_revision(conn, sql, schema)
        for sql in migration_sql(priority, "downgrade"):
            await execute_revision(conn, sql, schema)
        assert not await conn.fetchval(
            "select exists(select 1 from information_schema.columns "
            "where table_schema=$1 and table_name='salons' and column_name='display_priority')", schema
        )
        for sql in migration_sql(priority, "upgrade"):
            await execute_revision(conn, sql, schema)
        assert await conn.fetchval("select display_priority from salons where id=$1", legacy) == 0
    finally:
        await transaction.rollback()
        await conn.close()
