"""Supabase Auth gateway."""

from urllib.parse import urlencode

import httpx

from app.application.dto.auth import AuthTokens, RefreshInput
from app.application.ports.auth_gateway import AuthGateway
from app.core.config import Settings
from app.core.exceptions import (
    InvalidVerificationCodeError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from app.core.telemetry import measure_external


def channel_field(channel: str) -> str:
    """Map a verification channel to the Supabase request field."""

    return "email" if channel == "email" else "phone"


class SupabaseAuthGateway(AuthGateway):
    """Authenticate users through Supabase Auth REST endpoints."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def request_password_reset(self, email: str) -> None:
        path = "/auth/v1/recover"
        if self.settings.password_reset_redirect_url:
            path += "?" + urlencode({"redirect_to": str(self.settings.password_reset_redirect_url)})
        await self._raw_post(path, {"email": email})

    async def refresh(self, payload: RefreshInput) -> AuthTokens:
        """Refresh a session token."""

        return await self._post(
            "/auth/v1/token?grant_type=refresh_token",
            {"refresh_token": payload.refresh_token},
        )

    @measure_external("supabase_auth")
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
            "/auth/v1/verify",
            {"phone": phone, "token": otp, "type": "sms"},
        )

    async def send_verification_code(self, channel: str, destination: str) -> None:
        """Send an OTP to an existing user only (``create_user`` is false)."""

        body = {"create_user": False, channel_field(channel): destination}
        data = await self._raw_post("/auth/v1/otp", body)
        if data is None:
            raise ServiceUnavailableError("Could not send the verification code")

    async def verify_code_user_id(self, channel: str, destination: str, code: str) -> str:
        """Verify an OTP and return ONLY the user id; the issued session is dropped."""

        body = {
            "type": "email" if channel == "email" else "sms",
            channel_field(channel): destination,
            "token": code,
        }
        data = await self._raw_post("/auth/v1/verify", body)
        user = (data or {}).get("user") or {}
        if not user.get("id"):
            raise InvalidVerificationCodeError("The verification code is invalid or expired")
        return str(user["id"])

    @measure_external("supabase_auth")
    async def _raw_post(self, path: str, payload: dict[str, object]) -> dict[str, object] | None:
        if not self.settings.supabase_url or not self.settings.supabase_anon_key:
            raise ServiceUnavailableError("Authentication provider is not configured")
        base_url = str(self.settings.supabase_url).rstrip("/")
        headers = {
            "apikey": self.settings.supabase_anon_key,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{base_url}{path}", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("Authentication provider is unavailable") from exc
        if response.status_code in {400, 401, 403, 404, 422}:
            if path.endswith("/verify"):
                raise InvalidVerificationCodeError("The verification code is invalid or expired")
            return None
        if response.is_error:
            raise ServiceUnavailableError("Authentication provider request failed")
        parsed = response.json() if response.content else {}
        return parsed if isinstance(parsed, dict) else {}

    @measure_external("supabase_auth")
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
