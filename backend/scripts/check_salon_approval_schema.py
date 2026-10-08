"""Read-only schema verification: python -m scripts.check_salon_approval_schema."""

import asyncio
import json

import asyncpg
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings


async def main() -> None:
    connection = await asyncpg.connect(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
        timeout=15, statement_cache_size=0,
    )
    try:
        async with connection.transaction(readonly=True):
            exists = await connection.fetchval("select to_regclass('public.salons') is not null")
            tracking = await connection.fetchval("select to_regclass('public.alembic_version') is not null")
            revisions = await connection.fetch("select version_num from public.alembic_version") if tracking else []
            columns = await connection.fetch(
                "select column_name from information_schema.columns "
                "where table_schema='public' and table_name='salons' "
                "and column_name in ('approval_status','approved_at','approved_by','rejection_reason')"
            )
            policies = await connection.fetch(
                "select policyname from pg_policies where schemaname='public' "
                "and tablename='salons' and policyname='salons_public_read' "
                "and qual like '%approval_status%'"
            )
        history = ScriptDirectory.from_config(Config("alembic.ini"))
        known = {revision.revision for revision in history.walk_revisions()}
        current = [row["version_num"] for row in revisions]
        found = sorted(row["column_name"] for row in columns)
        print(json.dumps({
            "salons_exists": exists,
            "database_revisions": current,
            "unknown_revisions": [revision for revision in current if revision not in known],
            "local_heads": history.get_heads(),
            "approval_columns": found,
            "approval_schema_present": len(found) == 4,
            "public_read_requires_approval": bool(policies),
        }, indent=2))
    finally:
        await connection.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        # Connection exceptions may contain credentials; report only the exception type.
        print(f"Schema inspection failed ({type(exc).__name__})")
        raise SystemExit(1) from None
