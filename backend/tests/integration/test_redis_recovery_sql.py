"""Real independent processes, TCP partitions and committed disposable PostgreSQL data."""

import asyncio
import json
import os
import socket
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.deps import get_authenticated_session, get_current_actor, get_session
from app.infrastructure.cache import redis as cache_module
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.db.session import (
    MeasuredAsyncSession,
    read_cache_snapshot,
    set_actor_context,
)
from app.main import create_app
from tests.conftest import make_profile
from tests.integration.test_checkout_safety_sql import SafetyEnv
from tests.integration.test_payment_ledger_sql import TEST_DB, _build, _drop

REDIS_URL = os.environ.get("RECOVERY_TEST_REDIS")
pytestmark = pytest.mark.skipif(not TEST_DB or not REDIS_URL,
    reason="Requires disposable loopback PostgreSQL and Redis")


@pytest.fixture(scope="module")
def recovery_db():
    database = "redis_recovery_" + uuid4().hex
    asyncio.run(_build(database, revision="0037_customer_processing_charge"))
    try:
        yield make_url(TEST_DB).set(database=database, drivername="postgresql+asyncpg").render_as_string(hide_password=False)
    finally:
        asyncio.run(_drop(database))


@pytest.fixture
async def recovery(recovery_db):
    url = make_url(REDIS_URL)
    assert url.host == "127.0.0.1" and url.port == 16479
    env = SafetyEnv(recovery_db)
    fixture = await env.seed()
    category = (await env.sql("select category_id from service_subcategories where id=(select subcategory_id from services where id=:id)", id=fixture["service"]))[0]["category_id"]
    fixture["catalog"] = str(category)
    cache = RedisCache(Redis.from_url(REDIS_URL, decode_responses=True,
        socket_timeout=0.3, socket_connect_timeout=0.3))
    try:
        yield env, fixture, cache
    finally:
        await cache.close()
        await env.engine.dispose()


class Gate:
    """Drop commands before Redis receives them; never pause a command queue."""

    def __init__(self):
        self.blocked = False
        self.writers = set()
        self.tasks = set()

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        self.url = f"redis://127.0.0.1:{self.server.sockets[0].getsockname()[1]}/0"
        return self

    def cut(self):
        self.blocked = True
        for writer in list(self.writers):
            writer.close()

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        upstream = None
        transfers = []
        async def forward(source, target):
            while chunk := await source.read(65536):
                target.write(chunk)
                await target.drain()
        try:
            if self.blocked:
                return
            remote, upstream = await asyncio.open_connection("127.0.0.1", 16479)
            self.writers.update((writer, upstream))
            transfers = [asyncio.create_task(forward(reader, upstream)),
                asyncio.create_task(forward(remote, writer))]
            await asyncio.wait(transfers, return_when=asyncio.FIRST_COMPLETED)
        except (ConnectionError, OSError):
            return
        finally:
            for transfer in transfers:
                transfer.cancel()
            await asyncio.gather(*transfers, return_exceptions=True)
            for stream in (writer, upstream):
                if stream is not None:
                    self.writers.discard(stream)
                    stream.close()
            self.tasks.discard(task)

    async def __aexit__(self, *args):
        self.server.close()
        await self.server.wait_closed()
        self.cut()
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*list(self.tasks), return_exceptions=True)


async def worker(db, redis_url):
    environment = {k: v for k, v in os.environ.items() if k.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE",
        "LOCALAPPDATA", "APPDATA", "COMSPEC",
    }}
    environment.update(RECOVERY_TEST_DB=db, RECOVERY_TEST_REDIS=redis_url,
        SALON_ENV_FILE="__no_environment_file__", ENVIRONMENT="test", DATABASE_URL=db)
    return await asyncio.create_subprocess_exec(sys.executable, "-m",
        "tests.integration.cache_recovery_worker", env=environment,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)


async def ask(process, **command):
    process.stdin.write((json.dumps(command) + "\n").encode())
    await process.stdin.drain()
    line = await asyncio.wait_for(process.stdout.readline(), 15)
    assert line, (await process.stderr.read()).decode()[-1500:]
    return json.loads(line)


