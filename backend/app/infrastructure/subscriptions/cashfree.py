"""Cashfree one-time subscription orders. No booking splits or client-side payment proof.

Official PG API 2026-01-01; tested locally with MockTransport. Merchant sandbox
acceptance and live activation require operator credentials and domain approval.
Payment references are opaque `order_id:cf_payment_id` pairs because Cashfree
payment/refund reads require the order id. The ledger and worker store them unchanged.
"""

import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC
from decimal import Decimal
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
from app.core.exceptions import PaymentOutcomeUnknownError, PaymentProviderError, ValidationError
from app.domain.value_objects.money import Money
from app.infrastructure.payments.cashfree import dumps_json
from app.infrastructure.webhook_signing import header

_ORDER_ID = re.compile(r"[A-Za-z0-9_-]{3,45}\Z")
_PAYMENT_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
_PAYMENT_STATES = {
    "SUCCESS": ProviderPaymentState.captured,
    "FAILED": ProviderPaymentState.failed,
    "USER_DROPPED": ProviderPaymentState.failed,
    "PENDING": ProviderPaymentState.pending,
    "NOT_ATTEMPTED": ProviderPaymentState.pending,
}


class CashfreeSubscriptionProvider(SubscriptionProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._client_id = settings.subscription_cashfree_client_id or ""
        secret = settings.subscription_cashfree_client_secret
        self._secret = secret.get_secret_value() if secret else ""
        self._mode = settings.subscription_cashfree_environment
        host = "sandbox.cashfree.com" if self._mode == "sandbox" else "api.cashfree.com"
        self._base = f"https://{host}/pg"
        self._version = settings.subscription_cashfree_api_version
        self._timeout = settings.payment_provider_timeout_seconds
        self._client = client
        base = str(settings.public_api_base_url or "").rstrip("/")
        self._notify = f"{base}/v1/webhooks/cashfree" if base.startswith("https://") else None

    @property
    def provider_name(self) -> str:
        return "cashfree"

    def client_config(self) -> SubscriptionClientConfig:
        return SubscriptionClientConfig(provider="cashfree", public_key=None)

    async def _request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        key: str | None = None,
        missing_ok: bool = False,
    ) -> Any:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=5))
        headers = {
            "x-client-id": self._client_id,
            "x-client-secret": self._secret,
            "x-api-version": self._version,
            "accept": "application/json",
        }
        if key:
            headers["x-idempotency-key"] = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"subscription:{key}")
            )
        if body is not None:
            headers["content-type"] = "application/json"
        try:
            response = await self._client.request(
                method,
                self._base + path,
                headers=headers,
                content=dumps_json(body) if body is not None else None,
            )
        except httpx.HTTPError as exc:
            raise PaymentOutcomeUnknownError("Subscription provider is unreachable") from exc
        if response.status_code == 404 and missing_ok:
            return None
        if response.status_code >= 400:
            error = (
                PaymentOutcomeUnknownError
                if response.status_code >= 500 or response.status_code == 429
                else PaymentProviderError
            )
            raise error(
                "Subscription provider rejected the request",
                {"provider_status": response.status_code},
            )
        try:
            return json.loads(response.content, parse_float=Decimal)
        except ValueError as exc:
            raise PaymentOutcomeUnknownError(
                "Subscription provider returned an unreadable response"
            ) from exc

    @staticmethod
    def _order_id(value: str) -> str:
        if not _ORDER_ID.fullmatch(value):
            raise ValueError("Invalid subscription order reference")
        return value

    async def create_period_order(self, request: SubscriptionOrderRequest) -> ProviderOrder:
        self._order_id(request.receipt)
        if request.amount.amount < 1:
            raise ValidationError("The minimum subscription payment is INR 1")
        phone = re.sub(r"[^0-9]", "", request.customer_phone or "")
        if len(phone) == 12 and phone.startswith("91"):
            phone = phone[2:]
        if not re.fullmatch(r"[6-9][0-9]{9}", phone):
            raise ValidationError(
                "Add a valid Indian mobile number to your owner profile before paying"
            )
        customer = {"customer_id": request.customer_id or request.salon_id, "customer_phone": phone}
        if request.customer_name:
            customer["customer_name"] = request.customer_name[:100]
        if request.customer_email:
            customer["customer_email"] = request.customer_email
        meta = {}
        if request.return_url:
            meta["return_url"] = request.return_url
        if self._notify:
            meta["notify_url"] = self._notify
        body = {
            "order_id": request.receipt,
            "order_amount": request.amount.amount,
            "order_currency": request.currency,
            "customer_details": customer,
            "order_meta": meta,
            "order_tags": {
                "kind": "subscription_period",
                "billing_record_id": request.billing_record_id,
            },
        }
        if request.expires_at:
            body["order_expiry_time"] = request.expires_at.astimezone(UTC).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        try:
            data = await self._request("POST", "/orders", body, key=request.receipt)
        except PaymentProviderError as exc:
            if (exc.details or {}).get("provider_status") == 409:
                found = await self.fetch_order(request.receipt)
                if found is not None:
                    return found
            raise
        try:
            order = self._to_order(data)
        except PaymentProviderError as exc:
            raise PaymentOutcomeUnknownError(
                "Subscription order needs reconciliation by receipt"
            ) from exc
        if order.order_ref != request.receipt:
            raise PaymentOutcomeUnknownError(
                "Subscription order identity needs reconciliation by receipt"
            )
        return order

    def _to_order(self, data: Mapping[str, Any]) -> ProviderOrder:
        try:
            order_ref = self._order_id(str(data["order_id"]))
            amount = Money(str(data["order_amount"]))
            paid = data.get("order_status") == "PAID"
            if data.get("order_status") not in {"ACTIVE", "PAID"}:
                raise ValueError("Subscription order is no longer payable")
            if not paid and not isinstance(data.get("payment_session_id"), str):
                raise PaymentOutcomeUnknownError(
                    "Subscription payment session is not available yet"
                )
            payload = {"payment_session_id": data.get("payment_session_id"), "mode": self._mode}
            return ProviderOrder(
                provider="cashfree",
                order_ref=order_ref,
                receipt=order_ref,
                amount=amount,
                currency=str(data["order_currency"]),
                state=ProviderOrderState.paid if paid else ProviderOrderState.created,
                amount_paid=amount if paid else Money(0),
                client_payload=payload,
            )
        except (KeyError, ValueError, ArithmeticError, TypeError) as exc:
            raise PaymentProviderError("Subscription provider returned an invalid order") from exc

    async def fetch_order(self, order_ref: str) -> ProviderOrder | None:
        data = await self._request("GET", f"/orders/{self._order_id(order_ref)}", missing_ok=True)
        if data is None:
            return None
        order = self._to_order(data)
        if order.order_ref != order_ref:
            raise PaymentProviderError("Subscription provider returned a different order")
        return order

    async def find_order_by_receipt(self, receipt: str) -> ProviderOrder | None:
        return await self.fetch_order(receipt)

    @staticmethod
    def _payment(item: Mapping[str, Any], order_ref: str) -> ProviderPaymentObservation:
        try:
            if item.get("order_id") not in (None, order_ref):
                raise ValueError("Wrong order")
            payment_id = str(item["cf_payment_id"])
            if not _PAYMENT_ID.fullmatch(payment_id):
                raise ValueError("Invalid payment reference")
            return ProviderPaymentObservation(
                provider="cashfree",
                payment_ref=f"{order_ref}:{payment_id}",
                order_ref=order_ref,
                state=(
                    ProviderPaymentState.authorized
                    if item.get("is_captured") is False and item["payment_status"] == "SUCCESS"
                    else _PAYMENT_STATES.get(
                        str(item["payment_status"]), ProviderPaymentState.pending
                    )
                ),
                amount=Money(str(item["payment_amount"])),
                currency=str(item["payment_currency"]),
                failure_code=(item.get("error_details") or {}).get("error_code"),
            )
        except (KeyError, ValueError, ArithmeticError, TypeError) as exc:
            raise PaymentProviderError("Subscription provider returned an invalid payment") from exc

    async def fetch_order_payments(self, order_ref: str) -> list[ProviderPaymentObservation]:
        rows = await self._request("GET", f"/orders/{self._order_id(order_ref)}/payments")
        if not isinstance(rows, list):
            raise PaymentProviderError("Subscription provider returned invalid payments")
        return [self._payment(row, order_ref) for row in rows]

    @classmethod
    def _split_payment(cls, payment_ref: str) -> tuple[str, str]:
        order_ref, separator, payment_id = payment_ref.partition(":")
        cls._order_id(order_ref)
        if not separator or not _PAYMENT_ID.fullmatch(payment_id):
            raise ValueError("Invalid subscription payment reference")
        return order_ref, payment_id

    async def fetch_payment(self, payment_ref: str) -> ProviderPaymentObservation | None:
        order_ref, payment_id = self._split_payment(payment_ref)
        data = await self._request(
            "GET", f"/orders/{order_ref}/payments/{payment_id}", missing_ok=True
        )
        if data is None:
            return None
        observed = self._payment(data, order_ref)
        if observed.payment_ref != payment_ref:
            raise PaymentProviderError("Subscription provider returned a different payment")
        refunds = await self._request("GET", f"/orders/{order_ref}/refunds")
        if not isinstance(refunds, list):
            raise PaymentProviderError("Subscription provider returned invalid refunds")
        if any(
            row.get("refund_status") == "SUCCESS" and row.get("cf_payment_id") is None
            for row in refunds
        ):
            raise PaymentProviderError("Subscription refund payment attribution is missing")
        refunded = sum(
            (
                Decimal(str(row["refund_amount"]))
                for row in refunds
                if row.get("refund_status") == "SUCCESS"
                and str(row.get("cf_payment_id")) == payment_id
            ),
            Decimal(0),
        )
        state = observed.state
        if refunded < 0 or refunded > observed.amount.amount:
            raise PaymentProviderError("Subscription provider returned an invalid refunded amount")
        if refunded > 0:
            state = (
                ProviderPaymentState.refunded
                if refunded >= observed.amount.amount
                else ProviderPaymentState.partially_refunded
            )
        return replace(observed, amount_refunded=Money(refunded), state=state)

    def verify_client_callback(self, order_ref: str, payment_ref: str, signature: str) -> bool:
        return False  # Cashfree's browser result carries no signed payment proof.

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        stamp = header(headers, "x-webhook-timestamp")
        signature = header(headers, "x-webhook-signature")
        if not stamp or not signature or not self._secret:
            return False
        try:
            seconds = int(stamp) / 1000
            if abs(time.time() - seconds) > 86400:
                return False
        except (ValueError, OverflowError):
            return False
        digest = hmac.new(self._secret.encode(), stamp.encode() + raw_body, hashlib.sha256).digest()
        return hmac.compare_digest(base64.b64encode(digest), signature.encode())

    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> ProviderSubscriptionEvent:
        try:
            doc = json.loads(raw_body, parse_float=Decimal)
            raw_type = str(doc["type"])
            data = doc["data"]
            order = data.get("order") or {}
            payment = data.get("payment") or {}
            refund = data.get("refund") or {}
            order_ref = order.get("order_id") or refund.get("order_id")
            payment_id = payment.get("cf_payment_id") or refund.get("cf_payment_id")
            kinds = {
                "PAYMENT_SUCCESS_WEBHOOK": SubscriptionEventKind.payment_captured,
                "PAYMENT_FAILED_WEBHOOK": SubscriptionEventKind.payment_failed,
                "PAYMENT_USER_DROPPED_WEBHOOK": SubscriptionEventKind.payment_failed,
            }
            kind = kinds.get(raw_type, SubscriptionEventKind.ignored)
            if raw_type == "REFUND_STATUS_WEBHOOK":
                kind = {
                    "SUCCESS": SubscriptionEventKind.refund_processed,
                    "FAILED": SubscriptionEventKind.refund_failed,
                    "CANCELLED": SubscriptionEventKind.refund_failed,
                    "REJECTED": SubscriptionEventKind.refund_failed,
                }.get(str(refund.get("refund_status")), SubscriptionEventKind.ignored)
            amount = payment.get("payment_amount", refund.get("refund_amount"))
            return ProviderSubscriptionEvent(
                provider="cashfree",
                event_id=hashlib.sha256(raw_body).hexdigest(),
                kind=kind,
                raw_type=raw_type,
                order_ref=order_ref,
                payment_ref=f"{order_ref}:{payment_id}" if order_ref and payment_id else None,
                refund_ref=refund.get("refund_id"),
                amount=Money(str(amount)) if amount is not None else None,
                currency=payment.get("payment_currency") or order.get("order_currency"),
            )
        except (ValueError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
            raise ValueError("Unparseable subscription webhook") from exc

    async def refund(
        self, payment_ref: str, amount: Money, idempotency_key: str, reason: str | None = None
    ) -> ProviderRefund:
        order_ref, payment_id = self._split_payment(payment_ref)
        if amount.amount <= 0:
            raise ValueError("Subscription refund amount must be positive")
        refund_ref = "subrf_" + uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key).hex
        body = {
            "refund_id": refund_ref,
            "refund_amount": amount.amount,
            "refund_note": (reason or "Subscription refund")[:100],
            "refund_speed": "STANDARD",
        }
        try:
            data = await self._request("POST", f"/orders/{order_ref}/refunds", body, key=refund_ref)
        except PaymentProviderError as exc:
            if (exc.details or {}).get("provider_status") != 409:
                raise
            data = await self._request("GET", f"/orders/{order_ref}/refunds/{refund_ref}")
        if isinstance(data, list):
            if len(data) != 1:
                raise PaymentOutcomeUnknownError("Subscription refund needs reconciliation")
            data = data[0]
        try:
            if data["refund_id"] != refund_ref or Money(str(data["refund_amount"])) != amount:
                raise ValueError("Different refund returned")
            if str(data.get("cf_payment_id")) != payment_id:
                raise ValueError("Refund belongs to a different payment")
            status = {
                "SUCCESS": "processed",
                "FAILED": "failed",
                "CANCELLED": "failed",
                "REJECTED": "failed",
            }.get(str(data["refund_status"]), "created")
            return ProviderRefund(
                "cashfree",
                str(data["refund_id"]),
                payment_ref,
                Money(str(data["refund_amount"])),
                status,
            )
        except (KeyError, ValueError, ArithmeticError, TypeError) as exc:
            raise PaymentOutcomeUnknownError(
                "Subscription refund needs reconciliation by reference"
            ) from exc


def create_provider(settings: Settings) -> SubscriptionProvider:
    return CashfreeSubscriptionProvider(settings)
