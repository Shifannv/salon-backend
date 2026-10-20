# Startup profile baseline and import review — 20 October 2026

Priorities 1 and 2 of the [remediation plan](cloud-run-cold-start-remediation-plan-2026-10-20.md),
plus Cloud Run cold trials on tagged, no-traffic revisions. No application code was
changed. Production traffic and its serving revision were not changed.

## Result

- **Priority 1 done:** `scripts/startup_profile.py` gives a repeatable phase profile in
  fresh interpreters, and a `--serve` mode for a diagnostic Cloud Run revision.
- **Priority 2: no import change is worth making.** No deferrable import contributes
  meaningful time. The cost is fixed library imports plus route and schema construction.
- **Cloud Run:** the current 5-second startup probe adds about 3 s to every cold start
  (median server latency 10.19 s). A 1-second probe gave 7.19 s. The 3–5 s target is not
  met; imports and app construction (about 5.4 s) are now most of what remains.
- **Production risk found:** the Supabase session pooler allows 15 clients, which equals
  production's maximum connection budget (5 per instance, up to 3 instances).
- **Round 2:** a code change (deferred imports, env-file prefetch, concurrent warm-up)
  saved about 0.7 s on Cloud Run. Combined with a TCP probe on gen1, the median cold
  start fell from 10.19 s to 5.89 s on the server (10.70 s to 6.37 s for the client).

## Profiler

```bash
# Local, from backend/: no env file, no DB or Redis
SALON_ENV_FILE=/nonexistent ENVIRONMENT=test python scripts/startup_profile.py --trials 20 --out profile.json
# Add --dependencies to also time DB warm-up and Redis init with the configured settings.
```

Each trial is a new process that imports the stack in a fixed order. A phase's time is its
extra cost given earlier phases. Output holds phase names and durations only.

`--serve` logs one `startup_profile` JSON line, then serves the app on `$PORT` and logs a
`startup_profile_lifespan` line with `lifespan_ms` (DB warm-up plus Redis init, before the
port opens) and `since_entry_ms`. It is for an isolated diagnostic revision only: the
script is not in the production image, so it must be copied into a diagnostic image.

## Local baseline

Windows workstation, Python 3.12.13, 20 trials, all succeeded. Cloud Run's 1 vCPU was
roughly 2.5 times slower in the 19 October diagnostics; do not apply that ratio as a rule.

| Phase | Median ms | p95 ms | Max ms |
| --- | ---: | ---: | ---: |
| Interpreter start | 78 | 101 | 111 |
| uvicorn | 251 | 403 | 623 |
| fastapi (with pydantic, starlette) | 488 | 656 | 758 |
| sqlalchemy (async) | 393 | 503 | 517 |
| settings | 63 | 88 | 105 |
| deps (`app.api.deps`) | 433 | 553 | 687 |
| routes (`app.api.v1.router`) | 463 | 515 | 976 |
| app (`app.main`, builds the app) | 132 | 165 | 261 |
| **Total in process** | **2316** | **3002** | **3170** |

In one `--serve` run, Uvicorn's own setup after these phases added about 0.5 s before the
lifespan started.

## Import review

Ranked self time by package, median of three `-X importtime` runs of `import app.main`:
app modules 594 ms, SQLAlchemy 441, FastAPI 166, Pydantic 134, cryptography 106,
opentelemetry 47, asyncio 46, httpx 40.

| Candidate | Cost (local) | Loaded by | Decision |
| --- | ---: | --- | --- |
| `jose` + `cryptography` | ~160 ms | `app.core.security` (JWT verifier) | Keep. JWT verification must not be deferred; most first requests carry a token anyway. |
| `opentelemetry` | ~47 ms | FastAPI's own `fastapi.telemetry` | Not ours to change. |
| `httpx` | ~40–77 ms | security (JWKS), Supabase gateways | Keep. Needed by the first authenticated request. |
| `structlog` | ~36 ms | `app.core.logging` | Keep. Used at startup. |
| `email_validator` | ~26 ms | Pydantic `EmailStr` in schemas | Keep. Needed to build schemas. |
| `PIL` | ~31 ms | `app.infrastructure.r2.storage` | Deferrable to first upload, but too small to matter. |
| `segno` | ~20 ms | `app.core.qr` | Deferrable to first QR request, but too small to matter. |

Our own module time is mostly construction, not imports: about 165 ms registering 138
routes (FastAPI 0.143 does not copy routes on include, so none are duplicated) and about
120 ms defining 134 Pydantic models. Deferring PIL and segno would save about 50 ms locally,
roughly 2% of in-process startup, and add that time to the first upload or QR request.
Under the plan's rule ("confirm it contributes meaningful measured time"), neither change
is made.

