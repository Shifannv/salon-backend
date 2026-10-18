"""Mock adapter guarantees only; these tests establish no Cashfree capability."""

import hashlib
import hmac
import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentGateway,
    PaymentIntentRequest,
    RefundRequest,
    SettlementAccountRequest,
)
from app.application.ports.payment_provider import (
    PaymentProvider,
    PayoutProvider,
    ProviderFeeReconciler,
    RefundProvider,
    WebhookVerifier,
)
from app.core.config import Settings
from app.core.exceptions import (
    IdempotencyKeyReuseError,
    PaymentCapabilityError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
)
from app.domain.entities.payment import GatewayCapability, RefundStatus
from app.domain.entities.provider_finance import (
    EvidenceSource,
    PayoutRequest,
    PayoutStatus,
    ProviderFees,
)
from app.domain.value_objects.money import Money
from app.infrastructure.payments.fake import FakeProvider, create_gateway, synthetic_reference
from app.infrastructure.payments.null import NullPaymentGateway
from app.infrastructure.payments.resolver import PaymentGatewayResolver, build_gateway

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/providers/fake"


def config(**overrides):
    values = {
        "_env_file": None, "environment": "test", "payment_provider": "fake",
        "payment_fake_enabled": True, "payment_platform_fee_percent": "0",
        "payment_commission_base": "online_amount", "cashfree_enabled": False,
        "payment_allow_live": False,
    }
    values.update(overrides)
    return Settings(**values)


def intent(**overrides):
    values = {"intent_reference": "synthetic-booking-1", "booking_id": "b1", "salon_id": "salon-1",
              "amount": Money("150.00")}
    values.update(overrides)
    return PaymentIntentRequest(**values)


def payout(**overrides):
    values = {"salon_id": "salon-1", "amount": Money("100.00"), "idempotency_key": "synthetic-payout-1",
              "destination_reference": synthetic_reference("destination", "salon-1")}
    values.update(overrides)
    return PayoutRequest(**values)


def test_existing_gateway_composes_the_smaller_ports_without_replacing_its_contract():
    provider = FakeProvider()
    for port in (PaymentProvider, RefundProvider, PayoutProvider, WebhookVerifier,
                 ProviderFeeReconciler, PaymentGateway):
        assert isinstance(provider, port)
    resolver = PaymentGatewayResolver(config())
    assert resolver.payout_provider() is resolver.resolve()
    assert resolver.fee_reconciler() is resolver.resolve()
    assert isinstance(build_gateway(Settings(_env_file=None)), NullPaymentGateway)


@pytest.mark.parametrize("overrides", [
    {"payment_fake_enabled": False},
    {"environment": "production"}, {"environment": "staging"},
    {"payment_allow_live": True}, {"cashfree_enabled": True},
])
def test_fake_configuration_fails_closed(overrides):
    with pytest.raises(ValueError):
        config(**overrides)


def test_factory_rechecks_environment_even_when_settings_validation_was_bypassed():
    unsafe = config().model_copy(update={"environment": "production"})
    with pytest.raises(PaymentCapabilityError):
        create_gateway(unsafe)


def test_disabled_cashfree_requires_no_credentials_and_has_no_new_capabilities():
    settings = Settings(_env_file=None, payment_provider="cashfree", cashfree_enabled=False)
    resolver = PaymentGatewayResolver(settings)
    assert not resolver.enabled
    assert isinstance(resolver.resolve(), NullPaymentGateway)
    for method in (resolver.payout_provider, resolver.fee_reconciler):
        with pytest.raises(PaymentCapabilityError):
            method()


async def test_create_intent_replays_and_rejects_key_reuse_without_automatic_capture():
    provider = FakeProvider()
    request = intent()
    order = await provider.create_payment_intent(request)
    assert await provider.create_payment_intent(request) == order
    assert order.order_ref == synthetic_reference("order", request.intent_reference)
    assert order.amount == Money("150.00") and order.client_payload["mock"] is True
    assert await provider.fetch_payment(order_ref=order.order_ref) is None
    assert not provider.verify_payment_callback(PaymentCallback(order.order_ref, "unused", "unused"))
    with pytest.raises(IdempotencyKeyReuseError):
        await provider.create_payment_intent(replace(request, amount=Money("151")))
    with pytest.raises(IdempotencyKeyReuseError):
        await provider.create_payment_intent(replace(request, salon_id="other-salon"))


async def test_timeout_preserves_order_for_reconciliation_by_the_original_reference():
    provider = FakeProvider()
    request = intent()
    provider.simulate_timeout_after_accept("payment")
    with pytest.raises(PaymentOutcomeUnknownError):
        await provider.create_payment_intent(request)
    reference = provider.deterministic_order_ref(request.intent_reference)
    recovered = await provider.fetch_intent(reference, request)
    assert recovered == await provider.create_payment_intent(request)


