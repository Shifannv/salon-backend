# Website, customer app and owner app: developer handoff

Prepared: 21 October 2026. Audience: frontend developers, product owner and QA.

Read the shared contract first, then the website, customer app and owner app sections
in order. Common workflows are defined once and referenced by each client.

This note describes backend-supported behavior and the requested frontend scope.
The separate frontend repositories and running services were not inspected. An API
in source is not proof of deployment or a finished client screen. Confirm the target
release through `/openapi.json`; use `/docs` for interactive schema reference.

## 1. Project and responsibility map

The salon platform connects customers with salons and gives owners tools to run their
business. A shared FastAPI backend uses Supabase Auth/Postgres, backend-managed R2
media and optional push, email and payment providers. Frontends remain in separate repos.

| Client | Audience and responsibility |
| --- | --- |
| Website | Public introduction/discovery, customer booking and QR pages, requested owner web workspace, private super-admin review/management |
| Customer app | Mobile discovery, appointments, QR entry, customer notifications and account |
| Owner app | Mobile onboarding, appointment operations, staff/services, collections and business settings |

Authentication proves identity. The backend's database profile establishes role and
ownership. Approval controls salon publication/operations; entitlement controls access
to new business; owner pause controls booking acceptance. These are separate decisions.

## 2. Shared configuration and integration rules

### Values to request from the project owner

| Value | Clients | Exposure |
| --- | --- | --- |
| API base URL | All | Public configuration |
| Supabase project URL | All | Public configuration |
| Supabase publishable key or existing legacy anon key | All | Public configuration |
| Website origin and QR route | All where links are used | Public configuration |
| Actual auth callback/recovery URLs | Each client | App configuration and Supabase allowlist |
| Firebase client configuration or existing Expo setup | Mobile push integrations | Client configuration, never service-account secrets |

Example logical names; adapt to each repository's framework:

```dotenv
API_BASE_URL=https://<api-domain>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLIC_KEY=<public-key>
WEBSITE_ORIGIN=https://<website-domain>
```

For Next.js, browser-visible values may use its `NEXT_PUBLIC_` naming convention.
Use environment-specific values. Keep the API base URL/path convention consistent
so `/v1` is not duplicated. No actual credentials are supplied here.

Normal API access needs no separate shared FastAPI API key. Protected calls send:

```http
Authorization: Bearer <Supabase-access-token>
```

Database credentials, Supabase service-role/secret keys, R2 credentials, Firebase
service-account private keys, payment/webhook secrets and Resend keys stay server-side.
Mobile build variables are extractable. A separate maps provider may require a
restricted client key if chosen; the salon API does not require one.

Backend operators must configure website CORS, actual authentication redirects,
`WALKIN_BASE_URL=https://<website-origin>/s`, and provider delivery. Super-admin launch
also requires enrolled TOTP and `ADMIN_REQUIRE_MFA=true` for server enforcement.
This handoff does not authorize migrations or provider activation.

### Authentication and state

Use Supabase's supported sign-in/session lifecycle, then `GET /v1/auth/me`. Do not
authorize from local role flags or decoded JWT role claims. Business reads/writes go
through FastAPI, not direct Supabase business-table writes or booking RPCs.

Coordinate token refresh; `/v1/auth/refresh` is available when backend-assisted refresh
is needed. Protect sessions using the framework/platform's established storage model.
For a web server/BFF, use supported secure cookie handling and CSRF protections.
Clear private caches and subscriptions on logout/account change. Scope data by user
and salon; prevent late responses from overwriting a newer route selection.

Account email/password changes belong to Supabase Auth. Password recovery can start
through `POST /v1/auth/forgot-password` with `{email}`; complete the provider recovery
flow using the configured callback. A profile edit does not change the login email.

### Requests, money and recovery

Use exact deployed OpenAPI bodies, response models and methods. The examples below
identify entry points rather than replacing field-level contracts.

- Availability comes only from the API/database. Keep returned timestamps intact,
  display the salon timezone and submit the selected `slot_start` unchanged.
- Use server quotes and decimal money values. Do not compute final prices, fees,
  durations or refund entitlement independently.
- Supply `Idempotency-Key` for booking creation, collection and completion. Support
  and provider money operations require keys. Retry one uncertain operation with
  the same key/body; changed intent needs a new operation. A later status refresh
  is a separate operation. Prevent repeated taps and reconcile unknown outcomes.
- Push and configured Realtime signals trigger authorized API refetches. They do
  not establish approval, booking or payment truth. Do not queue consequential
  booking/payment/approval/closure writes blindly offline.

