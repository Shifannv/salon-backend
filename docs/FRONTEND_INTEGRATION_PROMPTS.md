# Frontend integration prompt pack

Reviewed against local backend source on 2026-10-10. This is a handoff, not proof that
these features are deployed or that any frontend works. No production provider settings,
database migrations, real SMS, push delivery, or frontend runtime were verified here.

The three frontend projects are customer app, owner app, and website. The website contains
public QR booking and the private super-admin workspace. Keep all three separate from
this backend repository. Run each prompt in the repository named by the prompt.

## Critique and corrected product workflow

The project already has much of the required API. The main work is verifying the deployed
release and wiring the clients to it, rather than rebuilding bookings in each frontend.

1. Owner signs in through Supabase, calls `/v1/auth/owner-access`, and completes salon
   onboarding. Incomplete, pending, rejected, and approved are different UI states.
2. Super admin reviews the persisted salon submission, then approves or rejects it.
   Rejected owners correct and resubmit. Public business requires approved, active,
   completed onboarding.
3. An approved owner retrieves the salon's existing QR through `/v1/salons/me/qr`.
   The printed QR opens `https://<website>/s/<qr_token>`.
4. The QR page resolves that token to the salon. The customer's Auth user ID identifies
   the customer; `salon_id` identifies the shop; `staff_id` identifies the selected worker;
   `qr_token` selects the scanned shop. An owner's user ID is not the QR identifier.
5. Customer selects services, compatible staff, and an authoritative server slot; phone
   verification establishes a customer session; the backend creates the QR booking.
6. The owner sees that booking alongside app and manual walk-ins. Customer and owner
   refetch authorized API state after changes. Manual approval can leave a booking pending.
7. Customers see their own status and delay estimate. Other customers' details stay private.

**Live status needs a precise meaning.** Available slots and own-booking status can be
refreshed now. There is no public queue feed, queue position, or explicit service-in-progress
status in the inspected API. Start with foreground polling. A live queue needs a separate
backend feature. An `estimated_end_datetime` is an estimate: it does not move reserved
slots or rewrite availability. Do not display it as a guaranteed new appointment time.

**One account across both apps has a current role boundary.** `/v1/auth/owner-access`
promotes a customer profile to owner; it is not merely a frontend workspace toggle.
Owners can use supported ordinary customer flows, but the QR booking use case requires
the database role to be exactly customer. Do not promise that the same owner's account
can complete the QR flow. Use an explicit customer account switch today, or separately
review a backend change to permit owner-as-customer QR booking. Never change profile
roles directly from the frontend to work around this.

**Newer additions to include:** service photos/categories; booking delay estimates;
payment/cancellation action requests; preview-and-confirm closures; admin approval and
full onboarding review; discovery visibility/home placement; optional server-enforced
admin MFA; stronger QR cache/retry scoping; validated media upload gateway and cleanup;
verified account deletion with a durable worker. Paid subscription checkout remains absent.
See `docs/features.md` and backend technical docs for boundaries.

**Documentation traps:** the older Redis prompt uses `slot_start` in a booking request;
the current request field is `start_datetime`. Both booking routes currently declare
201, including cached returns; do not depend on the older handoff's 200 replay claim.
Redis idempotency is best effort, with a short retry window, not durable exactly-once
booking. The ordinary app route does not have the QR route's payload-fingerprint check.
Never reuse one key for a changed payload.

**Admin powers currently available:** review salon/owner details, approve/reject,
create an owner/salon through the supported admin flow, change supported salon fields,
control discovery and placement, deactivate a salon, manage categories/subcategories,
manage manual/test subscription plans and subscriptions, read subscription events and
the privacy-safe deletion ledger. Deactivation also disables/bans the owner; no current
reactivate endpoint exists. Hiding discovery leaves approved direct QR access working.
There is no exhaustive user directory, general admin activity history, platform analytics,
or payment-verified checkout. Do not invent these screens as functional controls.

## Configuration: what belongs where

Inspect templates and provider settings without printing real values. A template entry
does not prove the deployed environment is configured.

