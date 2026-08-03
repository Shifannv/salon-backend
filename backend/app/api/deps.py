"""API dependency wiring."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import SupabaseJWTVerifier
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.profile_repository import SQLProfileRepository
from app.infrastructure.db.session import get_session, set_actor_context
from app.infrastructure.supabase.auth_gateway import SupabaseAuthGateway

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
_jwt_verifier = SupabaseJWTVerifier(settings)


def get_auth_gateway() -> SupabaseAuthGateway:
    """Return the configured Supabase Auth gateway."""

    return SupabaseAuthGateway(settings)


async def get_current_actor(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Profile:
    """Verify the bearer token and resolve it to a profile row."""

    actor_id = await _jwt_verifier.verify_subject(token)
    profile = await SQLProfileRepository(session).get_by_id(actor_id)
    if not profile or not profile.is_active:
        raise UnauthorizedError("User not found")
    await set_actor_context(session, profile.id)
    return profile


async def get_authenticated_session(
    actor: Profile = Depends(get_current_actor),
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a session with the actor context set for audit triggers."""

    await set_actor_context(session, actor.id)
    yield session


def require_role(*roles: Role):
    """Create a dependency requiring one of the given roles."""

    async def dependency(actor: Profile = Depends(get_current_actor)) -> Profile:
        if actor.role not in roles:
            from app.core.exceptions import ForbiddenError

            raise ForbiddenError("Insufficient permissions")
        return actor

    return dependency
