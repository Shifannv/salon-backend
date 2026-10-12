"""Cashfree adapter, config rules and webhook routing. No network: httpx.MockTransport only.

Evidence level: tested locally. Nothing here proves behaviour against the real provider.
"""

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from app.api import deps
from app.api.v1.routes import webhooks
from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentIntentRequest,
    RefundRequest,
    SettlementAccountRequest,
)
from app.core.config import Settings
from app.core.exceptions import (
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
    register_exception_handlers,
)
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    OnboardingStatus,
    PaymentEventType,
    RefundStatus,
    WebhookDomain,
)
from app.domain.value_objects.money import Money
from app.infrastructure.payments import cashfree as cf
from app.infrastructure.payments import razorpay as rzp
from app.infrastructure.payments.resolver import PaymentGatewayResolver

SECRET = "cf_client_secret_test"
APP_ROOT = Path(__file__).resolve().parents[2] / "app"


SUB_WH = "sub-webhook-secret-0123456789abcdef0123456789"
SUB = {
    "subscription_provider": "razorpay",
    "subscription_razorpay_key_id": "rzp_test_sub",
    "subscription_razorpay_key_secret": "sub-key-secret",
    "subscription_razorpay_webhook_secret": SUB_WH,
    "subscription_grace_days": 3,
}


def cf_settings(**kw) -> Settings:
    values = {
        "_env_file": None, "environment": "test", "payment_provider": "cashfree",
        "cashfree_client_id": "cid", "cashfree_client_secret": SECRET,
        "cashfree_easy_split_enabled": True, "payment_platform_fee_percent": Decimal("10"),
        "payment_commission_base": "online_amount",
    }
    values.update(kw)
    return Settings(**values)


