"""Owner subscription billing: config, adapter, entitlement, checkout, verify, webhooks, worker."""

import base64
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError
from support_subscription import (
    KEY_SECRET,
    WEBHOOK_SECRET,
    FakeBillingRepo,
    FakeProvider,
    owner,
    profile,
    resolver_for,
    sign,
    sub_settings,
    webhook,
)

from app.application.ports.subscription_provider import (
    SubscriptionEventKind,
    SubscriptionProvider,
)
from app.application.use_cases.subscription_billing import (
    SubscriptionBillingUseCases,
    SubscriptionReconciler,
    SubscriptionWebhookHandler,
    subscription_event_to_json,
)
from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    IdempotencyKeyRequiredError,
    IdempotencyKeyReuseError,
    NotFoundError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
)
from app.domain.entities.profile import Role
from app.domain.entities.subscription import EntitlementState, derive_entitlement
from app.domain.value_objects.money import Money
from app.infrastructure.subscriptions.null import NullSubscriptionProvider
from app.infrastructure.subscriptions.razorpay import (
    RazorpaySubscriptionProvider,
    from_paise,
    to_paise,
)
from app.infrastructure.subscriptions.resolver import (
    SubscriptionProviderResolver,
    build_subscription_provider,
)

APP_ROOT = Path(__file__).resolve().parents[2] / "app"
D = Decimal


# ================================================================== configuration
def test_subscription_provider_defaults_to_none_and_enables_nothing():
    s = Settings(_env_file=None, environment="test")
    assert s.subscription_provider == "none"
    assert s.subscription_webhook_provider is None
    assert isinstance(build_subscription_provider(s), NullSubscriptionProvider)
    assert SubscriptionProviderResolver(s).enabled is False


def test_enabled_provider_needs_every_credential_and_an_explicit_grace():
    sub_settings()  # complete configuration boots
    for missing in ("subscription_razorpay_key_id", "subscription_razorpay_key_secret",
                    "subscription_razorpay_webhook_secret"):
        with pytest.raises(PydanticValidationError, match=missing.upper()):
            sub_settings(**{missing: None})
    with pytest.raises(PydanticValidationError, match="SUBSCRIPTION_GRACE_DAYS"):
        sub_settings(subscription_grace_days=None)
    with pytest.raises(PydanticValidationError, match="SUBSCRIPTION_GRACE_DAYS"):
        sub_settings(subscription_grace_days="")  # KEY= in an env file means "undecided"
    assert sub_settings(subscription_grace_days=0).subscription_grace_days == 0  # explicit zero is fine


def test_webhook_secret_must_be_long_and_live_keys_need_acknowledgement():
    with pytest.raises(PydanticValidationError, match="at least 32"):
        sub_settings(subscription_razorpay_webhook_secret="short")
    with pytest.raises(PydanticValidationError, match="SUBSCRIPTION_ALLOW_LIVE"):
        sub_settings(subscription_razorpay_key_id="rzp_live_abc")
    live = sub_settings(subscription_razorpay_key_id="rzp_live_abc", subscription_allow_live=True)
    assert live.subscription_allow_live is True


def test_unknown_adapter_is_refused():
    with pytest.raises(PydanticValidationError, match="no adapter"):
        Settings(_env_file=None, environment="test", subscription_provider="nonesuch")


def test_booking_and_subscription_enablement_are_independent():
    cashfree = Settings(
        _env_file=None, environment="test", payment_provider="cashfree", cashfree_client_id="c",
        cashfree_client_secret="s", cashfree_easy_split_enabled=True,
        payment_platform_fee_percent=D("0"), payment_commission_base="online_amount",
    )
    assert cashfree.payment_provider == "cashfree" and cashfree.subscription_provider == "none"
    only_sub = sub_settings()
    assert only_sub.payment_provider == "none" and only_sub.subscription_webhook_provider == "razorpay"
    both = sub_settings(
        payment_provider="cashfree", cashfree_client_id="c", cashfree_client_secret="s",
        cashfree_easy_split_enabled=True, payment_platform_fee_percent=D("0"),
        payment_commission_base="online_amount",
    )
    assert both.payment_provider == "cashfree" and both.subscription_provider == "razorpay"


def test_decoupling_provider_name_stays_inside_its_adapter_files():
    banned = [
        "application/ports/subscription_provider.py",
        "application/use_cases/subscription_billing.py",
        "infrastructure/subscriptions/resolver.py",
        "infrastructure/subscriptions/null.py",
        "infrastructure/db/repositories/subscription_billing_repository.py",
        "api/v1/routes/subscription_billing.py",
        "api/v1/schemas/subscription_billing.py",
        "domain/entities/subscription.py",
    ]
    for rel in banned:
        assert "razorpay" not in (APP_ROOT / rel).read_text(encoding="utf-8").lower(), rel
    adapter = (APP_ROOT / "infrastructure/subscriptions/razorpay.py").read_text(encoding="utf-8")
    assert "UNVERIFIED" in adapter  # unconfirmed provider facts stay flagged


