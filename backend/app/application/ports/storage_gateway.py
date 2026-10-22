"""Storage gateway port."""

from abc import ABC, abstractmethod

from app.application.ports.image_processor import ImagePolicy, ProcessedImageFamily

_UPLOAD_TTL_SECONDS = 300  # 5 minutes — exposed so implementations stay consistent

_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
"""Image MIME types accepted for signed upload URLs.

Shared here so schemas and use cases can reference a single source of truth.
"""


class StorageGateway(ABC):
    """Abstract interface for cloud object storage.

    The infrastructure layer implements this for each storage backend:
    - R2StorageGateway  (validated backend upload gateway, Cloudflare R2 storage)
    """

    @abstractmethod
    async def get_upload_url(self, bucket: str, path: str, content_type: str = "image/jpeg") -> str:
        """Return a short-lived signed URL the client can PUT image bytes to.

        Args:
            bucket: Storage bucket name (e.g. 'salon-images').
            path: Object path within the bucket (e.g. '{salon_id}/{uuid}.jpg').
            content_type: MIME type of the file to be uploaded.

        Returns:
            A signed PUT URL valid for ``_UPLOAD_TTL_SECONDS`` seconds.
        """

    @abstractmethod
    def get_public_url(self, bucket: str, path: str) -> str:
        """Return the permanent public URL for a delivered object.

        Args:
            bucket: Storage bucket name (informational; may be ignored by some backends).
            path: Object path within the bucket.

        Returns:
            The HTTPS URL clients use to fetch the stored object.
        """

    @abstractmethod
    async def delete_object(self, bucket: str, path: str) -> None:
        """Delete an object from storage. No-op if the object does not exist.

        Called best-effort after a salon image soft-delete so the binary is
        removed from R2.  A storage failure must not prevent the DB soft-delete
        from being committed.

        Args:
            bucket: Storage bucket name.
            path: Object path within the bucket.
        """

    async def upload_processed_family(self, bucket: str, namespace: str,
                                      family: ProcessedImageFamily, *, alias: str | None = None) -> dict:
        """Upload explicitly processed variants; raw byte uploads are not a port."""
        raise NotImplementedError("Image families unavailable")

    async def publication_urls(self, url: str) -> list[str]:
        """Additional family URLs that must be locked before publication."""
        return []

    async def retirement_paths(self, path: str) -> list[str]:
        """Return all family members and aliases, or the single legacy key."""
        return [path]

    async def retirement_lock_paths(self, path: str) -> list[str]:
        return [path]

    async def retirement_ready(self, paths: list[str]) -> bool:
        return True

    async def erasure_lock_paths(self, path: str) -> list[str]:
        return [path]

    async def erasure_paths(self, path: str) -> list[str]:
        return [path]

    async def upload_result(self, token: str) -> dict:
        """Return variant metadata for a read-only result token (not an upload token)."""
        raise NotImplementedError("Image families unavailable")

    def get_result_url(self, upload_url: str) -> str | None:
        """Return a read-only URL for the upload's result, or None if unsupported."""
        return None

    def validate_upload_token(self, token: str, content_type: str) -> None:
        """Verify a backend upload capability before reading its body."""
        raise NotImplementedError("Upload gateway unavailable")

    async def accept_upload(self, token: str, data: bytes, content_type: str) -> dict:
        """Validate and process a signed upload before publishing it."""
        raise NotImplementedError("Upload gateway unavailable")

    async def validate_media_reference(self, url: str, namespace: str, *, policy: ImagePolicy | None = None) -> None:
        """Require an owned object with trusted proof of server-side processing."""
        raise NotImplementedError("Media publication validation unavailable")
