"""Storage gateway port."""

from abc import ABC, abstractmethod

_UPLOAD_TTL_SECONDS = 300  # 5 minutes — exposed so implementations stay consistent

_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
    }
)
"""Image MIME types accepted for presigned upload URLs.

Shared here so schemas and use cases can reference a single source of truth.
"""


class StorageGateway(ABC):
    """Abstract interface for cloud object storage.

    The infrastructure layer implements this for each storage backend:
    - R2StorageGateway  (Cloudflare R2, S3-compatible presigned URLs)
    - SupabaseStorageGateway  (legacy, kept for reference)
    """

    @abstractmethod
    async def get_upload_url(self, bucket: str, path: str, content_type: str = "image/jpeg") -> str:
        """Return a short-lived presigned URL the client can PUT to directly.

        Args:
            bucket: Storage bucket name (e.g. 'salon-images').
            path: Object path within the bucket (e.g. '{salon_id}/{uuid}.jpg').
            content_type: MIME type of the file to be uploaded.

        Returns:
            A presigned PUT URL valid for ``_UPLOAD_TTL_SECONDS`` seconds.
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

        Not yet wired to any HTTP route — the 501 stub remains until the schema
        supports soft-delete on ``salon_images``.

        Args:
            bucket: Storage bucket name.
            path: Object path within the bucket.
        """

    @abstractmethod
    async def upload_bytes(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "image/png",
    ) -> str:
        """Upload raw bytes directly from the server and return the public URL.

        This is the server-side complement to ``get_upload_url``/``get_public_url``.
        Use it when the backend itself generates the binary content (e.g. QR codes)
        rather than proxying a client upload.

        Args:
            bucket: Storage bucket name.
            path: Object path within the bucket.
            data: Raw bytes to upload.
            content_type: MIME type (defaults to image/png).

        Returns:
            The permanent public URL of the uploaded object.
        """
