"""Request metrics and conservative error-reporting sanitization."""

import re
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

import structlog

from app.core.logging import set_request_id


@dataclass
class RequestMetrics:
    database_duration_ms: float = 0
    database_query_count: int = 0
    error_code: str | None = None
    redis_duration_ms: float = 0
    cache_reads: int = 0
    cache_hits: int = 0


metrics: ContextVar[RequestMetrics | None] = ContextVar("request_metrics", default=None)
_log = structlog.get_logger("api.timing")
_REQUEST_ID = re.compile(r"[a-zA-Z0-9_-]{1,64}\Z")


def scrub_sentry(event, hint=None):
    """Retain timing and stack locations, discard submitted data and exception values."""
    for key in ("user", "extra", "request", "breadcrumbs", "logentry", "message"):
        event.pop(key, None)
    event["contexts"] = {k: v for k, v in event.get("contexts", {}).items() if k == "trace"}
    event["tags"] = {k: v for k, v in event.get("tags", {}).items() if k in {"environment", "request_id", "route"}}
    for value in event.get("exception", {}).get("values", []):
        value["value"] = "Backend error (details withheld)"
        for frame in value.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    for span in event.get("spans", []):
        span.pop("data", None)
        span["description"] = span.get("op", "operation")
    return event


def init_sentry(settings):
    if not settings.sentry_dsn or not settings.sentry_dsn.get_secret_value():
        return False
    import sentry_sdk
    sentry_sdk.init(dsn=settings.sentry_dsn.get_secret_value(), environment=settings.environment,
                    send_default_pii=False, include_local_variables=False,
                    traces_sample_rate=settings.sentry_traces_sample_rate,
                    before_send=scrub_sentry, before_send_transaction=scrub_sentry,
                    before_breadcrumb=lambda breadcrumb, hint: None)
    return True


class TimingMiddleware:
    def __init__(self, app, environment, sentry_enabled=False):
        self.app = app
        self.environment = environment
        self.sentry_enabled = sentry_enabled

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        current = RequestMetrics()
        token = metrics.set(current)
        started = time.perf_counter()
        supplied = dict(scope.get("headers", [])).get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        set_request_id(request_id)
        status_code, response_ms = 500, None

        async def timed_send(message):
            nonlocal status_code, response_ms
            if message["type"] == "http.response.start":
                if self.sentry_enabled:
                    import sentry_sdk
                    sentry_sdk.set_tag("route", getattr(scope.get("route"), "path", "unmatched"))
                status_code = message["status"]
                response_ms = (time.perf_counter() - started) * 1000
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode()))
                if self.environment in {"local", "test", "staging"}:
                    headers.append((b"server-timing", f"app;dur={response_ms:.2f}, db;dur={current.database_duration_ms:.2f}, queries;desc=\"{current.database_query_count}\"".encode()))
                    if current.cache_reads:
                        headers.append((b"x-cache-reads", str(current.cache_reads).encode()))
                        headers.append((b"x-cache-hits", str(current.cache_hits).encode()))
                message["headers"] = headers
            await send(message)

        try:
            if self.sentry_enabled:
                import sentry_sdk
                with sentry_sdk.isolation_scope() as sentry_scope:
                    sentry_scope.set_tag("request_id", request_id)
                    await self.app(scope, receive, timed_send)
            else:
                await self.app(scope, receive, timed_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            _log.info("api_request", request_id=request_id, route=route, method=scope["method"],
                      status_code=status_code, duration_ms=round(response_ms if response_ms is not None else (time.perf_counter() - started) * 1000, 3),
                      database_duration_ms=round(current.database_duration_ms, 3),
                      database_query_count=current.database_query_count,
                      cache_hit=bool(current.cache_hits) if current.cache_reads else None,
                      redis_duration_ms=round(current.redis_duration_ms,3),
                      error_code=current.error_code, environment=self.environment)
            metrics.reset(token)
            set_request_id("")


def install_database_metrics(engine):
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._metrics_start = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        current = metrics.get()
        if current is not None:
            current.database_query_count += 1
            current.database_duration_ms += (time.perf_counter() - context._metrics_start) * 1000