def gateway(handler, **kw) -> cf.CashfreeGateway:
    return cf.CashfreeGateway(
        cf_settings(**kw), httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def sign(body: bytes, ts: str | None = None, secret: str = SECRET) -> dict[str, str]:
    ts = ts or str(int(time.time() * 1000))
    digest = hmac.new(secret.encode(), ts.encode() + body, hashlib.sha256).digest()
    return {"x-webhook-signature": base64.b64encode(digest).decode(), "x-webhook-timestamp": ts,
            "x-webhook-version": "2025-01-01"}


def intent_request(**kw) -> PaymentIntentRequest:
    values = {
        "intent_reference": "pi_" + "a" * 32, "booking_id": "b1", "salon_id": "s1",
        "amount": Money(Decimal("199.99")), "customer_id": "11111111-2222-3333-4444-555555555555",
        "settlement_account_ref": "vendor_1", "platform_fee": Money(Decimal("20.00")),
        "customer_phone": "+91 98765 43210",
    }
    values.update(kw)
    return PaymentIntentRequest(**values)


# ------------------------------------------------------------------ config rules
def test_cashfree_needs_credentials_split_and_commission():
    with pytest.raises(PydanticValidationError, match="CASHFREE_CLIENT_ID"):
        cf_settings(cashfree_client_id=None)
    with pytest.raises(PydanticValidationError, match="CASHFREE_CLIENT_SECRET"):
        cf_settings(cashfree_client_secret=None)
    with pytest.raises(PydanticValidationError, match="EASY_SPLIT"):
        cf_settings(cashfree_easy_split_enabled=False)


def test_commission_has_no_default_for_a_real_provider():
    with pytest.raises(PydanticValidationError, match="PAYMENT_PLATFORM_FEE_PERCENT"):
        cf_settings(payment_platform_fee_percent=None)
    with pytest.raises(PydanticValidationError, match="PAYMENT_COMMISSION_BASE"):
        cf_settings(payment_commission_base=None)
    dormant = Settings(_env_file=None, environment="test")
    assert dormant.payment_platform_fee_percent is None and dormant.payment_commission_base is None


def test_blank_env_values_mean_unset_not_zero():
    s = Settings(_env_file=None, environment="test", payment_platform_fee_percent="",
                 payment_commission_base="")
    assert s.payment_platform_fee_percent is None and s.payment_commission_base is None


def test_live_activation_fails_closed():
    with pytest.raises(PydanticValidationError, match="PAYMENT_ALLOW_LIVE"):
        cf_settings(cashfree_environment="production")
    assert cf_settings(cashfree_environment="production", payment_allow_live=True)
    with pytest.raises(PydanticValidationError, match="PAYMENT_ALLOW_LIVE"):
        Settings(
            _env_file=None, environment="test", payment_provider="razorpay",
            razorpay_key_id="rzp_live_x", razorpay_key_secret="s", razorpay_webhook_secret="w",
            razorpay_route_enabled=True, payment_platform_fee_percent=Decimal("5"),
            payment_commission_base="online_amount")


def test_auto_release_cannot_be_enabled_it_is_not_built():
    with pytest.raises(PydanticValidationError, match="not built"):
        Settings(_env_file=None, environment="test", payment_auto_release_enabled=True)


def test_provider_defaults_stay_none():
    assert Settings(_env_file=None, environment="test").payment_provider == "none"


def test_decoupling_each_provider_named_only_in_its_adapter_and_config():
    for provider, own in (("razorpay", "razorpay.py"), ("cashfree", "cashfree.py")):
        offenders = [
            str(path.relative_to(APP_ROOT))
            for path in APP_ROOT.rglob("*.py")
            if path.name not in {"config.py", own} and provider in path.read_text(encoding="utf-8").lower()
        ]
        assert offenders == [], (provider, offenders)


# -------------------------------------------------------------------- signature
BODY = b'{"type":"PAYMENT_SUCCESS_WEBHOOK","data":{}}'


def test_signature_valid_forged_tampered_and_missing():
    g = cf.CashfreeGateway(cf_settings())
    assert g.verify_webhook_signature(BODY, sign(BODY))
    assert g.verify_webhook_signature(BODY, {k.upper(): v for k, v in sign(BODY).items()})
    assert not g.verify_webhook_signature(BODY, sign(BODY, secret="other"))
    assert not g.verify_webhook_signature(BODY + b" ", sign(BODY))
    headers = sign(BODY)
    headers["x-webhook-signature"] = "!!not-base64!!"
    assert not g.verify_webhook_signature(BODY, headers)
    assert not g.verify_webhook_signature(BODY, {})
    assert not g.verify_webhook_signature(BODY, {"x-webhook-timestamp": "1"})


def test_signature_is_base64_not_hex():
    g = cf.CashfreeGateway(cf_settings())
    ts = str(int(time.time() * 1000))
    hex_sig = hmac.new(SECRET.encode(), ts.encode() + BODY, hashlib.sha256).hexdigest()
    assert not g.verify_webhook_signature(
        BODY, {"x-webhook-signature": hex_sig, "x-webhook-timestamp": ts})


def test_replayed_old_timestamp_is_rejected_even_with_a_valid_signature():
    g = cf.CashfreeGateway(cf_settings(cashfree_webhook_tolerance_seconds=600))
    old = str(int((time.time() - 3600) * 1000))
    assert not g.verify_webhook_signature(BODY, sign(BODY, ts=old))
    old_seconds = str(int(time.time() - 3600))
    assert not g.verify_webhook_signature(BODY, sign(BODY, ts=old_seconds))
    fresh_seconds = str(int(time.time()))
    assert g.verify_webhook_signature(BODY, sign(BODY, ts=fresh_seconds))
    assert not g.verify_webhook_signature(BODY, sign(BODY, ts="not-a-number"))


def test_callback_is_never_proof_and_not_a_capability():
    g = cf.CashfreeGateway(cf_settings())
    assert g.verify_payment_callback(PaymentCallback("o", "p", "anything")) is False
    assert not g.supports(GatewayCapability.callback_signature)
    assert g.supports(GatewayCapability.server_status_refresh)
    assert g.supports(GatewayCapability.vendor_kyc)
    assert not cf.CashfreeGateway(cf_settings(cashfree_easy_split_enabled=True)).supports(
        GatewayCapability.callback_signature)


# ---------------------------------------------------------------- request shapes
async def test_create_order_request_shape_rupees_decimal_and_split():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["raw"] = request.content.decode()
        return httpx.Response(200, json={
            "order_id": "pi_" + "a" * 32, "payment_session_id": "sess_1", "order_amount": 199.99,
            "order_currency": "INR", "order_status": "ACTIVE", "cf_order_id": "9"})

    intent = await gateway(handler).create_payment_intent(intent_request())
    body = json.loads(seen["raw"])
    assert seen["url"] == "https://sandbox.cashfree.com/pg/orders"
    assert seen["headers"]["x-client-id"] == "cid"
    assert seen["headers"]["x-client-secret"] == SECRET
    assert seen["headers"]["x-api-version"] == "2026-01-01"
    uuid_key = seen["headers"]["x-idempotency-key"]
    assert len(uuid_key) == 36
    # a real JSON number with two decimals, not a string and not a float repr artefact
    assert '"order_amount":199.99' in seen["raw"]
    assert '"amount":179.99' in seen["raw"]  # vendor share = 199.99 - 20.00 commission
    assert body["order_id"] == "pi_" + "a" * 32 and body["order_currency"] == "INR"
    assert body["order_splits"] == [{"vendor_id": "vendor_1", "amount": 179.99}]
    assert body["customer_details"]["customer_phone"] == "9876543210"
    assert body["customer_details"]["customer_id"].startswith("11111111")
    assert intent.order_ref == "pi_" + "a" * 32
    assert intent.client_payload["payment_session_id"] == "sess_1"
    assert intent.client_payload["environment"] == "sandbox"
    assert intent.amount.amount == Decimal("199.99")


async def test_create_order_idempotency_key_is_stable_for_the_same_order():
    keys = []

    def handler(request):
        keys.append(request.headers["x-idempotency-key"])
        return httpx.Response(
            200, json={"order_id": json.loads(request.content)["order_id"], "payment_session_id": "s"})

    g = gateway(handler)
    await g.create_payment_intent(intent_request())
    await g.create_payment_intent(intent_request())
    await g.create_payment_intent(intent_request(intent_reference="pi_" + "b" * 32))
    assert keys[0] == keys[1] != keys[2]


async def test_production_base_url():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"order_id": "pi_" + "a" * 32, "payment_session_id": "s"})

    g = gateway(handler, cashfree_environment="production", payment_allow_live=True)
    await g.create_payment_intent(intent_request())
    assert seen["url"].startswith("https://api.cashfree.com/pg/")