| Integration | Backend/provider setup | Frontend setup |
| --- | --- | --- |
| API | HTTPS origin, `PUBLIC_API_BASE_URL` as origin without `/v1`, explicit `BACKEND_CORS_ORIGINS` | Environment API origin; establish whether the existing client appends `/v1` |
| Supabase Auth | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWKS_URL`, audience, server-only `SUPABASE_SERVICE_ROLE_KEY` | Project URL and public anon/publishable key supported by its SDK; bearer access token |
| QR landing | `WALKIN_BASE_URL=https://<website-origin>/s` | Implement `/s/<qr_token>` and direct navigation/deep-link handling |
| Phone/email delivery | Enable Supabase phone auth and configure its SMS provider; verify email delivery/recovery and redirect allowlists | OTP/recovery UI, cooldowns, country-code phone input, supported session establishment |
| Owner OAuth | Provider configuration and allowed redirect URLs in Supabase | Existing OAuth/deep-link callback flow, then owner-access bootstrap |
| Admin MFA | Trusted admin provisioning, TOTP enrollment, then `ADMIN_REQUIRE_MFA=true` | MFA challenge and `mfa_required` handling; no public admin signup |
| Images | R2 account, access key, secret, bucket, public URL; upload gateway; media guards/worker | Backend multipart or returned signed gateway URL; no R2 credentials |
| Redis | `REDIS_URL`, connectivity and worker/API access | No Redis credentials; booking retry keys and 429 handling |
| Notifications | FCM credentials for Firebase delivery; notification outbox worker | Device platform configuration, permission, token registration and logout removal |
| Account deletion | `ACCOUNT_DELETION_SECRET`, reviewed `0020` then `0021` migrations, deletion worker, provider delivery | Challenge, verification, explicit DELETE confirmation, sign-out/status flow; public web deletion entrypoint |
| Subscription payments | Current `SUBSCRIPTION_PROVIDER=none`; checkout/webhooks require new backend work | Manual/test labels only; no real purchase-success claim |

`UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` appear in the example env file,
but the inspected settings/cache implementation consumes `REDIS_URL`. REST credentials
alone do not wire up this backend. Do not add a second Redis integration unnecessarily.

API keys alone cannot complete the integration: SMS provider enablement, callback URLs,
MFA enrollment, reviewed migrations, workers, HTTPS, and device setup also matter.
No Claude/OpenAI API key is needed by this salon API for the listed product flows.

## Model assignments and cost discipline

These are task recommendations, not a measured ranking for these repositories. Select
the available equivalent in your account; model availability and billing depend on
the product and plan.

| Prompt | Codex choice | Claude alternative | Reason |
| --- | --- | --- | --- |
| 0: readiness/contract audit | GPT-6.1 Sol, medium | Sonnet 5.5 | Scoped source tracing and deployment checklist |
| 1: customer integration | GPT-6.1 Sol, medium | Sonnet 5.5 | API client, auth and booking implementation |
| 2: owner integration | GPT-6.1 Sol, medium | Sonnet 5.5 | Onboarding and operational workflows |
| 3: website QR/admin | GPT-6.1 Sol, medium; high for difficult auth/cache defects | Sonnet 5.5; Opus 5.5 for unresolved security defects | Two-salon isolation and MFA need careful tests |
| 4: optional queue backend | GPT-6 Astra, high for design/review | Opus 5.5 | New domain rules, privacy and transactional state |
| 5: final integrated review | GPT-6.1 Sol, high | Opus 5.5 for one focused review | Review the actual cross-app behavior and evidence |

Small copy-only/config-template edits can use GPT-6 Luna or an available Claude Haiku.
Keep booking authorization, account erasure, migrations, and payment verification with
a stronger model and meaningful verification.

Do not pay for Codex and Claude to implement the same task independently. Use one
executor per repository, then one focused reviewer for auth, booking and tenant isolation.
The existing `.claude/agents/code-refactorer.md` uses `model: opus` and asks for proactive
review after code changes. That can increase cost; a cost-conscious alternative is a
Sonnet routine review with Opus reserved for the risks above. This pack does not edit
that agent configuration. Its blanket hard-delete/direct-booking-update language also
needs to follow AGENTS.md's scoped account-erasure exception and verified lifecycle behavior.

Official model guidance checked for this handoff:
[OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection)
and [Anthropic cost/intelligence guidance](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence).

## How to use the prompts

Run prompt 0 in the backend first. Give the other projects its sanitized contract summary
and the deployed `/openapi.json`. A webpage coding tool cannot infer private backend files
from a path alone: attach the relevant docs or supply their contents if it has no repo access.
Never attach `.env` or credentials. Then run 1, 2 and 3 in their respective projects.
Use 4 only if a real queue is required. Finish with 5 once the clients and staging API exist.

### Prompt 0 — Backend readiness and corrected contract

