"""Authentication gateway port."""

from typing import Protocol

from app.application.dto.auth import AuthTokens, LoginInput, RefreshInput


class AuthGateway(Protocol):
    """External authentication provider operations."""

    async def login(self, payload: LoginInput) -> AuthTokens:
        """Authenticate an email and password through the identity provider."""

    async def refresh(self, payload: RefreshInput) -> AuthTokens:
        """Refresh a provider session."""
