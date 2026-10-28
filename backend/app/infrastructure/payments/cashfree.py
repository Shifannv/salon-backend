"""Cashfree booking Payment Gateway + Easy Split adapter.

Platform subscription revenue uses the separate subscriptions/cashfree.py adapter and
SUBSCRIPTION_CASHFREE_* credentials; enabling this booking adapter is not required for it.

Deleting this file removes Cashfree without touching the payment core (``PAYMENT_PROVIDER`` is
resolved by module name; see ``resolver.py``).

Evidence level: BUILT and TESTED LOCALLY through ``httpx.MockTransport`` only. It has never
spoken to Cashfree. Every item that was not confirmed from the provider's official pages is
isolated in a ``_UNVERIFIED_*`` constant or function with a ``# UNVERIFIED: confirm in Cashfree
sandbox`` comment; check them all before any live use.

Conventions:
* Cashfree amounts are RUPEES as decimals (some providers use minor units). ``Decimal`` end to end: the
  request body is serialised with real JSON numbers (never floats) and responses are parsed with
  ``parse_float=Decimal``.
* ``order_id`` = our persisted ``intent_reference`` (chosen by us, so a crash can be reconciled by
  that id). ``refund_id`` = a deterministic id derived from our persisted refund row.
* ``x-idempotency-key`` (a UUID derived from those ids) is sent on every create call.
* The mobile SDK callback is NOT proof of payment: ``callback_signature`` is not a capability, so
  the booking is only ever confirmed by GET order / GET order payments (server-side refresh) or a
  signed webhook.
* Webhook signature = Base64(HMAC-SHA256(key=client_secret, msg=timestamp + raw_body)).
"""

import base64
import hashlib
import hmac
import json
import logging
import re
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
    ValidationError,
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
from app.infrastructure.webhook_signing import header

logger = logging.getLogger(__name__)

PROVIDER = "cashfree"

_BASE_URL = {
    "sandbox": "https://sandbox.cashfree.com/pg",
    "production": "https://api.cashfree.com/pg",
}

# --------------------------------------------------------------------------- UNVERIFIED
# Each constant below was inferred from documentation summaries, not confirmed.
# UNVERIFIED: confirm in Cashfree sandbox
_UNVERIFIED_PAYMENTS_PATH = "/orders/{order_id}/payments"
# UNVERIFIED: confirm in Cashfree sandbox
_UNVERIFIED_PAYMENT_EVENTS = {
    "PAYMENT_SUCCESS_WEBHOOK": PaymentEventType.payment_captured,
    "PAYMENT_FAILED_WEBHOOK": PaymentEventType.payment_failed,
    "PAYMENT_USER_DROPPED_WEBHOOK": PaymentEventType.payment_failed,
}
# UNVERIFIED: confirm in Cashfree sandbox (the refund webhook type name and payload shape)
_UNVERIFIED_REFUND_EVENT = "REFUND_STATUS_WEBHOOK"
# UNVERIFIED: confirm in Cashfree sandbox (settlement payload amount key)
_UNVERIFIED_SETTLEMENT_AMOUNT_KEYS = ("settlement_amount", "amount")
# UNVERIFIED: confirm in Cashfree sandbox (vendor webhook payload keys)
_UNVERIFIED_VENDOR_EVENT = "VENDOR_STATUS_UPDATE"
# UNVERIFIED: confirm in Cashfree sandbox (refund_splits schema; off until verified)
_UNVERIFIED_SEND_REFUND_SPLITS = False
# UNVERIFIED: confirm in Cashfree sandbox (payment_group values -> instrument)
_UNVERIFIED_INSTRUMENT = {
    "upi": PaymentInstrument.upi,
    "credit_card": PaymentInstrument.card,
    "debit_card": PaymentInstrument.card,
    "prepaid_card": PaymentInstrument.card,
    "card": PaymentInstrument.card,
    "net_banking": PaymentInstrument.netbanking,
    "netbanking": PaymentInstrument.netbanking,
    "wallet": PaymentInstrument.wallet,
}
# UNVERIFIED: confirm in Cashfree sandbox (create-vendor body: status value and field names)
_UNVERIFIED_VENDOR_INITIAL_STATUS = "ACTIVE"
# UNVERIFIED: confirm in Cashfree sandbox (HTTP status meaning "vendor/refund already exists")
_UNVERIFIED_ALREADY_EXISTS_STATUS = 409
# UNVERIFIED: confirm in Cashfree sandbox (minimum order expiry)
_UNVERIFIED_MIN_EXPIRY_SECONDS = 900

