# Local Docker cold-start measurement — 16 October 2026

Ten fresh API-container trials passed. Median time from immediately before `docker run`
to the first complete HTTP 200 from `/health` was **2108.91 ms**; range
**2029.71–2519.28 ms**. This measures local Docker Desktop with ready local dependencies,
not Cloud Run startup or remote Mumbai database latency.

## Inspected startup configuration

- `backend/Dockerfile`: Python 3.12 slim Bookworm, non-root `app` user, port 8000.
  Unmodified command: `sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'`.
  One Uvicorn process, no Gunicorn, reload, or explicit worker-count option.
- `backend/docker-compose.yml`: API uses `init: true`, `.env` by default, and waits for
  Redis `service_healthy`. Redis persists to `redis-data`; all six worker services share
  application configuration. No explicit CPU/memory limits or separate startup probe.
  No dependency on database health is declared in this Compose file.
- `backend/docker-compose.test.yml`: separate older fixture configuration, API only,
  host-bound PostgreSQL/Redis/Auth test ports, no `depends_on` declaration. Not used here.
  No tracked conventional Compose override file was found.
- Image and main Compose API health checks call `/health` every 30 seconds, timeout
  5 seconds, start period 20 seconds, three retries. These checks are separate from
  the benchmark's 50 ms polling; Docker's `healthy` transition is not the timing endpoint.
- `app/main.py` lifespan first opens a business database session and executes `SELECT 1`,
  then initializes/pings Redis, before yielding to Uvicorn. Failures are logged and startup
  continues; therefore process health alone does not prove dependencies are reachable.
- `/health`: process-only response. `/health/db`: real `SELECT 1` using the shared pool's
  probe session. `/health/redis`: real Redis PING when configured; disabled Redis can also
  return 200. This benchmark requires `status=ok` and `redis=reachable`.
- `/health/ready` also checks DB and configured Redis, but is not the Docker health target
  and was not measured in these trials.
- Non-local/test environments require Supabase URL, anon key, JWKS URL and service-role
  configuration. This run uses `ENVIRONMENT=staging` for JSON logging and synthetic unused
  Auth settings pointed at container loopback port 9. Explicit local database/Redis URLs
  override defaults; `PORT=8000`; `SALON_ENV_FILE` points to a nonexistent path.
  Payments/subscriptions are `none`; Cashfree is disabled. Email, Firebase, R2 and Sentry
  credentials are absent. No environment file or existing container environment was read.

## Isolation and method

Image `salon-cold-start:20261016` was built from `backend/` before measuring. Build time,
image pulling, dependency initialization and test-container cleanup are excluded. Image ID:
`sha256:25f32e55936f79df1427bb4514cd4f509efc8b4504f32d51400034e5e820758b`.

Docker Desktop engine 29.8.2, Linux x86_64, overlayfs, 20 logical CPUs and 8,171,204,608
bytes of memory available to Docker. CPU and memory were shared with existing containers;
no per-container limits were added. This does not emulate a Cloud Run instance's resources.

The runner creates UUID-named, ownership-labeled containers and a dedicated bridge network.
Only the API port is published, bound to `127.0.0.1`. PostgreSQL 18 and Redis 7 have
unpublished ports and tmpfs data directories. PostgreSQL is read-only by default; public
user-table count was zero both before and after. No schema, migrations, fixtures, Auth users
or customer records are needed for these health checks. Dependencies remain ready between
trials; each API has a fresh process, connection pool and container filesystem.

The bridge permits egress; this is not an egress-firewall test. All supplied service targets
are local, external providers are disabled/unconfigured, and only health endpoints are called.
No workers are started. No Supabase, GCP, Cloud Run, VM, DNS or production setting is changed.

For each trial:

1. Start the clock immediately before launching `docker run -d --init` using the image ID.
2. Poll `/health` on loopback every 50 ms until HTTP 200 with `status=ok`.
3. Poll `/health/db`, then `/health/redis`, requiring actual reachable dependencies.
4. Send five warm requests to each of the three endpoints (15 warm requests per trial).
5. Save timings/logs, stop and remove only the labeled test API, and repeat.

Client elapsed times use `perf_counter_ns`. Creation, running and Uvicorn markers use
Docker UTC `Created`, `StartedAt`, and timestamped logs relative to the host origin.
These cross-clock markers assume Docker Desktop's guest and host clocks are aligned;
the primary HTTP cold-start metric uses only the host monotonic clock. Creation is the
Docker creation timestamp milestone, not a separately timed `docker create` RPC.
Polling adds detection delay of approximately one interval plus host scheduling and HTTP
time. Header timings and response completion timings are retained in the JSON; header timing
includes receiving/parsing headers and is not a packet-level first-byte measurement.

