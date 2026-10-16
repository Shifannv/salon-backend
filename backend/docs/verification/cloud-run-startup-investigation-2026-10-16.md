# Mumbai staging startup investigation — 16 October 2026

Status: investigation in progress. Cloud Run configuration has not been changed in this
investigation. Natural measurements run on the existing serving revision and save progress
after every observation. Final natural percentiles require ten verified cold first requests
per endpoint; a single response is not a completed distribution.

## Findings before any configuration change

The dominant measured span is **before the application lifespan**, not the health handler:
median **6997.98 ms** from Cloud Run's instance-start event to Uvicorn's server-process
message, across the existing ten verified fresh `/health` cold starts. This combines
platform provisioning/process scheduling, interpreter/Uvicorn imports, application imports,
FastAPI creation and route registration. Existing deployed telemetry cannot split those
components. It is not evidence that Python imports alone consume seven seconds.

| Existing cloud span, paired timestamps per instance | Samples | p50 ms | p95 / p99 ms |
| --- | ---: | ---: | ---: |
| Instance-start event → server-process message | 10 | 6997.98 | 11808.15 |
| Lifespan startup hook | 10 | 530.62 | 2462.03 |
| Lifespan start → database warm-up log | 10 | 127.21 | 1973.13 |
| Database warm-up log → Redis connected log | 10 | 401.43 | 692.98 |
| Lifespan complete → startup probe succeeds | 10 | 709.55 | 960.88 |
| Instance-start event → successful startup probe | 10 | 8123.80 | 13551.72 |

Spans overlap. Do not add medians or subtract unrelated percentiles. Database warm-up includes
connection acquisition, `SELECT 1`, transaction cleanup and logging; Redis initialization
includes its lazy Python import, client construction, DNS/TCP/TLS/authentication/PING and
logging. These are upper spans, not isolated network-operation measurements.

