"""Staff earnings money rules (S1): which rule applies, what is earned, how a refund reverses it.

Pure functions on integer paise. No database. The precedence is the owner's decision F07 and the
snapshot-at-completion and append-only reversal behaviour are F10 and the Phase 1 design.
"""

from datetime import UTC, datetime, timedelta
from itertools import product

import pytest

from app.domain.services.staff_earnings import (
    CommissionRule,
    earned_amount,
    reversal_due,
    select_rule,
    split_refund_across_lines,
)

T0 = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)


def rule(*, staff=None, service=None, kind="PERCENT_OF_SERVICE_VALUE", bps=None, fixed=None, since=T0, version=1, rid=None):
    if kind == "PERCENT_OF_SERVICE_VALUE" and bps is None:
        bps = 2000
    return CommissionRule(
        id=rid or f"r-{staff}-{service}-{version}", staff_id=staff, service_id=service, version=version,
        commission_type=kind, rate_basis_points=bps if kind == "PERCENT_OF_SERVICE_VALUE" else None,
        fixed_amount_paise=fixed if kind == "FIXED_PER_SERVICE" else None, effective_from=since,
    )


class TestPrecedence:
    """F07: 1 staff+service, 2 staff-wide, 3 service-wide, 4 salon default, 5 nothing = zero."""

    def rules(self):
        return [
            rule(staff="hafis", service="haircut", bps=1000, rid="staff+service"),
            rule(staff="hafis", bps=2000, rid="staff"),
            rule(service="haircut", bps=3000, rid="service"),
            rule(bps=4000, rid="default"),
        ]

    def test_the_most_specific_rule_wins(self):
        assert select_rule(self.rules(), "hafis", "haircut", T0).id == "staff+service"

    def test_then_the_staff_wide_rule(self):
        assert select_rule(self.rules(), "hafis", "colour", T0).id == "staff"

    def test_then_the_service_wide_rule(self):
        assert select_rule(self.rules(), "shuhail", "haircut", T0).id == "service"

    def test_then_the_salon_default(self):
        assert select_rule(self.rules(), "shuhail", "colour", T0).id == "default"

    def test_with_no_rule_at_all_nothing_is_earned_and_no_rate_is_invented(self):
        assert select_rule([], "hafis", "haircut", T0) is None
        assert earned_amount(None, 50_000) == 0

    def test_a_rule_for_another_staff_or_service_never_applies(self):
        only_other = [rule(staff="shuhail", service="beard", bps=5000)]
        assert select_rule(only_other, "hafis", "haircut", T0) is None

    @pytest.mark.parametrize("order", list(product(range(4), repeat=1)))
    def test_the_order_the_rules_arrive_in_never_matters(self, order):
        rules = self.rules()
        assert select_rule(list(reversed(rules)), "hafis", "haircut", T0).id == "staff+service"
        assert select_rule(rules[2:] + rules[:2], "hafis", "haircut", T0).id == "staff+service"


class TestVersionsAndDates:
    def test_a_rule_that_starts_later_does_not_apply_yet(self):
        future = [rule(staff="hafis", bps=2000, since=T0 + timedelta(days=1))]
        assert select_rule(future, "hafis", "haircut", T0) is None
        assert select_rule(future, "hafis", "haircut", T0 + timedelta(days=1)).staff_id == "hafis"

    def test_within_one_scope_the_latest_effective_rule_wins(self):
        rules = [
            rule(staff="hafis", bps=1000, since=T0 - timedelta(days=30), version=1, rid="old"),
            rule(staff="hafis", bps=1500, since=T0 - timedelta(days=1), version=2, rid="new"),
        ]
        assert select_rule(rules, "hafis", "haircut", T0).id == "new"

    def test_a_past_service_keeps_the_rule_that_was_in_force_then(self):
        rules = [
            rule(staff="hafis", bps=1000, since=T0 - timedelta(days=30), version=1, rid="old"),
            rule(staff="hafis", bps=1500, since=T0, version=2, rid="new"),
        ]
        assert select_rule(rules, "hafis", "haircut", T0 - timedelta(hours=1)).id == "old"

    def test_a_more_specific_old_rule_still_beats_a_newer_general_one(self):
        rules = [
            rule(staff="hafis", service="haircut", bps=1000, since=T0 - timedelta(days=90), rid="specific"),
            rule(bps=9000, since=T0 - timedelta(days=1), version=5, rid="default"),
        ]
        assert select_rule(rules, "hafis", "haircut", T0).id == "specific"


