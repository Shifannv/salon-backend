"""Measure fresh local API containers against isolated, already-ready dependencies.

Uses the image's unmodified CMD. No environment files, migrations, business requests,
external providers, or pre-existing containers/volumes are used. Build separately.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import math
import socket
import statistics
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def inventory() -> dict:
    ids = docker("ps", "-aq", "--no-trunc").splitlines()
    template = '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"status":{{json .State.Status}},"started_at":{{json .State.StartedAt}}}'
    containers = docker("inspect", "--format", template, *ids) if ids else ""
    return {
        "containers": [json.loads(line) for line in containers.splitlines()],
        "networks": docker("network", "ls", "--format", "{{.ID}} {{.Name}}").splitlines(),
        "volumes": docker("volume", "ls", "--format", "{{.Name}}").splitlines(),
    }


def stamp_ns(value: str) -> int:
    # Docker emits nanosecond RFC3339; datetime supports only microseconds.
    base, _, fraction = value.removesuffix("Z").partition(".")
    seconds = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC).timestamp()
    return int(seconds) * 1_000_000_000 + int(fraction.ljust(9, "0")[:9] or "0")


def request(port: int, path: str, timeout: float = 2) -> dict:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    start = time.perf_counter_ns()
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        headers_at = time.perf_counter_ns()
        body = response.read()
        end = time.perf_counter_ns()
        return {
            "path": path, "status": response.status,
            "headers_ms": (headers_at - start) / 1e6,
            "total_ms": (end - start) / 1e6,
            "body": json.loads(body), "completed_perf_ns": end,
        }
    finally:
        conn.close()


def poll(port: int, path: str, origin: int, timeout: float) -> dict:
    deadline = time.perf_counter() + timeout
    next_poll = time.perf_counter()
    attempts = 0
    while time.perf_counter() < deadline:
        time.sleep(max(0, next_poll - time.perf_counter()))
        attempts += 1
        try:
            result = request(port, path, timeout=0.04 if path == "/health" else 2)
            if result["status"] == 200 and result["body"].get("status") == "ok":
                result["since_start_ms"] = (result.pop("completed_perf_ns") - origin) / 1e6
                result["attempts"] = attempts
                return result
        except (OSError, http.client.HTTPException, ValueError):
            pass
        next_poll += 0.05
        # Avoid a catch-up burst if the host stalls.
        next_poll = max(next_poll, time.perf_counter())
    raise TimeoutError(f"No successful {path} within {timeout}s")


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "count": len(values), "min": min(values), "median": statistics.median(values),
        "mean": statistics.mean(values),
        "p95_nearest_rank": ordered[math.ceil(0.95 * len(values)) - 1],
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 10:
        parser.error("At least 10 trials are required")
    args.output.mkdir(parents=True, exist_ok=False)
    prefix = "salon-cold-" + uuid4().hex[:10]
    label = "salon.cold-start.run=" + prefix
    network = prefix + "-net"
    db, redis, api = (prefix + suffix for suffix in ("-db", "-redis", "-api"))
    before = inventory()
    image = json.loads(docker("image", "inspect", args.image))[0]
    info = json.loads(docker("info", "--format", "{{json .}}"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = {
        "ENVIRONMENT": "staging", "SALON_ENV_FILE": "/nonexistent-cold-start.env",
        "PORT": "8000", "DATABASE_URL": f"postgresql+asyncpg://postgres@{db}:5432/postgres",
        "REDIS_URL": f"redis://{redis}:6379/0", "PAYMENT_PROVIDER": "none",
        "SUBSCRIPTION_PROVIDER": "none", "CASHFREE_ENABLED": "false",
        "SUPABASE_URL": "http://127.0.0.1:9", "SUPABASE_ANON_KEY": "synthetic-unused",
        "SUPABASE_JWKS_URL": "http://127.0.0.1:9/auth/v1/.well-known/jwks.json",
        "SUPABASE_SERVICE_ROLE_KEY": "synthetic-unused", "BACKEND_CORS_ORIGINS": "[]",
    }
    data = {
        "started_utc": datetime.now(UTC).isoformat(), "run": prefix,
        "image": {k: image.get(k) for k in ("Id", "RepoDigests", "Created")},
        "image_config": {k: image["Config"].get(k) for k in ("Cmd", "Entrypoint", "User", "ExposedPorts", "Healthcheck")},
        "host": {k: info.get(k) for k in ("ServerVersion", "OperatingSystem", "OSType", "Architecture", "NCPU", "MemTotal", "Driver")},
        "environment": environment, "port": port, "network_internal": False,
        "isolation": "dedicated bridge; API published on loopback only; dependency ports unpublished; no provider credentials or workers",
        "dependencies_already_ready": True, "poll_interval_ms": 50,
        "http_client": "Python stdlib http.client; fresh loopback TCP connection per request; no proxy",
        "timing": "perf_counter_ns for client durations; Docker UTC timestamps for create/start/log markers",
        "cpu_memory_limits": "none; Docker Desktop shared host resources",
        "build_time_excluded": True, "trials": [], "before": before,
    }
    backend = Path(__file__).resolve().parents[1]
    data["source_hashes"] = {
        str(p.relative_to(backend)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [backend / "Dockerfile", *sorted((backend / "app").rglob("*.py"))]
    }
    created: list[str] = []
    network_created = False

    def save() -> None:
        (args.output / "results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        if data["trials"]:
            with (args.output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
                rows = [{k: v for k, v in row.items() if not isinstance(v, (dict, list))} for row in data["trials"]]
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with (args.output / "warm-requests.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["trial", "path", "sample", "status", "headers_ms", "total_ms"])
                writer.writeheader()
                for row in data["trials"]:
                    for index, sample in enumerate(row["warm_requests"]):
                        writer.writerow({"trial": row["trial"], "sample": index % 5 + 1,
                                         **{key: sample[key] for key in ("path", "status", "headers_ms", "total_ms")}})

    def remove_owned(name: str) -> None:
        actual = docker("inspect", "--format", '{{index .Config.Labels "salon.cold-start.run"}}', name)
        if actual != prefix:
            raise RuntimeError("Refusing cleanup: ownership label mismatch")
        docker("stop", "--time", "10", name)
        docker("rm", name)
        created.remove(name)

    try:
        docker("network", "create", "--label", label, network)
        network_created = True
        docker("run", "-d", "--pull=never", "--name", db, "--label", label,
               "--network", network, "--tmpfs", "/var/lib/postgresql",
               "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", "POSTGRES_DB=postgres",
               "postgres:18", "postgres", "-c", "default_transaction_read_only=on")
        created.append(db)
        docker("run", "-d", "--pull=never", "--name", redis, "--label", label,
               "--network", network, "--tmpfs", "/data", "redis:7-alpine",
               "redis-server", "--save", "", "--appendonly", "no")
        created.append(redis)
        # No migrations/schema/data needed for SELECT 1 and PING health checks.
        for _ in range(60):
            try:
                docker("exec", db, "pg_isready", "-U", "postgres")
                if docker("exec", redis, "redis-cli", "ping") == "PONG":
                    break
            except RuntimeError:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Disposable dependencies did not become ready")
        data["dependency_images"] = {
            name: docker("inspect", "--format", "{{.Image}}", name) for name in (db, redis)
        }
        data["database_read_only"] = docker("exec", db, "psql", "-U", "postgres", "-Atc", "SHOW default_transaction_read_only")
        data["database_user_tables_before"] = docker("exec", db, "psql", "-U", "postgres", "-Atc", "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        for trial in range(1, args.trials + 1):
            command = ["docker", "run", "-d", "--pull=never", "--init", "--name", api,
                       "--label", label, "--network", network, "-p", f"127.0.0.1:{port}:8000"]
            for key, value in environment.items():
                command.extend(["-e", f"{key}={value}"])
            command.append(image["Id"])
            start = time.perf_counter_ns()
            wall = time.time_ns()
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            completion = {}

            def await_run(child: subprocess.Popen = process, target: dict = completion) -> None:
                _stdout, stderr = child.communicate()
                target.update(stderr=stderr, returncode=child.returncode, ended_ns=time.perf_counter_ns())

            waiter = threading.Thread(target=await_run, daemon=True)
            waiter.start()
            created.append(api)
            health = poll(port, "/health", start, 90)
            # Start dependency probes immediately after process health succeeds.
            db_health = poll(port, "/health/db", start, 30)
            redis_health = poll(port, "/health/redis", start, 30)
            if db_health["body"].get("database") != "reachable" or redis_health["body"].get("redis") != "reachable":
                raise RuntimeError("A dependency health check was not actually reachable")
            waiter.join(timeout=10)
            if waiter.is_alive() or completion.get("returncode") != 0:
                raise RuntimeError(f"API docker run failed: {completion.get('stderr', 'timeout')}")
            warm = []
            for path in ("/health", "/health/db", "/health/redis"):
                for _ in range(5):
                    sample = request(port, path)
                    sample.pop("completed_perf_ns")
                    if sample["status"] != 200 or sample["body"].get("status") != "ok":
                        raise RuntimeError("Warm request failed")
                    warm.append(sample)
            state = json.loads(docker("inspect", api))[0]
            log_result = subprocess.run(["docker", "logs", "--timestamps", api], capture_output=True, text=True, timeout=15, check=True)
            logs = log_result.stdout + log_result.stderr
            (args.output / f"trial-{trial:02d}.log").write_text(logs, encoding="utf-8")
            markers = {}
            for line in logs.splitlines():
                for key, phrase in {"app_startup_complete_ms": "Application startup complete.", "api_process_ready_ms": "Uvicorn running on"}.items():
                    if phrase in line:
                        markers[key] = (stamp_ns(line.split(" ", 1)[0]) - wall) / 1e6
            if len(markers) != 2 or "Database warm-up failed" in logs or "reconnect pending" in logs:
                raise RuntimeError("Startup markers missing or a dependency warm-up failed")
            row = {
                "trial": trial, "container_id": state["Id"],
                "origin_utc": datetime.fromtimestamp(wall / 1e9, UTC).isoformat(),
                "container_created_ms": (stamp_ns(state["Created"]) - wall) / 1e6,
                "container_running_ms": (stamp_ns(state["State"]["StartedAt"]) - wall) / 1e6,
                **markers, "first_health_200_ms": health["since_start_ms"],
                "first_health_response_ms": health["total_ms"],
                "first_db_200_ms": db_health["since_start_ms"],
                "first_db_response_ms": db_health["total_ms"],
                "first_redis_200_ms": redis_health["since_start_ms"],
                "first_redis_response_ms": redis_health["total_ms"],
                "docker_run_cli_ms": (completion["ended_ns"] - start) / 1e6,
                "health_poll_attempts": health["attempts"],
                "warm_health_median_ms": statistics.median(s["total_ms"] for s in warm if s["path"] == "/health"),
                "warm_db_median_ms": statistics.median(s["total_ms"] for s in warm if s["path"] == "/health/db"),
                "warm_redis_median_ms": statistics.median(s["total_ms"] for s in warm if s["path"] == "/health/redis"),
                "first_responses": [health, db_health, redis_health], "warm_requests": warm,
                "container_created_utc": state["Created"], "container_started_utc": state["State"]["StartedAt"],
            }
            data["trials"].append(row)
            save()
            print(f"Trial {trial:02d}: health={row['first_health_200_ms']:.2f} ms; db={row['first_db_response_ms']:.2f} ms; redis={row['first_redis_response_ms']:.2f} ms", flush=True)
            remove_owned(api)
        data["database_user_tables_after"] = docker("exec", db, "psql", "-U", "postgres", "-Atc", "SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        data["summary_ms"] = {
            key: distribution([row[key] for row in data["trials"]])
            for key in data["trials"][0] if key.endswith("_ms")
        }
        data["warm_summary_ms"] = {
            path: distribution([sample["total_ms"] for row in data["trials"] for sample in row["warm_requests"] if sample["path"] == path])
            for path in ("/health", "/health/db", "/health/redis")
        }
        data["status"] = "passed"
    except BaseException as exc:
        data["status"] = "failed"
        data["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        cleanup_errors = []
        for name in list(reversed(created)):
            try:
                remove_owned(name)
            except Exception as exc:
                cleanup_errors.append(f"{name}: {exc}")
        if network_created and not cleanup_errors:
            docker("network", "rm", network)
        data["cleanup_errors"] = cleanup_errors
        data["after"] = inventory()
        data["preexisting_resources_preserved"] = data["before"] == data["after"]
        data["finished_utc"] = datetime.now(UTC).isoformat()
        save()
    print(json.dumps(data["summary_ms"], indent=2), flush=True)


if __name__ == "__main__":
    main()
