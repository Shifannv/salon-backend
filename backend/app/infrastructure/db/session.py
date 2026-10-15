"""Async SQLAlchemy session management."""

import ssl
import time
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.telemetry import install_database_metrics, metrics


def build_engines(config):
    """Share one pool; idle connections ping without a throwaway transaction.

    EVERY business session binds the READ COMMITTED engine. Only SELECT 1 probes
    use the base autocommit engine. Option engines share pool/disposal and restore
    isolation on return; no booking/payment transaction uses autocommit.
    """
    connect_args = {}
    if "asyncpg" in config.database_url:
        connect_args = {"statement_cache_size": 0, "timeout": config.db_connect_timeout_seconds}
        if getattr(config, "db_ssl_ca_file", None):
            tls = ssl.create_default_context(cafile=config.db_ssl_ca_file)
            if not getattr(config, "db_ssl_strict", True):
                if config.environment != "staging":
                    raise ValueError("Legacy CA compatibility is restricted to staging")
                # Supabase's published CA lacks the keyUsage extension required by
                # Python 3.13+ strict mode. Certificate/hostname checks remain on.
                tls.verify_flags &= ~ssl.VERIFY_X509_STRICT
            connect_args["ssl"] = tls
    pool = create_async_engine(
        config.database_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True,
        pool_size=config.db_pool_size, max_overflow=config.db_max_overflow,
        pool_timeout=config.db_pool_timeout_seconds,
        pool_recycle=config.db_pool_recycle_seconds, hide_parameters=True,
        connect_args=connect_args,
    )
    install_database_metrics(pool)
    return pool, pool.execution_options(isolation_level="READ COMMITTED")


class MeasuredAsyncSession(AsyncSession):
    async def commit(self) -> None:
        await super().commit()
        # Commit first: a reader must never cache old DB state in the new epoch.
        # All API and background-worker sessions share this session factory.
        from app.infrastructure.cache.redis import get_redis_cache
        await get_redis_cache().invalidate_read_models()

    async def execute(self, *args, **kwargs):
        if not self.in_transaction():
            started = time.perf_counter()
            try:
                await self.connection()
            finally:
                if (current := metrics.get()) is not None:
                    current.database_acquire_ms += (time.perf_counter()-started)*1000
        return await super().execute(*args, **kwargs)


_pool_engine, engine = build_engines(settings)
AsyncSessionLocal = async_sessionmaker(engine, class_=MeasuredAsyncSession, expire_on_commit=False)
_ProbeSessionLocal = async_sessionmaker(_pool_engine, class_=MeasuredAsyncSession, expire_on_commit=False)


async def get_probe_session() -> AsyncGenerator[AsyncSession, None]:
    """Real read-only reachability probe; shares the application connection pool."""
    async with _ProbeSessionLocal() as session:
        yield session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""

    async with AsyncSessionLocal() as session:
        yield session


async def set_actor_context(session: AsyncSession, actor_id: str) -> None:
    """Set the per-transaction actor consumed by Supabase-style audit triggers.

    Supabase's ``auth.uid()`` reads ``current_setting('request.jwt.claim.sub', true)``
    (singular, flat). PostgREST policies read the JSON blob from
    ``request.jwt.claims`` (plural). We set both so that:

    - ``auth.uid()``  used by the ``set_audit_actor`` trigger returns the right UUID
    - Row-level security policies that inspect claims work the same way
    """

    escaped = actor_id.replace('"', '\\"')
    await session.execute(
        text(
            f"""
            SELECT set_config('request.jwt.claims', '{{"sub":"{escaped}"}}', true),
                   set_config('request.jwt.claim.sub', '{escaped}', true)
            """
        )
    )
