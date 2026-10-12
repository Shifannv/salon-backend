"""Razorpay adapter for owner subscription billing (one-time Orders, manual renewal).

Deleting this file removes Razorpay from subscriptions without touching the core
(``SUBSCRIPTION_PROVIDER`` is resolved by module name; see ``resolver.py``). It is
independent of ``app/infrastructure/payments/razorpay.py``: separate credentials, separate
webhook secret, no shared code.

Status: written against Razorpay's documented REST API and exercised only through
``httpx.MockTransport``. It has NEVER spoken to the live or test service. Anything marked
``UNVERIFIED`` must be confirmed in Razorpay test mode before any real use.

Conventions:
* ``POST /v1/orders`` takes ``amount`` in integer PAISE, ``currency``, ``receipt`` (<= 40
  characters) and ``notes``. ``receipt`` is OUR deterministic id, persisted before the call, so a
  timeout is recovered by listing orders by receipt (UNVERIFIED: the ``receipt`` filter).
* Checkout returns ``razorpay_payment_id``, ``razorpay_order_id``, ``razorpay_signature`` where the
  signature is hex HMAC-SHA256(key_secret, ``order_id|payment_id``). That is a client-side result,
  never proof; proof is a server fetch or a verified webhook.
* Webhook signature = hex HMAC-SHA256(webhook_secret, raw body) (UNVERIFIED: hex encoding),
  dedupe id = header ``X-Razorpay-Event-Id``. Deliveries are at-least-once and unordered.
* Auto-capture is assumed to be the account setting (UNVERIFIED); an ``authorized``-only payment
  is reported as ``authorized`` and never counts as paid.
"""

import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

from app.application.ports.subscription_provider import (
    ProviderOrder,
    ProviderOrderState,
    ProviderPaymentObservation,
    ProviderPaymentState,
    ProviderRefund,
    ProviderSubscriptionEvent,
    SubscriptionClientConfig,
    SubscriptionEventKind,
    SubscriptionOrderRequest,
    SubscriptionProvider,
)
from app.core.config import Settings
from app.core.exceptions import PaymentOutcomeUnknownError, PaymentProviderError
from app.domain.value_objects.money import Money

logger = logging.getLogger(__name__)

PROVIDER = "razorpay"
RECEIPT_MAX = 40

_ORDER_STATE = {
    "created": ProviderOrderState.created,
    "attempted": ProviderOrderState.attempted,
    "paid": ProviderOrderState.paid,
}
_PAYMENT_STATE = {
    "created": ProviderPaymentState.pending,
    "authorized": ProviderPaymentState.authorized,
    "captured": ProviderPaymentState.captured,
    "refunded": ProviderPaymentState.refunded,
    "failed": ProviderPaymentState.failed,
}
_EVENT_KINDS = {
    "payment.captured": SubscriptionEventKind.payment_captured,
    "order.paid": SubscriptionEventKind.order_paid,
    "payment.failed": SubscriptionEventKind.payment_failed,
    "refund.processed": SubscriptionEventKind.refund_processed,
    "refund.failed": SubscriptionEventKind.refund_failed,
}


def to_paise(amount: Money) -> int:
    return int((amount.amount * 100).to_integral_value(ROUND_HALF_UP))


