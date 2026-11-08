"""Cache-coherence regressions; real TCP/SQL counterparts are opt-in integration tests."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.cache.redis import RedisCache, validated_cache_reads


class Store:
    def __init__(self):
        self.values = {}
        self.down = False

    def check(self):
        if self.down:
            raise ConnectionError("synthetic outage")

    async def get(self, key):
        self.check()
        return self.values.get(key)

    async def set(self, key, value):
        self.check()
        self.values[key] = value

    async def ping(self):
        self.check()
        return True

    async def delete(self, *keys):
        self.check()
        for key in keys:
            self.values.pop(key, None)

    async def scan_iter(self, match):
        self.check()
        import fnmatch
        for key in list(self.values):
            if fnmatch.fnmatch(key, match):
                yield key

    async def eval(self, script, n, epoch_key, key, epoch, ttl, value):
        self.check()
        if self.values.get(epoch_key, "initial") == epoch:
            self.values[key] = value


@pytest.mark.parametrize("key", [
    "catalog:categories:active", "catalog:subcategories:active:synthetic",
    "salon:synthetic:detail", "salon:synthetic:services", "salon:synthetic:staff",
    "walkin:qr:synthetic",
])
async def test_partitioned_writer_cannot_leave_stale_payload_for_healthy_reader(key):
    store = Store()
    writer, reader = RedisCache(store), RedisCache(store)
    snapshot = AsyncMock(return_value="db:10:10:")
    with validated_cache_reads(snapshot):
        assert await reader.get(key) is None
        await reader.set(key, {"name": "before"})
        assert await reader.get(key) == {"name": "before"}
        store.down = True
        assert await writer.invalidate_read_models() is False
        assert writer._read_cache_safe is False
        # DB commit changes the snapshot even if the writer crashes before retry.
        snapshot.return_value = "db:11:11:"
        store.down = False
        assert reader._read_cache_safe is True  # B never observed the fault.
        assert await reader.get(key) is None
        await reader.set(key, {"name": "after"})
        assert await reader.get(key) == {"name": "after"}
        assert await writer.ping() is True
        assert writer._read_cache_safe is True
        assert await reader.get(key) is None  # Retried epoch retires the generation.


async def test_disconnected_reader_recovers_before_serving_payload():
    store = Store()
    cache = RedisCache(store)
    with validated_cache_reads(AsyncMock(return_value="db:10:10:")):
        await cache.get("salon:synthetic:detail")
        await cache.set("salon:synthetic:detail", {"old": True})
        store.down = True
        assert await cache.get("salon:synthetic:detail") is None
        assert cache._read_cache_safe is False
        store.down = False
        assert await cache.get("salon:synthetic:detail") is None
        assert cache._read_cache_safe is True


async def test_unvalidated_or_failed_database_read_never_uses_cached_payload():
    store = Store()
    cache = RedisCache(store)
    key = "catalog:categories:active"
    with validated_cache_reads(AsyncMock(return_value="db:10:10:")):
        await cache.get(key)
        await cache.set(key, ["before"])
    assert await cache.get(key) is None
    for snapshot in (AsyncMock(return_value=None), AsyncMock(side_effect=TimeoutError)):
        with validated_cache_reads(snapshot):
            assert await cache.get(key) is None
            await cache.set(key, ["unsafe"])
    assert all(json.loads(v) != ["unsafe"] for v in store.values.values())


async def test_late_cache_fill_cannot_enter_new_epoch():
    store = Store()
    cache = RedisCache(store)
    key = "salon:synthetic:staff"
    with validated_cache_reads(AsyncMock(return_value="db:10:10:")):
        await cache.get(key)
        assert await cache.invalidate_read_models()
        await cache.set(key, ["late old payload"])
        assert await cache.get(key) is None


@pytest.mark.parametrize("prefix", ["availability:", "slot:", "slots:", "booking:", "bookings:"])
async def test_booking_and_availability_never_read_or_write_payload_cache(prefix):
    client = AsyncMock()
    cache = RedisCache(client)
    await cache.set(prefix + "synthetic", ["old"])
    assert await cache.get(prefix + "synthetic") is None
    client.get.assert_not_awaited()
    client.setex.assert_not_awaited()


@pytest.mark.parametrize("operation", ["delete", "delete_prefix"])
async def test_explicit_invalidation_failure_is_logged_and_retried(operation, caplog):
    store = Store()
    cache = RedisCache(store)
    store.down = True
    await getattr(cache, operation)("catalog:")
    assert not cache._read_cache_safe
    assert "invalidation retry pending" in caplog.text
    store.down = False
    assert await cache.ping()
    assert "read-model:epoch:v1" in store.values


async def test_strict_erasure_invalidation_propagates_failure():
    store = Store()
    cache = RedisCache(store)
    store.down = True
    with pytest.raises(ConnectionError):
        await cache.delete_prefix("salon:", strict=True)
    assert not cache._read_cache_safe


async def test_overlapping_request_contexts_do_not_share_cache_fill_versions():
    cache = RedisCache(Store())
    ready = asyncio.Event()
    waiting = 0
    async def request(version):
        nonlocal waiting
        with validated_cache_reads(AsyncMock(return_value=version)):
            await cache.get("salon:synthetic:detail")
            waiting += 1
            if waiting == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 2)
            await cache.set("salon:synthetic:detail", version)
            assert await cache.get("salon:synthetic:detail") == version
    await asyncio.gather(request("snapshot-a"), request("snapshot-b"))


@pytest.mark.parametrize("own_xid_absent,isolation,replica,allowed", [
    (True, "read committed", False, True),
    (False, "read committed", False, False),
    (True, "repeatable read", False, False),
    (True, "serializable", False, False),
    (True, "read committed", True, False),
])
async def test_snapshot_validation_rejects_unsafe_database_context(own_xid_absent, isolation, replica, allowed):
    from app.infrastructure.db.session import read_cache_snapshot

    result = MagicMock()
    result.one.return_value = ("synthetic", "10:10:", own_xid_absent, isolation, replica)
    session = AsyncMock()
    session.execute.return_value = result
    assert await read_cache_snapshot(session) == ("synthetic:10:10:" if allowed else None)


@pytest.mark.parametrize("reachable", [False, True])
async def test_erasure_worker_probes_retained_client_before_destructive_work(monkeypatch, reachable):
    from app.infrastructure.account_deletion import worker

    class StopLoop(Exception):
        pass
    async def stop_loop(seconds):
        raise StopLoop
    cache = AsyncMock()
    cache.available = True  # A retained client does not establish reachability.
    cache.ping.return_value = reachable
    settings = MagicMock(redis_url="redis://synthetic-only", account_deletion_worker_poll_seconds=1)
    drain, touch = AsyncMock(), MagicMock()
    monkeypatch.setattr(worker, "settings", settings)
    monkeypatch.setattr(worker, "validate_worker_configuration", lambda config: [])
    monkeypatch.setattr(worker, "init_redis_cache", AsyncMock(return_value=cache))
    monkeypatch.setattr(worker, "drain_account_deletions", drain)
    monkeypatch.setattr(worker, "redact_expired_payout_proofs", AsyncMock(return_value=0))
    monkeypatch.setattr(worker, "touch", touch)
    monkeypatch.setattr(worker.asyncio, "sleep", stop_loop)
    with pytest.raises(StopLoop):
        await worker.run_forever()
    cache.ping.assert_awaited_once()
    assert drain.await_count == int(reachable)
    assert touch.call_count == int(reachable)


async def test_startup_outage_retains_client_and_retries_epoch_after_reconnect():
    client = AsyncMock()
    client.ping.side_effect = [ConnectionError("synthetic startup outage"), True]
    with patch("redis.asyncio.from_url", return_value=client) as factory:
        cache = await RedisCache.create("redis://127.0.0.1:16479/0")
        assert cache._client is client and not cache._read_cache_safe
        assert await cache.ping()
        assert cache._read_cache_safe
        factory.assert_called_once()
        client.set.assert_awaited_once()
        await cache.close()
