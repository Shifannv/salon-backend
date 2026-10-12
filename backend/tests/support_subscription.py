"""Shared fakes for subscription billing tests (no network, no database)."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.application.ports.subscription_provider import (
    ProviderOrder,
    ProviderOrderState,
    ProviderPaymentObservation,
    ProviderPaymentState,
    ProviderRefund,
    SubscriptionOrderRequest,
)
from app.core.config import Settings
from app.core.exceptions import (
    IdempotencyInProgressError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
)
from app.domain.entities.profile import Profile, Role
from app.domain.value_objects.money import Money
from app.infrastructure.subscriptions.razorpay import RazorpaySubscriptionProvider, to_paise
from app.infrastructure.subscriptions.resolver import SubscriptionProviderResolver

WEBHOOK_SECRET = "sub-webhook-secret-0123456789abcdef0123456789"
KEY_SECRET = "sub-key-secret-value"
D = Decimal


def sub_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "environment": "test",
        "subscription_provider": "razorpay",
        "subscription_razorpay_key_id": "rzp_test_subkey",
        "subscription_razorpay_key_secret": KEY_SECRET,
        "subscription_razorpay_webhook_secret": WEBHOOK_SECRET,
        "subscription_grace_days": 3,
    }
    values.update(overrides)
    return Settings(**values)


def sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def webhook(event: str, *, order: str | None = None, payment: str | None = None,
            amount_paise: int | None = None, currency: str = "INR", refund: str | None = None,
            event_id: str = "evt_1") -> tuple[bytes, dict[str, str]]:
    entity: dict[str, Any] = {}
    if payment:
        entity["id"] = payment
    if order:
        entity["order_id"] = order
    if amount_paise is not None:
        entity["amount"] = amount_paise
        entity["currency"] = currency
    payload: dict[str, Any] = {"payment": {"entity": entity}}
    if event.startswith("refund."):
        payload = {"refund": {"entity": {"id": refund or "rfnd_1", "payment_id": payment,
                                         "amount": amount_paise, "currency": currency}}}
    body = json.dumps({"event": event, "payload": payload}).encode()
    return body, {"x-razorpay-signature": sign(body), "x-razorpay-event-id": event_id}


class FakeProvider(RazorpaySubscriptionProvider):
    """The real adapter's signature/parse code, with an in-memory provider behind it."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__(settings or sub_settings())
        self.orders: dict[str, dict[str, Any]] = {}
        self.payments: dict[str, dict[str, Any]] = {}
        self.calls: list[str] = []
        self.create_mode = "ok"  # ok | timeout_created | timeout_lost | reject
        self.refunds: list[tuple[str, Decimal, str]] = []

    # --- test controls
    def pay(self, order_ref: str, *, amount: Decimal | None = None, currency: str | None = None,
            status: str = "captured", payment_ref: str | None = None, refunded: Decimal = D(0)) -> str:
        order = self.orders[order_ref]
        ref = payment_ref or "pay_" + uuid.uuid4().hex[:12]
        self.payments[ref] = {
            "ref": ref, "order": order_ref, "status": status,
            "amount": amount if amount is not None else order["amount"],
            "currency": currency or order["currency"], "refunded": refunded,
        }
        if status == "captured":
            order["state"] = ProviderOrderState.paid
        return ref

    def _order(self, order_ref: str) -> ProviderOrder:
        o = self.orders[order_ref]
        return ProviderOrder(
            provider="razorpay", order_ref=order_ref, receipt=o["receipt"], amount=Money(o["amount"]),
            currency=o["currency"], state=o["state"],
            client_payload={"key_id": self._key_id, "order_id": order_ref,
                            "amount": to_paise(Money(o["amount"])), "currency": o["currency"]},
        )

    # --- port
    async def create_period_order(self, request: SubscriptionOrderRequest) -> ProviderOrder:
        self.calls.append("create")
        if self.create_mode == "reject":
            raise PaymentProviderError("rejected", {"provider_status": 400})
        if self.create_mode == "timeout_lost":
            raise PaymentOutcomeUnknownError("timeout")
        ref = "order_" + uuid.uuid4().hex[:12]
        self.orders[ref] = {"receipt": request.receipt, "amount": request.amount.amount,
                            "currency": request.currency, "state": ProviderOrderState.created}
        if self.create_mode == "timeout_created":
            raise PaymentOutcomeUnknownError("timeout after create")
        return self._order(ref)

    async def fetch_order(self, order_ref: str) -> ProviderOrder | None:
        self.calls.append("fetch_order")
        return self._order(order_ref) if order_ref in self.orders else None

    async def find_order_by_receipt(self, receipt: str) -> ProviderOrder | None:
        self.calls.append("find_by_receipt")
        for ref, o in self.orders.items():
            if o["receipt"] == receipt:
                return self._order(ref)
        return None

    def _obs(self, p: dict[str, Any]) -> ProviderPaymentObservation:
        return ProviderPaymentObservation(
            provider="razorpay", payment_ref=p["ref"], order_ref=p["order"],
            state=ProviderPaymentState(p["status"]), amount=Money(p["amount"]),
            currency=p["currency"], amount_refunded=Money(p["refunded"]),
        )

    async def fetch_order_payments(self, order_ref: str) -> list[ProviderPaymentObservation]:
        self.calls.append("fetch_order_payments")
        return [self._obs(p) for p in self.payments.values() if p["order"] == order_ref]

    async def fetch_payment(self, payment_ref: str) -> ProviderPaymentObservation | None:
        self.calls.append("fetch_payment")
        p = self.payments.get(payment_ref)
        return self._obs(p) if p else None

    async def refund(self, payment_ref: str, amount: Money, idempotency_key: str,
                     reason: str | None = None) -> ProviderRefund:
        self.refunds.append((payment_ref, amount.amount, idempotency_key))
        self.payments[payment_ref]["refunded"] += amount.amount
        return ProviderRefund("razorpay", "rfnd_" + idempotency_key[:8], payment_ref, amount, "processed")


