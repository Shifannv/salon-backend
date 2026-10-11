"""Payment foundation: config rules, dormant gateway, adapter vectors, decoupling, API."""

import hashlib
import hmac
import inspect
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from app.api import deps
from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentGateway,
    PaymentIntentRequest,
    RefundRequest,
)
from app.core.config import Settings
from app.core.exceptions import (
    PaymentCapabilityError,
    PaymentProviderNotConfiguredError,
)
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    PaymentEventType,
    SettlementModel,
    derive_payment_state,
    is_forward_transition,
)
from app.domain.value_objects.money import Money
from app.infrastructure.payments import razorpay as rzp
from app.infrastructure.payments.null import NullPaymentGateway
from app.infrastructure.payments.resolver import PaymentGatewayResolver, build_gateway
from app.main import app

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
SECRET = "whsec_test_secret"
KEY_SECRET = "key_secret_test"


def make_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "test",
        "payment_provider": "razorpay",
        "razorpay_key_id": "rzp_test_key",
        "razorpay_key_secret": KEY_SECRET,
        "razorpay_webhook_secret": SECRET,
        "razorpay_route_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


# ----------------------------------------------------------------- config rules
def test_provider_defaults_to_none():
    settings = Settings(_env_file=None, environment="test")
    assert settings.payment_provider == "none"
    assert settings.payment_settlement_model == "platform_collect"


def test_direct_to_salon_fails_boot_until_per_salon_credentials_exist():
    with pytest.raises(PydanticValidationError, match="direct_to_salon"):
        Settings(_env_file=None, environment="test", payment_settlement_model="direct_to_salon")


def test_configured_provider_needs_credentials():
    with pytest.raises(PydanticValidationError, match="RAZORPAY_KEY_SECRET"):
        make_settings(razorpay_key_secret=None)


def test_platform_collect_requires_route():
    with pytest.raises(PydanticValidationError, match="ROUTE_ENABLED"):
        make_settings(razorpay_route_enabled=False)


def test_unknown_provider_has_no_adapter():
    with pytest.raises(PydanticValidationError, match="no adapter"):
        Settings(_env_file=None, environment="test", payment_provider="nonesuch")


def test_payment_validation_fires_outside_production_too():
    # environment=local would normally skip provider checks; payment checks must not.
    with pytest.raises(PydanticValidationError):
        make_settings(environment="local", razorpay_webhook_secret=None)


# ------------------------------------------------------------- dormant gateway
def test_null_gateway_implements_every_abstract_method_and_refuses_all():
    gateway = NullPaymentGateway()  # instantiation fails if any abstract method is missing
    assert not getattr(NullPaymentGateway, "__abstractmethods__", frozenset())
    for capability in GatewayCapability:
        assert gateway.supports(capability) is False
    for name in PaymentGateway.__abstractmethods__:
        assert name in NullPaymentGateway.__dict__, f"NullPaymentGateway lacks {name}"
    with pytest.raises(PaymentProviderNotConfiguredError):
        gateway.client_config()
    with pytest.raises(PaymentProviderNotConfiguredError):
        gateway.verify_webhook_signature(b"{}", {})


def test_resolver_returns_null_gateway_when_none():
    resolver = PaymentGatewayResolver(Settings(_env_file=None, environment="test"))
    assert resolver.enabled is False
    assert isinstance(resolver.resolve("any-salon"), NullPaymentGateway)


def test_resolver_builds_adapter_by_module_name():
    gateway = build_gateway(make_settings())
    assert gateway.provider_name == "razorpay"