## Results

All values are milliseconds. Milestones below are cumulative from the same pre-run origin;
they must not be added together. Nearest-rank p95 with ten trials equals the maximum, so
the table shows the measured maximum rather than implying a reliable tail-latency SLO.

| Milestone | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: |
| Docker container created | 139.78 | 77.03 | 175.97 |
| Docker container running | 273.38 | 222.57 | 349.90 |
| Application startup complete log | 2076.75 | 2023.66 | 2515.74 |
| API ready: Uvicorn listening log | 2077.09 | 2023.94 | 2516.28 |
| First `/health` HTTP 200 completed | **2108.91** | 2029.71 | 2519.28 |
| First `/health/db` HTTP 200 completed | 2123.90 | 2048.15 | 2523.47 |
| First `/health/redis` HTTP 200 completed | 2139.11 | 2064.45 | 2543.00 |
| `docker run -d` CLI returned | 498.69 | 373.74 | 656.02 |

The DB and Redis probes are deliberately sequential after `/health`, so their cumulative
milestones are not independent estimates of earliest dependency readiness.

| Endpoint | First successful request median | Warm request median | Warm p95 | Warm samples |
| --- | ---: | ---: | ---: | ---: |
| `/health` | 8.01 | 2.66 | 33.81 | 50 |
| `/health/db` | 4.32 | 3.76 | 51.49 | 50 |
| `/health/redis` | 16.59 | 13.98 | 30.33 | 50 |

All 30 first-success endpoint responses and all 150 warm responses passed. Failed connection
attempts while waiting for startup are expected and are counted per trial. Median paired time
from container running to Uvicorn listening was **1811.67 ms**; imports, application construction,
and lifespan initialization occur within that interval. This run does not isolate their
individual CPU/database/Redis contributions.

## Evidence and reproduction

- [Runner](../../scripts/docker_cold_start_benchmark.py)
- [JSON: configuration, source hashes, individual requests, summaries and preservation evidence](../../.artifacts/docker-cold-start-2026-10-16-measured/results.json)
- [CSV: per-trial milestones and first-response durations](../../.artifacts/docker-cold-start-2026-10-16-measured/results.csv)
- [CSV: all 150 warm requests](../../.artifacts/docker-cold-start-2026-10-16-measured/warm-requests.csv)
- Timestamped synthetic API logs: `backend/.artifacts/docker-cold-start-2026-10-16-measured/trial-01.log`
  through `trial-10.log`. Raw artifacts are local and ignored by Git.

An earlier setup attempt on an `--internal` network failed host connectivity despite
container-local health succeeding: Docker's requested port binding was present, but
`NetworkSettings.Ports` had no published address. It was excluded from the ten-trial series,
cleaned up, and retained at `backend/.artifacts/docker-cold-start-2026-10-16/`.

From `backend/`, with Docker access and existing `postgres:18` / `redis:7-alpine` images:

```powershell
docker build --pull=false -t salon-cold-start:20261016 .
./.venv/Scripts/python.exe scripts/docker_cold_start_benchmark.py --image salon-cold-start:20261016 --trials 10 --output .artifacts/docker-cold-start-new-run
```

Use a new output directory per run. The runner refuses fewer than ten trials and does not
pull dependency images. The image's CMD and source application are unmodified.

## Verification and cleanup

- Both attempts: cleanup errors empty; before/after existing container IDs, images, states,
  start timestamps, networks and volumes match exactly.
- Final Docker queries found no remaining benchmark containers or networks. Test tmpfs data
  was removed with its containers; the benchmark image is retained. Existing containers,
  images and volumes were preserved. No prune command was used.
- `pytest -q tests/test_health.py -p no:cacheprovider`: **5 passed**, one existing dependency
  deprecation warning. Process configuration pointed at an unused local port; these tests
  use mocked dependencies and do not run migrations.
- `ruff check --no-cache app tests migrations scripts/docker_cold_start_benchmark.py`:
  **all checks passed**. Ruff's default cache directory was unwritable, so caching was disabled.
- Full migration/integration verification was not run for this measurement-only change,
  consistent with the request to run no migrations. No application or deployment configuration
  was changed. Files remain uncommitted.

These results describe fresh containers with a cached image and ready local dependencies.
They do not include image download, VM boot, Cloud Run scheduling, remote DNS/TLS, Mumbai
network transit, a remote DB-pool cold connection, business queries or authenticated flows.
