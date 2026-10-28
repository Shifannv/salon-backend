"""Deterministic, network-free provider for local/test dependency injection only.

The HMAC key below is public test material, not a credential. Fake events cannot
authenticate a real provider; the resolver only exposes them as provider ``fake``.
State is process-local and is never a substitute for database idempotency,
reservations, eligibility, accounting or erasure guarantees.
"""

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from app.application.ports.payment_gateway import (
    ClientConfig,
    PaymentCallback,
    PaymentEvent,
    PaymentGateway,
    PaymentIntent,
    PaymentIntentRequest,
    ProviderPayment,
    RefundRequest,
    RefundResult,
    SettlementAccount,
    SettlementAccountRequest,
)
from app.application.ports.payment_provider import PayoutProvider, ProviderFeeReconciler
from app.core.exceptions import (
    IdempotencyKeyReuseError,
    PaymentCapabilityError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
)
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    PaymentEventType,
    PaymentInstrument,
    RefundStatus,
)
from app.domain.entities.provider_finance import (
    EvidenceSource,
    PayoutRequest,
    PayoutStatus,
    ProviderFeeReconciliation,
    ProviderFees,
    ProviderPayout,
    require_positive_money,
)
from app.domain.value_objects.money import Money
from app.infrastructure.webhook_signing import header

_TEST_SIGNING_KEY = b"public-fake-provider-test-key-v1"
_REFERENCE = re.compile(r"fake_[a-z]+_[0-9a-f]{32}\Z")
_PAYMENT_EVENTS = {
    LedgerStatus.authorized: PaymentEventType.payment_authorized,
    LedgerStatus.captured: PaymentEventType.payment_captured,
    LedgerStatus.failed: PaymentEventType.payment_failed,
}
_SUPPORTED_EVENTS = frozenset(_PAYMENT_EVENTS.values()) | {
    PaymentEventType.refund_processed, PaymentEventType.refund_failed,
}


def synthetic_reference(kind: str, identity: str) -> str:
    """Stable test-only references; never resemble a real provider's namespace."""
    if not kind.isalpha() or not identity:
        raise ValueError("A reference kind and nonempty identity are required")
    digest = hashlib.sha256(f"fake:{kind}:{identity}".encode()).hexdigest()[:32]
    return f"fake_{kind}_{digest}"


def _require_reference(reference: str) -> None:
    if not isinstance(reference, str) or not _REFERENCE.fullmatch(reference):
        raise ValueError("Only synthetic fake-provider references are accepted")


def _encoded(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True, slots=True)
class MockWebhook:
    body: bytes = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)


