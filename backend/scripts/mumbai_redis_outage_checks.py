"""Two real processes exercising the runtime cache against isolated local Redis.

This tests cache invalidation itself, not committed multi-process DB mutations.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from mumbai_acceptance_checks import redis_control

BACKEND = Path(__file__).resolve().parents[1]


async def worker():
    sys.path.insert(0, str(BACKEND))
    from app.infrastructure.cache.redis import RedisCache

    port = int(sys.argv[sys.argv.index("--port") + 1])
    cache = await RedisCache.create(f"redis://127.0.0.1:{port}/0")
    if not await cache.ping():
        raise RuntimeError("Isolated Redis unavailable before test")
    try:
        while line := await asyncio.to_thread(sys.stdin.readline):
            command = json.loads(line)
            if command["action"] == "quit":
                break
            key = command["key"]
            if command["action"] == "warm":
                await cache.get(key)
                await cache.set(key, {"synthetic": "before-mutation"})
            elif command["action"] == "invalidate":
                await cache.invalidate_read_models()
            value = await cache.get(key)
            print(json.dumps({"miss": value is None,
                "cached_old": value == {"synthetic": "before-mutation"},
                "cache_safe": cache._read_cache_safe}), flush=True)
    finally:
        await cache.close()


async def main():
    children = []
    gates = []
    report = {"scope": "runtime cache layer; no database writes",
        "processes": 2, "redis_host": "127.0.0.1", "redis_port": 16391}
    key = "salon:synthetic-outage:" + uuid4().hex

    async def gate():
        state = {"blocked": False, "writers": set(), "tasks": set()}

        async def forward(reader, writer):
            while chunk := await reader.read(65536):
                writer.write(chunk)
                await writer.drain()

        async def handle(reader, writer):
            state["tasks"].add(asyncio.current_task())
            upstream = None
            transfers = []
            try:
                if state["blocked"]:
                    return
                remote, upstream = await asyncio.open_connection("127.0.0.1", 16391)
                state["writers"].update((writer, upstream))
                transfers = [asyncio.create_task(forward(reader, upstream)),
                    asyncio.create_task(forward(remote, writer))]
                await asyncio.wait(transfers, return_when=asyncio.FIRST_COMPLETED)
            except (ConnectionError, OSError):
                return
            finally:
                for task in transfers:
                    task.cancel()
                await asyncio.gather(*transfers, return_exceptions=True)
                for stream in (writer, upstream):
                    if stream is not None:
                        state["writers"].discard(stream)
                        stream.close()
                state["tasks"].discard(asyncio.current_task())

        state["server"] = await asyncio.start_server(handle, "127.0.0.1", 0)
        state["port"] = state["server"].sockets[0].getsockname()[1]
        gates.append(state)
        return state

    async def ask(process, action):
        process.stdin.write((json.dumps({"action": action, "key": key}) + "\n").encode())
        await process.stdin.drain()
        line = await asyncio.wait_for(process.stdout.readline(), timeout=20)
        if not line:
            raise RuntimeError("Cache worker ended without result")
        return json.loads(line)

    try:
        await redis_control(None)
        for _ in range(2):
            # Cache workers never inherit backend/provider credentials or env selectors.
            environment = {k: v for k, v in os.environ.items() if k.upper() in {
                "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP", "USERPROFILE",
                "LOCALAPPDATA", "APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "COMSPEC",
            }}
            proxy = await gate()
            process = await asyncio.create_subprocess_exec(sys.executable, __file__, "--worker", "--port", str(proxy["port"]),
                env=environment, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            children.append(process)
        first, second = children
        report["before_fault"] = [await ask(first, "warm"), await ask(second, "read")]
        assert all(value["cached_old"] for value in report["before_fault"])
        # Drop TCP streams rather than pausing Redis: a paused server may execute
        # a timed-out SET later and falsely make lost invalidation look safe.
        for proxy in gates:
            proxy["blocked"] = True
            for writer in list(proxy["writers"]):
                writer.close()
        report["fault"] = "Two real TCP paths cut; invalidation commands dropped before backing Redis"
        report["invalidator_during_outage"] = await ask(first, "invalidate")
        report["other_process_during_outage"] = await ask(second, "read")
        for proxy in gates:
            proxy["blocked"] = False
        report["invalidator_after_recovery"] = await ask(first, "read")
        report["other_process_after_recovery"] = await ask(second, "read")
        stale = report["other_process_after_recovery"]["cached_old"]
        report["status"] = "failed" if stale else "passed"
        report["stale_payload_returned_after_failed_invalidation"] = stale
        await ask(first, "invalidate")
        report["after_successful_invalidation"] = [await ask(first, "read"), await ask(second, "read")]
        report["successful_global_invalidation_clears_old_snapshot"] = all(
            value["miss"] for value in report["after_successful_invalidation"]
        )
    except Exception as error:
        report.update(status="blocked", error_type=type(error).__name__)
    finally:
        for process in children:
            if process.returncode is None:
                process.stdin.write(b'{"action":"quit"}\n')
                await process.stdin.drain()
                await asyncio.wait_for(process.wait(), timeout=15)
        for proxy in gates:
            proxy["server"].close()
            await proxy["server"].wait_closed()
            for task in list(proxy["tasks"]):
                task.cancel()
            await asyncio.gather(*proxy["tasks"], return_exceptions=True)
        target = BACKEND / ".artifacts/mumbai-refresh/multi-process-redis-outage.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    return report["status"] == "passed"


if __name__ == "__main__":
    if "--worker" in sys.argv:
        asyncio.run(worker())
    else:
        sys.exit(0 if asyncio.run(main()) else 1)
