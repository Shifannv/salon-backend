"""Profile API process startup phase by phase, in fresh interpreters.

Each trial starts a new Python process that imports the stack in a fixed order and
reports how long each phase took. A phase's time is its extra cost given the phases
before it, so a library shared by two phases is charged to the first.

Only phase names and durations are printed or saved: no settings, URLs, tokens or
request data. The environment is inherited unchanged; settings load as the app
would load them.

Local run (no env file, no DB or Redis):
    SALON_ENV_FILE=/nonexistent ENVIRONMENT=test python scripts/startup_profile.py --trials 20

Diagnostic Cloud Run revision: copy this file into a diagnostic image and set the
command to `python startup_profile.py --serve`. It logs one JSON line of phases,
then serves the app on $PORT. Never use it as the production command.
"""

from __future__ import annotations

import time

_ENTRY_NS = time.perf_counter_ns()

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

IMPORT_PHASES = [
    ("uvicorn", "uvicorn"),
    ("fastapi", "fastapi"),
    ("sqlalchemy", "sqlalchemy.ext.asyncio"),
    ("pydantic_settings", "pydantic_settings"),
    ("env_file_read", None),  # reads SALON_ENV_FILE first; contents are discarded
    ("settings", "app.core.config"),
    # Libraries only some routes need, timed on their own before deps pulls them in.
    ("jose_cryptography", "jose.jwt"),
    ("httpx", "httpx"),
    ("pillow", "PIL.Image"),
    ("segno", "segno"),
    ("deps", "app.api.deps"),
    ("routes", "app.api.v1.router"),
    ("app", "app.main"),  # app.main builds the app at import time
]


# STARTUP_PROFILE_PHASES=app times only uvicorn and app.main, so the profile does not
# pre-load libraries that the app defers. Use it to compare images end to end.
if os.environ.get("STARTUP_PROFILE_PHASES") == "app":
    IMPORT_PHASES = [("uvicorn", "uvicorn"), ("app", "app.main")]


def _ms(start_ns: int, end_ns: int) -> float:
    return round((end_ns - start_ns) / 1_000_000, 2)


def measure_imports() -> dict[str, float]:
    import importlib

    phases: dict[str, float] = {}
    last = time.perf_counter_ns()
    for name, module in IMPORT_PHASES:
        if module is None:
            try:
                Path(os.environ.get("SALON_ENV_FILE", ".env")).read_bytes()
            except OSError:
                pass
        else:
            importlib.import_module(module)
        now = time.perf_counter_ns()
        phases[name] = _ms(last, now)
        last = now
    return phases


async def measure_dependencies() -> dict[str, float]:
    """Time the same work lifespan does before the port opens."""
    from sqlalchemy import text

    from app.core.config import settings
    from app.infrastructure.cache.redis import close_redis_cache, init_redis_cache
    from app.infrastructure.db.session import AsyncSessionLocal, engine

    phases: dict[str, float] = {}
    start = time.perf_counter_ns()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
        phases["db_ok"] = 1
    except Exception:
        phases["db_ok"] = 0
    middle = time.perf_counter_ns()
    phases["db_warmup"] = _ms(start, middle)
    try:
        await init_redis_cache(settings.redis_url)
        phases["redis_ok"] = 1
    except Exception:
        phases["redis_ok"] = 0
    phases["redis_init"] = _ms(middle, time.perf_counter_ns())
    await close_redis_cache()
    await engine.dispose()
    return phases


def child(dependencies: bool) -> dict[str, float]:
    phases = measure_imports()
    if dependencies:
        import asyncio

        phases.update(asyncio.run(measure_dependencies()))
    phases["total_in_process"] = _ms(_ENTRY_NS, time.perf_counter_ns())
    phases["entry_ns"] = _ENTRY_NS
    return phases


def serve() -> None:
    phases = child(dependencies=False)
    phases.pop("entry_ns")
    print(json.dumps({"message": "startup_profile", "phases_ms": phases}), flush=True)

    from contextlib import asynccontextmanager

    import uvicorn

    from app.main import app

    # Lifespan (DB warm-up, Redis) runs inside uvicorn as in production; time it
    # as one phase. The port opens only after it finishes.
    original = app.router.lifespan_context

    @asynccontextmanager
    async def timed_lifespan(application):
        start = time.perf_counter_ns()
        async with original(application) as state:
            now = time.perf_counter_ns()
            print(json.dumps({"message": "startup_profile_lifespan",
                              "lifespan_ms": _ms(start, now),
                              "since_entry_ms": _ms(_ENTRY_NS, now)}), flush=True)
            yield state

    app.router.lifespan_context = timed_lifespan
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct / 100 * len(ordered)) - 1)]


def run_trials(trials: int, dependencies: bool) -> dict:
    results, failures = [], 0
    for _ in range(trials):
        args = [sys.executable, str(Path(__file__).resolve()), "--child"]
        if dependencies:
            args.append("--dependencies")
        spawn_ns = time.perf_counter_ns()
        proc = subprocess.run(args, cwd=BACKEND, capture_output=True, text=True, timeout=180, check=False)
        exited_ns = time.perf_counter_ns()
        line = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("{")), None)
        if proc.returncode or line is None:
            failures += 1
            continue
        phases = json.loads(line)
        # perf_counter is system-wide on Linux and Windows, so spawn and entry compare.
        phases["interpreter_start"] = _ms(spawn_ns, phases.pop("entry_ns"))
        phases["process_wall"] = _ms(spawn_ns, exited_ns)
        results.append(phases)

    summary = {}
    for name in results[0] if results else []:
        values = [r[name] for r in results]
        summary[name] = {
            "median": round(statistics.median(values), 2),
            "p95": round(percentile(values, 95), 2),
            "max": round(max(values), 2),
        }
    return {"trials": trials, "succeeded": len(results), "failures": failures,
            "python": sys.version.split()[0], "platform": sys.platform,
            "summary_ms": summary, "samples_ms": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--dependencies", action="store_true",
                        help="also time DB warm-up and Redis init with the configured settings")
    parser.add_argument("--out", type=Path, help="write the full result as JSON")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--serve", action="store_true",
                        help="log one profile, then serve the app on $PORT (diagnostic revisions only)")
    args = parser.parse_args()

    if args.child:
        sys.path.insert(0, str(BACKEND))
        print(json.dumps(child(args.dependencies)))
        return
    if args.serve:
        sys.path.insert(0, str(BACKEND))
        serve()
        return

    result = run_trials(args.trials, args.dependencies)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{result['succeeded']}/{result['trials']} trials succeeded, python {result['python']}")
    print(f"{'phase':<18}{'median':>10}{'p95':>10}{'max':>10}  (ms)")
    for name, row in result["summary_ms"].items():
        if name in ("db_ok", "redis_ok"):
            continue
        print(f"{name:<18}{row['median']:>10}{row['p95']:>10}{row['max']:>10}")


if __name__ == "__main__":
    main()
