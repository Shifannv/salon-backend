"""Login use case."""

from app.application.dto.auth import AuthTokens, LoginInput
from app.application.ports.auth_gateway import AuthGateway


class Login:
    """Authenticate a user through Supabase Auth."""

    def __init__(self, auth_gateway: AuthGateway) -> None:
        self.auth_gateway = auth_gateway

    async def execute(self, payload: LoginInput) -> AuthTokens:
        """Return provider tokens for valid credentials."""

        return await self.auth_gateway.login(payload)