def test_port_and_null_provider_are_complete():
    assert not getattr(NullSubscriptionProvider, "__abstractmethods__", frozenset())
    for name in SubscriptionProvider.__abstractmethods__:
        assert name in NullSubscriptionProvider.__dict__
    assert NullSubscriptionProvider().supports_recurring is False
    assert RazorpaySubscriptionProvider(sub_settings()).supports_recurring is False


# ======================================================================== adapter
def adapter(handler) -> RazorpaySubscriptionProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RazorpaySubscriptionProvider(sub_settings(), client)


def test_paise_conversion_is_exact():
    assert to_paise(Money("349.00")) == 34900
    assert to_paise(Money("0.01")) == 1
    assert from_paise(34900).amount == D("349.00")


async def test_create_order_sends_paise_receipt_and_basic_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "order_1", "amount": 34900, "currency": "INR",
                                         "receipt": "sub_abc12345", "status": "created"})

    from app.application.ports.subscription_provider import SubscriptionOrderRequest
    order = await adapter(handler).create_period_order(SubscriptionOrderRequest(
        receipt="sub_abc12345", billing_record_id="b1", salon_id="s1", plan_id="p1",
        amount=Money("349.00")))
    assert seen["url"].endswith("/orders")
    assert base64.b64decode(seen["auth"].split()[1]).decode() == f"rzp_test_subkey:{KEY_SECRET}"
    assert seen["body"]["amount"] == 34900 and seen["body"]["currency"] == "INR"
    assert seen["body"]["receipt"] == "sub_abc12345"
    assert order.amount.amount == D("349.00")
    assert order.client_payload == {"key_id": "rzp_test_subkey", "order_id": "order_1",
                                    "amount": 34900, "currency": "INR"}
    assert KEY_SECRET not in json.dumps(dict(order.client_payload))


async def test_create_order_rejects_long_receipt_and_zero_amount():
    from app.application.ports.subscription_provider import SubscriptionOrderRequest
    a = adapter(lambda r: httpx.Response(500))
    with pytest.raises(ValueError):
        await a.create_period_order(SubscriptionOrderRequest("x" * 41, "b", "s", "p", Money("1")))
    with pytest.raises(ValueError):
        await a.create_period_order(SubscriptionOrderRequest("sub_ok_123", "b", "s", "p", Money("0")))


async def test_timeouts_and_5xx_are_unknown_but_4xx_is_definitive():
    def boom(request):
        raise httpx.ConnectTimeout("t")

    from app.application.ports.subscription_provider import SubscriptionOrderRequest
    req = SubscriptionOrderRequest("sub_ok_123", "b", "s", "p", Money("5"))
    with pytest.raises(PaymentOutcomeUnknownError):
        await adapter(boom).create_period_order(req)
    with pytest.raises(PaymentOutcomeUnknownError):
        await adapter(lambda r: httpx.Response(502)).create_period_order(req)
    with pytest.raises(PaymentProviderError) as info:
        await adapter(lambda r: httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR"}})
                      ).create_period_order(req)
    assert not isinstance(info.value, PaymentOutcomeUnknownError)


async def test_fetches_map_states_and_404_is_none():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/orders/order_1/payments"):
            return httpx.Response(200, json={"items": [
                {"id": "pay_1", "order_id": "order_1", "amount": 34900, "currency": "INR",
                 "status": "captured", "amount_refunded": 1000, "refund_status": "partial"}]})
        if path.endswith("/orders/order_1"):
            return httpx.Response(200, json={"id": "order_1", "amount": 34900, "amount_paid": 34900,
                                             "currency": "INR", "status": "paid", "receipt": "r"})
        if path.endswith("/orders"):
            assert request.url.params["receipt"] == "sub_abc12345"
            return httpx.Response(200, json={"items": [{"id": "order_1", "amount": 34900,
                                                        "currency": "INR", "status": "created",
                                                        "receipt": "sub_abc12345"}]})
        return httpx.Response(404, json={"error": {"code": "BAD_REQUEST_ERROR"}})

    a = adapter(handler)
    payments = await a.fetch_order_payments("order_1")
    assert payments[0].state.value == "partially_refunded"
    assert payments[0].amount_refunded.amount == D("10.00")
    assert (await a.fetch_order("order_1")).state.value == "paid"
    assert (await a.find_order_by_receipt("sub_abc12345")).order_ref == "order_1"
    assert await a.fetch_order("missing") is None
    assert await a.fetch_payment("missing") is None


def test_client_callback_signature_vector():
    a = RazorpaySubscriptionProvider(sub_settings())
    import hashlib
    import hmac
    good = hmac.new(KEY_SECRET.encode(), b"order_1|pay_1", hashlib.sha256).hexdigest()
    assert a.verify_client_callback("order_1", "pay_1", good)
    assert not a.verify_client_callback("order_1", "pay_2", good)
    assert not a.verify_client_callback("order_1", "pay_1", "")


