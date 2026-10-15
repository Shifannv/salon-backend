"""Marketplace money rules (pure, Decimal only, no floats).

* The customer never pays a platform or convenience fee.
* The SALON bears the payment gateway fee: it is snapshotted per payment and deducted from the
  payee (Easy Split) share. Platform commission is separate and is 0 in this model.
* A customer-initiated cancellation of a paid-online booking keeps a configurable deduction;
  salon-initiated cancellations never deduct.
"""

from decimal import Decimal

from app.domain.value_objects.money import round_money

_HUNDRED = Decimal(100)
_ZERO = Decimal("0.00")


def gateway_fee_amount(amount: Decimal, percent: Decimal) -> Decimal:
    """Gateway fee on one payment: ``percent`` of ``amount``, half-up to paise, within [0, amount]."""

    amount, percent = Decimal(amount), Decimal(percent)
    if amount < 0 or percent < 0:
        raise ValueError("amount and percent must not be negative")
    return min(round_money(amount * percent / _HUNDRED), round_money(amount))


def payee_share(amount: Decimal, commission: Decimal, gateway_fee: Decimal) -> Decimal:
    """What the salon's linked account receives: amount - commission - gateway fee (floor 0).

    The platform keeps the remainder, which pays the provider's fee.
    """

    share = round_money(Decimal(amount)) - round_money(Decimal(commission)) - round_money(Decimal(gateway_fee))
    return max(share, _ZERO)


def cancellation_deduction(amount_paid: Decimal, rule_type: str, rule_value: Decimal) -> Decimal:
    """Amount kept when the customer cancels a paid-online booking.

    ``percent``: ``rule_value`` percent of the amount paid; ``flat``: ``rule_value`` rupees.
    Never negative and never above the amount paid.
    """

    paid, value = round_money(Decimal(amount_paid)), Decimal(rule_value)
    if rule_type == "percent":
        raw = round_money(paid * value / _HUNDRED)
    elif rule_type == "flat":
        raw = round_money(value)
    else:
        raise ValueError("cancellation deduction type must be 'percent' or 'flat'")
    return max(_ZERO, min(raw, paid))
