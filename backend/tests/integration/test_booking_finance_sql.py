import asyncio
from pathlib import Path

"""U08 policy snapshots and manual finance records on disposable local Postgres."""

from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.domain.entities.profile import Role
from app.domain.services.booking_finance_policy import POLICY_VERSION
from app.infrastructure.db.session import set_actor_context
from tests.conftest import make_owner, make_profile
from tests.integration.test_booking_changes_sql import changes_db  # noqa: F401
from tests.integration.test_booking_contract_sql import _customer
from tests.integration.test_booking_journeys_e2e import local_app
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason='Requires disposable local PostgreSQL')
D = Decimal


@pytest.fixture(scope='module')
def finance_db(changes_db):  # noqa: F811
    async def install():
        env=SafetyEnv(changes_db)
        try:
            async with env.session() as session:
                for file in ['0043_no_show_attendance_guards.sql','0046_u08_financial_outcomes.sql']:
                    source=Path(__file__).parents[2]/'migrations/sql'/file
                    for statement in source.read_text(encoding='utf-8').split('\n-- statement --\n'):
                        if statement.strip(): await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()
    asyncio.run(install())
    return changes_db


@pytest.fixture
async def finance(finance_db,monkeypatch):
    monkeypatch.setattr(settings,'booking_checkout_policy_version',POLICY_VERSION)
    monkeypatch.setattr(settings,'admin_require_mfa',False)  # Separate test below verifies the MFA gate.
    env=SafetyEnv(finance_db)
    yield env
    await env.engine.dispose()


async def setup(env,monkeypatch,amount='250',*,pending=False,self_booked=False):
    f=await env.seed()
    if self_booked: f['customer']=f['owner']
    b=await env.book(f)
    assert isinstance(b,dict),b
    await env.sql("update bookings set payment_preference='pay_full' where id=:id",id=b['id'])
    payments=await env.sql("""insert into booking_payments(booking_id,salon_id,channel,purpose,method,provider,
        amount,status,intent_reference,captured_at,settlement_model)
        values(:id,:salon,'gateway','full','online','cashfree',:amount,:status,:ref,now(),'platform_collect') returning id""",
        id=b['id'],salon=f['salon'],amount=D(amount),status='created' if pending else 'captured',ref='test-'+uuid4().hex)
    admin=await env.seed()
    await env.sql("update profiles set role='super_admin' where id=:id",id=admin['owner'])
    app,identity=local_app(env,monkeypatch,_customer(f['customer']))
    return f,b,app,identity,make_profile(admin['owner'],role=Role.super_admin),payments[0]['id']


async def terminal(env,f,b,*,hours=48,kind='cancelled',actor=None):
    async with env.session() as session:
        await set_actor_context(session,actor or f['customer'])
        await session.execute(text("select set_config('app.booking_cancel_origin','customer',true)"))
        await session.execute(text("""update bookings set start_datetime=statement_timestamp()+make_interval(hours=>:hours),
            end_datetime=statement_timestamp()+make_interval(hours=>:hours)+interval '30 minutes',
            status=cast(:status as booking_status),cancellation_reason='Test policy decision' where id=:id"""),
            {'hours':hours,'id':b['id'],'status':kind})
        await session.commit()


async def outcome(env,b):
    return (await env.sql('select * from booking_financial_outcomes where booking_id=:id',id=b['id']))[0]


async def command(client,b,version,action,amount,reference=None,key=None):
    return await client.post(f"/v1/admin/bookings/{b['id']}/finance/commands",
        json={'expected_version':version,'action':action,'amount':str(amount),'reference':reference or ('test-'+uuid4().hex)},
        headers={'Idempotency-Key':key or ('test-key-'+uuid4().hex)})


@pytest.mark.parametrize(('hours','paid','penalty'),[(48,'100','20'),(12,'100','5'),(11,'100','35'),(4,'100','100'),(0,'100','100'),(48,'5','5')])
async def test_exact_sql_cancellation_bands_and_durable_refund_job(finance,monkeypatch,hours,paid,penalty):
    f,b,_,_,_,_=await setup(finance,monkeypatch,paid)
    await terminal(finance,f,b,hours=hours)
    row=await outcome(finance,b)
    assert row['cancellation_penalty']==D(penalty)
    assert row['customer_refund_promised']==D(paid)-D(penalty)
    assert row['provider_costs'] is None
    jobs=await finance.sql('select amount,status from booking_policy_refund_jobs where booking_id=:id',id=b['id'])
    if D(paid)>D(penalty):
        assert jobs[0]['amount']==D(paid)-D(penalty) and jobs[0]['status']=='pending_provider'
    else: assert not jobs


