# ruff: noqa: F811  (pytest fixtures are imported by name so this module can use them)
"""Staff earnings API on disposable PostgreSQL: owner-only, tenant-isolated, versioned and idempotent."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.conftest import make_owner
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_owner_finance_api import client_for, key, trial_salon
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_staff_earnings_sql import complete_directly, env, staff_db  # noqa: F401

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

RULES = "/v1/salons/me/commission-rules"


def percent(bps=2000, **extra):
    return {"commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": bps, **extra}


async def booking_for(env):
    f = await trial_salon(env)
    booking = await env.book(f, delta=0)
    assert isinstance(booking, dict), booking
    return f, str(booking["id"])


async def second_barber(env, f):
    barber = str(uuid4())
    await env.sql("insert into staff(id, salon_id, name) values(:i, :s, 'Second barber')", i=barber, s=f["salon"])
    return barber


def staff_actor(f):
    return Profile(id=f["customer"], role=Role.staff, full_name="S", email="s@example.test",
                   phone=None, phone_verified=False, avatar_url=None, is_active=True)


async def test_an_owner_sets_a_rule_and_each_change_is_a_new_version(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        first = await http.post(RULES, headers=key(), json=percent(1000))
        assert first.status_code == 201, first.text
        assert first.json()["version"] == 1 and first.json()["staff_id"] is None
        second = await http.post(RULES, headers=key(), json=percent(2500))
        assert second.json()["version"] == 2
        scoped = await http.post(RULES, headers=key(), json={
            "staff_id": f["staff"], "service_id": f["service"], "commission_type": "FIXED_PER_SERVICE",
            "fixed_amount_paise": 5000,
        })
        assert scoped.status_code == 201 and scoped.json()["version"] == 1
        listed = (await http.get(RULES)).json()
        assert listed["can_write"] is True
        by_scope = {(r["staff_id"], r["service_id"]): r for r in listed["rules"]}
        assert by_scope[(None, None)]["rate_basis_points"] == 2500  # the newest version is the one in force
        assert by_scope[(f["staff"], f["service"])]["fixed_amount_paise"] == 5000
    # the earlier version is kept
    assert (await env.sql("select count(*) as n from staff_commission_rule_versions where salon_id = :s", s=f["salon"]))[0]["n"] == 3


async def test_a_retried_rule_replays_and_a_different_body_with_the_same_key_is_refused(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        headers = key()
        a = await http.post(RULES, headers=headers, json=percent(1500))
        b = await http.post(RULES, headers=headers, json=percent(1500))
        assert a.status_code == 201 and b.json()["id"] == a.json()["id"] and b.json()["replayed"] is True
        assert (await http.post(RULES, headers=headers, json=percent(1600))).status_code == 409
    assert (await env.sql("select count(*) as n from staff_commission_rule_versions where salon_id = :s", s=f["salon"]))[0]["n"] == 1


@pytest.mark.parametrize("bad", [
    {"commission_type": "NONE", "rate_basis_points": 100},
    {"commission_type": "FIXED_PER_SERVICE"},
    {"commission_type": "FIXED_PER_SERVICE", "fixed_amount_paise": 100, "rate_basis_points": 100},
    {"commission_type": "PERCENT_OF_SERVICE_VALUE"},
    {"commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": 10001},
    {"commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": -1},
    {"commission_type": "FIXED_PER_SERVICE", "fixed_amount_paise": -5},
    {"commission_type": "SOMETHING_ELSE"},
    {**percent(), "unknown": 1},
    {**percent(), "effective_from": "2030-01-01T00:00:00"},
])
async def test_an_invalid_rule_is_refused(env, monkeypatch, bad):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.post(RULES, headers=key(), json=bad)).status_code == 422
    assert (await env.sql("select count(*) as n from staff_commission_rule_versions where salon_id = :s", s=f["salon"]))[0]["n"] == 0


async def test_a_rule_cannot_start_in_the_past_or_before_one_already_scheduled(env, monkeypatch):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    now = datetime.now(UTC)
    async with http:
        past = await http.post(RULES, headers=key(), json=percent(effective_from=(now - timedelta(days=2)).isoformat()))
        assert past.status_code == 422
        far = await http.post(RULES, headers=key(), json=percent(effective_from=(now + timedelta(days=400)).isoformat()))
        assert far.status_code == 422
        ahead = await http.post(RULES, headers=key(), json=percent(effective_from=(now + timedelta(days=10)).isoformat()))
        assert ahead.status_code == 201
        sooner = await http.post(RULES, headers=key(), json=percent(3000, effective_from=(now + timedelta(days=5)).isoformat()))
        assert sooner.status_code == 409


async def test_a_rule_can_only_name_this_salons_staff_and_services(env, monkeypatch):
    f = await trial_salon(env)
    other = await env.seed()
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.post(RULES, headers=key(), json=percent(staff_id=other["staff"]))).status_code == 404
        assert (await http.post(RULES, headers=key(), json=percent(service_id=other["service"]))).status_code == 404
        assert (await http.post(RULES, headers=key(), json=percent(staff_id=str(uuid4())))).status_code == 404


async def test_one_salons_rules_are_never_listed_to_another(env, monkeypatch):
    f = await trial_salon(env)
    other = await trial_salon(env)
    mine, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with mine:
        await mine.post(RULES, headers=key(), json=percent(1111))
    theirs, _ = await client_for(env, monkeypatch, make_owner(other["owner"]))
    async with theirs:
        assert (await theirs.get(RULES)).json()["rules"] == []


async def test_staff_and_customers_cannot_touch_commission_or_earnings(env, monkeypatch):
    f, booking = await booking_for(env)
    http, _ = await client_for(env, monkeypatch, staff_actor(f))
    async with http:
        assert (await http.get(RULES)).status_code == 403
        assert (await http.post(RULES, headers=key(), json=percent())).status_code == 403
        assert (await http.get("/v1/salons/me/staff-earnings?from=2026-01-01&to=2026-01-31")).status_code == 403
        assert (await http.post(f"/v1/salons/me/bookings/{booking}/services/{f['service']}/staff",
                                json={"staff_id": f["staff"]})).status_code == 403


async def test_the_owner_names_who_does_a_service_and_can_change_it_until_it_is_finished(env, monkeypatch):
    f, booking = await booking_for(env)
    barber = await second_barber(env, f)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    url = f"/v1/salons/me/bookings/{booking}/services/{f['service']}/staff"
    async with http:
        first = await http.post(url, json={"staff_id": barber})
        assert first.status_code == 200, first.text
        assert (first.json()["staff_id"], first.json()["revision"]) == (barber, 1)
        again = await http.post(url, json={"staff_id": barber})  # naming the same person adds nothing
        assert again.json()["revision"] == 1
        back = await http.post(url, json={"staff_id": f["staff"]})
        assert back.json()["revision"] == 2
    rows = await env.sql("select revision from booking_service_staff where booking_id = :b order by revision", b=booking)
    assert [r["revision"] for r in rows] == [1, 2]
    await complete_directly(env, booking)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        late = await http.post(url, json={"staff_id": barber})
        assert late.status_code == 409


async def test_attribution_refuses_other_salons_bookings_staff_and_unknown_lines(env, monkeypatch):
    f, booking = await booking_for(env)
    other = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    url = f"/v1/salons/me/bookings/{booking}/services/{f['service']}/staff"
    async with http:
        assert (await http.post(url, json={"staff_id": other["staff"]})).status_code == 404
        assert (await http.post(url, json={"staff_id": str(uuid4())})).status_code == 404
        assert (await http.post(f"/v1/salons/me/bookings/{uuid4()}/services/{f['service']}/staff",
                                json={"staff_id": f["staff"]})).status_code == 404
        assert (await http.post(f"/v1/salons/me/bookings/{booking}/services/{uuid4()}/staff",
                                json={"staff_id": f["staff"]})).status_code == 404
    thief, _ = await client_for(env, monkeypatch, make_owner(other["owner"]))
    async with thief:  # another owner cannot reach this salon's booking at all
        assert (await thief.post(url, json={"staff_id": other["staff"]})).status_code == 404


async def test_earnings_report_what_each_person_earned_from_completed_services(env, monkeypatch):
    f, booking = await booking_for(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    today = datetime.now(UTC).date()
    window = f"from={today - timedelta(days=1)}&to={today + timedelta(days=1)}"
    async with http:
        assert (await http.post(RULES, headers=key(), json=percent(2000))).status_code == 201
        before = (await http.get(f"/v1/salons/me/staff-earnings?{window}")).json()
        assert before["staff"] == [] and before["commission_paise"] == 0
    paid = await env.collect(f, {"id": booking}, method="cash")
    assert isinstance(paid, dict), paid
    done = await env.complete(f, {"id": booking})
    assert isinstance(done, dict), done
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        report = (await http.get(f"/v1/salons/me/staff-earnings?{window}")).json()
    assert report["services_completed"] == 1 and report["service_value_paise"] == 25_000
    assert report["commission_paise"] == 5_000
    assert [(s["staff_id"], s["services_completed"], s["commission_paise"]) for s in report["staff"]] == [(f["staff"], 1, 5_000)]
    assert report["staff"][0]["staff_name"]


async def test_earnings_never_include_another_salons_services(env, monkeypatch):
    f, booking = await booking_for(env)
    other = await trial_salon(env)
    assert isinstance(await env.collect(f, {"id": booking}, method="cash"), dict)
    assert isinstance(await env.complete(f, {"id": booking}), dict)
    http, _ = await client_for(env, monkeypatch, make_owner(other["owner"]))
    today = datetime.now(UTC).date()
    async with http:
        report = (await http.get(f"/v1/salons/me/staff-earnings?from={today - timedelta(days=1)}&to={today + timedelta(days=1)}")).json()
    assert report["staff"] == [] and report["service_value_paise"] == 0


@pytest.mark.parametrize("query", [
    "from=2026-02-01&to=2026-01-01", "from=2025-01-01&to=2026-06-01", "from=nope&to=2026-01-01", "to=2026-01-01",
])
async def test_an_invalid_date_range_is_refused(env, monkeypatch, query):
    f = await trial_salon(env)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.get(f"/v1/salons/me/staff-earnings?{query}")).status_code == 422


# --------------------------------------------------------------------------- staff detail and the split (F19)
async def beard_service(env, f, price=200):
    """A second service the same barber does, so one booking can carry two lines."""
    service = str(uuid4())
    sub = (await env.sql("select subcategory_id::text as s from services where id = :i", i=f["service"]))[0]["s"]
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(
            text("insert into services(id, salon_id, subcategory_id, name, duration_minutes, price) values(:i, :s, :sub, 'Beard trim', 30, :p)"),
            {"i": service, "s": f["salon"], "sub": sub, "p": price},
        )
        await session.execute(text("insert into staff_services(staff_id, service_id) values(:st, :sv)"), {"st": f["staff"], "sv": service})
        await session.commit()
    return service


async def two_line_booking(env, f, beard, monkeypatch, *, delta, method, barber=None):
    """Haircut 250 + Beard 200 booked together, optionally with the beard done by another barber, paid and completed."""
    values = env.values(f, delta=delta)
    values["service_ids"] = [f["service"], beard]
    async with env.session() as session:
        await set_actor_context(session, f["customer"])
        booking = await PlatformRepository(session).create_booking(values)
    assert isinstance(booking, dict), booking
    if barber:
        http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
        async with http:
            named = await http.post(f"/v1/salons/me/bookings/{booking['id']}/services/{beard}/staff", json={"staff_id": barber})
            assert named.status_code == 200, named.text
    assert isinstance(await env.collect(f, booking, method=method), dict)
    assert isinstance(await env.complete(f, booking), dict)
    return booking


def window():
    today = datetime.now(UTC).date()
    return f"from={today - timedelta(days=1)}&to={today + timedelta(days=1)}"


async def test_the_bill_is_split_between_the_people_who_did_each_service(env, monkeypatch):
    f = await trial_salon(env)
    beard = await beard_service(env, f)
    hafis, shuhail = f["staff"], await second_barber(env, f)
    await two_line_booking(env, f, beard, monkeypatch, delta=0, method="cash", barber=shuhail)
    await two_line_booking(env, f, beard, monkeypatch, delta=120, method="upi_direct", barber=shuhail)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        report = (await http.get(f"/v1/salons/me/staff-earnings?{window()}")).json()
    people = {s["staff_id"]: s for s in report["staff"]}
    assert (people[hafis]["services_completed"], people[hafis]["service_value_paise"]) == (2, 50_000)
    assert (people[shuhail]["services_completed"], people[shuhail]["service_value_paise"]) == (2, 40_000)
    # each booking was paid 450 in one way; it is shared 250 / 200 by service value
    assert (people[hafis]["collected_cash_paise"], people[hafis]["collected_upi_paise"]) == (25_000, 25_000)
    assert (people[shuhail]["collected_cash_paise"], people[shuhail]["collected_upi_paise"]) == (20_000, 20_000)
    # the totals are the server's sums, and they add up to everything the customers paid
    assert (report["collected_cash_paise"], report["collected_upi_paise"]) == (45_000, 45_000)


async def test_a_processed_refund_lowers_what_was_collected_on_each_service(env, monkeypatch):
    f = await trial_salon(env)
    beard = await beard_service(env, f)
    shuhail = await second_barber(env, f)
    booking = await two_line_booking(env, f, beard, monkeypatch, delta=0, method="cash", barber=shuhail)
    payment = (await env.sql("select id from booking_payments where booking_id = :b", b=booking["id"]))[0]["id"]
    async with env.session() as session:
        await session.execute(text("set local session_replication_role=replica"))
        await session.execute(
            text(
                """insert into payment_refunds(payment_id, booking_id, amount, status, idempotency_key, processed_at)
                   values(:p, :b, 90, 'processed', 'refund-split-1', now())"""
            ),
            {"p": payment, "b": booking["id"]},
        )
        await session.commit()
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        report = (await http.get(f"/v1/salons/me/staff-earnings?{window()}")).json()
    people = {s["staff_id"]: s for s in report["staff"]}
    assert (people[f["staff"]]["collected_cash_paise"], people[shuhail]["collected_cash_paise"]) == (20_000, 16_000)
    assert report["collected_cash_paise"] == 36_000


async def test_the_detail_page_lists_each_service_with_its_share_and_pages_without_repeats(env, monkeypatch):
    f = await trial_salon(env)
    beard = await beard_service(env, f)
    shuhail = await second_barber(env, f)
    await two_line_booking(env, f, beard, monkeypatch, delta=0, method="cash", barber=shuhail)
    await two_line_booking(env, f, beard, monkeypatch, delta=120, method="upi_direct", barber=shuhail)
    await two_line_booking(env, f, beard, monkeypatch, delta=240, method="cash", barber=shuhail)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    url = f"/v1/salons/me/staff-earnings/{f['staff']}?{window()}"
    async with http:
        first = (await http.get(url + "&limit=2")).json()
        assert (first["services_completed"], first["service_value_paise"]) == (3, 75_000)
        assert (first["collected_cash_paise"], first["collected_upi_paise"]) == (50_000, 25_000)
        assert len(first["history"]) == 2 and first["next_cursor"]
        second = (await http.get(url + f"&limit=2&cursor={first['next_cursor']}")).json()
        assert len(second["history"]) == 1 and second["next_cursor"] is None
        seen = [(i["booking_id"], i["service_id"]) for i in first["history"] + second["history"]]
        assert len(set(seen)) == 3
        item = first["history"][0]
        assert item["service_name"] == "Haircut" and item["customer_first_name"] == "Local"
        assert item["service_value_paise"] == 25_000
        assert item["booking_cash_paise"] + item["booking_upi_paise"] == 45_000
        assert sorted(line["staff_name"] for line in item["booking_lines"]) == ["Local test staff", "Second barber"]
        stamps = [i["completed_at"] for i in first["history"]]
        assert stamps == sorted(stamps, reverse=True)


async def test_the_detail_page_is_owner_only_and_never_crosses_salons(env, monkeypatch):
    f = await trial_salon(env)
    other = await trial_salon(env)
    mine, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with mine:
        assert (await mine.get(f"/v1/salons/me/staff-earnings/{other['staff']}?{window()}")).status_code == 404
        assert (await mine.get(f"/v1/salons/me/staff-earnings/{uuid4()}?{window()}")).status_code == 404
        assert (await mine.get(f"/v1/salons/me/staff-earnings/{f['staff']}?{window()}&cursor=not-a-cursor")).status_code == 422
        empty = (await mine.get(f"/v1/salons/me/staff-earnings/{f['staff']}?{window()}")).json()
        assert empty["history"] == [] and empty["services_completed"] == 0 and empty["staff_name"]
    staff, _ = await client_for(env, monkeypatch, staff_actor(f))
    async with staff:
        assert (await staff.get(f"/v1/salons/me/staff-earnings/{f['staff']}?{window()}")).status_code == 403


async def test_the_owner_sees_who_is_doing_each_service_until_it_is_finished(env, monkeypatch):
    f = await trial_salon(env)
    beard = await beard_service(env, f)
    shuhail = await second_barber(env, f)
    values = env.values(f, delta=0)
    values["service_ids"] = [f["service"], beard]
    async with env.session() as session:
        await set_actor_context(session, f["customer"])
        booking = await PlatformRepository(session).create_booking(values)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    url = f"/v1/salons/me/bookings/{booking['id']}/service-staff"
    async with http:
        before = (await http.get(url)).json()
        assert before["can_change"] is True
        assert {line["staff_id"] for line in before["lines"]} == {f["staff"]}  # the booking's own staff by default
        assert {line["service_name"] for line in before["lines"]} == {"Haircut", "Beard trim"}
        named = await http.post(f"/v1/salons/me/bookings/{booking['id']}/services/{beard}/staff", json={"staff_id": shuhail})
        assert named.status_code == 200
        after = {line["service_id"]: line["staff_name"] for line in (await http.get(url)).json()["lines"]}
        assert after[beard] == "Second barber" and after[f["service"]] == "Local test staff"
        assert (await http.get(f"/v1/salons/me/bookings/{uuid4()}/service-staff")).status_code == 404
    assert isinstance(await env.collect(f, booking, method="cash"), dict)
    assert isinstance(await env.complete(f, booking), dict)
    http, _ = await client_for(env, monkeypatch, make_owner(f["owner"]))
    async with http:
        assert (await http.get(url)).json()["can_change"] is False
    other = await trial_salon(env)
    thief, _ = await client_for(env, monkeypatch, make_owner(other["owner"]))
    async with thief:
        assert (await thief.get(url)).status_code == 404
    staff, _ = await client_for(env, monkeypatch, staff_actor(f))
    async with staff:
        assert (await staff.get(url)).status_code == 403
