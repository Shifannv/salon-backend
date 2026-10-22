"""In-process API/use-case integration with FakeProvider and an in-memory ledger.

No SQL or migrations. This proves orchestration, not PostgreSQL/locking/provider behavior.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.routes import webhooks
from app.application.ports.payment_gateway import PaymentCallback
from app.application.use_cases.payments import BookingPaymentUseCases, PaymentWebhookUseCases
from app.core.exceptions import NotFoundError, register_exception_handlers
from app.domain.entities.payment import RefundStatus
from app.infrastructure.payments.fake import FakeProvider
from app.infrastructure.payments.resolver import PaymentGatewayResolver
from tests.unit.test_fake_provider import config, intent
from tests.unit.test_payment_stage1_flows import CUSTOMER, OTHER, OWNER, Ledger, Workspace


class IntakeLedger(Ledger):
    """Reuse existing fake ledger rules, adding durable-intake semantics in memory."""

    def __init__(self):
        super().__init__(total="150.00")
        self.intake = {}
        self.provider_keys = set()
        self.applied_events = 0

    async def insert_webhook_event(self, **values):
        key = (values["provider"], values["event_id"])
        if key in self.provider_keys:
            return None
        self.provider_keys.add(key)
        row_id = f"synthetic-event-{len(self.intake) + 1}"
        self.intake[row_id] = {**values, "id": row_id, "provider_name": values["provider"],
                               "processing_status": values["status"], "attempts": 0}
        return row_id

    async def claim_webhook_event(self, event_id, stale, max_attempts):
        row = self.intake[event_id]
        if row["processing_status"] != "received":
            return None
        row["processing_status"] = "processing"
        return row

    async def finish_webhook_event(self, event_id, status, error=None, *, retry=False):
        self.intake[event_id]["processing_status"] = status

    async def apply_payment_observation(self, **values):
        result = await super().apply_payment_observation(**values)
        if result == "applied":
            self.applied_events += 1
        return result

    async def apply_refund_observation(self, provider, refund_ref, status, failure_code):
        row = next((r for r in self.refunds.values() if r.get("refund_ref") == refund_ref), None)
        if row is None:
            return "unmatched"
        if row["status"] == status:
            return "ignored"
        row["status"] = status
        self._w()
        return "applied"


def build():
    ledger, provider, settings = IntakeLedger(), FakeProvider(), config()
    resolver = PaymentGatewayResolver(settings, provider)
    uc = BookingPaymentUseCases(ledger, resolver, settings, Workspace())
    return ledger, provider, resolver, settings, uc


async def test_fake_payment_and_refund_use_existing_intake_worker_and_replay_gate():
    ledger, provider, resolver, settings, uc = build()
    first = await uc.create_intent(CUSTOMER, "b1", "synthetic-checkout-1", None)
    assert first == await uc.create_intent(CUSTOMER, "b1", "synthetic-checkout-1", None)
    assert first["provider"] == "fake" and first["amount"] == "150.00"
    assert len(ledger.payments) == 1 and ledger.paid == 0
    provider.simulate_payment(first["order_ref"])
    webhook = provider.payment_webhook(first["order_ref"])
    worker = PaymentWebhookUseCases(ledger, resolver, settings)
    accepted, row_id = await worker.ingest("fake", webhook.body, dict(webhook.headers))
    assert accepted == "accepted"
    assert await worker.process(row_id) == "processed"
    assert ledger.paid == 150 and ledger.applied_events == 1
    assert await worker.ingest("fake", webhook.body, dict(webhook.headers)) == ("duplicate", None)
    assert await worker.process(row_id) == "skipped"
    refunded = await uc.refund(OWNER, "b1", first["payment_id"], None, None, "synthetic-refund-1")
    assert refunded["refunds"][0]["status"] == "created" and ledger.refunded == 0
    ref = next(iter(ledger.refunds.values()))["refund_ref"]
    provider.simulate_refund(ref, RefundStatus.processed)
    event = provider.refund_webhook(ref)
    _, row_id = await worker.ingest("fake", event.body, dict(event.headers))
    assert await worker.process(row_id) == "processed"
    assert ledger.refunded == 150
    assert await worker.ingest("fake", event.body, dict(event.headers)) == ("duplicate", None)
    assert len(ledger.refunds) == 1


async def test_existing_customer_authorization_is_enforced_with_fake_provider():
    ledger, _provider, _resolver, _settings, uc = build()
    with pytest.raises(NotFoundError):
        await uc.create_intent(OTHER, "b1", "synthetic-other-customer", None)
    assert ledger.payments == {}


def test_http_intake_rejects_tampering_and_cashfree_path_without_storing_effects():
    ledger, provider, resolver, settings, _ = build()
    # Use a checked-in deterministic event; no real provider or database is involved.
    order = asyncio.run(provider.create_payment_intent(intent()))
    provider.simulate_payment(order.order_ref)
    event = provider.payment_webhook(order.order_ref)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(webhooks.router)
    app.dependency_overrides[webhooks.get_session] = lambda: None
    app.dependency_overrides[deps.get_payment_gateway_resolver] = lambda: resolver
    with (
        patch.object(webhooks, "PaymentRepository", lambda session: ledger),
        patch.object(webhooks, "settings", settings),
        patch.object(webhooks, "process_in_background", AsyncMock()) as background,
        TestClient(app) as client,
    ):
        bad = client.post("/webhooks/fake", content=event.body + b" ", headers=event.headers)
        assert bad.status_code == 400 and ledger.intake == {}
        assert client.post("/webhooks/cashfree", content=event.body, headers=event.headers).status_code == 404
        assert ledger.intake == {}
        ok = client.post("/webhooks/fake", content=event.body, headers=event.headers)
        assert ok.status_code == 200 and ok.json() == {"status": "accepted"}
        assert client.post("/webhooks/fake", content=event.body, headers=event.headers).json() == {"status": "duplicate"}
        background.assert_awaited_once()
    assert len(ledger.intake) == 1


async def test_sdk_callback_never_marks_a_mock_payment_paid():
    ledger, provider, _resolver, _settings, uc = build()
    order = await uc.create_intent(CUSTOMER, "b1", "synthetic-checkout-1", None)
    assert not provider.verify_payment_callback(PaymentCallback(order["order_ref"], "unused", "unused"))
    assert ledger.paid == 0
