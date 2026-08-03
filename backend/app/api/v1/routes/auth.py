"""Authentication API routes."""

from fastapi import APIRouter, Depends, status

from app.api.deps import get_auth_gateway, get_current_actor
from app.api.v1.schemas.auth import LoginRequest, ProfileResponse, RefreshRequest, TokenResponse
from app.application.dto.auth import LoginInput, RefreshInput
from app.application.ports.auth_gateway import AuthGateway
from app.application.use_cases.auth.login import Login
from app.application.use_cases.auth.me import GetMe
from app.application.use_cases.auth.refresh import Refresh
from app.domain.entities.profile import Profile

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in with Supabase Auth",
)
async def login(
    payload: LoginRequest,
    auth_gateway: AuthGateway = Depends(get_auth_gateway),
) -> TokenResponse:
    """Authenticate an email-password user through Supabase Auth."""

    tokens = await Login(auth_gateway).execute(LoginInput(email=str(payload.email), password=payload.password))
    return TokenResponse(**tokens.__dict__)


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
    return ProfileResponse(**output.profile.__dict__)
