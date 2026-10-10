"""Idempotent, resumable erasure of a confirmed account-deletion request."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.application.ports.account_deletion_repository import AccountDeletionRepository
from app.application.ports.auth_admin_gateway import AuthAdminGateway
from app.application.ports.cache_gateway import CacheGateway
from app.application.ports.media_references import MediaReferences
from app.application.ports.storage_gateway import StorageGateway

logger = logging.getLogger(__name__)

MEDIA_NAMESPACES = ("avatars/", "salon-images/", "staff-photos/")


class ErasureVerificationError(RuntimeError):
    """Post-conditions did not hold; the request is retried, never completed."""


def managed_media_path(storage: StorageGateway, bucket: str, url: str) -> str | None:
    """Map a stored URL to an object key inside the platform's own namespaces."""

    for namespace in MEDIA_NAMESPACES:
        prefix = storage.get_public_url(bucket, namespace)
        if not url.startswith(prefix):
            continue
        rest = url[len(prefix):]
        parts = rest.split("/")
        if not rest or any(c in rest for c in ("%", "\\", "?", "#")):
            return None
        if any(p in ("", ".", "..") for p in parts):
            return None
        return namespace + rest
    return None


class AccountErasureService:
    """Runs each erasure step once, recording progress so retries resume safely."""

    def __init__(
        self,
        repository: AccountDeletionRepository,
        auth_admin: AuthAdminGateway,
        storage: StorageGateway,
        cache: CacheGateway,
        media_references: MediaReferences,
        release_media_lock: Callable[[], Awaitable[None]],
        bucket: str | None,
        stale_seconds: int,
    ) -> None:
        self.repository = repository
        self.auth_admin = auth_admin
        self.storage = storage
        self.cache = cache
        self.media_references = media_references
        self.release_media_lock = release_media_lock
        self.bucket = bucket
        self.stale_seconds = stale_seconds

    async def process_next(self) -> bool:
        """Claim and run one due request. Returns False when nothing was due."""

        request = await self.repository.claim_due_request(self.stale_seconds)
        if request is None:
            return False
        request_id = str(request["id"])
        try:
            await self._run(request)
        except Exception as exc:
            logger.warning(
                "Account erasure step failed for request %s: %s", request_id, type(exc).__name__
            )
            delay = min(3600, 30 * 2 ** min(int(request["attempts"]), 7))
            await self.repository.fail_request(request_id, type(exc).__name__, delay)
        return True

    async def _run(self, request: dict[str, Any]) -> None:
        request_id = str(request["id"])
        user_id = str(request["user_id"])
        state: dict[str, Any] = request["step_state"]

        async def once(step: str, action: Callable[[], Awaitable[None]]) -> None:
            if state.get(step):
                return
            await action()
            await self.repository.record_step(request_id, step)
            state[step] = True

        await once("auth_banned", lambda: self._ban(user_id, state.get("staff_profile_ids", [])))
        await once("db_erased", lambda: self.repository.erase_database(user_id, request["role"]))
        await once("media_deleted", lambda: self._delete_media(request["media_keys"]))
        await once("cache_cleared", lambda: self._clear_cache(user_id, request.get("salon_id")))
        await once("auth_deleted", lambda: self.auth_admin.delete_user(user_id))

        if await self.repository.profile_exists(user_id):
            raise ErasureVerificationError("profile_still_exists")
        if await self.auth_admin.get_user(user_id) is not None:
            raise ErasureVerificationError("auth_user_still_exists")
        await self.repository.complete_request(request_id)

    async def _ban(self, user_id: str, staff_profile_ids: list[str]) -> None:
        for target in [user_id, *staff_profile_ids]:
            if await self.auth_admin.get_user(target) is not None:
                await self.auth_admin.ban_user(target)

    async def _delete_media(self, urls: list[str]) -> None:
        if not urls:
            return
        if not self.bucket:
            raise ErasureVerificationError("storage_not_configured")
        for url in urls:
            path = managed_media_path(self.storage, self.bucket, url)
            if path is None:
                continue
            try:
                await self.media_references.lock_media_url(url)
                if not await self.media_references.media_url_is_referenced(url):
                    await self.storage.delete_object(self.bucket, path)
            finally:
                await self.release_media_lock()

    async def _clear_cache(self, user_id: str, salon_id: object | None) -> None:
        if salon_id:
            await self.cache.delete_prefix(f"salon:{salon_id}:")
            await self.cache.delete_prefix("walkin:qr:")
        await self.cache.delete_prefix(f"idempotency:walkin:v2:{user_id}:")