def from_paise(paise: int | str | Decimal) -> Money:
    return Money((Decimal(paise) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _hex_hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name:
            return value
    return None


class RazorpaySubscriptionProvider(SubscriptionProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._key_id = settings.subscription_razorpay_key_id or ""
        secret = settings.subscription_razorpay_key_secret
        self._key_secret = secret.get_secret_value() if secret else ""
        webhook = settings.subscription_razorpay_webhook_secret
        self._webhook_secret = webhook.get_secret_value() if webhook else ""
        self._base_url = settings.razorpay_api_base_url.rstrip("/")
        self._timeout = settings.payment_provider_timeout_seconds
        self._client = client

    @property
    def provider_name(self) -> str:
        return PROVIDER

    def client_config(self) -> SubscriptionClientConfig:
        return SubscriptionClientConfig(provider=PROVIDER, public_key=self._key_id)

    # ---------------------------------------------------------------------- http
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=5.0))
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._http().request(
                method,
                f"{self._base_url}{path}",
                json=json_body,
                params=params,
                headers=headers,
                auth=(self._key_id, self._key_secret),
            )
        except httpx.HTTPError as exc:
            logger.warning("Subscription provider unreachable: %s %s", method, path)
            raise PaymentOutcomeUnknownError("Subscription provider is unreachable") from exc
        if response.status_code >= 400:
            code = None
            try:
                code = (response.json().get("error") or {}).get("code")
            except ValueError:
                pass
            logger.warning(
                "Subscription provider rejected %s: status=%s code=%s",
                method,
                response.status_code,
                code,
            )
            error_cls = (
                PaymentOutcomeUnknownError if response.status_code >= 500 else PaymentProviderError
            )
            raise error_cls(
                "Subscription provider rejected the request",
                {"provider_status": response.status_code, "provider_code": code},
            )
        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderError("Subscription provider returned an invalid response") from exc

    @staticmethod
    def _is_not_found(exc: PaymentProviderError) -> bool:
        return (
            not isinstance(exc, PaymentOutcomeUnknownError)
            and (getattr(exc, "details", None) or {}).get("provider_status") == 404
        )

    # -------------------------------------------------------------------- orders
    async def create_period_order(self, request: SubscriptionOrderRequest) -> ProviderOrder:
        if len(request.receipt) > RECEIPT_MAX:
            raise ValueError("receipt exceeds the provider limit")
        if request.amount.amount <= 0:
            raise ValueError("Subscription amount must be positive")
        body = {
            "amount": to_paise(request.amount),
            "currency": request.currency,
            "receipt": request.receipt,
            "notes": {
                "billing_record_id": request.billing_record_id,
                "salon_id": request.salon_id,
                "plan_id": request.plan_id,
                "kind": "subscription_period",
            },
        }
        return self._to_order(await self._request("POST", "/orders", json_body=body))

    async def fetch_order(self, order_ref: str) -> ProviderOrder | None:
        try:
            return self._to_order(await self._request("GET", f"/orders/{order_ref}"))
        except PaymentProviderError as exc:
            if self._is_not_found(exc):
                return None
            raise

    async def find_order_by_receipt(self, receipt: str) -> ProviderOrder | None:
        # UNVERIFIED: confirm in Razorpay test mode that GET /orders?receipt= filters.
        listing = await self._request("GET", "/orders", params={"receipt": receipt, "count": 10})
        matches = [i for i in listing.get("items", []) if i.get("receipt") == receipt]
        if not matches:
            return None
        return self._to_order(matches[0])

    def _to_order(self, data: Mapping[str, Any]) -> ProviderOrder:
        try:
            return ProviderOrder(
                provider=PROVIDER,
                order_ref=str(data["id"]),
                receipt=data.get("receipt"),
                amount=from_paise(data["amount"]),
                currency=str(data.get("currency") or "INR"),
                state=_ORDER_STATE.get(str(data.get("status")), ProviderOrderState.created),
                amount_paid=from_paise(data.get("amount_paid") or 0),
                client_payload={
                    "key_id": self._key_id,
                    "order_id": str(data["id"]),
                    "amount": int(data["amount"]),  # PAISE, as Razorpay Checkout expects
                    "currency": str(data.get("currency") or "INR"),
                },
            )
        except (KeyError, ArithmeticError, ValueError) as exc:
            raise PaymentProviderError("Subscription provider returned an invalid order") from exc

    # ------------------------------------------------------------------ payments
    async def fetch_order_payments(self, order_ref: str) -> list[ProviderPaymentObservation]:
        listing = await self._request("GET", f"/orders/{order_ref}/payments")
        return [self._to_payment(item) for item in listing.get("items", [])]

    async def fetch_payment(self, payment_ref: str) -> ProviderPaymentObservation | None:
        try:
            return self._to_payment(await self._request("GET", f"/payments/{payment_ref}"))
        except PaymentProviderError as exc:
            if self._is_not_found(exc):
                return None
            raise

    @staticmethod
    def _to_payment(item: Mapping[str, Any]) -> ProviderPaymentObservation:
        try:
            state = _PAYMENT_STATE.get(str(item.get("status")), ProviderPaymentState.pending)
            refunded = from_paise(item.get("amount_refunded") or 0)
            if state is ProviderPaymentState.captured and item.get("refund_status") == "partial":
                state = ProviderPaymentState.partially_refunded
            return ProviderPaymentObservation(
                provider=PROVIDER,
                payment_ref=str(item["id"]),
                order_ref=item.get("order_id"),
                state=state,
                amount=from_paise(item["amount"]),
                currency=str(item.get("currency") or "INR"),
                amount_refunded=refunded,
                failure_code=item.get("error_code"),
            )
        except (KeyError, ArithmeticError, ValueError) as exc:
            raise PaymentProviderError("Subscription provider returned an invalid payment") from exc

    # ------------------------------------------------------------- verification
    def verify_client_callback(self, order_ref: str, payment_ref: str, signature: str) -> bool:
        expected = _hex_hmac(self._key_secret, f"{order_ref}|{payment_ref}".encode())
        return hmac.compare_digest(expected, signature or "")

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        signature = _header(headers, "x-razorpay-signature")
        if not signature or not self._webhook_secret:
            return False
        return hmac.compare_digest(_hex_hmac(self._webhook_secret, raw_body), signature)

    def parse_event(
        self, raw_body: bytes, headers: Mapping[str, str]
    ) -> ProviderSubscriptionEvent:
        try:
            document = json.loads(raw_body)
            raw_type = str(document["event"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Unparseable webhook body") from exc
        event_id = _header(headers, "x-razorpay-event-id") or hashlib.sha256(raw_body).hexdigest()
        kind = _EVENT_KINDS.get(raw_type)
        if kind is None:
            return ProviderSubscriptionEvent(
                provider=PROVIDER,
                event_id=event_id,
                kind=SubscriptionEventKind.ignored,
                raw_type=raw_type,
            )
        payload = document.get("payload") or {}
        try:
            if raw_type.startswith("refund."):
                refund = (payload.get("refund") or {}).get("entity") or {}
                return ProviderSubscriptionEvent(
                    provider=PROVIDER,
                    event_id=event_id,
                    kind=kind,
                    raw_type=raw_type,
                    payment_ref=refund.get("payment_id"),
                    refund_ref=refund.get("id"),
                    amount=from_paise(refund["amount"]) if refund.get("amount") is not None else None,
                    currency=refund.get("currency"),
                    failure_code=refund.get("error_code"),
                )
            payment = (payload.get("payment") or {}).get("entity") or {}
            order = (payload.get("order") or {}).get("entity") or {}
            amount_src = payment.get("amount", order.get("amount"))
            return ProviderSubscriptionEvent(
                provider=PROVIDER,
                event_id=event_id,
                kind=kind,
                raw_type=raw_type,
                order_ref=payment.get("order_id") or order.get("id"),
                payment_ref=payment.get("id"),
                amount=from_paise(amount_src) if amount_src is not None else None,
                currency=payment.get("currency") or order.get("currency"),
                failure_code=payment.get("error_code"),
            )
        except (ArithmeticError, ValueError) as exc:
            raise ValueError("Unparseable webhook amounts") from exc

    # -------------------------------------------------------------------- refund
    async def refund(
        self, payment_ref: str, amount: Money, idempotency_key: str, reason: str | None = None
    ) -> ProviderRefund:
        data = await self._request(
            "POST",
            f"/payments/{payment_ref}/refund",
            json_body={
                "amount": to_paise(amount),
                "speed": "normal",
                "notes": {"reason": (reason or "")[:200]},
            },
            # UNVERIFIED: confirm the idempotency header name in Razorpay test mode.
            headers={"X-Refund-Idempotency": idempotency_key},
        )
        try:
            return ProviderRefund(
                provider=PROVIDER,
                refund_ref=str(data["id"]),
                payment_ref=str(data.get("payment_id") or payment_ref),
                amount=from_paise(data.get("amount", to_paise(amount))),
                status=str(data.get("status") or "created"),
            )
        except (KeyError, ArithmeticError) as exc:
            raise PaymentProviderError("Subscription provider returned an invalid refund") from exc


def create_provider(settings: Settings) -> SubscriptionProvider:
    """Factory discovered by ``resolver.build_subscription_provider``."""

    return RazorpaySubscriptionProvider(settings)
