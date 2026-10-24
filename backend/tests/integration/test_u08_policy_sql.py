"""Explicit disposable sidecar tests; no remote Alembic policy is bypassed."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.domain.services.booking_finance_policy import POLICY_VERSION
from app.infrastructure.db.session import set_actor_context
from tests.conftest import make_owner
from tests.integration.test_booking_contract_sql import _customer
from tests.integration.test_booking_journeys_e2e import local_app
from tests.integration.test_checkout_safety_sql import safety, safety_db  # noqa: F401
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason='Requires disposable local PostgreSQL')
SQL = Path(__file__).parents[2] / 'migrations/sql'


async def policy_sql(env):
    async with env.session() as session:
        for statement in (SQL / '0044_versioned_checkout_policy.sql').read_text(encoding='utf-8').split('\n-- statement --\n'):
            if statement.strip():
                await session.execute(text(statement))
        await session.commit()


async def test_missing_policy_migration_rolls_back_instead_of_silently_binding_legacy(safety, monkeypatch):  # noqa: F811
    # Restore only the historical stamp in this disposable fixture to reproduce a
    # code-before-schema rollout. Always restore the candidate afterwards.
    old_stamp = (SQL / '0037_customer_processing_charge.sql').read_text(encoding='utf-8').split('-- statement --')[1]
    await safety.sql(old_stamp.replace('create function', 'create or replace function', 1))
    historical_fixture = await safety.seed()
    historical = await safety.book(historical_fixture)
    fixture = await safety.seed()
    monkeypatch.setattr(settings, 'booking_checkout_policy_version', POLICY_VERSION)
    app, _ = local_app(safety, monkeypatch, _customer(fixture['customer']))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
            result = await client.post('/v1/bookings', json={
                'salon_id': fixture['salon'], 'staff_id': fixture['staff'],
                'service_ids': [fixture['service']], 'start_datetime': fixture['start'].isoformat(),
                'customer_name': 'Policy test', 'payment_preference': 'pay_at_salon',
            }, headers={'Idempotency-Key': 'missing-policy-001'})
        assert result.status_code == 503, result.text
        assert 'SQL' not in result.text
        assert not await safety.sql('select id from bookings where salon_id=:id', id=fixture['salon'])
        assert not await safety.sql('select id from booking_audit_events where actor_id=:id', id=fixture['customer'])
        access = await safety.sql('select bookings_counted from salon_access where salon_id=:id', id=fixture['salon'])
        assert access[0]['bookings_counted'] == 0
    finally:
        await policy_sql(safety)
    stored = await safety.sql('select checkout_policy_version from bookings where id=:id', id=historical['id'])
    assert stored[0]['checkout_policy_version'] == 'customer_processing_v1'


@pytest.mark.parametrize('source', ['app', 'qr_walkin', 'manual_walkin'])
async def test_new_policy_is_stored_atomically_and_never_rewritten(safety, monkeypatch, source):  # noqa: F811
    await policy_sql(safety)
    await policy_sql(safety)
    fixture = await safety.seed()
    monkeypatch.setattr(settings, 'booking_checkout_policy_version', POLICY_VERSION)
    actor = make_owner(fixture['owner']) if source == 'manual_walkin' else _customer(fixture['customer'])
    app, _ = local_app(safety, monkeypatch, actor)
    token = (await safety.sql('select qr_token from salons where id=:id', id=fixture['salon']))[0]['qr_token']
    route = f'/v1/walkin/{token}/bookings' if source == 'qr_walkin' else '/v1/bookings'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        body = {'salon_id': fixture['salon'], 'staff_id': fixture['staff'],
                'service_ids': [fixture['service']], 'start_datetime': fixture['start'].isoformat(),
                'customer_name': 'Policy test', 'source': source, 'payment_preference': 'pay_at_salon',
                'checkout_policy_version': 'customer_processing_v1'}  # Client cannot select policy.
        created = await client.post(route, json=body, headers={'Idempotency-Key': 'policy-create-001'})
        assert created.status_code == 201, created.text
        booking_id = created.json()['id']
        replay = await client.post(route, json=body, headers={'Idempotency-Key': 'policy-create-001'})
        assert replay.status_code == 201 and replay.json()['id'] == booking_id
    stored = await safety.sql('select checkout_policy_version from bookings where id=:id', id=booking_id)
    assert stored[0]['checkout_policy_version'] == POLICY_VERSION
    with pytest.raises(DBAPIError, match='checkout_policy_is_immutable'):
        await safety.sql("update bookings set checkout_policy_version='customer_processing_v1' where id=:id", id=booking_id)
    monkeypatch.setattr(settings, 'booking_checkout_policy_version', 'customer_processing_v1')
    later = await safety.seed()
    legacy = await safety.book(later)
    assert (await safety.sql('select checkout_policy_version from bookings where id=:id', id=legacy['id']))[0]['checkout_policy_version'] == 'customer_processing_v1'
    assert (await safety.sql('select checkout_policy_version from bookings where id=:id', id=booking_id))[0]['checkout_policy_version'] == POLICY_VERSION


async def test_database_rejects_unknown_policy_and_never_adds_client_execute_grants(safety):  # noqa: F811
    await policy_sql(safety)
    fixture = await safety.seed()
    async with safety.session() as session:
        await set_actor_context(session, fixture['customer'])
        await session.execute(text("select set_config('app.booking_checkout_policy_version','unknown',true)"))
        with pytest.raises(DBAPIError, match='unsupported_checkout_policy'):
            await session.execute(text("select public.create_booking(cast(:salon as uuid),cast(:staff as uuid),"
                                       "array[cast(:service as uuid)],cast(:start as timestamptz),"
                                       "'Policy test',null,'app'::booking_source,null)"), fixture)
        await session.rollback()
    acl = await safety.sql("select has_function_privilege('anon','public.stamp_checkout_policy()','EXECUTE') as anon,"
                           "has_function_privilege('authenticated','public.stamp_checkout_policy()','EXECUTE') as authenticated")
    assert not acl[0]['anon'] and not acl[0]['authenticated']


async def test_policy_setting_is_local_to_transaction_on_reused_connection(safety):  # noqa: F811
    async with safety.engine.connect() as connection:
        await connection.execute(text("select set_config('app.booking_checkout_policy_version',:policy,true)"),
                                 {'policy': POLICY_VERSION})
        assert await connection.scalar(text("select current_setting('app.booking_checkout_policy_version',true)")) == POLICY_VERSION
        await connection.commit()
        assert await connection.scalar(text("select current_setting('app.booking_checkout_policy_version',true)")) in (None, '')
        await connection.rollback()
