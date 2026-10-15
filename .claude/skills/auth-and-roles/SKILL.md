---
name: auth-and-roles
description: Use when touching JWT verification, roles, MFA (aal2), ownership checks or any new protected endpoint. Covers the auth flow, where checks belong, and the role test matrix.
---

# Auth and roles

## Flow

1. Client sends `Authorization: Bearer <Supabase JWT>`.
2. `core/security.py` verifies the signature against Supabase JWKS.
3. The verified `sub` is resolved to `profiles.id`. The role is read from `profiles`; JWT role claims are never trusted.
4. `api/deps.py`: `get_current_actor` loads the profile, `get_authenticated_session` sets `SET LOCAL request.jwt.claims = '{"sub": "<uuid>"}'` once per request so audit triggers stamp the actor. `require_role(*roles)` gates the route.
5. Roles: `customer`, `owner`, `staff`, `super_admin`. For `super_admin`, `require_role` also demands `aal2` from the verified claims when `ADMIN_REQUIRE_MFA=true`; otherwise 403 `mfa_required`.

## Where checks go

- Route: coarse role gate via `require_role`.
- Use case: the real decision. Ownership (owner of this salon, staff of this salon, customer owns this booking), state checks, and cutoff rules. This is where IDOR is prevented.
- Repository: scope queries by actor/resource but do not decide policy.
- RLS: defense in depth only; never the sole control.
- Public salon reads require `approval_status='approved'`, `is_active` and `profile_completed`.

## Rules

- Never accept a user id for "me" operations from the body; use the verified actor. Account deletion targets the JWT `sub` only.
- Return 404 (not 403) for another tenant's resource when existence should not leak, matching neighbouring endpoints.
- Super-admin-only fields (discovery placement, visibility, approval) must be rejected for owners even if sent.
- Unauthenticated routes are exceptions: `/health*`, deletion status (HMAC token), `/v1/webhooks/{provider}` (provider signature). Do not add more without review.
- Never log tokens or full claims.

## Test matrix (every protected endpoint)

| Actor | Own resource | Another owner's resource |
|-------|--------------|--------------------------|
| anonymous | 401 | 401 |
| customer | allowed only if customer endpoint | 403/404 |
| owner | allowed if owner endpoint | 403/404 |
| staff | allowed only if explicitly permitted for their salon | 403/404 |
| super_admin (aal2) | allowed if admin endpoint | allowed if admin endpoint |
| super_admin (aal1, MFA on) | 403 `mfa_required` | 403 `mfa_required` |

Fixtures: `make_profile`, `make_owner`, `make_super_admin` in `backend/tests/conftest.py`; see `tests/unit/test_admin_mfa.py` for the aal2 pattern.