@pytest.mark.parametrize("kind,suffix", [
    ("salon", "detail"), ("salon", "services"), ("staff", "staff"), ("catalog", "categories"),
])
@pytest.mark.parametrize("fault", ["both", "writer_only", "writer_exits"])
async def test_two_processes_mutation_outage_reconnect_never_returns_stale(recovery, recovery_db, kind, suffix, fault):
    _, fixture, _ = recovery
    key = f"salon:{fixture['salon']}:{suffix}" if kind != "catalog" else "catalog:categories:active"
    command = {"key": key, "kind": kind, "id": fixture["salon" if kind == "salon" else kind]}
    async with Gate() as gate_a, Gate() as gate_b:
        a = await worker(recovery_db, gate_a.url)
        b = await worker(recovery_db, gate_b.url)
        try:
            initial = await ask(b, action="read", **command)
            # An unrelated PostgreSQL commit may conservatively cause another miss.
            for _ in range(5):
                warmed = await ask(b, action="read", **command)
                if warmed["cache_hit"]:
                    break
            assert warmed["cache_hit"], "Precondition: a real cached payload must exist"
            gate_a.cut()
            if fault == "both":
                gate_b.cut()
            mutation = await ask(a, action="mutate", **command)
            assert mutation == {"invalidated": False, "safe": False}
            if fault == "both":
                assert not (await ask(b, action="read", **command))["safe"]
            if fault == "writer_exits":
                a.kill()
                await a.wait()
            # B reads FIRST: neither writer recovery nor a global flush can hide the bug.
            gate_b.blocked = False
            recovered = await ask(b, action="read", **command)
            assert recovered["value"] == {"name": "synthetic-after"}
            assert recovered["value"] != initial["value"] and not recovered["cache_hit"]
            assert (await ask(b, action="read", **command))["cache_hit"]
            if fault != "writer_exits":
                gate_a.blocked = False
                assert (await ask(a, action="recover"))["recovered"]
                assert not (await ask(b, action="read", **command))["cache_hit"]
        finally:
            for process in (a, b):
                if process.returncode is None:
                    process.stdin.write(b'{"action":"quit"}\n')
                    await process.stdin.drain()
                    await asyncio.wait_for(process.wait(), 15)


async def test_snapshot_changes_on_commit_with_older_transaction_still_open(recovery):
    env, fixture, _ = recovery
    async with env.session() as old, env.session() as reader, env.session() as writer:
        await old.execute(text("select pg_current_xact_id()"))
        before = await read_cache_snapshot(reader)
        await writer.execute(text("update salons set name='synthetic-after' where id=:id"), {"id": fixture["salon"]})
        during = await read_cache_snapshot(reader)
        await writer.commit()
        after = await read_cache_snapshot(reader)
        assert before != after and during != after
        assert await read_cache_snapshot(old) is None  # Own XID cannot validate payloads.


