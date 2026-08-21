"""FastAPI application factory."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.api.v1.routes.health import router as health_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, set_request_id

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

    from app.infrastructure.db.session import AsyncSessionLocal, engine

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
        _log.info("Database connection pool warmed")
    except Exception:
        _log.exception("Database warm-up failed")

    yield  # Application runs here

    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""

    configure_logging()

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
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
# Trigger reload for environment variable updates
