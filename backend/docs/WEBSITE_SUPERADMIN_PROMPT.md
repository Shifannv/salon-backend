# Website implementation prompt

Source contract reviewed on 2026-10-10. Copy the prompt below into Claude Code in the
existing website repository. The website source is not in this backend repository.
Use the strongest available Claude Opus model for the implementation and security review.
Anthropic's current Opus page lists Opus 5.5: https://www.anthropic.com/claude/opus.

## Backend implementation status

Implemented locally, not deployed:

- Fixed the admin salon list query that omitted required approval metadata and owner details.
- Added `GET /v1/admin/salons/{salon_id}/onboarding` for full persisted salon setup,
  owner contact details, images, services, and staff, including unpublished submissions.
- Added discovery visibility and home placement controls through admin salon PATCH.
- Added `surface` and `shuffle_seed` to `GET /v1/salons`.
- Added optional server-enforced super-admin MFA. Enable `ADMIN_REQUIRE_MFA=true`
  after enrolling existing admin accounts. Missing verified `aal2` returns
  `403 error.code=mfa_required` on protected admin operations. `/v1/auth/me` remains
  accessible after first-factor login so the website can identify the database role.
- QR responses discard mismatched cached salon data. `fresh=true` bypasses Redis reads.
- QR staff responses include `service_ids`; QR salon responses include `working_hours`.
- OTP endpoints validate QR publication before contacting Supabase Auth.
- QR booking retries revalidate the current salon, scope keys by actor and QR token,
  and reject reuse of a key with a different payload.

Deployment requires reviewed migration `0019_discovery_placement` after `0018`.
Use the reviewed release image for the explicit migration step before deploying its code.
Set `WALKIN_BASE_URL=https://<website-origin>/s` so QR images encode `/s/<qr_token>`.
Include the website origin in `BACKEND_CORS_ORIGINS`; keep all provider secrets server-side.
Enroll the super admin in Supabase TOTP MFA and enable the backend MFA flag before public
admin launch. New templates enable MFA for production; an existing VM `.env` is preserved
by deployment and needs an explicit setting change.

Existing limitations, not promises:

- Automatic paid subscription checkout and verified provider webhooks are absent.
  `/subscription/test` is manual/test activation, not proof of payment.
- No platform analytics, exhaustive user directory, subscription history list, or
  general admin activity-history endpoint exists. Audit actor/time fields are available.
- The review list contains salons and owners, not every Supabase user without a salon.
- Random placement means a stable shuffled home group, not a random absolute position.
- Hiding from discovery does not suspend daily operations or disable an approved QR page.
- Availability is uncached and authoritative. Catalog cache reads may lag mutations by
  180 seconds; use the fresh QR read for the booking page.
- Idempotency is best-effort Redis storage with a 60-second TTL, not durable exactly-once
  execution. Concurrent equal requests can race. Do not blindly replay old submissions.
- Rejection/deactivation of a live salon needs operational care for existing bookings;
  it is separate from discovery hiding. Deactivation also disables/bans the owner.
- The website still needs a code audit and two-salon browser tests to diagnose its
  actual wrong-salon rendering bug; backend inspection alone cannot prove its cause.

## Copy-paste prompt

