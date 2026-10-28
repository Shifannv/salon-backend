"""Subscription billing provider port.

Deliberately separate from :class:`~app.application.ports.payment_gateway.PaymentGateway`:
booking payments split money to salons; a subscription is the platform's own revenue and is
never split. The two ports share only the webhook *intake* table, never methods or secrets.

Initial mode is ONE-TIME ORDERS for ONE paid period with MANUAL renewal. ``supports_recurring``
is the seam for provider-managed recurring billing (AutoPay) later: it is ``False`` for every
adapter today and nothing calls a recurring method. Never enable both for one period.

Amounts are :class:`~app.domain.value_objects.money.Money` (rupees, 2 dp, Decimal). Integer
minor units exist only inside an adapter.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.value_objects.money import Money


class ProviderOrderState(StrEnum):
    created = "created"
    attempted = "attempted"  # a payment was tried; the order is still open
    paid = "paid"


class ProviderPaymentState(StrEnum):
    pending = "pending"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


class SubscriptionEventKind(StrEnum):
    """Provider events normalised to the few that change billing state."""

    payment_captured = "payment_captured"
    order_paid = "order_paid"
    payment_failed = "payment_failed"
    refund_processed = "refund_processed"
    refund_failed = "refund_failed"
    ignored = "ignored"


@dataclass(frozen=True, slots=True)
class SubscriptionOrderRequest:
    """Create one payable order for one billing period."""

    receipt: str  # OUR deterministic id, persisted BEFORE the call; becomes the provider receipt
    billing_record_id: str
    salon_id: str
    plan_id: str
    amount: Money
    currency: str = "INR"
    description: str | None = None
    customer_id: str | None = None
    customer_phone: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    return_url: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderOrder:
    provider: str
    order_ref: str
    receipt: str | None
    amount: Money
    currency: str
    state: ProviderOrderState
    amount_paid: Money = field(default_factory=lambda: Money(0))
    # Opaque, public-only payload for the WEB checkout widget (never a secret). The adapter
    # owns its shape and its minor-unit conversion.
    client_payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderPaymentObservation:
    """A payment as the provider currently reports it."""

    provider: str
    payment_ref: str
    order_ref: str | None
    state: ProviderPaymentState
    amount: Money
    currency: str
    amount_refunded: Money = field(default_factory=lambda: Money(0))
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderRefund:
    provider: str
    refund_ref: str
    payment_ref: str
    amount: Money
    status: str  # 'created' | 'processed' | 'failed'


@dataclass(frozen=True, slots=True)
class ProviderSubscriptionEvent:
    """A verified webhook, normalised. Not proof of payment by itself."""

    provider: str
    event_id: str
    kind: SubscriptionEventKind
    raw_type: str
    order_ref: str | None = None
    payment_ref: str | None = None
    refund_ref: str | None = None
    amount: Money | None = None
    currency: str | None = None
    failure_code: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SubscriptionClientConfig:
    """What a WEB checkout needs. Never contains a secret."""

    provider: str
    public_key: str | None


class SubscriptionProvider(ABC):
    """Collects (and refunds) platform subscription revenue."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    def supports_recurring(self) -> bool:
        """Provider-managed recurring billing. Not built; reserved so the port can grow."""

        return False

    @abstractmethod
    def client_config(self) -> SubscriptionClientConfig: ...

    @abstractmethod
    async def create_period_order(self, request: SubscriptionOrderRequest) -> ProviderOrder:
        """Create the order. An unknown outcome raises ``PaymentOutcomeUnknownError``."""

    @abstractmethod
    async def fetch_order(self, order_ref: str) -> ProviderOrder | None: ...

    @abstractmethod
    async def find_order_by_receipt(self, receipt: str) -> ProviderOrder | None:
        """Recover an order after a timeout, by OUR receipt."""

    @abstractmethod
    async def fetch_order_payments(self, order_ref: str) -> list[ProviderPaymentObservation]: ...

    @abstractmethod
    async def fetch_payment(self, payment_ref: str) -> ProviderPaymentObservation | None: ...

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool: ...

    @abstractmethod
    def parse_event(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> ProviderSubscriptionEvent:
        """Normalise a body that has ALREADY been signature-verified. ``ValueError`` if garbled."""

    @abstractmethod
    def verify_client_callback(self, order_ref: str, payment_ref: str, signature: str) -> bool:
        """Client-side checkout result. A HINT only: never proof of payment."""

    @abstractmethod
    async def refund(
        self, payment_ref: str, amount: Money, idempotency_key: str, reason: str | None = None
    ) -> ProviderRefund: ...