def test_webhook_signature_and_parsing():
    a = RazorpaySubscriptionProvider(sub_settings())
    body, headers = webhook("payment.captured", order="o1", payment="p1", amount_paise=34900)
    assert a.verify_webhook_signature(body, headers)
    assert not a.verify_webhook_signature(body + b" ", headers)
    assert not a.verify_webhook_signature(body, {**headers, "x-razorpay-signature": "0" * 64})
    assert not a.verify_webhook_signature(body, {})
    # a signature made with the BOOKING-style key or an attacker secret never verifies
    assert not a.verify_webhook_signature(body, {"x-razorpay-signature": sign(body, "other-secret")})
    event = a.parse_event(body, headers)
    assert event.kind is SubscriptionEventKind.payment_captured and event.event_id == "evt_1"
    assert (event.order_ref, event.payment_ref, event.amount.amount) == ("o1", "p1", D("349.00"))
    paid = json.dumps({"event": "order.paid", "payload": {
        "order": {"entity": {"id": "o1", "amount": 34900, "currency": "INR"}},
        "payment": {"entity": {"id": "p1", "order_id": "o1", "amount": 34900, "currency": "INR"}}}}).encode()
    assert a.parse_event(paid, {}).kind is SubscriptionEventKind.order_paid
    refund, rh = webhook("refund.processed", payment="p1", amount_paise=1000)
    parsed = a.parse_event(refund, rh)
    assert parsed.kind is SubscriptionEventKind.refund_processed and parsed.payment_ref == "p1"
    assert a.parse_event(json.dumps({"event": "payment.authorized"}).encode(), {}).kind is (
        SubscriptionEventKind.ignored)
    with pytest.raises(ValueError):
        a.parse_event(b"not json", {})


async def test_refund_is_sent_in_paise_with_an_idempotency_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["key"] = request.headers["x-refund-idempotency"]
        return httpx.Response(200, json={"id": "rfnd_1", "payment_id": "pay_1", "amount": 5000,
                                         "status": "processed"})

    result = await adapter(handler).refund("pay_1", Money("50.00"), "key-1", "requested")
    assert seen["body"]["amount"] == 5000 and seen["key"] == "key-1"
    assert result.status == "processed" and result.amount.amount == D("50.00")


# ===================================================================== entitlement
NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


def ent(status, start=-10, end=20, grace=None):
    def at(days):
        return None if days is None else NOW + timedelta(days=days)
    return derive_entitlement(status=status, period_start=at(start), period_end=at(end),
                              grace_end=at(grace), now=NOW)


@pytest.mark.parametrize(
    ("kwargs", "active", "state"),
    [
        ({"status": None}, False, EntitlementState.none),
        ({"status": "active"}, True, EntitlementState.active),
        ({"status": "active", "end": -1}, False, EntitlementState.expired),
        ({"status": "active", "end": -1, "grace": 2}, True, EntitlementState.grace),
        ({"status": "active", "end": -3, "grace": -1}, False, EntitlementState.expired),
        ({"status": "cancelled"}, True, EntitlementState.cancelled_paid_through),
        ({"status": "cancelled", "end": -1}, False, EntitlementState.expired),
        ({"status": "past_due", "end": -1, "grace": 1}, True, EntitlementState.grace),
        ({"status": "past_due", "end": -1}, False, EntitlementState.expired),
        ({"status": "suspended"}, False, EntitlementState.suspended),
        ({"status": "pending", "start": None, "end": None}, False, EntitlementState.none),
        ({"status": "expired"}, False, EntitlementState.expired),
    ],
)
def test_entitlement_matrix(kwargs, active, state):
    result = ent(**kwargs)
    assert (result.active, result.state) == (active, state)


# ======================================================================= use cases
def make(repo=None, provider=None, settings=None):
    repo = repo or FakeBillingRepo()
    provider = provider or FakeProvider()
    settings = settings or sub_settings()
    uc = SubscriptionBillingUseCases(repo, resolver_for(provider, settings), settings, repo)
    return uc, repo, provider


def test_config_never_allows_native_purchase_and_exposes_only_the_public_key():
    uc, _, _ = make()
    body = uc.config()
    assert body["enabled"] is True and body["native_purchase_allowed"] is False
    assert body["mode"] == "one_time" and body["renewal"] == "manual"
    assert body["public_key"] == "rzp_test_subkey"
    assert KEY_SECRET not in json.dumps(body) and WEBHOOK_SECRET not in json.dumps(body)
    off = SubscriptionBillingUseCases(None, SubscriptionProviderResolver(Settings(
        _env_file=None, environment="test")), Settings(_env_file=None, environment="test"))
    assert off.config() == {"enabled": False, "provider": None, "mode": "one_time",
                            "renewal": "manual", "native_purchase_allowed": False,
                            "public_key": None, "currency": "INR",
                            "checkout_url": None}


