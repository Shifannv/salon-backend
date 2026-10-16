"""Child process for synthetic loopback-only Redis/PostgreSQL fault tests."""

import asyncio
import json
import os
import sys
from functools import partial

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.infrastructure.cache.redis import RedisCache, validated_cache_reads
from app.infrastructure.db.session import read_cache_snapshot


async def main():
    url = make_url(os.environ["RECOVERY_TEST_DB"])
    assert url.host == "127.0.0.1" and url.database.startswith("redis_recovery_")
    engine = create_async_engine(url, isolation_level="READ COMMITTED")
    cache = RedisCache(Redis.from_url(os.environ["RECOVERY_TEST_REDIS"],
        decode_responses=True, socket_timeout=0.3, socket_connect_timeout=0.3))
    try:
        while line := await asyncio.to_thread(sys.stdin.readline):
            cmd = json.loads(line)
            if cmd["action"] == "quit":
                break
            if cmd["action"] == "recover":
                result = {"recovered": await cache.ping()}
            else:
                # Only fixed table names and a synthetic fixture UUID cross the boundary.
                table = {"salon": "salons", "staff": "staff", "catalog": "service_categories"}[cmd["kind"]]
                async with AsyncSession(engine) as session:
                    if cmd["action"] == "mutate":
                        await session.execute(text(f"UPDATE {table} SET name=:name WHERE id=:id"),
                            {"name": "synthetic-after", "id": cmd["id"]})
                        await session.commit()
                        result = {"invalidated": await cache.invalidate_read_models()}
                    else:
                        with validated_cache_reads(partial(read_cache_snapshot, session)):
                            value = await cache.get(cmd["key"])
                            hit = value is not None
                            if not hit:
                                value = {"name": (await session.execute(text(
                                    f"SELECT name FROM {table} WHERE id=:id"
                                ), {"id": cmd["id"]})).scalar_one()}
                                await cache.set(cmd["key"], value)
                            result = {"cache_hit": hit, "value": value}
            result["safe"] = cache._read_cache_safe
            print(json.dumps(result), flush=True)
    finally:
        await cache.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
