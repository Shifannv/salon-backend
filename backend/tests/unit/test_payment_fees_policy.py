"""Pure money rules of the marketplace model: gateway fee, cancellation deduction, payee share."""

from decimal import Decimal

import pytest

from app.core.config import Settings
from app.domain.services.commission import commission_reversal, compute_commission
from app.domain.services.payment_fees import (
    cancellation_deduction,
    gateway_fee_amount,
    payee_share,
)

D = Decimal


def test_gateway_fee_is_percent_rounded_half_up_to_paise():
    assert gateway_fee_amount(D("250.00"), D("2")) == D("5.00")
    assert gateway_fee_amount(D("99.75"), D("2")) == D("2.00")  # 1.995 -> 2.00 (half up)
    assert gateway_fee_amount(D("10.25"), D("2")) == D("0.21")  # 0.205 -> 0.21


def test_gateway_fee_zero_rate_and_never_above_amount():
    assert gateway_fee_amount(D("250.00"), D("0")) == D("0.00")
    assert gateway_fee_amount(D("1.00"), D("100")) == D("1.00")


def test_gateway_fee_rejects_negative_inputs():
    with pytest.raises(ValueError):
        gateway_fee_amount(D("-1"), D("2"))
    with pytest.raises(ValueError):
        gateway_fee_amount(D("10"), D("-2"))


def test_payee_share_subtracts_commission_and_gateway_fee():
    assert payee_share(D("250.00"), D("0.00"), D("5.00")) == D("245.00")
    assert payee_share(D("250.00"), D("25.00"), D("5.00")) == D("220.00")


def test_payee_share_with_zero_commission_and_zero_fee_is_the_whole_amount():
    assert payee_share(D("250.00"), D("0.00"), D("0.00")) == D("250.00")


def test_payee_share_never_negative():
    assert payee_share(D("10.00"), D("9.00"), D("5.00")) == D("0.00")


def test_percent_deduction_default_rule():
    assert cancellation_deduction(D("250.00"), "percent", D("10.00")) == D("25.00")
    assert cancellation_deduction(D("99.95"), "percent", D("10.00")) == D("10.00")  # 9.995 half up


def test_flat_deduction():
    assert cancellation_deduction(D("250.00"), "flat", D("10.00")) == D("10.00")


def test_deduction_never_exceeds_amount_paid_and_never_negative():
    assert cancellation_deduction(D("6.00"), "flat", D("10.00")) == D("6.00")
    assert cancellation_deduction(D("50.00"), "percent", D("100")) == D("50.00")
    assert cancellation_deduction(D("0.00"), "flat", D("10.00")) == D("0.00")
    assert cancellation_deduction(D("100.00"), "flat", D("0")) == D("0.00")


def test_unknown_deduction_type_is_rejected():
    with pytest.raises(ValueError):
        cancellation_deduction(D("100"), "half", D("1"))


def test_zero_platform_commission_is_valid_in_the_commission_math():
    for base in ("online_amount", "booking_total"):
        assert compute_commission(
            rate_percent=D("0"), base=base, payment_amount=D("250.00"),
            booking_total=D("250.00"), already_allocated=D("0.00"),
        ) == D("0.00")
    assert commission_reversal(
        commission=D("0.00"), payment_amount=D("250.00"), refund_amount=D("225.00"),
        already_reversed=D("0.00"), already_refunded=D("0.00"),
    ) == D("0.00")


def _settings(**kw):
    return Settings(_env_file=None, environment="test", **kw)


def test_zero_platform_fee_percent_is_a_valid_boot_configuration():
    s = _settings(
        payment_provider="cashfree", cashfree_client_id="c", cashfree_client_secret="s",
        cashfree_easy_split_enabled=True, payment_platform_fee_percent="0",
        payment_commission_base="online_amount",
    )
    assert s.payment_platform_fee_percent == D("0")


def test_new_policy_defaults():
    s = _settings()
    assert s.payment_gateway_fee_percent == D("2.0")
    assert s.cancellation_deduction_type == "percent"
    assert s.cancellation_deduction_value == D("10.00")


def test_flat_and_percent_rules_are_both_accepted_and_percent_is_capped():
    assert _settings(cancellation_deduction_type="flat", cancellation_deduction_value="10").cancellation_deduction_type == "flat"
    with pytest.raises(ValueError):
        _settings(cancellation_deduction_type="percent", cancellation_deduction_value="101")
    with pytest.raises(ValueError):
        _settings(cancellation_deduction_type="half")
    with pytest.raises(ValueError):
        _settings(cancellation_deduction_value="-1")
    with pytest.raises(ValueError):
        _settings(payment_gateway_fee_percent="-0.1")
