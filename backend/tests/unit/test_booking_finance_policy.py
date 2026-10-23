"""Approved U08 boundaries; these calculations do not execute refunds or payouts."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.domain.services.booking_finance_policy import (
    POLICY_VERSION,
    cancellation_quote,
    completed_service_allocation,
    service_change_quote,
    validate_customer_change,
    validate_no_show,
)

D = Decimal
NOW = datetime(2026, 10, 23, 10, tzinfo=UTC)


@pytest.mark.parametrize(("remaining", "penalty", "refund"), [
    (timedelta(hours=48), "20.00", "180.00"),
    (timedelta(hours=48, microseconds=-1), "10.00", "190.00"),
    (timedelta(hours=12), "10.00", "190.00"),
    (timedelta(hours=12, microseconds=-1), "70.00", "130.00"),
    (timedelta(hours=4, microseconds=1), "70.00", "130.00"),
    (timedelta(hours=4), "200.00", "0.00"),
    (timedelta(hours=-1), "200.00", "0.00"),
])
def test_cancellation_exact_boundaries(remaining, penalty, refund):
    quote = cancellation_quote(D("200"), NOW + remaining, NOW, D("0"))
    assert quote.penalty == D(penalty)
    assert quote.customer_refund == D(refund)
    assert quote.policy_version == POLICY_VERSION
    assert quote.penalty + quote.customer_refund == D("200")


@pytest.mark.parametrize("paid", ["0", "0.01", "12", "20"])
def test_early_fee_is_capped_at_payment(paid):
    quote = cancellation_quote(D(paid), NOW + timedelta(days=3), NOW, D("0"))
    assert quote.penalty == D(paid)
    assert quote.customer_refund == D("0")


def test_actual_provider_cost_never_reduces_promised_refund():
    start = NOW + timedelta(days=3)
    free = cancellation_quote(D("200"), start, NOW, D("0"))
    costly = cancellation_quote(D("200"), start, NOW, D("25"))
    assert free.customer_refund == costly.customer_refund == D("180")
    assert costly.salon_share == costly.platform_share == D("0")
    assert costly.platform_shortfall == D("5")


def test_retained_pool_rounding_conserves_every_paisa():
    quote = cancellation_quote(D("200"), NOW + timedelta(days=3), NOW, D("17.95"))
    assert quote.retained_pool == D("2.05")
    assert quote.platform_share == D("0.62")
    assert quote.salon_share == D("1.43")
    assert quote.platform_share + quote.salon_share == quote.retained_pool


def test_percentage_penalty_rounds_half_up():
    quote = cancellation_quote(D("10.10"), NOW + timedelta(hours=12), NOW, D("0"))
    assert quote.penalty == D("0.51")
    assert quote.customer_refund == D("9.59")


def test_owner_pre_check_in_cancellation_refunds_full_payment_and_absorbs_cost():
    quote = cancellation_quote(D("200"), NOW + timedelta(hours=1), NOW, D("8"), salon_caused=True)
    assert quote.customer_refund == D("200")
    assert quote.penalty == quote.salon_share == quote.platform_share == D("0")
    assert quote.platform_shortfall == D("8")


def test_financial_result_is_immutable():
    quote = cancellation_quote(D("200"), NOW, NOW, D("0"))
    with pytest.raises(FrozenInstanceError):
        quote.customer_refund = D("200")


@pytest.mark.parametrize("invalid", [D("-0.001"), D("NaN"), D("Infinity"), 2.5, True])
def test_invalid_money_is_rejected_before_rounding(invalid):
    with pytest.raises(ValueError):
        cancellation_quote(invalid, NOW, NOW, D("0"))
    with pytest.raises(ValueError):
        cancellation_quote(D("20"), NOW, NOW, invalid)


def test_aware_appointment_instants_are_required():
    with pytest.raises(ValueError):
        cancellation_quote(D("20"), NOW.replace(tzinfo=None), NOW, D("0"))


def test_cutoffs_use_elapsed_time_across_daylight_saving_change():
    zone = ZoneInfo("America/New_York")
    before = datetime(2026, 11, 1, 0, 30, tzinfo=zone)
    after = datetime(2026, 11, 1, 4, 30, tzinfo=zone)
    # The wall clock advances four hours, but the elapsed interval is five hours.
    quote = cancellation_quote(D("200"), after, before, D("0"))
    assert quote.customer_refund == D("130")


def test_completed_service_has_zero_platform_commission():
    result = completed_service_allocation(D("200"), D("8.25"))
    assert result.salon_share == D("191.75")
    assert result.platform_share == result.platform_shortfall == D("0")


def test_completed_service_cost_shortfall_is_not_negative_salon_money():
    result = completed_service_allocation(D("1"), D("2"))
    assert result.salon_share == D("0")
    assert result.platform_shortfall == D("1")


@pytest.mark.parametrize(("new_total", "captured", "obligation", "extra"), [
    ("150", "200", "200", "0"),
    ("200", "200", "200", "0"),
    ("250", "200", "250", "50"),
    ("180", "200", "200", "0"),
    ("0", "0", "0", "0"),
])
def test_prepaid_service_changes_keep_prior_payment_and_quote_only_extra(new_total, captured, obligation, extra):
    quote = service_change_quote(D(new_total), D(captured), payment_preference="pay_full")
    assert quote.service_total == D(new_total)
    assert quote.total_obligation == D(obligation)
    assert quote.additional_online_payment == D(extra)
    assert quote.pay_at_salon_due == quote.customer_refund == D("0")


@pytest.mark.parametrize("new_total", ["0", "150", "250"])
def test_unpaid_pay_at_salon_change_uses_new_lower_or_higher_price(new_total):
    quote = service_change_quote(D(new_total), D("0"), payment_preference="pay_at_salon")
    assert quote.total_obligation == quote.pay_at_salon_due == D(new_total)
    assert quote.additional_online_payment == quote.customer_refund == D("0")


def test_partial_or_manual_collected_money_is_not_treated_as_an_unpaid_change():
    with pytest.raises(ValueError, match="booking_change_payment_state_unsupported"):
        service_change_quote(D("150"), D("50"), payment_preference="pay_at_salon")
    with pytest.raises(ValueError, match="booking_change_payment_state_unsupported"):
        service_change_quote(D("150"), D("50"), payment_preference="pay_advance")


@pytest.mark.parametrize(("new_total", "captured"), [(D("NaN"), D("0")), (D("1"), D("-1"))])
def test_service_change_quote_rejects_invalid_money(new_total, captured):
    with pytest.raises(ValueError):
        service_change_quote(new_total, captured, payment_preference="pay_full")


@pytest.mark.parametrize("count", [0, 1])
def test_change_is_permitted_only_above_four_hours(count):
    validate_customer_change(NOW + timedelta(hours=4, microseconds=1), NOW, count)


@pytest.mark.parametrize("remaining", [timedelta(hours=4), timedelta(hours=3), timedelta(hours=-1)])
def test_change_blocks_at_exactly_four_hours_and_later(remaining):
    with pytest.raises(ValueError, match="booking_change_cutoff"):
        validate_customer_change(NOW + remaining, NOW, 0)


def test_third_committed_reschedule_is_blocked():
    with pytest.raises(ValueError, match="booking_change_limit"):
        validate_customer_change(NOW + timedelta(days=1), NOW, 2)


def test_service_only_change_does_not_consume_another_time_reschedule():
    validate_customer_change(NOW + timedelta(days=1), NOW, 2, changes_time=False)


@pytest.mark.parametrize("count", [-1, 1.5, True])
def test_invalid_reschedule_count_is_rejected(count):
    with pytest.raises(ValueError):
        validate_customer_change(NOW + timedelta(days=1), NOW, count)


def test_no_show_needs_full_ten_minute_grace_and_nonblank_reason():
    start = NOW - timedelta(minutes=10)
    assert validate_no_show(start, NOW, "  Customer did not arrive  ") == "Customer did not arrive"
    with pytest.raises(ValueError, match="no_show_grace_period"):
        validate_no_show(start + timedelta(microseconds=1), NOW, "Did not arrive")
    with pytest.raises(ValueError, match="no_show_reason_required"):
        validate_no_show(start, NOW, "  ")