Errors use `error.code`, `message`, and `details` (object or validation array).

| Response | Client behavior |
| --- | --- |
| 401 | Coordinate refresh, then sign in if needed |
| 403 | Explain role/access restriction; route to approval/MFA when that code applies |
| 404 | Resource unavailable; never expose another tenant's resource |
| 409 | Refresh relevant state; handle slot, request, payment or idempotency conflict |
| 422 | Preserve input and show actionable validation/capability error |
| 429 | Respect cooldown information |
| Network/5xx | Recover without treating an uncertain write as definitely failed |

Every main screen needs loading, empty, offline, error and retry states. Use accessible
labels, scalable text, visible focus, adequate touch targets and statuses beyond color.

## 3. Shared customer workflows

Website customer pages and the customer app implement these same business flows.

### Discovery and normal booking

```text
Home/search -> Salon -> Services -> Compatible staff -> Date/live slot
-> Authenticate -> Customer details -> Server quote -> Review -> Submit
-> Actual pending/confirmed result -> My bookings
```

| Step | API |
| --- | --- |
| Home | `GET /v1/salons?surface=home&shuffle_seed=<stable-seed>` |
| Search | `GET /v1/salons?surface=search&search=<text>` |
| Nearby | `GET /v1/salons/nearby` with required location fields |
| Categories | `GET /v1/catalog/categories` and `/{id}/subcategories` |
| Salon | `GET /v1/salons/{id}` and its `/services`, `/staff` |
| Slots | `GET /v1/availability?staff_id=<id>&date=YYYY-MM-DD&service_ids=<id>`; repeat service IDs |
| Quote | `POST /v1/bookings/quote` (authenticated) |
| Create | `POST /v1/bookings` with `source: "app"` |
| History/detail | `GET /v1/bookings`, `GET /v1/bookings/{id}` |

Search supports name/city/address, service, category and supported location filters.
Allow manual search when location is denied. Preserve API ordering and a stable shuffle
seed across one home view's pagination. Use returned category names and image fallbacks.
Do not invent ratings, testimonials or global counts.

Creation uses salon/staff/service IDs, canonical start timestamp, customer details,
payment preference and supported optional notes. The server owns price/duration/end
time. Staff must support all chosen services; a quote does not reserve a slot.
Refresh availability after selection changes and conflicts. Creation can return pending
approval: do not always label the result confirmed.

Render returned checked-in/no-show states as well as pending, confirmed, completed,
rejected and cancelled. Use `can_cancel`, `can_request_cancellation` and
`can_confirm_payment` to expose customer actions:

- `POST /v1/bookings/{id}/cancel` for allowed direct cancellation.
- `POST /v1/bookings/{id}/cancellation-requests` for allowed late requests.
- `POST /v1/bookings/{id}/payment-confirmation-requests` for direct payment claims.

A cancellation request keeps the slot active until approved. A customer payment
claim is not proof of receipt. Display latest request decisions/reasons and delay
estimates separately from original times. Customers cannot run owner visit commands.

### QR booking

The printed URL is `https://<website-origin>/s/<qrToken>`. Resolve it through
`GET /v1/walkin/{qrToken}?fresh=true`. The route token determines salon context;
never substitute a previous selection, discovery result or the logged-in owner's salon.
Reset selections on token change and ignore late responses for an older token.

Use the returned services/staff assignments, then the normal live-slot selection.
The QR phone flow sends `POST /v1/walkin/{qrToken}/verify-phone` first with `{phone}`,
then `{phone, otp}`. Establish a supported customer session from successful verification.
Respect cooldowns; never simulate OTP success.

Submit `POST /v1/walkin/{qrToken}/bookings` with matching salon ID, customer bearer
token and idempotency key. The backend sets `source: "qr_walkin"`. Owner/staff sessions
are denied on this route. Do not forge QR source on normal booking creation.
Invalid/unavailable tokens show `qr_not_found`. There is no general QR rotation API.

### Customer payment behavior

Check the salon's `payment_options`, `online_payment_available` and unavailable reason,
alongside `GET /v1/payments/config`. Global enabled state alone is insufficient.
Offer only currently permitted methods. Pay at Salon uses `pay_at_salon`; online
advance/full preferences are `pay_advance`/`pay_full` when permitted.

Display server service amount, processing charge, total, paid/refunded/pending amounts
and instructions. Label the charge **Online payment processing charge**. Distinguish
booking, legacy payment, checkout and ledger states using each response's schema.

