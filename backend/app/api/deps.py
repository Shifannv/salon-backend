"""API dependency wiring."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.storage_gateway import StorageGateway
from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import SupabaseJWTVerifier
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.profile_repository import SQLProfileRepository
from app.infrastructure.db.session import get_session, set_actor_context
from app.infrastructure.r2.storage import R2StorageGateway
from app.infrastructure.supabase.auth_admin import SupabaseAuthAdminGateway
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway

bearer_scheme = HTTPBearer(
    scheme_name="Supabase Google OAuth",
    description="Supabase access token returned after Google OAuth sign-in.",
)
_jwt_verifier = SupabaseJWTVerifier(settings)


def get_auth_gateway() -> SupabaseAuthGateway:
    """Return the configured Supabase Auth gateway."""

    return SupabaseAuthGateway(settings)


def get_auth_admin_gateway() -> AuthAdminGateway:
    """Return the configured Supabase Auth Admin gateway (service-role key).

    Used by admin routes that need to create or ban Supabase Auth users.
    """

    return SupabaseAuthAdminGateway(settings)


def get_storage_gateway() -> StorageGateway:
    """Return the configured Cloudflare R2 storage gateway.

    Validates that all required R2 environment variables are set at
    dependency-injection time so callers get a clear error message
    (e.g. "Cloudflare R2 is not fully configured. Missing: R2_ACCESS_KEY_ID")
    instead of a cryptic failure deep inside an upload call.

    Raises:
        ValidationError → HTTP 422 if any R2 env var is absent.
    """

    gateway = R2StorageGateway(settings)
    gateway._assert_configured()
    return gateway


async def get_current_actor(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Profile:
    """Verify the bearer token and resolve it to a profile row.

    FastAPI deduplicates Depends(get_session) across the request — both this
    dependency and get_authenticated_session receive the SAME session instance.
    Actor context is set once in get_authenticated_session; not here.
    """

    actor_id = await _jwt_verifier.verify_subject(credentials.credentials)
    profile = await SQLProfileRepository(session).get_by_id(actor_id)
    if not profile or not profile.is_active:
        raise UnauthorizedError("User not found")
    return profile


async def get_authenticated_session(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session with the actor audit context set exactly once.

    FastAPI deduplicates Depends(get_session) — the session here is the same
    object passed to get_current_actor, so set_actor_context is called once
    on the session that all repository calls will use.
    """

    await set_actor_context(session, actor.id)
    yield session


def require_role(*roles: Role):
    """Create a dependency requiring one of the given roles."""

    async def dependency(actor: Profile = Depends(get_current_actor)) -> Profile:
        if actor.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return actor

    return dependency
