"""Health-check API routes."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.health import DatabaseHealthResponse, HealthResponse
from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.db.session import get_session

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
async def database_health(session: AsyncSession = Depends(get_session)) -> DatabaseHealthResponse:
    """Probe the database connection."""

    try:
        await session.execute(text("select 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Database is unavailable") from exc
    return DatabaseHealthResponse(status="ok", database="reachable")