## Cloud Run cold trials

The staging service no longer exists, so trials ran as tagged, no-traffic revisions of
`salon-api-production`, as on 19 October. Production traffic stayed 100% on
`salon-api-production-00004-nx7` throughout.

**Method.** Diagnostic image `api:startup-profile-20261020`
(`sha256:1d5a3c8d…332f`): the production image digest `sha256:e3893bd0…b9ea` plus
`scripts/startup_profile.py`, run with `--serve`. Each trial was a new revision with
revision minimum 0 and deployment prewarming off (`--no-deploy-health-check`), so the
first request started the instance. Ten rounds alternated the current probe (5 s period,
3 s timeout, threshold 24) with a 1-second probe (1 s period and timeout, threshold 120;
same 120 s allowance). The client was curl on this workstation calling `GET /v1/salons`
on the tagged `run.app` URL, followed by three warm requests. A trial counts only if the
logged AUTOSCALING instance start came after the client request and the request returned
200. Times combine Cloud Run log timestamps with the profiler's own durations.

### Results

| Variant | Confirmed cold 200s | Client total, median (min–max) | Server latency, median (min–max) |
| --- | ---: | ---: | ---: |
| 5 s probe (current) | 5 | 10.70 s (10.51–11.62) | 10.19 s (10.18–10.25) |
| 1 s probe | 6 | 7.57 s (5.61–8.68) | 7.19 s (5.19–7.28) |

Where the server time goes (medians):

| Step | 5 s probe | 1 s probe |
| --- | ---: | ---: |
| Instance start to Python entry | 0.38 s | 0.29 s |
| Imports and app construction | 6.37 s | 5.36 s |
| Uvicorn setup | 0.19 s | 0.17 s |
| Lifespan (DB warm-up + Redis init) | 0.48 s | 0.46 s |
| **Wait for a passing probe** | **2.60 s** (max 4.35) | **0.72 s** |
| First request after probe | 0.12 s | 0.15 s |

Import phases on Cloud Run, 1 s probe medians: fastapi 1092 ms, deps 947, routes 785,
uvicorn 727, sqlalchemy 721, settings 484, app 192. That is about 2.3 times the local
baseline, except `settings` (484 ms against 63 ms locally, about 7.7 times). Production
reads its configuration from a Secret Manager volume at settings load, which is a likely
but unproven cause.

### What this shows

- **The 5-second probe costs about 3 s per cold start.** Readiness is rounded up to the
  next probe check, so server latency sits at about 10.2 s whatever the import time. A
  1-second probe brings the median to 7.2 s. This is the largest single gain measured and
  needs no code change (Priority 4).
- **Imports and app construction are now about 75% of the remainder.** The DB and Redis
  warm-up takes about 0.5 s, so overlapping them (Priority 3) can save at most about
  0.2–0.3 s.
- **3–5 s is at the limit of this stack on 1 vCPU.** uvicorn, FastAPI and SQLAlchemy alone
  take about 2.5 s. Adding instance start, lifespan, probe and request gives about 4 s
  before any of our own code. One trial reached 5.19 s on the server (5.61 s client) when
  imports happened to take 3.7 s.

### Excluded trials and the pooler limit

Rounds 6–10 failed (500, then 503) and are excluded. From round 6 the trial instances got
`EMAXCONNSESSION max clients reached in session mode - max clients are limited to
pool_size: 15` from the Supabase session pooler. Each idle trial instance kept its DB
connections for about 9 minutes after its requests. Production returned no 5xx in that
window, because it kept the connections it already held.

The same limit is a production risk. Production allows 5 connections per instance
(`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`) and up to 3 instances, which is exactly 15. Any
other session-mode client, or old and new instances overlapping during a rollout, can push
past it and make new instances return 500s. Before raising maximum instances or
concurrency, check the pooler size or move the API to the transaction pooler.

Separately, one `GET /health/redis` on production returned 503 at 07:40 UTC; three
retries a minute later returned 200. Logs do not show whether this was related to the
trials.

### Cleanup

All 20 trial tags were removed. The service template was reset from `00004-nx7`: the
production image digest, no command override, the 5 s / 3 s / 24 probe, deployment
prewarming on, gen2, 1 CPU / 512 MiB, concurrency 8, CPU boost and max 3. The reset
created revision `salon-api-production-restore-10200734` with 0% traffic. Service minimum
stays 1, and `https://apiv1.mudassirmhd.in/health` returned 200 afterwards. The trial
revisions and the diagnostic image tag are kept for inspection.

