---
name: pytest-testing
description: Use when writing, fixing or running tests in this repo. Covers pytest-asyncio patterns, fixtures, domain unit tests, use-case tests with fake ports, API tests, booking concurrency tests, and real DB versus fakes.
---

# Testing

Config: `backend/pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`). Run from `backend/`: `python -m pytest -q`; one file: `python -m pytest tests/unit/test_x.py -q`.

## Layers

- **Domain** (`domain/`): pure unit tests, no mocks, no fixtures beyond data builders.
- **Use cases** (`application/use_cases/`): construct the use case with fake or `MagicMock`/`AsyncMock` ports (`make_mock_repo`, `make_profile`, `make_owner`, `make_super_admin`, `make_booking` in `tests/conftest.py`). Assert authorization outcomes and the calls made to ports. Examples: `tests/unit/test_booking_use_cases.py`, `test_owner_use_cases.py`.
- **API** (`tests/test_api_contract.py`, `tests/unit/*_api.py`): FastAPI `TestClient` or `httpx.AsyncClient` with dependency overrides for actor and session. Assert status code, response shape and that error bodies contain no SQL.
- **Repository / SQL behavior** (`tests/integration/`): real PostgreSQL, enabled by `MIGRATION_TEST_DB` (skipped otherwise; CI provides it). Use for `create_booking`, `get_available_slots`, triggers, RLS, erasure, migrations.

## Rules

- `async def test_...` needs no decorator in auto mode.
- Prefer fakes over patching internals; patch at the port boundary.
- One behavior per test; name it `test_<unit>_<condition>_<result>`.
- A bug fix starts with a failing test that reproduces it.
- Do not weaken or delete an existing test to get green; report it.
- No real network, Supabase, R2, FCM or payment provider calls. Use `httpx.MockTransport` or fake gateways.
- No real secrets or PII in fixtures.

## Role matrix

For protected endpoints cover anonymous, customer, owner (own and another's resource), staff, super_admin with and without `aal2`. See `auth-and-roles`.

## Booking concurrency test

Needs a real DB. Create two sessions, call `create_booking` for the same staff and overlapping slot concurrently with `asyncio.gather`, assert exactly one success and the other maps to a conflict. Pattern lives in `tests/integration/test_checkout_safety_sql.py`; add near it.

## Real DB vs fakes

Fakes when testing policy and mapping. Real DB when the behavior lives in SQL (functions, triggers, constraints, RLS, migration chain). Never mock `create_booking` and call it a booking test.

## Before finishing

`python -m ruff check app tests migrations` and `python -m pytest -q`. Report skips honestly; many integration tests skip without `MIGRATION_TEST_DB`.
