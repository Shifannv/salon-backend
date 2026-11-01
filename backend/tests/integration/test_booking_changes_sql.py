"""Customer changes against isolated local Postgres; no provider or remote data."""

import asyncio
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.domain.services.booking_finance_policy import POLICY_VERSION
from tests.integration.test_booking_contract_sql import _customer
from tests.integration.test_booking_journeys_e2e import local_app
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


@pytest.fixture(scope="module")
def changes_db():
    from uuid import uuid4

    from sqlalchemy.engine import make_url

    name = "booking_changes_" + uuid4().hex
    asyncio.run(_build(name))
    url = make_url(TEST_DB).set(database=name, drivername="postgresql+asyncpg").render_as_string(hide_password=False)

    async def install():
        env = SafetyEnv(url)
        try:
            async with env.session() as session:
                # Current finance API routes also resolve the feature matrix. Keep
                # that schema in every derived disposable API-test database.
                for file in [
                    "0044_versioned_checkout_policy.sql",
                    "0045_customer_booking_changes.sql",
                    "0055_feature_access.sql",
                ]:
                    source = Path(__file__).parents[2] / "migrations/sql" / file
                    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
                        if statement.strip():
                            await session.execute(text(statement))
                await session.commit()
        finally:
            await env.engine.dispose()

    try:
        asyncio.run(install())
        yield url
    finally:
        asyncio.run(_drop(name))


@pytest.fixture
async def changes(changes_db, monkeypatch):
    monkeypatch.setattr(settings, "booking_checkout_policy_version", POLICY_VERSION)
    env = SafetyEnv(changes_db)
    yield env
    await env.engine.dispose()


async def setup_client(env, monkeypatch):
    f = await env.seed()
    b = await env.book(f)
    assert isinstance(b, dict), b
    app, identity = local_app(env, monkeypatch, _customer(f['customer']))
    body = {'staff_id': f['staff'], 'service_ids': [f['service']],
            'start_datetime': (f['start'] + timedelta(hours=1)).isoformat(), 'expected_version': 0}
    return f, b, app, identity, body


