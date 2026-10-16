# Mumbai Cloud Run staging deployment — 16 October 2026

Staging is deployed and verified. Ten request-initiated cold starts have client-observed
**p50 8386.97 ms, p95 13815.61 ms, p99 13815.61 ms**. Nine prestarted trials are excluded
from those percentiles. This is a small first-instance-per-revision experiment, not a
production SLO or a measurement of a previously used revision naturally idling to zero.

## Final deployment

| Setting | Verified value |
| --- | --- |
| Project | `saloon-505509` |
| Region | `asia-south1` |
| Artifact Registry repository | `salon-mumbai-staging` |
| Service | `salon-api-mumbai-staging` |
| URL | `https://salon-api-mumbai-staging-jmqpp743pa-el.a.run.app` |
| Alternate service URL | `https://salon-api-mumbai-staging-283739091709.asia-south1.run.app` |
| Serving revision | `salon-api-mumbai-staging-cold19-20261016`, 100% staging traffic |
| Service created | `2026-10-16T11:57:06.784343Z` |
| Final verification started | `2026-10-16T12:09:09.579008Z` (17:39 IST) |
| Runtime identity | `salon-api-mumbai-staging@saloon-505509.iam.gserviceaccount.com` |
| Minimum instances | 0, effective service/revision default; never raised |
| Maximum instances | 1 at service and revision levels |
| CPU / memory | 1 vCPU / 512 MiB |
| Concurrency | 8 |
| Billing / CPU | Request-based, CPU throttling enabled |
| Startup CPU boost | Disabled |
| Invocation | IAM required; unauthenticated GET returns 403 |
| Execution environment | Gen2 |
| Container port | 8000, Cloud Run supplies `PORT` |
| Request timeout | 60 seconds |
| Startup probe | HTTP `/health`, port 8000, 1-second interval/timeout, failure threshold 60 |

Immutable deployed image:

```text
asia-south1-docker.pkg.dev/saloon-505509/salon-mumbai-staging/api@sha256:38ff423fbde6697e71a720c6f0506b0c0ec99ef0a80d8e11006bea9c2ad6b2a2
```

Source HEAD: `5df98ee125dca36bbbbb67aa0f220ec0585403c9`. Application code was not changed.
The image was built locally using `backend/` as context, from the existing Dockerfile
plus a staging-only layer containing the public Supabase database CA. No Cloud Build job
or worker was created. Startup remains a single Uvicorn process, binding `0.0.0.0` and
reading `${PORT:-8000}`. There is no Gunicorn or reload flag and no migration command.