_PAYMENT_STATUS = {
    "SUCCESS": LedgerStatus.captured,
    "FAILED": LedgerStatus.failed,
    "CANCELLED": LedgerStatus.failed,
    "VOID": LedgerStatus.failed,
    "USER_DROPPED": LedgerStatus.failed,
    "PENDING": LedgerStatus.created,
    "NOT_ATTEMPTED": LedgerStatus.created,
    "FLAGGED": LedgerStatus.created,  # held for review: money has not been confirmed
}
_RANK = {LedgerStatus.captured: 2, LedgerStatus.created: 1, LedgerStatus.failed: 0}
_REFUND_STATUS = {
    "SUCCESS": RefundStatus.processed,
    "CANCELLED": RefundStatus.failed,
    "REJECTED": RefundStatus.failed,
    "PENDING": RefundStatus.created,
    "PENDING_APPROVAL": RefundStatus.created,
    "ONHOLD": RefundStatus.created,
}
_VENDOR_STATUS = {
    "IN_BENE_CREATION": OnboardingStatus.pending,
    "IN_KYC_REVIEW": OnboardingStatus.pending,
    "ACTIVE": OnboardingStatus.active,
    "ACTION_REQUIRED": OnboardingStatus.needs_action,
    "BENE_CREATION_FAILED": OnboardingStatus.needs_action,
    "ON_HOLD": OnboardingStatus.suspended,
    "BLOCKED": OnboardingStatus.suspended,
    "DELETED": OnboardingStatus.rejected,
}
_VENDOR_REQUIREMENT = {
    "ACTION_REQUIRED": "The payment provider needs more information. Re-submit your KYC details.",
    "BENE_CREATION_FAILED": "The bank account or UPI id could not be verified. Re-submit the correct details.",
    "ON_HOLD": "Payouts to your account are on hold. Contact support.",
    "BLOCKED": "Your payout account was blocked by the payment provider. Contact support.",
    "DELETED": "Your payout account was removed. Register again with correct details.",
    "IN_KYC_REVIEW": "Your KYC details are being reviewed.",
    "IN_BENE_CREATION": "Your payout account is being set up.",
}

_ORDER_ID = re.compile(r"[A-Za-z0-9_-]{3,45}")
_DEC_TOKEN = uuid.uuid4().hex


def _sentinel(value: Decimal) -> str:
    return f"@@{_DEC_TOKEN}:{format(value, 'f')}@@"