def test_decoupling_razorpay_named_only_in_allowed_files():
    allowed = {"config.py", "razorpay.py"}
    offenders = [
        str(path.relative_to(APP_ROOT))
        for path in APP_ROOT.rglob("*.py")
        if path.name not in allowed and "razorpay" in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []
    resolver_source = (APP_ROOT / "infrastructure/payments/resolver.py").read_text()
    assert "razorpay" not in resolver_source.lower()


# ----------------------------------------------------------- domain helpers
def test_status_ordering_and_derived_state():
    assert is_forward_transition("created", "captured")
    assert is_forward_transition("failed", "captured")  # late capture after expiry is real money
    assert not is_forward_transition("captured", "failed")
    assert not is_forward_transition("authorized", "authorized")
    d = Decimal
    assert derive_payment_state("unpaid", d(0), d(0)).value == "unpaid"
    assert derive_payment_state("unpaid", d(100), d(0)).value == "partially_paid"
    assert derive_payment_state("paid", d(500), d(0)).value == "paid"
    assert derive_payment_state("unpaid", d(500), d(500)).value == "refunded"


# ------------------------------------------------------------ razorpay adapter
def hex_hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def gateway_with(handler, **overrides) -> rzp.RazorpayGateway:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return rzp.RazorpayGateway(make_settings(**overrides), client)


def test_webhook_signature_vectors():
    gateway = rzp.RazorpayGateway(make_settings())
    body = b'{"event":"payment.captured"}'
    good = hex_hmac(SECRET, body)
    assert gateway.verify_webhook_signature(body, {"X-Razorpay-Signature": good})
    assert gateway.verify_webhook_signature(body, {"x-razorpay-signature": good})
    assert not gateway.verify_webhook_signature(body + b" ", {"X-Razorpay-Signature": good})
    assert not gateway.verify_webhook_signature(body, {"X-Razorpay-Signature": "0" * 64})
    assert not gateway.verify_webhook_signature(body, {})


def test_callback_signature_vectors():
    gateway = rzp.RazorpayGateway(make_settings())
    sig = hex_hmac(KEY_SECRET, b"order_1|pay_1")
    assert gateway.verify_payment_callback(PaymentCallback("order_1", "pay_1", sig))
    assert not gateway.verify_payment_callback(PaymentCallback("order_1", "pay_2", sig))
    assert not gateway.verify_payment_callback(PaymentCallback("order_1", "pay_1", ""))


@pytest.mark.parametrize(
    ("major", "paise"),
    [("500.00", 50000), ("0.01", 1), ("199.99", 19999), ("1234.50", 123450), ("0.005", 1)],
)
def test_paise_rounding(major, paise):
    assert rzp.to_paise(Money(Decimal(major))) == paise
    assert rzp.from_paise(paise).amount == Money(Decimal(paise) / 100).amount


async def test_create_intent_sends_paise_receipt_and_transfers():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["path"] = request.url.path
        assert request.headers["authorization"].startswith("Basic ")
        return httpx.Response(200, json={"id": "order_abc"})

    gateway = gateway_with(handler)
    intent = await gateway.create_payment_intent(
        PaymentIntentRequest(
            intent_reference="pi_ref",
            booking_id="b1",
            salon_id="s1",
            amount=Money(Decimal("199.99")),
            settlement_model=SettlementModel.platform_collect,
            settlement_account_ref="acc_1",
            platform_fee=Money(Decimal("10.00")),
        )
    )
    assert seen["path"].endswith("/orders")
    assert seen["body"]["amount"] == 19999
    assert seen["body"]["receipt"] == "pi_ref"
    assert seen["body"]["transfers"][0]["account"] == "acc_1"
    assert seen["body"]["transfers"][0]["amount"] == 18999
    assert intent.order_ref == "order_abc"
    assert intent.client_payload["key_id"] == "rzp_test_key"


async def test_route_intent_without_settlement_account_is_rejected_before_any_http_call():
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"id": "order_x"})

    with pytest.raises(PaymentCapabilityError):
        await gateway_with(handler).create_payment_intent(
            PaymentIntentRequest("pi_r", "b", "s", Money(Decimal("10")))
        )
    assert sent == []


async def test_refund_uses_idempotency_header_and_paise():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        seen["path"] = request.url.path
        return httpx.Response(
            200, json={"id": "rfnd_1", "status": "processed", "amount": 2550, "payment_id": "pay_1"}
        )

    result = await gateway_with(handler).refund(
        RefundRequest("pay_1", Money(Decimal("25.50")), "fixed-key", "closed")
    )
    assert seen["path"].endswith("/payments/pay_1/refund")
    assert seen["body"]["amount"] == 2550
    assert seen["headers"]["x-refund-idempotency"] == "fixed-key"
    assert result.refund_ref == "rfnd_1" and result.status.value == "processed"
    assert result.amount.amount == Decimal("25.50")