```text
Work in the salon FastAPI BACKEND repository. Audit readiness for three separate
frontend projects: customer app, owner app, and website with QR booking/super admin.
This task is an audit and handoff, not a backend rewrite or production deployment.

Read AGENTS.md and its required docs in order. If .codegraph exists, use CodeGraph
before code searches; otherwise use targeted rg/source reads. Inspect routes/schemas,
relevant use cases, config templates, migration history and Compose workers. Do not
print secrets, load full real env files into output, or mutate production/provider data.

Produce a compact contract matrix: frontend screen/action -> HTTP method/path -> auth
and ownership -> request/response -> errors -> implemented/deployed/provider status.
Verify booking payload uses start_datetime, not the old Redis example's slot_start.
Cover owner-access/bootstrap, approval/resubmission, stable salon QR, phone OTP,
availability, all booking sources, lifecycle actions, delay estimates, payment and
cancellation requests, closures, discovery placement, media, notifications and deletion.
Document exact list/pagination shapes and the best-effort retry/idempotency boundary.
Distinguish public slots, private booking status, and the absent public live queue.
Flag that owner-access promotes customer to owner while QR booking requires customer;
document supported account switching versus a separately scoped role-policy change.

Inspect settings consumers: REDIS_URL drives Redis; Upstash REST entries alone do not.
List required public frontend settings separately from server/provider secrets, with
names and presence/check status only. Check SMS auth/provider enablement, OAuth/recovery
redirects, HTTPS/CORS/QR origins, R2, FCM/device setup, admin MFA enrollment/enforcement,
notification/media/deletion workers, and reviewed migration requirements through 0021.
Do not equate templates, source, health checks, or Alembic head with verified product flows.

If a staging API is configured, read health endpoints and /openapi.json and compare
its contract to local source. Otherwise mark deployment unverified and provide precise
checks. Do not invent a URL or run migrations automatically.

Critique the existing frontend handoff docs with file/line evidence for contradictions.
Give a prioritized launch checklist with backend/frontend/provider ownership and a
sanitized contract summary that can be passed to the other three repositories.
Use no general web searches; official docs only for a concrete unresolved SDK issue.
Do not spawn agents or re-audit unrelated modules. Report what you actually verified.
```

### Prompt 1 — Customer app

```text
Work in the existing CUSTOMER APP repository. Complete integration with the shared
FastAPI salon backend using the existing stack, design and API client. Keep frontend
code here. Use the supplied sanitized backend handoff and configured /openapi.json;
if either is unavailable, trace current API calls and identify the specific missing
contract rather than guessing. Verify feature presence on the deployed API.

Inspect repository instructions, auth/session storage, API origin/version handling,
generated types, query cache, navigation/deep links and current tests. Supabase is
for Auth; business reads/writes go through FastAPI. Only public Supabase config and
API origin belong in this app. Resolve role with GET /v1/auth/me; use bearer tokens,
one coordinated refresh flow and private-cache cleanup on logout/account changes.

Wire discovery: /v1/salons?surface=home and surface=search, nearby and salon detail,
services/staff. Keep shuffle_seed stable through a paginated view; use server ordering.
Show service photos with null fallback and returned category names, prices/durations.

Wire services -> compatible staff -> date -> GET /v1/availability with staff_id,
date=YYYY-MM-DD and repeated service_ids -> review -> POST /v1/bookings source=app.
Submit canonical slot_start as start_datetime and required customer_name. Format times
in salon timezone; never reconstruct booking timestamps from display labels or compute
slots locally. Include a UUID Idempotency-Key per logical attempt, disable double tap,
reuse only for identical short-window retries, and reconcile after unknown outcomes.
409 means refresh slots and choose again; do not promise exactly-once execution.

Wire role-scoped booking list/detail and show server pending/confirmed/rejected/
completed/cancelled status honestly. Use server action flags for cancellation and
pay-at-salon confirmation requests; a customer payment claim is not money received.
Display delay estimates separately from reserved times; do not shift bookings locally.
Support notification list/read/read-all and device registration/removal. Push triggers
authorized API refetches. Poll only active booking screens at a configurable bounded
interval (start at 30 seconds), pause in background, refetch on focus/reconnect and
show last checked time. Do not invent queue position or service-in-progress status.

If QR scanning/deep links already exist, resolve the scanned qr_token through the
walk-in API and use that salon, not the last selection. Use the documented QR booking
route/source and customer-session requirement. Do not add a camera dependency solely
to scan a printed link that the phone's camera can already open on the website.

Wire profile/avatar via validated backend upload contracts and salon reports. Add
verified account deletion: challenge, verify, explicit DELETE confirmation, accepted
request -> local sign-out, then token-scoped status. Handle open-booking blockers.
Use existing backend docs for exact deletion bodies/errors. Keep unsupported payments
and queue features out of functional UI; report the backend dependency.

Implement in small coherent increments. No general web search, blanket redesign,
duplicate auth system, direct business-table writes or parallel agents. Use official
SDK docs only for a named blocker. Run relevant type/lint/tests/build checks once,
fix failures, then confirm. Test slot conflict, duplicate taps/unknown outcome,
timezone boundary, session expiry, rejected/hidden salons, and two user accounts.
Report changed files, checks, public env names and provider/backend blockers without
secrets. Do not claim real-device push or production verification from mocked tests.
```

