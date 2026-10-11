"""Provider webhook intake. Registered only when a payment provider is configured."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_payment_gateway_resolver
from app.api.v1.schemas.payment import WebhookAckResponse
from app.application.use_cases.payments import PaymentWebhookUseCases
from app.core.config import settings
from app.core.exceptions import WebhookPayloadTooLargeError
from app.infrastructure.db.repositories.payment_repository import PaymentRepository
from app.infrastructure.db.session import AsyncSessionLocal, get_session
from app.infrastructure.payments.resolver import PaymentGatewayResolver

router = APIRouter()
_log = logging.getLogger(__name__)


async def process_in_background(event_id: str) -> None:
    """Apply a stored event in its own session; the worker retries anything that fails."""

    try:
        async with AsyncSessionLocal() as session:
            await PaymentWebhookUseCases(
                PaymentRepository(session), get_payment_gateway_resolver(), settings
            ).process(event_id)
    except Exception:
        _log.exception("Background webhook processing failed for %s", event_id)


@router.post(
    "/webhooks/{provider}",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment provider webhook",
    description=(
        "No auth: the provider signature over the raw body is the credential. Bad "
        "signature -> 400 and nothing is stored. Unknown events are acknowledged 200."
    ),
)
async def payment_webhook(
    provider: str,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    resolver: PaymentGatewayResolver = Depends(get_payment_gateway_resolver),
) -> WebhookAckResponse:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.payment_webhook_max_body_bytes:
        raise WebhookPayloadTooLargeError("Webhook payload too large")
    raw_body = await request.body()
    ack, event_id = await PaymentWebhookUseCases(
        PaymentRepository(session), resolver, settings
    ).ingest(provider, raw_body, dict(request.headers))
    if event_id is not None:
        background_tasks.add_task(process_in_background, event_id)
    return WebhookAckResponse(status=ack)
