"""Read-only DB transport/transaction profiling; run inside the target API container.

Uses the application's existing engine; prints no URL, credential, row data or SQL text.
This separate diagnostic process has its own application pool; HTTP benchmarks measure
the running API pool independently. Only SELECT 1, EXPLAIN SELECT 1 and aggregate stats run.
"""
import asyncio
import json
import socket
import time

from sqlalchemy import event, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.infrastructure.db.session import AsyncSessionLocal, engine


async def main():
    report = {"new_connections": 0, "sessions": [], "held_connection_queries_ms": []}
    @event.listens_for(engine.sync_engine, "connect")
    def connected(*args):
        report["new_connections"] += 1
    url = make_url(settings.database_url)
    started = time.perf_counter()
    addresses = await asyncio.get_running_loop().getaddrinfo(url.host, url.port or 5432, type=socket.SOCK_STREAM)
    report["dns_ms"] = (time.perf_counter()-started)*1000
    report["address_families"] = sorted({"IPv6" if a[0] == socket.AF_INET6 else "IPv4" for a in addresses})
    report["tcp_ms"] = []
    for _ in range(5):
        started = time.perf_counter()
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(url.host, url.port or 5432),10)
        report["tcp_ms"].append((time.perf_counter()-started)*1000)
        writer.close()
        await writer.wait_closed()
    for i in range(15):
        s = AsyncSessionLocal()
        started = time.perf_counter()
        await s.connection()
        checkout = time.perf_counter()
        await s.execute(text("select 1"))
        executed = time.perf_counter()
        await s.close()
        ended = time.perf_counter()
        report["sessions"].append({"iteration": i, "checkout_ms":(checkout-started)*1000,
            "begin_and_query_ms":(executed-checkout)*1000,"rollback_ms":(ended-executed)*1000})
    async with engine.connect() as conn:
        for _ in range(10):
            started = time.perf_counter()
            await conn.execute(text("select 1"))
            report["held_connection_queries_ms"].append((time.perf_counter()-started)*1000)
        report["plan"] = list((await conn.execute(text("explain (analyze, buffers, format text) select 1"))).scalars())
        report["connection_states"] = [dict(r) for r in (await conn.execute(text("select state,count(*) as connections from pg_stat_activity group by state"))).mappings()]
        report["max_connections"] = (await conn.execute(text("show max_connections"))).scalar_one()
    report["pool_after"] = engine.pool.status()
    print(json.dumps(report,indent=2))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
