"""Customer app use cases."""

import uuid
from typing import Any

from app.application.ports.storage_gateway import StorageGateway
from app.application.use_cases.media_publication import validate_media_reference
from app.application.use_cases.upload_helpers import _upload_extension, _upload_result
from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.entities.profile import Profile, Role
from app.infrastructure.db.repositories.platform_repository import PlatformRepository


class CustomerUseCases:
    """Customer app use cases."""

    def __init__(
        self,
        repository: PlatformRepository,
        storage_gateway: StorageGateway | None = None,
    ) -> None:
        self.repository = repository
        self.storage_gateway = storage_gateway

    async def update_profile(
        self,
        actor: Profile,
        values: dict[str, Any],
        *,
        bucket: str | None = None,
        r2_public_base: str | None = None,
    ) -> dict[str, Any]:
        """Update the customer profile owned by the actor.

        New hosted avatars require owned processing proof. Previous managed objects
        are retired by the worker after committed reference checks. Legacy URLs
        may remain unchanged and are never swept.

        Args:
            actor: Authenticated profile (customer or owner).
            values: Fields to update (``exclude_unset`` dict from Pydantic).
            bucket: Retained for call compatibility; cleanup uses worker settings.
            r2_public_base: Retained for call compatibility.
        """

        if actor.role not in {Role.customer, Role.owner}:
            raise ForbiddenError("Customer or owner access required")

        avatar = values.get("avatar_url")
        bundled = {f"__char__char-{index}" for index in range(1, 16)} | {"avatar:curly", "avatar:beard", "avatar:geek"}
        if avatar and avatar not in bundled:
            # The auth snapshot can be stale after a concurrent replacement.
            # Lock first and compare with the current committed reference.
            await self.repository.lock_media_url(avatar)
            current = await self.repository.get_profile(actor.id)
            if current is None:
                raise NotFoundError("Profile not found")
            if avatar != current.get("avatar_url"):
                await validate_media_reference(self.repository, self.storage_gateway, avatar, f"avatars/{actor.id}/")
        return await self.repository.update_profile(actor.id, values)

    async def list_salons(
        self,
        *,
        search: str | None,
        city: str | None,
        lat: float | None,
        lng: float | None,
        limit: int,
        offset: int,
        ids: list[str] | None = None,
        category: str | None = None,
        service: str | None = None,
        surface: str | None = None,
        shuffle_seed: str = "default",
    ) -> list[dict[str, Any]]:
        """List customer-visible salons.

        Services are NOT included. Use GET /salons/{salon_id}/services for service data.
        Pass ``category`` (e.g. ``"Hair Cutting"``) to filter salons by service category;
        the backend does a case-insensitive ILIKE match against ``service_categories.name``.
        """

        return await self.repository.list_salons(
            search=search,
            city=city,
            lat=lat,
            lng=lng,
            limit=limit,
            offset=offset,
            ids=ids,
            category=category,
            service=service,
            surface=surface,
            shuffle_seed=shuffle_seed,
        )

    async def assert_public_salon(self, salon_id: str) -> None:
        """Require current database visibility before returning cached public data."""
        await self.repository.assert_public_salon(salon_id)

    async def get_salon(self, salon_id: str) -> dict[str, Any]:
        """Return customer-visible salon details."""

        return await self.repository.get_public_salon(salon_id)

    async def list_salon_services(self, salon_id: str) -> list[dict[str, Any]]:
        """Return customer-visible services for a salon."""

        return await self.repository.list_public_services(salon_id)

    async def list_salon_staff(self, salon_id: str) -> list[dict[str, Any]]:
        """Return active staff for a customer-visible salon."""

        return await self.repository.list_public_staff(salon_id)

    async def get_avatar_upload_url(
        self,
        actor: Profile,
        content_type: str,
        filename: str,
        bucket: str,
    ) -> dict[str, Any]:
        """Generate a signed backend upload URL for a user profile avatar.

        Available to all authenticated roles (customer, owner, staff).
        The client should:
        1. Receive ``upload_url`` and ``public_url`` from this method.
        2. PUT the image binary directly to ``upload_url`` with the matching Content-Type header.
        3. Call PATCH /profiles/me with { "avatar_url": public_url } to record the URL.

        Args:
            actor: Authenticated profile (any role).
            content_type: MIME type of the image.
            filename: Original filename; used only to derive the file extension.
            bucket: R2 bucket name (read from settings in the router).

        Returns:
            Dict with keys: upload_url, public_url, expires_in.

        Note:
            ``storage_gateway`` is always a fully configured ``R2StorageGateway``
            when called from the router — ``get_storage_gateway()`` validates R2
            env vars at dependency-injection time before this method is reached.
        """
        assert self.storage_gateway is not None, "storage_gateway is required for avatar upload"

        if not actor.is_active:
            raise ForbiddenError("Active account required")
        ext = _upload_extension(filename, content_type)
        # Use a new key so a failed/replayed upload cannot replace a published photo.
        object_key = f"avatars/{actor.id}/{uuid.uuid4().hex}.{ext}"

        upload_url = await self.storage_gateway.get_upload_url(bucket, object_key, content_type)
        public_url = self.storage_gateway.get_public_url(bucket, object_key)
        return _upload_result(upload_url, public_url, self.storage_gateway.get_result_url(upload_url))
