"""Customer and owner payment operations."""

import json
import uuid
from decimal import Decimal
from typing import Any, cast

from app.application.ports.payment_gateway import (
    PaymentCallback,
    PaymentGateway,
    PaymentIntent,
    PaymentIntentRequest,
)
from app.application.use_cases.idempotency import (
    release_reservation,
    require_idempotency_key,
)
from app.application.use_cases.payments.ledger import (
    _fingerprint,
    _json_default,
    _ledger_row,
    _log,
    apply_provider_payment,
)
from app.application.use_cases.payments.refunds import RefundMixin
from app.application.use_cases.payments.settlement_accounts import SettlementAccountMixin
from app.application.use_cases.workspace import assert_approved_workspace
from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PaymentAmountMismatchError,
    PaymentCapabilityError,
    PaymentInProgressError,
    PaymentOutcomeUnknownError,
    PaymentOvercollectionError,
    PaymentProviderError,
    PaymentProviderNotConfiguredError,
    ValidationError,
)
from app.domain.entities.payment import (
    GatewayCapability,
    derive_payment_state,
)
from app.domain.entities.profile import Profile
from app.domain.services.booking_finance_policy import POLICY_VERSION
from app.domain.services.checkout import online_checkout_available
from app.domain.services.commission import compute_commission
from app.domain.value_objects.money import Money
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.payments.resolver import PaymentGatewayResolver


class _NoRepository:
    """Stand-in repository for config-only instances; any attribute access is a bug."""


class BookingPaymentUseCases(RefundMixin, SettlementAccountMixin):
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

    @classmethod
    def config_only(
        cls, resolver: PaymentGatewayResolver, settings: Settings
    ) -> "BookingPaymentUseCases":
        """Instance for ``config()`` alone, which never touches the database."""

        return cls(cast(PaymentRepository, _NoRepository()), resolver, settings)

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
        return require_idempotency_key(key, max_len=200)

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

        await release_reservation(self.repository, actor.id, scope, key)

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
        if not online_checkout_available(self.resolver.enabled, self.settings.booking_checkout_policy_version):
            return {"enabled": False, "online_payment_available": False,
                    "online_payment_unavailable_reason": "Online payment coming soon.", **base}
        gateway = self.resolver.resolve()
        client = gateway.client_config()
        return {
            "enabled": client.enabled,
            "online_payment_available": client.enabled,
            "online_payment_unavailable_reason": None if client.enabled else "Online payment coming soon.",
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
        if booking.get("checkout_policy_version") == POLICY_VERSION:
            # Do not send this policy through the legacy automatic split/order path.
            # Credentials alone cannot prove deferred settlement or approve a payout.
            raise PaymentProviderNotConfiguredError("Online payment coming soon.")
        if booking["status"] not in {"pending", "confirmed"}:
            raise ConflictError("Only pending or confirmed bookings can be paid online")
        if not booking.get("accepts_new_online_payment", True):
            raise ConflictError("This salon is not accepting online payments right now.")

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

        from app.domain.services.checkout import checkout_quote
        processing = Decimal("0")
        if booking.get("checkout_policy_version") == "customer_processing_v1":
            quoted = checkout_quote(amount.amount, "PAY_ONLINE")
            processing = quoted["online_processing_charge"]
            if purpose == "balance":
                full_charge = checkout_quote(total.amount,"PAY_ONLINE")["online_processing_charge"]
                allocated_charge = await self.repository.processing_charge_allocated(booking_id)
                processing = max(Decimal("0"),full_charge - allocated_charge)
            amount = Money(amount.amount + processing)
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
                **({"online_processing_charge": processing} if processing else {}),
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
        session_id = intent.client_payload.get("payment_session_id")
        kwargs = {"provider_session_id": session_id} if isinstance(session_id, str) else {}
        await self.repository.confirm_intent_order(payment_id, intent.order_ref, **kwargs)
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
