"""Account deletion: contact-bound verification, confirmation, status, admin ledger."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_auth_admin_gateway,
    get_auth_gateway,
    get_authenticated_session,
    get_current_actor,
    require_role,
)
from app.api.v1.schemas.account_deletion import (
    AccountDeletionAcceptedResponse,
    AccountDeletionStatusResponse,
    AdminAccountDeletionResponse,
    ConfirmAccountDeletionRequest,
    DeletionChallengeResponse,
    StartDeletionChallengeRequest,
    VerifiedDeletionChallengeResponse,
    VerifyDeletionChallengeRequest,
)
from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.auth_gateway import AuthGateway
from app.application.use_cases.account_deletion import AccountDeletionUseCases
from app.core.config import settings
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.account_deletion_repository import (
    SQLAccountDeletionRepository,
)
from app.infrastructure.db.session import get_session

router = APIRouter()
admin_router = APIRouter()

_ERRORS = {
    401: {"description": "Missing/invalid token, or the account is already deactivated"},
    403: {"description": "Account type cannot use self-service deletion"},
    404: {"description": "Challenge or request not found for this account"},
    409: {"description": "deletion_blocked. Customers: upcoming bookings or pending requests (details.open_bookings / details.pending_requests). Owners: only an active subscription (details.active_subscriptions) - open bookings never block an owner, they are cancelled and refunded"},
    429: {"description": "Cooldown, resend or attempt limit reached"},
}


def _use_cases(
    session: AsyncSession, auth_gateway: AuthGateway, auth_admin: AuthAdminGateway
) -> AccountDeletionUseCases:
    return AccountDeletionUseCases(
        SQLAccountDeletionRepository(session), auth_gateway, auth_admin, settings
    )


@router.post(
    "/challenges",
    response_model=DeletionChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a deletion verification code to your own verified email or phone",
    responses={**_ERRORS, 422: {"description": "contact_mismatch or no verified contact"}},
)
async def start_deletion_challenge(
    payload: StartDeletionChallengeRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> DeletionChallengeResponse:
    result = await _use_cases(session, auth_gateway, auth_admin).start_challenge(
        actor, payload.channel, payload.contact
    )
    return DeletionChallengeResponse(**result)


@router.post(
    "/challenges/{challenge_id}/verify",
    response_model=VerifiedDeletionChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify the code; returns a one-time confirmation token (nothing is deleted yet)",
    responses={**_ERRORS, 400: {"description": "invalid_verification_code"}},
)
async def verify_deletion_challenge(
    challenge_id: UUID,
    payload: VerifyDeletionChallengeRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> VerifiedDeletionChallengeResponse:
    result = await _use_cases(session, auth_gateway, auth_admin).verify_challenge(
        actor, str(challenge_id), payload.code
    )
    return VerifiedDeletionChallengeResponse(**result)


@router.post(
    "",
    response_model=AccountDeletionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Irreversibly delete the account (explicit confirmation)",
    description="Locks the account immediately and queues permanent erasure of the "
    "identity and personal data. There is no recovery. For an owner the worker first "
    "cancels every upcoming booking at their salons (customers are notified, online payments "
    "refunded) and only then erases.",
    responses={**_ERRORS, 400: {"description": "invalid_verification_code"}},
)
async def confirm_account_deletion(
    payload: ConfirmAccountDeletionRequest,
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AccountDeletionAcceptedResponse:
    result = await _use_cases(session, auth_gateway, auth_admin).confirm(
        actor, str(payload.challenge_id), payload.confirmation_token
    )
    return AccountDeletionAcceptedResponse(**result)


@router.get(
    "/{request_id}",
    response_model=AccountDeletionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Deletion progress; authenticated by X-Status-Token, not the JWT",
    responses={404: {"description": "Unknown request or wrong status token"}},
)
async def get_deletion_status(
    request_id: UUID,
    x_status_token: str = Header(min_length=20, max_length=128),
    session: AsyncSession = Depends(get_session),
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> AccountDeletionStatusResponse:
    result = await _use_cases(session, auth_gateway, auth_admin).get_status(
        str(request_id), x_status_token
    )
    return AccountDeletionStatusResponse(**result)


@admin_router.get(
    "/account-deletions",
    response_model=list[AdminAccountDeletionResponse],
    status_code=status.HTTP_200_OK,
    summary="Account deletion ledger (no personal identifiers)",
)
async def list_account_deletions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: Profile = Depends(require_role(Role.super_admin)),
    session: AsyncSession = Depends(get_authenticated_session),
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
    auth_admin: AuthAdminGateway = Depends(get_auth_admin_gateway),
) -> list[AdminAccountDeletionResponse]:
    rows = await _use_cases(session, auth_gateway, auth_admin).list_requests(actor, limit, offset)
    return [AdminAccountDeletionResponse(**row) for row in rows]
