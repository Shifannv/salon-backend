"""Cashfree subscription contract through real HTTP serialization, with no merchant calls."""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from prices import GROWTH_1M
from pydantic import ValidationError as SettingsError
from support_subscription import FakeBillingRepo, owner

from app.application.ports.subscription_provider import (
    ProviderPaymentState,
    SubscriptionEventKind,
    SubscriptionOrderRequest,
)
from app.application.use_cases.subscription_billing import SubscriptionBillingUseCases
from app.core.config import Settings
from app.core.exceptions import PaymentOutcomeUnknownError, PaymentProviderError, ValidationError
from app.domain.value_objects.money import Money
from app.infrastructure.subscriptions.cashfree import CashfreeSubscriptionProvider
from app.infrastructure.subscriptions.resolver import SubscriptionProviderResolver


def settings(**overrides):
    return Settings(
        **{
            "_env_file": None,
            "environment": "test",
            "subscription_provider": "cashfree",
            "subscription_cashfree_client_id": "test-sub-client",
            "subscription_cashfree_client_secret": "test-sub-secret-not-a-real-key",
            "subscription_grace_days": 0,
            "subscription_website_url": "https://salones.example/subscription/checkout",
            **overrides,
        }
    )


def request():
    return SubscriptionOrderRequest(
        receipt="sub_" + uuid4().hex,
        billing_record_id="billing-1",
        salon_id="salon-1",
        plan_id="plan-1",
        amount=Money("279.20"),
        customer_id="owner-1",
        customer_phone="+919876543210",
        return_url="https://salones.example/subscription/checkout?plan=growth_1m",
    )


def order(receipt, amount="279.20"):
    return {
        "order_id": receipt,
        "order_amount": amount,
        "order_currency": "INR",
        "order_status": "ACTIVE",
        "payment_session_id": "session_test",
    }


