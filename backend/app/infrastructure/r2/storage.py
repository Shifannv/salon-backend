"""Cloudflare R2 storage gateway — presigned PUT/DELETE via the S3-compatible API.

Cloudflare R2 exposes an S3-compatible endpoint at:
    https://<account_id>.r2.cloudflarestorage.com

boto3 is synchronous, so all blocking calls are dispatched to a thread-pool
executor to remain async-safe inside the FastAPI event loop.

Upload flow
-----------
1. Client calls POST /v1/salons/me/images/upload-url
2. Backend returns { upload_url, public_url, expires_in }
3. Client PUTs the image binary directly to upload_url (no backend in the path)
4. Client calls POST /v1/salons/me/images with { url: public_url }
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS, StorageGateway
from app.core.config import Settings
from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="r2")


class R2StorageGateway(StorageGateway):
    """Generate presigned PUT URLs for direct client uploads to Cloudflare R2.

    Requires the following settings (via environment variables):
        R2_ACCOUNT_ID           — Cloudflare account ID
        R2_ACCESS_KEY_ID        — R2 API token access key
        R2_SECRET_ACCESS_KEY    — R2 API token secret key
        R2_BUCKET               — bucket name (e.g. 'salon-images')
        R2_PUBLIC_URL           — public base URL (e.g. https://pub-xxx.r2.dev)

    If any of these are absent the gateway raises ValidationError (→ HTTP 422)
    so the rest of the API continues to function normally.

    The boto3 S3 client is created once per gateway instance and reused across
    requests. Client creation is protected by a threading.Lock so it is safe
    under concurrent async-to-thread dispatch.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None
        self._client_lock = threading.Lock()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _assert_configured(self) -> None:
        """Raise ValidationError if any required R2 setting is missing."""
        missing = [
            name
            for name, value in {
                "R2_ACCOUNT_ID": self.settings.r2_account_id,
                "R2_ACCESS_KEY_ID": self.settings.r2_access_key_id,
                "R2_SECRET_ACCESS_KEY": self.settings.r2_secret_access_key,
                "R2_BUCKET": self.settings.r2_bucket,
                "R2_PUBLIC_URL": self.settings.r2_public_url,
            }.items()
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValidationError(
                f"Cloudflare R2 is not fully configured. Missing: {joined}"
            )

    def _get_client(self) -> Any:
        """Return the cached boto3 S3 client, creating it on first call.

        Thread-safe: protected by a threading.Lock because this method is
        called from within the thread-pool executor.
        """
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = self._build_client()
        return self._client

    def _build_client(self) -> Any:
        """Construct a fresh boto3 S3 client pointed at the R2 endpoint.

        Called inside the thread executor — boto3 is synchronous.
        """
        import boto3  # type: ignore[import]

        endpoint = f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self.settings.r2_access_key_id,
            aws_secret_access_key=self.settings.r2_secret_access_key,
            region_name="auto",  # R2 uses 'auto' for region
        )

    def _presign_sync(self, bucket: str, path: str, content_type: str) -> str:
        """Generate a presigned PUT URL synchronously (runs in thread pool)."""
        client = self._get_client()
        url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": path,
                "ContentType": content_type,
            },
            ExpiresIn=_UPLOAD_TTL_SECONDS,
        )
        return url

    def _delete_sync(self, bucket: str, path: str) -> None:
        """Delete an object synchronously (runs in thread pool)."""
        client = self._get_client()
        client.delete_object(Bucket=bucket, Key=path)

    def _upload_sync(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        """Upload raw bytes synchronously (runs in thread pool)."""
        client = self._get_client()
        client.put_object(Bucket=bucket, Key=path, Body=data, ContentType=content_type)

    # ── StorageGateway interface ───────────────────────────────────────────────

    async def get_upload_url(
        self,
        bucket: str,
        path: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Return a presigned PUT URL the client can upload to directly.

        Args:
            bucket: R2 bucket name (e.g. 'salon-images').
            path: Object key within the bucket (e.g. 'salon-images/<salon_id>/<uuid>.jpg').
            content_type: MIME type of the upload (must match what the client sends).

        Returns:
            A presigned PUT URL valid for _UPLOAD_TTL_SECONDS seconds.
        """
        self._assert_configured()

        loop = asyncio.get_running_loop()
        try:
            url: str = await loop.run_in_executor(
                _executor,
                partial(self._presign_sync, bucket, path, content_type),
            )
        except Exception as exc:
            logger.error("R2 presign failed for path %s: %s", path, exc)
            raise ValidationError("Could not generate R2 upload URL") from exc

        return url

    def get_public_url(self, bucket: str, path: str) -> str:
        """Return the permanent public URL for a delivered R2 object.

        Args:
            bucket: Bucket name (unused for R2 public URL — the path is sufficient).
            path: Object key within the bucket.

        Returns:
            The HTTPS URL clients use to fetch the stored object.
        """
        self._assert_configured()
        base = str(self.settings.r2_public_url).rstrip("/")
        return f"{base}/{path}"

    async def delete_object(self, bucket: str, path: str) -> None:
        """Delete an object from the R2 bucket. No-op if the object does not exist.

        Dispatched to the thread executor because boto3 is synchronous.

        Args:
            bucket: R2 bucket name.
            path: Object key within the bucket.
        """
        self._assert_configured()

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                _executor,
                partial(self._delete_sync, bucket, path),
            )
        except Exception as exc:
            logger.error("R2 delete failed for path %s: %s", path, exc)
            raise ValidationError("Could not delete R2 object") from exc

    async def upload_bytes(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "image/png",
    ) -> str:
        """Upload raw bytes directly from the server to R2 and return the public URL.

        Used for server-generated content (e.g. QR code PNGs) where no presigned URL
        flow is needed.
        """
        self._assert_configured()

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                _executor,
                partial(self._upload_sync, bucket, path, data, content_type),
            )
        except Exception as exc:
            logger.error("R2 upload_bytes failed for path %s: %s", path, exc)
            raise ValidationError("Could not upload object to R2") from exc

        return self.get_public_url(bucket, path)
