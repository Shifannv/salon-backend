"""Platform commission arithmetic (pure, Decimal only, no floats).

The commission is a *snapshot*: it is computed once when a payment intent is created, stored on
the ledger row together with the rate, base and policy version that produced it, and never
recomputed. A refund reverses the snapshot proportionally. Provider processing fees and taxes
are a different quantity and never enter this module.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities.payment import CommissionBase

_CENT = Decimal("0.01")
_HUNDRED = Decimal(100)


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, ROUND_HALF_UP)


def compute_commission(
    *,
    rate_percent: Decimal,
    base: CommissionBase | str,
    payment_amount: Decimal,
    booking_total: Decimal,
    already_allocated: Decimal,
) -> Decimal:
    """Commission to snapshot on one payment of ``payment_amount``.

    ``online_amount``: ``rate`` of this payment.
    ``booking_total``: ``rate`` of the whole booking price, allocated across the booking's online
    payments so the sum can never exceed it (``already_allocated`` is the net commission already
    snapshotted on earlier online payments). Cash received at the salon carries no commission
    because the platform never holds that money.
    The result never exceeds the payment itself, so the payee share is never negative.
    """

    if rate_percent < 0 or rate_percent > _HUNDRED:
        raise ValueError("commission rate must be between 0 and 100")
    base = CommissionBase(base)
    if base is CommissionBase.online_amount:
        raw = _money(payment_amount * rate_percent / _HUNDRED)
    else:
        whole = _money(booking_total * rate_percent / _HUNDRED)
        raw = max(whole - already_allocated, Decimal(0))
    return min(raw, _money(payment_amount))


def commission_reversal(
    *,
    commission: Decimal,
    payment_amount: Decimal,
    refund_amount: Decimal,
    already_reversed: Decimal,
    already_refunded: Decimal,
) -> Decimal:
    """Share of the snapshotted ``commission`` returned by refunding ``refund_amount``.

    Proportional to the refunded part of the payment. The refund that exhausts the payment
    reverses exactly what is left, so rounding never leaves a residue.
    """

    if payment_amount <= 0 or commission <= 0:
        return Decimal("0.00")
    outstanding = commission - already_reversed
    if outstanding <= 0:
        return Decimal("0.00")
    if already_refunded + refund_amount >= payment_amount:
        return _money(outstanding)
    return min(_money(commission * refund_amount / payment_amount), _money(outstanding))