def adapter(handler):
    return CashfreeSubscriptionProvider(
        settings(), httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def test_configuration_is_independent_and_live_requires_explicit_activation():
    configured = settings()
    assert configured.payment_provider == "none"
    assert SubscriptionProviderResolver(configured).resolve().provider_name == "cashfree"
    with pytest.raises(SettingsError, match="SUBSCRIPTION_CASHFREE"):
        settings(subscription_cashfree_client_secret=None)
    with pytest.raises(SettingsError, match="SUBSCRIPTION_ALLOW_LIVE"):
        settings(subscription_cashfree_environment="production")
    settings(subscription_cashfree_environment="production", subscription_allow_live=True)


async def test_exact_amount_deterministic_order_and_public_only_session():
    req = request()
    bodies, keys = [], []

    def handler(call):
        assert call.url.host == "sandbox.cashfree.com"
        assert call.headers["x-client-id"] == "test-sub-client"
        bodies.append(json.loads(call.content, parse_float=Decimal))
        keys.append(call.headers["x-idempotency-key"])
        return httpx.Response(200, json=order(req.receipt))

    provider = adapter(handler)
    first = await provider.create_period_order(req)
    await provider.create_period_order(req)
    assert bodies[0]["order_amount"] == Decimal("279.20")
    assert bodies[0]["customer_details"]["customer_phone"] == "9876543210"
    assert bodies[0]["order_meta"]["return_url"].endswith("?plan=growth_1m")
    assert "order_splits" not in bodies[0]
    assert keys[0] == keys[1]
    assert first.client_payload == {"payment_session_id": "session_test", "mode": "sandbox"}
    assert provider.client_config().public_key is None


async def test_invalid_phone_never_calls_cashfree():
    provider = adapter(lambda _: pytest.fail("External call on invalid customer"))
    with pytest.raises(ValidationError, match="mobile number"):
        await provider.create_period_order(replace(request(), customer_phone=None))


async def test_payment_reads_are_scoped_and_refunds_are_absolute():
    def handler(call):
        if call.url.path.endswith("/refunds"):
            return httpx.Response(
                200,
                json=[
                    {"cf_payment_id": "123", "refund_amount": "20.20", "refund_status": "SUCCESS"},
                    {"cf_payment_id": "123", "refund_amount": "10", "refund_status": "PENDING"},
                    {"cf_payment_id": "999", "refund_amount": "200", "refund_status": "SUCCESS"},
                ],
            )
        return httpx.Response(
            200,
            json={
                "cf_payment_id": "123",
                "order_id": "sub_order1",
                "payment_status": "SUCCESS",
                "payment_amount": "279.20",
                "payment_currency": "INR",
            },
        )

    observation = await adapter(handler).fetch_payment("sub_order1:123")
    assert observation.payment_ref == "sub_order1:123"
    assert observation.amount_refunded == Money("20.20")
    assert observation.state is ProviderPaymentState.partially_refunded
    with pytest.raises(ValueError):
        await adapter(handler).fetch_payment("../../somewhere")


async def test_refund_without_payment_attribution_is_not_applied():
    def handler(call):
        if call.url.path.endswith("/refunds"):
            return httpx.Response(200, json=[{"refund_amount": "20", "refund_status": "SUCCESS"}])
        return httpx.Response(
            200,
            json={
                "cf_payment_id": "123",
                "order_id": "sub_order1",
                "payment_status": "SUCCESS",
                "payment_amount": "279.20",
                "payment_currency": "INR",
            },
        )

    with pytest.raises(PaymentProviderError, match="attribution"):
        await adapter(handler).fetch_payment("sub_order1:123")


@pytest.mark.parametrize("refund_status", ["CANCELLED", "REJECTED"])
async def test_cancelled_refund_is_terminal_failure_in_api_and_webhook(refund_status):
    def handler(call):
        payload = json.loads(call.content)
        return httpx.Response(
            200,
            json={
                "refund_id": payload["refund_id"],
                "cf_payment_id": "123",
                "refund_amount": "20.00",
                "refund_status": refund_status,
            },
        )

    provider = adapter(handler)
    refund = await provider.refund("sub_order1:123", Money("20.00"), "idempotent-refund")
    assert refund.status == "failed"
    event = provider.parse_event(
        json.dumps(
            {
                "type": "REFUND_STATUS_WEBHOOK",
                "data": {
                    "refund": {
                        "order_id": "sub_order1",
                        "cf_payment_id": "123",
                        "refund_id": refund.refund_ref,
                        "refund_status": refund_status,
                        "refund_amount": "20.00",
                    }
                },
            }
        ).encode(),
        {},
    )
    assert event.kind is SubscriptionEventKind.refund_failed


async def test_unreachable_or_unreadable_create_is_unknown_and_recoverable():
    for response in (httpx.Response(503), httpx.Response(200, text="unreadable")):
        with pytest.raises(PaymentOutcomeUnknownError):
            await adapter(lambda _, result=response: result).create_period_order(request())
    with pytest.raises(PaymentProviderError):
        await adapter(lambda _: httpx.Response(400)).create_period_order(request())


@pytest.mark.parametrize(
    "payload",
    [
        {"order_id": "sub_unknown"},
        {
            "order_id": "sub_different",
            "order_amount": "279.20",
            "order_currency": "INR",
            "order_status": "ACTIVE",
            "payment_session_id": "session_test",
        },
    ],
)
async def test_malformed_successful_create_preserves_the_original_receipt_for_recovery(payload):
    with pytest.raises(PaymentOutcomeUnknownError):
        await adapter(lambda _: httpx.Response(200, json=payload)).create_period_order(request())


def test_raw_webhook_signature_tampering_replay_and_no_browser_payment_proof():
    provider = adapter(lambda _: pytest.fail("Unexpected HTTP"))
    body = json.dumps(
        {
            "type": "PAYMENT_SUCCESS_WEBHOOK",
            "data": {
                "order": {"order_id": "sub_order1", "order_currency": "INR"},
                "payment": {
                    "cf_payment_id": 123,
                    "payment_amount": "279.20",
                    "payment_currency": "INR",
                },
            },
        }
    ).encode()
    timestamp = str(int(time.time() * 1000))
    signature = base64.b64encode(
        hmac.new(
            b"test-sub-secret-not-a-real-key", timestamp.encode() + body, hashlib.sha256
        ).digest()
    ).decode()
    headers = {"x-webhook-timestamp": timestamp, "x-webhook-signature": signature}
    assert provider.verify_webhook_signature(body, headers)
    assert not provider.verify_webhook_signature(body + b" ", headers)
    assert not provider.verify_webhook_signature(body, {**headers, "x-webhook-timestamp": "1"})
    event = provider.parse_event(body, headers)
    assert event.kind is SubscriptionEventKind.payment_captured
    assert event.payment_ref == "sub_order1:123"
    assert event.amount == Money("279.20")
    assert not provider.verify_client_callback("sub_order1", "123", "anything")


async def test_checkout_replay_and_server_verified_activation_use_existing_billing_flow():
    configured = settings()
    paid = False
    receipt = None
    calls = []

    def handler(call):
        nonlocal receipt
        calls.append(call.method + " " + call.url.path)
        if call.method == "POST":
            payload = json.loads(call.content)
            receipt = payload["order_id"]
            return httpx.Response(200, json=order(receipt, str(GROWTH_1M)))
        if call.url.path.endswith("/payments"):
            return httpx.Response(
                200,
                json=[
                    {
                        "cf_payment_id": 123,
                        "order_id": receipt,
                        "payment_status": "SUCCESS",
                        "payment_amount": str(GROWTH_1M),
                        "payment_currency": "INR",
                    }
                ]
                if paid
                else [],
            )
        return httpx.Response(200, json=order(receipt, str(GROWTH_1M)))

    repo = FakeBillingRepo()
    provider = CashfreeSubscriptionProvider(
        configured, httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    uc = SubscriptionBillingUseCases(
        repo, SubscriptionProviderResolver(configured, provider), configured, repo
    )
    actor = replace(owner(), phone="+919876543210")
    key = str(uuid4())
    checkout = await uc.checkout(actor, "plan-g1", key)
    assert checkout["amount"] == str(GROWTH_1M) and checkout["provider"] == "cashfree"
    assert await uc.checkout(actor, "plan-g1", key) == checkout
    assert sum(call.startswith("POST") for call in calls) == 1
    await uc.verify(actor, checkout["order_ref"])
    assert repo.applied_calls == 0
    paid = True
    await uc.verify(actor, checkout["order_ref"])
    assert repo.applied_calls == 1


async def test_missing_phone_does_not_lock_the_checkout_idempotency_key():
    configured = settings()
    calls = []

    def handler(call):
        calls.append(call)
        return httpx.Response(200, json=order(json.loads(call.content)["order_id"], str(GROWTH_1M)))

    repo = FakeBillingRepo()
    provider = CashfreeSubscriptionProvider(
        configured, httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    uc = SubscriptionBillingUseCases(
        repo, SubscriptionProviderResolver(configured, provider), configured, repo
    )
    key = str(uuid4())
    with pytest.raises(ValidationError, match="mobile number"):
        await uc.checkout(owner(), "plan-g1", key)
    assert calls == []
    result = await uc.checkout(replace(owner(), phone="+919876543210"), "plan-g1", key)
    assert result["provider"] == "cashfree" and len(calls) == 1
