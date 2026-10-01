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
- Deduplicates booking submissions via the `Idempotency-Key` HTTP header.
- Throttles sensitive endpoints (e.g. walk-in OTP verification) using atomic Redis counters.
- Gracefully degrades to a no-op if `REDIS_URL` is omitted or Redis is unreachable.
