"""Razorpay adapter: the ONLY module that knows this provider's wire format.

Deleting this file removes Razorpay without touching the payment core
(``PAYMENT_PROVIDER`` is resolved by module name; see ``resolver.py``).

Status of this adapter: complete against Razorpay's documented REST API, exercised in
tests only through ``httpx.MockTransport``. It has never spoken to the live service, so
every field name below is "per documentation, unverified against a sandbox".

Conventions:
* Orders and refunds use integer paise. ``Money`` is major units at 2 dp, so the
  conversion is exact (``ROUND_HALF_UP`` is applied defensively).
* ``receipt`` = our ``intent_reference`` (Razorpay caps receipts at 40 characters).
* ``transfers[]`` is sent only when Route is enabled (``RAZORPAY_ROUTE_ENABLED``).
* Webhook signature = hex HMAC-SHA256 of the raw body keyed by the webhook secret;
  callback signature = hex HMAC-SHA256 of ``f"{order_id}|{payment_id}"`` keyed by the API
  secret. Both are compared with ``hmac.compare_digest``.
* Auto-capture is assumed (the Razorpay account setting). An ``authorized``-only payment
  would need a capture call that this adapter does not make.
"""

import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx

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
from app.core.config import Settings
from app.core.exceptions import (
    PaymentCapabilityError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
)
from app.core.telemetry import measure_external
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    OnboardingStatus,
    PaymentEventType,
    PaymentInstrument,
    RefundStatus,
    SettlementModel,
)
from app.domain.value_objects.money import Money
from app.infrastructure.webhook_signing import header, hex_hmac

logger = logging.getLogger(__name__)

PROVIDER = "razorpay"
_RECEIPT_MAX = 40

_PAYMENT_STATUS = {
    "created": LedgerStatus.created,
    "authorized": LedgerStatus.authorized,
    "captured": LedgerStatus.captured,
    "refunded": LedgerStatus.refunded,
    "failed": LedgerStatus.failed,
}
_REFUND_STATUS = {
    "pending": RefundStatus.created,
    "created": RefundStatus.created,
    "processed": RefundStatus.processed,
    "failed": RefundStatus.failed,
}
_INSTRUMENT = {
    "upi": PaymentInstrument.upi,
    "card": PaymentInstrument.card,
    "netbanking": PaymentInstrument.netbanking,
    "wallet": PaymentInstrument.wallet,
}
_ACCOUNT_STATUS = {
    "created": OnboardingStatus.pending,
    "under_review": OnboardingStatus.pending,
    "needs_clarification": OnboardingStatus.needs_action,
    "activated": OnboardingStatus.active,
    "suspended": OnboardingStatus.suspended,
    "rejected": OnboardingStatus.rejected,
}
_EVENT_TYPES = {
    "payment.authorized": PaymentEventType.payment_authorized,
    "payment.captured": PaymentEventType.payment_captured,
    "payment.failed": PaymentEventType.payment_failed,
    "refund.processed": PaymentEventType.refund_processed,
    "refund.failed": PaymentEventType.refund_failed,
}


def to_paise(amount: Money) -> int:
    """Convert major units to integer paise."""

    return int((amount.amount * 100).to_integral_value(ROUND_HALF_UP))


def from_paise(paise: int | str | Decimal) -> Money:
    """Convert integer paise to ``Money``."""

    return Money((Decimal(paise) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP))


