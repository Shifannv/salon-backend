"""Webhook intake, event application and reconciliation."""

import hashlib
from decimal import Decimal
from typing import Any

from app.application.ports.subscription_provider import SubscriptionEventKind
from app.application.use_cases.payments.ledger import (
    _EVENT_STATUS,
    _clean_code,
    _log,
    apply_provider_payment,
    event_to_json,
)
from app.application.use_cases.subscription_billing import (
    SubscriptionWebhookHandler,
    subscription_event_to_json,
)
from app.core.config import Settings
from app.core.exceptions import (
    InvalidWebhookSignatureError,
    PaymentCapabilityError,
    PaymentProviderNotConfiguredError,
    WebhookPayloadTooLargeError,
)
from app.domain.entities.payment import (
    PaymentEventType,
    WebhookDomain,
)
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.payments.resolver import PaymentGatewayResolver
from app.infrastructure.subscriptions.resolver import get_subscription_resolver


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
