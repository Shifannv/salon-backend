"""0060 on disposable local PostgreSQL: newest row wins, rows follow the account, table is private."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.infrastructure.db.repositories.consent_repository import ConsentRepository
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

SQL = Path(__file__).parents[2] / "migrations/sql/0060_user_consents.sql"


@pytest.fixture(scope="module")
def consent_db(changes_db):  # noqa: F811
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
async def env(consent_db):
    environment = SafetyEnv(consent_db)
    yield environment
    await environment.engine.dispose()


async def new_user(env) -> str:
    uid = str(uuid4())
    async with env.session() as session:
        await session.execute(text("insert into auth.users(id,email) values(:i,:e)"), {"i": uid, "e": uid + "@x.test"})
        await session.commit()
    return uid


async def test_the_newest_answer_per_kind_is_the_current_one(env):
    user = await new_user(env)
    async with env.session() as session:
        repo = ConsentRepository(session)
        await repo.record(user, "customer_app", [("terms", "v1", True), ("marketing", "1", True)])
        await repo.record(user, "customer_app", [("terms", "v2", True), ("marketing", "1", False)])
        latest = await repo.latest(user)
    assert latest["terms"] == {"version": "v2", "granted": True}
    assert latest["marketing"]["granted"] is False
    async with env.session() as session:
        rows = (await session.execute(text("select count(*) from user_consents where user_id=cast(:u as uuid)"), {"u": user})).scalar_one()
    assert rows == 4, "history is kept: a change adds rows, nothing is overwritten"


async def test_one_persons_answers_are_not_another_persons(env):
    a, b = await new_user(env), await new_user(env)
    async with env.session() as session:
        await ConsentRepository(session).record(a, "owner_app", [("age_13_plus", "1", True)])
        assert await ConsentRepository(session).latest(b) == {}


async def test_the_database_refuses_unknown_kinds_sources_and_empty_versions(env):
    user = await new_user(env)
    for kind, version, source in (("newsletter", "v1", "customer_app"), ("terms", "", "customer_app"), ("terms", "v1", "email")):
        async with env.session() as session:
            with pytest.raises(IntegrityError):
                await session.execute(text(
                    "insert into user_consents(user_id,kind,version,granted,source) values (cast(:u as uuid),:k,:v,true,:s)"),
                    {"u": user, "k": kind, "v": version, "s": source})
            await session.rollback()


async def test_deleting_the_account_removes_its_consent_rows(env):
    user = await new_user(env)
    async with env.session() as session:
        await ConsentRepository(session).record(user, "walkin_web", [("terms", "v1", True)])
        await session.execute(text("delete from profiles where id=cast(:u as uuid)"), {"u": user})
        await session.commit()
        left = (await session.execute(text("select count(*) from user_consents where user_id=cast(:u as uuid)"), {"u": user})).scalar_one()
    assert left == 0


async def test_browser_facing_roles_have_no_access(env):
    async with env.session() as session:
        privileges = (await session.execute(text(
            "select has_table_privilege('anon','public.user_consents','select') or "
            "has_table_privilege('authenticated','public.user_consents','select') or "
            "has_table_privilege('authenticated','public.user_consents','insert')"))).scalar_one()
        rls = (await session.execute(text("select relrowsecurity from pg_class where oid='public.user_consents'::regclass"))).scalar_one()
    assert privileges is False and rls is True


async def test_backend_role_can_append_but_cannot_modify_consent_evidence(env):
    user = await new_user(env)
    async with env.session() as session:
        await session.execute(text("set local role service_role"))
        # Exercise the table/identity privileges without the owner-only profiles fixture.
        await session.execute(
            text("insert into user_consents(user_id,kind,version,granted,source) "
                 "values(cast(:u as uuid),'terms','v1',true,'customer_app')"),
            {"u": user},
        )
        await session.commit()
    for statement in (
        "update user_consents set granted=false",
        "delete from user_consents",
        "truncate user_consents",
    ):
        async with env.session() as session:
            await session.execute(text("set local role service_role"))
            with pytest.raises(DBAPIError) as error:
                await session.execute(text(statement))
            assert error.value.orig.sqlstate == "42501"
            await session.rollback()
    async with env.session() as session:
        assert (await ConsentRepository(session).latest(user))["terms"]["granted"] is True


async def test_concurrent_submissions_wait_before_allocating_sequence_values(env):
    user = await new_user(env)
    async with env.session() as first, env.session() as second, env.session() as observer:
        first_pid = (await first.execute(text("select pg_backend_pid()"))).scalar_one()
        second_pid = (await second.execute(text("select pg_backend_pid()"))).scalar_one()
        await first.execute(
            text("select id from profiles where id=cast(:u as uuid) for no key update"), {"u": user}
        )
        pending = asyncio.create_task(
            ConsentRepository(second).record(user, "owner_app", [("marketing", "1", False)])
        )
        try:
            blocked = False
            for _ in range(100):
                blocked = (await observer.execute(
                    text("select :first = any(pg_blocking_pids(:second))"),
                    {"first": first_pid, "second": second_pid},
                )).scalar_one()
                if blocked or pending.done():
                    break
                await asyncio.sleep(0.01)
            assert blocked, "later submission must wait for this user's earlier transaction"
            await ConsentRepository(first).record(user, "owner_app", [("marketing", "1", True)])
            await asyncio.wait_for(pending, timeout=5)
            assert (await ConsentRepository(first).latest(user))["marketing"]["granted"] is False
        finally:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
