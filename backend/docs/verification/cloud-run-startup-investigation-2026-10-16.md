# Mumbai staging startup investigation — 16–17 October 2026 (IST)

Status: twenty natural cold starts complete; startup inspection and read-only infrastructure audit complete. Fresh-revision DB-first measurements remain unavailable under the no-configuration-change constraint. No application or Cloud Run configuration change was made.

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

## Completed cold-start results

Twenty natural cold starts completed on **twenty distinct instances**, ten per
external first endpoint, with zero excluded HTTP trials. All 260 measured HTTP
requests (20 cold-first, 40 first follow-ups, 200 warm) returned 200 with status
`ok`. The existing `/health` startup probe remained enabled for both endpoint
scenarios. Dependency warm-up still happens in lifespan before external readiness.

| Scenario / endpoint | Samples | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| A: fresh revision, `/health` | 10 | 8386.97 | 13815.61 | 13815.61 |
| B: natural zero, `/health` | 10 | 8384.88 | 9429.90 | 9429.90 |
| B: natural zero, `/health/db` | 10 | 7422.67 | 9818.18 | 9818.18 |
| Warm after natural starts, `/health` | 100 | 59.18 | 172.68 | 292.29 |
| Warm after natural starts, `/health/db` | 100 | 71.72 | 105.74 | 221.80 |

Natural first requests ran from **16 October 2026, 17:54:17 IST** to completion at
**17 October 2026, 00:15:13 IST**. Most elapsed study time was waiting for genuine
idle shutdown, not executing HTTP requests. No forced shutdown or redeployment
was used. One read-access RuntimeError interrupted the observer at 22:29 IST;
read access was independently rechecked and the same saved study resumed around
22:30 IST. Its original detailed cause was not retained. No measured HTTP request
failed, and no saved measurement was discarded or reset.

The p50 is the median; p95/p99 use nearest rank. With only ten cold samples per
endpoint, both tail estimates equal the observed maximum and are not precise
estimates of a production p99. Warm samples are clustered within twenty instances
and use a persistent HTTP client within each trial. Client latency includes local
transport/TLS/IAM/platform overhead as well as application work. No improvement
is claimed: the configuration/image were unchanged and these are different
startup scenarios, not an optimization A/B.

**A: fresh revision with `/health/db` as the first external endpoint remains
unmeasured.** Earlier DB probes followed `/health`; they are not cold-first DB
results. New fresh-revision/tag trials would change resources/configuration and
are prohibited by the latest read-only/no-configuration-change instruction.
The existing ten fresh `/health` samples were reverified on the server clock;
previously excluded prestarted fresh-revision attempts remain excluded.

## Natural startup phase measurements

These are paired timestamps from each accepted instance, all on the server clock.

| Natural startup span | Samples | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Request arrival → instance-start event | 20 | 24.51 | 32.89 | 38.55 |
| Instance-start event → server-process log (combined pre-lifespan) | 20 | 6410.54 | 7465.06 | 7937.37 |
| Application lifespan startup | 20 | 561.68 | 632.28 | 740.87 |
| Startup DB warm-up, upper span | 20 | 118.33 | 133.75 | 150.70 |
| Startup Redis initialization, upper span | 20 | 442.33 | 514.66 | 606.83 |
| Lifespan complete → successful startup probe | 20 | 510.95 | 987.96 | 993.81 |
| Instance-start event → readiness probe succeeds | 20 | 7621.24 | 8128.72 | 9118.44 |

The dominant observed span remains **pre-lifespan: median 6410.54 ms naturally**,
versus 6997.98 ms in the existing fresh cohort. That combines platform/internal
container provisioning and scheduling with Python/Uvicorn imports and application
construction. Pure platform startup, interpreter imports, app factory and route
registration are not individually observable in the deployed logs. The 24.51 ms
request-arrival-to-instance-event median measures only that initial marker gap;
it is not the entire platform startup cost. Readiness takes median 7621.24 ms from
the instance-start marker across both natural endpoint cohorts. Spans overlap;
do not add medians or subtract percentiles to invent a missing component.

All twenty accepted instances have an independently verified successful Redis
connection log. Initial DB acquisition/TLS/SELECT/cleanup is inside the 118.33 ms
DB warm-up upper span; initial Redis import/DNS/TLS/auth/PING is inside the
442.33 ms Redis upper span. Existing telemetry cannot separate each sub-operation.

| Request-level Server-Timing, p50 | App ms | DB acquisition ms | DB query ms |
| --- | ---: | ---: | ---: |
| Cold-first external `/health` | 0.275 | 0.000 | 0.000 |
| Cold-first external `/health/db` | 14.850 | 9.000 | 4.475 |
| Warm `/health` | 0.290 | 0.000 | 0.000 |
| Warm `/health/db` | 14.350 | 9.015 | 4.410 |

Request-level DB acquisition is measured **after lifespan warmed the pool**;
the 9 ms result is not the first TLS/database connection time. `/health` does
not issue DB/Redis queries. Server-Timing does not attribute all external latency;
warm client tails must not be interpreted as equally slow database queries.