async def test_pending_refund_reserves_the_amount_and_replay_never_adds_another_refund():
    provider = FakeProvider()
    order = await provider.create_payment_intent(intent())
    payment = provider.simulate_payment(order.order_ref)
    request = RefundRequest(payment.payment_ref, Money("100"), "synthetic-refund-1")
    refund = await provider.refund(request)
    assert refund.status == RefundStatus.created
    assert await provider.refund(request) == refund
    with pytest.raises(PaymentProviderError):
        await provider.refund(RefundRequest(payment.payment_ref, Money("51"), "synthetic-refund-2"))
    with pytest.raises(IdempotencyKeyReuseError):
        await provider.refund(replace(request, amount=Money("99")))
    processed = provider.simulate_refund(refund.refund_ref, RefundStatus.processed)
    assert processed.status == RefundStatus.processed
    with pytest.raises(ValueError):
        provider.simulate_refund(refund.refund_ref, RefundStatus.failed)


async def test_refund_timeout_is_recovered_without_a_second_operation():
    provider = FakeProvider()
    port: RefundProvider = provider
    order = await provider.create_payment_intent(intent())
    payment = provider.simulate_payment(order.order_ref)
    reference = port.deterministic_refund_ref("synthetic-refund-timeout")
    request = RefundRequest(payment.payment_ref, Money("150"), "synthetic-refund-timeout",
                            refund_ref=reference)
    provider.simulate_timeout_after_accept("refund")
    with pytest.raises(PaymentOutcomeUnknownError):
        await port.refund(request)
    assert await port.fetch_refund(
        refund_ref=reference, order_ref=order.order_ref, payment_ref=payment.payment_ref,
    ) == await provider.refund(request)


async def test_reference_binding_does_not_return_another_orders_capture_or_refund():
    provider = FakeProvider()
    one = await provider.create_payment_intent(intent())
    two = await provider.create_payment_intent(intent(intent_reference="synthetic-booking-2"))
    observed = provider.simulate_payment(one.order_ref)
    assert await provider.fetch_payment(payment_ref=observed.payment_ref, order_ref=two.order_ref) is None
    with pytest.raises(ValueError):
        await provider.refund(RefundRequest(observed.payment_ref, Money("1"), "r1", order_ref=two.order_ref))
    with pytest.raises(ValueError):
        await provider.fetch_payment(payment_ref="real-provider-looking-reference")


async def test_payout_acceptance_timeout_and_mock_outcome_never_verify_settlement():
    provider = FakeProvider()
    port: PayoutProvider = provider
    request = payout()
    provider.simulate_timeout_after_accept("payout")
    with pytest.raises(PaymentOutcomeUnknownError):
        await port.create_payout(request)
    pending = await port.fetch_payout(idempotency_key=request.idempotency_key)
    reference = pending.payout_reference
    assert pending.status == PayoutStatus.processing
    assert pending.provider_transfer_reference is None
    assert pending.provider_settlement_reference is None
    assert await provider.create_payout(request) == pending
    with pytest.raises(IdempotencyKeyReuseError):
        await provider.create_payout(replace(request, amount=Money("101")))
    simulated = provider.simulate_payout(reference, PayoutStatus.succeeded)
    assert simulated.provider_transfer_reference.startswith("fake_transfer_")
    assert simulated.provider_settlement_reference is None  # independent; never invented from UTR
    assert simulated.evidence_source == EvidenceSource.mock and not simulated.provider_verified
    reversed_ = provider.simulate_payout(reference, PayoutStatus.reversed)
    assert reversed_.provider_transfer_reference == simulated.provider_transfer_reference
    with pytest.raises(ValueError):
        provider.simulate_payout(reference, PayoutStatus.succeeded)


async def test_fake_declares_no_easy_split_vendor_or_schedule_capability():
    provider = FakeProvider()
    assert not provider.supports(GatewayCapability.split_settlement)
    assert not provider.supports(GatewayCapability.linked_accounts)
    assert not provider.supports(GatewayCapability.vendor_kyc)
    with pytest.raises(PaymentCapabilityError):
        await provider.register_settlement_account(SettlementAccountRequest("salon-1", "Synthetic"))
    with pytest.raises(PaymentCapabilityError):
        await provider.get_settlement_account(synthetic_reference("vendor", "salon-1"))


