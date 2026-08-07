"""Supabase Auth gateway."""

import httpx

from app.application.dto.auth import AuthTokens, LoginInput, RefreshInput
from app.application.ports.auth_gateway import AuthGateway
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError, ValidationError


class SupabaseAuthGateway(AuthGateway):
    """Authenticate users through Supabase Auth REST endpoints."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def login(self, payload: LoginInput) -> AuthTokens:
        """Sign in with email and password."""

        return await self._post(
            "/auth/v1/token?grant_type=password",
            {"email": payload.email, "password": payload.password},
        )

    async def refresh(self, payload: RefreshInput) -> AuthTokens:
        """Refresh a session token."""

        return await self._post(
            "/auth/v1/token?grant_type=refresh_token",
            {"refresh_token": payload.refresh_token},
        )

    async def send_phone_otp(self, phone: str) -> None:
        """Send a phone OTP via Supabase Auth (walk-in QR flow)."""

        if not self.settings.supabase_url or not self.settings.supabase_anon_key:
            raise ValidationError("Supabase Auth is not configured")
        base_url = str(self.settings.supabase_url).rstrip("/")
        headers = {
            "apikey": self.settings.supabase_anon_key,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{base_url}/auth/v1/otp",
                json={"phone": phone},
                headers=headers,
            )
        if response.is_error:
            raise ValidationError("Could not send OTP — check phone number format")

    async def verify_phone_otp(self, phone: str, otp: str) -> AuthTokens:
        """Verify a phone OTP and return tokens (walk-in QR flow)."""

        return await self._post(
            "/auth/v1/token?grant_type=otp",
            {"phone": phone, "token": otp, "type": "sms"},
        )

    async def _post(self, path: str, payload: dict[str, str]) -> AuthTokens:
        if not self.settings.supabase_url or not self.settings.supabase_anon_key:
            raise ValidationError("Supabase Auth is not configured")

        base_url = str(self.settings.supabase_url).rstrip("/")
        headers = {
            "apikey": self.settings.supabase_anon_key,
            "Authorization": f"Bearer {self.settings.supabase_anon_key}",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{base_url}{path}", json=payload, headers=headers)

        if response.status_code in {400, 401}:
            raise UnauthorizedError("Invalid authentication credentials")
        if response.is_error:
            raise ValidationError("Authentication provider request failed")

        data = response.json()
        return AuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "bearer"),
            expires_in=data.get("expires_in"),
        )
