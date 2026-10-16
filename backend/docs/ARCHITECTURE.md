# Architecture

The service uses clean architecture:

```text
HTTP -> api -> application -> domain
                         ^
                         |
                  infrastructure
```

- `domain/` is pure Python and contains entities, values, repository contracts, and
  business rules.
- `application/` contains use cases, authorization, DTOs, and external-service ports.
- `infrastructure/` implements database, Supabase, R2, Firebase, and cache adapters.
- `api/` contains FastAPI routes, HTTP schemas, authentication extraction, and wiring.

Routers authenticate and delegate. Use cases authorize and coordinate. Repositories
perform data access. Typed application errors are mapped to HTTP responses centrally.

Booking creation and availability remain in Postgres because concurrent allocation
requires database-level consistency. Python must not insert directly into `bookings` or
`booking_services`, and must not calculate available slots.

## Caching and Idempotency

Redis is integrated through `app/application/ports/cache_gateway.py` and implemented
by `app/infrastructure/cache/redis.py`:

- Caches read-heavy public endpoints (categories, subcategories, salon services, and staff).
- Booking submissions use the existing PostgreSQL idempotency ledger, including QR
  submissions scoped by actor and hashed QR token. Redis is not booking replay authority.
- Throttles sensitive endpoints (e.g. walk-in OTP verification) using atomic Redis counters.
- Payload reads bypass Redis if it is omitted, unreachable or cannot be validated.
  Configured clients survive startup failures and retry on the next read or health ping.

Booking and availability payloads are never cached. Public salon, service, staff,
catalog and QR payload keys use `read-model:v2:<snapshot hash>:<Redis epoch>:<key>`.
Before looking up a payload, the route's existing READ COMMITTED primary session reads
`pg_current_snapshot()` without assigning an XID. A committed write changes snapshot
visibility even when its process loses Redis or exits before invalidation. Own writes,
replica sessions, older isolation snapshots and validation failures bypass caching.
Publication checks still run on cache hits. No schema change or additional grant is needed.

Failed invalidation logs a warning and marks the process's public read namespace unsafe.
A subsequent validated read or health ping retries the epoch change before recovery.
Late fills remain bound to their captured generation; old generations expire by TTL.
Explicit erasure deletes both v1/v2 generations and preserves strict failure propagation.
Idempotency and rate-limit keys are not flushed by recovery.

This conservative validation adds one database query to each eligible cached read and
may miss after unrelated database writes. Deploy all API/worker processes together:
legacy readers do not acquire validation from a new writer. After database restore or
switching clusters, rotate/clear the public read namespace before admitting readers.
See [recovery verification](verification/mumbai-redis-recovery-2026-10-16.md) for evidence,
local reproduction, latency limits and rollback.
