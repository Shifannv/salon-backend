"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.api.v1.routes.health import router as health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.telemetry import TimingMiddleware, init_sentry
from app.infrastructure.media.admission import UploadAdmissionMiddleware

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and graceful shutdown.

    On startup: warm the remote database connection pool so the first customer
    request does not pay the Supabase connection setup cost.
    On shutdown: dispose the SQLAlchemy engine connection pool so no
    in-flight connections are left dangling.
    """

    from sqlalchemy import text

    from app.infrastructure.cache.redis import close_redis_cache, init_redis_cache
    from app.infrastructure.db.session import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
        _log.info("Database connection pool warmed")
    except Exception:
        _log.exception("Database warm-up failed")

    try:
        await init_redis_cache(settings.redis_url)
    except Exception:
        _log.exception("Redis cache initialization failed")

    yield  # Application runs here

    await close_redis_cache()
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""

    configure_logging()
    sentry_enabled = init_sentry(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Last registered runs outermost: timing -> CORS -> admission -> routing.
    # Reject bodies before parsing while keeping the normal response wrappers.
    app.add_middleware(UploadAdmissionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-ID middleware — stamps every request/response with a correlation ID.
    app.add_middleware(TimingMiddleware, environment=settings.environment, sentry_enabled=sentry_enabled)

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
# Trigger reload for environment variable updates