Local evidence (ignored by Git): `backend/.artifacts/cloud-run-startup-profile-2026-10-20/`
holds the raw trial lines, per-trial analysis, local baseline, runner, analyzer and
diagnostic Dockerfile.

## Round 2: probe type, runtime and code change

Same method as above, with one change to protect the pooler: each trial revision was
untagged after measuring and deleted after the next trial, so at most two trial
instances held connections. All 40 trials below returned 200 and were confirmed cold.

### Infrastructure variants (production image, profiler with library phases)

| Variant | Trials | Server, median (p95) | Client, median |
| --- | ---: | ---: | ---: |
| HTTP probe every 1 s, gen2 | 6 | 7.22 s (8.25) | 7.78 s |
| TCP probe, gen2 | 6 | 7.13 s (10.77) | 7.63 s |
| TCP probe, gen1 | 6 | 6.67 s (7.67) | 7.15 s |

The TCP probe (port 8000, 240 s timeout) passes as soon as Uvicorn opens the port, and
Uvicorn opens it only after the lifespan finishes, so readiness is not reported early.
Probe wait fell to 0.00 s.

### Measured cost on Cloud Run (6 trials, medians)

| Item | Cloud Run | Local |
| --- | ---: | ---: |
| Env file first read (`/secrets/runtime.env`, Secret Manager volume) | 289 ms | 0.1 ms |
| `jose` + `cryptography` | 278 ms | 102 ms |
| `httpx` | 139 ms | 60 ms |
| Pillow | 65 ms | 17 ms |
| segno | 42 ms | 20 ms |

### Code change

1. `jose`, `httpx`, Pillow and segno are imported on first use (JWT verification,
   outbound HTTP calls, image processing, QR generation) instead of at app import.
   `tests/unit/test_startup.py` fails if any of them, or `cryptography`, loads with
   `app.main` again.
2. `app/main.py` starts reading `SALON_ENV_FILE` in a background thread before the
   framework imports, so the secret-volume fetch overlaps them. Contents are discarded;
   settings load reads the file as before.
3. The lifespan runs the DB warm-up and Redis init concurrently. Each still logs its own
   failure without stopping the other (covered by two new tests).

Local A/B (`git archive HEAD` against the working tree, minimal phases, 2 × 10 trials):
in-process startup 1.97 s before, 1.65 s after.

### Cloud Run A/B (TCP probe, gen1, 8 trials each, alternating)

"Before" is the production image; "after" is the same image with only `app/` replaced.
Both ran the profiler with `STARTUP_PROFILE_PHASES=app`, so it did not pre-load the
deferred libraries.

| Image | Server, median (p95) | Client, median (min–max) | App import, median |
| --- | ---: | ---: | ---: |
| Before | 6.61 s (7.84) | 7.06 s (5.68–8.58) | 4.47 s |
| After | **5.89 s** (7.14) | **6.37 s** (5.59–7.73) | 3.81 s |

The code change saved about 0.7 s of median server time. Lifespan time hardly changed
(0.47 s to 0.45 s), so concurrent warm-up is a small part of that saving. With 8 trials
per image the ranges overlap; treat 0.7 s as an estimate, not a guarantee.

### Combined effect

Against current production (5 s HTTP probe, gen2, current code: 10.19 s server and
10.70 s client median), TCP probe on gen1 with the code change measured 5.89 s server and
6.37 s client: about 4.3 s, or 42%, faster. The 3–5 s target is still not met at the
median. The fastest single trial was 5.12 s on the server.

### Cleanup

The service template was reset to the production configuration after each round
(latest reset: `salon-api-production-restore-10201032`, 0% traffic). All round 2 trial
revisions and tags were deleted. Traffic stayed 100% on `00004-nx7`. Diagnostic image
tags `startup-profile-20261020b`, `-20261020c`, `ab-before-20261020` and
`ab-after-20261020` remain in Artifact Registry.

## Recommended next steps

1. **Release the code change** through the normal review, image build and deploy.
2. **Production configuration**, which needs approval: TCP startup probe
   (`tcpSocket.port=8000`, timeout and period 240 s, threshold 1) and the gen1
   runtime. Gen1 ran all 26 gen1 trials here without errors, but run the full app
   checks on gen1 before switching.
3. **Pooler:** decide the DB connection budget before raising maximum instances or
   concurrency.
4. **Further code work:** the remaining app import is about 3.8 s on Cloud Run.
   Getting under 5 s at the median needs roughly another 1 s, mostly from FastAPI,
   SQLAlchemy and our own route and schema construction.