```text
You are working in our existing salon platform WEBSITE repository. Implement the
three website surfaces and fix the QR booking flow against our shared FastAPI backend.
Complete implementation, tests and handoff. Use the repository's existing stack,
routing, visual design, packages and deployment conventions.

FIRST INSPECT

Inspect repository instructions, routing, API clients, environment settings, Supabase
Auth integration, query/state caching, service workers, SSR/static generation, QR
rendering, and tests. Preserve existing working product behavior and brand assets.
Fetch the configured backend's /openapi.json and generate or update client types.
Check that the deployed API includes the contracts described here; report missing
deployment features explicitly. Do not fake responses to make an unsupported feature
appear functional. Business writes must go through FastAPI, with Supabase used for Auth.

ROUTES

- / : existing introduction/marketing page.
- /s/[qrToken] : public salon-specific QR landing and customer booking flow.
- /superadmin/login : email/password login and TOTP MFA challenge.
- /superadmin : protected workspace; default view is onboarding review queue.
- /superadmin/salons : all salons with search and approval filters.
- /superadmin/salons/[salonId] : complete submission review and management.
- /superadmin/discovery : visibility and placement editor with customer-feed preview.
- /superadmin/subscriptions : current admin plan and manual subscription controls.
- /superadmin/catalog : existing category/subcategory management.
- /superadmin/settings : current admin account email/password/MFA controls.

Adapt dynamic route syntax to the actual framework. Preserve existing QR paths with
safe aliases if needed. Routes for normal customers and admins must not share mutable
salon-selection state or private query caches.

INTRODUCTION PAGE

Keep the existing introduction page and its real app-download/contact links. Make
supported owner/customer journeys clear. Preserve supplied factual copy and assets;
avoid invented ratings, testimonials, revenue numbers or subscription prices.

AUTHENTICATION AND ADMIN SECURITY

Use Supabase Auth email/password sign-in and Supabase TOTP MFA. Supabase is the API's
identity provider. A Better Auth session token is not accepted by this backend; do not
silently migrate identity providers or introduce a second identity database.

Provision the administrator account through trusted operational tooling. There must
be no public admin registration, self-promotion, role-editing form or client-side secret.
Passwords belong to Supabase Auth, never source code, browser storage, URLs or JWT claims.
An email/password change does not modify a JWT manually: update the identity through
Supabase, complete its confirmation/reauthentication flow, and obtain a valid session.
Account email comes from Supabase Auth user data; profiles.email may be an older copy.

After login, call GET /v1/auth/me with the access token and require the returned database
role to be super_admin and is_active=true before rendering private data. Do not trust
role claims parsed from a token or a localStorage boolean. Complete MFA before admin
operations. Handle 403 mfa_required with an MFA challenge, not a retry loop.

Every admin API request sends Authorization: Bearer <Supabase access token>. The backend
verifies JWT signatures and checks the active database profile role. Enable
ADMIN_REQUIRE_MFA=true on the backend for production enforcement; a frontend MFA screen
alone does not enforce this. Confirm a real aal1 token is denied on an admin data call.

If the website supports a server/BFF, use secure HttpOnly cookies and appropriate
SameSite/CSRF protections using supported Supabase session handling. Use the established
SDK session flow when the existing website is browser-only and report that boundary.
Do not send access tokens in query strings. Do not log tokens or passwords. Prevent
untrusted return-URL redirects and caching private HTML/API responses publicly.

Support session expiry, one coordinated refresh attempt, sign-out, recovery, changing
email with provider confirmation, changing password with reauthentication, and MFA
enrollment/recovery through the supported Supabase APIs. Clear private caches on logout
or account change. Avoid promises that an email/password change instantly revokes every
previous JWT; use supported session revocation and short-lived sessions where available.

QR WRONG-SALON BUG: INVESTIGATE AND FIX

The URL token is the source of salon context for this page. Never use /v1/salons/me,
the authenticated owner's shop, the first discovery result, a hard-coded salon, or a
previously saved selection to choose the scanned shop.

1. Read the current route qrToken and call
   GET /v1/walkin/{qrToken}?fresh=true.
2. Render its id/name/address/city/image_url/timezone/working_hours/services/staff.
3. Treat staff.service_ids as supported service assignments. Only allow staff who
   support all selected services. Still let the database make the final validation.
4. Request available slots using
   GET /v1/availability?staff_id=<id>&date=YYYY-MM-DD&service_ids=<id>&service_ids=<id>.
5. Keep returned slot_start/slot_end as canonical timestamps. Format in salon timezone.
   Submit start_datetime=the selected slot_start, not a reconstructed display label.
6. Phone verification:
   POST /v1/walkin/{qrToken}/verify-phone with {phone}, then {phone, otp}.
   Handle verified=false as OTP sent, not authenticated. Establish the returned customer
   session using the supported Supabase SDK and its access_token/refresh_token.
   Do not log out or replace an admin session silently; require explicit account
   switching when a privileged user tries to complete a customer-only QR booking.
7. Submit POST /v1/walkin/{qrToken}/bookings with the exact OpenAPI request body.
   salon_id must be the resolved salon.id, staff and services must belong to that shop,
   and start_datetime must be the selected server slot. source is qr_walkin.
8. Include Idempotency-Key: a client UUID per logical attempt. Reuse it only with the
   identical payload within its retry window. Disable double taps. A changed payload
   needs a new key. Do not blindly replay after a restart or a long timeout; reconcile
   customer bookings and ask the customer to recheck availability if uncertain.
9. After success, fetch the authorized booking detail and display its canonical status.
   Manual approval may return pending; never label that booking confirmed locally.

Cache keys must include qrToken, resolved salon ID where relevant, selected staff,
service IDs and date. Include authenticated user ID for private booking queries.
When qrToken changes, clear dependent selections and cancel/ignore old fetches. Guard
against a slower response for QR A replacing QR B's current page. Audit service-worker
and CDN/SSR caches for accidental token-independent caching. Invalid/unapproved/closed
publication must show an unavailable state, without fallback to another salon.

Refetch fresh salon services and uncached availability on page focus, network reconnect,
selection changes and immediately before confirmation. While visible, use a bounded
configurable poll (for example 30 seconds) for live availability; pause it when hidden.
Use an explicit loading/refetch indicator and “last checked” time. Do not invent a
live queue or “busy now” status: no public queue feed currently exists. Working hours
and server slots are the supported information; opening hours alone do not prove availability.

On 409 slot_unavailable, refetch slots and request a new selection. On 429 OTP throttling,
honor Retry-After if supplied; otherwise show a cooldown and require manual retry.
Handle unauthorized, forbidden, unavailable, validation and network errors explicitly.
Browsing shop/services/slots does not require login; customer authentication is needed
to book. Never expose other customers' names, phone numbers or bookings publicly.

SUPER-ADMIN ONBOARDING REVIEW

GET /v1/admin/salons?approval_status=pending&limit=50&offset=0 supplies the review queue.
It is a JSON array, not an invented {items,total} envelope. Distinguish incomplete
registrations (profile_completed=false) from completed submissions ready for review.
The list includes owners with salons; it is not an exhaustive platform user directory.

Click a salon to load GET /v1/admin/salons/{salonId}/onboarding. Display the complete
persisted submission: shop identity/description/category/address/coordinates/timezone,
hours/slot interval/approval mode, owner name/email/phone/avatar/verified/active status,
shop images, service presentation/prices/durations/active state, staff details and hours,
approval metadata/rejection reason, and created_at/updated_at/updated_by.
Show missing values honestly. Passwords are neither available nor displayed.

Approve with POST /v1/admin/salons/{id}/approve. Reject with
POST /v1/admin/salons/{id}/reject body {rejection_reason: nonblank string}.
Refresh the record before reviewing/deciding and refetch the queue/detail after a
decision. Approval requires active, completed onboarding. Display returned conflicts.
Disable duplicate clicks; do not optimistically grant approval. Show a confirmation
that explains publication to customer discovery and access to owner daily operations.

Rejected owners can correct setup and resubmit via the owner app; the backend resets
rejected to pending. No separate admin notification feed exists for submissions, so
refetch the review queue on focus and use bounded foreground polling.

POST /v1/admin/salons can create an owner and salon if an existing operational need
requires it; it creates an owner, not a super admin. Support that form only with explicit
labels and the exact OpenAPI schema. Do not treat registration as approved onboarding.

DISCOVERY CONTROL

PATCH /v1/admin/salons/{id} supports:
- discovery_visibility: listed | search_only | hidden
- home_placement: top | normal | below | random
- display_priority: strict integer 0..100000, higher ranks first within ranking rules
- name and timezone

Use separate labeled controls for discovery visibility and home placement. Explain:
- listed: eligible for home and search, subject to approval/activity/completion.
- search_only: excluded from home, still eligible for search/nearby/all listings.
- hidden: excluded from every discovery listing; an approved direct detail/QR remains
  accessible. This does not disable the salon or owner account.
- top/normal/random/below: groups in that order for the home feed.
- random: a stable shuffled group; it does not promise random absolute feed positions.

Home GET /v1/salons?surface=home&shuffle_seed=<stable-per-view-seed>.
Search GET /v1/salons?surface=search&search=<query> with supported filters.
Nearby GET /v1/salons/nearby uses all-discovery eligibility.
The API owns ordering before pagination. Keep shuffle_seed constant across pages and
refreshes of one view. Do not re-sort results on the frontend.
Within nonrandom placement groups subscription ranking weight precedes display_priority,
then distance, name and ID. Explain that numeric priority is not an exact pinned position.

Preview placement changes using actual public API results after saving. Clearly label
the preview as the customer feed. Editing admin fields must not use direct Supabase
table writes. The customer app must consume the same surface=home/search contract.

Treat deactivation as a separate, high-impact action:
POST /v1/admin/salons/{id}/deactivate disables the salon and bans the owner.
Require an explicit confirmation and explain existing-booking implications. There is
no current reactivate endpoint; do not label this as a reversible discovery toggle.

SUBSCRIPTIONS: CURRENT CONTRACT AND FUTURE BOUNDARY

Under /v1/admin:
- GET/POST /subscription-plans
- PATCH /subscription-plans/{id}
- POST /subscription-plans/{id}/deactivate
- GET /salons/{salonId}/subscription (object or null)
- POST /salons/{salonId}/subscription/test (manual/test activation)
- POST /subscriptions/{id}/cancel
- POST /subscriptions/{id}/suspend
- GET /subscription-events with supported subscription_id/limit/offset

Use exact OpenAPI bodies, including salon_id if required by the current manual schema.
Display current status/periods and plan data the API provides. Label test/manual activation
prominently; require deliberate confirmation. Never label this purchase/payment verified.
There is no owner checkout, payment verification or webhook today. Do not implement
automatic paid activation, fake purchase success or browser-written subscription state.
The future purchase integration needs a selected provider, server-created checkout,
signature-verified webhooks, durable event deduplication and handling of expiry/refunds.
Report that dependency without fabricating provider credentials or making billing live.

CATALOG

Use existing admin category/subcategory endpoints in /openapi.json. Include search,
create/edit and soft deactivate, with explicit consequences. Do not invent platform
analytics, user-banning, support, audit-history or billing endpoints.

DESIGN AND STATE

Preserve the site's visual identity. Build the admin area for daily review work:
a responsive navigation rail, compact readable review table, clear status text,
search/filters and a detailed review view with approve/reject actions near the evidence.
Use real counts only when available; do not label the current page length as total users.
Keep subscriptions and placement in separate sections so payment, publication and
ordering cannot be confused. Avoid decorative charts and giant empty dashboard cards.

Build mobile QR booking as a clear sequence: shop identity -> services -> compatible
staff -> date/slots -> phone verification -> review -> result. Preserve form drafts,
show prices/durations from the API, and show server booking status honestly.
Support accessible labels, visible keyboard focus, adequate contrast, touch targets,
responsive layouts and status distinctions that do not depend on color alone.
Provide loading, empty, validation, forbidden, expired-session, stale-selection,
submission-in-progress, offline and outcome-unknown states.

SYNCHRONIZATION

Postgres/FastAPI is the source of business state. Push/Realtime events invalidate queries
and trigger authorized API refetches. They do not directly establish payment/approval or
booking status. Invalidate related list/detail queries after mutations. Scope caches
by user and shop; stop subscriptions on logout and route changes. Prevent older requests
from overwriting new state. Do not blindly queue approvals/payments/closures offline.

TEST AND FINISH

Run type checks, lint, relevant automated tests and production build. Test these flows:
- Direct /superadmin access while logged out and with a customer/owner account.
- A database-admin account with aal1 denied on an admin API when MFA is enabled.
- Admin sign-in, MFA, expiry, logout and account email/password update flows.
- Pending incomplete versus completed review, full detail, approve/reject/resubmission.
- Two different salons/QR tokens in the same browser and in two browser contexts.
- Slow QR A response arriving after QR B, browser Back/Forward and cached offline state.
- Wrong salon ID submitted under a valid QR rejected; revoked QR rejected on retries.
- Staff/service compatibility, timezone boundaries, concurrent slot conflict and double tap.
- Top/normal/random/below ordering, search-only, hidden, and stable paginated shuffle.
- Expired/cancelled subscriptions do not falsely display a purchase or override eligibility.
- No secrets, public admin registration or direct business-table writes in the bundle.

Use two owned test salons and disposable/staging accounts, never mutate production for
verification. Inspect desktop and mobile together once, fix defects, confirm once.
Report changed files, actual QR bug cause, test results, deployment settings, customer-app
contract changes, and remaining provider/backend dependencies. Do not claim production
deployment, zero data loss or absolute security from a successful local build.
```