async def test_missing_phone_is_rejected_before_any_http_call():
    sent = []
    g = gateway(lambda r: sent.append(r) or httpx.Response(200, json={}))
    with pytest.raises(ValidationError):
        await g.create_payment_intent(intent_request(customer_phone=None))
    assert sent == []


async def test_split_settlement_without_vendor_is_refused_before_http():
    sent = []
    g = gateway(lambda r: sent.append(r) or httpx.Response(200, json={}))
    with pytest.raises(Exception, match="settlement account"):
        await g.create_payment_intent(intent_request(settlement_account_ref=None))
    assert sent == []


async def test_order_mismatch_in_response_is_rejected():
    g = gateway(lambda r: httpx.Response(200, json={"order_id": "someone_elses", "payment_session_id": "s"}))
    with pytest.raises(PaymentProviderError, match="different order"):
        await g.create_payment_intent(intent_request())


async def test_timeout_is_an_unknown_outcome_and_5xx_too_but_4xx_is_definitive():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(PaymentOutcomeUnknownError):
        await gateway(timeout).create_payment_intent(intent_request())
    with pytest.raises(PaymentOutcomeUnknownError):
        await gateway(lambda r: httpx.Response(503, json={})).create_payment_intent(intent_request())
    with pytest.raises(PaymentProviderError) as info:
        await gateway(
            lambda r: httpx.Response(400, json={"message": "secret detail", "code": "order_amount_invalid"})
        ).create_payment_intent(intent_request())
    assert not isinstance(info.value, PaymentOutcomeUnknownError)
    assert "secret" not in info.value.message and "secret" not in json.dumps(info.value.details)


async def test_fetch_intent_returns_none_when_unknown_or_dead():
    ok = gateway(lambda r: httpx.Response(404, json={"message": "nope"}))
    assert await ok.fetch_intent("pi_" + "a" * 32, intent_request()) is None
    dead = gateway(lambda r: httpx.Response(200, json={
        "order_id": "pi_" + "a" * 32, "payment_session_id": "s", "order_status": "EXPIRED"}))
    assert await dead.fetch_intent("pi_" + "a" * 32, intent_request()) is None