The CA download is pinned to SHA-256
`700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.
An initial build rejected a byte-hash mismatch caused by CRLF versus LF; DER comparison
proved the local/downloaded certificates identical before pinning the downloaded bytes.
Runtime uses `DB_SSL_CA_FILE=/app/certs/supabase-ca.crt`, `DB_SSL_STRICT=true`.

## Configuration and secrets

The original Compose stack and its environment were inspected but not started, stopped,
or changed. The main Compose file loads `.env`, starts workers and waits for Redis health;
it is not the Cloud Run deployment input. The separate existing test Compose file was
not reused. No tracked default override was found during the earlier startup inspection.

Four newly created secrets use user-managed replication in `asia-south1`; each is pinned
to version **1** in the revision:

| Environment variable | Secret name |
| --- | --- |
| `DATABASE_URL` | `salon-mumbai-staging-database-url` |
| `REDIS_URL` | `salon-mumbai-staging-redis-url` |
| `SUPABASE_ANON_KEY` | `salon-mumbai-staging-supabase-anon-key` |
| `SUPABASE_SERVICE_ROLE_KEY` | `salon-mumbai-staging-supabase-service-role-key` |

Values were read from user-authorized secure local configuration and passed to gcloud
through stdin in memory. They were not placed in command arguments, artifacts or Git.
Only the dedicated runtime identity received an explicit Secret Accessor binding on each
secret. The tester received `roles/run.invoker` on this staging service. Existing deployer
Owner access was sufficient; no additional project-wide deployer role was granted.
Final service IAM has no `allUsers` or `allAuthenticatedUsers` binding.

`ENVIRONMENT=staging`, a nonexistent `SALON_ENV_FILE`, empty CORS origins, and the Mumbai
Auth/JWKS URLs are explicit nonsecret configuration. Database pool size is 5 with overflow
5, acquisition timeout 10 seconds, connection timeout 10 seconds and recycle 1800 seconds.
Supabase project `wqjlgpnbiapcrlkxumcp`, both key claim references and key roles matched.
The session pooler is in `ap-south-1`, port 5432, scoped to that project. A strict-TLS
`SELECT 1` preflight passed inside an explicitly read-only transaction. No schema or
business-data change was performed. The initial startup-setting-only read-only assertion
was insufficient through the pooler; the explicit read-only transaction was used instead.

Payments and subscriptions are `none`, Cashfree/live flags are false, and no email,
Firebase, R2 or Sentry credentials were supplied. Only the API is deployed. The image
contains migration files as usual but does not execute them.

## Existing Upstash validation

The existing `salon-mumbai-staging` database was used. Its Free plan and Mumbai
`ap-south-1` region were confirmed by the user; independent account metadata was
unavailable. No Upstash database creation, plan change or paid upgrade was attempted.
No endpoint hostname, URL, credential or token is recorded in this report.

Validation passed on the workstation and inside the deployed Python 3.12 image:

- Upstash DNS resolution; `rediss://` TCP connection with authentication, no REST URL.
- TLS 1.3, trusted certificate and hostname verification. Redis client defaults require
  certificates and hostname checks; no URL query options disabled those settings.
- Authenticated PING, SET/GET/DEL, expiry and atomic SET NX behavior.
- Current `redis-py` **8.1.0** and the repository's actual async `RedisCache` adapter.
- Cache idempotency round-trip and its 60-second TTL; this is not a booking replay test.
  Durable booking idempotency remains PostgreSQL-owned.
- Validated read-model fill through the real Lua script, epoch invalidation, subsequent
  miss/refill, SCAN/prefix deletion and atomic rate-limit counters.
- Every synthetic key was removed. A wrapper prefixed all test keys, including the epoch
  and Lua KEYS, so validation did not invalidate the shared application namespace.

| Local Redis measurement | Samples | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| Workstation TCP + verified TLS setup | 5 | 115.93 | 122.30 | 122.30 |
| Workstation warm authenticated PING | 30 | 42.68 | 48.51 | 53.63 |
| Python 3.12 Docker TCP + TLS setup | 5 | 128.80 | 164.62 | 164.62 |
| Python 3.12 Docker warm PING | 30 | 40.53 | 44.72 | 45.64 |

These Redis numbers are from the local machine, not intra-region Cloud Run command latency.
An existing `SETEX` deprecation warning did not prevent compatibility checks from passing.

## Authenticated cold-start method and results

Image build, push, deployment operations, gcloud token minting and IAM setup were outside
request timing. Identity tokens stayed in process memory. HTTPX measured monotonic wall
time until the complete HTTP response, including client DNS/TCP/TLS, network transit,
Cloud Run admission/startup, application lifespan and health handler work. Each trial
used a new HTTP client. Five later warm requests per endpoint reused that client's connection.

The lifespan warms the database connection before initializing Redis. `/health` returns
process health, `/health/db` executes `SELECT 1`, and `/health/redis` must report Redis
actually reachable; a disabled-cache HTTP 200 is not accepted.

Deployment-time health prewarming was disabled. Revisions 2–10 still had instance-start
timestamps preceding the timed requests and were excluded from cold results. Trial 1 and
tagged no-default-traffic trials 11–19 were verified cold. For every accepted sample:

1. The client request ID matched the application log's intended revision and instance ID.
2. Cloud Run logged `AUTOSCALING` for that instance.
3. The instance-start timestamp fell between the client request's start and completion.
4. The authenticated first request returned HTTP 200.