Backend guards include one active Pay at Salon booking per customer's appointment
date in Asia/Kolkata across salons, and a seven-day restriction after two no-shows.
Handle `pay_at_salon_daily_limit` and `pay_at_salon_temporarily_blocked`; do not calculate
eligibility locally. Disabled online requests return `online_payment_unavailable`.

When providers are enabled and verified: create `/v1/bookings/{id}/payments/intent`,
open the returned provider client payload, follow config `confirmation` via
`/payments/refresh` or `/payments/confirm`, and read `GET .../payments` plus booking
detail. SDK success alone does not establish payment. Show pending, failed, unknown
and refund states. Automatic slot release after payment failure/expiry is not guaranteed.

## 4. Website: screens and responsibilities

These are proposed website routes, not backend endpoint paths.

| Area | Routes and purpose |
| --- | --- |
| Home | `/`: factual introduction, customer discovery, register salon and owner login entry points |
| Customer | `/salons`, `/salons/[id]`, `/bookings`, `/bookings/[id]`: shared customer workflows in section 3 |
| QR | `/s/[qrToken]`: mobile-first shared QR workflow, usable without app installation |
| Account | `/login`, `/signup`, `/forgot-password`, actual callback/recovery routes, `/account`, `/notifications` |
| Owner entry | `/owner/login`, `/owner/onboarding`, `/owner/pending-approval` |
| Owner business | `/owner/dashboard`, `/owner/bookings`, `/owner/services`, `/owner/staff`, salon/hours/closures/QR/payout pages |
| Owner subscription | Website purchase and entitlement screens only when deployed billing is enabled and verified |
| Super admin | `/superadmin/login`, `/superadmin`, salon review/detail, discovery, catalog, subscriptions and settings |
| Information | Real contact/support, privacy, terms, cancellation/payment information and public account-deletion entry |

Owner web pages implement section 6's business workflows. They are requested scope,
not proof that the existing website has them. Keep customer QR state separate from
owner/admin caches. Preserve real supplied branding/app links; do not fabricate claims.

### Super-admin workflow

```text
Provisioned account -> Supabase email/password -> /v1/auth/me active super_admin
-> TOTP MFA -> Review queue -> Persisted submission -> Approve/reject
```

No public admin signup, role editor or self-promotion. Backend enforcement requires
verified `aal2` when MFA is enabled; handle `mfa_required` with a challenge. Provisioning
is trusted operational work. Prevent public caching of private HTML/data and unsafe
return-URL redirects. Account changes use supported provider confirmation flows.

| Operation | API |
| --- | --- |
| Queue/list | `GET /v1/admin/salons` with supported filters/pagination |
| Full review | `GET /v1/admin/salons/{id}` and `/{id}/onboarding` |
| Decisions | `POST /v1/admin/salons/{id}/approve` or `/reject` with required reason |
| Discovery | `PATCH /v1/admin/salons/{id}` |
| Deactivate | `POST /v1/admin/salons/{id}/deactivate` |
| Catalog | Supported `/v1/admin/catalog/categories` and subcategory commands |
| Plans | `/v1/admin/subscription-plans` and supported update/deactivate commands |
| Subscription management | Salon subscription read/manual-test activation; supported cancel/suspend and event reads |
| Erasure monitoring | `GET /v1/admin/account-deletions` |

Distinguish incomplete registrations from completed submissions. Review persisted
salon, owner contact, photos, services and staff before deciding. Refresh queue on
focus with bounded polling; do not require a general admin submission feed.

Discovery visibility is `listed|search_only|hidden`; home placement is
`top|normal|random|below`, with supported `display_priority`. Preview actual public
results. Priority is not an exact pinned position; random is a stable shuffled group.
Hiding from discovery does not disable an approved direct/QR page or owner operations.
Deactivation disables the salon and bans its owner; no current reactivation endpoint
exists. Require explicit consequence-aware confirmation.

Admin manual/test subscriptions must never be labeled payment-verified. Website owner
purchase uses `/v1/subscriptions/config`, `/v1/subscription-plans`,
`/v1/salons/me/subscription/checkout` and `/verify`, followed by authoritative entitlement
reads. Checkout requires an idempotency key; provider callback alone never grants access.
Supported cancellation/history live under `/v1/salons/me/subscription`. Confirm deployed
availability first; billing is disabled by default.

## 5. Customer app: screens and responsibilities