async def test_checkout_persists_the_row_before_calling_the_provider():
    uc, repo, provider = make()
    seen = {}
    original = provider.create_period_order

    async def spy(request):
        seen["rows"] = [dict(r) for r in repo.rows.values()]
        seen["commits"] = repo.commits
        return await original(request)

    provider.create_period_order = spy
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    assert len(seen["rows"]) == 1 and seen["rows"][0]["receipt"] == body["receipt"]
    assert seen["rows"][0]["provider_order_ref"] is None and seen["commits"] >= 1
    assert body["amount"] == "349.00" and body["currency"] == "INR"
    assert body["client_payload"]["amount"] == 34900 and body["order_ref"].startswith("order_")
    assert repo.rows[body["billing_id"]]["provider_order_ref"] == body["order_ref"]


async def test_checkout_amount_comes_from_the_plan_snapshot_not_the_client():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    repo.plans["plan-g1"]["price_amount"] = D("999.00")  # admin edits the price afterwards
    row = repo.rows[body["billing_id"]]
    assert row["amount"] == D("349.00")
    assert provider.orders[body["order_ref"]]["amount"] == D("349.00")


async def test_checkout_replay_returns_the_stored_response_without_a_second_order():
    uc, repo, provider = make()
    first = await uc.checkout(owner(), "plan-g1", "key-12345678")
    again = await uc.checkout(owner(), "plan-g1", "key-12345678")
    assert again == first and provider.calls.count("create") == 1 and len(repo.rows) == 1
    with pytest.raises(IdempotencyKeyReuseError):
        await uc.checkout(owner(), "plan-g6", "key-12345678")


async def test_checkout_requires_a_key_and_an_enabled_provider():
    uc, _, _ = make()
    for bad in (None, "", "short"):
        with pytest.raises(IdempotencyKeyRequiredError):
            await uc.checkout(owner(), "plan-g1", bad)
    settings = Settings(_env_file=None, environment="test")
    off = SubscriptionBillingUseCases(FakeBillingRepo(), SubscriptionProviderResolver(settings),
                                      settings, FakeBillingRepo())
    with pytest.raises(PaymentProviderNotConfiguredError):
        await off.checkout(owner(), "plan-g1", "key-12345678")


@pytest.mark.parametrize("role", [Role.customer, Role.staff, Role.super_admin])
async def test_only_a_salon_owner_can_use_the_owner_billing_use_cases(role):
    uc, repo, _ = make()
    repo.salons["x-1"] = "salon-9"
    actor = profile(role, "x-1")
    with pytest.raises(ForbiddenError):
        await uc.checkout(actor, "plan-g1", "key-12345678")
    with pytest.raises(ForbiddenError):
        await uc.get_subscription(actor)
    with pytest.raises(ForbiddenError):
        await uc.cancel(actor)
    with pytest.raises(ForbiddenError):
        await uc.history(actor, 10, 0)
    with pytest.raises(ForbiddenError):
        await uc.verify(actor, "order_1")
    assert repo.rows == {}


async def test_an_owner_without_a_salon_is_refused_and_cannot_touch_another_salons_order():
    uc, repo, provider = make()
    with pytest.raises(ForbiddenError):
        await uc.checkout(owner("owner-without-salon"), "plan-g1", "key-12345678")
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    repo.salons["owner-2"] = "salon-2"
    provider.pay(body["order_ref"])
    with pytest.raises(NotFoundError):
        await uc.verify(owner("owner-2"), body["order_ref"])
    assert repo.applied_calls == 0 and repo.rows[body["billing_id"]]["status"] == "created"


async def test_timeout_after_the_order_was_created_is_recovered_by_receipt():
    uc, repo, provider = make()
    provider.create_mode = "timeout_created"
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    assert body["order_ref"] in provider.orders and len(provider.orders) == 1
    assert "find_by_receipt" in provider.calls and len(repo.rows) == 1


async def test_lost_timeout_keeps_the_row_and_a_retry_resumes_it_creating_one_order():
    uc, repo, provider = make()
    provider.create_mode = "timeout_lost"
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.checkout(owner(), "plan-g1", "key-12345678")
    (row,) = repo.rows.values()
    assert row["status"] == "created" and row["provider_order_ref"] is None
    provider.create_mode = "ok"
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")  # same key: reservation released
    assert len(repo.rows) == 1 and body["receipt"] == row["receipt"]
    assert len(provider.orders) == 1


async def test_resuming_an_order_that_was_paid_meanwhile_conflicts_and_frees_the_key():
    uc, repo, provider = make()
    first = await uc.checkout(owner(), "plan-g1", "key-12345678")
    provider.pay(first["order_ref"])
    with pytest.raises(ConflictError):
        await uc.checkout(owner(), "plan-g1", "key-another-1")
    assert ("owner-1", "sub-checkout:salon-1", "key-another-1") not in repo.idem  # reservation released
    result = await uc.verify(owner(), first["order_ref"])
    assert result["verification"] == "started" and repo.applied_calls == 1


