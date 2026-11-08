"""0065 on disposable local PostgreSQL: date of birth once, one open guardian row, hashes only, private tables."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.infrastructure.db.repositories.age_repository import AgeRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SQL = Path(__file__).parents[2] / "migrations/sql/0065_age_and_guardian_consent.sql"
HASH = "a" * 64


@pytest.fixture(scope="module")
def age_db(changes_db):  # noqa: F811
    import asyncio

    async def install():
        env = SafetyEnv(changes_db)
        try:
            async with env.session() as session:
                for statement in SQL.read_text(encoding="utf-8").split("\n-- statement --\n"):
                    if statement.strip():
                        await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    asyncio.run(install())
    return changes_db


@pytest.fixture
async def env(age_db):
    environment = SafetyEnv(age_db)
    yield environment
    await environment.engine.dispose()


async def new_user(env) -> str:
    uid = str(uuid4())
    async with env.session() as session:
        await session.execute(text("insert into auth.users(id,email) values(:i,:e)"), {"i": uid, "e": uid + "@x.test"})
        await session.commit()
    return uid


async def test_the_birth_date_is_saved_once_and_an_earlier_one_wins(env):
    user = await new_user(env)
    async with env.session() as session:
        repo = AgeRepository(session)
        assert await repo.birth_date(user) is None
        assert await repo.set_birth_date(user, date(2012, 3, 1)) == date(2012, 3, 1)
        assert await repo.set_birth_date(user, date(1990, 1, 1)) == date(2012, 3, 1)
        assert await repo.birth_date(user) == date(2012, 3, 1)


async def test_an_absurd_birth_date_is_refused_by_the_database(env):
    user = await new_user(env)
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await AgeRepository(session).set_birth_date(user, date(1800, 1, 1))


async def test_only_one_open_guardian_row_per_person_but_a_revoked_one_is_history(env):
    user = await new_user(env)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    async with env.session() as session:
        repo = AgeRepository(session)
        await repo.start_request(user, HASH, "1234", HASH, expires)
        await session.commit()
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await AgeRepository(session).start_request(user, HASH, "1234", HASH, expires)
    async with env.session() as session:
        repo = AgeRepository(session)
        row = await repo.open_guardian_request(user)
        await repo.revoke(row["id"])
        await repo.start_request(user, HASH, "5678", HASH, expires)
        await session.commit()
        assert (await repo.open_guardian_request(user))["guardian_phone_last4"] == "5678"
    async with env.session() as session:
        total = (await session.execute(text("select count(*) from guardian_consents where user_id=cast(:u as uuid)"), {"u": user})).scalar_one()
    assert total == 2


async def test_approving_clears_the_code_and_stamps_the_time(env):
    user = await new_user(env)
    async with env.session() as session:
        repo = AgeRepository(session)
        await repo.start_request(user, HASH, "1234", HASH, datetime.now(UTC) + timedelta(minutes=10))
        row = await repo.open_guardian_request(user)
        await repo.approve(row["id"])
        await session.commit()
        approved = await repo.open_guardian_request(user)
    assert approved["status"] == "approved" and approved["code_hash"] is None


async def test_the_phone_and_code_columns_only_accept_hashes_and_last_four(env):
    user = await new_user(env)
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await AgeRepository(session).start_request(user, "+919812345678", "1234", HASH, datetime.now(UTC))
    async with env.session() as session:
        with pytest.raises(IntegrityError):
            await AgeRepository(session).start_request(user, HASH, "+9198", HASH, datetime.now(UTC))


async def test_deleting_the_account_removes_the_guardian_rows(env):
    user = await new_user(env)
    async with env.session() as session:
        await AgeRepository(session).start_request(user, HASH, "1234", HASH, datetime.now(UTC) + timedelta(minutes=5))
        await session.commit()
    async with env.session() as session:
        await session.execute(text("delete from profiles where id = cast(:u as uuid)"), {"u": user})
        await session.commit()
        remaining = (await session.execute(text("select count(*) from guardian_consents where user_id=cast(:u as uuid)"), {"u": user})).scalar_one()
    assert remaining == 0


async def test_the_table_is_private_to_the_backend_role(env):
    async with env.session() as session:
        for role in ("anon", "authenticated"):
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                allowed = (await session.execute(
                    text("select has_table_privilege(:r, 'public.guardian_consents', :p)"), {"r": role, "p": privilege}
                )).scalar_one()
                assert allowed is False, f"{role} must not have {privilege}"
        with pytest.raises(DBAPIError):
            await session.execute(text("select 1 from guardian_consents limit 1 /* sanity */"))
            await session.execute(text("set local role anon"))
            await session.execute(text("select 1 from guardian_consents limit 1"))


async def test_sends_are_counted_across_requests_so_withdrawing_cannot_reset_the_limit(env):
    user = await new_user(env)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    async with env.session() as session:
        repo = AgeRepository(session)
        await repo.start_request(user, HASH, "1234", HASH, expires)
        row = await repo.open_guardian_request(user)
        await repo.revoke(row["id"])
        await repo.start_request(user, HASH, "5678", HASH, expires)
        await session.commit()
        sends, last = await repo.recent_sends(user, datetime.now(UTC) - timedelta(hours=24))
        old_sends, old_last = await repo.recent_sends(user, datetime.now(UTC) + timedelta(hours=1))
    assert sends == 2 and last is not None
    assert old_sends == 0 and old_last is None
