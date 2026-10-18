"""Small provider ports composed by the existing PaymentGateway contract.

Payouts and fee reconciliation are separate capabilities: implementing payment
collection does not prove settlement, schedules, fee tariffs or payout support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING

from app.core.exceptions import PaymentCapabilityError
from app.domain.entities.provider_finance import (
    PayoutRequest,
    ProviderFeeReconciliation,
    ProviderPayout,
)

if TYPE_CHECKING:
    from app.application.ports.payment_gateway import (
        ClientConfig,
        PaymentCallback,
        PaymentEvent,
        PaymentIntent,
        PaymentIntentRequest,
        ProviderPayment,
        RefundRequest,
        RefundResult,
    )
    from app.domain.entities.payment import GatewayCapability


class PaymentProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def supports(self, capability: GatewayCapability) -> bool: ...

    @abstractmethod
    def client_config(self) -> ClientConfig: ...

    @abstractmethod
    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent: ...

    @abstractmethod
    def verify_payment_callback(self, callback: PaymentCallback) -> bool: ...

    @abstractmethod
    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None: ...

    def deterministic_order_ref(self, intent_reference: str) -> str | None:
        """Reference persistable before submission, if supported."""
        return None

    async def fetch_intent(self, order_ref: str, request: PaymentIntentRequest) -> PaymentIntent | None:
        raise PaymentCapabilityError("The payment provider cannot look up orders")


class RefundProvider(ABC):
    @abstractmethod
    async def refund(self, request: RefundRequest) -> RefundResult:
        """Submit an idempotent refund; acceptance is not final processing."""

    def deterministic_refund_ref(self, refund_id: str) -> str | None:
        """Persist before submission where supported; None does not prove nonmovement."""
        return None

    async def fetch_refund(
        self, *, refund_ref: str, order_ref: str | None, payment_ref: str | None
    ) -> RefundResult | None:
        raise PaymentCapabilityError("The payment provider cannot look up refunds")


class WebhookVerifier(ABC):
    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        """Authenticate exact raw bytes before parsing or storing effects."""

    @abstractmethod
    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        """Normalize an authenticated payload, without applying ledger effects."""


class PayoutProvider(ABC):
    @abstractmethod
    async def create_payout(self, request: PayoutRequest) -> ProviderPayout:
        """Execute a previously authorized/reserved instruction, never choose eligibility."""

    @abstractmethod
    async def fetch_payout(
        self, payout_reference: str | None = None, *, idempotency_key: str | None = None
    ) -> ProviderPayout | None:
        """Reconcile by persisted operation key even if submission returned no reference."""


class ProviderFeeReconciler(ABC):
    @abstractmethod
    async def reconcile_fees(self, reference: str) -> ProviderFeeReconciliation:
        """Return evidence components; missing fees stay unknown, never assumed zero."""