async def test_a_definitive_provider_refusal_fails_the_row_and_allows_a_fresh_attempt():
    uc, repo, provider = make()
    provider.create_mode = "reject"
    with pytest.raises(PaymentProviderError):
        await uc.checkout(owner(), "plan-g1", "key-12345678")
    (row,) = repo.rows.values()
    assert row["status"] == "failed"
    provider.create_mode = "ok"
    body = await uc.checkout(owner(), "plan-g1", "key-87654321")
    assert body["billing_id"] != row["id"] and len(repo.rows) == 2


async def test_second_checkout_resumes_the_open_order_and_another_plan_is_refused():
    uc, _repo, provider = make()
    first = await uc.checkout(owner(), "plan-g1", "key-12345678")
    second = await uc.checkout(owner(), "plan-g1", "key-other-key")
    assert second["billing_id"] == first["billing_id"] and second["order_ref"] == first["order_ref"]
    assert provider.calls.count("create") == 1
    with pytest.raises(ConflictError):
        await uc.checkout(owner(), "plan-g6", "key-third-key")


async def test_plan_change_is_refused_while_a_paid_period_runs_but_renewal_is_allowed():
    uc, repo, _ = make()
    repo.subscription = {
        "id": "s1", "salon_id": "salon-1", "plan_id": "plan-g1", "status": "active",
        "current_period_start": datetime.now(UTC) - timedelta(days=5),
        "current_period_end": datetime.now(UTC) + timedelta(days=5),
        "grace_period_end": None, "cancelled_at": None, "plan_code": "growth_1m",
        "plan_name": "Growth", "plan_tier": 1, "plan_features": {},
    }
    with pytest.raises(ConflictError):
        await uc.checkout(owner(), "plan-g6", "key-12345678")
    assert (await uc.checkout(owner(), "plan-g1", "key-87654321"))["plan_id"] == "plan-g1"
    repo.rows.clear()
    repo.subscription["status"] = "suspended"
    with pytest.raises(ConflictError):
        await uc.checkout(owner(), "plan-g1", "key-suspended-1")


# ======================================================================== verify
async def paid_flow(*, amount=None, currency=None):
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    pay = provider.pay(body["order_ref"], amount=amount, currency=currency)
    return uc, repo, provider, body, pay


async def test_verify_applies_a_provider_confirmed_payment_exactly_once():
    uc, repo, _, body, pay = await paid_flow()
    first = await uc.verify(owner(), body["order_ref"])
    second = await uc.verify(owner(), body["order_ref"])
    assert first["verification"] == "started" and second["verification"] == "already_applied"
    assert repo.applied_calls == 1
    row = repo.rows[body["billing_id"]]
    assert row["status"] == "paid" and row["provider_payment_ref"] == pay
    assert ("razorpay", f"applied:{row['id']}", "subscription_started") in repo.events


async def test_a_client_claim_without_provider_payment_never_activates():
    uc, repo, _provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    import hashlib
    import hmac
    forged = hmac.new(b"wrong", f"{body['order_ref']}|pay_fake".encode(), hashlib.sha256).hexdigest()
    result = await uc.verify(owner(), body["order_ref"], "pay_fake", forged)
    assert result["verification"] == "pending" and repo.applied_calls == 0
    valid = hmac.new(KEY_SECRET.encode(), f"{body['order_ref']}|pay_fake".encode(), hashlib.sha256
                     ).hexdigest()
    result = await uc.verify(owner(), body["order_ref"], "pay_fake", valid)
    assert result["verification"] == "pending" and repo.applied_calls == 0  # signature != payment
    assert repo.rows[body["billing_id"]]["status"] == "created"


async def test_amount_or_currency_mismatch_is_an_anomaly_and_never_activates():
    for kwargs in ({"amount": D("1.00")}, {"currency": "USD"}):
        uc, repo, _, body, _ = await paid_flow(**kwargs)
        result = await uc.verify(owner(), body["order_ref"])
        assert result["verification"] == "mismatch" and repo.applied_calls == 0
        assert repo.anomalies[0]["kind"] == "subscription_amount_mismatch"
        assert repo.rows[body["billing_id"]]["status"] == "created"


async def test_a_payment_on_another_order_does_not_count_for_this_one():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    provider.orders["order_other"] = {"receipt": "x", "amount": D("349.00"), "currency": "INR",
                                      "state": provider.orders[body["order_ref"]]["state"]}
    provider.pay("order_other")
    result = await uc.verify(owner(), body["order_ref"])
    assert result["verification"] == "pending" and repo.applied_calls == 0


async def test_a_second_captured_payment_on_one_order_is_flagged_not_double_applied():
    uc, repo, provider, body, first = await paid_flow()
    provider.pay(body["order_ref"], payment_ref="pay_zzz_second")
    result = await uc.verify(owner(), body["order_ref"])
    assert result["verification"] == "started" and repo.applied_calls == 1
    assert [a["kind"] for a in repo.anomalies] == ["subscription_duplicate_payment"]
    assert repo.rows[body["billing_id"]]["provider_payment_ref"] == first  # sorted: first ref wins