# ------------------------------------------------------------------------ fetch
def order_handler(payments, order_status="ACTIVE", order_id="o1"):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/payments"):
            return httpx.Response(200, json=payments)
        return httpx.Response(200, json={"order_id": order_id, "order_status": order_status,
                                         "order_amount": 500.00})
    return handler


def pay(status, pid="1", amount=500.00, **kw):
    return {"cf_payment_id": pid, "payment_status": status, "payment_amount": amount,
            "payment_currency": "INR", "payment_group": "upi", "order_id": "o1", **kw}


@pytest.mark.parametrize(("raw", "expected"), [
    ("SUCCESS", LedgerStatus.captured), ("FAILED", LedgerStatus.failed),
    ("CANCELLED", LedgerStatus.failed), ("VOID", LedgerStatus.failed),
    ("USER_DROPPED", LedgerStatus.failed), ("PENDING", LedgerStatus.created),
    ("NOT_ATTEMPTED", LedgerStatus.created), ("FLAGGED", LedgerStatus.created),
])
async def test_payment_status_mapping(raw, expected):
    observed = await gateway(order_handler([pay(raw)])).fetch_payment(order_ref="o1")
    assert observed.status is expected
    assert observed.amount.amount == Decimal("500.00") and observed.instrument.value == "upi"


async def test_fetch_picks_the_successful_payment_and_ignores_order_paid_flag():
    g = gateway(order_handler([pay("FAILED", "1"), pay("SUCCESS", "2")]))
    assert (await g.fetch_payment(order_ref="o1")).payment_ref == "2"
    # an order that says PAID without a SUCCESS payment row is not trusted
    g = gateway(order_handler([pay("PENDING", "3")], order_status="PAID"))
    assert (await g.fetch_payment(order_ref="o1")).status is LedgerStatus.created


async def test_fetch_no_payments_and_unknown_order_are_none():
    assert await gateway(order_handler([])).fetch_payment(order_ref="o1") is None
    assert await gateway(lambda r: httpx.Response(404, json={})).fetch_payment(order_ref="o1") is None


async def test_fetch_rejects_order_and_payment_ownership_mismatch():
    with pytest.raises(PaymentProviderError, match="different order"):
        await gateway(order_handler([pay("SUCCESS")], order_id="other")).fetch_payment(order_ref="o1")
    with pytest.raises(PaymentProviderError, match="another order"):
        await gateway(order_handler([pay("SUCCESS", order_id="other")])).fetch_payment(order_ref="o1")


async def test_fetch_amount_is_decimal_exact():
    observed = await gateway(order_handler([pay("SUCCESS", amount=199.99)])).fetch_payment(order_ref="o1")
    assert observed.amount.amount == Decimal("199.99")


# ------------------------------------------------------------------------ events
def event_body(kind, data):
    return json.dumps({"type": kind, "event_time": "2026-10-12T10:00:00+05:30", "data": data}).encode()


def test_parse_payment_events():
    g = cf.CashfreeGateway(cf_settings())
    ok = g.parse_event(event_body("PAYMENT_SUCCESS_WEBHOOK", {
        "order": {"order_id": "o1", "order_amount": 500.0},
        "payment": {"cf_payment_id": 77, "payment_status": "SUCCESS", "payment_amount": 500.0,
                    "payment_currency": "INR", "payment_group": "upi"}}), {})
    assert ok.event_type is PaymentEventType.payment_captured
    assert (ok.order_ref, ok.payment_ref, ok.amount.amount) == ("o1", "77", Decimal("500.00"))
    assert ok.event_id == "PAYMENT_SUCCESS_WEBHOOK:77"
    dropped = g.parse_event(event_body("PAYMENT_USER_DROPPED_WEBHOOK", {
        "order": {"order_id": "o1"}, "payment": {"cf_payment_id": 78, "payment_status": "USER_DROPPED"}}), {})
    assert dropped.event_type is PaymentEventType.payment_failed
    assert dropped.failure_code == "user_dropped"


