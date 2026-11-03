"""Baseline response headers for a JSON API. Pure ASGI, so it adds no per-request overhead of note."""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

_ALWAYS = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
)
_HSTS = (b"strict-transport-security", b"max-age=31536000")


class SecurityHeadersMiddleware:
    """Add anti-sniffing, referrer and HSTS headers, and keep authenticated responses out of shared caches.

    A header a route already set is left alone. HSTS is skipped for local and test runs, which use
    plain HTTP.
    """

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]], environment: str = "local") -> None:
        self.app = app
        self.hsts = environment not in {"local", "test"}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authenticated = any(name == b"authorization" for name, _ in scope.get("headers", []))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                extra = list(_ALWAYS)
                if self.hsts:
                    extra.append(_HSTS)
                if authenticated:
                    extra.append((b"cache-control", b"no-store"))
                headers.extend((name, value) for name, value in extra if name not in present)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