# ======================================================================== webhooks
def handler_for(repo, provider, settings=None):
    settings = settings or sub_settings()
    return SubscriptionWebhookHandler(repo, resolver_for(provider, settings), settings)


def normalized(provider, event, order=None, payment=None, amount=None, **kw):
    body, headers = webhook(event, order=order, payment=payment, amount_paise=amount, **kw)
    assert provider.verify_webhook_signature(body, headers)
    return subscription_event_to_json(provider.parse_event(body, headers))


async def test_captured_webhook_applies_once_even_when_delivered_repeatedly():
    _uc, repo, provider, body, pay = await paid_flow()
    h = handler_for(repo, provider)
    data = normalized(provider, "payment.captured", body["order_ref"], pay, 34900)
    assert await h.apply("razorpay", data, "evt_1") == "applied"
    assert await h.apply("razorpay", data, "evt_1") == "applied"  # duplicate delivery
    order_paid = normalized(provider, "order.paid", body["order_ref"], pay, 34900, event_id="evt_2")
    assert await h.apply("razorpay", order_paid, "evt_2") == "applied"  # second event, same payment
    assert repo.applied_calls == 1 and repo.rows[body["billing_id"]]["status"] == "paid"


async def test_webhook_amount_mismatch_is_loud_and_does_not_activate():
    _uc, repo, provider, body, pay = await paid_flow()
    data = normalized(provider, "payment.captured", body["order_ref"], pay, 100)
    assert await handler_for(repo, provider).apply("razorpay", data) == "mismatch"
    assert repo.applied_calls == 0 and repo.anomalies[0]["kind"] == "subscription_amount_mismatch"


async def test_webhook_for_an_unknown_order_is_acknowledged_and_ignored():
    _, repo, provider = make()
    data = normalized(provider, "payment.captured", "order_unknown", "pay_x", 100)
    assert await handler_for(repo, provider).apply("razorpay", data) == "ignored"
    assert repo.rows == {} and repo.applied_calls == 0


async def test_event_that_outruns_the_provider_read_model_is_retried_not_dropped():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    data = normalized(provider, "payment.captured", body["order_ref"], "pay_early", 34900)
    with pytest.raises(PaymentOutcomeUnknownError):
        await handler_for(repo, provider).apply("razorpay", data)
    provider.pay(body["order_ref"], payment_ref="pay_early")
    assert await handler_for(repo, provider).apply("razorpay", data) == "applied"
    assert repo.applied_calls == 1


async def test_failed_event_after_capture_does_not_regress_and_failure_before_capture_is_harmless():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    h = handler_for(repo, provider)
    failed = normalized(provider, "payment.failed", body["order_ref"], "pay_bad", 34900,
                        event_id="evt_f")
    assert await h.apply("razorpay", failed) == "applied"
    row = repo.rows[body["billing_id"]]
    assert row["status"] == "created" and row["failure_code"] == "payment_failed"  # still payable
    pay = provider.pay(body["order_ref"])
    captured = normalized(provider, "payment.captured", body["order_ref"], pay, 34900,
                          event_id="evt_c")
    assert await h.apply("razorpay", captured) == "applied"
    assert await h.apply("razorpay", failed) == "applied"  # delayed, out-of-order failure
    assert repo.rows[body["billing_id"]]["status"] == "paid" and repo.applied_calls == 1


async def test_refund_events_converge_and_never_revoke_access_automatically():
    _uc, repo, provider, body, pay = await paid_flow()
    h = handler_for(repo, provider)
    await h.apply("razorpay", normalized(provider, "payment.captured", body["order_ref"], pay, 34900))
    provider.payments[pay]["refunded"] = D("100.00")
    refund = normalized(provider, "refund.processed", None, pay, 10000, refund="rfnd_1")
    assert await h.apply("razorpay", refund) == "applied"
    assert await h.apply("razorpay", refund) == "applied"
    row = repo.rows[body["billing_id"]]
    assert row["status"] == "partially_refunded" and row["refunded_amount"] == D("100.00")
    provider.payments[pay]["refunded"] = D("349.00")
    await h.apply("razorpay", refund)
    assert repo.rows[body["billing_id"]]["status"] == "refunded"
    provider.payments[pay]["refunded"] = D("50.00")  # a stale, reordered view cannot lower it
    await h.apply("razorpay", refund)
    assert repo.rows[body["billing_id"]]["refunded_amount"] == D("349.00")
    assert repo.applied_calls == 1 and repo.rows[body["billing_id"]]["applied_at"] is not None


async def test_ignored_kinds_and_a_disabled_provider_are_acknowledged():
    _uc, repo, provider, body, pay = await paid_flow()
    ignored = subscription_event_to_json(provider.parse_event(
        json.dumps({"event": "subscription.charged", "payload": {}}).encode(), {}))
    assert await handler_for(repo, provider).apply("razorpay", ignored) == "ignored"
    data = normalized(provider, "payment.captured", body["order_ref"], pay, 34900)
    off = Settings(_env_file=None, environment="test")
    h = SubscriptionWebhookHandler(repo, SubscriptionProviderResolver(off), off)
    assert await h.apply("razorpay", data) == "ignored" and repo.applied_calls == 0