### Prompt 2 — Owner app

```text
Work in the existing OWNER APP repository. Finish integration with the shared salon
FastAPI API using existing components, Supabase Auth and client conventions. Read
repository instructions, the supplied backend handoff and deployed /openapi.json.
Do not bring this frontend into the backend repo or recreate booking rules locally.

After supported sign-in, POST /v1/auth/owner-access once per sign-in, use returned
database profile/role, then GET /v1/salons/me. Handle new-owner onboarding explicitly.
Wire /v1/salons/me/complete-profile, owner-editable profile/settings, service catalog,
staff/service assignments, hours, holidays, blocked slots and validated image uploads.
Show incomplete/pending/rejected/approved states and rejection reasons; support
correction/resubmission. Never mark onboarding approved locally or offer admin-only
placement/visibility controls. Explain API denial of daily operations until approval.

Retrieve the persisted salon QR through GET /v1/salons/me/qr. Render/share/print its
returned image URL or supported SVG response. The public image URL is not the booking
landing URL: the QR encodes the website /s/<qr_token>. Repeated reads must keep salon
identity stable; do not generate a new token, use owner user ID, or rebuild a QR from
an arbitrary frontend selection. Verify two owners receive their respective shop QR.

Wire role-scoped GET /v1/bookings for this owner's salon with status/source/date
filters. Display app/manual_walkin/qr_walkin bookings together with clear labels.
Use exact OpenAPI lifecycle endpoints for approve/reject/complete/cancel/payment/delay.
Manual walk-in uses the existing authorized booking creation flow and database slots;
never fabricate a customer account or insert into tables. Preserve server status.

Wire /v1/booking-action-requests and response decisions for customer cancellation and
payment claims. Only a returned authorized received decision confirms cash payment.
Support delay updates with estimated_end_datetime and optional affected-customer
notification; explain that reservations/availability do not automatically shift.
Closures require /v1/salons/me/closures/preview, review of affected bookings, then the
matching confirmed apply request; handle stale/conflicting previews and refetch.

Poll visible operational lists at a bounded configurable interval, pause in background,
refetch on focus/reconnect and after mutations; notifications invalidate authorized
queries. Scope private caches by actor/salon and clear on logout. Do not imply a
public live queue exists or blindly replay approvals/payments/closures offline.

Use the backend image validation gateway: request upload_url, PUT bytes to that exact
URL, then attach public_url via the documented mutation. Do not assume direct R2 PUT
or ship storage secrets. Wire notifications/device tokens and account deletion with
verification and explicit DELETE confirmation; deletion can be blocked by open work.
No owner paid checkout exists: report the gap and avoid fake purchase success.

No general web searches, full redesign, unrelated refactors or parallel agents.
Use official SDK docs only for a named blocker. Test approval gate/resubmission, QR
identity, walk-in conflict, stale action decisions, closure preview conflict, upload
failure/retry, session expiry and cross-owner data denial. Run relevant checks/build,
then report changes, evidence, public env names and unresolved integration dependencies.
```

### Prompt 3 — Website: QR booking and super admin

