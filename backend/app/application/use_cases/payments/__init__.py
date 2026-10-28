"""Booking payment use cases: intents, confirmation, refunds, earnings, webhooks.

Authorization lives here. Amounts are read from the booking (computed in SQL by
``create_booking``); nothing in this package accepts an amount from a client except an
optional *partial refund* amount, which is bounded by the captured payment.

Crash safety rule used throughout: persist the operation identity and COMMIT before every
outbound provider call, never hold a transaction or row lock across the call, and on an
unknown outcome reconcile by the persisted identity instead of retrying blindly.

The implementation is split by concern; this package re-exports the names that used to
live in the single ``payments`` module.
"""

from app.application.use_cases.payments.booking import BookingPaymentUseCases
from app.application.use_cases.payments.ledger import (
    SettlementRegistrationDetails,
    apply_provider_payment,
    event_to_json,
    observation_status,
)
from app.application.use_cases.payments.refunds import RefundMixin
from app.application.use_cases.payments.settlement_accounts import SettlementAccountMixin
from app.application.use_cases.payments.webhooks import PaymentWebhookUseCases

__all__ = [
    "BookingPaymentUseCases",
    "PaymentWebhookUseCases",
    "RefundMixin",
    "SettlementAccountMixin",
    "SettlementRegistrationDetails",
    "apply_provider_payment",
    "event_to_json",
    "observation_status",
]