async def test_payment_use_case_routes_subscription_domain_events_to_the_billing_handler():
    from app.application.use_cases.payments import PaymentWebhookUseCases

    class Stub:
        calls = []  # noqa: RUF012

        async def apply(self, provider, data, event_id):
            self.calls.append((provider, data["kind"], event_id))
            return "applied"

    stub = Stub()
    uc = PaymentWebhookUseCases(None, None, sub_settings(), stub)  # type: ignore[arg-type]
    data = {"domain": "subscription", "kind": "payment_captured", "event_type": "subscription"}
    assert await uc._apply("razorpay", data, "evt") == "applied"
    assert stub.calls == [("razorpay", "payment_captured", "evt")]


# ===================================================================== reconcile
def reconciler(repo, provider, settings=None):
    settings = settings or sub_settings()
    return SubscriptionReconciler(repo, resolver_for(provider, settings), settings)


async def test_reconciler_settles_an_order_whose_webhook_never_arrived():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    provider.pay(body["order_ref"])
    counts = await reconciler(repo, provider).run()
    assert counts["settled"] == 1 and repo.applied_calls == 1
    assert (await reconciler(repo, provider).run())["settled"] == 0  # nothing left to do


async def test_reconciler_expires_unpaid_orders_and_marks_failed_attempts_failed():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    repo.rows[body["billing_id"]]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    counts = await reconciler(repo, provider).run()
    assert counts["expired"] == 1 and repo.rows[body["billing_id"]]["status"] == "expired"
    body2 = await uc.checkout(owner(), "plan-g1", "key-87654321")
    provider.pay(body2["order_ref"], status="failed")
    repo.rows[body2["billing_id"]]["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    await reconciler(repo, provider).run()
    assert repo.rows[body2["billing_id"]]["status"] == "failed"


async def test_a_late_capture_on_an_expired_order_is_still_applied():
    uc, repo, provider = make()
    body = await uc.checkout(owner(), "plan-g1", "key-12345678")
    await repo.finish_unpaid(body["billing_id"], "expired")
    pay = provider.pay(body["order_ref"])
    data = normalized(provider, "payment.captured", body["order_ref"], pay, 34900)
    assert await handler_for(repo, provider).apply("razorpay", data) == "applied"
    assert repo.rows[body["billing_id"]]["status"] == "paid" and repo.applied_calls == 1


async def test_an_order_with_no_provider_trace_expires_locally():
    uc, repo, provider = make()
    provider.create_mode = "timeout_lost"
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.checkout(owner(), "plan-g1", "key-12345678")
    (row,) = repo.rows.values()
    row["expires_at"] = datetime.now(UTC) - timedelta(seconds=1)
    provider.create_mode = "ok"
    await reconciler(repo, provider).run()
    assert row["status"] == "expired"


async def test_reconciler_reapplies_a_paid_row_that_never_got_applied():
    _uc, repo, provider, body, pay = await paid_flow()
    await repo.mark_paid(body["billing_id"], pay)
    counts = await reconciler(repo, provider).run()
    assert counts["reapplied"] == 1 and repo.applied_calls == 1


async def test_reconciler_survives_a_provider_outage_and_still_sweeps():
    uc, repo, provider = make()
    await uc.checkout(owner(), "plan-g1", "key-12345678")

    async def down(order_ref):
        raise PaymentOutcomeUnknownError("down")

    provider.fetch_order_payments = down
    counts = await reconciler(repo, provider).run()
    assert counts["errors"] == 1 and counts["lapsed"] == 0


# =================================================================== cancel / state
async def test_cancel_is_idempotent_keeps_paid_through_and_works_with_billing_off():
    uc, repo, _ = make()
    with pytest.raises(NotFoundError):
        await uc.cancel(owner())
    end = datetime.now(UTC) + timedelta(days=10)
    repo.subscription = {
        "id": "s1", "salon_id": "salon-1", "plan_id": "plan-g1", "status": "active",
        "current_period_start": datetime.now(UTC) - timedelta(days=20), "current_period_end": end,
        "grace_period_end": end + timedelta(days=3), "cancelled_at": None, "plan_code": "growth_1m",
        "plan_name": "Growth", "plan_tier": 1, "plan_features": {"split_bill": True},
    }
    first = await uc.cancel(owner())
    second = await uc.cancel(owner())
    for state in (first, second):
        assert state["cancelled"] is True and state["entitlement_active"] is True
        assert state["entitlement_state"] == "cancelled_paid_through"
        assert state["paid_through"] == end and state["renewal"] == "manual"
    off_settings = Settings(_env_file=None, environment="test")
    off = SubscriptionBillingUseCases(repo, SubscriptionProviderResolver(off_settings), off_settings, repo)
    assert (await off.cancel(owner()))["cancelled"] is True  # never gated by the provider
    assert await off.history(owner(), 10, 0) == []


async def test_state_separates_provider_verified_payment_from_backend_entitlement():
    uc, repo, _provider, body, pay = await paid_flow()
    await repo.mark_paid(body["billing_id"], pay)  # verified paid but NOT yet applied
    state = await uc.get_subscription(owner())
    assert state["latest_payment"]["payment_verified"] is True
    assert state["latest_payment"]["entitlement_applied"] is False
    assert state["entitlement_active"] is False and state["status"] is None


async def test_access_state_labels_follow_the_plan_tier():
    uc, repo, _ = make()
    assert (await uc.access_state(owner()))["access_state"] == "not_subscribed"
    base = {
        "id": "s1", "salon_id": "salon-1", "plan_id": "plan-g1", "status": "active",
        "current_period_start": datetime.now(UTC) - timedelta(days=1),
        "current_period_end": datetime.now(UTC) + timedelta(days=9), "grace_period_end": None,
        "cancelled_at": None, "plan_code": "c", "plan_name": "n", "plan_features": {"x": True},
    }
    repo.subscription = {**base, "plan_tier": 1}
    assert (await uc.access_state(owner()))["access_state"] == "subscribed_growth"
    repo.subscription = {**base, "plan_tier": 2}
    assert (await uc.access_state(owner()))["access_state"] == "subscribed_premium"
    repo.subscription = {**base, "plan_tier": 2, "current_period_end": datetime.now(UTC) - timedelta(days=1)}
    state = await uc.access_state(owner())
    assert state["access_state"] == "not_subscribed" and state["features"] == {}


async def test_history_is_visible_after_lapse_and_money_is_serialised_as_decimal_strings():
    uc, _repo, _provider, _body, _pay = await paid_flow()
    rows = await uc.history(owner(), 10, 0)
    assert rows[0]["amount"] == "349.00" and rows[0]["refunded_amount"] == "0.00"


# ============================================================== HTTP-level routes
@pytest.fixture
def http():
    from app.api import deps
    from app.main import app

    repo = FakeBillingRepo()
    app.dependency_overrides[deps.get_current_actor] = lambda: owner()
    yield TestClient(app), app, deps, repo
    app.dependency_overrides.clear()


def test_admin_activation_routes_are_not_callable_by_owners(http):
    client, _app, _deps, _ = http
    for method, path in (
        ("post", "/v1/admin/salons/00000000-0000-0000-0000-000000000001/subscription/test"),
        ("post", "/v1/admin/subscriptions/00000000-0000-0000-0000-000000000001/cancel"),
        ("post", "/v1/admin/subscriptions/00000000-0000-0000-0000-000000000001/suspend"),
        ("get", "/v1/admin/subscription-plans"),
        ("get", "/v1/admin/subscription-events"),
    ):
        response = client.request(method.upper(), path, json={"plan_id": "x", "salon_id": "x"})
        assert response.status_code == 403, (path, response.status_code)


def test_public_config_route_and_native_purchase_flag(http):
    client, *_ = http
    body = client.get("/v1/subscriptions/config").json()
    assert body["native_purchase_allowed"] is False and body["mode"] == "one_time"
    assert body["enabled"] is False  # default settings: provider none


def test_every_new_owner_route_declares_a_response_model_and_requires_auth():
    from app.main import app

    schema = app.openapi()
    expected = {
        ("get", "/v1/subscription-plans"), ("get", "/v1/salons/me/subscription"),
        ("post", "/v1/salons/me/subscription/checkout"), ("post", "/v1/salons/me/subscription/verify"),
        ("post", "/v1/salons/me/subscription/cancel"), ("get", "/v1/salons/me/subscription/payments"),
        ("get", "/v1/salons/me/access-state"), ("get", "/v1/subscriptions/config"),
    }
    for method, path in expected:
        op = schema["paths"][path][method]
        assert "200" in op["responses"] and op["responses"]["200"]["content"], (method, path)
        if path != "/v1/subscriptions/config":
            assert op.get("security"), path
    amounts = schema["components"]["schemas"]["PurchasablePlanResponse"]["properties"]["price_amount"]
    assert "number" not in json.dumps(amounts) or amounts.get("anyOf")  # Decimal, not float
    plan_props = schema["components"]["schemas"]["PurchasablePlanResponse"]["properties"]
    assert "monthly_equivalent" in plan_props
    assert "discount_percent" in plan_props


def test_plan_prices_are_decimal_in_the_admin_schemas_too():
    from app.api.v1.schemas.subscription import PlanCreateRequest, PlanResponse

    assert PlanCreateRequest(code="c", name="n", price_amount="349.50").price_amount == D("349.50")
    with pytest.raises(PydanticValidationError):
        PlanCreateRequest(code="c", name="n", price_amount="1.234")
    with pytest.raises(PydanticValidationError):
        PlanCreateRequest(code="c", name="n", currency="inr")
    with pytest.raises(PydanticValidationError):
        PlanCreateRequest(code="c", name="n", billing_interval="fortnightly")
    assert PlanResponse.model_fields["price_amount"].annotation is Decimal
