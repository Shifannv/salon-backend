"""Barber/owner app API routes.

The routes live in ``owner_salon``, ``owner_holidays``, ``owner_catalog`` and ``owner_blocks``.
They are included here in their original order, so paths, operation ids and registration order
are unchanged. ``_use_cases`` stays defined in this module because tests patch it here.
"""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_storage_gateway
from app.api.v1.routes import owner_blocks, owner_catalog, owner_holidays, owner_salon
from app.api.v1.routes.owner_salon import get_my_qr
from app.api.v1.schemas.salon import QrCodeUrlResponse
from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.platform import OwnerUseCases
from app.core.config import settings
from app.infrastructure.db.repositories.platform_repository import PlatformRepository

__all__ = ["QrCodeUrlResponse", "get_my_qr", "router", "settings"]

router = APIRouter()


def _use_cases(
    session: AsyncSession,
    storage_gateway: StorageGateway | None = None,
) -> OwnerUseCases:
    return OwnerUseCases(
        PlatformRepository(session), storage_gateway=storage_gateway or get_storage_gateway(),
        service_media_base=settings.r2_public_url,
    )


router.include_router(owner_salon.router)
router.include_router(owner_holidays.router)
router.include_router(owner_catalog.router)
router.include_router(owner_blocks.router)