async def test_fee_components_preserve_unknown_zero_and_explicit_synthetic_evidence():
    provider = FakeProvider()
    reference = synthetic_reference("observation", "synthetic-statement-1")
    unknown = await provider.reconcile_fees(reference)
    assert set(unknown.fees.as_record().values()) == {None}
    assert unknown.evidence_source == EvidenceSource.unknown and not unknown.provider_verified
    fees = ProviderFees(Money("1.11"), Money("0.12"), Money("0.23"), Money("0.34"),
                        Money("0.45"), Money("0.00"))
    provider.set_fee_observation(reference, fees)
    recorded = await provider.reconcile_fees(reference)
    assert recorded.fees.as_record() == {
        "gateway_fee": "1.11", "gateway_fee_tax": "0.12", "easy_split_fee": "0.23",
        "settlement_fee": "0.34", "payout_fee": "0.45", "refund_fee": "0.00",
    }
    assert recorded.evidence_source == EvidenceSource.mock and not recorded.provider_verified
    provider.set_fee_observation(reference, fees)  # repeat observation is harmless
    with pytest.raises(IdempotencyKeyReuseError):
        provider.set_fee_observation(reference, ProviderFees(gateway_fee=Money("9")))
    assert (await provider.reconcile_fees(reference)).fees == fees


async def test_transfer_and_settlement_references_are_distinct_explicit_mock_evidence():
    provider = FakeProvider()
    reference = synthetic_reference("observation", "statement-with-references")
    transfer = synthetic_reference("transfer", "synthetic-bank-transfer")
    settlement = synthetic_reference("settlement", "synthetic-provider-settlement")
    provider.set_fee_observation(
        reference, ProviderFees(), provider_transfer_reference=transfer,
        provider_settlement_reference=settlement,
    )
    result = await provider.reconcile_fees(reference)
    assert result.provider_transfer_reference == transfer
    assert result.provider_settlement_reference == settlement
    assert transfer != settlement and not result.provider_verified
    assert transfer not in repr(result) and settlement not in repr(result)
    with pytest.raises(ValueError):
        provider.set_fee_observation(reference, ProviderFees(), provider_transfer_reference="real_ref")


@pytest.mark.parametrize("value", [1.2, "1.20", -1])
def test_fees_do_not_accept_untyped_float_or_negative_values(value):
    with pytest.raises(ValueError):
        ProviderFees(gateway_fee=value)


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_nonpositive_payout_is_rejected(amount):
    with pytest.raises(ValueError):
        payout(amount=Money(amount))


async def test_webhook_bytes_are_deterministic_and_tampering_is_rejected():
    provider = FakeProvider()
    order = await provider.create_payment_intent(intent())
    provider.simulate_payment(order.order_ref)
    webhook = provider.payment_webhook(order.order_ref)
    assert webhook == provider.payment_webhook(order.order_ref)
    assert provider.verify_webhook_signature(webhook.body, webhook.headers)
    assert provider.parse_event(webhook.body, webhook.headers).provider == "fake"
    assert not provider.verify_webhook_signature(webhook.body + b" ", webhook.headers)
    assert not provider.verify_webhook_signature(webhook.body, {"x-fake-signature": "not-hex"})
    with pytest.raises(ValueError):
        provider.parse_event(webhook.body + b" ", webhook.headers)
    assert webhook.body == (FIXTURES / "payment-captured.json").read_bytes().rstrip(b"\n")


async def test_refund_fixture_only_exists_after_explicit_simulated_processing():
    provider = FakeProvider()
    order = await provider.create_payment_intent(intent())
    payment = provider.simulate_payment(order.order_ref)
    refund = await provider.refund(RefundRequest(payment.payment_ref, Money("50"), "synthetic-refund-1"))
    with pytest.raises(ValueError):
        provider.refund_webhook(refund.refund_ref)
    provider.simulate_refund(refund.refund_ref, RefundStatus.processed)
    webhook = provider.refund_webhook(refund.refund_ref)
    assert webhook.body == (FIXTURES / "refund-processed.json").read_bytes().rstrip(b"\n")
    assert provider.parse_event(webhook.body, webhook.headers).refund_ref == refund.refund_ref


@pytest.mark.parametrize(("field", "value"), [
    ("provider", "another_provider"), ("currency", "USD"),
    ("event_type", "settlement_updated"), ("payment_ref", "non_synthetic_reference"),
    ("payment_ref", None), ("amount", 150.0),
])
def test_signed_but_invalid_mock_payload_is_rejected(field, value):
    # Public test key is deliberately documented, never a real provider credential.
    data = json.loads((FIXTURES / "payment-captured.json").read_bytes())
    data[field] = value
    data.pop("event_id")
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"))
    data["event_id"] = synthetic_reference("event", encoded)
    body = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(b"public-fake-provider-test-key-v1", body, hashlib.sha256).hexdigest()
    with pytest.raises(ValueError):
        FakeProvider().parse_event(body, {"x-fake-signature": signature})
