"""Owner wallet routes and the admin payout queue.

Owner: what the platform holds for the salon, the history, and asking for (or taking back) a payout.
Admin: every request, declined with a reason here, or paid with proof in ``payout_proof``.
Money is integer paise. A payout request needs an ``Idempotency-Key``.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_session, get_current_actor, require_role
from app.api.v1.routes.payout_proof import payout_notices
from app.api.v1.schemas.wallet import (
    AdminPayoutAccountFull,
    AdminPayoutRequestsResponse,
    PayoutRejectRequest,
    PayoutRequestCreate,
    PayoutStatus,
    WalletEntriesResponse,
    WalletEntryResponse,
    WalletResponse,
)
from app.application.use_cases.wallet import WalletAdminUseCases, WalletUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.feature_access_repository import FeatureAccessRepository
from app.infrastructure.db.repositories.payout_proof_repository import PayoutProofRepository
from app.infrastructure.db.repositories.wallet_repository import WalletRepository

router = APIRouter()
admin_router = APIRouter()


def _owner_use_cases(session: AsyncSession) -> WalletUseCases:
    return WalletUseCases(
        WalletRepository(session),
        online_payments_live=settings.payment_provider != "none",
        features=FeatureAccessRepository(session),
    )


def _admin_use_cases(session: AsyncSession) -> WalletAdminUseCases:
    repository = PayoutProofRepository(session)
    return WalletAdminUseCases(repository, audit=repository.audit, notices=payout_notices(repository))


@router.get(
    "/salons/me/wallet",
    response_model=WalletResponse,
    status_code=status.HTTP_200_OK,
    summary="What can be paid out to the salon now",
    description="Zero while online payments are off. `available_paise` is the server's figure.",
)
async def wallet(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletResponse:
    return WalletResponse(**await _owner_use_cases(session).summary(actor))


@router.get(
    "/salons/me/wallet/entries",
    response_model=WalletEntriesResponse,
    status_code=status.HTTP_200_OK,
    summary="Money in and out of the wallet, newest first",
)
async def wallet_entries(
    cursor: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=30, ge=1, le=100),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletEntriesResponse:
    return WalletEntriesResponse(**await _owner_use_cases(session).entries(actor, cursor, limit))


@router.post(
    "/salons/me/wallet/payout-requests",
    response_model=WalletEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ask for a payout on a day",
    description=(
        "Requires `Idempotency-Key`. The platform credits the saved bank or UPI account within "
        "24 hours of `scheduled_for`. The amount must fit the available balance."
    ),
)
async def request_payout(
    payload: PayoutRequestCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletEntryResponse:
    body = await _owner_use_cases(session).request_payout(
        actor, amount_paise=payload.amount_paise, scheduled_for=payload.scheduled_for,
        idempotency_key=idempotency_key,
    )
    return WalletEntryResponse(**body)


@router.post(
    "/salons/me/wallet/payout-requests/{request_id}/cancel",
    response_model=WalletEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Take back a payout request that has not been paid yet",
    description="Cancelling twice is safe. A request already paid or declined cannot be cancelled.",
)
async def cancel_payout(
    request_id: UUID,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletEntryResponse:
    return WalletEntryResponse(**await _owner_use_cases(session).cancel_payout(actor, str(request_id)))


@admin_router.get(
    "/wallet/payout-requests",
    response_model=AdminPayoutRequestsResponse,
    status_code=status.HTTP_200_OK,
    summary="Payout requests from every salon, oldest first",
    description="Account details are masked. Filter by `status` to see only what is waiting.",
)
async def list_payout_requests(
    status_filter: PayoutStatus | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None, max_length=300),
    limit: int = Query(default=30, ge=1, le=100),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AdminPayoutRequestsResponse:
    body = await _admin_use_cases(session).list_requests(
        actor, status=status_filter, cursor=cursor, limit=limit
    )
    return AdminPayoutRequestsResponse(**body)


@admin_router.post(
    "/wallet/payout-requests/{request_id}/reveal-account",
    response_model=AdminPayoutAccountFull,
    status_code=status.HTTP_200_OK,
    summary="The salon's full bank or UPI details, to pay one waiting request",
    description="Only while the request is waiting. Each look is recorded; the response is never cached.",
)
async def reveal_payout_account(
    request_id: UUID,
    response: Response,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> AdminPayoutAccountFull:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return AdminPayoutAccountFull(**await _admin_use_cases(session).reveal_account(actor, str(request_id)))


@admin_router.post(
    "/wallet/payout-requests/{request_id}/reject",
    response_model=WalletEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Decline a payout request; the money goes back to the owner's wallet",
)
async def reject_payout(
    request_id: UUID,
    payload: PayoutRejectRequest,
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
) -> WalletEntryResponse:
    return WalletEntryResponse(
        **await _admin_use_cases(session).reject(actor, str(request_id), payload.reason)
    )
