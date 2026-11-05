"""Real PostgreSQL visit allocation: consecutive staff, conflicts, rollback and release."""
import asyncio
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_staff_earnings_sql import staff_db  # noqa: F401

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.fixture(scope="module")
def visit_db(staff_db):  # noqa: F811
    async def install():
        env = SafetyEnv(staff_db)
        try:
            async with env.session() as session:
                source = Path(__file__).parents[2] / "migrations/sql/0061_staff_service_visits.sql"
                for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
                    if statement.strip():
                        await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()
    asyncio.run(install())
    return staff_db


@pytest.fixture
async def visits(visit_db):
    env = SafetyEnv(visit_db)
    yield env
    await env.engine.dispose()


async def menu(env):
    f = await env.seed()
    second, service = str(uuid4()), str(uuid4())
    await env.sql("insert into staff(id,salon_id,name) values(:id,:salon,'Beard specialist')", id=second, salon=f['salon'])
    await env.sql("update services set category_name='Hair Cutting' where id=:id", id=f['service'])
    await env.sql("""insert into services(id,salon_id,subcategory_id,name,duration_minutes,price,category_name)
        select :id,salon_id,subcategory_id,'Beard shape',20,100,'Beard Trimming' from services where id=:base""",
        id=service, base=f['service'])
    await env.sql("insert into staff_services(staff_id,service_id) values(:staff,:service)", staff=second, service=service)
    f.update(second=second, beard=service, segments=[
        {'staff_id': f['staff'], 'service_ids': [f['service']]},
        {'staff_id': second, 'service_ids': [service]},
    ])
    return f


async def create(env, f, key='visit-test-001'):
    async with env.session() as session:
        await set_actor_context(session, f['customer'])
        try:
            return await PlatformRepository(session).create_booking({**env.values(f, key=key),
                'segments': f['segments'], 'service_ids': [f['service'], f['beard']]})
        except AppError as exc:
            return exc


async def test_consecutive_segments_price_and_single_daily_booking(visits):
    f = await menu(visits)
    async with visits.session() as session:
        slots = await PlatformRepository(session).get_visit_slots(f['salon'], f['start'].date(), f['segments'])
    slot = next(s for s in slots if s['slot_start'] == f['start'])
    assert slot['segments'][0]['slot_end'] == slot['segments'][1]['slot_start']
    booking = await create(visits, f)
    assert isinstance(booking, dict), booking
    assert booking['is_multi_staff'] and len(booking['segments']) == 2
    assert booking['total_duration_minutes'] == 50 and booking['total_price'] == 350
    assert booking['end_datetime'] == f['start'] + timedelta(minutes=50)
    assert (await visits.sql('select count(*) as n from bookings where customer_id=:id', id=f['customer']))[0]['n'] == 1
    assert (await create(visits, f))['id'] == booking['id']


async def test_other_booking_in_second_segment_rejects_entire_visit(visits):
    f = await menu(visits)
    await visits.sql("""insert into blocked_slots(staff_id,salon_id,start_datetime,end_datetime,block_type)
        values(:staff,:salon,:start,:end,'break')""", staff=f['second'], salon=f['salon'],
        start=f['start']+timedelta(minutes=30), end=f['start']+timedelta(minutes=60))
    booking = await create(visits, f)
    assert isinstance(booking, AppError) and booking.code == 'slot_unavailable'
    assert (await visits.sql('select count(*) as n from bookings where salon_id=:id', id=f['salon']))[0]['n'] == 0


async def test_competing_visit_submissions_reserve_once(visits):
    f = await menu(visits)
    # Same customer and same request: a retry returns the identical booking.
    results = await asyncio.gather(create(visits, f), create(visits, f))
    assert all(isinstance(r, dict) for r in results), results
    assert results[0]['id'] == results[1]['id']
    assert (await visits.sql('select count(*) as n from booking_segments where booking_id=:id', id=results[0]['id']))[0]['n'] == 2


async def test_cancellation_releases_both_staff(visits):
    f = await menu(visits)
    booking = await create(visits, f)
    assert isinstance(booking, dict), booking
    await visits.sql("update bookings set status='cancelled' where id=:id", id=booking['id'])
    assert not any(r['is_active'] for r in await visits.sql('select is_active from booking_segments where booking_id=:id', id=booking['id']))
    async with visits.session() as session:
        slots = await PlatformRepository(session).get_visit_slots(f['salon'], f['start'].date(), f['segments'])
    assert any(s['slot_start'] == f['start'] for s in slots)


