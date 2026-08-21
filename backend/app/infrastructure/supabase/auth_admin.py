"""Supabase Auth Admin gateway — uses the service-role key."""

import httpx

from app.application.ports.auth_admin_gateway import AuthAdminGateway, CreatedAuthUser
from app.core.config import Settings
from app.core.exceptions import ConflictError, ValidationError


class SupabaseAuthAdminGateway(AuthAdminGateway):
    """Create and ban Supabase Auth users via the Admin REST API.

    Requires ``SUPABASE_SERVICE_ROLE_KEY`` — never expose this key to clients.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_user(
        self,
        email: str,
        password: str,
        role: str,
        full_name: str,
    ) -> CreatedAuthUser:
        """Create a Supabase Auth user with embedded role metadata."""

        base_url, headers = self._admin_base()
        payload = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"role": role, "full_name": full_name},
            "app_metadata": {"role": role},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{base_url}/auth/v1/admin/users",
                json=payload,
                headers=headers,
            )

        if response.status_code == 422:
            raise ConflictError("A user with this email already exists")
        if response.is_error:
            raise ValidationError(
                f"Could not create Supabase Auth user: {response.status_code}"
            )
        data = response.json()
        return CreatedAuthUser(user_id=data["id"], email=data["email"])

    async def ban_user(self, user_id: str) -> None:
        """Ban a Supabase Auth user so they cannot sign in."""

        base_url, headers = self._admin_base()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.put(
                f"{base_url}/auth/v1/admin/users/{user_id}",
                json={"ban_duration": "876000h"},  # 100 years ≈ permanent
                headers=headers,
            )
        if response.is_error:
            raise ValidationError(
                f"Could not ban Supabase Auth user {user_id}: {response.status_code}"
            )

    def _admin_base(self) -> tuple[str, dict[str, str]]:
        """Return base URL and auth headers for the Admin API."""

        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise ValidationError("Supabase admin credentials are not configured")
        base_url = str(self.settings.supabase_url).rstrip("/")
        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        return base_url, headers