```text
Work in the existing WEBSITE repository. Complete public salon QR booking and a
separate private super-admin workspace against our shared FastAPI backend. Keep the
existing marketing page, stack, branding and supported links. Use repository
instructions, the supplied backend handoff and deployed /openapi.json. If provided,
also read backend/docs/WEBSITE_SUPERADMIN_PROMPT.md for detailed contracts; prefer
verified deployed schemas over stale examples. Implement and test supported flows.

PUBLIC QR ROUTE /s/<qr_token>
The route token is the only source of salon context. GET /v1/walkin/{token}?fresh=true
returns salon identity/timezone/hours/services/staff. Never use /v1/salons/me, owner
user ID, first discovery result, localStorage salon, or admin selection for this page.
Scope query keys by token and dependent staff/services/date; clear selections on token
change and cancel/ignore late responses. Invalid/unpublished tokens show unavailable,
with no fallback shop. Audit service worker, SSR and CDN caching for token isolation.

Show shop -> services -> staff supporting every service -> date -> authoritative slots.
GET /v1/availability uses staff_id, date and repeated service_ids. Keep slot_start/
slot_end canonical; submit start_datetime=slot_start, formatted only for display in
salon timezone. POST /v1/walkin/{token}/verify-phone with {phone}, then {phone,otp};
verified=false means OTP sent, not logged in. Establish returned tokens with the
supported Supabase session API. Browsing is public; booking needs a customer session.
QR booking denies noncustomer roles, so require explicit account switching without
silently replacing the admin session. Do not submit an invented customer/user ID.

POST /v1/walkin/{token}/bookings uses the resolved salon_id, selected staff/service
IDs, required customer_name, canonical start_datetime and source=qr_walkin. Include
one UUID Idempotency-Key per logical attempt; short retries use identical payload.
Prevent double taps; changed payload gets a new key. For unknown outcomes reconcile
private bookings before another submission. 409 refreshes availability; 429 observes
server cooldowns. Read authorized booking detail after success and show its real
pending/confirmed/etc. status plus any delay estimate. No public customer list/queue.

Poll slots and own booking only while visible at a bounded configurable interval
(start at 30 seconds); refetch on focus/reconnect and before confirmation. Show last
checked time. Working hours are not proof of available capacity; estimates do not
reschedule reservations. Include loading, empty, stale, offline and outcome-unknown UI.

SUPER ADMIN
Use separate /superadmin login/workspace routes and private caches. Supabase email/
password plus TOTP MFA; GET /v1/auth/me must return active super_admin database role.
No public admin signup/self-promotion or second identity provider. Send bearer tokens;
403 mfa_required opens the challenge. Production backend must enforce ADMIN_REQUIRE_MFA.
Use established secure session handling; do not put tokens in URLs or public caches.

GET /v1/admin/salons?approval_status=pending is an array with limit/offset, not a total
user directory. Distinguish incomplete setups from ready submissions. Open
GET /v1/admin/salons/{id}/onboarding for persisted salon, owner, images, services/staff,
hours and approval evidence. Approve/reject through supported endpoints; rejection
body is {rejection_reason}. Refetch after decisions; no optimistic publication.

PATCH /v1/admin/salons/{id} supports discovery_visibility listed/search_only/hidden,
home_placement top/normal/random/below and display_priority. Explain hidden discovery
does not disable an approved direct QR, and random is a stable shuffled group. Preview
with public home/search APIs; keep shuffle_seed stable and use server ordering.
Salon deactivation is a separate confirmed action that also disables/bans the owner;
POST /v1/admin/salons/{id}/reactivate restores salon and owner access without changing
approval, discovery or subscription state. Explain existing-booking consequences. Do not
offer admin hard deletion: permanent owner-data erasure requires the verified account-
deletion flow and its retention/anonymization rules.

Wire admin category/subcategory management and supported subscription plan/current
subscription/event controls. Label /subscription/test as manual/test activation,
never verified payment. Do not invent analytics, all-user directory, general audit
history, booking override, online checkout or refund controls. Add privacy-safe
account-deletion ledger only if deployed. Admin account email/password/MFA settings
use supported Supabase flows; never expose passwords or service-role keys.

Add a public account-deletion help/entry page for customer/owner store-policy links.
The actual deletion requires that user's authenticated challenge/verify/explicit
DELETE flow and token-scoped status; no arbitrary account ID or unauthenticated erase.
Keep the deletion route outside private admin and salon QR navigation.

Deployment handoff: public API/Supabase config, correct API version handling, website
origin in backend CORS, WALKIN_BASE_URL=https://<website>/s, PUBLIC_API_BASE_URL as API
origin, Supabase callback allowlists, SMS provider readiness and admin MFA enforcement.
Never put DB, R2, FCM, Redis, deletion secret or service-role keys in the website.

No general web searches, new frameworks, blanket redesign or parallel agents. Official
SDK docs only for a specific blocker. Test two salons/tokens in one browser and separate
contexts, late A response after B, back/forward, cached content, wrong-salon payload,
slot conflict, OTP errors, manual pending approval, account switching and session expiry.
Test logged-out/customer/owner admin denial and real aal1 denial when MFA is enforced.
Use staging/disposable accounts, not production mutations. Run checks/build and browser
verification; report actual causes, changed files, checks and unavailable dependencies.
```

