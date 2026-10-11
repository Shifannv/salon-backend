"""Booking payment use cases: intents, confirmation, refunds, earnings, webhooks.

Authorization lives here. Amounts are read from the booking (computed in SQL by
``create_booking``); nothing in this module accepts an amount from a client except an
optional *partial refund* amount, which the database bounds by the captured payment.
"""

import hashlib
import json
import logging
import uuid
from decimal import Decimal
from typing import Any

from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentEvent,
    PaymentGateway,
    PaymentIntentRequest,
    RefundRequest,
    SettlementAccountRequest,
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
    PaymentOvercollectionError,
    PaymentProviderNotConfiguredError,
    ValidationError,
    WebhookPayloadTooLargeError,
)
from app.domain.entities.payment import (
    GatewayCapability,
    LedgerStatus,
    PaymentEventType,
    derive_payment_state,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_owner
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.payments.resolver import PaymentGatewayResolver

_log = logging.getLogger(__name__)

_EVENT_STATUS = {
    PaymentEventType.payment_authorized: "authorized",
    PaymentEventType.payment_captured: "captured",
    PaymentEventType.payment_failed: "failed",
}


def _fingerprint(**fields: Any) -> str:
    return hashlib.sha256(json.dumps(fields, sort_keys=True, default=str).encode()).hexdigest()


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
        "failure_code": row.get("failure_code"),
        "expires_at": row.get("expires_at"),
        "captured_at": row.get("captured_at"),
        "created_at": row["created_at"],
    }