| Screen group | Purpose |
| --- | --- |
| Startup/auth | Session restore, configured provider sign-in and safe callback/recovery |
| Home/search/nearby | Mobile discovery; manual location fallback |
| Salon/booking steps/result | Shared service/staff/slot/quote/submission flow |
| My bookings/detail | Appointment history, state, permitted cancellation/payment requests |
| QR entry | Camera scanner or supported app links into the shared QR flow |
| Notifications | Read state and navigation into current booking details |
| Account/help/legal | Profile/avatar, support/report, recovery, deletion and real policies |

Use section 3 without introducing a separate booking protocol. Allow public browsing
before login and preserve safe booking drafts through authentication. Never call
`/v1/auth/owner-access` in customer startup: it can promote the account to owner.

Native scanning/universal links need platform configuration in the app repository;
the backend does not supply them automatically. Validate supported QR origins and
do not treat arbitrary scanned URLs as trusted app navigation. Denied camera/location/
notification permissions need useful fallbacks. Suggested navigation is Home, Bookings
and Account, with QR/notifications accessible; adapt to the actual app.

## 6. Owner app and owner web: business workflows

The following applies to both owner clients. Mobile subscription restrictions are
stated separately below rather than assuming website and mobile purchase behavior match.

### Owner access, onboarding and review

```text
Configured Supabase sign-in -> POST /v1/auth/owner-access -> GET /v1/auth/me
-> GET /v1/salons/me -> Onboard -> Pending/rejected review -> Eligible workspace
```

The owner-access command promotes an active customer; owners/staff/admins are returned
unchanged. Route by returned role. It does not make staff an owner or assign an admin
a salon. Show onboarding if no salon exists. Initial salon creation is lazy through
`POST /v1/salons/me/complete-profile`; do not fabricate a salon ID or upload resources
against a nonexistent salon.

Collect the required business details, category, address/city, IANA timezone and
working hours using current schema. Continue setup with server
`GET /v1/salons/me/setup-status`: business basics, working hours, photos, services,
staff and payout. Use returned item actions/counts; checklist completion is not approval.

Pending owners see waiting status and supported setup edits. Rejected owners see
`rejection_reason`, correct details and resubmit complete-profile, resetting rejected
to pending. Approved owners enter operations only when active/completed and otherwise
eligible. Refresh salon/access state on foreground or approval notification. Daily
operations can return `awaiting_admin_approval` even if a client bypasses its screen.

Read `/v1/salons/me/access-state` and `/subscription` for backend trial/entitlement
facts, wall flag and messages. The trial is two calendar months or 120 created bookings,
whichever comes first; cancelled bookings do not replenish it. Preserve supported
existing-booking history, collection and completion after an entitlement lock.

### Owner screens and daily appointments

Provide startup/auth, onboarding/review, dashboard, booking list/detail, add walk-in,
customer requests, services, staff, salon/gallery, hours/time off, QR, collections,
payout, subscription/access, notifications/support and account screens.

Use actual booking/earnings data on the dashboard; no fabricated analytics or global
counts from one page. Suggested mobile navigation is Dashboard, Bookings and More
with service/staff management accessible. Staff need role-appropriate controls.

| Operation | API |
| --- | --- |
| Read bookings | `GET /v1/bookings`, `GET /v1/bookings/{id}` |
| Approve/reject | `POST /v1/bookings/{id}/approve`, `/reject` |
| Arrival/no-show | `POST .../check-in`, `.../no-show` |
| Collection/completion | `POST .../payment`, `.../complete` |
| Delay/cancel | `POST .../delay`, `.../cancel/barber` |
| Customer requests | `GET /v1/booking-action-requests`, `POST /{id}/respond` |

A typical visit is confirmation -> check-in -> service -> outstanding collection ->
completion, subject to backend transitions. No-show is rejected before appointment
start. Delay uses `estimated_end_datetime` later than the original end and optional
`notify_affected_customers`; display estimate separately. Use supported booking filters
and refresh after mutations; the backend owns authorization and legal actions.

Manual walk-in creation uses the normal live availability/quote rules and
`POST /v1/bookings` with `source: "manual_walkin"` and an idempotency key. Do not use
the customer-only QR route or fabricate an Auth identity for a manual customer.

Customer request decisions are `received|not_received` for payment and
`approve|decline` for cancellation, with a reason for decline. Follow current method
fields. A stale second decision can return 409. Never use a direct payment claim to
establish a gateway capture.

### Business resources, media and time off

