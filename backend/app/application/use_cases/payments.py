"""Booking payment use cases: intents, confirmation, refunds, earnings, webhooks.

Authorization lives here. Amounts are read from the booking (computed in SQL by
``create_booking``); nothing in this module accepts an amount from a client except an
optional *partial refund* amount, which is bounded by the captured payment.

Crash safety rule used throughout: persist the operation identity and COMMIT before every
outbound provider call, never hold a transaction or row lock across the call, and on an
unknown outcome reconcile by the persisted identity instead of retrying blindly.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentEvent,
    PaymentGateway,
    PaymentIntent,
    PaymentIntentRequest,
    ProviderPayment,
    RefundRequest,
    SettlementAccountRequest,
)
from app.application.ports.subscription_provider import SubscriptionEventKind
from app.application.use_cases.subscription_billing import (
    SubscriptionWebhookHandler,
    subscription_event_to_json,
)
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    IdempotencyKeyRequiredError,
    InvalidWebhookSignatureError,
    NotFoundError,
    PaymentAmountMismatchError,
    PaymentCapabilityError,
    PaymentInProgressError,
    PaymentOutcomeUnknownError,
    PaymentOvercollectionError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
    WebhookPayloadTooLargeError,
)
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    PaymentEventType,
    WebhookDomain,
    derive_payment_state,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_owner
from app.domain.services.commission import commission_reversal, compute_commission
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.payments.resolver import PaymentGatewayResolver
from app.infrastructure.subscriptions.resolver import get_subscription_resolver

_log = logging.getLogger(__name__)

_EVENT_STATUS = {
    PaymentEventType.payment_authorized: "authorized",
    PaymentEventType.payment_captured: "captured",
    PaymentEventType.payment_failed: "failed",
}
_SETTLED_STATUSES = {
    LedgerStatus.captured,
    LedgerStatus.partially_refunded,
    LedgerStatus.refunded,
}
_SAFE_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- ")


def _fingerprint(**fields: Any) -> str:
    return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode()).hexdigest()


def _clean_code(value: str | None) -> str | None:
    """Provider-supplied codes are stored as-is only when they look like codes."""

    if not value:
        return None
    cleaned = "".join(c for c in str(value) if c in _SAFE_CODE_CHARS).strip()[:120]
    return cleaned or None


def _ledger_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "booking_id": str(row["booking_id"]),
        "channel": row["channel"],
        "purpose": row["purpose"],
        "settlement_model": row["settlement_model"],
        "provider": row.get("provider"),
        "method": row.get("method"),
        "instrument": row.get("instrument"),
        "amount": row["amount"],
        "currency": row["currency"],
        "status": row["status"],
        "overcollected_amount": row.get("overcollected_amount") or Decimal("0.00"),
        "failure_code": row.get("failure_code"),
        "expires_at": row.get("expires_at"),
        "captured_at": row.get("captured_at"),
        "created_at": row["created_at"],
    }


def event_to_json(event: PaymentEvent) -> dict[str, Any]:
    """Serialise a normalised event for the intake table (identifiers and amounts only)."""

    return {
        "domain": event.domain.value,
        "event_type": event.event_type.value,
        "raw_type": _clean_code(event.raw_type),
        "payment_ref": event.payment_ref,
        "order_ref": event.order_ref,
        "refund_ref": event.refund_ref,
        "amount": str(event.amount.amount) if event.amount else None,
        "currency": event.currency,
        "instrument": event.instrument.value if event.instrument else None,
        "failure_code": _clean_code(event.failure_code),
        "account_ref": event.account_ref,
        "onboarding_status": event.onboarding_status.value if event.onboarding_status else None,
        "settlement_status": event.settlement_status,
    }


def observation_status(observed: ProviderPayment) -> LedgerStatus:
    """Collapse refund-progress statuses: the ledger tracks refunds on their own rows."""

    return LedgerStatus.captured if observed.status in _SETTLED_STATUSES else observed.status


async def apply_provider_payment(
    repository: PaymentRepository, provider: str, order_ref: str, observed: ProviderPayment
) -> str:
    """Fold a fetched provider payment into the ledger (shared by confirm, refresh, reconcile)."""

    return await repository.apply_payment_observation(
        provider=provider,
        order_ref=order_ref,
        payment_ref=observed.payment_ref,
        status=observation_status(observed).value,
        amount=observed.amount.amount,
        currency=observed.currency,
        instrument=observed.instrument.value if observed.instrument else None,
        failure_code=_clean_code(observed.failure_code),
    )


@dataclass(frozen=True, slots=True)
class SettlementRegistrationDetails:
    """KYC/bank details for payee registration. Used once in memory, never stored or logged."""

    legal_name: str = field(repr=False)
    contact_email: str = field(repr=False)
    contact_phone: str = field(repr=False)
    account_type: str = field(repr=False)
    business_type: str = field(repr=False)
    pan: str = field(repr=False)
    bank_account_number: str | None = field(default=None, repr=False)
    ifsc: str | None = field(default=None, repr=False)
    upi_id: str | None = field(default=None, repr=False)


class BookingPaymentUseCases:
    """Customer and owner payment operations."""

    def __init__(
        self,
        repository: PaymentRepository,
        resolver: PaymentGatewayResolver,
        settings: Settings,
        workspace: Any = None,
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings
        self.workspace = workspace  # PlatformRepository, for the approved-workspace check

    # ---------------------------------------------------------------- helpers
    def _require_gateway(self, capability: GatewayCapability) -> PaymentGateway:
        if not self.resolver.enabled:
            raise PaymentProviderNotConfiguredError("Online payment is not available yet")
        gateway = self.resolver.resolve()
        if not gateway.supports(capability):
            raise PaymentCapabilityError("The payment provider does not support this operation")
        return gateway

    def _gateway_of(self, row: dict[str, Any], capability: GatewayCapability) -> PaymentGateway:
        """The gateway that HOLDS this row's money (never the currently configured one)."""

        gateway = self.resolver.for_provider(row.get("provider"))
        if not gateway.supports(capability):
            raise PaymentCapabilityError("The payment provider does not support this operation")
        return gateway

    @staticmethod
    def _require_key(key: str | None) -> str:
        if not key or not key.strip():
            raise IdempotencyKeyRequiredError("The Idempotency-Key header is required")
        key = key.strip()
        if not 8 <= len(key) <= 200:
            raise IdempotencyKeyRequiredError("Idempotency-Key must be 8-200 characters")
        return key

    async def _idempotent(
        self, actor: Profile, scope: str, key: str, fingerprint: str
    ) -> dict[str, Any] | None:
        return await self.repository.begin_idempotent(
            actor.id, scope, key, fingerprint, self.settings.payment_idempotency_ttl_seconds
        )

    async def _store_and_commit(
        self, actor: Profile, scope: str, key: str, body: dict[str, Any], status_code: int = 200
    ) -> None:
        await self.repository.finish_idempotent(actor.id, scope, key, status_code, body)
        await self.repository.commit()

    async def _checkpoint(self, actor: Profile) -> None:
        """Commit (releasing every lock) and re-arm the audit actor for what follows."""

        await self.repository.commit()
        await self.repository.set_actor(actor.id)

    async def _abandon(self, actor: Profile, scope: str, key: str) -> None:
        """Release the idempotency reservation so the client can retry with the same key."""

        await self.repository.release_idempotent(actor.id, scope, key)
        await self.repository.commit()

    @staticmethod
    def _is_customer_of(booking: dict[str, Any], actor: Profile) -> bool:
        return booking.get("customer_id") is not None and str(booking["customer_id"]) == actor.id

    @staticmethod
    def _is_salon_side(booking: dict[str, Any], actor: Profile) -> bool:
        return (
            booking.get("owner_id") is not None and str(booking["owner_id"]) == actor.id
        ) or bool(booking.get("actor_is_staff"))

    # ----------------------------------------------------------------- config
    def config(self) -> dict[str, Any]:
        base = {
            "currency": self.settings.payment_currency,
            "advance_percent": self.settings.payment_advance_percent,
        }
        if not self.resolver.enabled:
            return {"enabled": False, **base}
        gateway = self.resolver.resolve()
        client = gateway.client_config()
        return {
            "enabled": client.enabled,
            "provider": client.provider,
            "public_key": client.public_key,
            "settlement_model": client.settlement_model.value if client.settlement_model else None,
            # How the app finishes: 'callback' (sign-verified confirm) or 'refresh'
            # (server-side status refresh; the SDK callback is not proof of payment).
            "confirmation": (
                "callback" if gateway.supports(GatewayCapability.callback_signature) else "refresh"
            ),
            **base,
        }

    # ------------------------------------------------------------- commission
    def _commission_policy(self) -> tuple[Decimal, str, str]:
        rate = self.settings.payment_platform_fee_percent
        base = self.settings.payment_commission_base
        if rate is None or base is None:
            raise PaymentProviderNotConfiguredError("The commission policy is not configured")
        return Decimal(rate), base, self.settings.payment_commission_policy_version

    # ----------------------------------------------------------------- intent
    async def create_intent(
        self, actor: Profile, booking_id: str, key: str | None, purpose: str | None
    ) -> dict[str, Any]:
        gateway = self._require_gateway(GatewayCapability.online_collection)
        key = self._require_key(key)
        scope = f"intent:{booking_id}"
        replay = await self._idempotent(actor, scope, key, _fingerprint(purpose=purpose))
        if replay is not None:
            return replay

        booking = await self.repository.lock_booking(booking_id, actor.id)
        if booking is None or not self._is_customer_of(booking, actor):
            raise NotFoundError("Booking not found")
        if booking["status"] not in {"pending", "confirmed"}:
            raise ConflictError("Only pending or confirmed bookings can be paid online")

        total = Money(booking["total_price"])
        net = Money(Decimal(booking["paid_amount"]) - Decimal(booking["refunded_amount"]))
        if net.amount >= total.amount:
            raise ConflictError("This booking is already fully paid")
        if purpose is None:
            if net.amount > 0:
                purpose = "balance"
            elif booking["payment_preference"] == "pay_advance" and booking["deposit_amount"]:
                purpose = "deposit"
            else:
                purpose = "full"
        if purpose == "deposit":
            if net.amount > 0 or not booking["deposit_amount"]:
                raise ConflictError("No deposit is due on this booking")
            amount = Money(booking["deposit_amount"])
        elif purpose == "balance":
            if net.amount <= 0:
                raise ConflictError("Nothing has been paid yet; use purpose 'full'")
            amount = total - net
        else:
            if net.amount > 0:
                raise ConflictError("Part of this booking is already paid; use purpose 'balance'")
            amount = total

        await self.repository.expire_stale_open_intents(booking_id)
        resume: dict[str, Any] | None = None
        if await self.repository.get_open_intent(booking_id) is not None:
            candidate = await self.repository.get_resumable_intent(booking_id)
            if (
                candidate is not None
                and str(candidate.get("payer_id")) == actor.id
                and candidate["provider"] == gateway.provider_name
                and candidate["purpose"] == purpose
                and Decimal(candidate["amount"]) == amount.amount
            ):
                resume = candidate  # a crash/timeout left it unacknowledged: finish it
            else:
                raise PaymentInProgressError(
                    "An online payment is already open for this booking; finish or cancel it"
                )

        account_ref = None
        if gateway.supports(GatewayCapability.split_settlement):
            account = await self.repository.get_provider_account(
                str(booking["salon_id"]), gateway.provider_name
            )
            if not account or account["onboarding_status"] != "active":
                raise ConflictError("This salon cannot take online payments yet")
            account_ref = account["provider_account_ref"]

        if resume is not None:
            payment_id = str(resume["id"])
            intent_reference = resume["intent_reference"]
            order_ref = resume.get("order_ref")
            fee = Money(resume["platform_commission_amount"])
        else:
            rate, base, version = self._commission_policy()
            allocated = await self.repository.commission_allocated(booking_id)
            fee = Money(
                compute_commission(
                    rate_percent=rate,
                    base=base,
                    payment_amount=amount.amount,
                    booking_total=total.amount,
                    already_allocated=allocated,
                )
            )
            intent_reference = "pi_" + uuid.uuid4().hex
            order_ref = gateway.deterministic_order_ref(intent_reference)
            payment_id = await self.repository.insert_intent(
                booking=booking,
                actor_id=actor.id,
                purpose=purpose,
                amount=amount.amount,
                commission_amount=fee.amount,
                commission_rate_percent=rate,
                commission_base=base,
                commission_policy_version=version,
                provider=gateway.provider_name,
                settlement_model=self.resolver.settlement_model.value,
                intent_reference=intent_reference,
                order_ref=order_ref,
                expires_in_seconds=self.settings.payment_intent_ttl_seconds,
            )
        # The operation identity is durable (and the booking lock released) BEFORE the call.
        await self._checkpoint(actor)

        request = PaymentIntentRequest(
            intent_reference=intent_reference,
            booking_id=str(booking["id"]),
            salon_id=str(booking["salon_id"]),
            amount=amount,
            currency=booking["currency"],
            customer_id=actor.id,
            settlement_model=self.resolver.settlement_model,
            settlement_account_ref=account_ref,
            platform_fee=fee,
            customer_phone=actor.phone,
            customer_email=actor.email,
            customer_name=actor.full_name,
        )
        intent = await self._call_create_intent(
            actor, scope, key, gateway, request, payment_id, order_ref, resumed=resume is not None
        )
        await self.repository.confirm_intent_order(payment_id, intent.order_ref)
        body = json.loads(
            json.dumps(
                {
                    "payment_id": payment_id,
                    "provider": intent.provider,
                    "order_ref": intent.order_ref,
                    "purpose": purpose,
                    "amount": str(intent.amount.amount),
                    "currency": intent.currency,
                    "client_payload": dict(intent.client_payload),
                    "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
                }
            )
        )
        await self._store_and_commit(actor, scope, key, body, 200)
        return body

    async def _call_create_intent(
        self,
        actor: Profile,
        scope: str,
        key: str,
        gateway: PaymentGateway,
        request: PaymentIntentRequest,
        payment_id: str,
        order_ref: str | None,
        *,
        resumed: bool,
    ) -> PaymentIntent:
        """Create (or recover) the provider order; classify failures by certainty."""

        try:
            if resumed and order_ref:
                try:
                    existing = await gateway.fetch_intent(order_ref, request)
                except PaymentCapabilityError:
                    existing = None
                if existing is not None:
                    return self._checked_intent(existing, request)
            return self._checked_intent(await gateway.create_payment_intent(request), request)
        except PaymentOutcomeUnknownError:
            recovered: PaymentIntent | None = None
            if order_ref:
                try:
                    recovered = await gateway.fetch_intent(order_ref, request)
                except Exception:  # still unknown: the persisted order id lets reconcile finish it
                    _log.warning("Intent %s outcome still unknown after a timeout", payment_id)
            if recovered is not None:
                return self._checked_intent(recovered, request)
            # The row stays open and unacknowledged; a retry resumes it and the worker's
            # reconcile pass asks the provider about its order id.
            await self._abandon(actor, scope, key)
            raise
        except (PaymentProviderError, PaymentCapabilityError, ValidationError, ValueError) as exc:
            # A definitive refusal: nothing exists at the provider, free the booking.
            await self.repository.fail_intent(payment_id, "provider_rejected")
            await self._abandon(actor, scope, key)
            if isinstance(exc, ValueError):
                raise ValidationError("The payment could not be started") from exc
            raise

    @staticmethod
    def _checked_intent(intent: PaymentIntent, request: PaymentIntentRequest) -> PaymentIntent:
        if intent.amount.amount != request.amount.amount or intent.currency != request.currency:
            raise PaymentProviderError("Payment provider returned a different order")
        return intent

    # ---------------------------------------------------------------- confirm
    async def confirm(
        self,
        actor: Profile,
        booking_id: str,
        order_ref: str,
        payment_ref: str | None,
        signature: str | None,
        key: str | None,
    ) -> dict[str, Any]:
        """Client "I paid" call. Signed-callback providers are verified; the rest refresh."""

        return await self._settle(
            actor, booking_id, order_ref, payment_ref, signature, key, scope_name="confirm"
        )

    async def refresh(
        self, actor: Profile, booking_id: str, order_ref: str, key: str | None
    ) -> dict[str, Any]:
        """Server-side status refresh: the backend asks the provider, the client proves nothing."""

        return await self._settle(
            actor, booking_id, order_ref, None, None, key, scope_name="refresh"
        )

    async def _settle(
        self,
        actor: Profile,
        booking_id: str,
        order_ref: str,
        payment_ref: str | None,
        signature: str | None,
        key: str | None,
        *,
        scope_name: str,
    ) -> dict[str, Any]:
        if not self.resolver.enabled:
            raise PaymentProviderNotConfiguredError("Online payment is not available yet")
        key = self._require_key(key)
        scope = f"{scope_name}:{booking_id}"
        replay = await self._idempotent(
            actor, scope, key, _fingerprint(o=order_ref, p=payment_ref, s=signature)
        )
        if replay is not None:
            return replay
        # Authorization only: no row lock is held while the provider is called.
        booking = await self.repository.read_booking(booking_id, actor.id)
        if booking is None or not self._is_customer_of(booking, actor):
            raise NotFoundError("Booking not found")
        row = await self.repository.get_payment_by_order(booking_id, order_ref)
        if row is None:
            raise NotFoundError("Payment not found")
        gateway = self._gateway_of(row, GatewayCapability.online_collection)

        verified_payment_ref: str | None = None
        if scope_name == "confirm" and gateway.supports(GatewayCapability.callback_signature):
            if not payment_ref or not signature:
                raise ValidationError("payment_ref and signature are required for this provider")
            if not gateway.verify_payment_callback(
                PaymentCallback(order_ref=order_ref, payment_ref=payment_ref, signature=signature)
            ):
                raise ValidationError("Payment could not be verified")
            verified_payment_ref = payment_ref
        # Any client-provided "success" is ignored: the provider is always asked.
        observed = await gateway.fetch_payment(
            payment_ref=verified_payment_ref, order_ref=None if verified_payment_ref else order_ref
        )
        if observed is not None and observed.order_ref not in (None, order_ref):
            raise ValidationError("Payment could not be verified")
        outcome = "ignored"
        if observed is not None:
            outcome = await apply_provider_payment(
                self.repository, row["provider"], order_ref, observed
            )
        if outcome in {"mismatch", "overcollection"}:
            await self.repository.commit()  # keep the failed row/anomaly; never mark paid
            if outcome == "mismatch":
                raise PaymentAmountMismatchError("The paid amount does not match the booking")
            raise PaymentOvercollectionError("This booking has already been paid in full")
        if outcome == "overcollected":
            _log.error(
                "OVERCOLLECTION on booking %s payment row %s: capture exceeds what was owed; "
                "recorded, excess refundable via the refund API",
                booking_id,
                row["id"],
            )
        body = await self._booking_payments_body(booking_id, actor.id)
        await self._store_and_commit(actor, scope, key, body, 200)
        return body

    # ----------------------------------------------------------------- cancel
    async def cancel(self, actor: Profile, booking_id: str, key: str | None) -> dict[str, Any]:
        self._require_gateway(GatewayCapability.online_collection)
        key = self._require_key(key)
        scope = f"cancel:{booking_id}"
        replay = await self._idempotent(actor, scope, key, _fingerprint())
        if replay is not None:
            return replay
        booking = await self.repository.lock_booking(booking_id, actor.id)
        if booking is None or not self._is_customer_of(booking, actor):
            raise NotFoundError("Booking not found")
        if await self.repository.cancel_open_intent(booking_id) is None:
            raise ConflictError("There is no open online payment to cancel")
        body = await self._booking_payments_body(booking_id, actor.id)
        await self._store_and_commit(actor, scope, key, body, 200)
        return body

    # ------------------------------------------------------------------- read
    async def _booking_payments_body(self, booking_id: str, actor_id: str) -> dict[str, Any]:
        booking = await self.repository.read_booking(booking_id, actor_id)
        if booking is None:
            raise NotFoundError("Booking not found")
        payments = await self.repository.list_payments(booking_id)
        refunds = await self.repository.list_refunds(booking_id)
        state = derive_payment_state(
            booking["payment_status"], booking["paid_amount"], booking["refunded_amount"]
        )
        body = {
            "booking_id": str(booking["id"]),
            "currency": booking["currency"],
            "total_price": booking["total_price"],
            "deposit_amount": booking["deposit_amount"],
            "paid_amount": booking["paid_amount"],
            "refunded_amount": booking["refunded_amount"],
            "payment_status": booking["payment_status"],
            "payment_state": state.value,
            "payments": [_ledger_row(p) for p in payments],
            "refunds": [
                {**r, "id": str(r["id"]), "payment_id": str(r["payment_id"])} for r in refunds
            ],
        }
        return json.loads(json.dumps(body, default=_json_default))

    async def list_payments(self, actor: Profile, booking_id: str) -> dict[str, Any]:
        booking = await self.repository.read_booking(booking_id, actor.id)
        if booking is None or not (
            self._is_customer_of(booking, actor) or self._is_salon_side(booking, actor)
        ):
            raise NotFoundError("Booking not found")
        if self._is_salon_side(booking, actor) and not self._is_customer_of(booking, actor):
            await assert_approved_workspace(self.workspace, actor)
        return await self._booking_payments_body(booking_id, actor.id)

    # ----------------------------------------------------------------- refund
    async def refund(
        self,
        actor: Profile,
        booking_id: str,
        payment_id: str,
        amount: Decimal | None,
        reason: str | None,
        key: str | None,
    ) -> dict[str, Any]:
        if not self.resolver.enabled:
            raise PaymentProviderNotConfiguredError("Online payment is not available yet")
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can refund a payment")
        await assert_approved_workspace(self.workspace, actor)
        key = self._require_key(key)
        scope = f"refund:{payment_id}"
        replay = await self._idempotent(
            actor, scope, key, _fingerprint(a=str(amount) if amount else None, r=reason)
        )
        if replay is not None:
            return replay
        booking = await self.repository.lock_booking(booking_id, actor.id)
        if booking is None or str(booking["owner_id"]) != actor.id:
            raise NotFoundError("Booking not found")
        payment = await self.repository.get_payment(booking_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        if payment["channel"] != "gateway" or not payment["payment_ref"]:
            raise ConflictError("Only online payments can be refunded here; cash is settled with the customer")
        if payment["status"] not in {"captured", "partially_refunded"}:
            raise ConflictError("This payment is not refundable")
        # The row's own provider refunds it. Never the currently configured one.
        gateway = self._gateway_of(payment, GatewayCapability.refunds)

        existing = await self.repository.get_refund_by_key(payment_id, key)
        if existing is not None:
            refund_id = str(existing["id"])
            refund_amount = Money(existing["amount"])
            refund_ref = existing["refund_ref"]
            if existing["status"] != "created":
                body = await self._booking_payments_body(booking_id, actor.id)
                await self._store_and_commit(actor, scope, key, body, 200)
                return body
            reversal = Money(0)
        else:
            refund_id, refund_amount, refund_ref, reversal = await self._plan_refund(
                actor, gateway, payment, amount, reason, key
            )
        # Identity durable and locks released BEFORE the provider is asked to move money.
        await self._checkpoint(actor)

        account = await self.repository.get_provider_account(
            str(payment["salon_id"]), payment["provider"]
        )
        provider_key = hashlib.sha256(f"{payment_id}:{key}".encode()).hexdigest()[:40]
        try:
            result = await gateway.refund(
                RefundRequest(
                    payment_ref=payment["payment_ref"],
                    amount=refund_amount,
                    idempotency_key=provider_key,
                    reason=reason,
                    order_ref=payment.get("order_ref"),
                    refund_ref=refund_ref,
                    settlement_account_ref=account["provider_account_ref"] if account else None,
                    commission_reversal=reversal,
                )
            )
        except PaymentOutcomeUnknownError:
            # May or may not have been issued. The row stays 'created' (it still reserves the
            # amount); retrying with the same key re-sends the SAME provider refund id, and the
            # worker reconciles it by that id.
            await self._abandon(actor, scope, key)
            raise
        except (PaymentProviderError, PaymentCapabilityError):
            await self.repository.update_refund(refund_id, None, "failed", "provider_rejected")
            await self._abandon(actor, scope, key)
            raise
        await self.repository.update_refund(
            refund_id, result.refund_ref, result.status.value, _clean_code(result.failure_code)
        )
        if result.failure_code == "onhold":
            await self.repository.record_anomaly(
                kind="refund_onhold",
                provider=payment["provider"],
                provider_ref=refund_id,
                salon_id=str(payment["salon_id"]),
                booking_id=booking_id,
                payment_id=payment_id,
                amount=refund_amount.amount,
                detail="provider holds the refund (insufficient balance)",
            )
        body = await self._booking_payments_body(booking_id, actor.id)
        await self._store_and_commit(actor, scope, key, body, 200)
        return body

    async def _plan_refund(
        self,
        actor: Profile,
        gateway: PaymentGateway,
        payment: dict[str, Any],
        amount: Decimal | None,
        reason: str | None,
        key: str,
    ) -> tuple[str, Money, str | None, Money]:
        """Decide kind (regular / excess), amount and commission reversal; insert the row."""

        paid = Decimal(payment["amount"])
        excess_total = Decimal(payment.get("overcollected_amount") or 0)
        totals = await self.repository.refund_totals(str(payment["id"]))
        regular_left = paid - excess_total - totals["regular"]
        excess_left = excess_total - totals["excess"]
        applies_to_excess = False
        if excess_left > 0:
            # The overcollected part is refunded first: it was never owed, and refunding it
            # must not reduce the booking's paid state.
            if amount is not None and amount > excess_left:
                raise ValidationError(
                    f"Refund the overcollected {excess_left} first, then request a second refund"
                )
            applies_to_excess = True
            refund_amount = Money(amount if amount is not None else excess_left)
        else:
            refund_amount = Money(amount) if amount is not None else Money(regular_left)
            if refund_amount.amount <= 0 or refund_amount.amount > regular_left:
                raise ValidationError("Refund amount exceeds what is left on this payment")
        reversal = Money(0)
        if not applies_to_excess:
            reversal = Money(
                commission_reversal(
                    commission=Decimal(payment.get("platform_commission_amount") or 0),
                    payment_amount=paid - excess_total,
                    refund_amount=refund_amount.amount,
                    already_reversed=totals["reversed"],
                    already_refunded=totals["regular"],
                )
            )
        refund_id = str(uuid.uuid4())
        refund_ref = gateway.deterministic_refund_ref(refund_id)
        await self.repository.insert_refund(
            payment=payment,
            actor_id=actor.id,
            amount=refund_amount.amount,
            reason=reason,
            idempotency_key=key,
            commission_reversal=reversal.amount,
            applies_to_excess=applies_to_excess,
            refund_id=refund_id,
            refund_ref=refund_ref,
        )
        return refund_id, refund_amount, refund_ref, reversal

    # --------------------------------------------------------------- earnings
    async def earnings(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view earnings")
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        currency = self.settings.payment_currency
        zero = Decimal("0.00")
        totals = (
            await self.repository.earnings(salon_id)
            if salon_id
            else {
                "online_collected": zero, "platform_fees": zero, "manual_recorded": zero,
                "online_count": 0, "manual_count": 0, "online_refunded": zero,
                "commission_reversed": zero, "overcollected": zero,
            }
        )
        commission_net = Decimal(totals["platform_fees"]) - Decimal(totals["commission_reversed"])
        net = Decimal(totals["online_collected"]) - Decimal(totals["online_refunded"]) - commission_net
        return {
            "currency": currency,
            "online_collected": totals["online_collected"],
            "online_refunded": totals["online_refunded"],
            "platform_fees": totals["platform_fees"],
            "commission_reversed": totals["commission_reversed"],
            "platform_commission_net": commission_net,
            "overcollected": totals["overcollected"],
            "online_net": net,
            "manual_recorded": totals["manual_recorded"],
            "online_payment_count": totals["online_count"],
            "manual_payment_count": totals["manual_count"],
            "note": (
                "Derived from the payment ledger using each payment's commission snapshot. "
                "Provider fees and taxes are not included. Payout timing is decided by the provider."
            ),
        }

    # ------------------------------------------------------ settlement account
    @staticmethod
    def _masked(ref: str | None) -> str | None:
        return None if not ref else "..." + ref[-4:]

    async def get_settlement_account(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view the settlement account")
        enabled = self.resolver.enabled
        gateway = self.resolver.resolve() if enabled else None
        supported = bool(gateway and gateway.supports(GatewayCapability.linked_accounts))
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        account = (
            await self.repository.get_provider_account(salon_id, self.resolver.provider)
            if salon_id and enabled
            else None
        )
        return {
            "provider_enabled": enabled,
            "supported": supported,
            "requires_details": bool(gateway and gateway.supports(GatewayCapability.vendor_kyc)),
            "onboarding_status": account["onboarding_status"] if account else "not_started",
            "requirements": list(account["requirements"]) if account else [],
            "account_reference_masked": self._masked(
                account["provider_account_ref"] if account else None
            ),
        }

    async def register_settlement_account(
        self,
        actor: Profile,
        key: str | None,
        details: SettlementRegistrationDetails | None = None,
    ) -> dict[str, Any]:
        gateway = self._require_gateway(GatewayCapability.linked_accounts)
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can register a settlement account")
        await assert_approved_workspace(self.workspace, actor)
        key = self._require_key(key)
        scope = "settlement-register"
        # Deliberately NOT a hash of the submitted details: low-entropy bank data must not be
        # recoverable from the idempotency table.
        replay = await self._idempotent(actor, scope, key, _fingerprint(kind="register"))
        if replay is not None:
            return replay
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        if salon_id is None:
            raise NotFoundError("Salon not found")
        needs_details = gateway.supports(GatewayCapability.vendor_kyc)
        if needs_details and details is None:
            raise ValidationError("Contact, PAN and bank or UPI details are required to register")
        holder = details.legal_name if details else await self.repository.get_payout_holder_name(salon_id)
        if not holder:
            raise ValidationError("Save your payout details before registering for online payments")

        salon_hex = salon_id.replace("-", "")
        pending = await self.repository.begin_registration(
            salon_id, gateway.provider_name, actor.id, lambda gen: f"sv{salon_hex}g{gen}"
        )
        # Vendor identity + 'pending' status are durable BEFORE the provider is called.
        await self._checkpoint(actor)
        request = SettlementAccountRequest(
            salon_id=salon_id,
            legal_name=holder,
            vendor_ref=pending["vendor_ref"],
            email=details.contact_email if details else None,
            phone=details.contact_phone if details else None,
            account_type=details.account_type if details else None,
            business_type=details.business_type if details else None,
            pan=details.pan if details else None,
            bank_account_number=details.bank_account_number if details else None,
            ifsc=details.ifsc if details else None,
            upi_id=details.upi_id if details else None,
        )
        try:
            account = await gateway.register_settlement_account(request)
        except PaymentOutcomeUnknownError:
            # Stays 'pending' under the same vendor id; a retry is idempotent at the provider.
            await self._abandon(actor, scope, key)
            raise
        except (PaymentProviderError, PaymentCapabilityError):
            await self.repository.set_account_result(
                salon_id, gateway.provider_name, "needs_action",
                ["The payment provider rejected the registration. Check the details and submit again."],
                actor.id,
            )
            await self.repository.add_account_audit(
                salon_id=salon_id, provider=gateway.provider_name, action="register_failed",
                previous_status="pending", new_status="needs_action",
                vendor_ref=pending["vendor_ref"], actor_id=actor.id,
            )
            await self._abandon(actor, scope, key)
            raise
        await self.repository.set_account_result(
            salon_id, gateway.provider_name, account.onboarding_status.value,
            list(account.requirements), actor.id, account.account_ref,
        )
        body = {
            "provider_enabled": True,
            "supported": True,
            "requires_details": needs_details,
            "onboarding_status": account.onboarding_status.value,
            "requirements": list(account.requirements),
            "account_reference_masked": self._masked(account.account_ref),
        }
        await self._store_and_commit(actor, scope, key, body, 200)
        return body


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class PaymentWebhookUseCases:
    """Webhook intake, event application and stale-intent reconciliation."""

    def __init__(
        self,
        repository: PaymentRepository,
        resolver: PaymentGatewayResolver,
        settings: Settings,
        subscription_handler: SubscriptionWebhookHandler | None = None,
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings
        self.subscription_handler = subscription_handler

    async def ingest(
        self, provider: str, raw_body: bytes, headers: dict[str, str]
    ) -> tuple[str, str | None]:
        """Verify, store (replay gate) and commit. Returns (ack_status, event_row_id).

        Only providers that are independently enabled are accepted, and each is verified with
        its own secret/algorithm over the raw bytes BEFORE any parsing. A bad signature raises
        and writes nothing. Unknown or subscription-domain events are stored ``ignored`` and
        acked 200. Dedupe is scoped by (provider, event reference).
        """

        candidates = self.resolver.webhook_gateways(provider)  # NotFoundError if not enabled
        if len(raw_body) > self.settings.payment_webhook_max_body_bytes:
            raise WebhookPayloadTooLargeError("Webhook payload too large")
        matched = next(
            ((gw, domain) for gw, domain in candidates if gw.verify_webhook_signature(raw_body, headers)),
            None,
        )
        if matched is None:
            raise InvalidWebhookSignatureError("Invalid webhook signature")
        gateway, domain = matched
        try:
            event = gateway.parse_event(raw_body, headers)
        except ValueError:
            return "ignored", None
        if domain is WebhookDomain.subscription:
            # Authorised by the SUBSCRIPTION secret and parsed by the subscription port: it
            # shares only this intake/dedupe table with booking money, never code or secrets.
            return await self._store_subscription_event(gateway, event, raw_body)
        status = "ignored" if event.event_type is PaymentEventType.ignored else "received"
        row_id = await self.repository.insert_webhook_event(
            provider=gateway.provider_name,
            event_id=event.event_id,
            event_type=event.event_type.value,
            payload_hash=hashlib.sha256(raw_body).hexdigest(),
            normalized=event_to_json(event),
            status=status,
        )
        await self.repository.commit()
        if row_id is None:
            return "duplicate", None
        return ("ignored", None) if status == "ignored" else ("accepted", row_id)

    async def _store_subscription_event(
        self, provider: Any, event: Any, raw_body: bytes
    ) -> tuple[str, str | None]:
        status = "ignored" if event.kind is SubscriptionEventKind.ignored else "received"
        row_id = await self.repository.insert_webhook_event(
            provider=provider.provider_name,
            event_id=event.event_id,
            event_type="subscription",
            payload_hash=hashlib.sha256(raw_body).hexdigest(),
            normalized=subscription_event_to_json(event),
            status=status,
        )
        await self.repository.commit()
        if row_id is None:
            return "duplicate", None
        return ("ignored", None) if status == "ignored" else ("accepted", row_id)

    async def process(self, event_id: str) -> str:
        """Claim and apply one stored event. Returns the final processing status."""

        claimed = await self.repository.claim_webhook_event(
            event_id,
            self.settings.payment_reconcile_after_seconds,
            self.settings.payment_webhook_max_attempts,
        )
        await self.repository.commit()
        if claimed is None:
            return "skipped"
        data = claimed["normalized"]
        provider = claimed["provider_name"]
        try:
            outcome = await self._apply(provider, data, event_id)
        except Exception as exc:
            await self.repository.rollback()
            _log.warning("Payment webhook %s failed: %s", event_id, type(exc).__name__)
            await self.repository.finish_webhook_event(
                event_id, "failed", type(exc).__name__[:120], retry=True
            )
            await self.repository.commit()
            return "failed"
        if outcome in {"mismatch", "overcollection"}:
            # Deliberately loud: the money did not match, a human must look. Not retried.
            _log.error("Payment webhook %s needs attention: %s", event_id, outcome)
            await self.repository.finish_webhook_event(event_id, "failed", outcome)
            await self.repository.commit()
            return "failed"
        if outcome == "overcollected":
            _log.error(
                "OVERCOLLECTION recorded from webhook %s: capture exceeded what the booking "
                "was owed (see payment_anomalies); refund the excess",
                event_id,
            )
        final = "processed" if outcome in {"applied", "overcollected"} else "ignored"
        await self.repository.finish_webhook_event(event_id, final)
        await self.repository.commit()
        return final

    async def _apply(self, provider: str, data: dict[str, Any], event_id: str = "") -> str:
        if data.get("domain") == "subscription":
            return await self._apply_subscription(provider, data, event_id)
        event_type = PaymentEventType(data["event_type"])
        if event_type in _EVENT_STATUS:
            return await self.repository.apply_payment_observation(
                provider=provider,
                order_ref=data.get("order_ref"),
                payment_ref=data.get("payment_ref"),
                status=_EVENT_STATUS[event_type],
                amount=Decimal(data["amount"]) if data.get("amount") else None,
                currency=data.get("currency"),
                instrument=data.get("instrument"),
                failure_code=data.get("failure_code"),
            )
        if event_type in {PaymentEventType.refund_processed, PaymentEventType.refund_failed}:
            if not data.get("refund_ref"):
                return "ignored"
            return await self.repository.apply_refund_observation(
                provider,
                data["refund_ref"],
                "processed" if event_type == PaymentEventType.refund_processed else "failed",
                data.get("failure_code"),
            )
        if event_type == PaymentEventType.account_updated and data.get("account_ref"):
            return await self.repository.apply_account_update(
                provider, data["account_ref"], data.get("onboarding_status")
            )
        if event_type == PaymentEventType.settlement_updated:
            status = data.get("settlement_status")
            if status in {"failed", "reversed"}:
                salon_id = (
                    await self.repository.find_salon_by_account(provider, data["account_ref"])
                    if data.get("account_ref")
                    else None
                )
                await self.repository.record_anomaly(
                    kind=f"settlement_{status}",
                    provider=provider,
                    provider_ref=event_id or data.get("account_ref"),
                    salon_id=salon_id,
                    amount=Decimal(data["amount"]) if data.get("amount") else None,
                    detail=f"vendor settlement {status}",
                )
                _log.error("Vendor settlement %s reported by %s", status, provider)
                return "applied"
            return "ignored"
        return "ignored"  # includes the 'subscription' domain: recorded elsewhere, never applied

    async def _apply_subscription(self, provider: str, data: dict[str, Any], event_id: str) -> str:
        """Subscription-domain events go to the billing handler on the SAME session."""

        handler = self.subscription_handler
        if handler is None:
            handler = SubscriptionWebhookHandler(
                SubscriptionBillingRepository(self.repository.session),
                get_subscription_resolver(),
                self.settings,
            )
        return await handler.apply(provider, data, event_id)

    async def reconcile_stale_intents(self, limit: int = 20) -> int:
        """Ask each row's OWN provider about intents whose webhook never arrived."""

        if not self.resolver.enabled:
            return 0
        rows = await self.repository.list_stale_intents(
            self.settings.payment_reconcile_after_seconds, limit
        )
        for row in rows:
            try:
                gateway = self.resolver.for_provider(row["provider"])
            except PaymentProviderNotConfiguredError:
                _log.error(
                    "Cannot reconcile payment %s: provider %r is not enabled", row["id"], row["provider"]
                )
                continue
            try:
                observed = await gateway.fetch_payment(order_ref=row["order_ref"])
                if observed is None:
                    if row["is_expired"]:
                        await self.repository.expire_intent(str(row["id"]))
                    else:
                        await self.repository.touch_intent(str(row["id"]))
                else:
                    outcome = await apply_provider_payment(
                        self.repository, row["provider"], row["order_ref"], observed
                    )
                    if outcome == "overcollected":
                        _log.error("OVERCOLLECTION recorded during reconcile of %s", row["id"])
                    await self.repository.touch_intent(str(row["id"]))
                await self.repository.commit()
            except Exception:
                await self.repository.rollback()
                _log.exception("Payment reconciliation failed for %s", row["id"])
        return len(rows)

    async def reconcile_open_refunds(self, limit: int = 20) -> int:
        """Resolve refunds whose provider outcome is unknown, by OUR deterministic refund id."""

        if not self.resolver.enabled:
            return 0
        rows = await self.repository.list_open_refunds(
            self.settings.payment_reconcile_after_seconds, limit
        )
        for row in rows:
            try:
                gateway = self.resolver.for_provider(row["provider"])
                result = await gateway.fetch_refund(
                    refund_ref=row["refund_ref"],
                    order_ref=row.get("order_ref"),
                    payment_ref=row.get("payment_ref"),
                )
                if result is not None and result.status.value != "created":
                    await self.repository.update_refund(
                        str(row["id"]), result.refund_ref, result.status.value,
                        _clean_code(result.failure_code),
                    )
                else:
                    await self.repository.touch_refund(str(row["id"]))
                await self.repository.commit()
            except PaymentCapabilityError:
                await self.repository.rollback()
            except Exception:
                await self.repository.rollback()
                _log.exception("Refund reconciliation failed for %s", row["id"])
        return len(rows)
