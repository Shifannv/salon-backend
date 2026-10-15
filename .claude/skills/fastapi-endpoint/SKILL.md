---
name: fastapi-endpoint
description: Use when adding or changing a FastAPI endpoint in this repo. Gives the layer-by-layer recipe (schema, route, use case, port, adapter, tests, error mapping) and a checklist.
---

# Adding an endpoint

Work inward-to-outward so dependencies always point inward. Paths are under `backend/app/`.

## Recipe

1. **Domain** (`domain/`): new entity, value object or policy only if a business rule is needed. Pure Python, no FastAPI/SQLAlchemy/Supabase/Firebase imports, no HTTP schemas.
2. **Port** (`application/ports/` or `domain/repositories/`): add the method to the existing repository/gateway contract. One contract per concern.
3. **Use case** (`application/use_cases/`): the method that does the work. Authorization and ownership checks go here. Raise typed errors from `core/exceptions.py`. Do not touch HTTP types.
4. **Adapter** (`infrastructure/db/repositories/...`): implement the port. Scope queries by actor or owned resource. Use `get_available_slots` and `create_booking` for availability and booking. No schema changes; no `INSERT` into `bookings`/`booking_services`.
5. **Schema** (`api/v1/schemas/`): Pydantic v2 request/response models. Validate input here (lengths, enums, ranges). Never echo internal fields.
6. **Route** (`api/v1/routes/`): thin. Declare `response_model`, `status_code`, `tags`, `summary`. Use `require_role(...)` and the authenticated session dependency from `api/deps.py`. Register in `api/v1/router.py` if the module is new.
7. **Errors**: add a typed exception in `core/exceptions.py` only if none fits; it is mapped to HTTP once globally. Never pass `str(db_error)`, SQL fragments or constraint names to a response. Map DB conflicts (e.g. slot taken) to 409 with a stable error code.
8. **Tests**: see `pytest-testing`. Role matrix per `auth-and-roles`.
9. **Docs**: update `backend/docs/` or `docs/frontend-integration.md` only if the contract changed.

## Checklist

- [ ] `response_model` and `status_code` set
- [ ] Role dependency and use-case ownership check both present
- [ ] Queries scoped by actor or `salon_id`; public reads use the approved+active+profile_completed gate
- [ ] No raw DB error text can reach a response
- [ ] List endpoints take bounded `limit`/`offset` (`Query(..., ge=, le=)`) and have a deterministic `ORDER BY`
- [ ] Mutations on cached data (`salon:{id}:*`, `walkin:qr:{token}`) invalidate the cache
- [ ] Soft delete via `is_active`; no hard delete
- [ ] Tests: success, validation error, each denied role, other owner's resource, 404/409 paths
- [ ] `python -m ruff check app tests migrations` and `python -m pytest -q` pass (from `backend/`)

## Anti-patterns

- Authorization in the router or repository.
- Computing slots or prices in Python when Postgres owns them.
- A new abstraction for a single endpoint.
