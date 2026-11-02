"""Admin salon erasure (0058) on the real prepared schema (0038..0058).

The append-only money guards stay in force for everyone else; erase_salon removes one salon and every
row that hangs off it, and puts the guards back. Opt-in like the other SQL suites: MIGRATION_TEST_DB.
"""

import re
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from tests.integration import salon_erasure_support as support
from tests.integration.salon_erasure_support import SQL_DIR, count, seed_money
from tests.integration.test_payment_ledger_sql import TEST_DB

env = support.env
prepared_db = support.prepared_db

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

async def test_erase_salon_removes_everything_including_the_append_only_money_records(env):
    f = await env.seed()
    other = await env.seed()
    ids = await seed_money(env, f)
    await seed_money(env, other)

    owner = (await env.sql("select erase_salon(:s) as owner", s=f["salon"]))[0]["owner"]

    assert str(owner) == f["owner"]
    assert await count(env, "salons", "id = :s", s=f["salon"]) == 0
    for table, column in (
        ("bookings", "salon_id"), ("staff", "salon_id"), ("services", "salon_id"),
        ("booking_payments", "salon_id"), ("salon_payout_requests", "salon_id"),
        ("salon_expenses", "salon_id"), ("support_tickets", "salon_id"),
    ):
        assert await count(env, table, f"{column} = :s", s=f["salon"]) == 0, table
    assert await count(env, "booking_audit_events", "booking_id = :b", b=ids["booking"]["id"]) == 0
    assert await count(env, "payout_proofs", "id = :p", p=ids["proof"]) == 0
    assert await count(env, "payout_audit", "payout_id = :p", p=ids["request"]) == 0
    # Only an opaque tombstone is left.
    job = (await env.sql("select salon_id, status from salon_erasure_jobs"))[0]
    assert (str(job["salon_id"]), job["status"]) == (f["salon"], "erased")
    # The other salon is untouched.
    assert await count(env, "salons", "id = :s", s=other["salon"]) == 1
    assert await count(env, "bookings", "salon_id = :s", s=other["salon"]) == 1
    assert await count(env, "salon_payout_requests", "salon_id = :s", s=other["salon"]) == 1


async def test_the_guards_are_back_in_force_after_an_erase(env):
    f = await env.seed()
    await seed_money(env, f)
    survivor = await env.seed()
    kept = await seed_money(env, survivor)
    await env.sql("select erase_salon(:s)", s=f["salon"])

    disabled = await env.sql(
        """select c.relname, t.tgname from pg_trigger t join pg_class c on c.oid = t.tgrelid
           where c.relnamespace = 'public'::regnamespace and not t.tgisinternal and t.tgenabled = 'D'""")
    assert disabled == []
    for statement in (
        "delete from salon_payout_requests where id = :r",
        "delete from booking_audit_events where booking_id = :b",
        "delete from salon_expenses where salon_id = :s",
    ):
        with pytest.raises(DBAPIError):
            await env.sql(statement, r=kept["request"], b=kept["booking"]["id"], s=survivor["salon"])


async def test_an_unknown_salon_is_refused_and_changes_nothing(env):
    f = await env.seed()
    with pytest.raises(DBAPIError, match="salon_not_found"):
        await env.sql("select erase_salon(:s)", s=str(uuid4()))
    assert await count(env, "salons", "id = :s", s=f["salon"]) == 1


async def test_a_failure_part_way_rolls_everything_back_and_keeps_the_guards(env):
    f = await env.seed()
    await seed_money(env, f)
    # An extra row that nothing in erase_salon deletes, so the final salon delete fails.
    await env.sql("create table if not exists zz_blocker(salon_id uuid references salons(id))")
    await env.sql("insert into zz_blocker(salon_id) values(:s)", s=f["salon"])
    try:
        with pytest.raises(DBAPIError):
            await env.sql("select erase_salon(:s)", s=f["salon"])
        assert await count(env, "bookings", "salon_id = :s", s=f["salon"]) == 1
        assert await count(env, "salon_payout_requests", "salon_id = :s", s=f["salon"]) == 1
        disabled = await env.sql("select 1 from pg_trigger where tgenabled = 'D' and not tgisinternal")
        assert disabled == []
    finally:
        await env.sql("drop table zz_blocker")


async def test_every_table_that_blocks_a_salon_delete_is_handled_by_erase_salon(env):
    """Walk the foreign-key graph: a table with a non-cascading reference toward salons must be listed."""
    handled = set(re.findall(r"'([a-z_]+)'", re.search(
        r"v_tables text\[\] := ARRAY\[(.*?)\];", (SQL_DIR / "0058_admin_salon_erasure.sql").read_text(encoding="utf-8"), re.DOTALL).group(1)))
    edges = await env.sql(
        """select conrelid::regclass::text as child, confrelid::regclass::text as parent, confdeltype as rule
           from pg_constraint where contype = 'f' and connamespace = 'public'::regnamespace""")
    reachable = {"salons"}
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge["parent"] in reachable and edge["child"] not in reachable:
                reachable.add(edge["child"])
                changed = True
    blockers = {e["child"] for e in edges
                if e["parent"] in reachable and e["rule"] in ("a", "r") and e["child"] != e["parent"]}
    missing = blockers - handled - {"profiles"}
    assert not missing, f"erase_salon does not delete from: {sorted(missing)}"