@pytest.mark.parametrize("source", ["app", "qr"])
async def test_concurrent_http_booking_and_idempotent_retry_during_redis_outage(recovery, monkeypatch, source):
    env, f, _ = recovery
    app = create_app()
    actor = make_profile(f["customer"])
    qr = (await env.sql("select qr_token from salons where id=:id", id=f["salon"]))[0]["qr_token"]
    endpoint = "/v1/bookings" if source == "app" else f"/v1/walkin/{qr}/bookings"
    sessions = async_sessionmaker(env.engine, class_=MeasuredAsyncSession, expire_on_commit=False)
    from app.infrastructure.db import session as session_module
    from app.infrastructure.push import outbox_worker
    monkeypatch.setattr(session_module, "AsyncSessionLocal", sessions)
    monkeypatch.setattr(outbox_worker, "AsyncSessionLocal", sessions)
    pids = set()
    entered = 0
    ready = asyncio.Event()
    async def authenticated_session():
        nonlocal entered
        async with sessions() as db:
            await set_actor_context(db, actor.id)
            pids.add((await db.execute(text("select pg_backend_pid()"))).scalar_one())
            entered += 1
            if entered == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 10)
            yield db
    async def session():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_authenticated_session] = authenticated_session
    async with Gate() as gate:
        cache = RedisCache(Redis.from_url(gate.url, decode_responses=True,
            socket_timeout=0.3, socket_connect_timeout=0.3))
        monkeypatch.setattr(cache_module, "_cache_instance", cache)
        gate.cut()
        body = {k: v for k, v in env.values(f).items() if k not in {"actor_id", "_idempotency_key"}}
        body["start_datetime"] = f["start"].isoformat()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://local.test") as client:
                responses = await asyncio.gather(*[
                    client.post(endpoint, json=body, headers={"Idempotency-Key": key, "X-Request-ID": "recovery-concurrent"})
                    for key in ("synthetic-a", "synthetic-b")])
                assert sorted(r.status_code for r in responses) == [201, 409]
                assert len(pids) == 2  # Both sessions held separate connections before either wrote.
                winner = next(r for r in responses if r.status_code == 201)
                notifications_before = await env.sql(
                    "select id from notifications where booking_id=:id", id=winner.json()["id"])
                assert notifications_before, "The original booking must create a notification"
                retry = await client.post(endpoint, json=body, headers={
                    "Idempotency-Key": winner.request.headers["Idempotency-Key"], "X-Request-ID": "recovery-retry"})
                assert retry.status_code == 201 and retry.json()["id"] == winner.json()["id"]
                assert "_idempotency_replay" not in retry.json()
                assert await env.sql("select id from notifications where booking_id=:id",
                    id=winner.json()["id"]) == notifications_before
                changed = await client.post(endpoint, json={**body, "customer_name": "Different synthetic name"},
                    headers={"Idempotency-Key": winner.request.headers["Idempotency-Key"]})
                assert changed.status_code == 409 and changed.json()["error"]["code"] == "idempotency_key_reuse"
                assert not cache._read_cache_safe
                gate.blocked = False
                reconnect_started = time.perf_counter()
                assert await cache.ping()
                reconnect_ms = (time.perf_counter() - reconnect_started) * 1000
                slots = await client.get("/v1/availability", params={"staff_id": f["staff"],
                    "date": f["start"].date().isoformat(), "service_ids": f["service"]})
                assert slots.status_code == 200
                assert all(slot["slot_start"] != winner.json()["start_datetime"] for slot in slots.json())
                for response in [*responses, retry]:
                    assert response.headers["x-request-id"] == response.request.headers["X-Request-ID"]
                    assert "server-timing" in response.headers
            count = (await env.sql("select count(*) as n from bookings where customer_id=:id", id=f["customer"]))[0]["n"]
            assert count == 1
            artifact = Path(".artifacts/redis-recovery")
            artifact.mkdir(parents=True, exist_ok=True)
            artifact.joinpath(f"booking-{source}-latency.json").write_text(json.dumps({
                "scope": "loopback; dropped TCP commands; synthetic data",
                "concurrent_statuses": sorted(r.status_code for r in responses),
                "concurrent_requests_ms": [r.elapsed.total_seconds() * 1000 for r in responses],
                "outage_duplicate_retry_ms": retry.elapsed.total_seconds() * 1000,
                "reconnect_ms": reconnect_ms,
                "independent_postgres_connections": len(pids),
            }, indent=2))
        finally:
            await cache.close()