def test_parse_refund_vendor_settlement_and_unknown():
    g = cf.CashfreeGateway(cf_settings())
    done = g.parse_event(event_body("REFUND_STATUS_WEBHOOK", {"refund": {
        "refund_id": "rfabc", "refund_status": "SUCCESS", "refund_amount": 10.5, "order_id": "o1"}}), {})
    assert done.event_type is PaymentEventType.refund_processed and done.refund_ref == "rfabc"
    pending = g.parse_event(event_body("REFUND_STATUS_WEBHOOK", {"refund": {
        "refund_id": "rfabc", "refund_status": "PENDING"}}), {})
    assert pending.event_type is PaymentEventType.ignored
    vendor = g.parse_event(event_body("VENDOR_STATUS_UPDATE", {
        "vendor_id": "sv1", "updated_status": "ACTIVE", "past_status": "IN_KYC_REVIEW"}), {})
    assert vendor.event_type is PaymentEventType.account_updated
    assert vendor.onboarding_status is OnboardingStatus.active and vendor.account_ref == "sv1"
    failed = g.parse_event(event_body("VENDOR_SETTLEMENT_FAILED", {
        "vendor_id": "sv1", "settlement_amount": 90.0}), {})
    assert failed.event_type is PaymentEventType.settlement_updated
    assert failed.settlement_status == "failed" and failed.amount.amount == Decimal("90.00")
    assert g.parse_event(event_body("SOMETHING_NEW", {}), {}).event_type is PaymentEventType.ignored
    with pytest.raises(ValueError):
        g.parse_event(b"not json", {})
    with pytest.raises(ValueError):
        g.parse_event(b'{"type":"X","data":[1]}', {})


def test_vendor_event_ids_differ_for_distinct_deliveries_so_a_flip_back_is_not_a_duplicate():
    g = cf.CashfreeGateway(cf_settings())
    a = g.parse_event(event_body("VENDOR_STATUS_UPDATE", {"vendor_id": "v", "updated_status": "ACTIVE"}), {})
    b = g.parse_event(json.dumps({"type": "VENDOR_STATUS_UPDATE", "event_time": "later",
                                  "data": {"vendor_id": "v", "updated_status": "ACTIVE"}}).encode(), {})
    assert a.event_id != b.event_id


# ----------------------------------------------------------------------- refunds
def refund_request(**kw) -> RefundRequest:
    values = {"payment_ref": "77", "amount": Money(Decimal("25.50")), "idempotency_key": "k",
              "reason": "closed", "order_ref": "o1", "refund_ref": "rf" + "c" * 32,
              "settlement_account_ref": "vendor_1", "commission_reversal": Money(Decimal("2.55"))}
    values.update(kw)
    return RefundRequest(**values)


async def test_refund_request_shape_and_deterministic_ids():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["raw"] = request.content.decode()
        seen["key"] = request.headers["x-idempotency-key"]
        return httpx.Response(200, json={"refund_id": "rf" + "c" * 32, "refund_status": "PENDING",
                                         "refund_amount": 25.5})

    result = await gateway(handler).refund(refund_request())
    assert seen["path"] == "/pg/orders/o1/refunds"
    body = json.loads(seen["raw"])
    assert body["refund_id"] == "rf" + "c" * 32 and '"refund_amount":25.50' in seen["raw"]
    assert body["refund_speed"] == "STANDARD" and "refund_splits" not in body  # UNVERIFIED, off
    assert result.status is RefundStatus.created and result.refund_ref == "rf" + "c" * 32
    assert cf.CashfreeGateway(cf_settings()).deterministic_refund_ref(
        "11111111-2222-3333-4444-555555555555") == "rf11111111222233334444555555555555"


async def test_refund_splits_shape_when_enabled(monkeypatch):
    monkeypatch.setattr(cf, "_UNVERIFIED_SEND_REFUND_SPLITS", True)
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"refund_id": "rf" + "c" * 32, "refund_status": "SUCCESS",
                                         "refund_amount": 25.5})

    result = await gateway(handler).refund(refund_request())
    assert seen["body"]["refund_splits"] == [{"vendor_id": "vendor_1", "amount": 22.95}]
    assert result.status is RefundStatus.processed


async def test_refund_onhold_is_pending_and_flagged():
    g = gateway(lambda r: httpx.Response(200, json={
        "refund_id": "rf" + "c" * 32, "refund_status": "ONHOLD", "refund_amount": 25.5}))
    result = await g.refund(refund_request())
    assert result.status is RefundStatus.created and result.failure_code == "onhold"


