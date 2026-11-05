"""Input bounds and safe unavailable-schema behavior for the visit contract."""
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import ProgrammingError

from app.application.use_cases.checkout import BookingCheckoutUseCases
from app.core.exceptions import (
    OnlinePaymentUnavailableError,
    ServiceUnavailableError,
    ValidationError,
)
from app.infrastructure.db.repositories.platform_repository import PlatformRepository
from tests.conftest import make_profile


async def test_missing_visit_migration_returns_service_unavailable_without_raw_sql():
    session = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())
    original = type("MissingFunction", (Exception,), {"sqlstate":"42883"})("private SQL")
    session.execute.side_effect = ProgrammingError("select private_sql", {}, original)
    repository = PlatformRepository(session)
    with pytest.raises(ServiceUnavailableError) as caught:
        await repository.create_booking({"actor_id":"actor", "service_ids":["service"], "segments":[{"staff_id":"staff","service_ids":["service"]}]})
    assert "private" not in str(caught.value)
    session.rollback.assert_awaited_once()


async def test_absent_itinerary_keeps_legacy_retry_fingerprint():
    session = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())
    repository = PlatformRepository(session)
    repository.begin_booking_operation = AsyncMock(return_value={"id":"legacy-booking"})
    result = await repository.create_booking({"actor_id":"actor", "service_ids":["service"], "segments":None})
    assert result["id"] == "legacy-booking"
    assert "segments" not in repository.begin_booking_operation.call_args.args[3]


def visit_quote_fixture():
    start = datetime(2030, 1, 1, 9, tzinfo=UTC)
    values = {'salon_id': 'salon', 'staff_id': 'first', 'service_ids': ['hair', 'beard'],
              'start_datetime': start, 'payment_mode': 'PAY_AT_SALON', 'segments': [
                  {'staff_id': 'first', 'service_ids': ['hair']},
                  {'staff_id': 'second', 'service_ids': ['beard']}]}
    repo = SimpleNamespace(
        checkout_salon=AsyncMock(return_value={'timezone': 'UTC', 'accepting_bookings': True}),
        get_visit_slots=AsyncMock(return_value=[{'slot_start': start, 'total_price': Decimal('300')}]),
    )
    return BookingCheckoutUseCases(repo, SimpleNamespace(enabled=True)), repo, values


async def test_visit_quote_only_offers_pay_at_salon_even_when_online_is_enabled():
    use_case, _, values = visit_quote_fixture()
    result = await use_case.quote(make_profile(), values)
    assert result['payment_options'] == ['PAY_AT_SALON']
    assert result['online_payment_available'] is False


async def test_visit_quote_refuses_online_payment():
    use_case, _, values = visit_quote_fixture()
    with pytest.raises(OnlinePaymentUnavailableError):
        await use_case.quote(make_profile(), {**values, 'payment_mode': 'PAY_ONLINE'})


@pytest.mark.parametrize('overrides', [
    {'staff_id': 'second'}, {'service_ids': ['hair']},
    {'segments': [{'staff_id': 'first', 'service_ids': ['hair', 'hair', 'beard']}]},
])
async def test_visit_quote_refuses_mismatched_or_duplicate_itineraries(overrides):
    use_case, repo, values = visit_quote_fixture()
    with pytest.raises(ValidationError, match='complete itinerary'):
        await use_case.quote(make_profile(), {**values, **overrides})
    repo.get_visit_slots.assert_not_awaited()
