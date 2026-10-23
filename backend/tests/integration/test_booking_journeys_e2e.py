"""HTTP -> use case -> actual Postgres booking/ledger/outbox end-to-end checks.

Uses only an automatically cleaned local database. Auth extraction is replaced
with explicit fixture actors; no production JWT or external provider is involved.
"""

import asyncio
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.api.deps import get_authenticated_session, get_current_actor
from app.infrastructure.db.session import get_session, set_actor_context
from app.main import create_app
from tests.conftest import make_owner
from tests.integration.test_booking_contract_sql import _customer
from tests.integration.test_checkout_safety_sql import safety, safety_db  # noqa: F401
from tests.integration.test_payment_ledger_sql import TEST_DB

pytestmark = pytest.mark.skipif(not TEST_DB, reason="Requires disposable local PostgreSQL")


async def attendance_guard(env):
    """Exercise the new SQL on the portable test schema, never bypass remote Alembic gates."""
    source = Path(__file__).parents[2] / 'migrations/sql/0043_no_show_attendance_guards.sql'
    async with env.session() as session:
        for statement in source.read_text(encoding='utf-8').split('\n-- statement --\n'):
            if statement.strip():
                await session.execute(text(statement))
        await session.commit()


def local_app(env, monkeypatch, initial_actor):
    from app.infrastructure.db import session as session_module
    from app.infrastructure.push import outbox_worker

    monkeypatch.setattr(session_module, 'AsyncSessionLocal', env.session)
    monkeypatch.setattr(outbox_worker, 'AsyncSessionLocal', env.session)
    app = create_app()
    identity = {'actor': initial_actor}

    async def actor():
        return identity['actor']

    async def session():
        async with env.session() as transaction:
            await set_actor_context(transaction, identity['actor'].id)
            yield transaction

    app.dependency_overrides[get_current_actor] = actor
    app.dependency_overrides[get_authenticated_session] = session
    app.dependency_overrides[get_session] = session
    return app, identity


@pytest.mark.parametrize('source', ['app', 'qr_walkin', 'manual_walkin'])
async def test_booking_check_in_collection_completion_journey(safety, monkeypatch, source):  # noqa: F811
    fixture = await safety.seed()
    customer, owner = _customer(fixture['customer']), make_owner(fixture['owner'])
    app, identity = local_app(safety, monkeypatch, owner if source == 'manual_walkin' else customer)
    token = (await safety.sql('select qr_token from salons where id=:id', id=fixture['salon']))[0]['qr_token']
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        resolved = await client.get(f'/v1/walkin/{token}', params={'fresh': 'true'})
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()['id'] == fixture['salon']
        assert any(item['id'] == fixture['service'] for item in resolved.json()['services'])
        image = await client.get(f'/v1/walkin/{token}/qr')
        assert image.status_code == 200 and image.content.startswith(b'\x89PNG')
        available = await client.get('/v1/availability', params=[
            ('staff_id', fixture['staff']), ('date', fixture['start'].date().isoformat()),
            ('service_ids', fixture['service']),
        ])
        assert available.status_code == 200 and available.json(), available.text
        body = {
            'salon_id': fixture['salon'], 'staff_id': fixture['staff'],
            'service_ids': [fixture['service']], 'start_datetime': fixture['start'].isoformat(),
            'customer_name': 'Isolated journey customer', 'source': source,
            'payment_preference': 'pay_at_salon',
        }
        url = f'/v1/walkin/{token}/bookings' if source == 'qr_walkin' else '/v1/bookings'
        created = await client.post(url, json=body, headers={'Idempotency-Key': 'e2e-create-001'})
        assert created.status_code == 201, created.text
        booking = created.json()
        booking_id = booking['id']
        assert booking['source'] == source
        assert str(booking['total_price']) in {'250', '250.0', '250.00'}
        replay = await client.post(url, json=body, headers={'Idempotency-Key': 'e2e-create-001'})
        assert replay.status_code == 201 and replay.json()['id'] == booking_id
        identity['actor'] = customer
        denied = await client.post(f'/v1/bookings/{booking_id}/check-in')
        assert denied.status_code == 403
        identity['actor'] = owner
        if booking['status'] == 'pending':
            approved = await client.post(f'/v1/bookings/{booking_id}/approve')
            assert approved.status_code == 200, approved.text
        # Advance only fixture appointment data into its visit window. No production clock/data changes.
        await safety.sql("update bookings set start_datetime=now()-interval '15 minutes', "
                         "end_datetime=now()+interval '15 minutes' where id=:id", id=booking_id)
        checked = await client.post(f'/v1/bookings/{booking_id}/check-in', headers={'Idempotency-Key': 'e2e-check-in-001'})
        assert checked.status_code == 200 and checked.json()['status'] == 'checked_in', checked.text
        unpaid = await client.post(f'/v1/bookings/{booking_id}/complete')
        assert unpaid.status_code == 409 and unpaid.json()['error']['code'] == 'payment_collection_required'
        received = await client.post(f'/v1/bookings/{booking_id}/payment', json={'payment_method': 'cash'},
                                     headers={'Idempotency-Key': 'e2e-collect-001'})
        assert received.status_code == 200, received.text
        done, again = await asyncio.gather(*[
            client.post(f'/v1/bookings/{booking_id}/complete', headers={'Idempotency-Key': 'e2e-complete-001'})
            for _ in range(2)
        ])
        assert done.status_code == again.status_code == 200, done.text + again.text
        assert done.json()['status'] == again.json()['status'] == 'completed'
    ledger = await safety.sql('select amount from booking_payments where booking_id=:id', id=booking_id)
    assert len(ledger) == 1 and ledger[0]['amount'] == 250
    events = await safety.sql("select actor_id from booking_audit_events where booking_id=:id and new_state='completed'", id=booking_id)
    assert len(events) == 1 and str(events[0]['actor_id']) == owner.id
    if source != 'manual_walkin':
        notices = await safety.sql("select id from notifications where booking_id=:id and type='booking_completed'", id=booking_id)
        assert len(notices) == 1, 'A completion retry must not send a second completion notice'


