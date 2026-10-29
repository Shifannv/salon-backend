"""Production cash book rules, pinned to the design fixture and the reference arithmetic."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from app.domain.services.finance_ledger import (
    MAX_RANGE_DAYS,
    TrialState,
    expected_closing_cash,
    finance_allowed,
    local_day_bounds,
    reason_is_written,
    today_in,
)
from tests.support_finance_reference import expected_closing_cash as reference_expected
from tests.support_finance_reference import local_day_bounds as reference_bounds

FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "finance" / "example_day.json").read_text(encoding="utf-8")
)
NOW = datetime(2026, 10, 29, 6, 0, tzinfo=UTC)


class TestCashFormula:
    def test_matches_the_brief_example(self):
        expected = FIXTURE["expected"]
        assert expected_closing_cash(
            opening_cash=FIXTURE["opening_cash_paise"],
            cash_collected=expected["cash_collected_paise"],
            cash_refunds=expected["cash_refunds_paise"],
            cash_expenses=expected["cash_expenses_paise"],
        ) == expected["expected_closing_cash_paise"] == 125000

    @pytest.mark.parametrize(
        "values",
        [
            {"opening_cash": 0, "cash_collected": 0, "cash_refunds": 0, "cash_expenses": 0},
            {"opening_cash": 100, "cash_collected": 50, "cash_refunds": 70, "cash_expenses": 90},
            {"opening_cash": 5, "cash_collected": 1, "cash_refunds": 0, "cash_expenses": 0,
             "adjustments_in": 7, "adjustments_out": 3},
        ],
    )
    def test_production_and_reference_agree(self, values):
        reference = {k.replace("adjustments_", "cash_adjustments_"): v for k, v in values.items()}
        assert expected_closing_cash(**values) == reference_expected(**reference)

    def test_cash_can_go_negative_and_is_reported_as_it_is(self):
        assert expected_closing_cash(opening_cash=0, cash_collected=0, cash_refunds=500, cash_expenses=0) == -500


class TestSalonDay:
    @pytest.mark.parametrize("zone", ["Asia/Kolkata", "America/New_York", "Pacific/Auckland"])
    def test_bounds_match_the_reference(self, zone):
        assert local_day_bounds(date(2026, 3, 8), zone) == reference_bounds(date(2026, 3, 8), zone)

    def test_a_late_night_instant_belongs_to_the_salons_next_day(self):
        instant = datetime(2026, 10, 29, 19, 0, tzinfo=UTC)  # 00:30 on the 30th in India
        assert today_in("Asia/Kolkata", instant) == date(2026, 10, 30)
        assert today_in("UTC", instant) == date(2026, 10, 29)

    def test_a_range_limit_exists(self):
        assert MAX_RANGE_DAYS == 93


class TestReason:
    @pytest.mark.parametrize("value", [None, "", "  ", "ab", " a "])
    def test_too_short_is_not_a_reason(self, value):
        assert reason_is_written(value) is False

    def test_three_characters_is_enough(self):
        assert reason_is_written("tip") is True


def trial(*, started=NOW - timedelta(days=10), ends=NOW + timedelta(days=20), limit=500, counted=0, reached=None):
    return TrialState(started_at=started, ends_at=ends, booking_limit=limit, bookings_counted=counted,
                      limit_reached_at=reached)


class TestPlanGate:
    def test_a_paid_plan_with_the_feature_is_allowed(self):
        assert finance_allowed(features={"daily_ledger": True}, entitlement_active=True, trial=None, now=NOW)

    def test_a_paid_plan_without_the_feature_is_refused_even_if_a_trial_row_exists(self):
        assert not finance_allowed(features={"unlimited_bookings": True}, entitlement_active=True,
                                   trial=trial(), now=NOW)

    def test_the_feature_must_be_exactly_true(self):
        for value in (False, None, "true", 1, "yes"):
            assert not finance_allowed(features={"daily_ledger": value}, entitlement_active=True,
                                       trial=None, now=NOW)

    def test_an_inactive_plan_never_grants_its_features(self):
        assert not finance_allowed(features={"daily_ledger": True}, entitlement_active=False, trial=None, now=NOW)

    def test_a_salon_on_its_free_trial_counts_as_growth(self):
        assert finance_allowed(features={}, entitlement_active=False, trial=trial(), now=NOW)

    @pytest.mark.parametrize(
        "state",
        [
            trial(ends=NOW - timedelta(seconds=1)),
            trial(ends=NOW),
            trial(limit=10, counted=10),
            trial(limit=10, counted=11),
            trial(reached=NOW - timedelta(days=1)),
            TrialState(None, None, None, None, None),
        ],
    )
    def test_an_expired_exhausted_or_missing_trial_is_refused(self, state):
        assert not finance_allowed(features={}, entitlement_active=False, trial=state, now=NOW)

    def test_no_trial_and_no_plan_is_refused(self):
        assert not finance_allowed(features={}, entitlement_active=False, trial=None, now=NOW)

    def test_a_trial_without_a_booking_limit_is_judged_on_its_dates_alone(self):
        assert finance_allowed(features={}, entitlement_active=False, trial=trial(limit=None), now=NOW)