async def test_refund_duplicate_resolves_to_the_existing_refund():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(409, json={"code": "refund_already_exists"})
        return httpx.Response(200, json={"refund_id": "rf" + "c" * 32, "refund_status": "SUCCESS",
                                         "refund_amount": 25.5})

    result = await gateway(handler).refund(refund_request())
    assert result.status is RefundStatus.processed


async def test_refund_timeout_is_unknown_and_other_refund_id_rejected():
    def timeout(request):
        raise httpx.ConnectTimeout("t", request=request)

    with pytest.raises(PaymentOutcomeUnknownError):
        await gateway(timeout).refund(refund_request())
    g = gateway(lambda r: httpx.Response(200, json={"refund_id": "zzz", "refund_status": "SUCCESS",
                                                    "refund_amount": 25.5}))
    with pytest.raises(PaymentProviderError, match="different refund"):
        await g.refund(refund_request())
    with pytest.raises(ValueError):
        await g.refund(refund_request(refund_ref=None))


async def test_fetch_refund_by_our_id():
    g = gateway(lambda r: httpx.Response(200, json={"refund_id": "rf" + "c" * 32,
                                                    "refund_status": "CANCELLED", "refund_amount": 25.5}))
    result = await g.fetch_refund(refund_ref="rf" + "c" * 32, order_ref="o1", payment_ref=None)
    assert result.status is RefundStatus.failed
    missing = gateway(lambda r: httpx.Response(404, json={}))
    assert await missing.fetch_refund(refund_ref="x", order_ref="o1", payment_ref=None) is None


# ---------------------------------------------------------------- vendor onboarding
def vendor_request(**kw) -> SettlementAccountRequest:
    values = {"salon_id": "s1", "legal_name": "Asha Salon", "vendor_ref": "sv" + "d" * 32 + "g1",
              "email": "owner@example.com", "phone": "9876543210", "account_type": "individual",
              "business_type": "salon", "pan": "ABCDE1234F", "bank_account_number": "123456789012",
              "ifsc": "HDFC0001234"}
    values.update(kw)
    return SettlementAccountRequest(**values)


async def test_vendor_registration_shape_and_status_mapping():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        seen["key"] = request.headers["x-idempotency-key"]
        return httpx.Response(200, json={"vendor_id": "sv" + "d" * 32 + "g1", "status": "IN_KYC_REVIEW"})

    account = await gateway(handler).register_settlement_account(vendor_request())
    assert seen["path"] == "/pg/easy-split/vendors"
    assert seen["body"]["vendor_id"] == "sv" + "d" * 32 + "g1"
    assert seen["body"]["bank"]["ifsc"] == "HDFC0001234" and "upi" not in seen["body"]
    assert seen["body"]["kyc_details"]["pan"] == "ABCDE1234F"
    assert account.onboarding_status is OnboardingStatus.pending
    assert account.requirements and "reviewed" in account.requirements[0]


async def test_vendor_upi_variant_and_existing_vendor_fallback():
    seen = {}

    def handler(request):
        if request.method == "POST":
            seen["body"] = json.loads(request.content)
            return httpx.Response(409, json={"code": "vendor_exists"})
        return httpx.Response(200, json={"vendor_id": "sv" + "d" * 32 + "g1", "status": "ACTIVE"})

    account = await gateway(handler).register_settlement_account(
        vendor_request(bank_account_number=None, ifsc=None, upi_id="asha@okbank"))
    assert seen["body"]["upi"]["vpa"] == "asha@okbank" and "bank" not in seen["body"]
    assert account.onboarding_status is OnboardingStatus.active and account.requirements == ()


@pytest.mark.parametrize(("raw", "state"), [
    ("IN_BENE_CREATION", "pending"), ("ACTION_REQUIRED", "needs_action"),
    ("BENE_CREATION_FAILED", "needs_action"), ("ACTIVE", "active"), ("ON_HOLD", "suspended"),
    ("BLOCKED", "suspended"), ("DELETED", "rejected"),
])
async def test_vendor_status_states_have_actionable_text(raw, state):
    g = gateway(lambda r: httpx.Response(200, json={"vendor_id": "v", "status": raw}))
    account = await g.get_settlement_account("v")
    assert account.onboarding_status.value == state
    assert (account.requirements == ()) == (state == "active")