async def test_menu_categories_do_not_collapse_shared_general_subcategory(visits):
    f = await menu(visits)
    rows = await visits.sql('select menu_category_id from services where salon_id=:id', id=f['salon'])
    assert len({str(r['menu_category_id']) for r in rows}) == 2


async def test_staff_capabilities_and_prices_are_public_without_profile_ids(visits):
    f = await menu(visits)
    async with visits.session() as session:
        rows = await PlatformRepository(session).list_public_staff(f['salon'])
    barber = next(r for r in rows if r['id'] == f['second'])
    assert barber['service_ids'] == [f['beard']]
    assert barber['services'][0]['duration_minutes'] == 20
    assert 'profile_id' not in barber and 'working_hours' not in barber


async def test_legacy_booking_cannot_overlap_secondary_barber(visits):
    f = await menu(visits)
    booked = await create(visits, f)
    assert isinstance(booked, dict), booked
    another = await visits.seed()
    competitor = {**f, 'customer': another['customer'], 'staff': f['second'], 'service': f['beard'],
        'start': f['start'] + timedelta(minutes=40)}
    result = await visits.book(competitor)
    assert isinstance(result, AppError) and result.code == 'slot_unavailable'
    # The first barber is free after their segment, despite the visit continuing.
    async with visits.session() as session:
        slots = await PlatformRepository(session).get_available_slots(f['staff'], f['start'].date(), [f['service']])
    assert any(slot['slot_start'] == f['start'] + timedelta(minutes=30) for slot in slots)


async def test_competing_customers_only_one_gets_complete_visit(visits):
    f = await menu(visits)
    other = await visits.seed()
    second = {**f, 'customer': other['customer']}
    results = await asyncio.gather(create(visits, f), create(visits, second, key='other-visit-001'))
    assert sum(isinstance(result, dict) for result in results) == 1, results
    assert next(result for result in results if isinstance(result, AppError)).code == 'slot_unavailable'


async def test_second_staff_leave_preview_includes_whole_visit(visits):
    f = await menu(visits)
    booked = await create(visits, f)
    assert isinstance(booked, dict), booked
    async with visits.session() as session:
        rows = await PlatformRepository(session).preview_closure(f['owner'], {
            'kind': 'staff_leave', 'staff_id': f['second'],
            'start_datetime': f['start'] + timedelta(minutes=30),
            'end_datetime': f['start'] + timedelta(minutes=50)})
    assert len(rows) == 1 and str(rows[0]['booking_id']) == booked['id']


async def test_batch_creation_is_atomic_and_preserves_shared_defaults(visits):
    f = await menu(visits)
    payload = {'name':'Medium fade','price':250,'duration_minutes':30,'category_name':'Hair Cutting',
        'subcategory_name':'Hair Cutting','selection_group':'__category__'}
    async with visits.session() as session:
        repo = PlatformRepository(session)
        rows = await repo.create_owner_services(f['owner'], [payload, {**payload,'name':'High fade'}])
    assert len(rows) == 2 and len({r['menu_category_id'] for r in rows}) == 1
    assert all(r['duration_minutes'] == 30 for r in rows)
    before = (await visits.sql('select count(*) as n from services where salon_id=:id', id=f['salon']))[0]['n']
    async with visits.session() as session:
        with pytest.raises(IntegrityError):
            await PlatformRepository(session).create_owner_services(f['owner'], [
                {**payload, 'name':'Rollback valid'}, {**payload, 'name':'Rollback invalid','duration_minutes':-1}])
    assert (await visits.sql('select count(*) as n from services where salon_id=:id', id=f['salon']))[0]['n'] == before


async def test_legacy_creation_enforces_alternatives_but_allows_complements(visits):
    f = await menu(visits)
    wash = str(uuid4())
    await visits.sql("""insert into services(id,salon_id,subcategory_id,name,duration_minutes,price,category_name)
        select :id,salon_id,subcategory_id,'Another haircut',30,100,category_name from services where id=:base""", id=wash, base=f['service'])
    await visits.sql('insert into staff_services(staff_id,service_id) values(:staff,:service)', staff=f['staff'], service=wash)
    async with visits.session() as session:
        await set_actor_context(session, f['customer'])
        with pytest.raises(AppError) as caught:
            await PlatformRepository(session).create_booking({**visits.values(f), 'service_ids':[f['service'],wash]})
    assert caught.value.code == 'validation_error'
    await visits.sql('update services set selection_group=null where id=:id', id=wash)
    async with visits.session() as session:
        await set_actor_context(session, f['customer'])
        result = await PlatformRepository(session).create_booking({**visits.values(f), 'service_ids':[f['service'],wash]})
    assert result['total_duration_minutes'] == 60