@pytest.mark.parametrize("kind", ["salon", "catalog", "staff", "services"])
async def test_public_http_and_playwright_refresh_after_lost_invalidation(recovery, monkeypatch, kind):
    import uvicorn
    from starlette.responses import HTMLResponse

    env, f, reader = recovery
    table, identifier, endpoint = {
        "salon": ("salons", f["salon"], f"/v1/salons/{f['salon']}"),
        "catalog": ("service_categories", f["catalog"], "/v1/catalog/categories"),
        "staff": ("staff", f["staff"], f"/v1/salons/{f['salon']}/staff"),
        "services": ("services", f["service"], f"/v1/salons/{f['salon']}/services"),
    }[kind]
    app = create_app()
    sessions = async_sessionmaker(env.engine, class_=MeasuredAsyncSession, expire_on_commit=False)
    async def session():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_session] = session
    monkeypatch.setattr(cache_module, "_cache_instance", reader)
    hits = []
    real_get = reader.get
    async def observed_get(key):
        result = await real_get(key)
        hits.append(result is not None)
        return result
    monkeypatch.setattr(reader, "get", observed_get)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://local.test") as client:
        timings = []
        for _ in range(12):
            started = time.perf_counter()
            response = await client.get(endpoint, headers={"X-Request-ID": "recovery-cache-read"})
            timings.append((time.perf_counter() - started) * 1000)
            assert response.status_code == 200, response.text
            assert response.headers["x-request-id"] == "recovery-cache-read"
            assert "server-timing" in response.headers
        assert hits[0] is False and any(hits[1:])
        before = response.json()

    # Only a local fixture page is served; no frontend repository or remote service is changed.
    async def browser_app(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/__recovery_test":
            html = "<pre id='result'>loading</pre><script>fetch(" + json.dumps(endpoint) + ").then(r=>r.json()).then(v=>document.querySelector('#result').textContent=JSON.stringify(v))</script>"
            return await HTMLResponse(html)(scope, receive, send)
        await app(scope, receive, send)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(browser_app, lifespan="off", log_level="error"))
    serving = asyncio.create_task(server.serve(sockets=[sock]))
    for _ in range(100):
        if server.started:
            break
        if serving.done():
            await serving
        await asyncio.sleep(0.02)
    assert server.started
    # The Node runner uses installed Playwright; it pauses while Python commits the mutation.
    browser = await asyncio.create_subprocess_exec("node", "tests/integration/redis_recovery_browser.cjs",
        f"http://127.0.0.1:{port}/__recovery_test", stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        assert json.loads(await asyncio.wait_for(browser.stdout.readline(), 20))["before"] == before
        async with Gate() as gate:
            writer = RedisCache(Redis.from_url(gate.url, decode_responses=True,
                socket_timeout=0.3, socket_connect_timeout=0.3))
            gate.cut()
            monkeypatch.setattr(cache_module, "_cache_instance", writer)
            try:
                async with sessions() as db:
                    await db.execute(text(f"UPDATE {table} SET name='synthetic-after' WHERE id=:id"), {"id": identifier})
                    await db.commit()
                assert not writer._read_cache_safe
                monkeypatch.setattr(cache_module, "_cache_instance", reader)
                browser.stdin.write(b"refresh\n")
                await browser.stdin.drain()
                browser.stdin.close()
                result = json.loads(await asyncio.wait_for(browser.stdout.readline(), 20))
                after = result["after"]
                assert after != before
                row = after if kind == "salon" else next(item for item in after if item["id"] == identifier)
                assert row["name"] == "synthetic-after"
                assert not hits[-1]  # Real get_cache dependency bound the database validator.
                assert await asyncio.wait_for(browser.wait(), 15) == 0, (await browser.stderr.read()).decode()
                gate.blocked = False
                assert await writer.ping()
            finally:
                await writer.close()
        artifact = Path(".artifacts/redis-recovery")
        artifact.mkdir(parents=True, exist_ok=True)
        artifact.joinpath(f"{kind}-latency.json").write_text(json.dumps({
            "scope": "loopback API; synthetic disposable DB; browser fixture page",
            "samples": len(timings), "cold_ms": timings[0],
            "warm_p50_ms": sorted(timings[1:])[5], "warm_p95_ms": max(timings[1:]),
            "browser_refresh": "passed", "request_id_and_timing_headers": "passed",
        }, indent=2))
    finally:
        if browser.returncode is None:
            browser.kill()
            await browser.wait()
        server.should_exit = True
        await asyncio.wait_for(serving, 10)
        sock.close()


async def test_independent_customers_compete_for_same_slot_without_serialized_fixture(recovery):
    from app.core.exceptions import AppError
    from app.infrastructure.db.repositories.platform_repository import PlatformRepository

    env, fixture, _ = recovery
    other = await env.seed()
    ready = asyncio.Event()
    pids = set()
    async def book(customer):
        async with env.session() as session:
            await set_actor_context(session, customer)
            pids.add((await session.execute(text("select pg_backend_pid()"))).scalar_one())
            if len(pids) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 10)
            try:
                return await PlatformRepository(session).create_booking(env.values(
                    {**fixture, "customer": customer}, key="synthetic-slot-race"))
            except AppError as error:
                return error
    results = await asyncio.gather(book(fixture["customer"]), book(other["customer"]))
    assert len(pids) == 2
    assert sum(isinstance(result, dict) for result in results) == 1
    assert next(result for result in results if isinstance(result, AppError)).status_code == 409
    assert (await env.sql("select count(*) as n from bookings where staff_id=:id", id=fixture["staff"]))[0]["n"] == 1