class RazorpayGateway(PaymentGateway):
    """Razorpay Orders + Route implementation of the payment port."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._key_id = settings.razorpay_key_id or ""
        self._key_secret = settings.razorpay_key_secret or ""
        self._webhook_secret = webhook_secret or settings.razorpay_webhook_secret or ""
        self._route_enabled = settings.razorpay_route_enabled
        self._base_url = settings.razorpay_api_base_url.rstrip("/")
        self._currency = settings.payment_currency
        self._intent_ttl = settings.payment_intent_ttl_seconds
        self._settlement_model = SettlementModel(settings.payment_settlement_model)
        self._client = client

    # ------------------------------------------------------------------ identity
    @property
    def provider_name(self) -> str:
        return PROVIDER

    def supports(self, capability: GatewayCapability) -> bool:
        if capability in {
            GatewayCapability.online_collection,
            GatewayCapability.refunds,
            GatewayCapability.callback_signature,
        }:
            return True
        if capability in {GatewayCapability.split_settlement, GatewayCapability.linked_accounts}:
            return self._route_enabled
        return False

    def client_config(self) -> ClientConfig:
        return ClientConfig(
            enabled=True,
            provider=PROVIDER,
            public_key=self._key_id,
            currency=self._currency,
            settlement_model=self._settlement_model,
        )

    # ---------------------------------------------------------------------- http
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        return self._client

    @measure_external("razorpay")
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        base_url: str | None = None,
    ) -> dict[str, Any]:
        url = f"{base_url or self._base_url}{path}"
        try:
            response = await self._http().request(
                method,
                url,
                json=json_body,
                headers=headers,
                auth=(self._key_id, self._key_secret),
            )
        except httpx.HTTPError as exc:
            logger.warning("Payment provider unreachable: %s %s", method, path)
            raise PaymentOutcomeUnknownError("Payment provider is unreachable") from exc
        if response.status_code >= 400:
            code = None
            try:
                code = (response.json().get("error") or {}).get("code")
            except ValueError:
                pass
            logger.warning(
                "Payment provider rejected %s %s: status=%s code=%s",
                method,
                path,
                response.status_code,
                code,
            )
            error_cls = (
                PaymentOutcomeUnknownError if response.status_code >= 500 else PaymentProviderError
            )
            raise error_cls(
                "Payment provider rejected the request",
                {"provider_status": response.status_code, "provider_code": code},
            )
        try:
            return response.json()
        except ValueError as exc:
            raise PaymentProviderError("Payment provider returned an invalid response") from exc

    # -------------------------------------------------------------------- intents
    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent:
        if len(request.intent_reference) > _RECEIPT_MAX:
            raise ValueError("intent_reference exceeds the provider receipt limit")
        if request.amount.amount <= 0:
            raise ValueError("Payment amount must be positive")
        body: dict[str, Any] = {
            "amount": to_paise(request.amount),
            "currency": request.currency,
            "receipt": request.intent_reference,
            "notes": {"booking_id": request.booking_id, "salon_id": request.salon_id},
        }
        if self._route_enabled:
            if not request.settlement_account_ref:
                raise PaymentCapabilityError("The salon has no active settlement account")
            payee = request.amount - request.platform_fee
            body["transfers"] = [
                {
                    "account": request.settlement_account_ref,
                    "amount": to_paise(payee),
                    "currency": request.currency,
                    "on_hold": 0,
                    "notes": {"booking_id": request.booking_id},
                }
            ]
        order = await self._request("POST", "/orders", json_body=body)
        try:
            order_id = str(order["id"])
        except KeyError as exc:
            raise PaymentProviderError("Payment provider returned an invalid order") from exc
        return PaymentIntent(
            provider=PROVIDER,
            order_ref=order_id,
            intent_reference=request.intent_reference,
            amount=request.amount,
            currency=request.currency,
            client_payload={
                "key_id": self._key_id,
                "order_id": order_id,
                "amount": body["amount"],
                "currency": request.currency,
            },
            expires_at=datetime.now(UTC) + timedelta(seconds=self._intent_ttl),
        )

    # ------------------------------------------------------------- verification
    def verify_payment_callback(self, callback: PaymentCallback) -> bool:
        expected = hex_hmac(
            self._key_secret, f"{callback.order_ref}|{callback.payment_ref}".encode()
        )
        return hmac.compare_digest(expected, callback.signature or "")

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        signature = header(headers, "x-razorpay-signature")
        if not signature or not self._webhook_secret:
            return False
        return hmac.compare_digest(hex_hmac(self._webhook_secret, raw_body), signature)

    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        try:
            document = json.loads(raw_body)
            raw_type = str(document["event"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Unparseable webhook body") from exc
        event_id = header(headers, "x-razorpay-event-id") or hashlib.sha256(raw_body).hexdigest()
        payload = document.get("payload") or {}

        if raw_type.startswith("account."):
            entity = (payload.get("account") or {}).get("entity") or {}
            status = _ACCOUNT_STATUS.get(
                str(entity.get("status") or raw_type.removeprefix("account."))
            )
            return PaymentEvent(
                provider=PROVIDER,
                event_id=event_id,
                event_type=PaymentEventType.account_updated,
                raw_type=raw_type,
                account_ref=entity.get("id"),
                onboarding_status=status,
            )

        event_type = _EVENT_TYPES.get(raw_type)
        if event_type is None:
            return PaymentEvent(
                provider=PROVIDER,
                event_id=event_id,
                event_type=PaymentEventType.ignored,
                raw_type=raw_type,
            )
        if raw_type.startswith("refund."):
            refund = (payload.get("refund") or {}).get("entity") or {}
            return PaymentEvent(
                provider=PROVIDER,
                event_id=event_id,
                event_type=event_type,
                raw_type=raw_type,
                payment_ref=refund.get("payment_id"),
                refund_ref=refund.get("id"),
                amount=from_paise(refund["amount"]) if refund.get("amount") is not None else None,
                currency=refund.get("currency"),
                failure_code=refund.get("error_code"),
            )
        payment = (payload.get("payment") or {}).get("entity") or {}
        return PaymentEvent(
            provider=PROVIDER,
            event_id=event_id,
            event_type=event_type,
            raw_type=raw_type,
            payment_ref=payment.get("id"),
            order_ref=payment.get("order_id"),
            amount=from_paise(payment["amount"]) if payment.get("amount") is not None else None,
            currency=payment.get("currency"),
            instrument=_INSTRUMENT.get(str(payment.get("method"))),
            failure_code=payment.get("error_code"),
        )

    # -------------------------------------------------------------------- fetches
    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None:
        if payment_ref:
            return self._to_payment(await self._request("GET", f"/payments/{payment_ref}"))
        if not order_ref:
            raise ValueError("payment_ref or order_ref is required")
        listing = await self._request("GET", f"/orders/{order_ref}/payments")
        payments = [self._to_payment(item) for item in listing.get("items", [])]
        if not payments:
            return None
        rank = {
            LedgerStatus.refunded: 5,
            LedgerStatus.partially_refunded: 4,
            LedgerStatus.captured: 3,
            LedgerStatus.authorized: 2,
            LedgerStatus.created: 1,
            LedgerStatus.failed: 0,
        }
        return max(payments, key=lambda p: rank.get(p.status, 0))

    @staticmethod
    def _to_payment(item: Mapping[str, Any]) -> ProviderPayment:
        status = _PAYMENT_STATUS.get(str(item.get("status")), LedgerStatus.created)
        if status == LedgerStatus.captured and item.get("refund_status") == "partial":
            status = LedgerStatus.partially_refunded
        return ProviderPayment(
            provider=PROVIDER,
            payment_ref=str(item["id"]),
            order_ref=item.get("order_id"),
            status=status,
            amount=from_paise(item["amount"]),
            currency=str(item.get("currency") or "INR"),
            instrument=_INSTRUMENT.get(str(item.get("method"))),
            failure_code=item.get("error_code"),
        )

    # -------------------------------------------------------------------- refunds
    async def refund(self, request: RefundRequest) -> RefundResult:
        body: dict[str, Any] = {
            "amount": to_paise(request.amount),
            "speed": "normal",
            "notes": {"reason": (request.reason or "")[:200]},
        }
        if self._route_enabled:
            body["reverse_all"] = 1  # claw the refunded share back from the linked account
        data = await self._request(
            "POST",
            f"/payments/{request.payment_ref}/refund",
            json_body=body,
            headers={"X-Refund-Idempotency": request.idempotency_key},
        )
        return RefundResult(
            provider=PROVIDER,
            refund_ref=str(data["id"]),
            status=_REFUND_STATUS.get(str(data.get("status")), RefundStatus.created),
            amount=from_paise(data.get("amount", body["amount"])),
            payment_ref=data.get("payment_id") or request.payment_ref,
            failure_code=data.get("error_code"),
        )

    # ------------------------------------------------------- settlement accounts
    def _v2(self) -> str:
        return self._base_url[: -len("/v1")] + "/v2" if self._base_url.endswith("/v1") else self._base_url

    async def register_settlement_account(
        self, request: SettlementAccountRequest
    ) -> SettlementAccount:
        if not self._route_enabled:
            raise PaymentCapabilityError("Linked accounts require Route to be enabled")
        data = await self._request(
            "POST",
            "/accounts",
            base_url=self._v2(),
            json_body={
                "email": request.email,
                "phone": request.phone,
                "type": "route",
                "reference_id": request.salon_id,
                "legal_business_name": request.legal_name,
                "business_type": "individual",
                "contact_name": request.legal_name,
                "profile": {"category": "services", "subcategory": "salon_and_spa"},
            },
        )
        return self._to_account(data)

    async def get_settlement_account(self, account_ref: str) -> SettlementAccount:
        if not self._route_enabled:
            raise PaymentCapabilityError("Linked accounts require Route to be enabled")
        return self._to_account(
            await self._request("GET", f"/accounts/{account_ref}", base_url=self._v2())
        )

    @staticmethod
    def _to_account(data: Mapping[str, Any]) -> SettlementAccount:
        requirements = tuple(
            str(item.get("field_reference") or item.get("reason_code") or item)
            for item in (data.get("requirements") or [])
        )
        return SettlementAccount(
            provider=PROVIDER,
            account_ref=str(data["id"]),
            onboarding_status=_ACCOUNT_STATUS.get(str(data.get("status")), OnboardingStatus.pending),
            requirements=requirements,
        )


def create_gateway(settings: Settings) -> PaymentGateway:
    """Factory discovered by ``resolver.build_gateway``."""

    return RazorpayGateway(settings)
