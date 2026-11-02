"""Admin payout proof routes (mounted under /admin): pay with proof, look one up, correct, reconcile.

The proof file never leaves through a public URL: it is returned only to a super admin, as bytes
that are never cached, and each look is written to the audit trail.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, require_role
from app.api.v1.schemas.payout_proof import (
    PROOF_FORM_DESCRIPTION,
    PaymentMethod,
    PayoutDetailResponse,
    ReconciliationResponse,
)
from app.api.v1.schemas.wallet import WalletEntryResponse
from app.application.use_cases.payout_proof import PayoutNotices, PayoutProofUseCases
from app.core.exceptions import PayoutProofInvalidError
from app.domain.entities.profile import Profile, Role
from app.domain.services.payout_proof import MAX_PROOF_BYTES
from app.infrastructure.db.repositories.payout_proof_repository import PayoutProofRepository
from app.infrastructure.push.outbox_worker import enqueue_and_deliver_notification

admin_router = APIRouter()


async def notify_owner(
    *, user_id: str, notification_type: str, title: str, body: str, data: dict[str, Any] | None = None
) -> None:
    await enqueue_and_deliver_notification(
        user_id=user_id, booking_id=None, notification_type=notification_type, title=title, body=body, data=data
    )


def payout_notices(repository: PayoutProofRepository) -> PayoutNotices:
    return PayoutNotices(notify_owner, repository.owner_id_of_salon)


def _use_cases(session: AsyncSession) -> PayoutProofUseCases:
    repository = PayoutProofRepository(session)
    return PayoutProofUseCases(repository, notices=payout_notices(repository))


async def _read_proof(proof: UploadFile) -> bytes:
    """The uploaded bytes, read one byte past the limit so an oversized file is refused, not stored."""

    data = await proof.read(MAX_PROOF_BYTES + 1)
    if not data:
        raise PayoutProofInvalidError("Attach the payment screenshot or PDF")
    return data


def _file_response(file: dict[str, Any]) -> Response:
    return Response(
        content=file["content"],
        media_type=file["mime_type"],
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@admin_router.post(
    "/wallet/payout-requests/{request_id}/mark-paid",
    response_model=WalletEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Record that a payout was paid, with its reference, details and proof",
    description=(
        "Multipart form. The reference, method, time, amount and a proof file are all required. "
        "If the amount differs from the request, `adjustment_reason` is required. Retrying with the "
        "same reference returns the stored payment. " + PROOF_FORM_DESCRIPTION
    ),
)
async def mark_payout_paid(
    request_id: UUID,
    reference: str = Form(min_length=1, max_length=100),
    method: PaymentMethod = Form(),
    paid_at: datetime = Form(),
    amount_paid_paise: int = Form(gt=0),
    adjustment_reason: str | None = Form(default=None, max_length=500),
    note: str | None = Form(default=None, max_length=200),
    proof: UploadFile = File(description=PROOF_FORM_DESCRIPTION),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletEntryResponse:
    body = await _use_cases(session).pay(
        actor, str(request_id), reference=reference, method=method, paid_at=paid_at,
        amount_paid_paise=amount_paid_paise, adjustment_reason=adjustment_reason, note=note,
        proof=await _read_proof(proof),
    )
    return WalletEntryResponse(**body)


@admin_router.get(
    "/wallet/payout-requests/{request_id}",
    response_model=PayoutDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="One payout: salon, amounts, masked account, timeline, payment, proof and corrections",
)
async def payout_detail(
    request_id: UUID,
    response: Response,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PayoutDetailResponse:
    response.headers["Cache-Control"] = "no-store"
    return PayoutDetailResponse(**await _use_cases(session).detail(actor, str(request_id)))


@admin_router.get(
    "/wallet/payout-requests/{request_id}/proof",
    status_code=status.HTTP_200_OK,
    summary="The payment proof file of a paid payout",
    description="Returns the file itself (image or PDF), never cached. Each look is recorded.",
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}, "application/pdf": {}}}},
)
async def payout_proof(
    request_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    return _file_response(await _use_cases(session).proof(actor, str(request_id)))


@admin_router.post(
    "/wallet/payout-requests/{request_id}/corrections",
    response_model=PayoutDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Correct a paid payout with a linked entry; the paid record is never edited",
    description="Multipart form. `delta_paise` is positive when more was paid, negative when less. "
    + PROOF_FORM_DESCRIPTION,
)
async def correct_payout(
    request_id: UUID,
    delta_paise: int = Form(),
    reason: str = Form(min_length=3, max_length=500),
    reference: str = Form(min_length=1, max_length=100),
    proof: UploadFile = File(description=PROOF_FORM_DESCRIPTION),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> PayoutDetailResponse:
    body = await _use_cases(session).correct(
        actor, str(request_id), delta_paise=delta_paise, reason=reason, reference=reference,
        proof=await _read_proof(proof),
    )
    return PayoutDetailResponse(**body)


@admin_router.get(
    "/wallet/payout-requests/{request_id}/corrections/{correction_id}/proof",
    status_code=status.HTTP_200_OK,
    summary="The proof file of one correction",
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}, "application/pdf": {}}}},
)
async def correction_proof(
    request_id: UUID,
    correction_id: UUID,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> Response:
    return _file_response(await _use_cases(session).correction_proof(actor, str(request_id), str(correction_id)))


@admin_router.get(
    "/wallet/payout-reconciliation",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_200_OK,
    summary="Per day: payouts asked for, actually paid and declined, to match the bank statement",
    description="Days are Indian calendar days. At most 92 days.",
)
async def payout_reconciliation(
    start: date = Query(alias="from"),
    end: date = Query(alias="to"),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ReconciliationResponse:
    return ReconciliationResponse(**await _use_cases(session).reconciliation(actor, start, end))
