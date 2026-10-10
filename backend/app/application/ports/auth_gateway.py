"""Authentication gateway port."""

from typing import Protocol

from app.application.dto.auth import AuthTokens, RefreshInput


class AuthGateway(Protocol):
    """External authentication provider operations."""

    async def refresh(self, payload: RefreshInput) -> AuthTokens:
        """Refresh a provider session."""

    async def send_verification_code(self, channel: str, destination: str) -> None:
        """Send a one-time code to an EXISTING user's email/phone; never create a user."""

    async def verify_code_user_id(self, channel: str, destination: str, code: str) -> str:
        """Verify a code and return only the provider user id; session tokens are discarded."""
