"""Owner subscription billing: checkout, server-side verification, webhooks, reconciliation.

Initial mode is ONE-TIME provider orders for ONE paid period with MANUAL renewal. The
rules this module enforces:

* Money is only ever applied from a SERVER-VERIFIED paid state: a provider fetch (order
  payments / payment) or a verified webhook that is itself re-checked by a provider fetch.
  A client-side checkout result is a hint at most.
* The purchase row (with the plan price snapshot) is committed BEFORE the provider is called;
  after a timeout the order is recovered by OUR receipt.
* Activation is the SQL function ``apply_subscription_billing_record``: atomic, serialised per
  salon, exactly once (``applied_at``). Duplicate, delayed and reordered events converge.
* Expiry/lapse never blocks history, refunds or cancelling; it only ends the premium benefit.
* The platform keeps subscription revenue: nothing here splits money.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from app.application.ports.subscription_provider import (
    ProviderOrder,
    ProviderOrderState,
    ProviderPaymentState,
    ProviderSubscriptionEvent,
    SubscriptionEventKind,
    SubscriptionOrderRequest,
)
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    IdempotencyKeyRequiredError,
    NotFoundError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
)
from app.domain.entities.profile import Profile, Role
from app.domain.entities.subscription import (
    Entitlement,
    EntitlementState,
    derive_entitlement,
)
from app.domain.services.finance_ledger import TrialState
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.feature_access_repository import FeatureAccessRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.subscriptions.resolver import SubscriptionProviderResolver

_log = logging.getLogger(__name__)

_PAID = {"paid", "partially_refunded", "refunded"}
_CAPTURED = {
    ProviderPaymentState.captured,
    ProviderPaymentState.partially_refunded,
    ProviderPaymentState.refunded,
}
_APPLIED_OUTCOMES = {"started", "renewed", "already_applied"}
_BLOCKED_OUTCOMES = {"blocked_suspended", "blocked_closed"}


def subscription_event_to_json(event: ProviderSubscriptionEvent) -> dict[str, Any]:
    """The normalised form stored in ``payment_webhook_events.normalized`` (domain 'subscription')."""

    return {
        "domain": "subscription",
        "event_type": "subscription",
        "kind": event.kind.value,
        "raw_type": event.raw_type,
        "order_ref": event.order_ref,
        "payment_ref": event.payment_ref,
        "refund_ref": event.refund_ref,
        "amount": str(event.amount.amount) if event.amount is not None else None,
        "currency": event.currency,
        "failure_code": event.failure_code,
    }


def _body_amount(value: Decimal | str | None) -> str | None:
    return None if value is None else str(Money(value).amount)


# ============================================================ settlement (shared)
class SubscriptionSettlement:
    """Turns a provider-verified payment into an applied entitlement, idempotently."""

    def __init__(
        self,
        repository: SubscriptionBillingRepository,
        resolver: SubscriptionProviderResolver,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings

    def _grace_days(self) -> int:
        days = self.settings.subscription_grace_days
        if days is None:
            raise PaymentProviderNotConfiguredError("Subscription grace period is not configured")
        return days

    async def _anomaly(self, kind: str, record: dict[str, Any], ref: str | None, detail: str) -> None:
        await self.repository.record_anomaly(
            kind=kind,
            provider=record["provider"],
            provider_ref=ref or str(record["id"]),
            salon_id=str(record["salon_id"]),
            amount=Decimal(record["amount"]),
            detail=detail,
        )

    async def apply_paid(self, record: dict[str, Any], event_ref: str | None = None) -> str:
        """Apply an already-paid record. Outcome is one of the SQL function's codes."""

        outcome = await self.repository.apply(str(record["id"]), self._grace_days())
        if outcome in _BLOCKED_OUTCOMES:
            await self._anomaly(
                "subscription_blocked", record, record.get("provider_payment_ref"),
                f"paid period could not be applied: {outcome}",
            )
            _log.error("ALERT subscription_billing: paid record %s %s", record["id"], outcome)
        elif outcome in {"started", "renewed"}:
            applied = await self.repository.get_billing(str(record["id"]))
            await self.repository.log_event(
                subscription_id=str(applied["subscription_id"]) if applied else None,
                provider=record["provider"],
                reference=f"applied:{record['id']}",
                event_type="subscription_started" if outcome == "started" else "subscription_renewed",
                payload={"billing_id": str(record["id"]), "outcome": outcome, "via": event_ref},
            )
        return outcome

    async def settle(
        self, record: dict[str, Any], *, hint_payment_ref: str | None = None
    ) -> str:
        """Ask the provider what really happened to this order and apply it.

        Returns ``started|renewed|already_applied`` (entitlement in place), ``pending`` (not
        paid at the provider), ``no_order`` (no provider order exists), ``mismatch`` /
        ``duplicate_payment`` / ``blocked_*`` (needs an operator; anomaly recorded).
        """

        if record["status"] in _PAID and record["provider_payment_ref"]:
            return await self.apply_paid(record)
        provider = self.resolver.for_provider(record["provider"])
        order_ref = record["provider_order_ref"]
        if not order_ref:
            found = await provider.find_order_by_receipt(record["receipt"])
            if found is None:
                return "no_order"
            order_ref = found.order_ref
            await self.repository.set_order_ref(str(record["id"]), order_ref)
        payments = list(await provider.fetch_order_payments(order_ref))
        if hint_payment_ref and all(p.payment_ref != hint_payment_ref for p in payments):
            hinted = await provider.fetch_payment(hint_payment_ref)
            if hinted is not None:
                payments.append(hinted)
        # Ownership: only payments the provider attributes to THIS order count.
        mine = [p for p in payments if p.order_ref == order_ref]
        captured = sorted((p for p in mine if p.state in _CAPTURED), key=lambda p: p.payment_ref)
        if not captured:
            failed = [p for p in mine if p.state is ProviderPaymentState.failed]
            if failed:
                await self.repository.note_failure(str(record["id"]), failed[-1].failure_code)
            return "pending"
        winner = captured[0]
        if winner.amount.amount != Decimal(record["amount"]) or winner.currency != record["currency"]:
            await self._anomaly(
                "subscription_amount_mismatch", record, winner.payment_ref,
                f"provider reports {winner.amount} {winner.currency}",
            )
            _log.error("ALERT subscription_billing: amount mismatch on record %s", record["id"])
            return "mismatch"
        for extra in captured[1:]:
            await self._anomaly(
                "subscription_duplicate_payment", record, extra.payment_ref,
                "second captured payment on the same order; refund needed",
            )
        if not await self.repository.mark_paid(str(record["id"]), winner.payment_ref):
            current = await self.repository.get_billing(str(record["id"]))
            if not (
                current
                and current["status"] in _PAID
                and current["provider_payment_ref"] == winner.payment_ref
            ):
                await self._anomaly(
                    "subscription_duplicate_payment", record, winner.payment_ref,
                    "order already settled by a different payment; refund needed",
                )
                return "duplicate_payment"
        if winner.amount_refunded.amount > 0:
            await self.repository.set_refunded(str(record["id"]), winner.amount_refunded.amount)
        paid = await self.repository.get_billing(str(record["id"]))
        return await self.apply_paid(paid or record)


