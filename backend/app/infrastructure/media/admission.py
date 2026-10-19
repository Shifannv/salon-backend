"""Bound image ingress before Starlette can parse or spool multipart bodies.

Limits are deliberately process-local. Deployments with several API processes must
also enforce aggregate request/rate limits at their trusted ingress.
"""

import asyncio
import logging
import math
import time
from collections import OrderedDict
from email.message import Message

from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.types import Message as ASGIMessage

from app.core.exceptions import (
    PayloadTooLargeError,
    RequestTimeoutError,
    ServiceUnavailableError,
    TooManyRequestsError,
    UnsupportedMediaTypeError,
    app_error_response,
)

_log = logging.getLogger(__name__)
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_ADMISSION_ERRORS = {
    408: RequestTimeoutError,
    413: PayloadTooLargeError,
    415: UnsupportedMediaTypeError,
    429: TooManyRequestsError,
    503: ServiceUnavailableError,
}


class UploadAdmissionMiddleware:
    """Bound bytes, request duration, concurrency and client-IP upload attempts."""

    def __init__(
        self, app: ASGIApp, max_body_bytes: int = 5_242_880,
        multipart_overhead: int = 65_536, max_inflight: int = 4,
        rate_limit: int = 30, window_seconds: float = 60, read_timeout: float = 10,
    ) -> None:
        if min(max_body_bytes, max_inflight, rate_limit, window_seconds, read_timeout) <= 0:
            raise ValueError("Upload admission limits must be positive")
        if multipart_overhead < 0:
            raise ValueError("Multipart overhead cannot be negative")
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.multipart_overhead = multipart_overhead
        self.max_inflight = max_inflight
        self.rate_limit = rate_limit
        self.window_seconds = window_seconds
        self.read_timeout = read_timeout
        self._inflight = 0
        self._rates: OrderedDict[tuple[str, str], tuple[float, int]] = OrderedDict()

    @staticmethod
    def _kind(scope: Scope) -> str | None:
        path, method = scope.get("path", ""), scope.get("method", "")
        if method == "PUT" and path.startswith("/v1/media/uploads/"):
            return "binary"
        if method == "GET" and path.startswith("/v1/media/results/"):
            return "metadata"
        if method == "POST" and path == "/v1/customer/profile/avatar":
            return "multipart"
        if method == "POST" and (
            path == "/v1/profiles/me/avatar-upload-url"
            or path == "/v1/salons/me/images/upload-url"
            or (path.startswith("/v1/salons/me/staff/") and path.endswith("/photo-upload-url"))
        ):
            return "grant"
        return None

    def _retry_after(self, scope: Scope, kind: str) -> int:
        now = time.monotonic()
        # Expiration scans are bounded by the map's hard 1024-entry cap.
        for key, (started, _) in list(self._rates.items()):
            if now - started >= self.window_seconds:
                del self._rates[key]
        client = scope.get("client")
        key = (str(client[0]) if client else "unknown", "grant" if kind == "grant" else "upload")
        started, count = self._rates.pop(key, (now, 0))
        self._rates[key] = (started, count + 1)
        while len(self._rates) > 1024:
            self._rates.popitem(last=False)
        if count >= self.rate_limit:
            return max(1, math.ceil(self.window_seconds - (now - started)))
        return 0

    @staticmethod
    async def _reject(send: Send, status: int, detail: str, retry: int = 0) -> None:
        _log.warning("image_upload_admission_rejected", extra={"status_code": status})
        response = app_error_response(_ADMISSION_ERRORS[status](detail))
        if retry:
            response.headers["Retry-After"] = str(retry)
        await send({"type": "http.response.start", "status": response.status_code,
                    "headers": response.raw_headers})
        await send({"type": "http.response.body", "body": response.body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        kind = self._kind(scope) if scope["type"] == "http" else None
        if kind is None:
            await self.app(scope, receive, send)
            return
        retry = self._retry_after(scope, kind)
        if retry:
            await self._reject(send, 429, "Too many image upload requests", retry)
            return
        if self._inflight >= self.max_inflight:
            await self._reject(send, 503, "Image upload capacity is busy", 1)
            return
        # No await between checking and acquiring: one ASGI event-loop turn.
        self._inflight += 1
        try:
            await self._admit(scope, receive, send, kind)
        finally:
            self._inflight -= 1

    async def _admit(self, scope: Scope, receive: Receive, send: Send, kind: str) -> None:
        headers: dict[bytes, list[bytes]] = {}
        for name, value in scope.get("headers", []):
            headers.setdefault(name.lower(), []).append(value)
        lengths = headers.get(b"content-length", [])
        declared = None
        if lengths:
            if len(lengths) != 1 or not lengths[0] or any(c not in b"0123456789" for c in lengths[0]):
                await self._reject(send, 413, "Invalid image request size")
                return
            # Avoid parsing attacker-controlled arbitrarily large integers.
            if len(lengths[0]) > 20:
                await self._reject(send, 413, "Image request is too large")
                return
            declared = int(lengths[0])
        if lengths and b"transfer-encoding" in headers:
            await self._reject(send, 413, "Invalid image request size")
            return
        content_types = headers.get(b"content-type", [])
        content_type = content_types[0].decode("latin-1") if len(content_types) == 1 else ""
        media = Message()
        media["content-type"] = content_type
        if kind == "binary" and content_type.lower().strip() not in _IMAGE_TYPES:
            await self._reject(send, 415, "Upload a JPEG, PNG or WebP image")
            return
        if kind == "multipart":
            boundary = media.get_param("boundary", header="content-type")
            if (
                media.get_content_type() != "multipart/form-data"
                or not isinstance(boundary, str) or not 1 <= len(boundary) <= 70
                or any(ord(char) < 32 or ord(char) > 126 for char in boundary)
                or boundary.endswith(" ")
            ):
                await self._reject(send, 415, "A valid multipart image request is required")
                return
        limit = self.max_body_bytes + (self.multipart_overhead if kind == "multipart" else 0)
        if kind == "grant":
            limit = min(limit, 8192)
        elif kind == "metadata":
            limit = 0
        if declared is not None and declared > limit:
            await self._reject(send, 413, "Image request is too large")
            return
        body = bytearray()
        try:
            async with asyncio.timeout(self.read_timeout):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    if message["type"] != "http.request":
                        await self._reject(send, 413, "Invalid image request body")
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > limit:
                        await self._reject(send, 413, "Image request is too large")
                        return
                    body.extend(chunk)
                    if declared is not None and len(body) > declared:
                        await self._reject(send, 413, "Invalid image request size")
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await self._reject(send, 408, "Image upload request timed out")
            return
        if declared is not None and len(body) != declared:
            await self._reject(send, 413, "Invalid image request size")
            return
        replayed = False

        async def replay() -> ASGIMessage:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


# Descriptive alias for callers that prefer the longer name.
ImageUploadAdmissionMiddleware = UploadAdmissionMiddleware