def resolver_for(provider: FakeProvider, settings: Settings | None = None) -> SubscriptionProviderResolver:
    return SubscriptionProviderResolver(settings or sub_settings(), provider)


def owner(uid: str = "owner-1") -> Profile:
    return Profile(id=uid, role=Role.owner, full_name="Owner", email="o@example.test",
                   phone=None, phone_verified=True, avatar_url=None, is_active=True)


def profile(role: Role, uid: str) -> Profile:
    return Profile(id=uid, role=role, full_name="X", email=None, phone=None,
                   phone_verified=False, avatar_url=None, is_active=True)


# ---------------------------------------------------------------------------
class FakeBillingRepo:
    """In-memory stand-in for SubscriptionBillingRepository (orchestration tests only).

    Activation SEMANTICS (extension, overlap, idempotency) are proven on real PostgreSQL in
    tests/integration/test_subscription_billing_sql.py; ``apply`` here only counts calls.
    """

    PLAN = {  # noqa: RUF012
        "id": "plan-g1", "code": "growth_1m", "name": "Growth - 1 month", "tier": 1,
        "price_amount": D("349.00"), "currency": "INR", "billing_interval": "monthly",
        "features": {"split_bill": True}, "is_active": True,
    }

    def __init__(self, salons: dict[str, str] | None = None) -> None:
        self.salons = salons if salons is not None else {"owner-1": "salon-1"}
        self.plans = {"plan-g1": dict(self.PLAN),
                      "plan-g6": {**self.PLAN, "id": "plan-g6", "code": "growth_6m",
                                  "price_amount": D("1499.00"), "billing_interval": "semiannual"}}
        self.rows: dict[str, dict[str, Any]] = {}
        self.subscription: dict[str, Any] | None = None
        self.idem: dict[tuple, dict[str, Any] | None] = {}
        self.idem_fp: dict[tuple, str] = {}
        self.commits = 0
        self.events: list[tuple] = []
        self.anomalies: list[dict[str, Any]] = []
        self.applied_calls = 0
        self.session = object()

    # transactions / identity
    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None: ...

    async def set_actor(self, actor_id: str) -> None: ...

    async def find_owner_salon_id(self, actor_id: str) -> str | None:
        return self.salons.get(actor_id)

    async def get_workspace_salon(self, actor_id: str) -> dict[str, Any] | None:
        return {"is_active": True, "profile_completed": True, "approval_status": "approved"}

    # idempotency
    async def begin_idempotent(self, actor_id, scope, key, fingerprint, ttl):
        k = (actor_id, scope, key)
        if k in self.idem:
            if self.idem_fp[k] != fingerprint:
                from app.core.exceptions import IdempotencyKeyReuseError
                raise IdempotencyKeyReuseError("reuse")
            if self.idem[k] is None:
                raise IdempotencyInProgressError("busy")
            return self.idem[k]
        self.idem[k] = None
        self.idem_fp[k] = fingerprint
        return None

    async def finish_idempotent(self, actor_id, scope, key, status, body):
        self.idem[(actor_id, scope, key)] = json.loads(json.dumps(body, default=str))

    async def release_idempotent(self, actor_id, scope, key):
        if self.idem.get((actor_id, scope, key)) is None:
            self.idem.pop((actor_id, scope, key), None)

    async def record_anomaly(self, **kw):
        self.anomalies.append(kw)

    # plans / subscription
    async def list_purchasable_plans(self):
        return [p for p in self.plans.values() if p["is_active"]]

    async def get_plan(self, plan_id):
        return self.plans.get(plan_id)

    async def latest_subscription(self, salon_id):
        return self.subscription

    async def cancel_renewal(self, salon_id):
        if self.subscription is None:
            return "none"
        if self.subscription["status"] == "cancelled":
            return "already_cancelled"
        self.subscription["status"] = "cancelled"
        self.subscription["cancelled_at"] = datetime.now(UTC)
        return "cancelled"

    async def sweep_lapsed(self):
        return 0

    # billing rows
    async def insert_billing(self, *, salon_id, plan_id, provider, receipt, actor_id, ttl_seconds):
        from app.core.exceptions import ConflictError
        if any(r["salon_id"] == salon_id and r["status"] in ("created", "authorized")
               for r in self.rows.values()):
            raise ConflictError("open exists")
        plan = self.plans[plan_id]
        row = {
            "id": "bill-" + uuid.uuid4().hex[:8], "salon_id": salon_id, "plan_id": plan_id,
            "plan_code": plan["code"], "provider": provider, "receipt": receipt,
            "provider_order_ref": None, "provider_payment_ref": None, "status": "created",
            "amount": plan["price_amount"], "currency": plan["currency"],
            "billing_interval": plan["billing_interval"], "tax_amount": None, "tax_inclusive": None,
            "benefits": plan["features"], "refunded_amount": D("0.00"), "period_start": None,
            "period_end": None, "subscription_id": None,
            "expires_at": datetime.now(UTC) + timedelta(seconds=ttl_seconds), "paid_at": None,
            "applied_at": None, "failure_code": None, "created_by": actor_id,
            "created_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
        }
        self.rows[row["id"]] = row
        return dict(row)

    def _find(self, **match):
        for r in self.rows.values():
            if all(r.get(k) == v for k, v in match.items()):
                return dict(r)
        return None

    async def get_billing(self, billing_id, *, lock=False):
        r = self.rows.get(billing_id)
        return dict(r) if r else None

    async def get_open_billing(self, salon_id):
        for r in self.rows.values():
            if r["salon_id"] == salon_id and r["status"] in ("created", "authorized"):
                return dict(r)
        return None

    async def get_billing_by_order(self, provider, order_ref):
        return self._find(provider=provider, provider_order_ref=order_ref)

    async def get_billing_by_payment(self, provider, payment_ref):
        return self._find(provider=provider, provider_payment_ref=payment_ref)

    async def list_history(self, salon_id, limit, offset):
        rows = [dict(r) for r in self.rows.values() if r["salon_id"] == salon_id]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[offset:offset + limit]

    async def set_order_ref(self, billing_id, order_ref):
        r = self.rows[billing_id]
        if r["provider_order_ref"] in (None, order_ref):
            r["provider_order_ref"] = order_ref

    async def mark_paid(self, billing_id, payment_ref):
        r = self.rows[billing_id]
        if r["status"] in ("created", "authorized", "failed", "expired") and \
                r["provider_payment_ref"] in (None, payment_ref):
            r.update(status="paid", provider_payment_ref=payment_ref, failure_code=None,
                     paid_at=r["paid_at"] or datetime.now(UTC))
            return True
        return False

    async def note_failure(self, billing_id, code):
        r = self.rows[billing_id]
        if r["status"] in ("created", "authorized"):
            r["failure_code"] = code or "payment_failed"

    async def finish_unpaid(self, billing_id, status):
        r = self.rows[billing_id]
        if r["status"] in ("created", "authorized"):
            r["status"] = status
            return True
        return False

    async def touch(self, billing_id): ...

    async def set_refunded(self, billing_id, refunded):
        r = self.rows[billing_id]
        if r["status"] not in ("paid", "partially_refunded", "refunded"):
            return None
        r["refunded_amount"] = max(r["refunded_amount"], min(refunded, r["amount"]))
        if r["refunded_amount"] >= r["amount"]:
            r["status"] = "refunded"
        elif r["refunded_amount"] > 0:
            r["status"] = "partially_refunded"
        return r["status"]

    async def apply(self, billing_id, grace_days):
        r = self.rows[billing_id]
        if r["applied_at"] is not None:
            return "already_applied"
        if r["status"] not in ("paid", "partially_refunded"):
            return "not_paid"
        self.applied_calls += 1
        r["applied_at"] = datetime.now(UTC)
        r["period_start"] = r["applied_at"]
        r["period_end"] = r["applied_at"] + timedelta(days=30)
        r["subscription_id"] = "sub-1"
        return "started"

    async def list_stale_open(self, after_seconds, limit):
        return [{**r, "is_expired": r["expires_at"] <= datetime.now(UTC)}
                for r in self.rows.values() if r["status"] in ("created", "authorized")]

    async def list_unapplied_paid(self, limit):
        return [dict(r) for r in self.rows.values()
                if r["status"] in ("paid", "partially_refunded") and r["applied_at"] is None]

    async def log_event(self, **kw):
        self.events.append((kw["provider"], kw["reference"], kw["event_type"]))
        return True
