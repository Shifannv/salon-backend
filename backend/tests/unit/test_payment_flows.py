"""Webhook intake, idempotency, ledger observation, worker and migration shape.

None of this touches a database: SQL behaviour that depends on triggers is covered only
structurally (see PAYMENTS.md "Verification status").
"""

import hashlib
import hmac
import importlib.util
import json
import re
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.api.v1.routes import webhooks
from app.application.use_cases.payments import PaymentWebhookUseCases
from app.core.config import Settings
from app.core.exceptions import (
    IdempotencyInProgressError,
    IdempotencyKeyReuseError,
    register_exception_handlers,
)
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.payments import razorpay as rzp
from app.infrastructure.payments import webhook_worker
from app.infrastructure.payments.resolver import PaymentGatewayResolver

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
SECRET = "whsec_flow"


def settings(**kw) -> Settings:
    values = {
        "_env_file": None, "environment": "test", "payment_provider": "razorpay",
        "razorpay_key_id": "k", "razorpay_key_secret": "s", "razorpay_webhook_secret": SECRET,
        "razorpay_route_enabled": True, "payment_webhook_max_body_bytes": 2048,
        "payment_platform_fee_percent": Decimal("10"), "payment_commission_base": "online_amount",
    }
    values.update(kw)
    return Settings(**values)


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def captured_body(amount=50000) -> bytes:
    return json.dumps({
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": "pay_1", "order_id": "order_1", "amount": amount, "currency": "INR",
            "method": "upi"}}},
    }).encode()


class FakeRepo:
    """In-memory stand-in for the intake side of PaymentRepository."""

    def __init__(self):
        self.events: dict[str, dict] = {}
        self.commits = 0
        self.finished: list[tuple] = []
        self.observations: list[dict] = []
        self.outcome = "applied"

    async def insert_webhook_event(self, **kw):
        key = (kw["provider"], kw["event_id"])
        if key in self.events:
            return None
        self.events[key] = kw
        return f"row-{len(self.events)}"

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass

    async def claim_webhook_event(self, event_id, stale, max_attempts):
        return {"id": event_id, "provider_name": "razorpay", "attempts": 1,
                "event_type": "payment_captured", "normalized": self.claimed}

    async def apply_payment_observation(self, **kw):
        self.observations.append(kw)
        return self.outcome

    async def finish_webhook_event(self, event_id, status, error=None, *, retry=False):
        self.finished.append((event_id, status, error, retry))


@pytest.fixture
def client():
    repo = FakeRepo()
    resolver = PaymentGatewayResolver(settings())
    fapp = FastAPI()
    register_exception_handlers(fapp)
    fapp.include_router(webhooks.router)
    fapp.dependency_overrides[webhooks.get_session] = lambda: None
    fapp.dependency_overrides[deps.get_payment_gateway_resolver] = lambda: resolver
    with patch.object(webhooks, "PaymentRepository", lambda session: repo), \
            patch.object(webhooks, "process_in_background", AsyncMock()) as bg, \
            patch.object(webhooks, "settings", settings()):
        yield TestClient(fapp), repo, bg


def post(http, body: bytes, sig: str | None = None, event_id="evt_1", provider="razorpay"):
    headers = {"X-Razorpay-Signature": sig if sig is not None else sign(body),
               "X-Razorpay-Event-Id": event_id}
    return http.post(f"/webhooks/{provider}", content=body, headers=headers)


def test_valid_webhook_is_stored_committed_and_processed_after_ack(client):
    http, repo, bg = client
    response = post(http, captured_body())
    assert response.status_code == 200 and response.json() == {"status": "accepted"}
    assert len(repo.events) == 1 and repo.commits == 1
    bg.assert_called_once_with("row-1")


def test_replayed_webhook_is_a_noop(client):
    http, repo, bg = client
    post(http, captured_body())
    again = post(http, captured_body())
    assert again.status_code == 200 and again.json() == {"status": "duplicate"}
    assert len(repo.events) == 1
    assert bg.call_count == 1  # not processed a second time


def test_bad_signature_is_rejected_and_writes_nothing(client):
    http, repo, bg = client
    response = post(http, captured_body(), sig="0" * 64)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook_signature"
    assert repo.events == {} and repo.commits == 0 and bg.call_count == 0


def test_signature_is_checked_over_raw_bytes_before_parsing(client):
    http, repo, _ = client
    body = b"\xff\xfenot json"
    assert post(http, body, sig="bad").status_code == 400
    assert repo.events == {}
    # valid signature but unparseable body: acknowledged (a 4xx would disable the hook)
    assert post(http, body).json() == {"status": "ignored"}
    assert repo.events == {}