# ============================================================ owner-facing use cases
class SubscriptionBillingUseCases:
    def __init__(
        self,
        repository: SubscriptionBillingRepository | None,
        resolver: SubscriptionProviderResolver,
        settings: Settings,
        workspace: Any = None,
        features: FeatureAccessRepository | None = None,
    ) -> None:
        self.repository = repository  # type: ignore[assignment]
        self.features = features
        self.resolver = resolver
        self.settings = settings
        self.workspace = workspace
        self.settlement = (
            SubscriptionSettlement(repository, resolver, settings) if repository else None
        )

    # ------------------------------------------------------------ helpers
    async def _owner_salon(self, actor: Profile) -> str:
        if actor.role is not Role.owner:
            raise ForbiddenError("Salon owner access required")
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        if salon_id is None:
            raise ForbiddenError("Active salon workspace required")
        return salon_id

    @staticmethod
    def _require_key(key: str | None) -> str:
        if not key or not key.strip():
            raise IdempotencyKeyRequiredError("The Idempotency-Key header is required")
        key = key.strip()
        if not 8 <= len(key) <= 200:
            raise IdempotencyKeyRequiredError("Idempotency-Key must be 8-200 characters")
        return key

    def _require_provider(self):
        if not self.resolver.enabled:
            raise PaymentProviderNotConfiguredError("Subscription billing is not available yet")
        return self.resolver.resolve()

    # -------------------------------------------------------------- config
    def config(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "enabled": self.resolver.enabled,
            "provider": None,
            "mode": "one_time",
            "renewal": "manual",
            "native_purchase_allowed": False,  # store policy: purchase happens on the website
            "public_key": None,
            "currency": "INR",
            "checkout_url": self.settings.subscription_website_url,
        }
        if self.resolver.enabled:
            client = self.resolver.resolve().client_config()
            body["provider"] = client.provider
            body["public_key"] = client.public_key
        return body

    # --------------------------------------------------------------- plans
    async def list_plans(self, actor: Profile) -> list[dict[str, Any]]:
        if actor.role not in {Role.owner, Role.super_admin}:
            raise ForbiddenError("Salon owner access required")
        # An owner sees their own salon's prices; an admin has no salon, so sees the plan prices.
        salon_id = await self._owner_salon(actor) if actor.role is Role.owner else None
        return await self.repository.list_purchasable_plans(salon_id)

    # --------------------------------------------------------------- state
    @staticmethod
    def _entitlement(sub: dict[str, Any] | None, now: datetime | None = None) -> Entitlement:
        return derive_entitlement(
            status=str(sub["status"]) if sub else None,
            period_start=sub["current_period_start"] if sub else None,
            period_end=sub["current_period_end"] if sub else None,
            grace_end=sub["grace_period_end"] if sub else None,
            now=now or datetime.now(UTC),
        )

    @staticmethod
    def payment_view(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "plan_code": row["plan_code"],
            "status": row["status"],
            "amount": _body_amount(row["amount"]),
            "currency": row["currency"],
            "billing_interval": row["billing_interval"],
            "tax_amount": _body_amount(row["tax_amount"]),
            "tax_inclusive": row["tax_inclusive"],
            "refunded_amount": _body_amount(row["refunded_amount"]),
            "order_ref": row["provider_order_ref"],
            "receipt": row["receipt"],
            "period_start": row["period_start"],
            "period_end": row["period_end"],
            "expires_at": row["expires_at"],
            "paid_at": row["paid_at"],
            "applied_at": row["applied_at"],
            # Provider-side verification and backend entitlement are different facts.
            "payment_verified": row["status"] in _PAID,
            "entitlement_applied": row["applied_at"] is not None,
            "created_at": row["created_at"],
        }

    async def state_for_salon(self, salon_id: str) -> dict[str, Any]:
        sub = await self.repository.latest_subscription(salon_id)
        ent = self._entitlement(sub)
        history = await self.repository.list_history(salon_id, 1, 0)
        open_row = await self.repository.get_open_billing(salon_id)
        features = (sub or {}).get("plan_features") or {}
        return {
            "provider_enabled": self.resolver.enabled,
            "status": str(sub["status"]) if sub else None,
            "plan": (
                {
                    "id": str(sub["plan_id"]),
                    "code": sub["plan_code"],
                    "name": sub["plan_name"],
                    "tier": sub["plan_tier"],
                }
                if sub
                else None
            ),
            "entitlement_active": ent.active,
            "entitlement_state": ent.state.value,
            "features": features if ent.active else {},
            "paid_through": ent.paid_through,
            "grace_ends_at": ent.grace_ends_at if ent.state is EntitlementState.grace else None,
            "in_grace": ent.state is EntitlementState.grace,
            "renewal": "manual",
            "cancelled": bool(sub and str(sub["status"]) == "cancelled"),
            "cancelled_at": sub["cancelled_at"] if sub else None,
            "latest_payment": self.payment_view(history[0]) if history else None,
            "open_checkout": self.payment_view(open_row) if open_row else None,
        }

    async def get_subscription(self, actor: Profile) -> dict[str, Any]:
        return await self.state_for_salon(await self._owner_salon(actor))

    async def access_state(self, actor: Profile) -> dict[str, Any]:
        """What the SUBSCRIPTION alone implies. Phase 1 extends this with trial/soft-lock."""

        state = await self.get_subscription(actor)
        salon_id = await self._owner_salon(actor)
        access = await self.repository.booking_access(salon_id)
        tier = (state["plan"] or {}).get("tier")
        if not state["entitlement_active"]:
            label = "not_subscribed"
        elif tier == 1:
            label = "subscribed_growth"
        elif tier is not None and tier >= 2:
            label = "subscribed_premium"
        else:
            label = "subscribed"
        feature_access, plan_content = await self._feature_view(salon_id, state, tier, access)
        return {
            "access_state": label,
            "entitlement_active": state["entitlement_active"],
            "entitlement_state": state["entitlement_state"],
            # Plan benefits stay for older app builds; resolved feature switches win over them.
            "features": {
                **state["features"],
                **{k: v["enabled"] for k, v in (feature_access or {}).items()},
            },
            "feature_access": feature_access,
            "plan_content": plan_content,
            "paid_through": state["paid_through"],
            "grace_ends_at": state["grace_ends_at"],
            "source": "subscription",
            "accepts_new_bookings": bool(access["eligible"]),
            "subscription_wall": not bool(access["eligible"]),
            "wall_messages": [] if access["eligible"] else [
                "Your salon is hidden from customers.",
                "Subscribe to restore search visibility, online payments, and booking details.",
            ],
            "trial_started_at": access.get("trial_started_at"),
            "trial_ends_at": access.get("trial_ends_at"),
            "trial_booking_limit": access.get("trial_booking_limit"),
            "trial_bookings_counted": access.get("bookings_counted"),
        }

    async def _feature_view(
        self, salon_id: str, state: dict[str, Any], tier: int | None, access: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Super-admin feature switches for this salon, or ``(None, None)`` when the feature repository is not wired."""

        if self.features is None:
            return None, None
        now = datetime.now(UTC)
        trial = TrialState(
            started_at=access.get("trial_started_at"),
            ends_at=access.get("trial_ends_at"),
            booking_limit=access.get("trial_booking_limit"),
            bookings_counted=access.get("bookings_counted"),
            limit_reached_at=access.get("trial_limit_reached_at"),
        )
        resolved = await self.features.resolve_for_salon(
            salon_id,
            entitlement_active=bool(state["entitlement_active"]),
            tier=tier,
            trial_active=trial.active(now),
            now=now,
        )
        return resolved, await self.features.plan_content()

    async def history(self, actor: Profile, limit: int, offset: int) -> list[dict[str, Any]]:
        salon_id = await self._owner_salon(actor)
        rows = await self.repository.list_history(salon_id, limit, offset)
        return [self.payment_view(r) for r in rows]

    # ------------------------------------------------------------ checkout
    async def checkout(self, actor: Profile, plan_id: str, key: str | None) -> dict[str, Any]:
        provider = self._require_provider()
        key = self._require_key(key)
        salon_id = await self._owner_salon(actor)
        await assert_approved_workspace(self.workspace, actor)
        scope = f"sub-checkout:{salon_id}"
        fingerprint = hashlib.sha256(f"plan={plan_id}".encode()).hexdigest()
        replay = await self.repository.begin_idempotent(
            actor.id, scope, key, fingerprint, self.settings.payment_idempotency_ttl_seconds
        )
        if replay is not None:
            if replay.get("provider") != provider.provider_name:
                raise ConflictError("This payment belongs to a different provider; contact support")
            return replay

        plan = await self.repository.get_plan(plan_id)
        if plan is None or not plan["is_active"] or Decimal(plan["price_amount"]) <= 0:
            raise NotFoundError("Subscription plan not found")
        sub = await self.repository.latest_subscription(salon_id)
        if sub and str(sub["status"]) == "suspended":
            raise ConflictError("This subscription is suspended; contact support")
        ent = self._entitlement(sub)
        if ent.state in {EntitlementState.active, EntitlementState.cancelled_paid_through} and (
            str(sub["plan_id"]) != str(plan["id"])
        ):
            raise ConflictError(
                "Plan changes are not supported while a paid period is running; renew the "
                "current plan or wait until it ends"
            )

        record = await self.repository.get_open_billing(salon_id)
        resumed = False
        if record is not None:
            if record["provider"] != provider.provider_name:
                await self._abandon(actor, scope, key)
                raise ConflictError("An existing payment uses a different provider; contact support before paying")
            expired = record["expires_at"] <= datetime.now(UTC)
            if str(record["plan_id"]) == str(plan["id"]) and not expired:
                resumed = True  # a crash/timeout or a second tab: finish the same order
            elif expired:
                await self.repository.finish_unpaid(str(record["id"]), "expired")
                record = None
            else:
                raise ConflictError(
                    "A different subscription payment is already open; finish it or wait for it to expire"
                )
        if record is None:
            record = await self.repository.insert_billing(
                salon_id=salon_id,
                plan_id=str(plan["id"]),
                provider=provider.provider_name,
                receipt="sub_" + uuid.uuid4().hex,
                actor_id=actor.id,
                ttl_seconds=self.settings.subscription_order_ttl_seconds,
            )
        # The purchase identity is durable BEFORE the provider is called.
        await self.repository.commit()
        await self.repository.set_actor(actor.id)

        order = await self._obtain_order(actor, scope, key, provider, record, resumed)
        await self.repository.set_order_ref(str(record["id"]), order.order_ref)
        body = {
            "billing_id": str(record["id"]),
            "provider": order.provider,
            "order_ref": order.order_ref,
            "receipt": record["receipt"],
            "plan_id": str(plan["id"]),
            "plan_code": record["plan_code"],
            "amount": _body_amount(record["amount"]),
            "currency": record["currency"],
            "billing_interval": record["billing_interval"],
            "expires_at": record["expires_at"].isoformat(),
            "client_payload": dict(order.client_payload),
        }
        await self.repository.finish_idempotent(actor.id, scope, key, 200, body)
        await self.repository.commit()
        return body

    async def _obtain_order(
        self, actor: Profile, scope: str, key: str, provider: Any, record: dict[str, Any], resumed: bool
    ) -> ProviderOrder:
        request = SubscriptionOrderRequest(
            receipt=record["receipt"],
            billing_record_id=str(record["id"]),
            salon_id=str(record["salon_id"]),
            plan_id=str(record["plan_id"]),
            amount=Money(record["amount"]),
            currency=record["currency"],
            customer_id=str(actor.id),
            customer_phone=actor.phone,
            customer_email=actor.email,
            customer_name=actor.full_name,
            return_url=(
                f"{self.settings.subscription_website_url}"
                f"{'&' if '?' in self.settings.subscription_website_url else '?'}"
                f"{urlencode({'plan': record['plan_code']})}"
                if self.settings.subscription_website_url else None
            ),
            expires_at=record["expires_at"],
        )
        try:
            order: ProviderOrder | None = None
            if record["provider_order_ref"]:
                order = await provider.fetch_order(record["provider_order_ref"])
            elif resumed:
                order = await provider.find_order_by_receipt(record["receipt"])
            if order is None:
                order = await provider.create_period_order(request)
            return self._checked(order, record)
        except PaymentOutcomeUnknownError:
            recovered = None
            try:
                recovered = await provider.find_order_by_receipt(record["receipt"])
            except Exception:  # still unknown: the persisted receipt lets a retry/worker finish
                _log.warning("Subscription order %s outcome still unknown", record["id"])
            if recovered is not None:
                return self._checked(recovered, record)
            await self._abandon(actor, scope, key)
            raise
        except ConflictError:
            # e.g. the resumed order was paid meanwhile: free the key so the owner can verify/retry
            await self._abandon(actor, scope, key)
            raise
        except (PaymentProviderError, ValueError, ValidationError) as exc:
            await self.repository.finish_unpaid(str(record["id"]), "failed")
            await self._abandon(actor, scope, key)
            if isinstance(exc, ValueError):
                raise ValidationError("The subscription payment could not be started") from exc
            raise

    @staticmethod
    def _checked(order: ProviderOrder, record: dict[str, Any]) -> ProviderOrder:
        if order.amount.amount != Decimal(record["amount"]) or order.currency != record["currency"]:
            raise PaymentProviderError("Subscription provider returned a different order")
        if order.state is ProviderOrderState.paid:
            raise ConflictError("This subscription payment is already paid; refresh its status")
        return order

    async def _abandon(self, actor: Profile, scope: str, key: str) -> None:
        await self.repository.release_idempotent(actor.id, scope, key)
        await self.repository.commit()

    # -------------------------------------------------------------- verify
    async def verify(
        self,
        actor: Profile,
        order_ref: str,
        payment_ref: str | None = None,
        signature: str | None = None,
    ) -> dict[str, Any]:
        salon_id = await self._owner_salon(actor)
        provider = self._require_provider()
        record = await self.repository.get_billing_by_order(provider.provider_name, order_ref)
        if record is None or str(record["salon_id"]) != salon_id:
            raise NotFoundError("Subscription payment not found")
        hint = None
        if payment_ref and signature and provider.verify_client_callback(
            order_ref, payment_ref, signature
        ):
            hint = payment_ref  # only tells us WHICH payment to fetch; the fetch is the proof
        outcome = await self.settlement.settle(record, hint_payment_ref=hint)
        await self.repository.commit()
        state = await self.state_for_salon(salon_id)
        state["verification"] = outcome
        return state

    # -------------------------------------------------------------- cancel
    async def cancel(self, actor: Profile) -> dict[str, Any]:
        salon_id = await self._owner_salon(actor)
        outcome = await self.repository.cancel_renewal(salon_id)
        if outcome == "none":
            raise NotFoundError("No subscription to cancel")
        await self.repository.commit()
        return await self.state_for_salon(salon_id)


# ============================================================ webhook handling
class SubscriptionWebhookHandler:
    """Applies a stored, signature-verified subscription event (normalised JSON)."""

    def __init__(
        self,
        repository: SubscriptionBillingRepository,
        resolver: SubscriptionProviderResolver,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings
        self.settlement = SubscriptionSettlement(repository, resolver, settings)

    async def apply(self, provider_name: str, data: dict[str, Any], event_id: str = "") -> str:
        """Returns ``applied|ignored|mismatch``; raises to schedule a retry."""

        kind = SubscriptionEventKind(data.get("kind", "ignored"))
        if kind is SubscriptionEventKind.ignored or not self.resolver.enabled:
            return "ignored"
        if self.resolver.provider_name != provider_name:
            return "ignored"
        if kind in {SubscriptionEventKind.payment_captured, SubscriptionEventKind.order_paid,
                    SubscriptionEventKind.payment_failed}:
            record = await self._record_for_payment_event(provider_name, data)
            if record is None:
                return "ignored"  # a valid event for an order that is not ours / not known yet
            if kind is SubscriptionEventKind.payment_failed:
                await self.repository.note_failure(str(record["id"]), data.get("failure_code"))
                return "applied"
            if self._differs(record, data):
                await self.settlement._anomaly(
                    "subscription_amount_mismatch", record, data.get("payment_ref") or event_id,
                    "webhook amount/currency differs from the purchase snapshot",
                )
                _log.error("ALERT subscription_billing: webhook amount mismatch on %s", record["id"])
                return "mismatch"
            outcome = await self.settlement.settle(
                record, hint_payment_ref=data.get("payment_ref")
            )
            if outcome in _APPLIED_OUTCOMES:
                return "applied"
            if outcome in {"pending", "no_order"}:
                # The event outran the provider's own read model: retry with backoff.
                raise PaymentOutcomeUnknownError("Provider does not show the payment yet")
            return "mismatch"
        if kind in {SubscriptionEventKind.refund_processed, SubscriptionEventKind.refund_failed}:
            return await self._refund(provider_name, data, event_id, kind)
        return "ignored"

    async def _record_for_payment_event(
        self, provider_name: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        record = None
        if data.get("order_ref"):
            record = await self.repository.get_billing_by_order(provider_name, data["order_ref"])
        if record is None and data.get("payment_ref"):
            record = await self.repository.get_billing_by_payment(provider_name, data["payment_ref"])
        return record

    @staticmethod
    def _differs(record: dict[str, Any], data: dict[str, Any]) -> bool:
        if data.get("amount") is not None and Money(data["amount"]).amount != Decimal(record["amount"]):
            return True
        return data.get("currency") is not None and data["currency"] != record["currency"]

    async def _refund(
        self, provider_name: str, data: dict[str, Any], event_id: str, kind: SubscriptionEventKind
    ) -> str:
        payment_ref = data.get("payment_ref")
        record = (
            await self.repository.get_billing_by_payment(provider_name, payment_ref)
            if payment_ref
            else None
        )
        if record is None:
            return "ignored"
        ref = data.get("refund_ref") or event_id
        if kind is SubscriptionEventKind.refund_failed:
            await self.settlement._anomaly(
                "subscription_refund", record, f"failed:{ref}", "provider reported a failed refund"
            )
            return "applied"
        observed = await self.resolver.for_provider(provider_name).fetch_payment(payment_ref)
        if observed is None:
            raise PaymentOutcomeUnknownError("Provider does not show the payment")
        # Absolute and monotonic: duplicate or reordered refund events converge.
        await self.repository.set_refunded(str(record["id"]), observed.amount_refunded.amount)
        await self.settlement._anomaly(
            "subscription_refund", record, f"processed:{ref}",
            "refund recorded; remaining access is NOT revoked automatically (operator decision)",
        )
        return "applied"


# ============================================================ reconciliation
class SubscriptionReconciler:
    """Worker pass, independent of HTTP: settle stale orders, expire unpaid ones, sweep lapses."""

    def __init__(
        self,
        repository: SubscriptionBillingRepository,
        resolver: SubscriptionProviderResolver,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings
        self.settlement = SubscriptionSettlement(repository, resolver, settings)

    async def run(self, limit: int = 20) -> dict[str, int]:
        counts = {"settled": 0, "expired": 0, "reapplied": 0, "lapsed": 0, "errors": 0}
        if self.resolver.enabled:
            await self._open_orders(limit, counts)
            await self._unapplied(limit, counts)
        try:
            counts["lapsed"] = await self.repository.sweep_lapsed()
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            counts["errors"] += 1
            _log.exception("ALERT subscription_billing: lapse sweep failed")
        return counts

    async def _open_orders(self, limit: int, counts: dict[str, int]) -> None:
        rows = await self.repository.list_stale_open(
            self.settings.subscription_reconcile_after_seconds, limit
        )
        for row in rows:
            try:
                outcome = await self.settlement.settle(row)
                if outcome in _APPLIED_OUTCOMES:
                    counts["settled"] += 1
                elif outcome in {"pending", "no_order"}:
                    if row["is_expired"]:
                        fresh = await self.repository.get_billing(str(row["id"]))
                        failed = bool(fresh and fresh.get("failure_code"))
                        await self.repository.finish_unpaid(
                            str(row["id"]), "failed" if failed else "expired"
                        )
                        counts["expired"] += 1
                    else:
                        await self.repository.touch(str(row["id"]))
                await self.repository.commit()
            except Exception:
                await self.repository.rollback()
                counts["errors"] += 1
                _log.exception("ALERT subscription_billing: reconcile failed for %s", row["id"])

    async def _unapplied(self, limit: int, counts: dict[str, int]) -> None:
        for row in await self.repository.list_unapplied_paid(limit):
            try:
                outcome = await self.settlement.apply_paid(row)
                if outcome in {"started", "renewed"}:
                    counts["reapplied"] += 1
                await self.repository.commit()
            except Exception:
                await self.repository.rollback()
                counts["errors"] += 1
                _log.exception("ALERT subscription_billing: re-apply failed for %s", row["id"])


__all__ = [
    "SubscriptionBillingUseCases",
    "SubscriptionReconciler",
    "SubscriptionSettlement",
    "SubscriptionWebhookHandler",
    "subscription_event_to_json",
]
