"""Supabase JWT verification and actor extraction."""

from typing import Any

import httpx
from jose import JWTError, jwt

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError


class SupabaseJWTVerifier:
    """Verify Supabase JWTs against the project's JWKS endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks: dict[str, Any] | None = None

    async def verify_subject(self, token: str) -> str:
        """Return the verified Supabase user id from a bearer token."""

        if not self.settings.supabase_jwks_url:
            raise UnauthorizedError("Supabase JWKS URL is not configured")

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not isinstance(kid, str):
                raise UnauthorizedError("Invalid token header")

            key_data = await self._get_key(kid)
            claims = jwt.decode(
                token,
                key_data,
                algorithms=[key_data.get("alg", "RS256")],
                audience=self.settings.supabase_jwt_audience,
                issuer=str(self.settings.supabase_url).rstrip("/") + "/auth/v1"
                if self.settings.supabase_url
                else None,
                options={"verify_aud": self.settings.supabase_jwt_audience is not None},
            )
        except (JWTError, ValueError, KeyError) as exc:
            raise UnauthorizedError("Invalid authentication credentials") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise UnauthorizedError("Invalid authentication credentials")
        return subject

    async def _get_key(self, kid: str) -> dict[str, Any]:
        if self._jwks is None:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(str(self.settings.supabase_jwks_url))
                response.raise_for_status()
                self._jwks = response.json()
        for key_data in self._jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return key_data
        self._jwks = None
        raise UnauthorizedError("Invalid authentication credentials")
