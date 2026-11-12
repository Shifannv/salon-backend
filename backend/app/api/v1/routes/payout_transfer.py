"""Automatic payout: admin routes (mounted under /admin) and the provider webhook.

The super admin picks per request: ``mark-paid`` (by hand, with proof) or ``send-transfer`` (the
payout provider sends it). Both end in the same ``paid`` state. The webhook is unauthenticated: the
provider signature over the raw body is the credential, and a bad signature stores and changes nothing.
"""

import logging
from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.routes.payout_proof import payout_notices
from app.api.v1.schemas.payment import WebhookAckResponse
from app.api.v1.schemas.payout_proof import PayoutDetailResponse
from app.application.ports.payout_transfer import PayoutTransferGateway
from app.application.use_cases.payout_proof import PayoutProofUseCases
from app.application.use_cases.payout_transfer import PayoutTransferUseCases
from app.core.config import settings
from app.core.exceptions import (
    InvalidWebhookSignatureError,
    NotFoundError,
    PayoutProviderUnavailableError,
    WebhookPayloadTooLargeError,
)
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.payout_proof_repository import PayoutProofRepository
from app.infrastructure.db.session import get_session
from app.infrastructure.payouts.resolver import build_payout_gateway

_log = logging.getLogger(__name__)

admin_router = APIRouter()
webhook_router = APIRouter()


@lru_cache(maxsize=1)
def _configured_gateway() -> PayoutTransferGateway | None:
    return build_payout_gateway(settings)


def get_payout_gateway() -> PayoutTransferGateway | None:
    """A dependency so tests can swap the provider; None when automatic payout is not configured."""

    return _configured_gateway()


def _use_cases(session: AsyncSession, gateway: PayoutTransferGateway | None) -> PayoutTransferUseCases:
    repository = PayoutProofRepository(session)
    key = settings.payout_encryption_key
    return PayoutTransferUseCases(
        repository, gateway, notices=payout_notices(repository),
        beneficiary_secret=key.get_secret_value() if key else "",
    )


async def _detail(session: AsyncSession, actor: Profile, request_id: UUID) -> PayoutDetailResponse:
    repository = PayoutProofRepository(session)
    return PayoutDetailResponse(**await PayoutProofUseCases(repository).detail(actor, str(request_id)))


@admin_router.post(
    "/wallet/payout-requests/{request_id}/send-transfer",
    response_model=PayoutDetailResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a waiting payout to the salon's bank or UPI account through the payout provider",
    description=(
        "Alternative to `mark-paid`. 202: the transfer was started; `transfer.status` is `pending` until "
        "the provider confirms (webhook, or `transfer/refresh`). The request becomes `paid` only on success. "
        "While a transfer is pending or successful it cannot be cancelled, declined or paid by hand. "
        "`payout_provider_unavailable` means automatic payout is not set up: pay by hand."
    ),
)
async def send_transfer(
    request_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    gateway: PayoutTransferGateway | None = Depends(get_payout_gateway),
) -> PayoutDetailResponse:
    await _use_cases(session, gateway).send(actor, str(request_id))
    return await _detail(session, actor, request_id)


@admin_router.post(
    "/wallet/payout-requests/{request_id}/transfer/refresh",
    response_model=PayoutDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the payout provider where the transfer stands",
    description="Safe to repeat. Applies the same result the webhook would (success pays the request).",
)
async def refresh_transfer(
    request_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    gateway: PayoutTransferGateway | None = Depends(get_payout_gateway),
) -> PayoutDetailResponse:
    await _use_cases(session, gateway).refresh(actor, str(request_id))
    return await _detail(session, actor, request_id)


@webhook_router.post(
    "/webhooks/payouts/{provider}",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Payout provider webhook",
    description=(
        "No auth: the signature over the raw body is the credential. A bad signature is a 400 and "
        "changes nothing. Events this app does not act on are acknowledged with 200. `provider` must be "
        "the configured payout provider."
    ),
)
async def payout_webhook(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    gateway: PayoutTransferGateway | None = Depends(get_payout_gateway),
) -> WebhookAckResponse:
    if gateway is None:
        raise PayoutProviderUnavailableError("Automatic payout is not set up")
    if provider != gateway.provider_name:
        raise NotFoundError("Unknown payout provider")
    limit = settings.payment_webhook_max_body_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise WebhookPayloadTooLargeError("Webhook payload too large")
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():  # bounded read: a lying Content-Length cannot buffer without limit
        received += len(chunk)
        if received > limit:
            raise WebhookPayloadTooLargeError("Webhook payload too large")
        chunks.append(chunk)
    raw_body = b"".join(chunks)
    if not gateway.verify_webhook_signature(raw_body, dict(request.headers)):
        raise InvalidWebhookSignatureError("Webhook signature is not valid")
    result = gateway.parse_webhook(raw_body)
    if result is None:
        return WebhookAckResponse(status="ignored")
    # An error here is a 5xx on purpose: the provider retries, and apply() is safe to repeat.
    await _use_cases(session, gateway).apply(result, admin_id=None)
    return WebhookAckResponse(status="accepted")
