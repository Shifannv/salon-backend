"""Opt-in media locking/reference SQL on an explicitly disposable localhost DB."""

import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.application.use_cases.media_cleanup import retire_unreferenced_media
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.unit.test_image_processing import gateway, photo_data

TEST_DB = os.environ.get("MEDIA_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable localhost PostgreSQL via MEDIA_TEST_DB")


async def test_publication_lock_and_reference_scan_protect_shared_object():
    assert urlsplit(TEST_DB).hostname in {"localhost", "127.0.0.1", "::1"}
    engine = create_async_engine(TEST_DB)
    schema = "media_test_" + uuid4().hex
    path = "avatars/user-001/photo.jpg"
    gw = gateway()
    gw._client = MagicMock()
    gw._client.head_object.return_value = {"Metadata": gw._processed_metadata(path, photo_data, "image/jpeg"),
                                          "ContentType": "image/jpeg", "ContentLength": len(photo_data)}
    url = gw.get_public_url("images", path)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'create schema "{schema}"'))
            await connection.execute(text(f'set local search_path to "{schema}"'))
            for table, column in (("profiles", "avatar_url"), ("staff", "photo_url"),
                                  ("services", "photo_url"), ("service_categories", "image_url"),
                                  ("service_subcategories", "image_url"), ("salons", "qr_image_url")):
                await connection.execute(text(f"create table {table} ({column} text)"))
            await connection.execute(text("create table salon_images (url text, is_active boolean)"))
            migration_path = Path(__file__).resolve().parents[2] / "migrations/versions/0020_media_reference_guards.py"
            spec = importlib.util.spec_from_file_location("media_guard_migration", migration_path)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            statements = []
            with patch.object(migration.op, "execute", side_effect=statements.append):
                migration.upgrade()
            for statement in statements:
                await connection.execute(text(statement))
            role_result = await connection.execute(text("select exists(select 1 from pg_roles where rolname = 'authenticated')"))
            has_authenticated_role = role_result.scalar_one()
            if has_authenticated_role:
                await connection.execute(text(f'grant usage on schema "{schema}" to authenticated'))
                await connection.execute(text(f'grant select, insert, update on all tables in schema "{schema}" to authenticated'))
            await connection.execute(text("insert into services (photo_url) values (:url)"), {"url": url})

        # PlatformRepository only needs the execute/commit interface for these methods.
        async with engine.connect() as publisher, engine.connect() as cleaner:
            await publisher.execute(text(f'set local search_path to "{schema}"'))
            await cleaner.execute(text(f'set local search_path to "{schema}"'))
            publishing_repo = PlatformRepository(publisher)
            cleanup_repo = PlatformRepository(cleaner)
            assert await publishing_repo.media_reference_guards_installed()
            await publishing_repo.lock_media_url(url)
            available = await cleaner.execute(
                text("select pg_try_advisory_xact_lock(hashtextextended(:url, 0))"), {"url": url})
            assert available.scalar_one() is False
            # An ordinary SQL reference write also participates in the same lock,
            # without calling the API application helper.
            await cleaner.execute(text("set local lock_timeout = '100ms'"))
            with pytest.raises(DBAPIError):
                await cleaner.execute(text("insert into staff (photo_url) values (:url)"), {"url": url})
            await cleaner.rollback()
            await cleaner.execute(text(f'set local search_path to "{schema}"'))
            await publisher.rollback()
            assert not await retire_unreferenced_media(cleanup_repo, gw, "images", path)
            gw._client.delete_object.assert_not_called()
            await cleaner.rollback()
            await cleaner.execute(text(f'set local search_path to "{schema}"'))
            await cleaner.execute(text("delete from services where photo_url = :url"), {"url": url})
            await cleaner.commit()
            await cleaner.execute(text(f'set local search_path to "{schema}"'))
            assert await retire_unreferenced_media(cleanup_repo, gw, "images", path)
            gw._client.delete_object.assert_called_once_with(Bucket="images", Key=path)
            await cleaner.commit()
            if has_authenticated_role:
                # Test the real PostgREST role if the disposable DB provides it;
                # grants are confined to the temporary schema removed below.
                await cleaner.execute(text(f'set local search_path to "{schema}"'))
                await cleaner.execute(text("set local role authenticated"))
                with pytest.raises(DBAPIError, match="backend image upload API"):
                    await cleaner.execute(text("insert into staff (photo_url) values (:url)"), {"url": url})
                await cleaner.rollback()
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'drop schema if exists "{schema}" cascade'))
        await engine.dispose()
