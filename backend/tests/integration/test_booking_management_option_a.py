"""Approved self-booking quotas, immediate cancellation and atomic visit edits on real PostgreSQL."""
import asyncio
from datetime import timedelta

import pytest

from app.core.exceptions import AppError
from app.infrastructure.db.repositories.booking_changes import BookingChangeRepository
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from app.infrastructure.db.session import set_actor_context
from tests.integration.salon_erasure_support import prepared_db  # noqa: F401
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB
from tests.integration.test_staff_service_visits import menu

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")

@pytest.fixture
async def env(prepared_db):  # noqa: F811
    value = SafetyEnv(prepared_db)
    yield value
    await value.engine.dispose()

async def cancel(env, f, booking):
    async with env.session() as session:
        await set_actor_context(session, f['customer'])
        return await PlatformRepository(session).cancel_customer_booking(f['customer'],booking['id'],'Changed plans',240)

async def test_three_self_bookings_per_date_and_fourth_refused(env):
    f = await env.seed()
    bookings = [await env.book(f, delta=n*30) for n in range(3)]
    assert all(isinstance(b,dict) for b in bookings), bookings
    fourth = await env.book(f,delta=90)
    assert isinstance(fourth,AppError) and fourth.code == 'pay_at_salon_daily_limit'
    await cancel(env,f,bookings[0])
    assert isinstance(await env.book(f,delta=90),dict)

async def test_upcoming_limit_is_across_dates_and_salons(env):
    f = await env.seed()
    for day in range(5):
        assert isinstance(await env.book({**f,'start':f['start']+timedelta(days=day)}),dict)
    other = await env.seed()
    blocked = await env.book({**other,'customer':f['customer'],'start':f['start']+timedelta(days=6)})
    assert isinstance(blocked,AppError) and blocked.code == 'pay_at_salon_upcoming_limit'

async def test_cancel_rebook_does_not_reset_rolling_week(env):
    f = await env.seed()
    for _ in range(8):
        booking = await env.book(f)
        assert isinstance(booking,dict), booking
        await cancel(env,f,booking)
    result = await env.book(f)
    assert isinstance(result,AppError) and result.code == 'pay_at_salon_weekly_limit'

async def test_owner_cancel_restores_weekly_credit(env):
    f = await env.seed()
    for _ in range(9):
        booking = await env.book(f)
        assert isinstance(booking,dict),booking
        async with env.session() as session:
            await set_actor_context(session,f['owner'])
            await PlatformRepository(session).update_booking_status(f['owner'],booking['id'],'cancelled',cancellation_reason='Staff unavailable')

async def test_same_customer_cannot_overlap_different_salons(env):
    f = await env.seed()
    assert isinstance(await env.book(f),dict)
    other = await env.seed()
    result = await env.book({**other,'customer':f['customer'],'start':f['start']})
    assert isinstance(result,AppError) and result.code == 'customer_booking_overlap'

async def test_concurrent_fourth_reservations_cannot_bypass_limit(env):
    f = await env.seed()
    assert isinstance(await env.book(f),dict)
    assert isinstance(await env.book(f,delta=30),dict)
    results = await asyncio.gather(env.book(f,delta=60),env.book(f,delta=90))
    assert sum(isinstance(row,dict) for row in results)==1,results
    assert next(row for row in results if isinstance(row,AppError)).code=='pay_at_salon_daily_limit'

async def test_cancellation_inside_old_cutoff_releases_all_segments_and_no_approval(env):
    f = await menu(env)
    async with env.session() as session:
        await set_actor_context(session,f['customer'])
        booking = await PlatformRepository(session).create_booking({**env.values(f),
            'segments':f['segments'],'service_ids':[f['service'],f['beard']]})
    result = await cancel(env,f,booking)
    assert result['status']=='cancelled'
    assert not any(row['is_active'] for row in await env.sql('select is_active from booking_segments where booking_id=:id',id=booking['id']))
    assert (await env.sql("select count(*) n from booking_action_requests where booking_id=:id and kind='cancellation'",id=booking['id']))[0]['n']==0
    notices = await env.sql("select title from notifications where booking_id=:id and type='booking_cancelled'",id=booking['id'])
    assert [n['title'] for n in notices]==['Booking cancelled']

async def change_quote(env,f,b,start,parts=None):
    parts = parts or f['segments']
    values={'staff_id':parts[0]['staff_id'],'service_ids':[sid for p in parts for sid in p['service_ids']],
        'segments':parts,'start_datetime':start,'expected_version':b['change_version']}
    async with env.session() as session:
        await set_actor_context(session,f['customer'])
        q = await BookingChangeRepository(session).quote(b['id'],values)
    return values,q

async def test_multi_staff_change_is_atomic_idempotent_and_retains_one_booking(env):
    f = await menu(env)
    async with env.session() as session:
        await set_actor_context(session,f['customer'])
        b = await PlatformRepository(session).create_booking({**env.values(f),'segments':f['segments'],'service_ids':[f['service'],f['beard']]})
    values,q=await change_quote(env,f,b,f['start']+timedelta(hours=2))
    assert q['slot_available'] and len(q['segments'])==2,q
    assert q['segments'][0]['slot_end']==q['segments'][1]['slot_start']
    for _ in range(2):
        async with env.session() as session:
            await set_actor_context(session,f['customer'])
            result=await BookingChangeRepository(session).commit(b['id'],{**values,'quote_fingerprint':q['quote_fingerprint']},'complete-visit-change-001')
        assert result['change_version']==1 and result['committed_reschedules']==1
        assert result['total_price']==b['total_price']
    assert (await env.sql('select count(*) n from bookings where customer_id=:id',id=f['customer']))[0]['n']==1
    assert (await env.sql('select count(*) n from booking_customer_changes where booking_id=:id',id=b['id']))[0]['n']==1

async def test_secondary_slot_taken_after_quote_keeps_original_itinerary(env):
    f = await menu(env)
    async with env.session() as session:
        await set_actor_context(session,f['customer'])
        b=await PlatformRepository(session).create_booking({**env.values(f),'segments':f['segments'],'service_ids':[f['service'],f['beard']]})
    values,q=await change_quote(env,f,b,f['start']+timedelta(hours=2))
    await env.sql("""insert into blocked_slots(staff_id,salon_id,start_datetime,end_datetime,block_type)
       values(:staff,:salon,:start,:end,'break')""",staff=f['second'],salon=f['salon'],
       start=values['start_datetime']+timedelta(minutes=30),end=values['start_datetime']+timedelta(minutes=60))
    async with env.session() as session:
        await set_actor_context(session,f['customer'])
        with pytest.raises(AppError):
            await BookingChangeRepository(session).commit(b['id'],{**values,'quote_fingerprint':q['quote_fingerprint']},'conflicted-change-001')
    row=(await env.sql('select start_datetime,change_version from bookings where id=:id',id=b['id']))[0]
    assert row['start_datetime']==f['start'] and row['change_version']==0

async def test_change_cannot_exclude_someone_elses_booking(env):
    f=await env.seed()
    b=await env.book(f)
    other=await env.seed()
    async with env.session() as session:
        await set_actor_context(session,other['customer'])
        with pytest.raises(AppError) as caught:
            await BookingChangeRepository(session).quote(b['id'],{'segments':[{'staff_id':f['staff'],'service_ids':[f['service']]}],
                'start_datetime':f['start'],'expected_version':0})
    assert caught.value.code=='not_found'
