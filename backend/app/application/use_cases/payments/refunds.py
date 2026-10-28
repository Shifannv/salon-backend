"""Refund planning and execution for ``BookingPaymentUseCases``."""

import hashlib
import uuid
from decimal import Decimal
from typing import Any

from app.application.ports.payment_gateway import (
    PaymentGateway,
    RefundRequest,
)
from app.application.use_cases.payments.ledger import (
    _clean_code,
    _fingerprint,
)
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PaymentCapabilityError,
    PaymentOutcomeUnknownError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
)
from app.domain.entities.payment import (
    GatewayCapability,
)
from app.domain.entities.profile import Profile
from app.domain.services.authorization import is_owner
from app.domain.services.commission import commission_reversal
from app.domain.value_objects.money import Money


class RefundMixin:
    """Refund operations; mixed into ``BookingPaymentUseCases``."""

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