This cross-system correlation assumes workstation and Cloud Run UTC clocks are aligned;
the latency duration itself uses the workstation monotonic clock. All ten accepted samples
have distinct instance IDs. All measured requests matched their intended revisions.

| Verified cold `/health` request | Samples | p50 ms | p95 ms | p99 ms | Min ms | Max ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Complete client response time | 10 | **8386.97** | **13815.61** | **13815.61** | 6298.14 | 13815.61 |

Percentiles use nearest-rank tails and an ordinary median. With ten cold observations,
p95/p99 both equal the measured maximum; they do not establish a reliable tail-latency SLO.
These are first-instance starts for fresh revisions, not repeated post-idle starts of the
same revision. Scale-to-zero is configured; natural idle termination was not timed.

Warm results include all 19 successful rounds, including the rounds excluded only from
the cold distribution:

| Endpoint | Samples | p50 ms | p95 ms | p99 ms |
| --- | ---: | ---: | ---: | ---: |
| `/health` | 95 | 56.84 | 70.82 | 109.64 |
| `/health/db` | 95 | 72.36 | 91.70 | 155.32 |
| `/health/redis` | 95 | 61.65 | 103.38 | 295.36 |

All **342** authenticated measurement requests succeeded, including **285** warm requests;
all 19 unauthenticated checks returned 403. After measurement, all nine temporary tags
were removed, staging traffic was set to revision 19, and all three health endpoints
returned 200 again. Final anonymous access returned 403. Minimum instances stayed zero.

## Evidence, costs and verification limits

Local ignored evidence under `backend/.artifacts/cloud-run-staging/`:

- [Redis validation](../../.artifacts/cloud-run-staging/redis-validation.json),
  [Docker Redis validation](../../.artifacts/cloud-run-staging/redis-validation-docker.json),
  [read-only database validation](../../.artifacts/cloud-run-staging/database-validation.json).
- [All request timings JSON](../../.artifacts/cloud-run-staging/cloud-run-measurements.json),
  [CSV](../../.artifacts/cloud-run-staging/cloud-run-measurements.csv).
- [Audited cold distribution and exclusions](../../.artifacts/cloud-run-staging/cold-start-audit.json),
  [instance-start logs](../../.artifacts/cloud-run-staging/instance-start-evidence.json),
  [request-ID/revision/instance evidence](../../.artifacts/cloud-run-staging/app-request-evidence.json).
- [Final configuration, scoped IAM and HTTP verification](../../.artifacts/cloud-run-staging/final-verification.json).
- Reproduction scripts, generated staging Dockerfile and nonsecret environment configuration
  are in the same ignored directory. Raw first-invocation summaries in the measurement JSON
  include prestarted trials; use `cold-start-audit.json` for cold percentiles.

The approved cost model remains approximately $0.091 per active instance-hour, $0.10/month
per 1 GiB of registry storage and $0.24/month for four active secret versions, before free
allowances. The earlier one-active-hour/one-month scenario is approximately **$0.43** for
those line items. Redis remains the user-confirmed Free plan. This is an estimate, not an
invoice or spending cap; transfer, logging, tax and existing Supabase charges are separate.
See [Cloud Run pricing](https://cloud.google.com/run/pricing),
[Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing) and
[Secret Manager pricing](https://cloud.google.com/secret-manager/pricing).

Verification: **12 health/cache tests passed**, one existing dependency deprecation warning;
Ruff passed for `app tests migrations` and the earlier local benchmark runner. Full integration
and migration tests were not run under the no-migrations instruction. This deployment does
not establish booking, payment-provider, email, notification or customer-app acceptance.

No VM change, production deployment, Sydney access, DNS/frontend URL change, migration,
stamp, worker deployment, Memorystore creation or credential commit was performed. Existing
local containers and unrelated uncommitted files were preserved. Work remains uncommitted
on `thameem/cloud-run-mumbai-staging`.
