"""0041 runs only in a fresh disposable database created by this test."""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.exceptions import ValidationError
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

TEST_DB = os.environ.get("MIGRATION_TEST_DB")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable loopback PostgreSQL")
SQL = Path(__file__).resolve().parents[2] / "migrations/sql/0041_salon_photo_limits.sql"


async def test_description_removal_photo_cleanup_constraints_and_concurrent_uploads():
    assert urlsplit(TEST_DB).hostname in {"127.0.0.1", "localhost", "::1"}
    database = "photo_review_" + uuid4().hex
    admin = await asyncpg.connect(TEST_DB)
    connection = None
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{database}"')
        # Database name is generated locally; runtime database settings are never read.
        target = TEST_DB.rsplit("/", 1)[0] + "/" + database
        connection = await asyncpg.connect(target)
        for role in ("anon", "authenticated"):
            if not await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname=$1", role):
                await admin.execute(f'CREATE ROLE "{role}"')
        await connection.execute("""
            CREATE TYPE approval_mode AS ENUM ('auto','manual');
            CREATE TABLE salons (id uuid PRIMARY KEY, name text, description text, category text,
                city text, timezone text, approval_mode approval_mode, qr_token text,
                is_active boolean DEFAULT true, profile_completed boolean DEFAULT true,
                approval_status text DEFAULT 'approved');
            ALTER TABLE salons ADD COLUMN address text;
            ALTER TABLE salons ADD COLUMN working_hours jsonb DEFAULT '{}';
            ALTER TABLE salons ADD COLUMN accepting_bookings boolean DEFAULT true;
            ALTER TABLE salons ADD COLUMN owner_id uuid;
            CREATE TABLE services (id uuid PRIMARY KEY, description text, category_name text, subcategory_name text);
            ALTER TABLE services ADD COLUMN salon_id uuid;
            CREATE TABLE salon_images (id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                salon_id uuid REFERENCES salons(id), url text NOT NULL, caption text,
                is_main boolean NOT NULL DEFAULT false, sort_order int NOT NULL DEFAULT 0,
                is_active boolean NOT NULL DEFAULT true,
                created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
            CREATE UNIQUE INDEX uq_salon_main_image ON salon_images(salon_id) WHERE is_main;
            CREATE FUNCTION enforce_single_salon_main_image() RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF NEW.is_main THEN
                  UPDATE salon_images SET is_main=false WHERE salon_id=NEW.salon_id AND id<>NEW.id AND is_main;
                END IF;
                RETURN NEW;
              END;
            $$;
            CREATE TRIGGER t_salon_main_image BEFORE INSERT OR UPDATE OF is_main ON salon_images
            FOR EACH ROW EXECUTE FUNCTION enforce_single_salon_main_image();
            CREATE FUNCTION get_salon_by_qr(p_qr_token text)
            RETURNS TABLE(id uuid,name text,description text,city text,timezone text,approval_mode approval_mode)
            LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public AS $$
              SELECT s.id,s.name,s.description,s.city,s.timezone,s.approval_mode FROM salons s WHERE qr_token=p_qr_token;
            $$;
            REVOKE ALL ON FUNCTION get_salon_by_qr(text) FROM PUBLIC;
            GRANT EXECUTE ON FUNCTION get_salon_by_qr(text) TO authenticated;
        """)
        salon, race_salon, service = uuid4(), uuid4(), uuid4()
        for key in (salon, race_salon):
            await connection.execute("INSERT INTO salons(id,name,description,category,city,timezone,approval_mode,qr_token) VALUES ($1,'Test','remove me','keep me','Test city','UTC','auto',$2)", key, str(key))
        await connection.execute("INSERT INTO services VALUES ($1,'remove me','keep category','keep subcategory')", service)
        owner, other_owner, other_service = uuid4(), uuid4(), uuid4()
        await connection.execute("UPDATE salons SET owner_id=$2 WHERE id=$1", salon, owner)
        await connection.execute("UPDATE salons SET owner_id=$2 WHERE id=$1", race_salon, other_owner)
        await connection.execute("UPDATE services SET salon_id=$2 WHERE id=$1", service, salon)
        await connection.execute("INSERT INTO services(id,description,salon_id) VALUES($1,'other owner text',$2)", other_service, race_salon)
        engine = create_async_engine(target.replace("postgresql://", "postgresql+asyncpg://", 1))
        async with AsyncSession(engine) as session:
            await SQLAccountDeletionRepository(session)._scrub_legacy_descriptions({"uid": str(owner)})
            await session.commit()
        assert await connection.fetchval("SELECT description FROM salons WHERE id=$1", salon) is None
        assert await connection.fetchval("SELECT description FROM services WHERE id=$1", service) is None
        assert await connection.fetchval("SELECT description FROM salons WHERE id=$1", race_salon) == "remove me"
        assert await connection.fetchval("SELECT description FROM services WHERE id=$1", other_service) == "other owner text"
        for url, main, order in (("cover", True, 0), ("cover", False, 0), ("one", False, 1),
                                 ("two", False, 2), ("three", False, 3), ("one", False, 4)):
            await connection.execute("INSERT INTO salon_images(salon_id,url,is_main,sort_order) VALUES($1,$2,$3,$4)", salon, url, main, order)
        before_urls = await connection.fetch("SELECT id,url FROM salon_images ORDER BY id")
        before_acl = await connection.fetchval("SELECT proacl::text FROM pg_proc WHERE oid='get_salon_by_qr(text)'::regprocedure")
        async with connection.transaction():
            for statement in SQL.read_text(encoding="utf-8").split("\n-- statement --\n"):
                if statement.strip():
                    await connection.execute(statement)
        assert await connection.fetch("SELECT id,url FROM salon_images ORDER BY id") == before_urls
        assert [r["url"] for r in await connection.fetch("SELECT url FROM salon_images WHERE is_active ORDER BY is_main DESC,sort_order")] == ["cover", "one", "two"]
        assert await connection.fetchval("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('salons','services') AND column_name='description'") == 0
        assert await connection.fetchval("SELECT category FROM salons WHERE id=$1", salon) == "keep me"
        assert await connection.fetchval("SELECT category_name FROM services WHERE id=$1", service) == "keep category"
        assert await connection.fetchval("SELECT description FROM get_salon_by_qr($1)", str(salon)) is None
        assert await connection.fetchval("SELECT proacl::text FROM pg_proc WHERE oid='get_salon_by_qr(text)'::regprocedure") == before_acl
        for query in (
            "INSERT INTO salon_images(salon_id,url) VALUES($1,'four')",
            "UPDATE salon_images SET is_active=true WHERE salon_id=$1 AND url='three'",
            "INSERT INTO salon_images(salon_id,url,is_main) VALUES($1,'second-cover',true)",
        ):
            with pytest.raises(asyncpg.CheckViolationError):
                await connection.execute(query, salon)
        with pytest.raises(asyncpg.UniqueViolationError):
            await connection.execute("UPDATE salon_images SET url='cover' WHERE salon_id=$1 AND url='one' AND is_active", salon)
        await connection.execute("UPDATE salon_images SET url='new-cover' WHERE salon_id=$1 AND is_main", salon)
        async with connection.transaction(isolation="repeatable_read"):
            with pytest.raises(asyncpg.SerializationError):
                async with connection.transaction():
                    await connection.execute("INSERT INTO salon_images(salon_id,url) VALUES($1,'rr')", race_salon)
        await connection.execute("INSERT INTO salon_images(salon_id,url) VALUES($1,'initial')", race_salon)

        async def upload(url):
            c = await asyncpg.connect(target)
            try:
                await c.execute("INSERT INTO salon_images(salon_id,url) VALUES($1,$2)", race_salon, url)
                return "saved"
            except asyncpg.CheckViolationError:
                return "limited"
            finally:
                await c.close()

        assert sorted(await asyncio.gather(upload("race-a"), upload("race-b"))) == ["limited", "saved"]
        async with AsyncSession(engine) as session:
            # After 0041, the same compatibility phase must not query removed columns.
            await SQLAccountDeletionRepository(session)._scrub_legacy_descriptions({"uid": str(owner)})
            repository = PlatformRepository(session)
            with patch.object(repository, "get_owner_salon", AsyncMock(return_value={"id": str(salon)})):
                photos = await repository.list_salon_images(str(salon))
                slide = next(image for image in photos if image["url"] == "two")
                updated = await repository.update_salon_image("owner", slide["id"], {"url": "replacement"})
                assert updated["url"] == "replacement" and not updated["is_main"]
                cover = next(image for image in photos if image["is_main"])
                unchanged_role = await repository.update_salon_image("owner", cover["id"], {"is_main": None, "caption": "Cover"})
                assert unchanged_role["is_main"] is True
                with pytest.raises(ValidationError):
                    await repository.create_salon_image("owner", {"url": "extra"})
                await session.rollback()
            await connection.execute("UPDATE salon_images SET is_active=false WHERE salon_id=$1 AND is_main", salon)
            await connection.execute("INSERT INTO salon_images(salon_id,url,is_main) VALUES($1,'active-cover',true)", salon)
            with (
                patch.object(repository, "list_public_services", AsyncMock(return_value=[])),
                patch.object(repository, "_list_walkin_staff", AsyncMock(return_value=[])),
            ):
                qr = await repository.get_salon_by_qr(str(salon))
                assert qr["image_url"] == "active-cover"
                assert "new-cover" not in {image["url"] for image in qr["images"]}
    finally:
        if engine is not None:
            await engine.dispose()
        if connection is not None:
            await connection.close()
        await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await admin.close()