The observer sent no HTTP requests during idle intervals. Before each trial it
required explicit active=0 **and** idle=0 observations; termination logs were
also checked. Final lifecycle revalidation confirms every prior known instance
had finished before each accepted new external request. Cloud Monitoring samples
can lag, so active=0 by itself was never accepted as proof of shutdown.
Each accepted request maps to a new AUTOSCALING event inside its trace-correlated
server HTTP arrival/response interval; first-trial evidence was independently
revalidated from its unique instance/request. No cross-clock subtraction was used.
[Metric timing/state definitions](https://docs.cloud.google.com/monitoring/api/metrics_gcp_p_z).

## Individual natural cold requests

All values below are milliseconds. Ready is instance-start event → startup probe
success; it overlaps the preceding phase columns. Full request-level timings
are also saved as JSON and CSV.

| Trial | External first endpoint | First HTTP | Pre-lifespan | Lifespan | DB warm-up | Redis init | Ready |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `/health` | 8382.75 | 6584.99 | 525.59 | 118.64 | 406.82 | 8104.42 |
| 2 | `/health/db` | 8348.61 | 6972.50 | 559.25 | 117.67 | 441.34 | 8095.40 |
| 3 | `/health` | 8387.02 | 7117.80 | 632.28 | 150.70 | 481.18 | 8128.72 |
| 4 | `/health/db` | 7343.36 | 5740.22 | 502.63 | 125.38 | 376.64 | 7106.30 |
| 5 | `/health` | 8335.50 | 6741.24 | 589.98 | 118.02 | 471.81 | 8114.85 |
| 6 | `/health/db` | 9818.18 | 7465.06 | 592.73 | 120.59 | 471.93 | 8114.59 |
| 7 | `/health` | 8418.12 | 7312.87 | 603.36 | 119.80 | 483.51 | 8115.93 |
| 8 | `/health/db` | 7427.10 | 5628.69 | 513.51 | 111.40 | 401.94 | 7126.48 |
| 9 | `/health` | 7783.12 | 6252.68 | 574.12 | 114.52 | 459.57 | 7103.53 |
| 10 | `/health/db` | 6425.54 | 5507.50 | 477.19 | 96.31 | 380.65 | 6127.80 |
| 11 | `/health` | 7435.82 | 6180.07 | 624.29 | 129.71 | 494.09 | 7123.37 |
| 12 | `/health/db` | 7445.79 | 5886.69 | 606.87 | 115.92 | 490.78 | 7147.08 |
| 13 | `/health` | 8486.71 | 6568.41 | 564.11 | 120.64 | 443.31 | 8120.50 |
| 14 | `/health/db` | 8455.75 | 6594.87 | 540.78 | 125.94 | 414.20 | 8113.76 |
| 15 | `/health` | 8391.56 | 6739.25 | 498.75 | 124.56 | 374.00 | 8110.97 |
| 16 | `/health/db` | 7418.23 | 6026.88 | 630.47 | 115.60 | 514.66 | 7115.65 |
| 17 | `/health` | 7555.82 | 5686.48 | 532.70 | 117.64 | 415.03 | 7135.78 |
| 18 | `/health/db` | 6415.94 | 5536.30 | 500.24 | 112.28 | 387.80 | 6105.88 |
| 19 | `/health` | 9429.90 | 7937.37 | 740.87 | 133.75 | 606.83 | 9118.44 |
| 20 | `/health/db` | 6395.72 | 5353.44 | 494.15 | 97.52 | 396.56 | 6112.16 |

## Final verification and infrastructure separation

Configuration fingerprint remained unchanged:
`613b4bea84a9946c701a72ea31f5e006b0f8dfbbfea6e2dc80b8adb9ad2f26a2`.
The serving revision remains `salon-api-mumbai-staging-cold19-20261016`, 100%
traffic, min 0/max 1, 1 vCPU/512 MiB, concurrency 8, request billing, CPU boost off.

Post-study IAM-authenticated health checks below were warm verification requests
using a new client, not extra cold samples:

| Endpoint | HTTP | Status | Client ms |
| --- | ---: | --- | ---: |
| `/health` | 200 | ok | 174.48 |
| `/health/db` | 200 | ok | 63.22 |
| `/health/redis` | 200 | ok | 54.18 |

The separate [ownership/cost audit](infrastructure-ownership-cost-2026-10-16.md)
records the still-running production VM, production DNS → VM IP, staging-only
Cloud Run entry, free allowances, estimated ongoing costs and exact proposed
cleanup commands. Nothing was deleted. VM proxy internals and Upstash account
plan metadata remain explicitly unverified; Cloud Run was not assumed to replace
the VM. No business API/customer data was exercised.

## Recommendations reported before any Cloud Run change

1. **Keep the measured baseline unchanged until a separate optimization experiment is authorized.** Retain min 0/max 1,
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
- [Completed natural results/status](../../.artifacts/cold-start-investigation/natural-results.json)
- [Completed natural CSV](../../.artifacts/cold-start-investigation/natural-results.csv)

Additional evidence: [phase/request analysis](../../.artifacts/cold-start-investigation/natural-analysis.json), [all measured requests CSV](../../.artifacts/cold-start-investigation/natural-requests.csv), [final verification](../../.artifacts/cold-start-investigation/final-verification.json).

Verification covered 20 unique cold instances, both-zero snapshots, all prior terminations, trace/request linkage, 260 successful measured requests and the final three health checks. Only documentation/local measurement helpers changed; no application behavior was modified. Full application/migration tests were not run as part of this read-only study.

No improvement is claimed. No production, VM, Sydney, DNS, frontend URL, migration, stamp,
payment, worker or Cloud Run resource/configuration change was made in this investigation.
The earlier local/deployment report files were absent from the clean `shifan` checkout at
the start of this request; their ignored measurement evidence was available and was reused.
No removed files were restored or unrelated changes overwritten.
