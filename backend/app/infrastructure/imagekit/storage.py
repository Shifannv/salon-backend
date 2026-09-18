"""ImageKit uploads with bounded, signed PUT tickets for existing clients."""

import base64
import hashlib
import hmac
import json
import time
from pathlib import PurePosixPath

import httpx

from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS, StorageGateway
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError, ValidationError


class ImageKitStorageGateway(StorageGateway):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _key(self) -> str:
        if not self.settings.imagekit_private_key or not self.settings.imagekit_url_endpoint:
            raise ValidationError("Configure IMAGEKIT_PRIVATE_KEY and IMAGEKIT_URL_ENDPOINT")
        return self.settings.imagekit_private_key

    def _signature(self, payload: str) -> str:
        return hmac.new(self._key().encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def get_upload_url(self, bucket: str, path: str, content_type: str = "image/jpeg") -> str:
        self._key()
        if not self.settings.public_api_base_url:
            raise ValidationError("Configure PUBLIC_API_BASE_URL for ImageKit upload URLs")
        payload = base64.urlsafe_b64encode(json.dumps({
            "path": path, "content_type": content_type,
            "expires": int(time.time()) + _UPLOAD_TTL_SECONDS,
        }).encode()).decode()
        ticket = f"{payload}.{self._signature(payload)}"
        return f"{str(self.settings.public_api_base_url).rstrip('/')}/v1/media/uploads/{ticket}"

    def verify_ticket(self, ticket: str) -> dict:
        try:
            payload, signature = ticket.split(".")
            if not hmac.compare_digest(self._signature(payload), signature):
                raise ValueError
            values = json.loads(base64.urlsafe_b64decode(payload))
            if values["expires"] <= time.time():
                raise ValueError
            return values
        except (ValueError, KeyError, TypeError) as exc:
            raise UnauthorizedError("Invalid or expired upload URL") from exc

    def get_public_url(self, bucket: str, path: str) -> str:
        self._key()
        return f"{str(self.settings.imagekit_url_endpoint).rstrip('/')}/{path}"

    async def upload_bytes(self, bucket: str, path: str, data: bytes,
                           content_type: str = "image/png") -> str:
        key = self._key()
        destination = PurePosixPath(path)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://upload.imagekit.io/api/v1/files/upload",
                    auth=(key, ""),
                    files={"file": (destination.name, data, content_type)},
                    data={"fileName": destination.name, "folder": str(destination.parent),
                          "useUniqueFileName": "false", "isPrivateFile": "false"},
                )
                response.raise_for_status()
                result = response.json()
                if not result.get("url"):
                    raise ValueError("Missing upload URL")
        except (httpx.HTTPError, ValueError) as exc:
            raise ValidationError("ImageKit upload failed; check server storage configuration") from exc
        return self.get_public_url(bucket, path)

    async def delete_object(self, bucket: str, path: str) -> None:
        # The existing port stores paths, whereas ImageKit deletion requires file IDs.
        # Keep media for retention; platform records continue to use soft deletion.
        return None
