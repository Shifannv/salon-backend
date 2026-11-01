"""Owner wallet rules: what is available, which payout days are allowed."""

from datetime import date, timedelta

import pytest

from app.domain.services.wallet import (
    MAX_PAYOUT_DAYS_AHEAD,
    PayoutDateProblem,
    available_paise,
    can_cancel,
    check_payout_day,
    net_online_paise,
)

TODAY = date(2026, 11, 1)


class TestNetOnline:
    def test_collected_less_commission_and_refunds_plus_reversed(self):
        assert net_online_paise(collected=100_000, commission=10_000, refunded=20_000, commission_reversed=2_000) == 72_000

    def test_never_negative(self):
        assert net_online_paise(collected=1_000, commission=0, refunded=5_000, commission_reversed=0) == 0


class TestAvailable:
    def test_requested_and_paid_money_is_held_back(self):
        assert available_paise(net_online=90_000, requested=20_000, paid=30_000) == 40_000

    def test_floors_at_zero_after_a_refund_following_a_payout(self):
        assert available_paise(net_online=10_000, requested=0, paid=30_000) == 0

    def test_a_rejected_request_is_simply_not_counted(self):
        assert available_paise(net_online=50_000, requested=0, paid=0) == 50_000


class TestPayoutDay:
    def test_today_and_the_far_edge_are_allowed(self):
        check_payout_day(TODAY, TODAY)
        check_payout_day(TODAY + timedelta(days=MAX_PAYOUT_DAYS_AHEAD), TODAY)

    def test_past_is_refused(self):
        with pytest.raises(PayoutDateProblem):
            check_payout_day(TODAY - timedelta(days=1), TODAY)

    def test_too_far_ahead_is_refused(self):
        with pytest.raises(PayoutDateProblem):
            check_payout_day(TODAY + timedelta(days=MAX_PAYOUT_DAYS_AHEAD + 1), TODAY)


@pytest.mark.parametrize(("status", "expected"), [("requested", True), ("paid", False), ("rejected", False), ("cancelled", False)])
def test_only_a_waiting_request_can_be_cancelled(status, expected):
    assert can_cancel(status) is expected
