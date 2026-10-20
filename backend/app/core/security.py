"""Supabase JWT verification and actor extraction."""

import time
from typing import Any

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.core.telemetry import measure_external

# JWKS keys are long-lived; Supabase rotates them very rarely.
# Cache for 60 minutes so a key rotation is picked up within an hour
# without restarting the server.
_JWKS_TTL_SECONDS = 3600


class SupabaseJWTVerifier:
    """Verify Supabase JWTs against the project's JWKS endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0.0  # epoch seconds

    async def verify_subject(self, token: str) -> str:
        """Return the verified Supabase user id from a bearer token."""
        return (await self.verify_claims(token))["sub"]

    async def verify_claims(self, token: str) -> dict[str, Any]:
        """Return claims only after signature, issuer, audience and expiry verification."""

        if not self.settings.supabase_jwks_url:
            raise UnauthorizedError("Supabase JWKS URL is not configured")

        # Imported on first use: jose loads cryptography, which costs about 0.3 s of
        # Cloud Run cold start that public routes do not need.
        from jose import JWTError, jwt

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
        return claims

    async def _get_key(self, kid: str) -> dict[str, Any]:
        """Return the JWK matching kid, refreshing the cache if stale."""

        now = time.monotonic()
        cache_expired = (now - self._jwks_fetched_at) > _JWKS_TTL_SECONDS

        if self._jwks is None or cache_expired:
            await self._refresh_jwks()

        key = self._find_key(kid)
        if key is not None:
            return key

        # kid not found — force a refresh once in case Supabase just rotated keys
        await self._refresh_jwks()
        key = self._find_key(kid)
        if key is not None:
            return key

        raise UnauthorizedError("Invalid authentication credentials")

    def _find_key(self, kid: str) -> dict[str, Any] | None:
        if self._jwks is None:
            return None
        for key_data in self._jwks.get("keys", []):
            if key_data.get("kid") == kid:
                return key_data
        return None

    @measure_external("supabase_jwks")
    async def _refresh_jwks(self) -> None:
        """Fetch fresh JWKS from Supabase and update the in-memory cache."""

        import httpx  # on first use, to keep it out of cold start

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(str(self.settings.supabase_jwks_url))
            response.raise_for_status()
            self._jwks = response.json()
            self._jwks_fetched_at = time.monotonic()
