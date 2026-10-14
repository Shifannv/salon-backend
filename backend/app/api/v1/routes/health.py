"""Health-check API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cache
from app.api.v1.schemas.health import DatabaseHealthResponse, HealthResponse, RedisHealthResponse
from app.application.ports.cache_gateway import CacheGateway
from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.db.session import get_probe_session

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Check API process health",
)
async def health() -> HealthResponse:
    """Return process health."""

    return HealthResponse(status="ok")


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Check database connectivity",
)
async def database_health(session: AsyncSession = Depends(get_probe_session)) -> DatabaseHealthResponse:
    """Probe the database connection."""

    try:
        await session.execute(text("select 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Database is unavailable") from exc
    return DatabaseHealthResponse(status="ok", database="reachable")


@router.get(
    "/health/redis",
    response_model=RedisHealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Check Redis cache connectivity",
)
async def redis_health(cache: CacheGateway = Depends(get_cache)) -> RedisHealthResponse:
    """Probe the Redis cache connection."""

    if not cache.available:
        return RedisHealthResponse(status="disabled", redis="not configured")
    is_alive = await cache.ping()
    if not is_alive:
        raise ServiceUnavailableError("Redis is unavailable")
    return RedisHealthResponse(status="ok", redis="reachable")


@router.get("/health/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK, tags=["health"])
async def readiness(session: AsyncSession = Depends(get_probe_session), cache: CacheGateway = Depends(get_cache)) -> HealthResponse:
    from app.core.config import settings
    try:
        await session.execute(text("select 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Database is unavailable") from exc
    if settings.redis_url and (not cache.available or not await cache.ping()):
        raise ServiceUnavailableError("Redis is unavailable")
    return HealthResponse(status="ok")