async def test_no_show_grace_reason_notification_and_replay(safety, monkeypatch):  # noqa: F811
    await attendance_guard(safety)
    await attendance_guard(safety)
    fixture = await safety.seed()
    booking = await safety.book(fixture)
    app, identity = local_app(safety, monkeypatch, make_owner(fixture['owner']))
    booking_id = str(booking['id'])
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        if booking['status'] == 'pending':
            assert (await client.post(f'/v1/bookings/{booking_id}/approve')).status_code == 200
        for payload in ({}, {'reason': '   '}):
            assert (await client.post(f'/v1/bookings/{booking_id}/no-show', json=payload)).status_code == 422
        await safety.sql("update bookings set start_datetime=now()-interval '9 minutes', "
                         "end_datetime=now()+interval '21 minutes' where id=:id", id=booking_id)
        early = await client.post(f'/v1/bookings/{booking_id}/no-show', json={'reason': 'Customer did not arrive'})
        assert early.status_code == 422
        with pytest.raises(DBAPIError, match='no_show_grace_period'):
            await safety.sql("update bookings set status='no_show',cancellation_reason='Did not arrive' where id=:id", id=booking_id)
        with pytest.raises(DBAPIError, match='no_show_grace_period'):
            await safety.sql("update bookings set status='cancelled',cancellation_reason='Customer no-show' where id=:id", id=booking_id)
        await safety.sql("update bookings set start_datetime=now()-interval '11 minutes', "
                         "end_datetime=now()+interval '19 minutes' where id=:id", id=booking_id)
        with pytest.raises(DBAPIError, match='no_show_reason_required'):
            await safety.sql("update bookings set status='no_show' where id=:id", id=booking_id)
        with pytest.raises(DBAPIError, match='no_show_reason_required'):
            await safety.sql("update bookings set status='no_show',cancellation_reason=E'\\t \\n' where id=:id", id=booking_id)
        identity['actor'] = _customer(fixture['customer'])
        denied = await client.post(f'/v1/bookings/{booking_id}/no-show', json={'reason': 'Did not arrive'})
        assert denied.status_code == 403
        identity['actor'] = make_owner(fixture['owner'])
        for _ in range(2):
            marked = await client.post(f'/v1/bookings/{booking_id}/no-show',
                                      json={'reason': 'Customer did not arrive'}, headers={'Idempotency-Key': 'e2e-no-show-001'})
            assert marked.status_code == 200 and marked.json()['status'] == 'no_show', marked.text
    notices = await safety.sql("select id from notifications where booking_id=:id and type='booking_no_show'", id=booking_id)
    assert len(notices) == 1
    restriction = await safety.sql('select no_show_count from customer_booking_restrictions where customer_id=:id', id=fixture['customer'])
    assert restriction[0]['no_show_count'] == 1


async def test_sql_exact_no_show_boundary_and_same_state_erasure(safety):  # noqa: F811
    await attendance_guard(safety)
    fixture = await safety.seed()
    booking = await safety.book(fixture)
    async with safety.session() as session:
        await set_actor_context(session, fixture['owner'])
        await session.execute(text("update bookings set status='no_show', "
            "start_datetime=statement_timestamp()-interval '10 minutes', "
            "end_datetime=statement_timestamp()+interval '20 minutes', "
            "cancellation_reason='Customer no-show' where id=:id"), {'id': booking['id']})
        await session.commit()
    audit = await safety.sql("select actor_id from booking_audit_events where booking_id=:id and new_state='no_show'", id=booking['id'])
    assert len(audit) == 1 and str(audit[0]['actor_id']) == fixture['owner']
    async with safety.session() as session:
        await session.execute(text("set local app.account_erasure='on'"))
        await session.execute(text("update bookings set cancellation_reason=null where id=:id"), {'id': booking['id']})
        await session.execute(text("update booking_audit_events set actor_id=null where booking_id=:id"), {'id': booking['id']})
        await session.commit()
    retained = await safety.sql('select status::text,cancellation_reason from bookings where id=:id', id=booking['id'])
    assert retained[0]['status'] == 'no_show' and retained[0]['cancellation_reason'] is None


async def test_checked_in_booking_cannot_be_marked_absent_by_either_path(safety, monkeypatch):  # noqa: F811
    await attendance_guard(safety)
    fixture = await safety.seed()
    booking = await safety.book(fixture)
    await safety.sql("update bookings set status='checked_in',start_datetime=now()-interval '20 minutes', "
                     "end_datetime=now()+interval '10 minutes' where id=:id", id=booking['id'])
    for target in ('no_show', 'cancelled'):
        with pytest.raises(DBAPIError, match='no_show_after_check_in'):
            await safety.sql("update bookings set status=cast(:target as booking_status), "
                             "cancellation_reason='Customer no-show' where id=:id", target=target, id=booking['id'])
    app, _ = local_app(safety, monkeypatch, make_owner(fixture['owner']))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://local.test') as client:
        rejected = await client.post(f"/v1/bookings/{booking['id']}/no-show", json={'reason': 'Did not arrive'})
        assert rejected.status_code == 409
