"""Disposable local admin demo. Run with --postgres-port for a dedicated test Postgres.

Creates a fresh synthetic database; never drops or reuses an existing database. No .env,
Supabase, storage, payment provider or worker is used. Identity is a fixed synthetic
superadmin, so this server binds ONLY to loopback and must never be deployed.
"""

import argparse
import asyncio
import os
from pathlib import Path
from uuid import uuid4


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-port", type=int, required=True)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    if not 1024 <= args.postgres_port <= 65535 or args.postgres_port == 5432:
        parser.error("Use the dedicated disposable container's published port, never native 5432")
    database = "admin_erase_demo_" + uuid4().hex
    base = f"postgresql://postgres:local-erase-test-only@127.0.0.1:{args.postgres_port}"
    os.environ.update({
        "SALON_ENV_FILE": "__no_admin_demo_environment_file__", "ENVIRONMENT": "test",
        "DATABASE_URL": base.replace("postgresql://", "postgresql+asyncpg://") + "/" + database,
        "MIGRATION_TEST_DB": base + "/postgres", "ADMIN_REQUIRE_MFA": "false",
        "PAYMENT_PROVIDER": "none", "SUBSCRIPTION_PROVIDER": "none", "REDIS_URL": "",
    })

    import uvicorn
    from sqlalchemy import text

    from app.api.deps import get_auth_admin_gateway, get_current_actor
    from app.domain.entities.profile import Role
    from app.main import create_app
    from tests.conftest import make_profile
    from tests.integration.test_admin_salon_erasure_flow import FakeAuth
    from tests.integration.test_checkout_safety_sql import SafetyEnv
    from tests.integration.test_payment_ledger_sql import _build

    async def seed():
        await _build(database)
        env = SafetyEnv(os.environ["DATABASE_URL"])
        try:
            await env.sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role")
            sql_dir = Path(__file__).resolve().parents[1] / "migrations/sql"
            for number in range(38, 59):
                files = list(sql_dir.glob(f"{number:04d}_*.sql"))
                assert len(files) == 1, number
                async with env.session() as session:
                    for statement in files[0].read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                    await session.commit()
            admin_id = str(uuid4())
            await env.sql("insert into auth.users(id, email) values(:i, 'admin@local.example.test')", i=admin_id)
            await env.sql("update profiles set role = 'super_admin' where id = :i", i=admin_id)
            salons = []
            for name in ("Local Delete Demo", "Local Booking Demo"):
                f = await env.seed()
                await env.sql("update salons set name = :n where id = :s", n=name, s=f["salon"])
                if name == "Local Booking Demo":
                    await env.book(f)
                salons.append(f)
            return admin_id, salons
        finally:
            await env.engine.dispose()

    admin_id, salons = asyncio.run(seed())
    app = create_app()

    async def actor():
        return make_profile(id=admin_id, role=Role.super_admin)

    auth = FakeAuth([s["owner"] for s in salons])
    app.dependency_overrides[get_current_actor] = actor
    app.dependency_overrides[get_auth_admin_gateway] = lambda: auth
    print("Disposable admin demo; synthetic superadmin identity; external integrations disabled.", flush=True)
    print("Database:", database, flush=True)
    for s in salons:
        print("Salon:", s["salon"], flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, lifespan="off")


if __name__ == "__main__":
    main()
