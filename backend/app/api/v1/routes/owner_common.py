"""Shared helper for the owner route modules."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.platform import OwnerUseCases


def owner_use_cases(
    session: AsyncSession, storage_gateway: StorageGateway | None = None
) -> OwnerUseCases:
    """Build the owner use cases through ``owner._use_cases``, resolved at call time.

    Tests patch ``app.api.v1.routes.owner._use_cases``; looking it up here on every call keeps
    that patch target effective for the routes that now live in the ``owner_*`` modules.
    """

    from app.api.v1.routes import owner

    if storage_gateway is None:
        return owner._use_cases(session)
    return owner._use_cases(session, storage_gateway)
