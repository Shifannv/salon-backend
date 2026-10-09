# Authorization

Clients send Supabase access tokens as bearer tokens. The backend verifies each token
against Supabase JWKS, uses the verified `sub` to load `profiles.id`, and reads the role
from the database. JWT role claims are not trusted.

Super-admin operations additionally require a verified `aal2` claim when
`ADMIN_REQUIRE_MFA=true`. Enroll admins in Supabase TOTP before enabling it on an
existing deployment. A first-factor admin can still read `/v1/auth/me`, but admin
operations return `403 mfa_required` until MFA is complete. Frontend route guards do
not replace these checks. Email/password changes remain Supabase Auth operations.

Authorization belongs in application use cases:

- customers access their own profile, bookings, notifications, and reports;
- owners access the salon workspace they own and may also use customer flows;
- staff access only operations explicitly allowed for their salon;
- super admins manage platform-wide salon and catalog records.

Repository queries must still scope reads and writes by actor or owned resource, but
repositories do not decide policy. RLS stays enabled as defense in depth.

Public salon discovery and details require `approval_status = 'approved'`,
`is_active = true`, and `profile_completed = true`. List/search, category, nearby/map,
and favorite ID queries share the same database predicate; no separate featured or
recommended API exists. Public services, staff, and service summaries apply the same
gate. QR reads and availability use the approval-aware Postgres functions installed by
the existing `0015_salon_admin_approval` revision.

Discovery lists also honor `discovery_visibility` from `0019_discovery_placement`:
`hidden` excludes all discovery listings; `search_only` excludes the home surface.
Approved direct details and QR booking remain accessible when hidden from discovery.
Home placement is separate from approval and subscription state. Only super admins
can change placement or visibility, including Data API writes guarded in Postgres.

Detail, services, staff, and QR cache hits revalidate current publication in Postgres
before returning any cached payload. Cache keys and mutation invalidation are never
authorization: old entries or late cache fills after revocation still return the
existing public not-found response. This requires no additional migration or endpoint.

Authenticated transactions set:

```sql
SET LOCAL request.jwt.claims = '{"sub": "<verified-user-uuid>"}';
```

This allows database audit triggers to record the verified actor.

Payment recording and booking-delay updates remain owner/staff operations. A customer
may report that they paid at the salon, but this creates a pending request and never
marks money received. Only an authorized salon owner/staff decision records cash paid.
Online payment still requires a verified provider webhook.

Customer cancellation is immediate only before the configured cutoff. After the cutoff,
the customer can request cancellation while the booking remains active; only the owning
salon may approve or decline it. Closure preview/application is owner-only.