| Resource | API entry points |
| --- | --- |
| Business profile/settings | `GET/PATCH /v1/salons/me`, `PATCH /v1/salons/me/settings` |
| Services | `GET/POST /v1/salons/me/services`, supported item PATCH/DELETE |
| Staff | `GET/POST /v1/salons/me/staff`, supported item PATCH/DELETE |
| Assignments | `GET/POST /v1/salons/me/staff/{id}/services`; supported assignment languages GET/PUT |
| Gallery | `GET/POST /v1/salons/me/images`, supported item PATCH/DELETE |
| Hours/time off | Settings; `/v1/salons/me/holidays`, `/blocks` and supported removals |
| Closure | `POST /v1/salons/me/closures/preview`, then `/closures` |
| Owner QR | `GET /v1/salons/me/qr` |

Assign services to active compatible staff; a visible service without an eligible
assignment is not necessarily bookable. Use server price/duration overrides and
soft-deactivation semantics. No general staff invitation/transfer flow is established.
Availability selects a specific staff member; do not invent an "Any staff" API.

Use backend-issued upload grants for gallery, staff photos and profile avatars.
PUT supported processed image bytes to the signed gateway, then attach the returned
media references/proof using the resource API. Follow any result URL in the current
response; never construct R2 URLs or attach an unprocessed original on failure.
JPEG/PNG/WebP inputs are limited to 5 MiB and backend pixel/dimension limits; convert
HEIC/HEIF on device. Handle grant expiry, retries and namespace validation.

Closures require an impact preview, explicit review and confirmation of the exact
expected booking IDs. If impact changes, refresh/review again. Pausing new bookings
is not the same as cancelling existing appointments. Owner QR sharing/printing must
use the returned code and be tested against the actual web destination.

### Collections, payout and provider onboarding

Record direct collection with `POST /v1/bookings/{id}/payment` using the current
`cash|upi_direct` contract. Completion can return `payment_collection_required` until
paid. Read `/v1/bookings/{id}/payments` and `/v1/salons/me/earnings` for authoritative
records. Separate cash/manual receipts, gateway collections, refunds, commissions and
settlements; earnings are not proof of bank settlement.

Owner-only `GET/PUT /v1/salons/me/payout-account` and `/history` work during pending
setup. Responses mask bank numbers. Omitted PUT fields keep values; explicit null/blank
clears them. The merged details need a holder plus UPI or account/IFSC. Never resubmit
masked last-four digits as a full account number or log sensitive bank/KYC input.

Provider status lives separately at `/v1/salons/me/settlement-account` with supported
`/register`. Show it only when configured/supported and render returned requirements.
Saved payout details do not establish active provider KYC. Registration/refund unknown
outcomes require same-key retry/reconciliation. Owner refund endpoint is
`POST /v1/bookings/{id}/payments/{payment_id}/refund`; follow ledger rules, especially
for excess collections, rather than calculating refund entitlement locally.

### Owner mobile subscription boundary

Current project integration sets `native_purchase_allowed=false`. Owner mobile reads
entitlement/trial state and notices; it must not show subscription prices or purchase
controls. Do not add a purchase link without the reviewed project distribution flow.
Website purchase is described in section 4. This is the repository contract, not a new
legal/store-policy assessment. Plan feature labels do not prove every named feature
is implemented. Never invoke admin test activation or grant premium locally.

## 7. Shared notifications, profile, support and erasure

### Profile and notifications

Customer profile uses `/v1/customer/profile`; shared identity profile uses
`/v1/profiles/me`, with supported GET/PATCH. Customer avatar upload additionally
supports `POST /v1/customer/profile/avatar`, multipart field `image`, persisting the
processed avatar without a second PATCH. Owner resource media uses section 6's grants.

Use `GET /v1/notifications`, `POST /v1/notifications/{id}/read`,
`POST /v1/notifications/read-all`, `POST /v1/devices` and supported device token removal.
Handle denied permissions, token rotation and account switching. Approval notifications
may have no booking ID; route owners to review/setup. Scheduled reminders require
separate scheduled infrastructure and are not guaranteed by these endpoints.

### Reports and support

Customers report salons using `POST /v1/reports`; identity/timestamps are server-owned.
This is not a public review. Support provides `POST /v1/support/tickets`, known thread
`GET /v1/support/tickets/{id}` and authorized owner/admin `POST /{id}/reply`. Creation/
replies need idempotency. A general inbox/list route and customer reply route are not
established. Email status `/v1/email/events/{id}` is scoped to its customer; owners
must not assume access. Delivery depends on configured email processing.

### Account deletion: one protocol, different consequences