def test_unknown_event_is_recorded_ignored_and_acked_200(client):
    http, repo, bg = client
    body = b'{"event":"order.paid"}'
    response = post(http, body, event_id="evt_x")
    assert response.status_code == 200 and response.json() == {"status": "ignored"}
    assert next(iter(repo.events.values()))["status"] == "ignored"
    assert bg.call_count == 0


def test_oversized_body_is_rejected(client):
    http, repo, _ = client
    big = b"{" + b" " * 5000 + b"}"
    assert post(http, big).status_code == 413
    assert repo.events == {}


def test_wrong_provider_in_path_is_404(client):
    http, repo, _ = client
    assert post(http, captured_body(), provider="stripe").status_code == 404
    assert repo.events == {}


# ---------------------------------------------------------- applying events
def make_processor(outcome="applied", amount="500.00"):
    repo = FakeRepo()
    repo.outcome = outcome
    repo.claimed = {"event_type": "payment_captured", "order_ref": "order_1",
                    "payment_ref": "pay_1", "amount": amount, "currency": "INR",
                    "instrument": "upi", "failure_code": None}
    return repo, PaymentWebhookUseCases(repo, PaymentGatewayResolver(settings()), settings())


async def test_process_applies_capture_with_exact_amount():
    repo, uc = make_processor()
    assert await uc.process("e1") == "processed"
    assert repo.observations[0]["status"] == "captured"
    assert repo.observations[0]["amount"] == Decimal("500.00")
    assert repo.finished == [("e1", "processed", None, False)]


async def test_amount_mismatch_fails_event_loudly_without_retry():
    repo, uc = make_processor(outcome="mismatch")
    assert await uc.process("e1") == "failed"
    assert repo.finished == [("e1", "failed", "mismatch", False)]


async def test_overcollection_fails_event_without_retry():
    repo, uc = make_processor(outcome="overcollection")
    assert await uc.process("e1") == "failed"
    assert repo.finished[0][2] == "overcollection" and repo.finished[0][3] is False


async def test_unmatched_reference_is_ignored_not_failed():
    _, uc = make_processor(outcome="unmatched")
    assert await uc.process("e1") == "ignored"


async def test_exception_schedules_backoff_retry():
    repo, uc = make_processor()
    repo.apply_payment_observation = AsyncMock(side_effect=RuntimeError("boom"))
    assert await uc.process("e1") == "failed"
    assert repo.finished == [("e1", "failed", "RuntimeError", True)]


async def test_unclaimable_event_is_skipped():
    repo, uc = make_processor()
    repo.claim_webhook_event = AsyncMock(return_value=None)
    assert await uc.process("e1") == "skipped"
    assert repo.observations == []


# ------------------------------------------------- repository SQL behaviours
class _Result:
    def __init__(self, row=None, first=None, scalar=None):
        self._row, self._first, self._scalar = row, first, scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self._row

    def one(self):
        return self._row

    def first(self):
        return self._first

    def scalar_one(self):
        return self._scalar


def repo_with(*results):
    session = MagicMock()
    session.execute = AsyncMock(side_effect=list(results))
    session.begin_nested = MagicMock(return_value=MagicMock(
        __aenter__=AsyncMock(), __aexit__=AsyncMock(return_value=False)))
    return PaymentRepository(session), session


async def test_idempotency_first_use_reserves():
    repo, _ = repo_with(_Result(), _Result(first=("id",)))
    assert await repo.begin_idempotent("u", "intent:b", "key-12345", "fp", 86400) is None


async def test_idempotency_replays_completed_response():
    repo, _ = repo_with(
        _Result(), _Result(first=None),
        _Result(row={"request_fingerprint": "fp", "response_body": {"payment_id": "p1"}}),
    )
    assert await repo.begin_idempotent("u", "s", "key-12345", "fp", 60) == {"payment_id": "p1"}


async def test_idempotency_mismatched_fingerprint_is_409():
    repo, _ = repo_with(
        _Result(), _Result(first=None),
        _Result(row={"request_fingerprint": "other", "response_body": {"x": 1}}),
    )
    with pytest.raises(IdempotencyKeyReuseError):
        await repo.begin_idempotent("u", "s", "key-12345", "fp", 60)


async def test_idempotency_unfinished_original_is_in_progress():
    repo, _ = repo_with(
        _Result(), _Result(first=None),
        _Result(row={"request_fingerprint": "fp", "response_body": None}),
    )
    with pytest.raises(IdempotencyInProgressError):
        await repo.begin_idempotent("u", "s", "key-12345", "fp", 60)


