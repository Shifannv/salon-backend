"""Payment gateway port.

An ABC (not a Protocol) because there are real adapters. ``PaymentGateway`` collects and
refunds customer money. It is deliberately a *separate* port from any future subscription
adapter: the two have disjoint methods, and ``subscription_events`` stays the subscription
domain log while ``payment_webhook_events`` is only the shared provider intake.

Amounts are :class:`~app.domain.value_objects.money.Money` (major units, 2 dp). Converting
to a provider's minor unit is an adapter concern.

Model (A) = provider-side split settlement to a linked account per salon.
Model (B) = customer pays the salon's own provider account directly. Only model (A)
uses ``register_settlement_account``/``get_settlement_account``; a model (B) adapter
rejects them with ``PaymentCapabilityError``.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.exceptions import PaymentCapabilityError
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    OnboardingStatus,
    PaymentEventType,
    PaymentInstrument,
    RefundStatus,
    SettlementModel,
    WebhookDomain,
)
from app.domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """What a client app needs to start checkout. Never contains secrets."""

    enabled: bool
    provider: str | None = None
    public_key: str | None = None
    currency: str = "INR"
    settlement_model: SettlementModel | None = None


@dataclass(frozen=True, slots=True)
class PaymentIntentRequest:
    """Create one payable order for a booking."""

    intent_reference: str  # our idempotent reference; becomes the provider receipt
    booking_id: str
    salon_id: str
    amount: Money
    currency: str = "INR"
    description: str | None = None
    customer_id: str | None = None
    settlement_model: SettlementModel = SettlementModel.platform_collect
    # Provider linked-account reference of the payee salon (model A only).
    settlement_account_ref: str | None = None
    # Platform commission snapshotted for THIS payment (never provider fees or taxes). The
    # payee share is ``amount - platform_fee``.
    platform_fee: Money = field(default_factory=lambda: Money(0))
    # Payer contact details some providers insist on. Excluded from repr so they never
    # reach logs.
    customer_phone: str | None = field(default=None, repr=False)
    customer_email: str | None = field(default=None, repr=False)
    customer_name: str | None = field(default=None, repr=False)
    # Lifetime of the order; the adapter turns it into the provider's expiry field.
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentIntent:
    """The provider's order, plus the opaque payload the client SDK needs."""

    provider: str
    order_ref: str
    intent_reference: str
    amount: Money
    currency: str
    client_payload: Mapping[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentCallback:
    """The client-side success callback, verified server-side before it is trusted."""

    order_ref: str
    payment_ref: str
    signature: str


@dataclass(frozen=True, slots=True)
class ProviderPayment:
    """A payment as the provider currently reports it."""

    provider: str
    payment_ref: str
    order_ref: str | None
    status: LedgerStatus
    amount: Money
    currency: str
    instrument: PaymentInstrument | None = None
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class RefundRequest:
    """Refund part or all of a captured payment."""

    payment_ref: str
    amount: Money
    # Fixed per payment/refund so a retry can never refund twice at the provider.
    idempotency_key: str
    reason: str | None = None
    # Providers that refund by order need it; ``refund_ref`` is OUR deterministic refund id
    # (persisted before the call) for providers that take a caller-chosen one.
    order_ref: str | None = None
    refund_ref: str | None = None
    # Split-settlement providers: the payee and the commission share being reversed.
    settlement_account_ref: str | None = None
    commission_reversal: Money = field(default_factory=lambda: Money(0))


@dataclass(frozen=True, slots=True)
class RefundResult:
    """The provider's view of a refund."""

    provider: str
    refund_ref: str
    status: RefundStatus
    amount: Money
    payment_ref: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """A provider webhook, normalised. Contains identifiers and amounts, never PII."""

    provider: str
    event_id: str
    event_type: PaymentEventType
    raw_type: str
    payment_ref: str | None = None
    order_ref: str | None = None
    refund_ref: str | None = None
    amount: Money | None = None
    currency: str | None = None
    instrument: PaymentInstrument | None = None
    failure_code: str | None = None
    account_ref: str | None = None
    onboarding_status: OnboardingStatus | None = None
    # Settlement events: provider status normalised to initiated|success|failed|reversed.
    settlement_status: str | None = None
    domain: WebhookDomain = WebhookDomain.payment


@dataclass(frozen=True, slots=True)
class SettlementAccountRequest:
    """Register a salon as a payee (model A).

    Every field except ``salon_id``/``vendor_ref`` is sensitive KYC or bank data: it is used
    once in memory for the provider call, never persisted by this backend, and hidden from
    ``repr`` so it can not reach a log line.
    """

    salon_id: str
    legal_name: str = field(repr=False)
    # Our deterministic payee id, persisted (status 'pending') BEFORE the provider call.
    vendor_ref: str | None = None
    email: str | None = field(default=None, repr=False)
    phone: str | None = field(default=None, repr=False)
    account_type: str | None = field(default=None, repr=False)
    business_type: str | None = field(default=None, repr=False)
    pan: str | None = field(default=None, repr=False)
    bank_account_number: str | None = field(default=None, repr=False)
    ifsc: str | None = field(default=None, repr=False)
    upi_id: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class SettlementAccount:
    """A salon's payee account at the provider."""

    provider: str
    account_ref: str
    onboarding_status: OnboardingStatus
    requirements: tuple[str, ...] = ()


class PaymentGateway(ABC):
    """Collect, verify and refund customer payments."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable lowercase provider identifier stored on ledger rows."""

    @abstractmethod
    def supports(self, capability: GatewayCapability) -> bool:
        """Whether this gateway can do ``capability``. Never raises."""

    @abstractmethod
    def client_config(self) -> ClientConfig:
        """Public checkout configuration for client apps."""

    @abstractmethod
    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent:
        """Create a provider order for ``request.amount``."""

    @abstractmethod
    def verify_payment_callback(self, callback: PaymentCallback) -> bool:
        """Constant-time check of the client callback signature."""

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Constant-time check over the RAW request bytes, before any parsing."""

    @abstractmethod
    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        """Normalise an already-verified webhook body."""

    @abstractmethod
    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None:
        """Fetch the provider's current view by payment or order reference.

        With ``order_ref`` the most advanced payment on that order is returned, or ``None``
        when nobody has attempted payment yet. Used for reconciliation after a lost webhook.
        """

    # ---- optional capabilities (safe defaults; adapters override what they can do) ----
    def deterministic_order_ref(self, intent_reference: str) -> str | None:
        """Provider order id derivable from our intent reference, or ``None``.

        A provider that lets the caller choose the order id gets it persisted with the ledger
        row BEFORE the create call, so a crash or timeout can be reconciled by that id.
        """

        return None

    def deterministic_refund_ref(self, refund_id: str) -> str | None:
        """Provider refund id derivable from our refund row id, or ``None``."""

        return None

    async def fetch_intent(self, order_ref: str, request: PaymentIntentRequest) -> PaymentIntent | None:
        """Look up an existing order. ``None`` = the provider confirms it does not exist.

        Raises ``PaymentCapabilityError`` when the adapter cannot look orders up (the caller
        then falls back to letting the unconfirmed intent expire).
        """

        raise PaymentCapabilityError("The payment provider cannot look up orders")

    async def fetch_refund(
        self, *, refund_ref: str, order_ref: str | None, payment_ref: str | None
    ) -> RefundResult | None:
        """Look up a refund by OUR refund id. Raises ``PaymentCapabilityError`` if unsupported."""

        raise PaymentCapabilityError("The payment provider cannot look up refunds")

    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundResult:
        """Refund a captured payment, idempotently by ``request.idempotency_key``."""

    @abstractmethod
    async def register_settlement_account(
        self, request: SettlementAccountRequest
    ) -> SettlementAccount:
        """Create the salon's payee account (model A only)."""

    @abstractmethod
    async def get_settlement_account(self, account_ref: str) -> SettlementAccount:
        """Fetch the salon's payee account state (model A only)."""
