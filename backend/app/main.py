"""FastAPI application factory."""

import asyncio
import contextlib
import gc
import logging
import os
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager


def _prefetch_env_file() -> None:
    with contextlib.suppress(OSError), open(os.environ.get("SALON_ENV_FILE", ".env"), "rb") as handle:
        handle.read()


# On Cloud Run the env file is a Secret Manager volume whose first read takes about
# 0.3 s. Start that read now so it overlaps the imports below; settings load reads
# the file again shortly after, when it is already fetched. Contents are discarded.
threading.Thread(target=_prefetch_env_file, name="env-prefetch", daemon=True).start()

# Importing the framework and building the app create hundreds of thousands of
# long-lived objects; collecting garbage while they are created costs about 5-10% of
# startup. Collection is paused here and resumed once the app is built (end of file).
gc.disable()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.api.v1.routes.health import router as health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.telemetry import TimingMiddleware, init_sentry

_log = logging.getLogger(__name__)


async def _warm_database() -> None:
    from sqlalchemy import text

    from app.infrastructure.db.session import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
        _log.info("Database connection pool warmed")
    except Exception:
        _log.exception("Database warm-up failed")


async def _init_cache() -> None:
    from app.infrastructure.cache.redis import init_redis_cache

    try:
        await init_redis_cache(settings.redis_url)
    except Exception:
        _log.exception("Redis cache initialization failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and graceful shutdown.

    On startup: warm the remote database connection pool so the first customer
    request does not pay the Supabase connection setup cost, and connect Redis.
    The two are independent, so they run concurrently to shorten cold start; each
    logs its own failure without stopping the other.
    On shutdown: dispose the SQLAlchemy engine connection pool so no
    in-flight connections are left dangling.
    """

    from app.infrastructure.cache.redis import close_redis_cache
    from app.infrastructure.db.session import engine

    await asyncio.gather(_warm_database(), _init_cache())

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

# Resume collection. freeze() moves the startup objects out of the tracked
# generations, so later collections do not rescan them. Startup leaves under 1,000
# unreachable objects, which freeze keeps; freeing them would cost a ~70 ms collection.
gc.enable()
gc.freeze()