def _prepare(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _sentinel(value)
    if isinstance(value, dict):
        return {k: _prepare(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_prepare(v) for v in value]
    return value


def dumps_json(body: Mapping[str, Any]) -> bytes:
    """JSON with ``Decimal`` emitted as exact numbers (no float round trip)."""

    text = json.dumps(_prepare(dict(body)), separators=(",", ":"))
    text = re.sub(rf'"@@{_DEC_TOKEN}:(-?\d+(?:\.\d+)?)@@"', r"\1", text)
    return text.encode()


def _uuid_for(namespace: str, value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"salon-platform:{namespace}:{value}"))


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _phone(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        raise ValidationError("Add a 10-digit phone number to your profile to pay online")
    return digits[-10:]


class CashfreeGateway(PaymentGateway):
    """Cashfree PG + Easy Split implementation of the payment port."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._client_id = settings.cashfree_client_id or ""
        self._secret = (
            settings.cashfree_client_secret.get_secret_value() if settings.cashfree_client_secret else ""
        )
        self._environment = settings.cashfree_environment
        self._base_url = _BASE_URL[settings.cashfree_environment]
        self._api_version = settings.cashfree_api_version
        self._easy_split = settings.cashfree_easy_split_enabled
        self._currency = settings.payment_currency
        self._intent_ttl = settings.payment_intent_ttl_seconds
        self._settlement_model = SettlementModel(settings.payment_settlement_model)
        self._return_url = settings.cashfree_return_url
        self._tolerance = settings.cashfree_webhook_tolerance_seconds
        self._webhook_version = settings.cashfree_webhook_version
        self._timeout = settings.payment_provider_timeout_seconds
        base = str(settings.public_api_base_url).rstrip("/") if settings.public_api_base_url else ""
        self._notify_url = f"{base}/v1/webhooks/{PROVIDER}" if base.startswith("https://") else None
        self._client = client

    # ------------------------------------------------------------------ identity
    @property
    def provider_name(self) -> str:
        return PROVIDER

    def supports(self, capability: GatewayCapability) -> bool:
        if capability in {
            GatewayCapability.online_collection,
            GatewayCapability.refunds,
            GatewayCapability.server_status_refresh,
        }:
            return True
        if capability in {
            GatewayCapability.split_settlement,
            GatewayCapability.linked_accounts,
            GatewayCapability.vendor_kyc,
        }:
            return self._easy_split
        return False  # callback_signature: Cashfree has none

    def client_config(self) -> ClientConfig:
        return ClientConfig(
            enabled=True,
            provider=PROVIDER,
            public_key=None,
            currency=self._currency,
            settlement_model=self._settlement_model,
        )

    def deterministic_order_ref(self, intent_reference: str) -> str | None:
        if not _ORDER_ID.fullmatch(intent_reference):
            raise ValueError("intent_reference is not a valid Cashfree order id")
        return intent_reference

    def deterministic_refund_ref(self, refund_id: str) -> str | None:
        return "rf" + refund_id.replace("-", "")  # 34 chars, within Cashfree's 3-40

    # ---------------------------------------------------------------------- http
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=5.0))
        return self._client

    @measure_external("cashfree")
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
        not_found_ok: bool = False,
    ) -> Any:
        headers = {
            "x-client-id": self._client_id,
            "x-client-secret": self._secret,
            "x-api-version": self._api_version,
            "accept": "application/json",
        }
        content = None
        if json_body is not None:
            headers["content-type"] = "application/json"
            content = dumps_json(json_body)
        if idempotency_key:
            headers["x-idempotency-key"] = idempotency_key
        try:
            response = await self._http().request(
                method, f"{self._base_url}{path}", content=content, headers=headers
            )
        except httpx.HTTPError as exc:
            logger.warning("Payment provider unreachable: %s %s", method, path.split("?")[0])
            raise PaymentOutcomeUnknownError("Payment provider is unreachable") from exc
        if response.status_code == 404 and not_found_ok:
            return None
        if response.status_code >= 400:
            code = None
            try:
                code = (json.loads(response.content) or {}).get("code")
            except (ValueError, AttributeError):
                pass
            logger.warning(
                "Payment provider rejected %s %s: status=%s code=%s",
                method, path.split("?")[0], response.status_code, code,
            )
            error_cls = PaymentOutcomeUnknownError if response.status_code >= 500 else PaymentProviderError
            raise error_cls(
                "Payment provider rejected the request",
                {"provider_status": response.status_code, "provider_code": str(code)[:60] if code else None},
            )
        try:
            return json.loads(response.content, parse_float=Decimal)
        except ValueError as exc:
            raise PaymentProviderError("Payment provider returned an invalid response") from exc

    # -------------------------------------------------------------------- intents
    async def create_payment_intent(self, request: PaymentIntentRequest) -> PaymentIntent:
        order_id = self.deterministic_order_ref(request.intent_reference)
        if request.amount.amount < 1:
            raise ValueError("Cashfree minimum order amount is 1.00")
        phone = _phone(request.customer_phone)  # before any HTTP call
        if (
            self._settlement_model is SettlementModel.platform_collect
            and self._easy_split
            and not request.settlement_account_ref
        ):
            raise PaymentCapabilityError("The salon has no active settlement account")
        expires_at = request.expires_at or datetime.now(UTC) + timedelta(
            seconds=max(self._intent_ttl, _UNVERIFIED_MIN_EXPIRY_SECONDS)
        )
        customer: dict[str, Any] = {
            "customer_id": re.sub(r"[^A-Za-z0-9_-]", "", request.customer_id or "guest")[:50] or "guest",
            "customer_phone": phone,
        }
        if request.customer_email:
            customer["customer_email"] = request.customer_email
        if request.customer_name:
            customer["customer_name"] = request.customer_name[:100]
        meta: dict[str, Any] = {}
        if self._notify_url:
            meta["notify_url"] = self._notify_url
        if self._return_url:
            meta["return_url"] = self._return_url[:250]
        body: dict[str, Any] = {
            "order_id": order_id,
            "order_amount": request.amount.amount,
            "order_currency": request.currency,
            "customer_details": customer,
            "order_expiry_time": expires_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_note": f"Booking {request.booking_id}"[:200],
        }
        if meta:
            body["order_meta"] = meta
        if request.settlement_account_ref:
            # The vendor's share; the remainder (the platform commission) settles to the
            # platform. Cashfree's PG fee is borne by the platform.
            body["order_splits"] = [
                {
                    "vendor_id": request.settlement_account_ref,
                    "amount": (request.amount - request.platform_fee).amount,
                }
            ]
        data = await self._request(
            "POST", "/orders", json_body=body, idempotency_key=_uuid_for("order", order_id)
        )
        return self._to_intent(data, request, order_id)

    async def fetch_intent(self, order_ref: str, request: PaymentIntentRequest) -> PaymentIntent | None:
        data = await self._request("GET", f"/orders/{order_ref}", not_found_ok=True)
        if data is None:
            return None
        if str(data.get("order_status")) in {"EXPIRED", "TERMINATED", "TERMINATION_REQUESTED"}:
            return None
        return self._to_intent(data, request, order_ref)

    def _to_intent(self, data: Mapping[str, Any], request: PaymentIntentRequest, order_id: str) -> PaymentIntent:
        try:
            if str(data["order_id"]) != order_id:
                raise PaymentProviderError("Payment provider returned a different order")
            session_id = str(data["payment_session_id"])
            amount = _decimal(data.get("order_amount", request.amount.amount))
        except (KeyError, ArithmeticError) as exc:
            raise PaymentProviderError("Payment provider returned an invalid order") from exc
        expiry = data.get("order_expiry_time")
        expires_at = request.expires_at
        if isinstance(expiry, str):
            try:
                expires_at = datetime.fromisoformat(expiry)
            except ValueError:
                pass
        return PaymentIntent(
            provider=PROVIDER,
            order_ref=order_id,
            intent_reference=request.intent_reference,
            amount=Money(amount),
            currency=str(data.get("order_currency") or request.currency),
            client_payload={
                "payment_session_id": session_id,
                "order_id": order_id,
                "environment": self._environment,
            },
            expires_at=expires_at,
        )

    # ------------------------------------------------------------- verification
    def verify_payment_callback(self, callback: PaymentCallback) -> bool:
        return False  # the SDK callback carries no signature and is never proof

    def verify_webhook_signature(self, raw_body: bytes, headers: Mapping[str, str]) -> bool:
        signature = header(headers, "x-webhook-signature")
        timestamp = header(headers, "x-webhook-timestamp")
        if not signature or not timestamp or not self._secret:
            return False
        try:
            stamp = int(timestamp)
        except ValueError:
            return False
        seconds = stamp / 1000 if stamp > 10**11 else stamp  # UNVERIFIED: ms vs s
        if abs(time.time() - seconds) > self._tolerance:
            return False  # replay window
        digest = hmac.new(self._secret.encode(), timestamp.encode() + raw_body, hashlib.sha256).digest()
        expected = base64.b64encode(digest)
        return hmac.compare_digest(expected, signature.encode("utf-8", "ignore"))

    def parse_event(self, raw_body: bytes, headers: Mapping[str, str]) -> PaymentEvent:
        try:
            document = json.loads(raw_body, parse_float=Decimal)
            raw_type = str(document["type"])
            data = document.get("data") or {}
            if not isinstance(data, dict):
                raise TypeError("data must be an object")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Unparseable webhook body") from exc
        digest = hashlib.sha256(raw_body).hexdigest()
        version = header(headers, "x-webhook-version")
        if version and version != self._webhook_version:
            logger.warning("Cashfree webhook version %s differs from configured", version[:20])

        def ignored() -> PaymentEvent:
            return PaymentEvent(PROVIDER, f"{raw_type}:{digest}"[:200], PaymentEventType.ignored, raw_type)

        if raw_type in _UNVERIFIED_PAYMENT_EVENTS:
            order = data.get("order") or {}
            payment = data.get("payment") or {}
            payment_id = payment.get("cf_payment_id")
            if payment_id is None or not order.get("order_id"):
                return ignored()
            failed = _UNVERIFIED_PAYMENT_EVENTS[raw_type] is PaymentEventType.payment_failed
            status = str(payment.get("payment_status") or "")
            error = payment.get("error_details") or {}
            return PaymentEvent(
                provider=PROVIDER,
                event_id=f"{raw_type}:{payment_id}",
                event_type=_UNVERIFIED_PAYMENT_EVENTS[raw_type],
                raw_type=raw_type,
                payment_ref=str(payment_id),
                order_ref=str(order["order_id"]),
                amount=Money(_decimal(payment["payment_amount"])) if payment.get("payment_amount") is not None else None,
                currency=payment.get("payment_currency"),
                instrument=_UNVERIFIED_INSTRUMENT.get(str(payment.get("payment_group") or "").lower()),
                failure_code=(
                    str(error.get("error_code") or status or "failed").lower() if failed else None
                ),
            )
        if raw_type == _UNVERIFIED_REFUND_EVENT:
            refund = data.get("refund") or {}
            ours = refund.get("refund_id")
            status = _REFUND_STATUS.get(str(refund.get("refund_status")))
            if not ours or status is None or status is RefundStatus.created:
                return ignored()
            return PaymentEvent(
                provider=PROVIDER,
                event_id=f"refund:{ours}:{refund.get('refund_status')}",
                event_type=(
                    PaymentEventType.refund_processed
                    if status is RefundStatus.processed
                    else PaymentEventType.refund_failed
                ),
                raw_type=raw_type,
                refund_ref=str(ours),
                order_ref=refund.get("order_id"),
                amount=Money(_decimal(refund["refund_amount"])) if refund.get("refund_amount") is not None else None,
                failure_code=None if status is RefundStatus.processed else str(refund.get("refund_status")).lower(),
            )
        if raw_type == _UNVERIFIED_VENDOR_EVENT:
            vendor = data.get("vendor_id")
            mapped = _VENDOR_STATUS.get(str(data.get("updated_status")))
            if not vendor or mapped is None:
                return ignored()
            return PaymentEvent(
                provider=PROVIDER,
                event_id=f"{raw_type}:{digest}"[:200],
                event_type=PaymentEventType.account_updated,
                raw_type=raw_type,
                account_ref=str(vendor),
                onboarding_status=mapped,
            )
        if raw_type.startswith("VENDOR_SETTLEMENT_"):
            vendor = data.get("vendor_id")
            amount = next((data[k] for k in _UNVERIFIED_SETTLEMENT_AMOUNT_KEYS if data.get(k) is not None), None)
            if not vendor:
                return ignored()
            return PaymentEvent(
                provider=PROVIDER,
                event_id=f"{raw_type}:{digest}"[:200],
                event_type=PaymentEventType.settlement_updated,
                raw_type=raw_type,
                account_ref=str(vendor),
                amount=Money(_decimal(amount)) if amount is not None else None,
                settlement_status=raw_type.removeprefix("VENDOR_SETTLEMENT_").lower(),
            )
        return ignored()

    # -------------------------------------------------------------------- fetches
    async def fetch_payment(
        self, *, payment_ref: str | None = None, order_ref: str | None = None
    ) -> ProviderPayment | None:
        if not order_ref:
            raise PaymentCapabilityError("Cashfree payments are looked up by order id")
        order = await self._request("GET", f"/orders/{order_ref}", not_found_ok=True)
        if order is None:
            return None
        if str(order.get("order_id")) != order_ref:
            raise PaymentProviderError("Payment provider returned a different order")
        listing = await self._request(
            "GET", _UNVERIFIED_PAYMENTS_PATH.format(order_id=order_ref), not_found_ok=True
        )
        payments = [self._to_payment(item, order_ref) for item in (listing or [])]
        if payment_ref:
            payments = [p for p in payments if p.payment_ref == payment_ref]
        if not payments:
            return None
        return max(payments, key=lambda p: _RANK[p.status])

    @staticmethod
    def _to_payment(item: Mapping[str, Any], order_ref: str) -> ProviderPayment:
        try:
            if item.get("order_id") not in (None, order_ref):
                raise PaymentProviderError("Payment provider returned a payment of another order")
            status = _PAYMENT_STATUS.get(str(item.get("payment_status")), LedgerStatus.created)
            error = item.get("error_details") or {}
            return ProviderPayment(
                provider=PROVIDER,
                payment_ref=str(item["cf_payment_id"]),
                order_ref=order_ref,
                status=status,
                amount=Money(_decimal(item["payment_amount"])),
                currency=str(item.get("payment_currency") or "INR"),
                instrument=_UNVERIFIED_INSTRUMENT.get(str(item.get("payment_group") or "").lower()),
                failure_code=(
                    str(error.get("error_code") or item.get("payment_status")).lower()[:120]
                    if status is LedgerStatus.failed
                    else None
                ),
            )
        except (KeyError, ArithmeticError, ValueError) as exc:
            raise PaymentProviderError("Payment provider returned an invalid payment") from exc

    # -------------------------------------------------------------------- refunds
    async def refund(self, request: RefundRequest) -> RefundResult:
        if not request.order_ref or not request.refund_ref:
            raise ValueError("Cashfree refunds need the order id and our refund id")
        body: dict[str, Any] = {
            "refund_id": request.refund_ref,
            "refund_amount": request.amount.amount,
            "refund_note": (request.reason or "Refund")[:100],
            "refund_speed": "STANDARD",
        }
        if _UNVERIFIED_SEND_REFUND_SPLITS and request.settlement_account_ref:
            body["refund_splits"] = [
                {
                    "vendor_id": request.settlement_account_ref,
                    "amount": (request.amount - request.commission_reversal).amount,
                }
            ]
        try:
            data = await self._request(
                "POST",
                f"/orders/{request.order_ref}/refunds",
                json_body=body,
                idempotency_key=_uuid_for("refund", request.refund_ref),
            )
        except PaymentProviderError as exc:
            if (exc.details or {}).get("provider_status") == _UNVERIFIED_ALREADY_EXISTS_STATUS:
                existing = await self.fetch_refund(
                    refund_ref=request.refund_ref, order_ref=request.order_ref, payment_ref=None
                )
                if existing is not None:
                    return existing
            raise
        return self._to_refund(data, request.refund_ref, request.payment_ref)

    async def fetch_refund(
        self, *, refund_ref: str, order_ref: str | None, payment_ref: str | None
    ) -> RefundResult | None:
        if not order_ref:
            raise PaymentCapabilityError("Cashfree refunds are looked up by order id")
        data = await self._request(
            "GET", f"/orders/{order_ref}/refunds/{refund_ref}", not_found_ok=True
        )
        if data is None:
            return None
        return self._to_refund(data, refund_ref, payment_ref)

    @staticmethod
    def _to_refund(data: Mapping[str, Any], refund_ref: str, payment_ref: str | None) -> RefundResult:
        try:
            if str(data.get("refund_id", refund_ref)) != refund_ref:
                raise PaymentProviderError("Payment provider returned a different refund")
            raw_status = str(data.get("refund_status"))
            return RefundResult(
                provider=PROVIDER,
                refund_ref=refund_ref,
                status=_REFUND_STATUS.get(raw_status, RefundStatus.created),
                amount=Money(_decimal(data["refund_amount"])),
                payment_ref=payment_ref,
                failure_code=(
                    "onhold" if raw_status == "ONHOLD"
                    else raw_status.lower() if _REFUND_STATUS.get(raw_status) is RefundStatus.failed
                    else None
                ),
            )
        except (KeyError, ArithmeticError) as exc:
            raise PaymentProviderError("Payment provider returned an invalid refund") from exc

    # ------------------------------------------------------- settlement accounts
    @staticmethod
    def _vendor_body(request: SettlementAccountRequest) -> dict[str, Any]:
        # UNVERIFIED: confirm in Cashfree sandbox (every key below)
        body: dict[str, Any] = {
            "vendor_id": request.vendor_ref,
            "status": _UNVERIFIED_VENDOR_INITIAL_STATUS,
            "name": request.legal_name,
            "email": request.email,
            "phone": request.phone,
            "verify_account": True,
            "kyc_details": {
                "account_type": request.account_type,
                "business_type": request.business_type,
                "pan": request.pan,
            },
        }
        if request.bank_account_number:
            body["bank"] = {
                "account_number": request.bank_account_number,
                "account_holder": request.legal_name,
                "ifsc": request.ifsc,
            }
        elif request.upi_id:
            body["upi"] = {"vpa": request.upi_id, "account_holder": request.legal_name}
        return body

    async def register_settlement_account(
        self, request: SettlementAccountRequest
    ) -> SettlementAccount:
        if not self._easy_split:
            raise PaymentCapabilityError("Linked accounts require Easy Split to be enabled")
        if not request.vendor_ref:
            raise ValueError("A persisted vendor reference is required")
        try:
            data = await self._request(
                "POST",
                "/easy-split/vendors",
                json_body=self._vendor_body(request),
                idempotency_key=_uuid_for("vendor", request.vendor_ref),
            )
        except PaymentProviderError as exc:
            if (exc.details or {}).get("provider_status") == _UNVERIFIED_ALREADY_EXISTS_STATUS:
                return await self.get_settlement_account(request.vendor_ref)
            raise
        return self._to_account(data, request.vendor_ref)

    async def get_settlement_account(self, account_ref: str) -> SettlementAccount:
        if not self._easy_split:
            raise PaymentCapabilityError("Linked accounts require Easy Split to be enabled")
        data = await self._request("GET", f"/easy-split/vendors/{account_ref}")
        return self._to_account(data, account_ref)

    @staticmethod
    def _to_account(data: Mapping[str, Any], vendor_ref: str) -> SettlementAccount:
        raw = str(data.get("status"))
        status = _VENDOR_STATUS.get(raw, OnboardingStatus.pending)
        requirement = _VENDOR_REQUIREMENT.get(raw)
        return SettlementAccount(
            provider=PROVIDER,
            account_ref=str(data.get("vendor_id") or vendor_ref),
            onboarding_status=status,
            requirements=(requirement,) if requirement and status is not OnboardingStatus.active else (),
        )


def create_gateway(settings: Settings) -> PaymentGateway:
    """Factory discovered by ``resolver.build_gateway``."""

    return CashfreeGateway(settings)