async def test_time_change_replay_preserves_status_and_notifies_once(changes, monkeypatch):
    _f, b, app, _, body = await setup_client(changes, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        quote = await client.post(f"/v1/bookings/{b['id']}/change-quote", json=body)
        assert quote.status_code == 200, quote.text
        assert quote.json()['slot_available'] and Decimal(quote.json()['additional_payment_required']) == 0
        body['quote_fingerprint'] = quote.json()['quote_fingerprint']
        result = await client.post(f"/v1/bookings/{b['id']}/change", json=body, headers={'Idempotency-Key': 'change-001'})
        assert result.status_code == 200, result.text
        assert result.json()['status'] == b['status']
        assert result.json()['change_version'] == 1 and result.json()['committed_reschedules'] == 1
        replay = await client.post(f"/v1/bookings/{b['id']}/change", json=body, headers={'Idempotency-Key': 'change-001'})
        assert replay.status_code == 200 and replay.json()['change_version'] == 1
    rows = await changes.sql("select count(*) as n from booking_customer_changes where booking_id=:id", id=b['id'])
    assert rows[0]['n'] == 1
    notices = await changes.sql("select count(*) as n from notifications where booking_id=:id and type='booking_changed'", id=b['id'])
    assert notices[0]['n'] == 2


async def test_two_reschedules_and_stale_versions_never_move_original_on_failure(changes, monkeypatch):
    f, b, app, _, body = await setup_client(changes, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        for version in range(3):
            body.update(expected_version=version, start_datetime=(f['start'] + timedelta(hours=version+1)).isoformat())
            if version < 2:
                quote = await client.post(f"/v1/bookings/{b['id']}/change-quote", json=body)
                assert quote.status_code == 200, quote.text
                submitted = {**body, 'quote_fingerprint': quote.json()['quote_fingerprint']}
            else:
                submitted = {**body, 'quote_fingerprint': '0'*64}
            result = await client.post(f"/v1/bookings/{b['id']}/change", json=submitted, headers={'Idempotency-Key': f'change-{version}'})
            assert result.status_code == (200 if version < 2 else 409), result.text
        assert result.json()['error']['code'] == 'booking_change_limit'
    rows = await changes.sql("select committed_reschedules,start_datetime from bookings where id=:id", id=b['id'])
    assert rows[0]['committed_reschedules'] == 2 and rows[0]['start_datetime'] == f['start'] + timedelta(hours=2)


async def test_concurrent_same_version_only_one_change_commits(changes, monkeypatch):
    f, b, app, _, body = await setup_client(changes, monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        requests = []
        for i in range(2):
            selected = {**body, 'start_datetime': (f['start']+timedelta(hours=i+1)).isoformat()}
            quote = await client.post(f"/v1/bookings/{b['id']}/change-quote", json=selected)
            assert quote.status_code == 200, quote.text
            requests.append({**selected,'quote_fingerprint':quote.json()['quote_fingerprint']})
        a, z = await asyncio.gather(*[
            client.post(f"/v1/bookings/{b['id']}/change", json=requests[i],
                        headers={'Idempotency-Key': f'race-change-{i}'}) for i in range(2)
        ])
        assert sorted([a.status_code, z.status_code]) == [200,409]
        loser = a if a.status_code == 409 else z
        assert loser.json()['error']['code'] == 'booking_change_version_conflict'


async def test_other_customer_cannot_quote_or_change_and_customer_cannot_forge_price(changes, monkeypatch):
    _, b, app, identity, body = await setup_client(changes, monkeypatch)
    other = await changes.seed()
    identity['actor'] = _customer(other['customer'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        for suffix in ['change-quote', 'change']:
            data = body if suffix == 'change-quote' else {**body,'quote_fingerprint':'0'*64}
            result = await client.post(f"/v1/bookings/{b['id']}/{suffix}", json=data, headers={'Idempotency-Key':'foreign-change'})
            assert result.status_code == 404, result.text
        result = await client.post(f"/v1/bookings/{b['id']}/change", json={**body,'total_price': '1'}, headers={'Idempotency-Key':'forge-price'})
        assert result.status_code == 422


async def new_service(env, fixture, price='100.00'):
    service = str(uuid4())
    await env.sql("""insert into services(id,salon_id,subcategory_id,name,duration_minutes,price)
        select cast(:id as uuid),salon_id,subcategory_id,'Different service',30,cast(:price as numeric)
        from services where id=cast(:old as uuid)""", id=service, old=fixture['service'], price=price)
    await env.sql("insert into staff_services(staff_id,service_id) values(cast(:staff as uuid),cast(:service as uuid))",
                  staff=fixture['staff'], service=service)
    return service


async def reviewed(client, booking_id, body):
    quote = await client.post(f'/v1/bookings/{booking_id}/change-quote', json=body)
    assert quote.status_code == 200, quote.text
    return {**body,'quote_fingerprint':quote.json()['quote_fingerprint']}, quote.json()


@pytest.mark.parametrize('prepaid', [False,True])
async def test_cheaper_service_keeps_history_and_prepaid_money_but_reduces_unpaid_price(changes, monkeypatch, prepaid):
    f,b,app,_,body = await setup_client(changes, monkeypatch)
    if prepaid:
        await changes.sql("update bookings set payment_preference='pay_full' where id=:id",id=b['id'])
        # Synthetic verified ledger observation only; no payment-provider API is called.
        await changes.sql("""insert into booking_payments(booking_id,salon_id,channel,purpose,method,
            provider,amount,status,intent_reference,captured_at,settlement_model)
            values(:id,:salon,'gateway','full','online','cashfree',250,'captured',:ref,now(),'platform_collect')""",
            id=b['id'],salon=f['salon'],ref='test-'+uuid4().hex)
    cheap = await new_service(changes,f)
    body.update(service_ids=[cheap])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,quote = await reviewed(client,b['id'],body)
        assert Decimal(quote['total_payable']) == (250 if prepaid else 100)
        result = await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'cheaper-service'})
        assert result.status_code == 200,result.text
        data = result.json()
        assert Decimal(data['total_price']) == (250 if prepaid else 100)
        assert Decimal(data['service_fulfilment_amount']) == 100
        assert [line['service_id'] for line in data['services']] == [cheap]
    lines = await changes.sql('select service_id,is_active from booking_services where booking_id=:id',id=b['id'])
    assert len(lines)==2 and sum(line['is_active'] for line in lines)==1
    history = await changes.sql('select previous_services,committed_services from booking_customer_changes where booking_id=:id',id=b['id'])
    assert Decimal(str(history[0]['previous_services'][0]['price']))==250
    assert Decimal(str(history[0]['committed_services'][0]['price']))==100


async def test_prepaid_upgrade_never_commits_without_verified_extra_money(changes,monkeypatch):
    f,b,app,_,body=await setup_client(changes,monkeypatch)
    await changes.sql("update bookings set payment_preference='pay_full' where id=:id",id=b['id'])
    await changes.sql("""insert into booking_payments(booking_id,salon_id,channel,purpose,method,
        provider,amount,status,intent_reference,captured_at,settlement_model)
        values(:id,:salon,'gateway','full','online','cashfree',250,'captured',:ref,now(),'platform_collect')""",
        id=b['id'],salon=f['salon'],ref='test-'+uuid4().hex)
    body['service_ids']=[await new_service(changes,f,'350')]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,quote=await reviewed(client,b['id'],body)
        assert Decimal(quote['additional_payment_required'])==100
        result=await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'unverified-extra'})
        assert result.status_code==409 and result.json()['error']['code']=='additional_payment_required'
    stored=await changes.sql('select change_version,total_price,start_datetime from bookings where id=:id',id=b['id'])
    assert stored[0]['change_version']==0 and stored[0]['total_price']==250 and stored[0]['start_datetime']==f['start']
    assert not await changes.sql('select id from booking_customer_changes where booking_id=:id',id=b['id'])


async def test_changed_catalog_quote_requires_reacceptance_and_time_only_keeps_booked_price(changes,monkeypatch):
    f,b,app,_,body=await setup_client(changes,monkeypatch)
    alternative=await new_service(changes,f)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,_=await reviewed(client,b['id'],{**body,'service_ids':[alternative]})
        await changes.sql('update services set price=150 where id=:id',id=alternative)
        result=await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'stale-price'})
        assert result.status_code==409 and result.json()['error']['code']=='booking_change_quote_stale'
        await changes.sql('update services set price=999,duration_minutes=60 where id=:id',id=f['service'])
        payload,quote=await reviewed(client,b['id'],body)
        assert Decimal(quote['total_payable'])==250 and quote['duration_minutes']==30
        result=await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'time-only-price'})
        assert result.status_code==200 and Decimal(result.json()['total_price'])==250