### Prompt 4 — Optional actual live queue backend

```text
Work in the BACKEND repository. Design a real live queue feature beyond the current
slots and booking-status API. This is a bounded design/contract task first; do not
invent a queue in the frontend or change existing booking semantics silently.

Read AGENTS.md and required docs. Trace booking states, delay estimates, availability,
walk-ins, role authorization and migrations. Current lifecycle is pending/confirmed/
rejected/completed/cancelled, not an arrival/service-progress model.

Propose the smallest coherent contract for owner-controlled arrival, service start,
completion and an anonymized QR-scoped public summary. Separate appointment reservation
from actual service progression. Define late/no-show/walk-in ordering, multi-service
duration, per-staff capacity, competing appointments, timezone/day boundaries and
estimate uncertainty. Flag product decisions that change who gets served first.

Private customer tracking must authorize ownership; public data may expose counts and
coarse wait estimates only, never customer names/phones/profile IDs or raw booking IDs.
Clarify whether hidden discovery keeps QR queue access, and enforce approved/active/
completed salon publication. Owners mutate only their own salon; staff only explicitly
assigned operations. Keep authorization in use cases and actor context on DB work.

Compare bounded HTTP polling first with SSE/WebSocket only if concrete latency/load
needs justify them. Define atomic updates, stale-write conflicts, idempotency, limits,
indexes and cache isolation. Events trigger API refetch, not client-side truth.
Slots remain exclusively get_available_slots and booking creation exclusively
create_booking. Delay estimates must not silently rewrite reserved times. Any schedule
changes need explicit business policy and reviewed database migrations.

Output the proposed endpoints/schemas, state transitions, migration plan, privacy rules,
frontend handoff, acceptance tests and rollout/rollback limitations. Distinguish safe
defaults from questions requiring a product decision. Do not run migrations or deploy.
No generic research, unrelated refactor or multi-agent work. If implementation is later
authorized, use a focused branch and meaningful concurrency/authorization tests plus
the required backend pytest/Ruff checks before handoff.
```

### Prompt 5 — Final cross-project verification

```text
Verify the integrated customer app, owner app, website QR/super-admin and staging
FastAPI API. Use access already provided; if a repo or staging service is unavailable,
complete accessible checks and explicitly mark the missing tier unverified.
This is a focused integration review, not a new implementation of all three clients.

Read sanitized contract summaries, deployed /openapi.json and relevant changed files.
Use two staging salons with distinct owners, a customer and a provisioned MFA admin.
Never print secrets or mutate production. Verify this full story:
owner sign-in/bootstrap -> onboarding -> admin full review/approval -> stable printed
QR -> scanned shop/services/staff/slots -> customer OTP -> QR booking -> same booking
in owner list -> approval/delay/action decisions -> customer's authorized refreshed
status/notification. Verify ordinary app and manual walk-in bookings share conflict
protection. Distinguish pending from confirmed and claims from received cash.

Adversarial checks: QR A/B navigation and late responses; owner A requesting owner B
data; customer reading another customer's booking; wrong salon/service/staff pairing;
slot race; double tap; expired retry key/unknown outcome; revoked salon; expired session;
MFA aal1 denial; hidden discovery versus direct QR; server timezone and midnight.
Check image gateway/attachment, deletion blocked by open work, confirmation -> lockout,
and worker completion using a disposable account. Verify worker/provider readiness;
mocked SMS/push/storage are not live delivery verification.

Inspect public bundles/config for forbidden secrets and direct business-table writes.
Run each project's relevant checks/build once; diagnose failures before repeat runs.
Do not repeat the whole repository audit or perform broad web searches. Use official
documentation only to resolve a named SDK issue. No parallel agents by default.

Produce pass/fail/unverified evidence per story, critical/high issues with file/line,
precise proposed fixes, public deployment settings, provider dependencies and a
prioritized launch decision. Do not claim production readiness from health endpoints,
mocked tests, or a successful build alone. New public live queue and paid checkout
remain separate scope unless explicitly implemented and verified.
```
