"""Supabase Storage gateway — signed upload URLs."""

import httpx

from app.application.ports.storage_gateway import StorageGateway
from app.core.config import Settings
from app.core.exceptions import ValidationError


class SupabaseStorageGateway(StorageGateway):
    """Generate signed upload URLs via the Supabase Storage REST API.

    Clients upload directly to Supabase Storage; this backend only hands
    out time-limited signed URLs so it never touches the binary data.
    """

    _SIGNED_UPLOAD_TTL_SECONDS = 300  # 5 minutes

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_upload_url(
        self,
        bucket: str,
        path: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Return a signed URL the client can PUT to directly.

        Args:
            bucket: Supabase Storage bucket name (e.g. 'salon-images').
            path: Object path within the bucket.
            content_type: MIME type of the upload.
        """
        if not self.settings.supabase_url or not self.settings.supabase_service_role_key:
            raise ValidationError("Supabase Storage is not configured")

        base_url = str(self.settings.supabase_url).rstrip("/")
        headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{base_url}/storage/v1/object/upload/sign/{bucket}/{path}",
                json={
                    "expiresIn": self._SIGNED_UPLOAD_TTL_SECONDS,
                    "contentType": content_type,
                },
                headers=headers,
            )
        if response.is_error:
            raise ValidationError(
                f"Could not generate upload URL: {response.status_code}"
            )
        data = response.json()
        signed_url: str = data.get("signedURL") or data.get("url", "")
        if not signed_url:
            raise ValidationError("Supabase Storage returned no URL")
        return signed_url
