"""Pins the owner-finance design arithmetic (Phase 1) to the product brief's 700-rupee example.

Design tests only: pure functions in tests/support_finance_reference.py, no database, no app code.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tests.support_finance_reference import (
    CommissionPolicy,
    close_difference,
    earned_commission,
    expected_closing_cash,
    half_up_div,
    local_day_bounds,
    net_expense_total,
    refund_reversals,
)

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "finance" / "example_day.json").read_text(encoding="utf-8")
)
EXPECTED = FIXTURE["expected"]


def policy(name: str) -> CommissionPolicy:
    return CommissionPolicy(**FIXTURE["policies"][name])


def lines_for(staff: str) -> list[dict]:
    return [s for s in FIXTURE["booking"]["services"] if s["staff"] == staff]


class TestExampleDay:
    def test_sales_and_receipts_are_separate_salon_level_totals(self):
        services = FIXTURE["booking"]["services"]
        assert sum(s["value_paise"] for s in services) == EXPECTED["gross_completed_sales_paise"]
        cash = sum(r["amount_paise"] for r in FIXTURE["receipts"] if r["method"] == "cash")
        upi = sum(r["amount_paise"] for r in FIXTURE["receipts"] if r["method"] == "upi_direct")
        assert (cash, upi) == (EXPECTED["cash_collected_paise"], EXPECTED["non_cash_received_paise"])
        # Money in equals value sold, so nothing is outstanding.
        assert cash + upi == EXPECTED["gross_completed_sales_paise"]
        assert EXPECTED["outstanding_due_paise"] == 0

    def test_expected_closing_cash_follows_the_approved_formula(self):
        cash_expenses = sum(
            e["amount_paise"] for e in FIXTURE["expenses"] if e["payment_method"] == "cash"
        )
        assert cash_expenses == EXPECTED["cash_expenses_paise"]
        assert expected_closing_cash(
            opening_cash=FIXTURE["opening_cash_paise"],
            cash_collected=EXPECTED["cash_collected_paise"],
            cash_refunds=EXPECTED["cash_refunds_paise"],
            cash_expenses=cash_expenses,
        ) == EXPECTED["expected_closing_cash_paise"]

    def test_a_non_cash_expense_and_a_non_cash_receipt_never_touch_cash(self):
        base = expected_closing_cash(
            opening_cash=0, cash_collected=40000, cash_refunds=0, cash_expenses=0
        )
        assert base == 40000  # the 20000 non-cash utilities expense and the 30000 UPI are not cash

    def test_audited_adjustments_move_cash_both_ways(self):
        assert expected_closing_cash(
            opening_cash=0, cash_collected=0, cash_refunds=0, cash_expenses=0,
            cash_adjustments_in=2500, cash_adjustments_out=1000,
        ) == 1500

    @pytest.mark.parametrize("staff", ["Hafis", "Shuhail"])
    def test_staff_earnings_come_from_service_lines_not_from_how_the_customer_paid(self, staff):
        lines = lines_for(staff)
        expected = EXPECTED["staff"][staff]
        assert len(lines) == expected["services_completed"]
        assert sum(s["value_paise"] for s in lines) == expected["attributable_value_paise"]
        earned = sum(earned_commission(policy(staff), s["value_paise"]) for s in lines)
        assert earned == expected["earned_paise"]

    def test_a_partial_refund_reverses_only_its_share_of_that_services_commission(self):
        haircut = next(s for s in FIXTURE["booking"]["services"] if s["service_id"] == "haircut")
        earned = earned_commission(policy("Hafis"), haircut["value_paise"])
        assert earned == 12000
        refund = FIXTURE["refunds"][0]["amount_paise"]
        assert refund_reversals(earned, haircut["value_paise"], [refund]) == [
            EXPECTED["staff"]["Hafis"]["haircut_reversal_paise"]
        ]


class TestCommission:
    def test_none_pays_nothing_and_cannot_carry_a_rate(self):
        assert earned_commission(CommissionPolicy("NONE"), 50000) == 0
        with pytest.raises(ValueError):
            CommissionPolicy("NONE", rate_basis_points=1000)

    def test_percent_rounds_half_up_to_the_paise(self):
        # 12.5% of 1.01 rupees = 12.625 paise -> 13
        assert earned_commission(CommissionPolicy("PERCENT_OF_SERVICE_VALUE", rate_basis_points=1250), 101) == 13
        assert half_up_div(5, 2) == 3 and half_up_div(4, 2) == 2

    def test_a_policy_must_have_exactly_the_fields_for_its_type(self):
        for bad in (
            {"commission_type": "PERCENT_OF_SERVICE_VALUE"},
            {"commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": 10001},
            {"commission_type": "PERCENT_OF_SERVICE_VALUE", "rate_basis_points": 100, "fixed_amount_paise": 5},
            {"commission_type": "FIXED_PER_SERVICE"},
            {"commission_type": "FIXED_PER_SERVICE", "fixed_amount_paise": -1},
            {"commission_type": "BONUS"},
        ):
            with pytest.raises(ValueError):
                CommissionPolicy(**bad)

    def test_a_later_rule_change_cannot_rewrite_a_stored_earning(self):
        snapshot = policy("Hafis")
        stored = earned_commission(snapshot, 30000)
        new_rule = CommissionPolicy("PERCENT_OF_SERVICE_VALUE", rate_basis_points=1000)
        assert earned_commission(new_rule, 30000) != stored
        assert earned_commission(snapshot, 30000) == stored  # recomputing from the snapshot is stable

    @pytest.mark.parametrize("splits", [[10001], [3334, 3333, 3334], [1] * 10001, [5000, 5001]])
    def test_reversals_never_drift_or_exceed_the_earning(self, splits):
        value = 10001
        earned = earned_commission(CommissionPolicy("PERCENT_OF_SERVICE_VALUE", rate_basis_points=3333), value)
        reversals = refund_reversals(earned, value, splits)
        assert sum(reversals) == earned  # the whole service refunded reverses the whole earning
        assert all(r >= 0 for r in reversals)

    def test_refunding_more_than_the_service_value_is_refused(self):
        with pytest.raises(ValueError):
            refund_reversals(1000, 5000, [3000, 2001])


class TestDayClose:
    def test_a_matching_count_needs_no_reason(self):
        assert close_difference(125000, 125000, None) == 0

    def test_a_shortfall_or_surplus_needs_a_written_reason(self):
        with pytest.raises(ValueError, match="difference_reason_required"):
            close_difference(125000, 124500, None)
        with pytest.raises(ValueError, match="difference_reason_required"):
            close_difference(125000, 125500, "   ")
        assert close_difference(125000, 124500, "Tip jar emptied") == -500


class TestExpenses:
    def test_a_reversal_cancels_exactly_one_expense_and_never_edits_it(self):
        entries = [
            {"id": "e1", "entry_type": "expense", "amount_paise": 5000, "reverses_id": None},
            {"id": "e2", "entry_type": "expense", "amount_paise": 20000, "reverses_id": None},
            {"id": "r1", "entry_type": "reversal", "amount_paise": 5000, "reverses_id": "e1"},
        ]
        assert net_expense_total(entries) == 20000

    def test_double_reversal_and_dangling_reversal_are_refused(self):
        base = [{"id": "e1", "entry_type": "expense", "amount_paise": 5000, "reverses_id": None}]
        twice = base + [
            {"id": "r1", "entry_type": "reversal", "amount_paise": 5000, "reverses_id": "e1"},
            {"id": "r2", "entry_type": "reversal", "amount_paise": 5000, "reverses_id": "e1"},
        ]
        with pytest.raises(ValueError, match="expense_already_reversed"):
            net_expense_total(twice)
        with pytest.raises(ValueError):
            net_expense_total(base + [{"id": "r", "entry_type": "reversal", "amount_paise": 1, "reverses_id": "nope"}])

    def test_amounts_must_be_positive_integers_of_paise(self):
        with pytest.raises(ValueError):
            net_expense_total([{"id": "e", "entry_type": "expense", "amount_paise": 0, "reverses_id": None}])


class TestSalonLocalDay:
    def test_a_late_night_payment_belongs_to_the_next_local_day(self):
        start, end = local_day_bounds(date(2026, 10, 29), FIXTURE["timezone"])
        assert (start, end) == (
            datetime(2026, 10, 28, 18, 30, tzinfo=UTC),
            datetime(2026, 10, 29, 18, 30, tzinfo=UTC),
        )
        just_before_midnight_ist = datetime(2026, 10, 29, 18, 29, tzinfo=UTC)
        just_after = datetime(2026, 10, 29, 18, 30, tzinfo=UTC)
        assert start <= just_before_midnight_ist < end
        assert not start <= just_after < end  # the interval is half-open

    def test_consecutive_days_neither_overlap_nor_leave_a_gap(self):
        _, first_end = local_day_bounds(date(2026, 10, 29), "Asia/Kolkata")
        second_start, _ = local_day_bounds(date(2026, 10, 30), "Asia/Kolkata")
        assert first_end == second_start

    def test_a_dst_zone_has_a_23_hour_day(self):
        start, end = local_day_bounds(date(2026, 3, 8), "America/New_York")
        assert (end - start).total_seconds() == 23 * 3600
