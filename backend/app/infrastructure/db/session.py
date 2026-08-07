"""Async SQLAlchemy session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    connect_args={"statement_cache_size": 0} if "asyncpg" in settings.database_url else {},
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""

    async with AsyncSessionLocal() as session:
        yield session


async def set_actor_context(session: AsyncSession, actor_id: str) -> None:
    """Set the per-transaction actor consumed by Supabase-style audit triggers."""

    escaped = actor_id.replace('"', '\\"')
    await session.execute(text(f"""SET LOCAL request.jwt.claims = '{{"sub":"{escaped}"}}'"""))
