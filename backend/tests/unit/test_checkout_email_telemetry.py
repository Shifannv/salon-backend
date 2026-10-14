"""Checkout math, provider-disabled isolation, email replay and privacy regressions."""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.application.use_cases.payments import BookingPaymentUseCases
from app.core.config import Settings
from app.core.exceptions import PaymentProviderNotConfiguredError, ServiceUnavailableError
from app.core.telemetry import scrub_sentry
from app.domain.services.checkout import PAY_AT_SALON_INSTRUCTIONS, checkout_quote
from app.infrastructure.email.resend import ResendEmailGateway
from app.infrastructure.payments.resolver import PaymentGatewayResolver, build_gateway
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway
from app.main import create_app


@pytest.mark.parametrize("amount,fee,total",[("250","12.50","262.50"),("0.10","0.01","0.11"),("0","0.00","0.00"),("999.99","50.00","1049.99")])
def test_online_charge_uses_decimal_half_up(amount,fee,total):
    quote=checkout_quote(Decimal(amount),"PAY_ONLINE")
    assert quote["online_processing_charge"]==Decimal(fee) and quote["total_payable"]==Decimal(total)
    assert quote["charge_label"]=="Online payment processing charge"


def test_pay_at_salon_is_fee_free_with_exact_instructions():
    quote=checkout_quote(Decimal("250"),"PAY_AT_SALON")
    assert quote["online_processing_charge"]==0 and quote["total_payable"]==Decimal("250")
    assert quote["instructions"]==PAY_AT_SALON_INSTRUCTIONS


@pytest.mark.parametrize("amount",[1.1,Decimal("NaN"),Decimal("Infinity"),Decimal("-1")])
def test_invalid_money_is_rejected(amount):
    with pytest.raises(ValueError):
        checkout_quote(amount,"PAY_ONLINE")


async def test_cashfree_disabled_never_builds_adapter_or_calls_provider():
    cfg=Settings(_env_file=None,environment="test",payment_provider="cashfree",cashfree_enabled=False)
    with patch("app.infrastructure.payments.resolver._adapter_module",side_effect=AssertionError("Provider called")):
        resolver=PaymentGatewayResolver(cfg)
        assert not resolver.enabled and build_gateway(cfg).provider_name=="none"
        uc=BookingPaymentUseCases(AsyncMock(),resolver,cfg)
        with pytest.raises(PaymentProviderNotConfiguredError):
            await uc.create_intent(None,"booking-test","idempotency-test",None)
        assert uc.config()["online_payment_unavailable_reason"]=="Online payment coming soon."


async def test_resend_provider_key_is_server_only_and_retries_keep_same_idempotency_key():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={"id":"email-provider-reference"})
    cfg=Settings(_env_file=None,resend_api_key="test-key-only",resend_from_email="Test <no-reply@example.test>",resend_domain_verified=True)
    gateway=ResendEmailGateway(cfg,httpx.MockTransport(handler))
    for _ in range(2):
        assert await gateway.send(recipient="customer@example.test",subject="Test",body="Test message",event_key="booking-confirmation-1")=="email-provider-reference"
    assert calls[0].headers["idempotency-key"]==calls[1].headers["idempotency-key"]
    assert calls[0].headers["authorization"]=="Bearer test-key-only"
    assert "test-key-only" not in calls[0].content.decode()


async def test_only_resend_key_without_verified_sender_makes_no_network_call():
    cfg=Settings(_env_file=None,resend_api_key="test-key-only")
    gateway=ResendEmailGateway(cfg,httpx.MockTransport(lambda r:pytest.fail("Unexpected call")))
    with pytest.raises(ServiceUnavailableError):
        await gateway.send(recipient="customer@example.test",subject="Test",body="Test",event_key="event-1")


async def test_password_reset_delegates_to_supabase_never_mints_tokens():
    cfg=Settings(_env_file=None,password_reset_redirect_url="https://website.example.test/reset-password")
    gateway=SupabaseAuthGateway(cfg)
    gateway._raw_post=AsyncMock(return_value=None)
    assert await gateway.request_password_reset("customer@example.test") is None
    path,body=gateway._raw_post.await_args.args
    assert path.startswith("/auth/v1/recover?redirect_to=") and body=={"email":"customer@example.test"}


def test_sentry_removes_credentials_pii_sql_parameters_and_breadcrumbs():
    unsafe={"request":{"headers":{"authorization":"Bearer private-token"},"data":{"password":"private-password"}},
            "user":{"email":"person@example.test"},"extra":{"RESEND_API_KEY":"test-secret"},
            "breadcrumbs":{"values":[{"message":"private-token"}]},
            "exception":{"values":[{"value":"private-password","stacktrace":{"frames":[{"vars":{"secret":"private-token"},"filename":"app.py"}]}}]},
            "spans":[{"op":"db","description":"select private-token","data":{"password":"private-password"}}]}
    result=json.dumps(scrub_sentry(unsafe))
    for secret in ("private-token","private-password","test-secret","person@example.test"):
        assert secret not in result
    assert "app.py" in result


def test_timing_headers_request_ids_and_validation_do_not_echo_secrets():
    client=TestClient(create_app())
    result=client.get("/health",headers={"X-Request-ID":"known-request-123"})
    assert result.headers["x-request-id"]=="known-request-123"
    assert "app;dur=" in result.headers["server-timing"]
    result=client.post("/v1/bookings/quote",json={"password":"private-password","RESEND_API_KEY":"private-key"})
    assert result.status_code in {401,403,422}
    assert "private-password" not in result.text and "private-key" not in result.text
    result=client.get("/health",headers={"X-Request-ID":"email@example.test"})
    assert "email@example.test" not in result.headers["x-request-id"]
