"""Unit tests for profit_paise, balance_paise and per-staff lists on the daily ledger."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.use_cases.finance import FinanceUseCases
from app.domain.entities.profile import Profile, Role
from app.domain.services.finance_ledger import (
    daily_balance,
    daily_profit,
    group_receipts_by_staff,
)

# ---------------------------------------------------------------------------
# Domain helper: daily_balance
# ---------------------------------------------------------------------------


def test_balance_is_received_minus_expenses():
    assert daily_balance(cash_collected=10_000, non_cash_received=5_000, expenses_total=3_000) == 12_000


def test_balance_can_be_negative():
    assert daily_balance(cash_collected=0, non_cash_received=0, expenses_total=5_000) == -5_000


def test_balance_is_zero_when_empty():
    assert daily_balance(cash_collected=0, non_cash_received=0, expenses_total=0) == 0


# ---------------------------------------------------------------------------
# Domain helper: daily_profit
# ---------------------------------------------------------------------------


def test_profit_subtracts_refunds_from_balance():
    balance = daily_balance(cash_collected=10_000, non_cash_received=0, expenses_total=2_000)
    assert daily_profit(balance_paise=balance, cash_refunds=1_000, non_cash_refunds=500) == 6_500


def test_profit_can_be_negative():
    assert daily_profit(balance_paise=1_000, cash_refunds=2_000, non_cash_refunds=0) == -1_000


def test_profit_zero_when_all_refunded():
    assert daily_profit(balance_paise=5_000, cash_refunds=3_000, non_cash_refunds=2_000) == 0


# ---------------------------------------------------------------------------
# Domain helper: group_receipts_by_staff
# ---------------------------------------------------------------------------

ALICE = {"staff_id": "a1", "staff_name": "Alice", "cash_paise": 6_000, "non_cash_paise": 0}
BOB = {"staff_id": "b2", "staff_name": "Bob", "cash_paise": 4_000, "non_cash_paise": 2_000}


def test_group_projects_cash_key():
    rows = group_receipts_by_staff([ALICE, BOB], total=10_000, amount_key="cash_paise")
    assert len(rows) == 2
    assert all("cash_paise" in r for r in rows)
    assert all("non_cash_paise" not in r for r in rows)
    assert sum(r["cash_paise"] for r in rows) == 10_000


def test_group_projects_non_cash_key():
    rows = group_receipts_by_staff([ALICE, BOB], total=2_000, amount_key="non_cash_paise")
    ids = [r["staff_id"] for r in rows]
    assert "b2" in ids
    assert "a1" not in ids  # Alice's non_cash is 0 — dropped


def test_group_appends_unassigned_for_remainder():
    rows = group_receipts_by_staff([ALICE], total=10_000, amount_key="cash_paise")
    unassigned = next(r for r in rows if r["staff_id"] == "unassigned")
    assert unassigned["cash_paise"] == 4_000  # 10000 - 6000


def test_group_no_unassigned_when_total_equals_sum():
    rows = group_receipts_by_staff([ALICE, BOB], total=10_000, amount_key="cash_paise")
    assert all(r["staff_id"] != "unassigned" for r in rows)


def test_group_empty_receipts_all_unassigned():
    rows = group_receipts_by_staff([], total=5_000, amount_key="cash_paise")
    assert len(rows) == 1
    assert rows[0]["staff_id"] == "unassigned"
    assert rows[0]["cash_paise"] == 5_000


def test_group_empty_receipts_zero_total_returns_empty():
    assert group_receipts_by_staff([], total=0, amount_key="cash_paise") == []


# ---------------------------------------------------------------------------
# Use case: daily_ledger returns new fields
# ---------------------------------------------------------------------------

_SALON_ID = str(uuid4())
_NOW = datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)
_DATE = date(2026, 11, 9)
_TIMEZONE = "Asia/Kolkata"


def _make_actor() -> Profile:
    actor = MagicMock(spec=Profile)
    actor.id = str(uuid4())
    actor.role = Role.owner
    return actor


def _make_salon() -> dict:
    return {
        "id": _SALON_ID, "timezone": _TIMEZONE, "is_active": True,
        "profile_completed": True, "approval_status": "approved", "can_write": True,
    }


def _make_figures(**overrides) -> dict:
    base = {
        "sales": 50_000, "cash_collected": 20_000, "non_cash_received": 10_000,
        "cash_refunds": 2_000, "non_cash_refunds": 1_000,
        "cash_expenses": 3_000, "non_cash_expenses": 2_000,
        "adjustments_in": 0, "adjustments_out": 0,
        "paid_without_receipt": False, "refund_pending": False,
    }
    return {**base, **overrides}


def _make_repo(figures=None, receipts=None, staff_on=True) -> MagicMock:
    repo = MagicMock()
    repo.owner_salon = AsyncMock(return_value=_make_salon())
    # Return a fresh dict each call: _salon pops "feature_access" in-place, so a shared
    # return_value would arrive empty on the second plan_access call in daily_ledger.
    def _fresh_access(*_a, **_kw):
        return {
            "features": {}, "entitlement_active": True, "trial": None,
            "feature_access": {
                "daily_ledger": {"enabled": True, "source": "plan", "plans": []},
                "staff_earnings": {"enabled": staff_on, "source": "plan", "plans": []},
                "finance_page": {"enabled": True, "source": "plan", "plans": []},
            },
        }
    repo.plan_access = AsyncMock(side_effect=_fresh_access)
    repo.day_figures = AsyncMock(return_value=figures or _make_figures())
    repo.receipts_by_staff = AsyncMock(return_value=receipts or [])
    repo.opening_cash = AsyncMock(return_value=(0, "not_set"))
    repo.latest_close = AsyncMock(return_value=None)
    repo.outstanding_due = AsyncMock(return_value=0)
    return repo


@pytest.mark.asyncio
async def test_balance_paise_equals_received_minus_expenses():
    repo = _make_repo()
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    # 20000 + 10000 - (3000 + 2000) = 25000
    assert result["balance_paise"] == 25_000


@pytest.mark.asyncio
async def test_profit_paise_subtracts_refunds_from_balance():
    repo = _make_repo()
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    # balance 25000 - (2000 + 1000) = 22000
    assert result["profit_paise"] == 22_000


@pytest.mark.asyncio
async def test_cash_adjustments_excluded_from_profit():
    figures = _make_figures(adjustments_in=5_000, adjustments_out=3_000)
    repo = _make_repo(figures=figures)
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    # balance = 20000+10000-5000 = 25000; profit = 25000-3000 = 22000 (adjustments irrelevant)
    assert result["profit_paise"] == 22_000


@pytest.mark.asyncio
async def test_staff_lists_empty_when_staff_earnings_locked():
    repo = _make_repo(staff_on=False)
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    assert result["cash_by_staff"] == []
    assert result["non_cash_by_staff"] == []
    repo.receipts_by_staff.assert_not_called()


@pytest.mark.asyncio
async def test_staff_lists_populated_when_staff_earnings_enabled():
    receipts = [
        {"staff_id": "s1", "staff_name": "Staff One", "cash_paise": 20_000, "non_cash_paise": 10_000},
    ]
    repo = _make_repo(receipts=receipts, staff_on=True)
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    assert len(result["cash_by_staff"]) == 1
    assert result["cash_by_staff"][0]["staff_id"] == "s1"
    assert result["cash_by_staff"][0]["cash_paise"] == 20_000
    assert len(result["non_cash_by_staff"]) == 1
    assert result["non_cash_by_staff"][0]["non_cash_paise"] == 10_000


@pytest.mark.asyncio
async def test_unassigned_row_added_for_remainder():
    receipts = [
        {"staff_id": "s1", "staff_name": "Staff One", "cash_paise": 15_000, "non_cash_paise": 0},
    ]
    repo = _make_repo(receipts=receipts, staff_on=True)
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    unassigned = next((r for r in result["cash_by_staff"] if r["staff_id"] == "unassigned"), None)
    assert unassigned is not None
    assert unassigned["cash_paise"] == 5_000  # 20000 - 15000


@pytest.mark.asyncio
async def test_existing_fields_unchanged():
    repo = _make_repo()
    uc = FinanceUseCases(repo, clock=lambda: _NOW)
    result = await uc.daily_ledger(_make_actor(), _DATE)
    assert result["cash_collected_paise"] == 20_000
    assert result["non_cash_received_paise"] == 10_000
    assert result["expenses_total_paise"] == 5_000
    assert result["gross_completed_sales_paise"] == 50_000
    assert result["needs_review"] is False
    assert result["can_write"] is True