async def test_observation_amount_mismatch_fails_row_and_never_captures():
    row = {"id": "p1", "booking_id": "b1", "salon_id": "s1", "status": "created",
           "amount": Decimal("500.00"), "currency": "INR"}
    repo, session = repo_with(
        _Result(row={"id": "p1", "booking_id": "b1"}), _Result(row={"total_price": Decimal("500")}),
        _Result(row=row), _Result(), _Result())
    outcome = await repo.apply_payment_observation(
        provider="razorpay", order_ref="o", payment_ref="pay", status="captured",
        amount=Decimal("400.00"), currency="INR", instrument=None, failure_code=None)
    assert outcome == "mismatch"
    update_params = session.execute.await_args_list[-2].args[1]
    assert update_params["s"] == "failed" and update_params["f"] == "amount_mismatch"
    anomaly_sql = str(session.execute.await_args_list[-1].args[0]).lower()
    assert "insert into payment_anomalies" in anomaly_sql


async def test_observation_out_of_order_event_is_ignored():
    row = {"id": "p1", "booking_id": "b1", "salon_id": "s1", "status": "captured",
           "amount": Decimal("500.00"), "currency": "INR"}
    repo, session = repo_with(
        _Result(row={"id": "p1", "booking_id": "b1"}), _Result(row={"total_price": Decimal("500")}),
        _Result(row=row))
    outcome = await repo.apply_payment_observation(
        provider="razorpay", order_ref="o", payment_ref="pay", status="failed",
        amount=None, currency=None, instrument=None, failure_code="x")
    assert outcome == "ignored" and session.execute.await_count == 3  # no write happened


async def test_observation_unknown_reference_is_unmatched():
    repo, _ = repo_with(_Result(row=None))
    assert await repo.apply_payment_observation(
        provider="razorpay", order_ref="o", payment_ref=None, status="captured",
        amount=None, currency=None, instrument=None, failure_code=None) == "unmatched"


# ------------------------------------------------------------------- worker
async def test_worker_claim_sql_is_atomic_and_backoff_is_exponential():
    repo, session = repo_with(_Result(row=None))
    assert await repo.claim_webhook_event("e1", 600, 8) is None
    claim_sql = str(session.execute.await_args.args[0]).lower()
    assert "update payment_webhook_events" in claim_sql and "attempts = attempts + 1" in claim_sql
    assert "attempts < :max" in claim_sql
    repo, session = repo_with(_Result())
    await repo.finish_webhook_event("e1", "failed", "X", retry=True)
    finish_sql = str(session.execute.await_args.args[0]).lower()
    assert "power(2, attempts) * 10" in finish_sql and "3600" in finish_sql


async def test_drain_processes_each_due_event_once(monkeypatch):
    processed = []

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class FakeRepoW:
        def __init__(self, session):
            pass

        async def list_due_webhook_event_ids(self, stale, max_attempts, limit):
            return ["a", "b"]

    class FakeUC:
        def __init__(self, repo, resolver, cfg):
            pass

        async def process(self, event_id):
            processed.append(event_id)

    monkeypatch.setattr(webhook_worker, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(webhook_worker, "PaymentRepository", FakeRepoW)
    monkeypatch.setattr(webhook_worker, "PaymentWebhookUseCases", FakeUC)
    assert await webhook_worker.drain_webhook_events() == 2
    assert processed == ["a", "b"]


async def test_reconcile_applies_provider_truth_and_expires_unpaid_intents():
    class Gateway:
        def __init__(self):
            self.orders = []

        async def fetch_payment(self, *, payment_ref=None, order_ref=None):
            self.orders.append(order_ref)
            if order_ref == "o_paid":
                return rzp.ProviderPayment(
                    "razorpay", "pay_9", "o_paid", rzp.LedgerStatus.captured,
                    rzp.from_paise(50000), "INR")
            return None

    gateway = Gateway()
    resolver = PaymentGatewayResolver(settings(), gateway)
    repo = FakeRepo()
    expired, touched = [], []
    repo.list_stale_intents = AsyncMock(return_value=[
        {"id": "1", "provider": "razorpay", "order_ref": "o_paid", "is_expired": False},
        {"id": "2", "provider": "razorpay", "order_ref": "o_dead", "is_expired": True},
    ])
    repo.expire_intent = AsyncMock(side_effect=lambda i: expired.append(i))
    repo.touch_intent = AsyncMock(side_effect=lambda i: touched.append(i))
    uc = PaymentWebhookUseCases(repo, resolver, settings())
    assert await uc.reconcile_stale_intents() == 2
    assert repo.observations[0]["status"] == "captured"
    assert expired == ["2"]


# -------------------------------------------------------- manual receipt path
def test_platform_repository_no_longer_writes_payment_status_directly():
    source = (Path(__file__).resolve().parents[2] / "app/infrastructure/db/repositories"
              / "platform_repository.py").read_text(encoding="utf-8")
    assert not re.search(r"set\s+payment_status", source)
    assert "payment_method = 'cash'" not in source
    assert "insert into booking_payments" in source


async def test_manual_receipt_inserts_ledger_row_and_refuses_while_gateway_open():
    from app.core.exceptions import PaymentInProgressError
    from app.infrastructure.db.repositories.platform_repository import PlatformRepository

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[_Result(first=(1,))])
    with pytest.raises(PaymentInProgressError):
        await PlatformRepository(session)._insert_manual_payment(
            booking_id="b", actor_id="a", method="cash")
    session.execute = AsyncMock(side_effect=[_Result(first=None), _Result()])
    await PlatformRepository(session)._insert_manual_payment(
        booking_id="b", actor_id="a", method="online")
    sql = str(session.execute.await_args.args[0]).lower()
    assert "insert into booking_payments" in sql and "'manual'" in sql
    assert session.execute.await_args.args[1]["method"] == "online"