def test_kyc_fields_never_appear_in_repr():
    text = repr(vendor_request()) + repr(intent_request())
    for secret in ("ABCDE1234F", "123456789012", "HDFC0001234", "owner@example.com", "9876543210",
                   "Asha Salon"):
        assert secret not in text


# ------------------------------------------------------------- resolver / routing
def test_resolver_registry_never_substitutes_a_provider():
    class Fake:
        provider_name = "razorpay"

    resolver = PaymentGatewayResolver(cf_settings())
    assert resolver.for_provider("cashfree").provider_name == "cashfree"
    with pytest.raises(PaymentProviderNotConfiguredError):
        resolver.for_provider("razorpay")  # not independently enabled
    with pytest.raises(PaymentProviderNotConfiguredError):
        resolver.for_provider(None)
    with_extra = PaymentGatewayResolver(cf_settings(), gateways={"razorpay": Fake()})
    assert with_extra.for_provider("razorpay").provider_name == "razorpay"
    assert resolver.resolve().provider_name == "cashfree"


def test_webhook_gateways_are_per_enabled_provider():
    from app.core.exceptions import NotFoundError

    s = cf_settings(**SUB)
    resolver = PaymentGatewayResolver(s)
    assert [d for _, d in resolver.webhook_gateways("cashfree")] == [WebhookDomain.payment]
    assert [d for _, d in resolver.webhook_gateways("razorpay")] == [WebhookDomain.subscription]
    with pytest.raises(NotFoundError):
        resolver.webhook_gateways("stripe")
    with pytest.raises(NotFoundError):
        PaymentGatewayResolver(cf_settings()).webhook_gateways("razorpay")  # no subscription secret


# --------------------------------------------------- simultaneous providers over HTTP
class IntakeRepo:
    def __init__(self):
        self.events = {}
        self.commits = 0

    async def insert_webhook_event(self, **kw):
        key = (kw["provider"], kw["event_id"])
        if key in self.events:
            return None
        self.events[key] = kw
        return f"row-{len(self.events)}"

    async def commit(self):
        self.commits += 1


@pytest.fixture
def both_client():
    """Cashfree as the booking provider, Razorpay verified for subscriptions only."""

    s = cf_settings(payment_webhook_max_body_bytes=4096, **SUB)
    repo = IntakeRepo()
    resolver = PaymentGatewayResolver(s)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(webhooks.router)
    app.dependency_overrides[webhooks.get_session] = lambda: None
    app.dependency_overrides[deps.get_payment_gateway_resolver] = lambda: resolver
    with patch.object(webhooks, "PaymentRepository", lambda session: repo), \
            patch.object(webhooks, "process_in_background", AsyncMock()) as bg, \
            patch.object(webhooks, "settings", s):
        yield TestClient(app), repo, bg


SUCCESS = event_body("PAYMENT_SUCCESS_WEBHOOK", {
    "order": {"order_id": "o1"}, "payment": {"cf_payment_id": 5, "payment_status": "SUCCESS",
                                             "payment_amount": 500.0, "payment_currency": "INR"}})


def test_cashfree_webhook_accepted_replayed_and_forged(both_client):
    http, repo, bg = both_client
    ok = http.post("/webhooks/cashfree", content=SUCCESS, headers=sign(SUCCESS))
    assert ok.json() == {"status": "accepted"} and bg.call_count == 1
    again = http.post("/webhooks/cashfree", content=SUCCESS, headers=sign(SUCCESS))
    assert again.json() == {"status": "duplicate"} and bg.call_count == 1
    forged = http.post("/webhooks/cashfree", content=SUCCESS, headers=sign(SUCCESS, secret="evil"))
    assert forged.status_code == 400 and len(repo.events) == 1
    # A late provider retry keeps its original timestamp; a valid signature plus event-id dedupe is the
    # replay defence, so a 2-hour-old delivery is a harmless duplicate, not a rejection.
    late_retry = http.post("/webhooks/cashfree", content=SUCCESS,
                           headers=sign(SUCCESS, ts=str(int((time.time() - 7200) * 1000))))
    assert late_retry.status_code == 200 and late_retry.json() == {"status": "duplicate"}
    ancient = http.post("/webhooks/cashfree", content=SUCCESS,
                        headers=sign(SUCCESS, ts=str(int((time.time() - 90000) * 1000))))
    assert ancient.status_code == 400


