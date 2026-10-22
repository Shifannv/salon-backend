"""Super-admin month-end statement for salons closed by account deletion.

The statement exposes only money totals per month (no booking, customer or payment-level
detail) and only for a salon whose owner deleted their account.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_session, get_current_actor, get_session
from app.application.use_cases.account_deletion import AccountDeletionUseCases
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.main import app
from tests.conftest import make_owner, make_profile, make_super_admin

SALON = str(uuid4())
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


def _month(month: date, **values) -> dict:
    row = {
        "month": month, "currency": "INR", "online_collected": Decimal("1000.00"),
        "platform_fees": Decimal("50.00"), "overcollected": Decimal("0"),
        "manual_recorded": Decimal("300.00"), "online_count": 2, "manual_count": 1,
        "online_refunded": Decimal("100.00"), "commission_reversed": Decimal("5.00"),
        "subscription_paid": Decimal("499.00"), "subscription_refunded": Decimal("0"),
    }
    row.update(values)
    return row


class _Repo:
    def __init__(self, months=None, known=True):
        self.months = months if months is not None else []
        self.known = known

    async def list_closed_salons(self, limit, offset):
        return [{"id": str(uuid4()), "role": "owner", "salon_id": SALON, "salon_name": "Closed salon",
                 "salon_city": None, "status": "completed", "requested_at": NOW}]

    async def closed_salon_monthly_statement(self, salon_id):
        return self.months if self.known else None


def _uc(repo) -> AccountDeletionUseCases:
    return AccountDeletionUseCases(repo, MagicMock(), MagicMock(), settings)


@pytest.mark.asyncio
async def test_only_super_admin_can_list_or_read_statements():
    uc = _uc(_Repo([_month(date(2026, 9, 1))]))
    for actor in (make_owner(), make_profile()):
        with pytest.raises(ForbiddenError):
            await uc.list_closed_salons(actor, 50, 0)
        with pytest.raises(ForbiddenError):
            await uc.closed_salon_statement(actor, SALON)


@pytest.mark.asyncio
async def test_statement_of_a_salon_that_was_not_closed_by_deletion_is_not_found():
    with pytest.raises(NotFoundError):
        await _uc(_Repo(known=False)).closed_salon_statement(make_super_admin(), SALON)


@pytest.mark.asyncio
async def test_statement_derives_net_figures_and_totals_per_currency():
    repo = _Repo([_month(date(2026, 8, 1)), _month(date(2026, 9, 1), online_collected=Decimal("2000.00"))])
    result = await _uc(repo).closed_salon_statement(make_super_admin(), SALON)

    august = result["months"][0]
    assert august["month"] == "2026-08"
    assert august["platform_commission_net"] == Decimal("45.00")      # 50 - 5 reversed
    assert august["online_net"] == Decimal("855.00")                  # 1000 - 100 - 45
    assert august["platform_revenue"] == Decimal("544.00")            # 45 commission + 499 subscription
    totals = result["totals"]
    assert len(totals) == 1 and totals[0]["currency"] == "INR"
    assert totals[0]["online_collected"] == Decimal("3000.00")
    assert totals[0]["platform_revenue"] == Decimal("1088.00")
    assert totals[0]["online_count"] == 4


@pytest.mark.asyncio
async def test_statement_with_no_transactions_is_empty_not_an_error():
    result = await _uc(_Repo([])).closed_salon_statement(make_super_admin(), SALON)
    assert result["months"] == [] and result["totals"] == []


# ── HTTP ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    overrides = app.dependency_overrides.copy()
    actor = {"value": make_super_admin()}
    app.dependency_overrides[get_current_actor] = lambda: actor["value"]
    app.dependency_overrides[get_session] = lambda: None
    app.dependency_overrides[get_authenticated_session] = lambda: None
    use_cases = AsyncMock(unsafe=True)
    with patch("app.api.v1.routes.account_deletion._use_cases", return_value=use_cases):
        try:
            yield TestClient(app), use_cases, actor
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides)


def test_routes_are_super_admin_only(client):
    http, _uc_mock, actor = client
    actor["value"] = make_owner()
    assert http.get("/v1/admin/deleted-salons").status_code == 403
    assert http.get(f"/v1/admin/deleted-salons/{SALON}/statement").status_code == 403


def test_statement_route_exposes_only_money_totals(client):
    http, uc, _actor = client
    month = {"month": "2026-09", "currency": "INR", "online_collected": "1000.00",
             "online_refunded": "100.00", "platform_fees": "50.00", "commission_reversed": "5.00",
             "platform_commission_net": "45.00", "overcollected": "0", "online_net": "855.00",
             "manual_recorded": "300.00", "subscription_paid": "499.00",
             "subscription_refunded": "0", "platform_revenue": "544.00",
             "online_count": 2, "manual_count": 1,
             "customer_name": "must-not-leak"}
    uc.closed_salon_statement.return_value = {"salon_id": SALON, "months": [month], "totals": []}
    response = http.get(f"/v1/admin/deleted-salons/{SALON}/statement")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"salon_id", "months", "totals"}
    assert "customer_name" not in body["months"][0]


def test_malformed_salon_id_is_rejected_before_the_database(client):
    http, uc, _actor = client
    assert http.get("/v1/admin/deleted-salons/not-a-uuid/statement").status_code == 422
    uc.closed_salon_statement.assert_not_awaited()


def test_queue_route_returns_ledger_rows(client):
    http, uc, _actor = client
    uc.list_closed_salons.return_value = [{
        "id": str(uuid4()), "role": "owner", "salon_id": SALON, "salon_name": "Closed salon",
        "salon_city": None, "status": "completed", "requested_at": NOW.isoformat(),
    }]
    response = http.get("/v1/admin/deleted-salons?limit=10")
    assert response.status_code == 200
    assert response.json()[0]["salon_id"] == SALON
