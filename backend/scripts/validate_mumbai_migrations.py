"""Opt-in, read-only Mumbai migration validation. Never executes revision SQL."""

import argparse
import asyncio
import json
import os
import ssl
from pathlib import Path

from alembic.script import ScriptDirectory
from alembic.util import CommandError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.migration_policy import (
    MUMBAI_PROJECT,
    PORTABLE_CI_REVISION,
    PREPARED_MUMBAI_REVISION,
    validate_migration_target,
)


async def validate(args):
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise CommandError("Provide the explicit Mumbai DATABASE_URL secret using postgresql+asyncpg; no local/default connection is authorized")
    script = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "migrations"))
    validate_migration_target(script, PREPARED_MUMBAI_REVISION, url, {
        "migration_policy": "mumbai", "mumbai_project": args.confirm_project,
        "approval_id": args.approval_id, "approval_manifest": args.approval_manifest,
    })
    # Supplied trust material is explicit; never disable hostname/certificate validation.
    tls = ssl.create_default_context(cafile=args.ca_file)
    engine = create_async_engine(url, connect_args={"ssl": tls, "statement_cache_size": 0})
    try:
        async with engine.connect() as connection, connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.execute(text("SET LOCAL statement_timeout='15s'"))
                ssl_enabled = (await connection.execute(text(
                    "select ssl from pg_stat_ssl where pid=pg_backend_pid()"
                ))).scalar_one()
                history = list((await connection.execute(text("select version_num from public.alembic_version"))).scalars())
                managed_roles = (await connection.execute(text(
                    "select count(*) from pg_roles where rolname in ('anon','authenticated','service_role','supabase_admin')"
                ))).scalar_one()
                print(json.dumps({"project_ref": MUMBAI_PROJECT, "read_only": True,
                    "tls": ssl_enabled, "history": history, "managed_roles_present": managed_roles == 4,
                    "portable_target": PORTABLE_CI_REVISION, "prepared_target": PREPARED_MUMBAI_REVISION}))
                if not ssl_enabled or managed_roles != 4 or history != [PORTABLE_CI_REVISION]:
                    raise RuntimeError("Mumbai execution held: TLS, managed prerequisites or reviewed starting history is not ready; do not stamp")
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-project", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--approval-manifest", required=True)
    parser.add_argument("--ca-file", required=True)
    args = parser.parse_args()
    try:
        asyncio.run(validate(args))
    except CommandError as error:
        print(json.dumps({"status": "failed", "reason": str(error), "migration_execution": "not performed"}))
        return 1
    except Exception as error:
        # Driver errors can contain credentials/SQL; report the class only.
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
            "migration_execution": "not performed"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