1. Request `POST /v1/account/deletion/challenges` for the supported verified contact.
2. Verify code at `POST /v1/account/deletion/challenges/{id}/verify`.
3. Show irreversible consequences; submit `/v1/account/deletion` with challenge,
   confirmation token and `confirm: "DELETE"`.
4. After acceptance sign out/clear private data; track `/v1/account/deletion/{id}`
   using returned `X-Status-Token`, not the old bearer token. Keep status tokens private.

| Account | Consequences/blockers |
| --- | --- |
| Customer | Open bookings/pending action requests can block with `deletion_blocked`; explain returned counts; past history is anonymized |
| Owner | Show `bookings_to_cancel`; upcoming appointments are cancelled, customers notified and applicable online refunds processed; direct salon receipts are not platform-refunded; configured active paid subscriptions can block |

Owner erasure removes business/account details and can remove salon-only staff identities;
an anonymous closed-salon shell retains customer history. Show returned queued/refunding/
waiting/erasing/completed stages. A failed status can indicate scheduled retry. No grace
period or unconditional refund/completion-time promise: provider failures have retry
limits and operator handling. Customers seeing `salon_closed` need closure/refund context.

## 8. Critical boundaries and release evidence

These points take precedence over optimistic or older examples:

- Provider adapters and checkout routes exist, but online payments/subscription billing
  are disabled by default and need real staging/sandbox verification. Do not equate
  source implementation, a mocked test or SDK success with a live payment feature.
- Older website guidance says subscription checkout is absent and booking idempotency
  is short-lived Redis-only. Current source/newer checkout contracts add provider
  billing and transaction-backed replay. Confirm the deployed version before adopting
  either behavior; do not copy old assumptions.
- Older owner examples omit newer checked-in/no-show and trial/access-wall behavior
  and use earlier payment methods. Follow deployed schemas and newer checkout rules.
- Customer reviews/ratings submission, cloud favorites and style-photo publishing are
  future work. General platform analytics, exhaustive user directory, general admin
  activity history and automatic failed-payment slot release are not established.
- Backend rollout requires separately reviewed migrations and workers. Do not copy
  historical `upgrade head` examples as current deployment authorization.
- The static audit records unresolved backend issues, including some outages reported
  as slot conflicts, OTP throttle weaknesses, proxy rate-limit concerns and CI gaps.
  Repeated conflicts need recovery/support rather than endless slot retries. Coordinate
  backend remediation and target-specific verification before public release.

### Verification ownership

| Owner | Minimum evidence |
| --- | --- |
| Every frontend | Real auth/callback/refresh/logout, role isolation, accessible states, no secrets, own lint/tests/build |
| Website | Customer/owner journeys; direct admin URL denial; real MFA enforcement; persisted review and discovery preview; two QR routes with back/forward and late responses |
| Customer app | Permission fallbacks; real booking and cancellation/claim flow; native QR/app links; concurrent slot conflict and same-key retry |
| Owner app | No-salon onboarding; pending/rejected/approved states; staff restrictions; collection-before-completion; closure impact changes; no native subscription purchase UI |
| Backend/provider operators | Correct deployed contract/migrations, workers and redirects; actual OTP/push/email; payment sandbox and erasure/refund recovery |

Use two owned test salons and disposable/staging accounts. Test account switching,
timezones, duplicate taps, unknown write outcomes, disabled providers, entitlement locks
preserving history, media failure and deletion blockers. This handoff involved no live
provider/frontend tests or application changes; it is not release sign-off.

## 9. Technical references

These are detailed contracts and evidence, not additional copies of this handoff:

- [Complete current API inventory and data models](BACKEND_API_REFERENCE.md)
- [Customer API contract](Customer-App-Backend-API-Document.md)
- [Owner API contract](Salon-Owner-App-Backend-API-Document.md)
- [Public discovery and QR](PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md)
- [Frontend integration](frontend-integration.md)
- [Current checkout and access rules](../backend/docs/PRODUCTION_VERIFICATION.md)
- [Salon approval](../backend/docs/SALON_APPROVAL.md)
- [Payments](../backend/docs/PAYMENTS.md)
- [Payout accounts](../backend/docs/PAYOUT_ACCOUNTS.md)
- [Subscriptions](../backend/docs/SUBSCRIPTIONS.md)
- [Media](../backend/docs/IMAGE_MEDIA.md)
- [Account deletion](../backend/docs/ACCOUNT_DELETION.md)
- [Static audit and limitations](../backend/docs/verification/FULL_API_ARCHITECTURE_AUDIT_2026-10-21.md)
