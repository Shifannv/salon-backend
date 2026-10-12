"""Payment webhook retry worker (its own Compose service).

Same claim-process-backoff shape as ``push/outbox_worker.py``: each event is claimed by an
atomic UPDATE (so concurrent workers never double-process), failures back off
exponentially, and an event that exhausts ``PAYMENT_WEBHOOK_MAX_ATTEMPTS`` stays ``failed``
for an operator. A second pass reconciles stale open intents against the provider, the only
defence against a webhook that never arrived.
"""

import asyncio
import logging

from app.application.use_cases.payments import PaymentWebhookUseCases
from app.application.use_cases.subscription_billing import SubscriptionReconciler
from app.core.config import settings
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.db.repositories.subscription_billing_repository import (
    SubscriptionBillingRepository,
)
from app.infrastructure.db.session import AsyncSessionLocal
from app.infrastructure.payments.resolver import get_payment_resolver
from app.infrastructure.subscriptions.resolver import get_subscription_resolver

_log = logging.getLogger(__name__)


async def drain_webhook_events(limit: int = 50) -> int:
    """Attempt each due event once; returns how many were attempted."""

    resolver = get_payment_resolver()
    async with AsyncSessionLocal() as session:
        ids = await PaymentRepository(session).list_due_webhook_event_ids(
            settings.payment_reconcile_after_seconds,
            settings.payment_webhook_max_attempts,
            limit,
        )
    for event_id in ids:
        async with AsyncSessionLocal() as session:
            await PaymentWebhookUseCases(PaymentRepository(session), resolver, settings).process(
                event_id
            )
    return len(ids)


async def reconcile_once(limit: int = 20) -> int:
    """Reconcile stale open intents with the provider and prune expired idempotency keys."""

    async with AsyncSessionLocal() as session:
        repository = PaymentRepository(session)
        use_cases = PaymentWebhookUseCases(repository, get_payment_resolver(), settings)
        count = await use_cases.reconcile_stale_intents(limit)
        count += await use_cases.reconcile_open_refunds(limit)
        await repository.purge_expired_idempotency()
        await repository.commit()
    return count


async def reconcile_subscriptions_once(limit: int = 20) -> dict[str, int]:
    """Subscription pass: settle stale orders, expire unpaid ones, sweep lapsed periods.

    Independent of HTTP and of the booking provider. Errors are logged with the stable
    ``ALERT subscription_billing`` prefix so one log filter can alert on them.
    """

    async with AsyncSessionLocal() as session:
        reconciler = SubscriptionReconciler(
            SubscriptionBillingRepository(session), get_subscription_resolver(), settings
        )
        return await reconciler.run(limit)


async def run_forever() -> None:
    while True:
        # Booking and subscription passes fail independently of each other.
        try:
            await drain_webhook_events()
            if get_payment_resolver().enabled:
                await reconcile_once()
        except Exception:
            _log.exception("Payment worker poll failed")
        try:
            await reconcile_subscriptions_once()
        except Exception:
            _log.exception("ALERT subscription_billing: reconciliation pass failed")
        await asyncio.sleep(settings.payment_worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())