@pytest.mark.parametrize('hours', [4,3])
async def test_four_hour_cutoff_blocks_quote_and_commit(changes,monkeypatch,hours):
    _,b,app,_,body=await setup_client(changes,monkeypatch)
    await changes.sql("update bookings set start_datetime=now()+make_interval(hours=>:hours) where id=:id",id=b['id'],hours=hours)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        for suffix in ['change-quote','change']:
            payload=body if suffix=='change-quote' else {**body,'quote_fingerprint':'0'*64}
            result=await client.post(f"/v1/bookings/{b['id']}/{suffix}",json=payload,headers={'Idempotency-Key':'cutoff-test'})
            assert result.status_code==409 and result.json()['error']['code']=='booking_change_cutoff'


async def test_change_availability_excludes_only_own_booking_and_preserves_public_slots(changes,monkeypatch):
    f,b,app,identity,_=await setup_client(changes,monkeypatch)
    params={'staff_id':f['staff'],'service_ids':[f['service']],'date':f['start'].date().isoformat()}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        response=await client.get(f"/v1/bookings/{b['id']}/change-availability",params=params)
        assert response.status_code==200,response.text
        from datetime import datetime
        assert any(datetime.fromisoformat(row['slot_start'])==f['start'] for row in response.json())
        regular=await client.get('/v1/availability',params=params)
        assert regular.status_code==200,regular.text
        assert all(datetime.fromisoformat(row['slot_start'])!=f['start'] for row in regular.json())
        other=await changes.seed();identity['actor']=_customer(other['customer'])
        response=await client.get(f"/v1/bookings/{b['id']}/change-availability",params=params)
        assert response.status_code==404,response.text