async def test_capabilities_replace_services_and_languages_atomically(visits):
    f = await menu(visits)
    async with visits.session() as session:
        repo = PlatformRepository(session)
        updated = await repo.set_staff_capabilities(f['owner'],f['staff'],
            {'service_ids':[f['beard']], 'languages':['English','Malayalam']})
    assert updated['service_ids'] == [f['beard']] and set(updated['languages']) == {'English','Malayalam'}
    async with visits.session() as session:
        repo = PlatformRepository(session)
        public = await repo.list_public_staff(f['salon'])
        member = next(row for row in public if row['id'] == f['staff'])
        assert member['service_ids'] == [f['beard']]
        assert set(member['languages']) == {'English','Malayalam'}
        with pytest.raises(AppError):
            await repo.set_staff_capabilities(f['owner'],f['staff'], {'service_ids':[f['service']], 'languages':['Invalid language']})
        unchanged = await repo.get_staff_capabilities(f['owner'],f['staff'])
    assert unchanged == updated


async def test_visit_http_contract_and_staff_capability_owner_isolation(visits,monkeypatch):
    import httpx

    from tests.integration.test_booking_contract_sql import _customer
    from tests.integration.test_booking_journeys_e2e import local_app, make_owner
    f = await menu(visits)
    app, identity = local_app(visits, monkeypatch, make_owner(f['owner']))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        slots = await client.post('/v1/availability/visit',json={
            'salon_id':f['salon'],'date':f['start'].date().isoformat(),'segments':f['segments']})
        assert slots.status_code == 200, slots.text
        assert all(len(slot['segments']) == 2 for slot in slots.json())
        saved = await client.put(f"/v1/salons/me/staff/{f['staff']}/capabilities",json={
            'service_ids':[f['service']],'languages':['English']})
        assert saved.status_code == 200 and saved.json()['languages'] == ['English'], saved.text
        identity['actor'] = _customer(f['customer'])
        denied = await client.put(f"/v1/salons/me/staff/{f['staff']}/capabilities",json={
            'service_ids':[],'languages':[]})
        assert denied.status_code == 403
        created = await client.post('/v1/bookings',json={
            'salon_id':f['salon'],'staff_id':f['staff'],'service_ids':[f['service'],f['beard']],
            'segments':f['segments'],'start_datetime':f['start'].isoformat(),
            'customer_name':'Local visit customer','source':'app','payment_preference':'pay_at_salon'},
            headers={'Idempotency-Key':'http-visit-create-001'})
        assert created.status_code == 201, created.text
        assert created.json()['is_multi_staff'] and len(created.json()['segments']) == 2
        assert {part['staff_name'] for part in created.json()['segments']} == {'Local test staff','Beard specialist'}
        changed = await client.post(f"/v1/bookings/{created.json()['id']}/change", json={
            'staff_id':f['staff'],'service_ids':[f['service']],'start_datetime':f['start'].isoformat(),
            'expected_version':0,'quote_fingerprint':'0'*64},headers={'Idempotency-Key':'visit-change-blocked'})
        assert changed.status_code == 409 and changed.json()['error']['code'] == 'visit_change_requires_full_itinerary', changed.text
        cancelled = await client.post(f"/v1/bookings/{created.json()['id']}/cancel",json={})
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()['status'] == 'cancelled'



async def test_owner_erasure_scrubs_new_category_and_selection_labels(visits):
    f = await menu(visits)
    await visits.sql("update services set selection_group='Custom styles' where id=:id",id=f['service'])
    async with visits.session() as session:
        await session.execute(text("select set_config('app.account_erasure','on',true)"))
        await session.execute(text("update salons set is_active=false,name='Closed salon' where id=:id"), {'id':f['salon']})
        await session.commit()
    rows = await visits.sql('select name,is_active from salon_service_categories where salon_id=:id',id=f['salon'])
    assert rows and all(row['name'].startswith('Removed category ') and not row['is_active'] for row in rows)
    assert (await visits.sql('select selection_group from services where id=:id',id=f['service']))[0]['selection_group'] is None
