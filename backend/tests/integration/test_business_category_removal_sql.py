"""Exercise the actual 0042 upgrade against an isolated loopback database."""

import importlib.util
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DB = os.environ.get("MIGRATION_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable loopback PostgreSQL")
REVISION = Path(__file__).resolve().parents[2] / "migrations/versions/0042_remove_business_category.py"


async def test_upgrade_removes_only_business_category_and_refuses_dependencies():
    assert urlsplit(TEST_DB).hostname in {"127.0.0.1", "localhost", "::1"}
    database = "category_review_" + uuid4().hex
    admin = await asyncpg.connect(TEST_DB)
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
        target = TEST_DB.rsplit("/", 1)[0] + "/" + database
        engine = create_async_engine(target.replace("postgresql://", "postgresql+asyncpg://", 1))
        spec = importlib.util.spec_from_file_location("business_category_revision", REVISION)
        revision = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(revision)

        def upgrade(connection):
            with Operations.context(MigrationContext.configure(connection)):
                revision.upgrade()

        async with engine.begin() as connection:
            for statement in (
                "CREATE TABLE salons(id int PRIMARY KEY, name text, category text)",
                "INSERT INTO salons VALUES(1, 'Studio', 'obsolete')",
                "CREATE TABLE service_categories(id int PRIMARY KEY, name text)",
                "INSERT INTO service_categories VALUES(1, 'Hair Cutting')",
                "CREATE TABLE services(id int PRIMARY KEY, category_name text, subcategory_name text)",
                "INSERT INTO services VALUES(1, 'Hair Cutting', 'Haircut')",
                "CREATE VIEW category_dependency AS SELECT category FROM salons",
            ):
                await connection.execute(text(statement))
        # RESTRICT must refuse, rather than deleting a dependent view silently.
        with pytest.raises(DBAPIError):
            async with engine.begin() as connection:
                await connection.run_sync(upgrade)
        async with engine.begin() as connection:
            assert (await connection.execute(text("SELECT category FROM category_dependency"))).scalar_one() == "obsolete"
            await connection.execute(text("DROP VIEW category_dependency"))
        async with engine.begin() as connection:
            await connection.run_sync(upgrade)
        async with engine.begin() as connection:
            assert (await connection.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='salons' AND column_name='category'"))).scalar_one() == 0
            assert (await connection.execute(text("SELECT name FROM salons"))).scalar_one() == "Studio"
            assert (await connection.execute(text("SELECT name FROM service_categories"))).scalar_one() == "Hair Cutting"
            assert tuple((await connection.execute(text("SELECT category_name, subcategory_name FROM services"))).one()) == ("Hair Cutting", "Haircut")
            await connection.run_sync(upgrade)  # repeat is harmless
        with pytest.raises(RuntimeError, match="permanently removed"):
            revision.downgrade()
    finally:
        if engine:
            await engine.dispose()
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await admin.close()
