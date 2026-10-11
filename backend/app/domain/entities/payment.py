"""Payment domain vocabulary (pure Python, provider-neutral).

The ledger (``booking_payments``) records what happened to money. Booking-level
``payment_status`` stays the two-valued ``unpaid|paid`` cache; richer state is derived
with :func:`derive_payment_state`.
"""

from decimal import Decimal
from enum import StrEnum


class PaymentChannel(StrEnum):
    """How money reached the salon."""

    manual = "manual"  # receipt recorded by salon staff (cash / paid elsewhere)
    gateway = "gateway"  # collected through a payment provider


class PaymentPurpose(StrEnum):
    """What a ledger row pays for."""

    deposit = "deposit"
    balance = "balance"
    full = "full"


class SettlementModel(StrEnum):
    """Where the money ended up."""

    offline = "offline"
    platform_collect = "platform_collect"  # provider-side split settlement (escrow + payee split)
    direct_to_salon = "direct_to_salon"  # customer pays the salon's own provider account


class PaymentPreference(StrEnum):
    """Customer's choice at booking time."""

    pay_at_salon = "pay_at_salon"
    pay_advance = "pay_advance"
    pay_full = "pay_full"


class ManualMethod(StrEnum):
    """Mirrors the existing ``payment_method`` enum; deliberately not widened."""

    cash = "cash"
    online = "online"


class PaymentInstrument(StrEnum):
    """The real instrument, known only from a gateway row."""

    upi = "upi"
    card = "card"
    netbanking = "netbanking"
    wallet = "wallet"
    other = "other"


class LedgerStatus(StrEnum):
    """Lifecycle of one ledger row."""

    created = "created"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"
    partially_refunded = "partially_refunded"
    refunded = "refunded"


class RefundStatus(StrEnum):
    """Lifecycle of one refund."""

    created = "created"
    processed = "processed"
    failed = "failed"


class PaymentState(StrEnum):
    """Derived booking-level state exposed to both apps."""

    unpaid = "unpaid"
    partially_paid = "partially_paid"
    paid = "paid"
    refunded = "refunded"


class WebhookStatus(StrEnum):
    """Processing state of a stored provider event."""

    received = "received"
    processing = "processing"
    processed = "processed"
    ignored = "ignored"
    failed = "failed"


class OnboardingStatus(StrEnum):
    """Salon payee (linked account) lifecycle, model (A) only."""

    not_started = "not_started"
    pending = "pending"
    needs_action = "needs_action"
    active = "active"
    rejected = "rejected"
    suspended = "suspended"


class GatewayCapability(StrEnum):
    """What a configured gateway can do; asked via ``PaymentGateway.supports``."""

    online_collection = "online_collection"
    refunds = "refunds"
    split_settlement = "split_settlement"
    linked_accounts = "linked_accounts"


class PaymentEventType(StrEnum):
    """Provider events normalised to the few that change ledger state."""

    payment_authorized = "payment_authorized"
    payment_captured = "payment_captured"
    payment_failed = "payment_failed"
    refund_processed = "refund_processed"
    refund_failed = "refund_failed"
    account_updated = "account_updated"
    ignored = "ignored"


SETTLED_STATUSES = frozenset(
    {LedgerStatus.captured, LedgerStatus.partially_refunded, LedgerStatus.refunded}
)
OPEN_STATUSES = frozenset({LedgerStatus.created, LedgerStatus.authorized})
TERMINAL_FAILURE_STATUSES = frozenset(
    {LedgerStatus.failed, LedgerStatus.cancelled, LedgerStatus.expired}
)

# Out-of-order delivery guard. An event may only move a row to a status of strictly
# higher rank; lower-rank (stale) events are ignored. A late capture on a row we already
# expired/failed/cancelled is deliberately allowed: real money moved.
_STATUS_RANK = {
    LedgerStatus.created: 0,
    LedgerStatus.authorized: 1,
    LedgerStatus.failed: 1,
    LedgerStatus.cancelled: 1,
    LedgerStatus.expired: 1,
    LedgerStatus.captured: 2,
    LedgerStatus.partially_refunded: 3,
    LedgerStatus.refunded: 4,
}


def status_rank(status: LedgerStatus | str) -> int:
    """Return the monotonic rank of a ledger status."""

    return _STATUS_RANK[LedgerStatus(status)]


def is_forward_transition(current: LedgerStatus | str, new: LedgerStatus | str) -> bool:
    """True when ``new`` is a strictly later state than ``current``."""

    return status_rank(new) > status_rank(current)


def derive_payment_state(
    payment_status: str, paid_amount: Decimal, refunded_amount: Decimal
) -> PaymentState:
    """Derive the booking-level state from the cached columns."""

    net = Decimal(paid_amount) - Decimal(refunded_amount)
    if Decimal(refunded_amount) > 0 and net <= 0:
        return PaymentState.refunded
    if payment_status == "paid":
        return PaymentState.paid
    if net > 0:
        return PaymentState.partially_paid
    return PaymentState.unpaid