def event_to_json(event: PaymentEvent) -> dict[str, Any]:
    """Serialise a normalised event for the intake table (identifiers and amounts only)."""

    return {
        "event_type": event.event_type.value,
        "raw_type": event.raw_type,
        "payment_ref": event.payment_ref,
        "order_ref": event.order_ref,
        "refund_ref": event.refund_ref,
        "amount": str(event.amount.amount) if event.amount else None,
        "currency": event.currency,
        "instrument": event.instrument.value if event.instrument else None,
        "failure_code": event.failure_code,
        "account_ref": event.account_ref,
        "onboarding_status": event.onboarding_status.value if event.onboarding_status else None,
    }


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
        client = self.resolver.resolve().client_config()
        return {
            "enabled": client.enabled,
            "provider": client.provider,
            "public_key": client.public_key,
            "settlement_model": client.settlement_model.value if client.settlement_model else None,
            **base,
        }

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
        if await self.repository.get_open_intent(booking_id) is not None:
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

        fee = Money(
            amount.amount * self.settings.payment_platform_fee_percent / Decimal(100)
        )
        intent_reference = "pi_" + uuid.uuid4().hex
        payment_id = await self.repository.insert_intent(
            booking=booking,
            actor_id=actor.id,
            purpose=purpose,
            amount=amount.amount,
            platform_fee=fee.amount,
            provider=gateway.provider_name,
            settlement_model=self.resolver.settlement_model.value,
            intent_reference=intent_reference,
            expires_in_seconds=self.settings.payment_intent_ttl_seconds,
        )
        intent = await gateway.create_payment_intent(
            PaymentIntentRequest(
                intent_reference=intent_reference,
                booking_id=str(booking["id"]),
                salon_id=str(booking["salon_id"]),
                amount=amount,
                currency=booking["currency"],
                customer_id=actor.id,
                settlement_model=self.resolver.settlement_model,
                settlement_account_ref=account_ref,
                platform_fee=fee,
            )
        )
        await self.repository.set_intent_order(payment_id, intent.order_ref)
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

    # ---------------------------------------------------------------- confirm
    async def confirm(
        self,
        actor: Profile,
        booking_id: str,
        order_ref: str,
        payment_ref: str,
        signature: str,
        key: str | None,
    ) -> dict[str, Any]:
        gateway = self._require_gateway(GatewayCapability.online_collection)
        key = self._require_key(key)
        scope = f"confirm:{booking_id}"
        replay = await self._idempotent(
            actor, scope, key, _fingerprint(o=order_ref, p=payment_ref, s=signature)
        )
        if replay is not None:
            return replay
        booking = await self.repository.lock_booking(booking_id, actor.id)
        if booking is None or not self._is_customer_of(booking, actor):
            raise NotFoundError("Booking not found")
        row = await self.repository.get_payment_by_order(booking_id, order_ref)
        if row is None:
            raise NotFoundError("Payment not found")
        if not gateway.verify_payment_callback(
            PaymentCallback(order_ref=order_ref, payment_ref=payment_ref, signature=signature)
        ):
            raise ValidationError("Payment could not be verified")
        # The signature proves the payment belongs to the order; the amount is still
        # checked against what the provider actually holds.
        observed = await gateway.fetch_payment(payment_ref=payment_ref)
        if observed is not None and observed.order_ref not in (None, order_ref):
            raise ValidationError("Payment could not be verified")
        outcome = "ignored"
        if observed is not None:
            status = (
                LedgerStatus.captured
                if observed.status
                in {
                    LedgerStatus.captured,
                    LedgerStatus.partially_refunded,
                    LedgerStatus.refunded,
                }
                else observed.status
            )
            outcome = await self.repository.apply_payment_observation(
                provider=gateway.provider_name,
                order_ref=order_ref,
                payment_ref=payment_ref,
                status=status.value,
                amount=observed.amount.amount,
                currency=observed.currency,
                instrument=observed.instrument.value if observed.instrument else None,
                failure_code=observed.failure_code,
            )
        if outcome in {"mismatch", "overcollection"}:
            await self.repository.commit()  # keep the failed row; never mark paid
            if outcome == "mismatch":
                raise PaymentAmountMismatchError("The paid amount does not match the booking")
            raise PaymentOvercollectionError("This booking has already been paid in full")
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
        gateway = self._require_gateway(GatewayCapability.refunds)
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
        committed = await self.repository.refunded_or_pending(payment_id)
        remaining = Money(Decimal(payment["amount"]) - committed)
        refund_amount = Money(amount) if amount is not None else remaining
        if refund_amount.amount <= 0 or refund_amount.amount > remaining.amount:
            raise ValidationError("Refund amount exceeds what is left on this payment")
        # Deterministic provider key: a retry can never refund twice.
        provider_key = hashlib.sha256(f"{payment_id}:{key}".encode()).hexdigest()[:40]
        refund_id = await self.repository.insert_refund(
            payment=payment,
            actor_id=actor.id,
            amount=refund_amount.amount,
            reason=reason,
            idempotency_key=key,
        )
        result = await gateway.refund(
            RefundRequest(
                payment_ref=payment["payment_ref"],
                amount=refund_amount,
                idempotency_key=provider_key,
                reason=reason,
            )
        )
        await self.repository.update_refund(
            refund_id, result.refund_ref, result.status.value, result.failure_code
        )
        body = await self._booking_payments_body(booking_id, actor.id)
        await self._store_and_commit(actor, scope, key, body, 200)
        return body

    # --------------------------------------------------------------- earnings
    async def earnings(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view earnings")
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        currency = self.settings.payment_currency
        totals = (
            await self.repository.earnings(salon_id)
            if salon_id
            else {
                "online_collected": Decimal(0), "platform_fees": Decimal(0),
                "manual_recorded": Decimal(0), "online_count": 0, "manual_count": 0,
                "online_refunded": Decimal(0),
            }
        )
        net = (
            Decimal(totals["online_collected"])
            - Decimal(totals["online_refunded"])
            - Decimal(totals["platform_fees"])
        )
        return {
            "currency": currency,
            "online_collected": totals["online_collected"],
            "online_refunded": totals["online_refunded"],
            "platform_fees": totals["platform_fees"],
            "online_net": net,
            "manual_recorded": totals["manual_recorded"],
            "online_payment_count": totals["online_count"],
            "manual_payment_count": totals["manual_count"],
            "note": (
                "Derived from the payment ledger. Payout timing and any commission are "
                "decided by the provider and are not computed here."
            ),
        }

    # ------------------------------------------------------ settlement account
    async def get_settlement_account(self, actor: Profile) -> dict[str, Any]:
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can view the settlement account")
        enabled = self.resolver.enabled
        supported = enabled and self.resolver.resolve().supports(
            GatewayCapability.linked_accounts
        )
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        account = (
            await self.repository.get_provider_account(salon_id, self.resolver.provider)
            if salon_id and enabled
            else None
        )
        return {
            "provider_enabled": enabled,
            "supported": bool(supported),
            "onboarding_status": account["onboarding_status"] if account else "not_started",
            "requirements": list(account["requirements"]) if account else [],
        }

    async def register_settlement_account(
        self, actor: Profile, key: str | None
    ) -> dict[str, Any]:
        gateway = self._require_gateway(GatewayCapability.linked_accounts)
        if not is_owner(actor):
            raise ForbiddenError("Only the salon owner can register a settlement account")
        await assert_approved_workspace(self.workspace, actor)
        key = self._require_key(key)
        scope = "settlement-register"
        replay = await self._idempotent(actor, scope, key, _fingerprint())
        if replay is not None:
            return replay
        salon_id = await self.repository.find_owner_salon_id(actor.id)
        if salon_id is None:
            raise NotFoundError("Salon not found")
        holder = await self.repository.get_payout_holder_name(salon_id)
        if not holder:
            raise ValidationError("Save your payout details before registering for online payments")
        account = await gateway.register_settlement_account(
            SettlementAccountRequest(
                salon_id=salon_id, legal_name=holder, email=None, phone=None
            )
        )
        await self.repository.upsert_provider_account(
            salon_id,
            gateway.provider_name,
            account.account_ref,
            account.onboarding_status.value,
            list(account.requirements),
            actor.id,
        )
        body = {
            "provider_enabled": True,
            "supported": True,
            "onboarding_status": account.onboarding_status.value,
            "requirements": list(account.requirements),
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
        self, repository: PaymentRepository, resolver: PaymentGatewayResolver, settings: Settings
    ) -> None:
        self.repository = repository
        self.resolver = resolver
        self.settings = settings

    async def ingest(
        self, provider: str, raw_body: bytes, headers: dict[str, str]
    ) -> tuple[str, str | None]:
        """Verify, store (replay gate) and commit. Returns (ack_status, event_row_id).

        The signature is checked over the raw bytes BEFORE any parsing; a bad signature
        raises and writes nothing. Unknown events are stored as ``ignored`` and acked 200.
        """

        if not self.resolver.enabled or provider != self.resolver.provider:
            raise NotFoundError("Not found")
        if len(raw_body) > self.settings.payment_webhook_max_body_bytes:
            raise WebhookPayloadTooLargeError("Webhook payload too large")
        gateway = self.resolver.resolve()
        if not gateway.verify_webhook_signature(raw_body, headers):
            raise InvalidWebhookSignatureError("Invalid webhook signature")
        try:
            event = gateway.parse_event(raw_body, headers)
        except ValueError:
            return "ignored", None
        status = "ignored" if event.event_type == PaymentEventType.ignored else "received"
        row_id = await self.repository.insert_webhook_event(
            provider=provider,
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
            outcome = await self._apply(provider, data)
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
        final = "processed" if outcome == "applied" else "ignored"
        await self.repository.finish_webhook_event(event_id, final)
        await self.repository.commit()
        return final

    async def _apply(self, provider: str, data: dict[str, Any]) -> str:
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
        return "ignored"

    async def reconcile_stale_intents(self, limit: int = 20) -> int:
        """Ask the provider about intents whose webhook never arrived (the lost-webhook defence)."""

        if not self.resolver.enabled:
            return 0
        gateway = self.resolver.resolve()
        rows = await self.repository.list_stale_intents(
            self.settings.payment_reconcile_after_seconds, limit
        )
        for row in rows:
            try:
                observed = await gateway.fetch_payment(order_ref=row["order_ref"])
                if observed is None:
                    if row["is_expired"]:
                        await self.repository.expire_intent(str(row["id"]))
                    else:
                        await self.repository.touch_intent(str(row["id"]))
                else:
                    status = (
                        LedgerStatus.captured
                        if observed.status
                        in {
                            LedgerStatus.captured,
                            LedgerStatus.partially_refunded,
                            LedgerStatus.refunded,
                        }
                        else observed.status
                    )
                    await self.repository.apply_payment_observation(
                        provider=row["provider"],
                        order_ref=row["order_ref"],
                        payment_ref=observed.payment_ref,
                        status=status.value,
                        amount=observed.amount.amount,
                        currency=observed.currency,
                        instrument=observed.instrument.value if observed.instrument else None,
                        failure_code=observed.failure_code,
                    )
                    await self.repository.touch_intent(str(row["id"]))
                await self.repository.commit()
            except Exception:
                await self.repository.rollback()
                _log.exception("Payment reconciliation failed for %s", row["id"])
        return len(rows)