class FakeProvider(PaymentGateway, PayoutProvider, ProviderFeeReconciler):
    def __init__(self) -> None:
        self._orders: dict[str, PaymentIntent] = {}
        self._payments: dict[str, ProviderPayment] = {}
        self._refunds: dict[str, RefundResult] = {}
        self._payouts: dict[str, ProviderPayout] = {}
        self._fees: dict[str, ProviderFeeReconciliation] = {}
        self._fingerprints: dict[tuple[str, str], bytes] = {}
        self._unknown_after_accept: set[str] = set()

    @property
    def provider_name(self) -> str:
        return "fake"

    def supports(self, capability: GatewayCapability) -> bool:
        return capability in {
            GatewayCapability.online_collection, GatewayCapability.refunds,
            GatewayCapability.server_status_refresh,
        }

    def client_config(self) -> ClientConfig:
        return ClientConfig(enabled=True, provider="fake")

    def deterministic_order_ref(self, intent_reference: str) -> str:
        return synthetic_reference("order", intent_reference)

    def deterministic_refund_ref(self, refund_id: str) -> str:
        return synthetic_reference("refund", refund_id)

    def _bind(self, operation: str, key: str, values: dict[str, Any]) -> None:
        if not key or len(key) > 200:
            raise ValueError("A bounded idempotency reference is required")
        fingerprint = _encoded(values)
        previous = self._fingerprints.get((operation, key))
        if previous is not None and previous != fingerprint:
            raise IdempotencyKeyReuseError("The operation reference was used for different data")
        self._fingerprints[(operation, key)] = fingerprint

    def simulate_timeout_after_accept(self, operation: str) -> None:
        """Next operation persists fake state then reports an uncertain outcome."""
        if operation not in {"payment", "refund", "payout"}:
            raise ValueError("Unsupported mock operation")
        self._unknown_after_accept.add(operation)

    def _maybe_timeout(self, operation: str) -> None:
        if operation in self._unknown_after_accept:
            self._unknown_after_accept.remove(operation)
            raise PaymentOutcomeUnknownError("Synthetic provider outcome needs reconciliation")

    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent:
        require_positive_money(request.amount)
        if request.currency != "INR":
            raise ValueError("Only INR is supported")
        # No PII is retained or hashed; binding covers the immutable financial instruction.
        self._bind("payment", request.intent_reference, {
            "booking": request.booking_id, "salon": request.salon_id,
            "amount": str(request.amount), "currency": request.currency,
            "platform_fee": str(request.platform_fee),
            "settlement_model": request.settlement_model.value,
            "destination": request.settlement_account_ref,
        })
        reference = self.deterministic_order_ref(request.intent_reference)
        if reference not in self._orders:
            self._orders[reference] = PaymentIntent(
                "fake", reference, request.intent_reference, request.amount, request.currency,
                {"mock": True, "payment_session_id": synthetic_reference("session", reference)},
                request.expires_at,
            )
        self._maybe_timeout("payment")
        return self._orders[reference]

    async def fetch_intent(
        self, order_ref: str, request: PaymentIntentRequest
    ) -> PaymentIntent | None:
        _require_reference(order_ref)
        intent = self._orders.get(order_ref)
        if intent is not None and (
            intent.intent_reference != request.intent_reference
            or intent.amount != request.amount or intent.currency != request.currency
        ):
            raise IdempotencyKeyReuseError("The order does not match the financial instruction")
        return intent

    def verify_payment_callback(self, callback: PaymentCallback) -> bool:
        # A mobile callback is never evidence of receipt, including in this mock.
        return False

    def simulate_payment(
        self, order_ref: str, status: LedgerStatus = LedgerStatus.captured
    ) -> ProviderPayment:
        if status not in _PAYMENT_EVENTS:
            raise ValueError("Unsupported simulated payment state")
        order = self._orders[order_ref]
        previous = self._payments.get(order_ref)
        if previous and previous.status == LedgerStatus.captured and status != LedgerStatus.captured:
            raise ValueError("A captured payment cannot regress")
        observed = ProviderPayment(
            "fake", synthetic_reference("payment", order_ref), order_ref, status,
            order.amount, order.currency, PaymentInstrument.upi,
        )
        self._payments[order_ref] = observed
        return observed

    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None:
        for value in (payment_ref, order_ref):
            if value is not None:
                _require_reference(value)
        if not payment_ref and not order_ref:
            raise ValueError("A payment or order reference is required")
        return next((p for p in self._payments.values()
                     if (not payment_ref or p.payment_ref == payment_ref)
                     and (not order_ref or p.order_ref == order_ref)), None)

    async def refund(self, request: RefundRequest) -> RefundResult:
        require_positive_money(request.amount)
        payment = await self.fetch_payment(payment_ref=request.payment_ref)
        if payment is None or payment.status != LedgerStatus.captured:
            raise PaymentProviderError("No captured mock payment exists")
        if request.order_ref is not None and request.order_ref != payment.order_ref:
            raise ValueError("Refund order does not match its payment")
        reference = request.refund_ref or self.deterministic_refund_ref(request.idempotency_key)
        _require_reference(reference)
        self._bind("refund", request.idempotency_key, {
            "payment": request.payment_ref, "amount": str(request.amount), "reference": reference,
        })
        existing = self._refunds.get(reference)
        if existing and (existing.payment_ref != request.payment_ref or existing.amount != request.amount):
            raise IdempotencyKeyReuseError("The refund reference was used for different data")
        if existing is None:
            reserved = sum(r.amount.amount for r in self._refunds.values()
                           if r.payment_ref == request.payment_ref and r.status != RefundStatus.failed)
            if reserved + request.amount.amount > payment.amount.amount:
                raise PaymentProviderError("Refund exceeds the captured mock amount")
            self._refunds[reference] = RefundResult(
                "fake", reference, RefundStatus.created, request.amount, request.payment_ref,
            )
        self._maybe_timeout("refund")
        return self._refunds[reference]

    async def fetch_refund(
        self, *, refund_ref: str, order_ref: str | None, payment_ref: str | None
    ) -> RefundResult | None:
        _require_reference(refund_ref)
        refund = self._refunds.get(refund_ref)
        if refund is None:
            return None
        payment = await self.fetch_payment(payment_ref=refund.payment_ref)
        if (payment_ref and refund.payment_ref != payment_ref) or (
            order_ref and (payment is None or payment.order_ref != order_ref)
        ):
            return None
        return refund

    def simulate_refund(self, refund_ref: str, status: RefundStatus) -> RefundResult:
        result = self._refunds[refund_ref]
        if status not in {RefundStatus.processed, RefundStatus.failed}:
            raise ValueError("Only terminal mock refund outcomes may be simulated")
        if result.status != RefundStatus.created and status != result.status:
            raise ValueError("A terminal mock refund cannot change outcome")
        self._refunds[refund_ref] = replace(result, status=status)
        return self._refunds[refund_ref]

    async def create_payout(self, request: PayoutRequest) -> ProviderPayout:
        _require_reference(request.destination_reference)
        self._bind("payout", request.idempotency_key, {
            "salon": request.salon_id, "destination": request.destination_reference,
            "amount": str(request.amount), "currency": request.currency,
        })
        reference = synthetic_reference("payout", request.idempotency_key)
        if reference not in self._payouts:
            self._payouts[reference] = ProviderPayout(
                "fake", reference, request.amount, PayoutStatus.processing,
                evidence_source=EvidenceSource.mock,
            )
        self._maybe_timeout("payout")
        return self._payouts[reference]

    async def fetch_payout(
        self, payout_reference: str | None = None, *, idempotency_key: str | None = None
    ) -> ProviderPayout | None:
        if payout_reference is None and not idempotency_key:
            raise ValueError("A payout reference or persisted idempotency key is required")
        if payout_reference is not None:
            _require_reference(payout_reference)
        by_key = synthetic_reference("payout", idempotency_key) if idempotency_key else None
        if payout_reference and by_key and payout_reference != by_key:
            return None
        return self._payouts.get(payout_reference or by_key)

    def simulate_payout(self, payout_reference: str, status: PayoutStatus) -> ProviderPayout:
        result = self._payouts[payout_reference]
        allowed = {
            PayoutStatus.processing: {PayoutStatus.succeeded, PayoutStatus.failed},
            PayoutStatus.succeeded: {PayoutStatus.reversed},
        }
        if status != result.status and status not in allowed.get(result.status, set()):
            raise ValueError("Invalid simulated payout transition")
        transfer = result.provider_transfer_reference
        if status == PayoutStatus.succeeded:
            transfer = synthetic_reference("transfer", payout_reference)
        self._payouts[payout_reference] = replace(
            result, status=status, provider_transfer_reference=transfer,
        )
        return self._payouts[payout_reference]

    def set_fee_observation(
        self, reference: str, fees: ProviderFees, *,
        provider_transfer_reference: str | None = None,
        provider_settlement_reference: str | None = None,
    ) -> None:
        """Explicit synthetic components only; never load a default provider tariff."""
        _require_reference(reference)
        if not isinstance(fees, ProviderFees):
            raise TypeError("Typed fee components are required")
        for value in (provider_transfer_reference, provider_settlement_reference):
            if value is not None:
                _require_reference(value)
        result = ProviderFeeReconciliation(
            "fake", reference, fees, evidence_source=EvidenceSource.mock,
            provider_transfer_reference=provider_transfer_reference,
            provider_settlement_reference=provider_settlement_reference,
        )
        if reference in self._fees and self._fees[reference] != result:
            raise IdempotencyKeyReuseError("Fee corrections require a new observation reference")
        self._fees[reference] = result

    async def reconcile_fees(self, reference: str) -> ProviderFeeReconciliation:
        _require_reference(reference)
        return self._fees.get(reference, ProviderFeeReconciliation("fake", reference))

    async def register_settlement_account(
        self, request: SettlementAccountRequest
    ) -> SettlementAccount:
        raise PaymentCapabilityError("The mock makes no vendor/KYC or split capability claim")

    async def get_settlement_account(self, account_ref: str) -> SettlementAccount:
        raise PaymentCapabilityError("The mock cannot verify vendor settlement")

    def payment_webhook(self, order_ref: str) -> MockWebhook:
        payment = self._payments[order_ref]
        return self._webhook({
            "event_type": _PAYMENT_EVENTS[payment.status].value,
            "payment_ref": payment.payment_ref, "order_ref": order_ref,
            "refund_ref": None, "amount": str(payment.amount), "currency": payment.currency,
        })

    def refund_webhook(self, refund_ref: str) -> MockWebhook:
        refund = self._refunds[refund_ref]
        kind = {RefundStatus.processed: PaymentEventType.refund_processed,
                RefundStatus.failed: PaymentEventType.refund_failed}.get(refund.status)
        if kind is None:
            raise ValueError("A pending refund has no terminal webhook")
        return self._webhook({
            "event_type": kind.value, "payment_ref": refund.payment_ref,
            "order_ref": None, "refund_ref": refund_ref,
            "amount": str(refund.amount), "currency": "INR",
        })

    @staticmethod
    def _webhook(data: dict[str, Any]) -> MockWebhook:
        data = {**data, "provider": "fake", "version": 1, "evidence_source": "mock"}
        data["event_id"] = synthetic_reference("event", _encoded(data).decode())
        body = _encoded(data)
        signature = hmac.new(_TEST_SIGNING_KEY, body, hashlib.sha256).hexdigest()
        return MockWebhook(body, {"x-fake-signature": signature})

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        signature = header(headers, "x-fake-signature") or ""
        if not isinstance(signature, str) or not re.fullmatch(r"[0-9a-f]{64}", signature):
            return False
        expected = hmac.new(_TEST_SIGNING_KEY, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        # Defensive standalone use also authenticates; intake already checks before parsing.
        if not self.verify_webhook_signature(raw_body, headers):
            raise ValueError("Invalid mock webhook signature")
        data = json.loads(raw_body)
        required = {"provider", "version", "evidence_source", "event_id", "event_type",
                    "payment_ref", "order_ref", "refund_ref", "amount", "currency"}
        if not isinstance(data, dict) or set(data) != required:
            raise ValueError("Invalid mock webhook shape")
        if data["provider"] != "fake" or data["version"] != 1 or data["evidence_source"] != "mock":
            raise ValueError("Invalid mock provider identity")
        event_id = data.pop("event_id")
        if event_id != synthetic_reference("event", _encoded(data).decode()):
            raise ValueError("Invalid deterministic mock event identity")
        kind = PaymentEventType(data["event_type"])
        if kind not in _SUPPORTED_EVENTS or data["currency"] != "INR":
            raise ValueError("Unsupported mock event")
        for name in ("payment_ref", "order_ref", "refund_ref"):
            if data[name] is not None:
                _require_reference(data[name])
        if not data["payment_ref"] or (
            kind in _PAYMENT_EVENTS.values() and not data["order_ref"]
        ) or (kind in {PaymentEventType.refund_processed, PaymentEventType.refund_failed}
              and not data["refund_ref"]):
            raise ValueError("Mock event references are incomplete")
        if not isinstance(data["amount"], str) or not re.fullmatch(r"[0-9]+\.[0-9]{2}", data["amount"]):
            raise ValueError("A decimal-string mock amount is required")
        amount = Money(data["amount"])
        require_positive_money(amount)
        return PaymentEvent(
            "fake", event_id, kind, f"fake.{kind.value}",
            payment_ref=data["payment_ref"], order_ref=data["order_ref"],
            refund_ref=data["refund_ref"], amount=amount, currency="INR",
        )


def create_gateway(settings) -> FakeProvider:
    # Repeat the safety check at the factory boundary, including model_construct callers.
    if not settings.fake_payments_enabled:
        raise PaymentCapabilityError("The fake provider is restricted to isolated local/test use")
    return FakeProvider()