async def test_history_immutable_and_clients_cannot_execute_changes(changes,monkeypatch):
    from sqlalchemy.exc import DBAPIError

    _,b,app,_,body=await setup_client(changes,monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,_=await reviewed(client,b['id'],body)
        assert (await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'immutable-test'})).status_code==200
    for statement in ['update booking_customer_changes set previous_total=1 where booking_id=:id',
                      'delete from booking_customer_changes where booking_id=:id','truncate booking_customer_changes']:
        with pytest.raises(DBAPIError,match='booking_change_history_is_immutable'):
            await changes.sql(statement,id=b['id'])
    acl=await changes.sql("""select has_table_privilege('service_role','booking_customer_changes','TRUNCATE') as truncate,
        has_table_privilege('authenticated','booking_customer_changes','SELECT') as client_read,
        has_function_privilege('authenticated','public.apply_customer_booking_change(uuid,uuid,uuid[],timestamptz,integer,text,text)','EXECUTE') as client_execute""")
    assert not any(acl[0].values())


async def test_concurrent_closure_is_rechecked_after_shared_salon_lock(changes,monkeypatch):
    f,b,app,_,body=await setup_client(changes,monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,_=await reviewed(client,b['id'],body)
        async with changes.session() as closure:
            await closure.execute(text('select pg_advisory_xact_lock(hashtextextended(:salon,0))'),{'salon':f['salon']})
            await closure.execute(text("""insert into blocked_slots(salon_id,staff_id,start_datetime,end_datetime)
                values(:salon,:staff,:start,:finish)"""),{'salon':f['salon'],'staff':f['staff'],
                'start':f['start']+timedelta(hours=1),'finish':f['start']+timedelta(hours=2)})
            pending=asyncio.create_task(client.post(f"/v1/bookings/{b['id']}/change",json=payload,
                headers={'Idempotency-Key':'closure-race'}))
            await asyncio.sleep(0.2)
            assert not pending.done(), 'Change must wait for the closure transaction'
            await closure.commit()
        result=await pending
        assert result.status_code==409 and result.json()['error']['code']=='slot_unavailable'
    stored=await changes.sql('select start_datetime,change_version from bookings where id=:id',id=b['id'])
    assert stored[0]['start_datetime']==f['start'] and stored[0]['change_version']==0


async def test_other_booking_takes_reviewed_slot_without_losing_original(changes,monkeypatch):
    f,b,app,_,body=await setup_client(changes,monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,_=await reviewed(client,b['id'],body)
        other=await changes.seed()
        competitor={**f,'customer':other['customer']}
        taken=await changes.book(competitor,delta=60)
        assert isinstance(taken,dict),taken
        result=await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'taken-after-quote'})
        assert result.status_code==409 and result.json()['error']['code']=='slot_unavailable'
    stored=await changes.sql('select start_datetime,committed_reschedules from bookings where id=:id',id=b['id'])
    assert stored[0]['start_datetime']==f['start'] and stored[0]['committed_reschedules']==0


async def test_booking_change_requires_key_and_rejects_key_reuse(changes,monkeypatch):
    _,b,app,_,body=await setup_client(changes,monkeypatch)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url='http://local.test') as client:
        payload,_=await reviewed(client,b['id'],body)
        missing=await client.post(f"/v1/bookings/{b['id']}/change",json=payload)
        assert missing.status_code==400 and missing.json()['error']['code']=='idempotency_key_required'
        assert (await client.post(f"/v1/bookings/{b['id']}/change",json=payload,headers={'Idempotency-Key':'same-key-test'})).status_code==200
        changed=await client.post(f"/v1/bookings/{b['id']}/change",json={**payload,'expected_version':1},headers={'Idempotency-Key':'same-key-test'})
        assert changed.status_code==409 and changed.json()['error']['code']=='idempotency_key_reuse'
