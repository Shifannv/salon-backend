"""Refresh-session use case."""

from app.application.dto.auth import AuthTokens, RefreshInput
from app.application.ports.auth_gateway import AuthGateway


class Refresh:
    """Refresh a Supabase Auth session."""

    def __init__(self, auth_gateway: AuthGateway) -> None:
        self.auth_gateway = auth_gateway

    async def execute(self, payload: RefreshInput) -> AuthTokens:
        """Return a refreshed provider session."""

        return await self.auth_gateway.refresh(payload)
