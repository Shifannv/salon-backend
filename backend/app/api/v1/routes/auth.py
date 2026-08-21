"""Authentication API routes."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_gateway, get_authenticated_session, get_current_actor
from app.api.v1.schemas.auth import ProfileResponse, RefreshRequest, TokenResponse
from app.application.dto.auth import RefreshInput
from app.application.ports.auth_gateway import AuthGateway
from app.application.use_cases.auth.me import GetMe
from app.application.use_cases.auth.owner_access import EnsureOwnerAccess
from app.application.use_cases.auth.refresh import Refresh
from app.domain.entities.profile import Profile
from app.infrastructure.db.repositories.profile_repository import SQLProfileRepository

router = APIRouter()


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh a Supabase Auth session",
)
async def refresh(
    payload: RefreshRequest,
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
) -> TokenResponse:
    """Refresh a Supabase Auth session using a refresh token."""

    tokens = await Refresh(auth_gateway).execute(RefreshInput(refresh_token=payload.refresh_token))
    return TokenResponse(**tokens.__dict__)


@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated profile",
)
async def me(actor: Profile = Depends(get_current_actor)) -> ProfileResponse:
    """Return the profile resolved from the verified Supabase JWT subject."""

    output = await GetMe().execute(actor)
    return ProfileResponse(**asdict(output.profile))


@router.post(
    "/owner-access",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Claim salon-owner access for the current account",
)
async def owner_access(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_authenticated_session),
) -> ProfileResponse:
    """Ensure the signed-in account holds a salon-workspace role, and return it.

    The owner app calls this once per sign-in. It is idempotent, so a returning owner
    pays one no-op round-trip and a brand-new Google account gets the ``owner`` role it
    needs before `GET /salons/me` is ever asked for.
    """

    output = await EnsureOwnerAccess(SQLProfileRepository(session)).execute(actor)
    return ProfileResponse(**asdict(output.profile))
