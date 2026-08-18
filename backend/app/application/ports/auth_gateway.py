"""Authentication gateway port."""

from typing import Protocol

from app.application.dto.auth import AuthTokens, RefreshInput


class AuthGateway(Protocol):
    """External authentication provider operations."""

    async def refresh(self, payload: RefreshInput) -> AuthTokens:
        """Refresh a provider session."""
