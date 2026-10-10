"""Cloudflare R2 storage gateway — validated upload capabilities and S3 storage.

Cloudflare R2 exposes an S3-compatible endpoint at:
    https://<account_id>.r2.cloudflarestorage.com

boto3 is synchronous, so all blocking calls are dispatched to a thread-pool
executor to remain async-safe inside the FastAPI event loop.

Upload flow
-----------
1. Client calls POST /v1/salons/me/images/upload-url
2. Backend returns { upload_url, public_url, expires_in }
3. Client PUTs to the backend gateway; only decoded, processed bytes reach R2
4. Client calls POST /v1/salons/me/images with { url: public_url }
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
from io import BytesIO
from typing import Any

from PIL import Image

from app.application.ports.image_processor import ImagePolicy
from app.application.ports.storage_gateway import _UPLOAD_TTL_SECONDS, StorageGateway
from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.infrastructure.media.pillow_processor import PillowImageProcessor

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="r2")


class R2StorageGateway(StorageGateway):
    """Issue signed backend upload capabilities; never presign a public R2 PUT.

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

    def _sign(self, payload: str) -> str:
        secret = self.settings.r2_secret_access_key or ""
        return hmac.new(secret.encode(), ("image-upload-v1:" + payload).encode(), hashlib.sha256).hexdigest()

    def _processed_metadata(self, path: str, data: bytes, mime: str) -> dict[str, str]:
        self._policy(path, mime)
        with Image.open(BytesIO(data)) as image:
            dimension, pixels = max(image.size), image.width * image.height
        payload = json.dumps({"bucket": self.settings.r2_bucket, "path": path, "mime": mime, "size": len(data),
                              "sha256": hashlib.sha256(data).hexdigest(),
                              "dimension": dimension, "pixels": pixels}, sort_keys=True)
        return {"processed-image-v1": payload, "processed-signature": self._sign(payload)}

    def _verify_processed_head(self, path: str, head: dict) -> dict:
        try:
            metadata = head["Metadata"]
            payload = metadata["processed-image-v1"]
            if not hmac.compare_digest(self._sign(payload), metadata["processed-signature"]):
                raise ValueError()
            proof = json.loads(payload)
            policy = self._policy(path, proof["mime"])
            if (proof["bucket"] != self.settings.r2_bucket or proof["path"] != path or proof["mime"] != head["ContentType"]
                    or proof["size"] != head["ContentLength"]
                    or not 0 < proof["size"] <= policy.max_bytes
                    or not 0 < proof["dimension"] <= policy.max_dimension
                    or not 0 < proof["pixels"] <= self.settings.image_max_pixels):
                raise ValueError()
            return proof
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError("Photo has not passed the current image processing policy") from exc

    async def inspect_processed_object(self, path: str) -> dict:
        self._assert_configured()
        try:
            head = await asyncio.get_running_loop().run_in_executor(
                _executor, partial(self._head_sync, path),
            )
            return self._verify_processed_head(path, head)
        except Exception as exc:
            raise ValidationError("Photo is missing or has not passed image validation") from exc

    def _head_sync(self, path: str) -> dict:
        return self._get_client().head_object(Bucket=self.settings.r2_bucket, Key=path)

    def _list_sync(self, params: dict) -> dict:
        return self._get_client().list_objects_v2(**params)

    async def validate_media_reference(self, url: str, namespace: str, *, policy: ImagePolicy | None = None) -> None:
        self._assert_configured()
        prefix = f"{str(self.settings.r2_public_url).rstrip('/')}/{namespace}"
        if not url.startswith(prefix):
            raise ValidationError("Photo must use this account's validated hosted media")
        path = url[len(str(self.settings.r2_public_url).rstrip('/')) + 1:]
        if any(char in path for char in ("%", "\\", "?", "#")) or any(not part for part in path.split("/")):
            raise ValidationError("Invalid image object URL")
        proof = await self.inspect_processed_object(path)
        if policy and (proof["dimension"] > policy.max_dimension or proof["size"] > policy.max_bytes):
            raise ValidationError("Photo exceeds this media category's dimensions or size limit")

    async def cleanup_candidates(self) -> AsyncIterator[str]:
        """List aged keys; the worker must verify signed metadata before deletion."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.settings.media_cleanup_grace_seconds)
        loop = asyncio.get_running_loop()
        for prefix in ("avatars/", "salon-images/", "staff-photos/"):
            continuation = None
            while True:
                params = {"Bucket": self.settings.r2_bucket, "Prefix": prefix, "MaxKeys": 1000}
                if continuation:
                    params["ContinuationToken"] = continuation
                page = await loop.run_in_executor(_executor, partial(self._list_sync, params))
                for item in page.get("Contents", []):
                    if item["LastModified"] < cutoff:
                        yield item["Key"]
                if not page.get("IsTruncated"):
                    break
                continuation = page["NextContinuationToken"]

    def _claims(self, token: str, content_type: str) -> dict:
        self._assert_configured()
        try:
            payload, signature = token.split(".")
            if not hmac.compare_digest(self._sign(payload), signature):
                raise ValueError()
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if claims["expires"] <= time.time() or claims["mime"] != content_type:
                raise ValueError()
            if claims["bucket"] != self.settings.r2_bucket:
                raise ValueError()
            self._policy(claims["path"], content_type)
            return claims
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError("Invalid or expired image upload URL") from exc

    def _policy(self, path: str, content_type: str) -> ImagePolicy:
        extensions = {"image/jpeg": {"jpg", "jpeg"}, "image/png": {"png"}, "image/webp": {"webp"}}
        if content_type not in extensions or path.rsplit(".", 1)[-1] not in extensions[content_type]:
            raise ValidationError("Image filename and content type must agree")
        if ".." in path or "?" in path or "#" in path or path.startswith("/"):
            raise ValidationError("Invalid image object key")
        if path.startswith("avatars/"):
            return ImagePolicy(self.settings.image_avatar_dimension, self.settings.image_avatar_max_bytes)
        if path.startswith("staff-photos/"):
            return ImagePolicy(self.settings.image_staff_dimension, self.settings.image_photo_max_bytes)
        if path.startswith("salon-images/"):
            return ImagePolicy(self.settings.image_gallery_dimension, self.settings.image_photo_max_bytes)
        raise ValidationError("Unsupported media category")

    def validate_upload_token(self, token: str, content_type: str) -> None:
        self._claims(token, content_type)

    async def accept_upload(self, token: str, data: bytes, content_type: str) -> None:
        claims = self._claims(token, content_type)
        policy = self._policy(claims["path"], content_type)
        processor = PillowImageProcessor(self.settings.image_max_pixels)
        # Share the decoder pool with customer multipart uploads.
        loop = asyncio.get_running_loop()
        processed = await processor.process_async(data, content_type, policy)
        self._claims(token, content_type)
        try:
            await loop.run_in_executor(
                _executor,
                partial(self._create_image_sync, claims["bucket"], claims["path"], processed, content_type),
            )
        except Exception as exc:
            # A lost PUT response can safely retry the same content and capability.
            # Different bytes must never overwrite or delete the first upload.
            try:
                proof = await self.inspect_processed_object(claims["path"])
                if proof["sha256"] == hashlib.sha256(processed).hexdigest():
                    return
            except ValidationError:
                pass
            raise ValidationError("Image upload failed or this URL has already been used; request a new URL") from exc

    def _create_image_sync(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        self._get_client().put_object(
            Bucket=bucket, Key=path, Body=data, ContentType=content_type, IfNoneMatch="*",
            Metadata=self._processed_metadata(path, data, content_type),
        )

    def _delete_sync(self, bucket: str, path: str) -> None:
        """Delete an object synchronously (runs in thread pool)."""
        client = self._get_client()
        client.delete_object(Bucket=bucket, Key=path)

    def _upload_sync(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        """Upload raw bytes synchronously (runs in thread pool)."""
        client = self._get_client()
        # Only the avatar use case calls this with already-processed bytes.
        # Other server-generated objects are not enrolled in automated image cleanup.
        metadata = self._processed_metadata(path, data, content_type) if path.startswith("avatars/") else {}
        client.put_object(Bucket=bucket, Key=path, Body=data, ContentType=content_type,
                          Metadata=metadata, IfNoneMatch="*")

    # ── StorageGateway interface ───────────────────────────────────────────────

    async def get_upload_url(
        self,
        bucket: str,
        path: str,
        content_type: str = "image/jpeg",
    ) -> str:
        """Return a signed backend PUT URL with unchanged upload response fields.

        Args:
            bucket: R2 bucket name (e.g. 'salon-images').
            path: Object key within the bucket (e.g. 'salon-images/<salon_id>/<uuid>.jpg').
            content_type: MIME type of the upload (must match what the client sends).

        Returns:
            A signed backend PUT URL valid for _UPLOAD_TTL_SECONDS seconds.
        """
        self._assert_configured()

        self._policy(path, content_type)
        if bucket != self.settings.r2_bucket:
            raise ValidationError("Invalid upload bucket")
        origin = self.settings.public_api_base_url
        if not origin:
            raise ValidationError("PUBLIC_API_BASE_URL is required for validated image uploads")
        claims = {"bucket": bucket, "path": path, "mime": content_type,
                  "expires": int(time.time()) + _UPLOAD_TTL_SECONDS}
        payload = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).decode().rstrip("=")
        return f"{str(origin).rstrip('/')}/v1/media/uploads/{payload}.{self._sign(payload)}"

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