Registry image import happens at deployment; Cloud Run retains the imported image and does
not pull it again from Artifact Registry for each new instance. Internal image/filesystem
provisioning is not separately timed by this application's logs. Do not label the whole
pre-lifespan span as "image pull". [Cloud Run image deployment documentation](https://docs.cloud.google.com/run/docs/deploying).

Cloud Monitoring startup/probe distributions are available. Their container-startup metric
is a provider startup measure, not an independent pure-platform component that can be added
to the application span. [Metric definitions](https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z).

Single-observation histogram intervals matched eight original samples for provider container
startup (median 8673.87 ms, p95/p99 13061.78 ms) and seven for the provider probe metric
(median 9014.09 ms, p95/p99 13050.86 ms). Other intervals aggregated multiple observations
and were not treated as individual measurements. These are different subsets with overlapping
definitions; do not subtract their percentiles.

## Inspected startup components

- `backend/Dockerfile`: Python 3.12, single Uvicorn process, `PORT` respected, no Gunicorn,
  reload, startup migration or worker. The deployed staging image adds only the public DB CA.
- `app/main.py`: imports routers eagerly, constructs the FastAPI app, adds middleware and
  exception handlers, registers routers; lifespan warms DB then initializes Redis in sequence.
- `app/infrastructure/db/session.py`: creates the engine and pool objects eagerly, without
  connecting until lifespan. Pool size 5, overflow 5, pre-ping on; business isolation remains
  READ COMMITTED and probes use the shared AUTOCOMMIT base engine.
- `app/api/deps.py`, `app/core/security.py`: creates a lightweight JWT verifier with an empty
  JWKS cache. JWKS is fetched only when authentication needs it. Supabase gateways use HTTPX
  and are constructed lazily; no Supabase Auth network call is required to serve health.
- `app/infrastructure/cache/redis.py`: imports the Redis client during startup initialization;
  `from_url` constructs a client/pool and the first PING establishes the TLS/authenticated
  connection. No Redis REST client is involved.
- `app/infrastructure/push/fcm_gateway.py`: Firebase import/initialization is lazy; it is not
  initialized in this health-only startup. No Firebase credentials are configured.
- `app/infrastructure/r2/storage.py`: the module/Pillow import is eager through dependency
  wiring, but the boto3 client and network access are lazy. No R2 credentials are configured.
- `app/core/telemetry.py`: Sentry is disabled without its DSN. Middleware registration does
  not perform provider calls. Runtime middleware construction also occurs as ASGI starts;
  its exact deployed duration is not currently logged.
- Cloud Run HTTP startup probe uses `/health`, period/timeout 1 second, threshold 60.
  Security, JWT verification and dependency health checks have not been bypassed or removed.

## Local timing-only profiles

The deployed image was run in disposable local Docker containers with **1 CPU / 512 MiB**,
no network, synthetic configuration and no lifespan execution. Ten ordinary imports/app
constructions had median **1081.57 ms**, range **1041.08–1397.42 ms**. These are local cached-image
filesystem/CPU results, not Cloud Run measurements.

A separate ten-run, low-overhead in-memory wrapper profile recorded these medians:

| Local component | Median ms |
| --- | ---: |
| Imports + profiling setup + app construction | 1149.70 |
| App factory, inclusive | 82.51 |
| Top-level route registration, within app factory | 82.23 |
| DB engine/pool object construction, no network | 39.50 |
| FastAPI constructor | 0.139 |
| Middleware registration | 0.009 |
| JWT verifier constructor, no JWKS network | 0.003 |
| Disabled Sentry check | 0.001 |

A general Python function profiler increased import time to about 4.1 seconds and is excluded
from performance conclusions. The low-overhead wrapper only changes isolated test processes;
no deployed application source was instrumented. Local results cannot be used to subtract
Python time from a Cloud Run percentile and call the remainder platform time.

One ordinary `-X importtime` diagnostic reported cumulative FastAPI imports 467 ms, router
module imports 776 ms and SQLAlchemy 134 ms. These overlap. The R2/Pillow module path was
25 ms locally; stripping that integration is not supported as a multi-second improvement.

## Separate measurement scenarios

| Scenario | `/health` cold-first status | `/health/db` cold-first status |
| --- | --- | --- |
| A: fresh revision | Existing 10 verified samples: p50 8386.97 ms, p95/p99 13815.61 ms | Not measured as the first cold endpoint; earlier DB probes followed `/health` and must not be relabeled. New trials require revision/tag changes prohibited by the latest user instruction. |
| B: natural idle scale-to-zero | Running toward 10 samples; first verified response 8382.75 ms | Running toward 10 samples; not yet a completed distribution |

The original ten fresh samples were additionally checked against Cloud Run HTTP-request
arrival timestamps and instance-start events on the **same server clock**. This avoids
assuming workstation UTC and server UTC are identical. The client duration remains measured
with a monotonic clock. Previously excluded prestarted trials remain excluded.

The natural runner sends no HTTP requests during idle waits. It requires both active and idle
instance counts to be explicitly zero, plus logged termination of all known instances of the
serving revision, before requesting a new start. Monitoring alone can lag or momentarily
understate a live instance; zero active instances is particularly not sufficient.
Monitoring is sampled every 60 seconds and can appear up to 120 seconds later.
[Metric timing and state definitions](https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z).

Natural trials alternate which endpoint is first. Each accepted trial must match a new instance
ID and an AUTOSCALING event inside its server-clock HTTP request interval. Prestarted, failed
or unverified observations are retained and excluded with a reason. Identity tokens remain
in memory. Server-Timing, first responses and five subsequent warm calls per endpoint are
saved separately. Ten cold-first trials per endpoint require twenty independent shutdowns;
Cloud Run may retain idle instances for up to fifteen minutes.
[Autoscaling lifecycle](https://docs.cloud.google.com/run/docs/about-instance-autoscaling).

## Recommendations reported before any Cloud Run change

1. **Keep the baseline unchanged while natural sampling completes.** Retain min 0/max 1,
   1 vCPU/512 MiB, concurrency 8, boost disabled and all health/security checks.
2. **Add low-overhead staging startup markers before changing performance behavior.** Exact
   files: `backend/app/main.py`, new `backend/app/core/startup_timing.py`, and, for a process-entry
   marker before Uvicorn import, new `backend/app/staging_startup.py` and a new staging-only
   `backend/Dockerfile.cloudrun-staging`. A typed opt-in flag belongs in `backend/app/core/config.py`.
   Measure router imports, factory steps and middleware construction; never log settings.
   Use the existing `RequestMetrics` context during startup DB warming to capture actual
   acquisition/query timing. Optional finer client initialization timing belongs in
   `backend/app/infrastructure/cache/redis.py` and `backend/app/infrastructure/db/session.py`.
   Regression coverage belongs in `backend/tests/unit/test_startup_timing.py` and existing
   `backend/tests/test_health.py` / `backend/tests/unit/test_redis_cache.py`.
   Tradeoff: a new diagnostic image/revision and small logging/timer overhead. This would
   change deployed configuration and has not been done during this investigation.
3. **Test startup CPU boost next, as a separate A/B after baseline/instrumentation.** It is
   a plausible experiment for the dominant pre-lifespan span, not a promised speedup. Keep
   the image, memory, concurrency and min/max fixed. It adds CPU during startup and ten
   seconds afterward. For one extra vCPU over a hypothetical 20-second boost window, the
   CPU component is about $0.00048/start before free allowances; changed startup duration
   changes the actual net charge. No boost setting was changed.
   [CPU boost behavior/pricing](https://docs.cloud.google.com/run/docs/configuring/services/cpu).
4. **Do not raise memory on current evidence.** Available memory-utilization interval means
   ranged from 10.85% to 16.44% of 512 MiB, and no memory failure was observed. These means
   are not peak RSS, so inspect peak samples before ruling memory pressure out entirely.
   At the published request-based rate, 512 MiB → 1 GiB adds about $0.0045 per active hour.
5. **Keep concurrency 8.** Single sequential cold requests do not test concurrency capacity;
   lowering it does not address the measured startup path and can increase queueing with
   max 1. Raising it requires load tests and a DB-connection budget, not cold-start guesses.
6. **Do not permanently raise CPU yet.** A 2-vCPU test can follow boost/instrumentation if
   justified, but single-process Python initialization will not necessarily use two cores
   effectively. At unchanged duration, 1 → 2 vCPU adds about $0.0864 per active hour. Compare
   actual latency and billable duration rather than assuming twice the CPU halves startup.
7. **Consider build-time bytecode only after isolating import cost.** Exact file:
   `backend/Dockerfile` (or a staging-only variant), adding explicit compileall for application
   modules. This preserves source/security behavior but adds bytecode to the image; Python
   and source changes invalidate it. It does not eliminate Pydantic model/router construction
   or platform scheduling. No benefit has been measured and no such image was deployed.
8. **Preserve DB warm-up and probes during this experiment.** Moving connections lazily could
   make `/health` look faster while shifting cost/failures to `/health/db` or the first customer
   request. Parallel DB/Redis initialization might remove some sequential overlap, but changes
   startup failure semantics and must be tested in `app/main.py` with before/after evidence.

All cost examples are USD before free allowances, transfer, logging and taxes. Current compute
is about $0.0909 per active instance-hour; request-based min-zero idle waiting is not equivalent
to always-on CPU billing. This is not a cost cap. [Cloud Run pricing](https://cloud.google.com/run/pricing).

## Evidence and scope

Ignored local evidence is under `backend/.artifacts/cold-start-investigation/`:

- [Startup phase breakdown](../../.artifacts/cold-start-investigation/existing-startup-breakdown.json)
- [Fresh server-clock revalidation](../../.artifacts/cold-start-investigation/fresh-server-clock-audit.json)
- [Local ordinary imports](../../.artifacts/cold-start-investigation/local-profiles.json)
- [Low-overhead local factory profiles](../../.artifacts/cold-start-investigation/local-factory-profiles.json)
- [Incremental natural results/status](../../.artifacts/cold-start-investigation/natural-results.json)
- [Incremental natural CSV](../../.artifacts/cold-start-investigation/natural-results.csv)

No improvement is claimed. No production, VM, Sydney, DNS, frontend URL, migration, stamp,
payment, worker or Cloud Run resource/configuration change was made in this investigation.
The earlier local/deployment report files were absent from the clean `shifan` checkout at
the start of this request; their ignored measurement evidence was available and was reused.
No removed files were restored or unrelated changes overwritten.