class TestEarnedAmount:
    @pytest.mark.parametrize(
        ("value", "bps", "expected"),
        [(50_000, 2000, 10_000), (30_000, 1000, 3_000), (10_001, 5000, 5_001), (10_000, 3333, 3_333), (1, 5000, 1), (0, 5000, 0), (7, 3333, 2)],
    )
    def test_a_percentage_rounds_half_up_to_whole_paise(self, value, bps, expected):
        assert earned_amount(rule(staff="x", bps=bps), value) == expected

    def test_a_fixed_amount_is_the_same_for_every_service(self):
        assert earned_amount(rule(staff="x", kind="FIXED_PER_SERVICE", fixed=5_000), 30_000) == 5_000
        assert earned_amount(rule(staff="x", kind="FIXED_PER_SERVICE", fixed=5_000), 90_000) == 5_000

    def test_a_fixed_amount_never_exceeds_what_the_service_cost(self):
        assert earned_amount(rule(staff="x", kind="FIXED_PER_SERVICE", fixed=50_000), 30_000) == 30_000

    def test_the_none_type_earns_nothing(self):
        assert earned_amount(rule(staff="x", kind="NONE"), 30_000) == 0

    def test_a_hundred_percent_earns_the_whole_service_and_never_more(self):
        assert earned_amount(rule(staff="x", bps=10_000), 12_345) == 12_345


class TestReversalAfterRefund:
    """A refund after completion reverses the matching share of the earning, append-only."""

    def test_nothing_refunded_means_nothing_reversed(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=0, already_reversed=0) == 0

    def test_a_full_refund_reverses_the_whole_earning(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=30_000, already_reversed=0) == 6_000

    def test_a_half_refund_reverses_half(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=15_000, already_reversed=0) == 3_000

    def test_a_second_refund_reverses_only_the_new_part(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=30_000, already_reversed=3_000) == 3_000

    def test_the_same_refund_seen_twice_reverses_nothing_more(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=15_000, already_reversed=3_000) == 0

    def test_a_refund_above_the_service_value_never_reverses_more_than_was_earned(self):
        assert reversal_due(earned=6_000, service_value=30_000, refunded_to_line=99_000, already_reversed=0) == 6_000

    def test_a_service_that_earned_nothing_reverses_nothing(self):
        assert reversal_due(earned=0, service_value=30_000, refunded_to_line=30_000, already_reversed=0) == 0

    def test_reversals_never_drift_or_exceed_the_earning(self):
        """However a refund arrives in pieces, the total reversed ends exactly where one big refund would."""
        earned, value = 3_333, 10_000
        for pieces in (1, 2, 3, 7, 13, 100):
            refunded = reversed_total = 0
            step = value // pieces
            while refunded < value:
                refunded = min(value, refunded + max(step, 1))
                due = reversal_due(earned=earned, service_value=value, refunded_to_line=refunded, already_reversed=reversed_total)
                assert due >= 0
                reversed_total += due
                assert reversed_total <= earned
            assert reversed_total == earned


class TestSplitRefundAcrossLines:
    """A refund belongs to a payment; each service line gets a share that adds up to the refund exactly."""

    def test_proportional_to_the_line_values(self):
        assert split_refund_across_lines(7_000, [30_000, 20_000, 20_000]) == [3_000, 2_000, 2_000]

    def test_the_shares_always_add_up_to_the_refund(self):
        for refund, values in ((2, [1, 1, 1]), (100, [33, 33, 34]), (7, [1, 2, 4]), (99_999, [33_333, 33_333, 33_334]), (1, [5, 5]), (5, [3, 3, 3])):
            shares = split_refund_across_lines(refund, values)
            assert sum(shares) == refund and all(share >= 0 for share in shares)

    def test_no_line_gets_more_than_it_cost(self):
        assert split_refund_across_lines(70_000, [30_000, 20_000, 20_000]) == [30_000, 20_000, 20_000]

    def test_a_refund_larger_than_the_total_is_capped_at_the_total(self):
        assert sum(split_refund_across_lines(10**9, [30_000, 20_000])) == 50_000

    def test_a_zero_refund_or_no_lines_gives_zero_shares(self):
        assert split_refund_across_lines(0, [10, 20]) == [0, 0]
        assert split_refund_across_lines(500, []) == []
        assert split_refund_across_lines(500, [0, 0]) == [0, 0]
