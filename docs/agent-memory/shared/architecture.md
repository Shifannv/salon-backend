# Architecture

Verified against `backend/app/` and `backend/docs/ARCHITECTURE.md`.

```
api -> application -> domain
infrastructure -> application/domain ports
```

- `backend/app/domain/`: pure Python. `entities/`, `value_objects/`, `repositories/` (contracts), `services/` (policies: authorization, booking_policy, checkout, commission, payment_fees, subscription_eligibility).
- `backend/app/application/`: `use_cases/` (authorization lives here), `ports/` (gateways), `dto/`.
- `backend/app/infrastructure/`: adapters. `db/` (SQLAlchemy repos, `set_actor_context`), `supabase/`, `r2/`, `imagekit/`, `push/` (FCM/Expo outbox worker), `payments/`, `cache/` (Redis), `email/`, `media/`, `account_deletion/`, `subscriptions/`.
- `backend/app/api/`: `deps.py` (auth, `require_role`, session scoping), `v1/routes/`, `v1/schemas/`.
- `backend/app/core/`: config, exceptions (mapped to HTTP once globally), security (JWKS), logging, pagination.
- Entry point: `backend/app/main.py`. Health routes: `/health`, `/health/db`, `/health/redis`.
- Clients: customer app, owner app, admin website, walk-in QR website. All call this one `/v1` API. Frontends live in separate repos.