async def test_record_payment_requires_can_record_payment():
    from app.application.use_cases.platform import BookingUseCases
    from app.core.exceptions import ForbiddenError
    from tests.conftest import make_mock_repo, make_super_admin

    with pytest.raises(ForbiddenError):
        await BookingUseCases(make_mock_repo()).record_payment(make_super_admin(), "b", "cash")


# --------------------------------------------------------------- migrations
def load(name):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(module, fn):
    statements = []
    with patch.object(module.op, "execute", side_effect=lambda s: statements.append(str(s))):
        getattr(module, fn)()
    return "\n".join(statements).lower()


def test_0026_chain_tables_and_security_shape():
    m = load("0026_booking_payments")
    assert m.revision == "0026_booking_payments" and m.down_revision == "0025_salon_payout_accounts"
    sql = run(m, "upgrade")
    for table in ("booking_payments", "payment_refunds", "payment_webhook_events",
                  "payment_idempotency_keys", "payment_provider_accounts"):
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
        assert f"revoke all on public.{table} from public, anon, authenticated" in sql
        assert f"grant all on public.{table} to postgres, service_role" in sql
    assert "uq_booking_payments_one_open_intent" in sql
    assert "where channel = 'gateway' and status in ('created', 'authorized')" in sql
    assert "unique (provider_name, provider_event_reference)" in sql
    assert "unique (actor_id, scope, idempotency_key)" in sql
    assert "'pay_at_salon', 'pay_advance', 'pay_full'" in sql
    assert "payment_overcollection" in sql and "errcode = '23514'" in sql
    assert "payment_recorded_at" in sql  # set by the recompute, not by auth.uid()
    assert "create or replace function public.recompute_booking_payment_state" in sql


def test_0026_does_not_widen_the_enums():
    sql = run(load("0026_booking_payments"), "upgrade")
    assert "alter type" not in sql and "add value" not in sql


def test_0026_downgrade_restores_narrow_check_and_drops_everything():
    sql = run(load("0026_booking_payments"), "downgrade")
    assert "payment_preference = 'pay_at_salon'" in sql
    assert "drop table if exists public.booking_payments" in sql
    assert "drop column if exists paid_amount" in sql


def test_0027_chain_and_hardening_shape():
    m = load("0027_payout_account_audit")
    assert m.down_revision == "0026_booking_payments"
    sql = run(m, "upgrade")
    assert "updated_by" in sql and "set_audit_actor()" in sql
    assert "salon_payout_account_history" in sql
    assert "right(r.bank_account_number, 4)" in sql
    assert "'bank_account_number', r.bank_account_number" not in sql  # last4 only in history
    assert "security definer" in sql and "salon_payout_account_masked" in sql
    assert "ck_payout_bank_triple" in sql and "bank_account_fingerprint" in sql
    assert "revoke all on public.salon_payout_account_history" in sql
    down = run(m, "downgrade")
    assert "drop table if exists public.salon_payout_account_history" in down


def test_migration_heads_are_linear():
    revisions = {}
    for path in VERSIONS.glob("0*.py"):
        text = path.read_text(encoding="utf-8")
        rev = re.search(r'^revision[^=]*=\s*"([^"]+)"', text, re.MULTILINE).group(1)
        down = re.search(r'^down_revision[^=]*=\s*"([^"]+)"', text, re.MULTILINE)
        revisions[rev] = down.group(1) if down else None
    parents = [d for d in revisions.values() if d]
    assert len(parents) == len(set(parents)), "two revisions share a parent (branch)"
    assert [r for r in revisions if r not in parents] == ["0043_no_show_attendance_guards"]