def test_razorpay_secret_cannot_authorise_a_cashfree_path_and_vice_versa(both_client):
    http, repo, _ = both_client
    rz_body = b'{"event":"subscription.charged","payload":{}}'
    rz_sig = hmac.new(SUB_WH.encode(), rz_body, hashlib.sha256).hexdigest()
    # subscription secret on the cashfree path: rejected, nothing stored
    r = http.post("/webhooks/cashfree", content=rz_body, headers={"x-razorpay-signature": rz_sig})
    assert r.status_code == 400
    # cashfree signature on the razorpay path: rejected
    r = http.post("/webhooks/razorpay", content=SUCCESS, headers=sign(SUCCESS))
    assert r.status_code == 400 and repo.events == {}


def test_subscription_domain_event_is_stored_for_the_billing_handler_not_booking_money(both_client):
    http, repo, bg = both_client
    body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {
        "id": "pay_9", "order_id": "o1", "amount": 50000, "currency": "INR"}}}}).encode()
    sig = hmac.new(SUB_WH.encode(), body, hashlib.sha256).hexdigest()
    r = http.post("/webhooks/razorpay", content=body,
                  headers={"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_sub"})
    assert r.status_code == 200 and r.json() == {"status": "accepted"}
    stored = next(iter(repo.events.values()))
    assert stored["provider"] == "razorpay" and stored["event_type"] == "subscription"
    assert stored["status"] == "received" and stored["normalized"]["domain"] == "subscription"
    assert stored["normalized"]["kind"] == "payment_captured"
    assert stored["normalized"]["amount"] == "500.00"
    assert bg.call_count == 1  # processed by the subscription handler; payment code never sees it
    unknown = json.dumps({"event": "subscription.charged", "payload": {}}).encode()
    sig2 = hmac.new(SUB_WH.encode(), unknown, hashlib.sha256).hexdigest()
    r2 = http.post("/webhooks/razorpay", content=unknown,
                   headers={"x-razorpay-signature": sig2, "x-razorpay-event-id": "evt_unknown"})
    assert r2.status_code == 200 and r2.json() == {"status": "ignored"} and bg.call_count == 1


def test_same_event_reference_is_deduped_per_provider_not_globally(both_client):
    http, repo, _ = both_client
    http.post("/webhooks/cashfree", content=SUCCESS, headers=sign(SUCCESS))
    body = b'{"event":"subscription.charged"}'
    sig = hmac.new(SUB_WH.encode(), body, hashlib.sha256).hexdigest()
    http.post("/webhooks/razorpay", content=body,
              headers={"x-razorpay-signature": sig, "x-razorpay-event-id": "PAYMENT_SUCCESS_WEBHOOK:5"})
    assert {k[0] for k in repo.events} == {"cashfree", "razorpay"}


def test_unknown_valid_event_is_acked_200_and_unknown_provider_404(both_client):
    http, _repo, bg = both_client
    body = event_body("SOMETHING_NEW", {})
    r = http.post("/webhooks/cashfree", content=body, headers=sign(body))
    assert r.status_code == 200 and r.json() == {"status": "ignored"} and bg.call_count == 0
    assert http.post("/webhooks/stripe", content=body).status_code == 404


def test_body_is_bounded_even_without_content_length(both_client):
    http, repo, _ = both_client

    def chunks():
        for _ in range(10):
            yield b"x" * 1024

    r = http.post("/webhooks/cashfree", content=chunks(), headers=sign(b""))
    assert r.status_code == 413 and repo.events == {}


def test_razorpay_booking_adapter_still_works_alongside():
    s = Settings(
        _env_file=None, environment="test", payment_provider="razorpay", razorpay_key_id="k",
        razorpay_key_secret="s", razorpay_webhook_secret="w", razorpay_route_enabled=True,
        payment_platform_fee_percent=Decimal("5"), payment_commission_base="booking_total")
    g = rzp.RazorpayGateway(s)
    assert g.supports(GatewayCapability.callback_signature)
    assert not g.supports(GatewayCapability.server_status_refresh)
    assert PaymentGatewayResolver(s).resolve().provider_name == "razorpay"