async def test_customer_can_cancel_inside_old_cutoff_and_snapshot_is_immutable(finance,monkeypatch):
    from sqlalchemy.exc import DBAPIError

    _,b,app,_,_,_=await setup(finance,monkeypatch)
    await finance.sql("update bookings set start_datetime=now()+interval '1 hour',end_datetime=now()+interval '90 minutes' where id=:id",id=b['id'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        detail=await client.get(f"/v1/bookings/{b['id']}")
        assert detail.json()['can_cancel'] and not detail.json()['can_request_cancellation']
        cancelled=await client.post(f"/v1/bookings/{b['id']}/cancel",json={})
        assert cancelled.status_code==200,cancelled.text
    row=await outcome(finance,b)
    assert row['kind']=='customer_cancellation' and row['refund_due']==0
    with pytest.raises(DBAPIError,match='financial_history_is_immutable'):
        await finance.sql('update booking_financial_outcomes set customer_refund_promised=1 where booking_id=:id',id=b['id'])


async def test_provider_costs_do_not_reduce_promised_refund_and_platform_absorbs_shortfall(finance,monkeypatch):
    f,b,app,identity,admin,_=await setup(finance,monkeypatch)
    await terminal(finance,f,b,hours=48)
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await command(client,b,0,'provider_costs','100')
        assert result.status_code==200,result.text
        row=result.json()
        assert D(row['customer_refund_promised'])==230 and D(row['refund_due'])==230
        assert D(row['salon_share'])==0 and D(row['platform_share'])==0 and D(row['platform_shortfall'])==80
        denied=await command(client,b,1,'approve','1')
        assert denied.status_code==409


async def test_manual_approval_partial_payout_idempotency_and_owner_redaction(finance,monkeypatch):
    f,b,app,identity,admin,_=await setup(finance,monkeypatch,'100')
    await terminal(finance,f,b,hours=4)
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        assert (await command(client,b,0,'provider_costs','3')).status_code==200
        assert (await command(client,b,1,'hold_review','0')).status_code==200
        approved=await command(client,b,2,'approve','67.90')
        assert approved.status_code==200,approved.text
        ref='payout-'+uuid4().hex;key='payout-key-'+uuid4().hex
        first=await command(client,b,3,'record_payout','20',reference=ref,key=key)
        assert first.status_code==200,first.text
        replay=await command(client,b,3,'record_payout','20',reference=ref,key=key)
        assert replay.status_code==200 and D(replay.json()['paid_out_amount'])==20
        remaining=await command(client,b,4,'record_payout','47.90')
        assert remaining.status_code==200 and D(remaining.json()['paid_out_amount'])==D('67.90')
        identity['actor']=make_owner(f['owner'])
        owner=await client.get(f"/v1/salons/me/bookings/{b['id']}/payout")
        assert owner.status_code==200,owner.text
        assert set(owner.json())=={'booking_id','approved_amount','paid_out_amount','status'}
        assert owner.json()['status']=='paid'
        identity['actor']=_customer(f['customer'])
        assert (await client.get(f"/v1/admin/bookings/{b['id']}/finance")).status_code==403
        assert (await command(client,b,5,'record_payout','1')).status_code==403


async def test_owner_cancelling_self_booked_visit_is_full_refund_not_customer_penalty(finance,monkeypatch):
    f,b,app,identity,_,_=await setup(finance,monkeypatch,self_booked=True)
    identity['actor']=make_owner(f['owner'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await client.post(f"/v1/bookings/{b['id']}/cancel/barber",json={'reason_code':'barber_unavailable'})
        assert result.status_code==200,result.text
    row=await outcome(finance,b)
    assert row['kind']=='salon_cancellation' and row['customer_refund_promised']==250 and row['cancellation_penalty']==0


async def test_late_capture_is_retained_in_ledger_and_blocks_payout_for_reconciliation(finance,monkeypatch):
    f,b,app,identity,admin,payment=await setup(finance,monkeypatch,pending=True)
    await terminal(finance,f,b,hours=48)
    assert (await outcome(finance,b))['requires_reconciliation']
    await finance.sql("update booking_payments set status='captured' where id=:id",id=payment)
    row=await outcome(finance,b)
    assert row['captured_amount']==0 and row['requires_reconciliation']
    queue=await finance.sql('select reason,observed_captured from booking_finance_reconciliations where booking_id=:id',id=b['id'])
    assert queue[0]['reason']=='ledger_changed' and queue[0]['observed_captured']==250
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await command(client,b,row['version'],'approve','1')
        assert result.status_code==409 and result.json()['error']['code']=='finance_reconciliation_required'


async def test_excess_refund_after_snapshot_invalidates_approval(finance,monkeypatch):
    f,b,app,identity,admin,payment=await setup(finance,monkeypatch,'100')
    await terminal(finance,f,b,hours=4)
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        assert (await command(client,b,0,'provider_costs','0')).status_code==200
        assert (await command(client,b,1,'hold_review','0')).status_code==200
        assert (await command(client,b,2,'approve','70')).status_code==200
        await finance.sql("""insert into payment_refunds(payment_id,booking_id,provider,amount,status,idempotency_key)
            values(:payment,:booking,'cashfree',100,'processed',:key)""",payment=payment,booking=b['id'],key='refund-'+uuid4().hex)
        row=await outcome(finance,b)
        assert row['requires_reconciliation']
        refused=await command(client,b,row['version'],'record_payout','70')
        assert refused.status_code==409 and refused.json()['error']['code']=='finance_reconciliation_required'


async def test_admin_finance_requires_mfa_and_other_owner_cannot_read_statement(finance,monkeypatch):
    f,b,app,identity,admin,_=await setup(finance,monkeypatch)
    await terminal(finance,f,b)
    identity['actor']=admin;monkeypatch.setattr(settings,'admin_require_mfa',True)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        assert (await client.get(f"/v1/admin/bookings/{b['id']}/finance")).status_code==403
        other=await finance.seed();identity['actor']=make_owner(other['owner'])
        assert (await client.get(f"/v1/salons/me/bookings/{b['id']}/payout")).status_code==404


async def test_completed_prepaid_has_zero_commission_and_only_actual_provider_cost(finance,monkeypatch):
    f,b,app,identity,admin,_=await setup(finance,monkeypatch)
    await terminal(finance,f,b,hours=0,kind='completed')
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await command(client,b,0,'provider_costs','7.65')
        assert result.status_code==200,result.text
        row=result.json()
        assert D(row['customer_refund_promised'])==0 and D(row['cancellation_penalty'])==0
        assert D(row['platform_share'])==0 and D(row['salon_share'])==D('242.35')


async def test_prepaid_completion_cannot_hide_an_uncollected_balance(finance,monkeypatch):
    from sqlalchemy.exc import DBAPIError

    f,b,_,_,_,_=await setup(finance,monkeypatch,'100')
    with pytest.raises(DBAPIError,match='payment_collection_required'):
        await terminal(finance,f,b,kind='completed')
    assert not await finance.sql('select booking_id from booking_financial_outcomes where booking_id=:id',id=b['id'])


async def test_retained_pool_half_up_rounding_gives_residue_to_salon(finance,monkeypatch):
    f,b,app,identity,admin,_=await setup(finance,monkeypatch,'20')
    await terminal(finance,f,b,hours=48)
    identity['actor']=admin
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await command(client,b,0,'provider_costs','19.95')
        assert result.status_code==200,result.text
        assert D(result.json()['platform_share'])==D('0.02') and D(result.json()['salon_share'])==D('0.03')


async def test_checked_in_collection_capability_is_owner_scoped(finance,monkeypatch):
    f,b,app,identity,_,_=await setup(finance,monkeypatch,'100')
    await finance.sql("update bookings set status='checked_in' where id=:id",id=b['id'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        customer=await client.get(f"/v1/bookings/{b['id']}")
        assert customer.status_code==200 and not customer.json()['can_record_payment']
        identity['actor']=make_owner(f['owner'])
        owner=await client.get(f"/v1/bookings/{b['id']}")
        assert owner.status_code==200 and owner.json()['can_record_payment']
        assert not owner.json()['can_confirm_payment']


async def test_legacy_policy_allows_direct_cancellation_before_start(finance,monkeypatch):
    monkeypatch.setattr(settings,'booking_checkout_policy_version','customer_processing_v1')
    _,b,app,_,_,_=await setup(finance,monkeypatch)
    await finance.sql("update bookings set start_datetime=now()+interval '1 hour',end_datetime=now()+interval '90 minutes' where id=:id",id=b['id'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        result=await client.post(f"/v1/bookings/{b['id']}/cancel",json={})
        assert result.status_code==200, result.text
        assert result.json()['status']=='cancelled'
    assert not await finance.sql('select booking_id from booking_financial_outcomes where booking_id=:id',id=b['id'])


async def test_cancellation_quote_uses_verified_funds_and_is_customer_scoped(finance, monkeypatch):
    _f,b,app,identity,_,_=await setup(finance,monkeypatch,'250')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        response=await client.get(f"/v1/bookings/{b['id']}/cancellation-quote")
        assert response.status_code==200,response.text
        quote=response.json()
        assert quote['can_cancel'] and quote['paid_online'] and not quote['requires_review']
        assert D(quote['refund_amount'])==230 and D(quote['deduction_amount'])==20
        assert not await finance.sql('select id from payment_refunds where booking_id=:id',id=b['id'])
        outsider=await finance.seed()
        identity['actor']=_customer(outsider['customer'])
        hidden=await client.get(f"/v1/bookings/{b['id']}/cancellation-quote")
        assert hidden.status_code==404


async def test_unpaid_cancellation_quote_does_not_promise_a_refund(finance,monkeypatch):
    f=await finance.seed()
    b=await finance.book(f)
    app,_=local_app(finance,monkeypatch,_customer(f['customer']))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        response=await client.get(f"/v1/bookings/{b['id']}/cancellation-quote")
        assert response.status_code==200,response.text
        quote=response.json()
        assert quote['can_cancel'] and not quote['paid_online']
        assert D(quote['refund_amount'])==0 and D(quote['amount_paid'])==0
