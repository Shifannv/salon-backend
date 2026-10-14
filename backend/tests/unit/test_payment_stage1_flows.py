# ruff: noqa: RUF059
"""Use-case level financial flows against an in-memory ledger and a scriptable gateway.

The fake repository mirrors the SQL rules that matter here (idempotency, one open intent,
overcollection recording, refund kinds) and, crucially, tracks an uncommitted-writes flag so the
tests can assert that every provider call happens only AFTER a commit. The real SQL behaviour is
covered separately in tests/integration/test_payment_ledger_sql.py (opt-in, needs PostgreSQL).
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.ports.payment_gateway import (
    PaymentGateway,
    PaymentIntent,
    ProviderPayment,
    RefundResult,
    SettlementAccount,
)
from app.application.use_cases.payments import (
    BookingPaymentUseCases,
    PaymentWebhookUseCases,
    SettlementRegistrationDetails,
)
from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    IdempotencyInProgressError,
    IdempotencyKeyReuseError,
    NotFoundError,
    PaymentAmountMismatchError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
)
from app.domain.entities.payment import (
    GatewayCapability as C,
)
from app.domain.entities.payment import (
    LedgerStatus,
    OnboardingStatus,
    RefundStatus,
)
from app.domain.entities.profile import Role
from app.domain.value_objects.money import Money
from app.infrastructure.payments.resolver import PaymentGatewayResolver
from tests.conftest import make_profile

D = Decimal
CUSTOMER = make_profile("cust-1", Role.customer)
OTHER = make_profile("cust-2", Role.customer)
OWNER = make_profile("owner-1", Role.owner)
SETTLED = {"captured", "partially_refunded", "refunded"}


def settings(**kw) -> Settings:
    values = {
        "_env_file": None, "environment": "test", "payment_provider": "cashfree", "cashfree_enabled": True,
        "cashfree_client_id": "cid", "cashfree_client_secret": "sec",
        "cashfree_easy_split_enabled": True, "payment_platform_fee_percent": D("10"),
        "payment_commission_base": "online_amount", "payment_commission_policy_version": "v7",
    }
    values.update(kw)
    return Settings(**values)


# --------------------------------------------------------------------------- fakes
class Ledger:
    """In-memory PaymentRepository stand-in with uncommitted-write tracking."""

    def __init__(self, total="1000.00", deposit=None):
        self.dirty = False
        self.commits = 0
        self.idem: dict[tuple, dict] = {}
        self.payments: dict[str, dict] = {}
        self.refunds: dict[str, dict] = {}
        self.anomalies: list[dict] = []
        self.accounts: dict[tuple, dict] = {}
        self.audit: list[dict] = []
        self.events: list[str] = []
        self.booking = {
            "id": "b1", "salon_id": "salon-1", "customer_id": "cust-1", "owner_id": "owner-1",
            "status": "confirmed", "total_price": D(total), "deposit_amount": deposit and D(deposit),
            "currency": "INR", "payment_preference": "pay_full", "actor_is_staff": False,
        }

    # -- plumbing
    def _w(self):
        self.dirty = True

    async def commit(self):
        self.commits += 1
        self.dirty = False
        self.events.append("commit")

    async def rollback(self):
        self.dirty = False

    async def set_actor(self, actor_id):
        pass

    # -- idempotency
    async def begin_idempotent(self, actor, scope, key, fingerprint, ttl):
        k = (actor, scope, key)
        if k in self.idem:
            if self.idem[k]["fp"] != fingerprint:
                raise IdempotencyKeyReuseError("reuse")
            if self.idem[k]["body"] is None:
                raise IdempotencyInProgressError("busy")
            return self.idem[k]["body"]
        self.idem[k] = {"fp": fingerprint, "body": None}
        self._w()
        return None

    async def finish_idempotent(self, actor, scope, key, status, body):
        self.idem[(actor, scope, key)]["body"] = body
        self._w()

    async def release_idempotent(self, actor, scope, key):
        if self.idem.get((actor, scope, key), {}).get("body", 1) is None:
            del self.idem[(actor, scope, key)]
        self._w()

    # -- derived booking state
    def _settled(self):
        return [p for p in self.payments.values() if p["status"] in SETTLED]

    @property
    def paid(self):
        return sum((p["amount"] - p["overcollected_amount"] for p in self._settled()), D(0))

    @property
    def refunded(self):
        return sum((r["amount"] for r in self.refunds.values()
                    if r["status"] == "processed" and not r["applies_to_excess"]), D(0))

    def _booking_view(self):
        paid = self.paid
        return {**self.booking, "paid_amount": paid, "refunded_amount": self.refunded,
                "payment_status": "paid" if paid - self.refunded >= self.booking["total_price"] else "unpaid"}

    async def lock_booking(self, booking_id, actor_id):
        return self._booking_view()

    read_booking = lock_booking

    # -- intents
    async def expire_stale_open_intents(self, booking_id):
        for p in self.payments.values():
            if p["status"] in {"created", "authorized"} and p["expires_at"] < datetime.now(UTC):
                p["status"] = "expired"

    def _open(self):
        return [p for p in self.payments.values() if p["status"] in {"created", "authorized"}]

    async def get_open_intent(self, booking_id):
        return (self._open() or [None])[0]

    async def get_resumable_intent(self, booking_id):
        for p in self._open():
            if p["status"] == "created" and p["provider_order_confirmed_at"] is None:
                return p
        return None

    async def get_provider_account(self, salon_id, provider):
        return self.accounts.get((salon_id, provider))

    async def commission_allocated(self, booking_id):
        live = sum((p["platform_commission_amount"] for p in self.payments.values()
                    if p["status"] in {"created", "authorized"} | SETTLED), D(0))
        reversed_ = sum((r["commission_reversal_amount"] for r in self.refunds.values()
                         if r["status"] == "processed"), D(0))
        return live - reversed_

    async def insert_intent(self, *, booking, actor_id, purpose, amount, commission_amount,
                            commission_rate_percent, commission_base, commission_policy_version,
                            provider, settlement_model, intent_reference, order_ref, expires_in_seconds):
        pid = f"pay-{len(self.payments) + 1}"
        self.payments[pid] = {
            "id": pid, "booking_id": booking["id"], "salon_id": booking["salon_id"], "payer_id": actor_id,
            "channel": "gateway", "purpose": purpose, "settlement_model": settlement_model,
            "provider": provider, "method": None, "instrument": None, "amount": amount,
            "currency": "INR", "status": "created", "overcollected_amount": D("0.00"),
            "failure_code": None, "expires_at": datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
            "captured_at": None, "created_at": datetime.now(UTC), "order_ref": order_ref,
            "payment_ref": None, "intent_reference": intent_reference,
            "platform_commission_amount": commission_amount,
            "commission_rate_percent": commission_rate_percent, "commission_base": commission_base,
            "commission_policy_version": commission_policy_version,
            "provider_order_confirmed_at": None,
        }
        self._w()
        return pid

    async def confirm_intent_order(self, payment_id, order_ref, provider_session_id=None):
        p = self.payments[payment_id]
        p["order_ref"] = p["order_ref"] or order_ref
        p["provider_order_confirmed_at"] = datetime.now(UTC)
        self._w()

    async def fail_intent(self, payment_id, code):
        p = self.payments[payment_id]
        if p["status"] in {"created", "authorized"} and p["provider_order_confirmed_at"] is None:
            p["status"], p["failure_code"] = "failed", code
        self._w()

    async def cancel_open_intent(self, booking_id):
        for p in self._open():
            p["status"] = "cancelled"
            return p
        return None

    async def get_payment_by_order(self, booking_id, order_ref):
        return next((p for p in self.payments.values() if p["order_ref"] == order_ref), None)

    async def get_payment(self, booking_id, payment_id):
        return self.payments.get(payment_id)

    async def list_payments(self, booking_id):
        return list(self.payments.values())

    async def list_refunds(self, booking_id):
        return [{**r, "reason": None, "created_at": datetime.now(UTC), "processed_at": None}
                for r in self.refunds.values()]

    # -- observation (mirrors the SQL rules)
    async def apply_payment_observation(self, *, provider, order_ref, payment_ref, status, amount,
                                        currency, instrument, failure_code):
        row = next((p for p in self.payments.values() if p["provider"] == provider and (
            (order_ref and p["order_ref"] == order_ref) or (payment_ref and p["payment_ref"] == payment_ref))), None)
        if row is None:
            return "unmatched"
        rank = {"created": 0, "authorized": 1, "failed": 1, "cancelled": 1, "expired": 1, "captured": 2}
        if rank[status] <= rank[row["status"]]:
            return "ignored"
        outcome = "applied"
        if status in {"authorized", "captured"} and (
                (amount is not None and amount != row["amount"]) or (currency and currency != row["currency"])):
            row.update(status="failed", failure_code="amount_mismatch")
            self.anomalies.append({"kind": "amount_mismatch", "payment_id": row["id"]})
            self._w()
            return "mismatch"
        if status == "captured":
            owed = max(self.booking["total_price"] - (self.paid - self.refunded), D(0))
            excess = max(row["amount"] - owed, D(0))
            row["overcollected_amount"] = excess
            row["captured_at"] = datetime.now(UTC)
            if excess > 0:
                outcome = "overcollected"
                self.anomalies.append({"kind": "overcollection", "payment_id": row["id"], "amount": excess})
        row.update(status=status, payment_ref=payment_ref or row["payment_ref"], instrument=instrument,
                   failure_code=failure_code)
        self._w()
        return outcome

    async def add_manual_cash(self, amount):
        self.payments[f"cash-{len(self.payments)}"] = {
            "id": f"cash-{len(self.payments)}", "booking_id": "b1", "salon_id": "salon-1", "channel": "manual",
            "purpose": "full", "settlement_model": "offline", "provider": None, "method": "cash",
            "instrument": None, "amount": D(amount), "currency": "INR", "status": "captured",
            "overcollected_amount": D("0.00"), "failure_code": None, "expires_at": None,
            "captured_at": datetime.now(UTC), "created_at": datetime.now(UTC), "order_ref": None,
            "payment_ref": None, "platform_commission_amount": D("0.00"), "payer_id": None}

    # -- reconcile
    async def list_stale_intents(self, after, limit):
        return [{"id": p["id"], "provider": p["provider"], "order_ref": p["order_ref"],
                 "is_expired": p["expires_at"] < datetime.now(UTC)}
                for p in self._open() if p["order_ref"]]

    async def expire_intent(self, pid):
        self.payments[pid]["status"] = "expired"

    async def touch_intent(self, pid):
        pass

    # -- refunds
    async def get_refund_by_key(self, payment_id, key):
        return next((r for r in self.refunds.values() if r["payment_id"] == payment_id and r["key"] == key), None)

    async def refund_totals(self, payment_id):
        live = [r for r in self.refunds.values() if r["payment_id"] == payment_id and r["status"] != "failed"]
        return {"regular": sum((r["amount"] for r in live if not r["applies_to_excess"]), D(0)),
                "excess": sum((r["amount"] for r in live if r["applies_to_excess"]), D(0)),
                "reversed": sum((r["commission_reversal_amount"] for r in live), D(0))}

    async def insert_refund(self, *, payment, actor_id, amount, reason, idempotency_key,
                            commission_reversal=D("0.00"), applies_to_excess=False, refund_id=None,
                            refund_ref=None):
        rid = refund_id or str(uuid.uuid4())
        self.refunds[rid] = {"id": rid, "payment_id": payment["id"], "amount": amount, "status": "created",
                             "key": idempotency_key, "refund_ref": refund_ref,
                             "commission_reversal_amount": commission_reversal,
                             "applies_to_excess": applies_to_excess, "provider": payment["provider"]}
        self._w()
        return rid

    async def update_refund(self, refund_id, refund_ref, status, failure_code):
        r = self.refunds[refund_id]
        if r["status"] == "created":
            r.update(status=status, refund_ref=refund_ref or r["refund_ref"], failure_code=failure_code)
        self._w()

    async def list_open_refunds(self, after, limit):
        return [{"id": r["id"], "provider": r["provider"], "refund_ref": r["refund_ref"], "amount": r["amount"],
                 "order_ref": self.payments[r["payment_id"]]["order_ref"], "payment_ref": "p"}
                for r in self.refunds.values() if r["status"] == "created" and r["refund_ref"]]

    async def touch_refund(self, rid):
        pass

    async def record_anomaly(self, **kw):
        self.anomalies.append(kw)

    async def find_salon_by_account(self, provider, ref):
        return "salon-1"

    # -- accounts
    async def find_owner_salon_id(self, actor_id):
        return "salon-1"

    async def get_payout_holder_name(self, salon_id):
        return "Saved Holder"

    async def begin_registration(self, salon_id, provider, actor_id, vendor_ref_for):
        acct = self.accounts.get((salon_id, provider))
        if acct and acct["onboarding_status"] == "pending":
            return {"vendor_ref": acct["provider_account_ref"], "generation": acct["gen"], "previous_status": "pending"}
        gen = (acct["gen"] + 1) if acct else 1
        previous = acct["onboarding_status"] if acct else None
        self.accounts[(salon_id, provider)] = {"provider_account_ref": vendor_ref_for(gen), "gen": gen,
                                               "onboarding_status": "pending", "requirements": []}
        self.audit.append({"action": "re_registered" if acct else "registered", "previous": previous})
        self._w()
        return {"vendor_ref": vendor_ref_for(gen), "generation": gen, "previous_status": previous}

    async def set_account_result(self, salon_id, provider, status, requirements, actor_id, account_ref=None):
        a = self.accounts[(salon_id, provider)]
        a.update(onboarding_status=status, requirements=requirements)
        a["provider_account_ref"] = account_ref or a["provider_account_ref"]
        self._w()

    async def add_account_audit(self, **kw):
        self.audit.append({"action": kw["action"], "previous": kw["previous_status"]})


class Workspace:
    async def get_workspace_salon(self, actor_id):
        return {"is_active": True, "profile_completed": True, "approval_status": "approved"}


class FakeGateway(PaymentGateway):
    def __init__(self, ledger, name="cashfree", caps=None, deterministic=True):
        self.ledger = ledger
        self._name = name
        self.caps = caps if caps is not None else {
            C.online_collection, C.refunds, C.server_status_refresh, C.split_settlement,
            C.linked_accounts, C.vendor_kyc}
        self.deterministic = deterministic
        self.create_script: list[tuple] = []
        self.refund_script: list[tuple] = []
        self.register_script: list[tuple] = []
        self.orders: dict[str, PaymentIntent] = {}
        self.payments: dict[str, ProviderPayment | None] = {}
        self.refund_results: dict[str, RefundResult] = {}
        self.fetch_intent_down = False
        self.calls: list[tuple] = []
        self.dirty_at_call: list[bool] = []
        self.requests: list = []
        self.signature_ok = True

    @property
    def provider_name(self):
        return self._name

    def supports(self, capability):
        return capability in self.caps

    def client_config(self):
        from app.application.ports.payment_gateway import ClientConfig
        return ClientConfig(enabled=True, provider=self._name)

    def deterministic_order_ref(self, intent_reference):
        return intent_reference if self.deterministic else None

    def deterministic_refund_ref(self, refund_id):
        return "rf" + refund_id.replace("-", "") if self.deterministic else None

    def _note(self, what):
        self.calls.append(what)
        self.dirty_at_call.append(self.ledger.dirty)

    async def create_payment_intent(self, request):
        self._note("create")
        self.requests.append(request)
        action = self.create_script.pop(0) if self.create_script else ("ok",)
        order_ref = request.intent_reference if self.deterministic else "gen_" + request.intent_reference
        intent = PaymentIntent(self._name, order_ref, request.intent_reference, request.amount,
                               request.currency, {"payment_session_id": "sess"})
        if action[0] == "ok" or (action[0] == "unknown" and action[1]):
            self.orders[order_ref] = intent
        if action[0] == "unknown":
            raise PaymentOutcomeUnknownError("timeout")
        if action[0] == "reject":
            raise PaymentProviderError("rejected")
        return intent

    async def fetch_intent(self, order_ref, request):
        self._note("fetch_intent")
        if self.fetch_intent_down:
            raise PaymentOutcomeUnknownError("down")
        return self.orders.get(order_ref)

    def verify_payment_callback(self, callback):
        return self.signature_ok

    def verify_webhook_signature(self, raw_body, headers):
        return True

    def parse_event(self, raw_body, headers):
        raise ValueError

    async def fetch_payment(self, *, payment_ref=None, order_ref=None):
        self._note("fetch_payment")
        return self.payments.get(order_ref) or next(
            (p for p in self.payments.values() if p and p.payment_ref == payment_ref), None)

    async def refund(self, request):
        self._note("refund")
        self.requests.append(request)
        action = self.refund_script.pop(0) if self.refund_script else ("ok",)
        ref = request.refund_ref or "prov_ref"
        if action[0] == "unknown":
            raise PaymentOutcomeUnknownError("timeout")
        if action[0] == "reject":
            raise PaymentProviderError("rejected")
        result = RefundResult(self._name, ref, RefundStatus.processed, request.amount, request.payment_ref)
        self.refund_results[ref] = result
        return result

    async def fetch_refund(self, *, refund_ref, order_ref, payment_ref):
        self._note("fetch_refund")
        return self.refund_results.get(refund_ref)

    async def register_settlement_account(self, request):
        self._note("register")
        self.requests.append(request)
        action = self.register_script.pop(0) if self.register_script else ("ok",)
        if action[0] == "unknown":
            raise PaymentOutcomeUnknownError("timeout")
        if action[0] == "reject":
            raise PaymentProviderError("rejected")
        return SettlementAccount(self._name, request.vendor_ref or "acc_x", OnboardingStatus.pending,
                                 ("Your KYC details are being reviewed.",))

    async def get_settlement_account(self, account_ref):
        return SettlementAccount(self._name, account_ref, OnboardingStatus.active)


def build(total="1000.00", deposit=None, **kw):
    ledger = Ledger(total, deposit)
    gateway = FakeGateway(ledger, **{k: kw.pop(k) for k in ("name", "caps", "deterministic") if k in kw})
    cfg = settings(**kw)
    ledger.accounts[("salon-1", "cashfree")] = {
        "provider_account_ref": "vendor_1", "onboarding_status": "active", "requirements": [], "gen": 1}
    resolver = PaymentGatewayResolver(cfg, gateway)
    uc = BookingPaymentUseCases(ledger, resolver, cfg, Workspace())
    return ledger, gateway, uc, resolver, cfg


def capture(order, amount, pid="pay_1", status=LedgerStatus.captured, **kw):
    return ProviderPayment("cashfree", pid, order, status, Money(D(amount)), "INR", **kw)


KEY = "idem-key-0001"


# ============================================================ commission snapshot
async def test_intent_snapshots_rate_base_version_and_amount():
    ledger, gateway, uc, *_ = build("1000.00")
    await uc.create_intent(CUSTOMER, "b1", KEY, None)
    row = next(iter(ledger.payments.values()))
    assert row["platform_commission_amount"] == D("100.00")
    assert (row["commission_rate_percent"], row["commission_base"], row["commission_policy_version"]) == (
        D("10"), "online_amount", "v7")
    assert gateway.requests[0].platform_fee.amount == D("100.00")  # the payee share is amount - fee


async def test_booking_total_base_allocates_across_deposit_and_balance_never_above_total():
    ledger, gateway, uc, *_ = build("1000.00", deposit="30.00", payment_commission_base="booking_total",
                                    payment_platform_fee_percent=D("10"))
    ledger.booking["payment_preference"] = "pay_advance"
    first = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    assert first["purpose"] == "deposit"
    # whole-booking commission is 100.00 but a 30.00 deposit can carry at most 30.00
    assert next(iter(ledger.payments.values()))["platform_commission_amount"] == D("30.00")
    gateway.payments[first["order_ref"]] = capture(first["order_ref"], "30.00")
    await uc.refresh(CUSTOMER, "b1", first["order_ref"], "refresh-key-1")
    second = await uc.create_intent(CUSTOMER, "b1", "idem-key-0002", None)
    assert second["purpose"] == "balance" and second["amount"] == "970.00"
    commissions = [p["platform_commission_amount"] for p in ledger.payments.values()]
    assert commissions == [D("30.00"), D("70.00")] and sum(commissions) == D("100.00")


async def test_balance_absorbs_processing_charge_rounding_residue():
    ledger, gateway, uc, *_ = build("0.20")
    async def booking_view(*args):
        return {**ledger._booking_view(), "paid_amount": D("0.10"),
                "checkout_policy_version": "customer_processing_v1"}
    async def allocated(*args):
        return D("0.01")  # The deposit already carried the whole rounded fee.
    ledger.lock_booking = booking_view
    ledger.processing_charge_allocated = allocated
    result = await uc.create_intent(CUSTOMER, "b1", KEY, "balance")
    assert result["amount"] == "0.10"
    assert gateway.requests[0].amount.amount == D("0.10")


async def test_missing_commission_policy_fails_closed():
    ledger, gateway, uc, _, cfg = build()
    cfg.payment_platform_fee_percent = None
    with pytest.raises(PaymentProviderNotConfiguredError):
        await uc.create_intent(CUSTOMER, "b1", KEY, None)
    assert gateway.calls == [] and ledger.payments == {}


async def test_snapshot_is_never_recomputed_and_refund_reverses_it_proportionally():
    ledger, gateway, uc, _, cfg = build("1000.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    cfg.payment_platform_fee_percent = D("50")  # the business changes the rate later
    cfg.payment_commission_base = "booking_total"
    pid = intent["payment_id"]
    await uc.refund(OWNER, "b1", pid, D("250.00"), None, "refund-key-1")
    await uc.refund(OWNER, "b1", pid, None, None, "refund-key-2")
    r1, r2 = list(ledger.refunds.values())
    assert (r1["amount"], r1["commission_reversal_amount"]) == (D("250.00"), D("25.00"))
    assert (r2["amount"], r2["commission_reversal_amount"]) == (D("750.00"), D("75.00"))
    assert ledger.payments[pid]["platform_commission_amount"] == D("100.00")


async def test_full_refund_reversal_absorbs_rounding_residue():
    ledger, gateway, uc, *_ = build("100.00", payment_platform_fee_percent=D("7.5"))
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "100.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    for i, amount in enumerate(("33.33", "33.33", None)):
        await uc.refund(OWNER, "b1", intent["payment_id"], amount and D(amount), None, f"refund-key-{i}")
    assert sum(r["commission_reversal_amount"] for r in ledger.refunds.values()) == D("7.50")


# ====================================================================== crash safety
async def test_intent_identity_is_committed_before_the_provider_is_called():
    ledger, gateway, uc, *_ = build()
    result = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    assert gateway.dirty_at_call == [False]  # nothing uncommitted when the provider call was made
    row = ledger.payments[result["payment_id"]]
    assert row["order_ref"] == row["intent_reference"]  # deterministic order id persisted up front
    assert row["provider_order_confirmed_at"] is not None


async def test_timeout_where_provider_created_the_order_recovers_by_order_id():
    ledger, gateway, uc, *_ = build()
    gateway.create_script = [("unknown", True)]  # the provider DID create it, we never heard back
    result = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    assert gateway.calls == ["create", "fetch_intent"]
    assert result["order_ref"] == next(iter(ledger.payments.values()))["intent_reference"]
    assert len(ledger.payments) == 1


async def test_unrecoverable_timeout_leaves_one_row_and_a_retry_resumes_it():
    ledger, gateway, uc, *_ = build()
    gateway.create_script = [("unknown", False)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.create_intent(CUSTOMER, "b1", KEY, None)
    (row,) = ledger.payments.values()
    assert row["status"] == "created" and row["provider_order_confirmed_at"] is None
    assert ledger.idem == {}  # the key was released, so the same key can be retried
    result = await uc.create_intent(CUSTOMER, "b1", KEY, None)  # retry, same key
    assert len(ledger.payments) == 1 and result["payment_id"] == row["id"]
    assert gateway.requests[0].intent_reference == gateway.requests[1].intent_reference
    assert gateway.dirty_at_call == [False] * 4  # create, recover-lookup, resume-lookup, create


async def test_a_different_purpose_cannot_hijack_an_unacknowledged_intent():
    ledger, gateway, uc, *_ = build(deposit="300.00")
    gateway.create_script = [("unknown", False)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.create_intent(CUSTOMER, "b1", KEY, "full")
    with pytest.raises(Exception, match="already open"):
        await uc.create_intent(CUSTOMER, "b1", "idem-key-0002", "deposit")


async def test_definitive_provider_rejection_fails_the_row_and_frees_the_booking():
    ledger, gateway, uc, *_ = build()
    gateway.create_script = [("reject",)]
    with pytest.raises(PaymentProviderError):
        await uc.create_intent(CUSTOMER, "b1", KEY, None)
    (row,) = ledger.payments.values()
    assert row["status"] == "failed" and ledger.idem == {}
    again = await uc.create_intent(CUSTOMER, "b1", "idem-key-0002", None)  # not blocked
    assert again["order_ref"] != row["order_ref"]


async def test_provider_success_never_persisted_is_recovered_by_reconcile():
    ledger, gateway, uc, resolver, cfg = build()
    gateway.create_script = [("unknown", False)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.create_intent(CUSTOMER, "b1", KEY, None)
    (row,) = ledger.payments.values()
    # the customer later paid at the provider although we never got the order response
    gateway.payments[row["order_ref"]] = capture(row["order_ref"], "1000.00")
    count = await PaymentWebhookUseCases(ledger, resolver, cfg).reconcile_stale_intents()
    assert count == 1 and row["status"] == "captured"
    assert ledger._booking_view()["payment_status"] == "paid"


async def test_non_deterministic_provider_cannot_recover_and_row_is_left_to_expire():
    ledger, gateway, uc, *_ = build(deterministic=False)
    gateway.create_script = [("unknown", False)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.create_intent(CUSTOMER, "b1", KEY, None)
    (row,) = ledger.payments.values()
    assert row["order_ref"] is None and row["status"] == "created"  # documented Razorpay-style gap


async def test_refund_row_with_deterministic_ref_is_committed_before_the_provider_call():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    gateway.dirty_at_call.clear()
    await uc.refund(OWNER, "b1", intent["payment_id"], D("100.00"), "why", "refund-key-1")
    assert gateway.dirty_at_call == [False]
    (refund,) = ledger.refunds.values()
    assert refund["refund_ref"] == "rf" + refund["id"].replace("-", "")
    assert gateway.requests[-1].refund_ref == refund["refund_ref"] and refund["status"] == "processed"


async def test_refund_timeout_keeps_one_row_and_retry_resends_the_same_provider_id():
    ledger, gateway, uc, resolver, cfg = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    gateway.refund_script = [("unknown",)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.refund(OWNER, "b1", intent["payment_id"], D("400.00"), None, "refund-key-1")
    (refund,) = ledger.refunds.values()
    assert refund["status"] == "created"  # still reserves the amount
    # worker reconciliation while the provider did not issue it: stays open
    assert await PaymentWebhookUseCases(ledger, resolver, cfg).reconcile_open_refunds() == 1
    assert refund["status"] == "created"
    await uc.refund(OWNER, "b1", intent["payment_id"], D("400.00"), None, "refund-key-1")
    assert len(ledger.refunds) == 1 and refund["status"] == "processed"
    assert gateway.requests[-1].refund_ref == gateway.requests[-2].refund_ref  # same id both times


async def test_unknown_refund_outcome_is_resolved_by_the_worker_via_our_refund_id():
    ledger, gateway, uc, resolver, cfg = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    gateway.refund_script = [("unknown",)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.refund(OWNER, "b1", intent["payment_id"], D("400.00"), None, "refund-key-1")
    (refund,) = ledger.refunds.values()
    gateway.refund_results[refund["refund_ref"]] = RefundResult(
        "cashfree", refund["refund_ref"], RefundStatus.processed, Money(D("400.00")))  # it had landed
    await PaymentWebhookUseCases(ledger, resolver, cfg).reconcile_open_refunds()
    assert refund["status"] == "processed"


async def test_definitive_refund_rejection_frees_the_amount():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    gateway.refund_script = [("reject",)]
    with pytest.raises(PaymentProviderError):
        await uc.refund(OWNER, "b1", intent["payment_id"], D("1000.00"), None, "refund-key-1")
    assert next(iter(ledger.refunds.values()))["status"] == "failed"
    await uc.refund(OWNER, "b1", intent["payment_id"], D("1000.00"), None, "refund-key-2")  # not blocked


def details(**kw):
    values = {"legal_name": "Asha Salon", "contact_email": "o@example.com", "contact_phone": "9876543210",
              "account_type": "individual", "business_type": "salon", "pan": "ABCDE1234F",
              "bank_account_number": "123456789012", "ifsc": "HDFC0001234"}
    values.update(kw)
    return SettlementRegistrationDetails(**values)


async def test_vendor_identity_and_pending_status_are_committed_before_registration():
    ledger, gateway, uc, *_ = build()
    ledger.accounts.clear()
    body = await uc.register_settlement_account(OWNER, KEY, details())
    assert gateway.dirty_at_call == [False]
    acct = ledger.accounts[("salon-1", "cashfree")]
    assert acct["provider_account_ref"] == "svsalon-1g1".replace("-", "")[:0] + "svsalon1g1"
    assert body["onboarding_status"] == "pending" and body["requirements"]


async def test_vendor_timeout_keeps_pending_and_retry_reuses_the_same_vendor_id():
    ledger, gateway, uc, *_ = build()
    ledger.accounts.clear()
    gateway.register_script = [("unknown",)]
    with pytest.raises(PaymentOutcomeUnknownError):
        await uc.register_settlement_account(OWNER, KEY, details())
    acct = ledger.accounts[("salon-1", "cashfree")]
    assert acct["onboarding_status"] == "pending" and ledger.idem == {}
    await uc.register_settlement_account(OWNER, KEY, details())
    assert gateway.requests[0].vendor_ref == gateway.requests[1].vendor_ref
    assert acct["gen"] == 1


async def test_vendor_rejection_becomes_needs_action_with_audit_and_no_kyc_stored():
    ledger, gateway, uc, *_ = build()
    ledger.accounts.clear()
    gateway.register_script = [("reject",)]
    with pytest.raises(PaymentProviderError):
        await uc.register_settlement_account(OWNER, KEY, details())
    acct = ledger.accounts[("salon-1", "cashfree")]
    assert acct["onboarding_status"] == "needs_action" and acct["requirements"]
    assert any(a["action"] == "register_failed" for a in ledger.audit)
    stored = repr(ledger.accounts) + repr(ledger.audit) + repr(ledger.idem)
    for secret in ("ABCDE1234F", "123456789012", "HDFC0001234", "o@example.com", "9876543210"):
        assert secret not in stored


async def test_reregistration_after_activation_is_a_new_generation_with_audit():
    ledger, gateway, uc, *_ = build()  # fixture account is active, generation 1
    body = await uc.register_settlement_account(OWNER, KEY, details(bank_account_number="999999999999"))
    acct = ledger.accounts[("salon-1", "cashfree")]
    assert acct["gen"] == 2 and acct["provider_account_ref"].endswith("g2")
    assert ledger.audit[0] == {"action": "re_registered", "previous": "active"}
    assert body["onboarding_status"] == "pending"
    with pytest.raises(ConflictError, match="cannot take online payments"):
        await uc.create_intent(CUSTOMER, "b1", "idem-key-0009", None)  # not payable until KYC passes


async def test_registration_requires_details_and_owner_role_and_masks_the_reference():
    ledger, gateway, uc, *_ = build()
    with pytest.raises(ValidationError):
        await uc.register_settlement_account(OWNER, KEY, None)
    with pytest.raises(ForbiddenError):
        await uc.register_settlement_account(CUSTOMER, "idem-key-0002", details())
    state = await uc.get_settlement_account(OWNER)
    assert state["onboarding_status"] == "active" and state["requires_details"] is True
    assert state["account_reference_masked"] == "...or_1" or state["account_reference_masked"].endswith("or_1")
    assert "vendor_1" not in repr(state)


# ================================================================ refresh / confirm
async def test_refresh_confirms_from_the_provider_not_from_the_client():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    # nothing paid at the provider yet: a refresh changes nothing (the client claims nothing anyway)
    body = await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    assert body["payment_state"] == "unpaid" and body["payments"][0]["status"] == "created"
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    body = await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-2")
    assert body["payment_state"] == "paid" and body["payments"][0]["status"] == "captured"


async def test_refresh_is_idempotent_replays_and_rejects_key_reuse_with_another_order():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    first = await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    calls = len(gateway.calls)
    assert await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1") == first
    assert len(gateway.calls) == calls  # replayed, the provider is not asked again
    with pytest.raises(IdempotencyKeyReuseError):
        await uc.refresh(CUSTOMER, "b1", "another_order", "refresh-key-1")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-3")  # a new key is safe
    assert len(ledger.payments) == 1 and ledger.paid == D("1000.00")  # never paid twice


async def test_refresh_authorization_only_the_bookings_customer():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    for who in (OTHER, OWNER):
        with pytest.raises(NotFoundError):
            await uc.refresh(who, "b1", intent["order_ref"], "refresh-key-x" + who.id)
    with pytest.raises(NotFoundError):
        await uc.refresh(CUSTOMER, "b1", "somebody_elses_order", "refresh-key-y")
    assert ledger.paid == D("0")  # nothing was applied for anybody else


async def test_refresh_requires_an_idempotency_key_and_a_provider():
    ledger, gateway, uc, *_ = build()
    from app.core.exceptions import IdempotencyKeyRequiredError
    with pytest.raises(IdempotencyKeyRequiredError):
        await uc.refresh(CUSTOMER, "b1", "o", None)
    dormant = BookingPaymentUseCases(ledger, PaymentGatewayResolver(Settings(_env_file=None, environment="test")),
                                     Settings(_env_file=None, environment="test"))
    with pytest.raises(PaymentProviderNotConfiguredError):
        await dormant.refresh(CUSTOMER, "b1", "o", KEY)


async def test_refresh_amount_mismatch_fails_the_row_and_never_marks_paid():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "400.00")
    with pytest.raises(PaymentAmountMismatchError):
        await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    row = next(iter(ledger.payments.values()))
    assert row["status"] == "failed" and row["failure_code"] == "amount_mismatch"
    assert ledger.paid == D("0") and ledger.anomalies[0]["kind"] == "amount_mismatch"


async def test_confirm_on_a_refresh_provider_ignores_a_client_supplied_signature():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    # a forged "success" payload is simply not consulted: the provider reports nothing paid
    body = await uc.confirm(CUSTOMER, "b1", intent["order_ref"], "pay_forged", "sig_forged", "confirm-key-1")
    assert body["payment_state"] == "unpaid"
    assert gateway.calls[-1] == "fetch_payment"


async def test_confirm_on_a_signed_callback_provider_rejects_forged_and_missing_signature():
    ledger, gateway, uc, *_ = build(caps={C.online_collection, C.refunds, C.callback_signature})
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    gateway.signature_ok = False
    with pytest.raises(ValidationError, match="could not be verified"):
        await uc.confirm(CUSTOMER, "b1", intent["order_ref"], "pay_1", "forged", "confirm-key-1")
    with pytest.raises(ValidationError, match="required"):
        await uc.confirm(CUSTOMER, "b1", intent["order_ref"], None, None, "confirm-key-2")
    assert ledger.paid == D("0")
    gateway.signature_ok = True
    body = await uc.confirm(CUSTOMER, "b1", intent["order_ref"], "pay_1", "good", "confirm-key-3")
    assert body["payment_state"] == "paid"


# ==================================================================== overcollection
async def test_online_capture_after_cash_is_recorded_as_overcollection_not_dropped(caplog):
    ledger, gateway, uc, resolver, cfg = build("500.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    await ledger.add_manual_cash("500.00")  # the salon took cash while the online order was open
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "500.00")
    with caplog.at_level(logging.ERROR):
        body = await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    online = next(p for p in body["payments"] if p["channel"] == "gateway")
    assert online["status"] == "captured" and D(online["overcollected_amount"]) == D("500.00")
    assert body["payment_state"] == "paid" and D(body["paid_amount"]) == D("500.00")  # not 1000
    assert any(a["kind"] == "overcollection" for a in ledger.anomalies)
    assert any("OVERCOLLECTION" in r.message for r in caplog.records)
    # the reconcile loop no longer sees it as open, so it cannot fail forever
    assert await ledger.list_stale_intents(0, 10) == []


async def test_excess_must_be_refunded_first_and_does_not_unpay_the_booking():
    ledger, gateway, uc, *_ = build("500.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    await ledger.add_manual_cash("500.00")
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "500.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    pid = intent["payment_id"]
    with pytest.raises(ValidationError, match="overcollected"):
        await uc.refund(OWNER, "b1", pid, D("500.01"), None, "refund-key-0")
    body = await uc.refund(OWNER, "b1", pid, None, "excess", "refund-key-1")  # default = the excess
    (refund,) = ledger.refunds.values()
    assert refund["applies_to_excess"] is True and refund["amount"] == D("500.00")
    assert refund["commission_reversal_amount"] == D("0.00")  # the excess never earned commission
    assert body["payment_state"] == "paid" and ledger.refunded == D("0")


async def test_partial_payment_then_balance_then_overcollected_extra():
    ledger, gateway, uc, *_ = build("1000.00", deposit="300.00")
    ledger.booking["payment_preference"] = "pay_advance"
    deposit = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[deposit["order_ref"]] = capture(deposit["order_ref"], "300.00", "pay_d")
    await uc.refresh(CUSTOMER, "b1", deposit["order_ref"], "refresh-key-1")
    assert ledger._booking_view()["payment_status"] == "unpaid" and ledger.paid == D("300.00")
    balance = await uc.create_intent(CUSTOMER, "b1", "idem-key-0002", None)
    assert balance["purpose"] == "balance" and balance["amount"] == "700.00"
    gateway.payments[balance["order_ref"]] = capture(balance["order_ref"], "700.00", "pay_b")
    await uc.refresh(CUSTOMER, "b1", balance["order_ref"], "refresh-key-2")
    assert ledger._booking_view()["payment_status"] == "paid"
    with pytest.raises(ConflictError, match="already fully paid"):
        await uc.create_intent(CUSTOMER, "b1", "idem-key-0003", None)


# ==================================================================== provider routing
async def test_refund_uses_the_rows_own_provider_never_the_configured_one():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    ledger.payments[intent["payment_id"]]["provider"] = "razorpay"  # the money is at another provider
    gateway.calls.clear()
    with pytest.raises(PaymentProviderNotConfiguredError):
        await uc.refund(OWNER, "b1", intent["payment_id"], None, None, "refund-key-1")
    assert "refund" not in gateway.calls and ledger.refunds == {}


async def test_refund_goes_to_the_other_enabled_provider_when_the_row_belongs_to_it():
    ledger, gateway, uc, resolver, cfg = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    other = FakeGateway(ledger, name="razorpay", caps={C.online_collection, C.refunds, C.callback_signature})
    ledger.payments[intent["payment_id"]]["provider"] = "razorpay"
    resolver._extra["razorpay"] = other
    gateway.calls.clear()
    await uc.refund(OWNER, "b1", intent["payment_id"], D("10.00"), None, "refund-key-1")
    assert other.calls == ["refund"] and "refund" not in gateway.calls


async def test_reconcile_does_not_ask_the_wrong_provider_about_a_row():
    ledger, gateway, uc, resolver, cfg = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    ledger.payments[intent["payment_id"]]["provider"] = "razorpay"
    gateway.calls.clear()
    assert await PaymentWebhookUseCases(ledger, resolver, cfg).reconcile_stale_intents() == 1
    assert gateway.calls == []  # skipped, not looked up through the cashfree gateway


async def test_refund_authorization_and_cash_refusal():
    ledger, gateway, uc, *_ = build()
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    gateway.payments[intent["order_ref"]] = capture(intent["order_ref"], "1000.00")
    await uc.refresh(CUSTOMER, "b1", intent["order_ref"], "refresh-key-1")
    with pytest.raises(ForbiddenError):
        await uc.refund(CUSTOMER, "b1", intent["payment_id"], None, None, "refund-key-1")
    stranger = make_profile("owner-2", Role.owner)
    with pytest.raises(NotFoundError):
        await uc.refund(stranger, "b1", intent["payment_id"], None, None, "refund-key-2")
    await ledger.add_manual_cash("1.00")
    cash_id = next(k for k in ledger.payments if k.startswith("cash"))
    with pytest.raises(ConflictError, match="Only online payments"):
        await uc.refund(OWNER, "b1", cash_id, None, None, "refund-key-3")


async def test_intent_idempotency_replays_the_stored_response():
    ledger, gateway, uc, *_ = build()
    first = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    again = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    assert again == first and len(ledger.payments) == 1 and gateway.calls.count("create") == 1


# ======================================================================= webhook apply
def process_events(ledger, resolver, cfg, data, provider="cashfree"):
    async def claim(event_id, stale, attempts):
        return {"id": event_id, "provider_name": provider, "normalized": data, "attempts": 1,
                "event_type": data["event_type"]}

    finished = []

    async def finish(event_id, status, error=None, *, retry=False):
        finished.append((status, error, retry))

    ledger.claim_webhook_event = claim
    ledger.finish_webhook_event = finish
    return PaymentWebhookUseCases(ledger, resolver, cfg), finished


async def test_settlement_failure_and_reversal_become_operator_visible_anomalies():
    ledger, gateway, uc, resolver, cfg = build()
    for status in ("failed", "reversed"):
        webhook, finished = process_events(ledger, resolver, cfg, {
            "event_type": "settlement_updated", "settlement_status": status, "account_ref": "vendor_1",
            "amount": "90.00"})
        assert await webhook.process(f"evt-{status}") == "processed"
    assert [a["kind"] for a in ledger.anomalies] == ["settlement_failed", "settlement_reversed"]
    assert ledger.anomalies[0]["amount"] == D("90.00") and ledger.anomalies[0]["salon_id"] == "salon-1"
    ok, finished = process_events(ledger, resolver, cfg, {
        "event_type": "settlement_updated", "settlement_status": "success", "account_ref": "vendor_1"})
    assert await ok.process("evt-ok") == "ignored" and len(ledger.anomalies) == 2


async def test_overcollected_webhook_is_processed_not_failed_and_not_retried(caplog):
    ledger, gateway, uc, resolver, cfg = build("500.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    await ledger.add_manual_cash("500.00")
    webhook, finished = process_events(ledger, resolver, cfg, {
        "event_type": "payment_captured", "order_ref": intent["order_ref"], "payment_ref": "pay_1",
        "amount": "500.00", "currency": "INR"})
    with caplog.at_level(logging.ERROR):
        assert await webhook.process("evt-1") == "processed"
    assert finished == [("processed", None, False)]
    assert any("OVERCOLLECTION" in r.message for r in caplog.records)


async def test_out_of_order_and_duplicate_payment_events_do_not_double_apply():
    ledger, gateway, uc, resolver, cfg = build("500.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    base = {"order_ref": intent["order_ref"], "payment_ref": "pay_1", "currency": "INR", "amount": "500.00"}
    ok, _ = process_events(ledger, resolver, cfg, {**base, "event_type": "payment_captured"})
    assert await ok.process("e1") == "processed"
    late_fail, _ = process_events(ledger, resolver, cfg, {**base, "event_type": "payment_failed", "amount": None})
    assert await late_fail.process("e2") == "ignored"  # a stale failure cannot undo a capture
    dup, _ = process_events(ledger, resolver, cfg, {**base, "event_type": "payment_captured"})
    assert await dup.process("e3") == "ignored"
    assert ledger.paid == D("500.00") and next(iter(ledger.payments.values()))["status"] == "captured"


async def test_wrong_currency_and_unknown_order_are_handled():
    ledger, gateway, uc, resolver, cfg = build("500.00")
    intent = await uc.create_intent(CUSTOMER, "b1", KEY, None)
    bad, finished = process_events(ledger, resolver, cfg, {
        "event_type": "payment_captured", "order_ref": intent["order_ref"], "payment_ref": "p",
        "amount": "500.00", "currency": "USD"})
    assert await bad.process("e1") == "failed" and finished == [("failed", "mismatch", False)]
    stranger, _ = process_events(ledger, resolver, cfg, {
        "event_type": "payment_captured", "order_ref": "not_ours", "payment_ref": "p2",
        "amount": "500.00", "currency": "INR"})
    assert await stranger.process("e2") == "ignored"
    assert ledger.paid == D("0")