async def test_provider_error_never_leaks_body():
    from app.core.exceptions import PaymentProviderError

    def handler(request):
        return httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR", "description": "secret"}})

    with pytest.raises(PaymentProviderError) as info:
        await gateway_with(handler).fetch_payment(payment_ref="pay_1")
    assert "secret" not in info.value.message


async def test_fetch_by_order_picks_most_advanced_payment():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": "pay_a", "status": "failed", "amount": 100, "currency": "INR"},
                    {"id": "pay_b", "status": "captured", "amount": 100, "currency": "INR",
                     "method": "upi", "order_id": "o1"},
                ]
            },
        )

    payment = await gateway_with(handler).fetch_payment(order_ref="o1")
    assert payment.payment_ref == "pay_b" and payment.status is LedgerStatus.captured
    assert payment.instrument.value == "upi"


def test_parse_event_normalises_and_ignores_unknown():
    gateway = rzp.RazorpayGateway(make_settings())
    body = json.dumps(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_1", "order_id": "order_1", "amount": 50000,
                        "currency": "INR", "method": "upi",
                    }
                }
            },
        }
    ).encode()
    event = gateway.parse_event(body, {"X-Razorpay-Event-Id": "evt_1"})
    assert event.event_type is PaymentEventType.payment_captured
    assert event.event_id == "evt_1" and event.amount.amount == Decimal("500.00")
    other = gateway.parse_event(b'{"event":"order.paid"}', {})
    assert other.event_type is PaymentEventType.ignored
    with pytest.raises(ValueError):
        gateway.parse_event(b"not json", {})


def test_capabilities():
    gateway = rzp.RazorpayGateway(make_settings())
    assert gateway.supports(GatewayCapability.online_collection)
    assert gateway.supports(GatewayCapability.refunds)
    assert gateway.supports(GatewayCapability.split_settlement)


# ------------------------------------------------------------ dormant HTTP API
def test_payment_config_is_200_and_disabled_without_provider():
    response = TestClient(app).get("/v1/payments/config")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False and body["currency"] == "INR"
    assert body["public_key"] is None


def test_money_post_without_provider_is_503_with_documented_code():
    from app.api.deps import get_authenticated_session, get_current_actor
    from tests.conftest import make_profile

    saved = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_actor] = lambda: make_profile()
    app.dependency_overrides[get_authenticated_session] = lambda: None
    try:
        response = TestClient(app).post(
            "/v1/bookings/b-1/payments/intent", headers={"Idempotency-Key": "abcdefgh12"}
        )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "payment_provider_not_configured"


def test_webhook_path_404s_when_no_provider_configured():
    assert TestClient(app).post("/v1/webhooks/razorpay", content=b"{}").status_code == 404


def test_payment_endpoints_are_in_openapi():
    paths = app.openapi()["paths"]
    for path in (
        "/v1/payments/config",
        "/v1/bookings/{booking_id}/payments/intent",
        "/v1/bookings/{booking_id}/payments/confirm",
        "/v1/bookings/{booking_id}/payments/cancel",
        "/v1/bookings/{booking_id}/payments",
        "/v1/bookings/{booking_id}/payments/{payment_id}/refund",
        "/v1/salons/me/earnings",
        "/v1/salons/me/settlement-account",
        "/v1/salons/me/settlement-account/register",
        "/v1/salons/me/payout-account/history",
    ):
        assert path in paths, path
    assert "/v1/webhooks/{provider}" not in paths  # dormant by default


def test_create_booking_request_accepts_new_preferences():
    from app.api.v1.schemas.platform import BookingCreateRequest

    for value in ("pay_at_salon", "pay_advance", "pay_full", None):
        BookingCreateRequest(
            salon_id="s", staff_id="t", service_ids=["x"],
            start_datetime="2030-01-01T10:00:00+00:00", customer_name="A",
            payment_preference=value,
        )
    with pytest.raises(PydanticValidationError):
        BookingCreateRequest(
            salon_id="s", staff_id="t", service_ids=["x"],
            start_datetime="2030-01-01T10:00:00+00:00", customer_name="A",
            payment_preference="pay_later",
        )


def test_deps_exposes_domain_typed_factory():
    assert "PaymentGateway" in str(inspect.signature(deps.get_payment_gateway).return_annotation)
