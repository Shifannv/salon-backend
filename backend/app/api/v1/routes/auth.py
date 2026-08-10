"""Authentication API routes."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_gateway, get_current_actor
from app.api.v1.schemas.auth import ProfileResponse, RefreshRequest, TokenResponse
from app.application.dto.auth import RefreshInput
from app.application.ports.auth_gateway import AuthGateway
from app.application.use_cases.auth.me import GetMe
from app.application.use_cases.auth.refresh import Refresh
from app.domain.entities.profile import Profile

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
