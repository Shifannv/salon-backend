"""API dependency wiring."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.payment_gateway import PaymentGateway
from app.application.ports.storage_gateway import StorageGateway
from app.core.config import settings
from app.core.exceptions import AdminMFARequiredError, ForbiddenError, UnauthorizedError
from app.core.security import SupabaseJWTVerifier
from app.domain.entities.profile import Profile, Role
from app.infrastructure.cache.redis import get_redis_cache
from app.infrastructure.db.repositories.profile_repository import SQLProfileRepository
from app.infrastructure.db.session import get_session, set_actor_context
from app.infrastructure.payments.resolver import PaymentGatewayResolver, get_payment_resolver
from app.infrastructure.r2.storage import R2StorageGateway
from app.infrastructure.subscriptions.resolver import (
    SubscriptionProviderResolver,
    get_subscription_resolver,
)
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
    """Return R2 lazily, so routes that do not upload remain independent of storage."""
    return R2StorageGateway(settings)


def get_cache() -> CacheGateway:
    """Return the configured cache gateway."""
    return get_redis_cache()


def get_payment_gateway_resolver() -> PaymentGatewayResolver:
    """Return the process-wide payment gateway resolver (dormant unless configured)."""
    return get_payment_resolver()


def get_payment_gateway() -> PaymentGateway:
    """Domain-typed annotation, concrete factory: the platform-level gateway."""
    return get_payment_resolver().resolve()


def get_subscription_provider_resolver() -> SubscriptionProviderResolver:
    """Return the process-wide subscription billing resolver (dormant unless configured)."""
    return get_subscription_resolver()


async def get_current_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Profile:
    """Verify the bearer token and resolve it to a profile row.

    FastAPI deduplicates Depends(get_session) across the request — both this
    dependency and get_authenticated_session receive the SAME session instance.
    Actor context is set once in get_authenticated_session; not here.
    """

    claims = await _jwt_verifier.verify_claims(credentials.credentials)
    request.state.verified_auth_claims = claims
    actor_id = claims["sub"]
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

    async def dependency(request: Request, actor: Profile = Depends(get_current_actor)) -> Profile:
        if actor.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        if actor.role == Role.super_admin and settings.admin_require_mfa:
            claims = getattr(request.state, "verified_auth_claims", {})
            if claims.get("aal") != "aal2":
                raise AdminMFARequiredError("Multi-factor authentication required for admin access")
        return actor

    return dependency
