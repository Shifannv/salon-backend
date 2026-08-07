"""Storage gateway port."""

from abc import ABC, abstractmethod


class StorageGateway(ABC):
    """Abstract interface for cloud object storage.

    The infrastructure layer (SupabaseStorageGateway) implements this.
    """

    @abstractmethod
    async def get_upload_url(self, bucket: str, path: str, content_type: str = "image/jpeg") -> str:
        """Return a short-lived signed URL for a direct client upload.

        Args:
            bucket: Supabase Storage bucket name (e.g. 'salon-images').
            path: Object path within the bucket (e.g. '{salon_id}/cover.jpg').
            content_type: MIME type of the file to be uploaded.

        Returns:
            A signed upload URL the client can PUT to directly.
        """
