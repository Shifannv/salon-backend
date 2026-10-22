# Static API and architecture audit: salon-backend

| | |
|---|---|
| **Date** | 2026-10-21 (corrected 2026-10-22) |
| **Commit** | `828d73b` (branch `shifan`) |
| **Scope** | All 140 routes under `backend/app/api/`, plus the use cases, repositories, schemas, SQL migrations and tests behind them |
| **Mode** | Static and read-only. No code, test, migration, database, infrastructure or provider was changed or contacted. This is not a runtime or security certification. |
| **Audience** | CTO and backend team |

## 1. Executive summary

The backend is in better shape than a typical early-stage API. The rules that matter most hold:

- Bookings are created only through Postgres `create_booking()`.
- Double-booking is prevented by a GiST exclusion constraint, which since migration 0035 also covers checked-in bookings.
- A database trigger enforces the booking state machine.
- Every sampled by-ID owner, booking and money operation is scoped to the actor's salon and returns 404 for other tenants.
- Webhooks verify signatures over raw bytes before parsing.
- One error envelope is mapped centrally.

Most POST routes are correct commands, not misused writes. HTTP-method problems are rare: two findings among 140 routes.

**Findings:** Critical 0 · **High 4** · **Medium 17** · Low 23 · Informational 11. **No finding needs a database migration.** Every recommendation is backward compatible, because client integration status is not verified (§2).

**Scope of this audit.** This is a static API and architecture audit. It inspected all 140 route declarations and traced the highest-risk code paths. It is **not** a complete runtime or security certification. The four specialist reviews stopped early, so authorization and security tracing was sampled in several areas (§2). Findings labelled **Concern** need targeted verification before action. Findings labelled **Proven** are established by reading the code path and stand as written.

### Top five risks

1. **ERR-02 (High): booking creation reports outages as slot conflicts.** `except Exception` plus message-substring matching (`platform_repository.py:1571-1590`) turns connection failures, timeouts and bad data into 409 `slot_unavailable` or `conflict`. That breaks the published "real slot conflict only" guarantee and hides 5xx errors on the platform's main write path.
2. **SEC-01 (High): the walk-in OTP rate limit can be bypassed.** The limit is keyed on the raw phone string (`walkin.py:152`), so `+919876543210` and `+91 98765 43210` get separate buckets. The limiter fails open without Redis, and the only gate is a QR token printed on the salon wall. The risk is SMS cost and harassment of third parties.
3. **SEC-02 (High — deployment verification required): per-IP limits may collapse behind a proxy.** uvicorn trusts `X-Forwarded-For` only from configured trusted proxies, and none is configured. If Cloud Run presents its own proxy address, the password-reset limit (10 per hour per IP) applies to **everyone** together. This is a check for the deployment owner, not an immediate code change, and the fix must not be a blanket trust setting (§8).
4. **TEST-01 (High): the account-erasure real-Postgres suite never runs in CI.** Only `MIGRATION_TEST_DB` is set (`backend.yml:49`). The only hard-delete path, which handles PII and refunds, can regress with a green CI. Media locking, approval and Redis-recovery suites are skipped too.
5. **ENUM-03 / ERR-01 (Medium): bad input surfaces as server errors.** A mistyped salon `timezone`, which is free text and used in slot SQL, makes that salon's availability fail for every customer. Malformed path IDs return 500 "Please try again".

### Top five quick wins (each under half a day, no migration)

1. **SEC-01 + ENUM-02:** key the OTP limiter on the normalised phone, using the profile validator that already exists (`schemas/platform.py:46-74`), and back it with the fail-closed Postgres throttle.
2. **SEC-02 verification on isolated staging (deployment owner):** confirm the real proxy path and trusted peer addresses before any `FORWARDED_ALLOW_IPS` change.
3. **TEST-01:** add the missing gate variables to `backend.yml` so the erasure and other real-Postgres suites run in CI.
4. **ERR-01 + ENUM-03:** type path IDs as `UUID` and validate `timezone` against IANA names. Both turn 500s into 422s.
5. **DATA-01:** reuse the allow-list pattern already in `platform_repository.py:1199-1206` at the 10 other sites that build SQL column names from dictionary keys.

### Migration outlook

No Phase A or Phase B item requires an Alembic migration. Two optional later hardenings would need one: a `CHECK` constraint on `salons.timezone`, and explicit `ERRCODE` values raised from the booking SQL functions. Both are deferrable.

### Coverage caveat

The four specialist review agents stopped early on an API usage limit, so their domains were covered by direct tracing of the highest-risk paths rather than an exhaustive per-route review. §2 lists exactly what was and was not covered.

## 2. Audit methodology and limitations

### Method

1. **Route inventory.** Every route decorator in the 18 modules under `backend/app/api/v1/routes/`, plus the mount table in `backend/app/api/v1/router.py` and the health mount in `backend/app/main.py:114`, was read and tabulated: method, full path, handler, request and response schema, status code, auth dependency and parameter validation. Result: **140 routes** (Appendix, §17).
2. **Layer-by-layer tracing.** No finding is based on a route name. Each candidate was traced handler → schema → use case → repository → test before being recorded. Several candidates were **disproved** this way and are listed in §15 so they are not raised again (for example the "stale walk-in cache after a staff change" that looks like a bug but is not, §11).
3. **Specialist review.** Four of this repository's read-only review agents (`security-reviewer`, `database-reviewer`, `python-reviewer`, `performance-analyst`) were dispatched in parallel. **All four stopped early on an API usage limit and returned no findings.** Their scope was then covered directly, by tracing the highest-risk paths in each domain: tenant isolation on by-ID operations, money routes, uploads, webhooks, role promotion, rate limits, the booking constraint, transaction and cache behaviour, unbounded lists, and blocking work on the event loop. That coverage is a **sample of high-risk paths, not an exhaustive per-route review**. §2 "Limitations" lists what this leaves open.
4. **Dedup against the decision record.** Every finding was checked against `docs/agent-memory/shared/decisions.md`, `backend/docs/migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md` (owner approvals U01–U07 and about 80 statused decisions), `docs/agent-memory/shared/{roadmap,domain-rules,gotchas}.md` and the 28 prior reviews in `backend/docs/verification/`. Anything already decided is cited in §15 or §16, **not** raised as a new finding.
5. **Binding rules.** Code was judged against the 51 rules in `AGENTS.md` and the HTTP-method standard in the audit brief (GET read-only; POST for creation **and** for commands such as approve, reject, cancel, check-in, webhook receipt and idempotent actions; PATCH for partial update of editable fields; PUT only for true full replacement; DELETE where retention allows).

### Evidence labels

Every finding carries one of two labels.

- **Proven**: the defect is established by reading the code path end to end. The file and line references let a reader confirm it without running anything.
- **Concern**: the mechanism is proven from code, but its real-world impact depends on something this read-only audit could not observe (traffic shape, provider configuration, a database behaviour that needs a live connection). Each concern states how to verify it.

### Limitations: what was NOT verified

This was a static, read-only audit. In particular:

- **No code was executed.** `pytest`, `alembic` and the application were not run. Test coverage statements in §12 come from reading test files and names, not from a coverage report.
- **No database, Redis, R2, Supabase, Cashfree, Razorpay or FCM was contacted**, and no staging or production environment was touched. Database-level behaviour (lock ordering, constraint enforcement, the exact error asyncpg raises for a malformed UUID) is inferred from source and SQL, and is labelled as such.
- **Provider-side controls are unknown.** In particular the Supabase project's own SMS and OTP rate limits were not visible, and they bound the impact of SEC-01.
- **Sampled, not exhaustive, security and data review.** Because the specialist agents did not complete, the following were **not** reviewed route by route: tenant scoping of every one of the 91 actor-only routes (a high-risk sample was traced; §8.1); every booking-action and closure SQL path; subscription-billing transaction ordering; the payment-flow commits in `use_cases/payments.py` beyond the refund and intent paths; N+1 patterns outside `list_bookings`; and connection-pool sizing against the deployment's process count. A follow-up specialist pass on these areas is recommended. It should reuse this report's §15 and §16 to avoid re-raising settled items.
- **The knowledge graph is stale.** `graphify-out/GRAPH_REPORT.md` was built from commit `54c09ff`, while `HEAD` is `828d73b`, and `graphify-out/wiki/` does not exist. No finding relies on a graph signal alone.
- **Frontend repositories were not inspected.** "Frontend impact" columns describe the effect on a client of this API, not verified client code.

### Client integration status

Client integration status differs by client and is not fully verified. Some frontend flows remain mock-first or await deployment/API wiring. Therefore all API changes must preserve backward compatibility until each client is verified against the deployed contract.

Every recommendation in this report is therefore **additive or versioned**. No response shape, enum tightening, path rename or method change is proposed as a breaking change. Where a method or path is semantically wrong, the recommendation is to add the correct form alongside the existing one and deprecate the old form, not to replace it.

Evidence for the mixed state: `docs/FRONTEND_INTEGRATION_PROMPTS.md:13-14` ("The main work is verifying the deployed release and wiring the clients to it") and `docs/frontend-integration.md:3-8` (contract items clients "must adopt"). This audit did not inspect the frontend repositories, so it makes no claim about which routes any client calls.

## 3. Current backend architecture overview

This section describes what exists so the findings have context. It does not restate [`backend/docs/ARCHITECTURE.md`](../ARCHITECTURE.md) or [`backend/docs/AUTHORIZATION.md`](../AUTHORIZATION.md); those remain the source of truth.

### Layers

| Layer | Path | Size | Role |
|---|---|---|---|
| API | `backend/app/api/` | 18 route modules, 15 schema modules, `deps.py` | Routers, request and response schemas, auth extraction, dependency wiring |
| Application | `backend/app/application/` | 17 use-case modules, 13 ports | Use cases (authorization lives here) and gateway ports |
| Domain | `backend/app/domain/` | 27 `StrEnum` types, policy services | Pure Python entities, enums and policies |
| Infrastructure | `backend/app/infrastructure/` | 9 repositories plus adapters | Postgres, Supabase, R2, Redis, FCM, Cashfree, Razorpay, fake provider, workers |

About 25,800 lines of application code in 142 files, and 93 test files.

### Request path

`TimingMiddleware` (request ID, timing; outermost) → `CORSMiddleware` → `UploadAdmissionMiddleware` (media paths only) → router (`backend/app/main.py:99-111`).

Authentication is a dependency chain in `backend/app/api/deps.py`:

- `get_current_actor` (`deps.py:80`) verifies the Supabase JWT against JWKS and loads the profile by `sub`. It rejects a missing or inactive profile with 401. It performs **no role check**.
- `get_authenticated_session` (`deps.py:101`) adds, on every POST, PUT, PATCH and DELETE, a per-actor throttle backed by the Postgres table `api_rate_limits`, **commits** it (`deps.py:119`), then arms the audit actor with `SET LOCAL request.jwt.claims` (`deps.py:120`).
- `require_role(*roles)` (`deps.py:124`) adds the role check from `profiles` and, for `super_admin`, the `aal2` MFA requirement.

### Data rules that hold

The core database rules in `AGENTS.md` are **met** (confirmed in §10):

- Bookings are created only through Postgres `create_booking()` (`platform_repository.py:1523-1531`, the single call site).
- Availability comes only from Postgres `get_available_slots()` (`platform_repository.py:1453`, `:1635`).
- No Python code inserts into or deletes from `bookings` or `booking_services`.
- Availability, slot and booking payloads are never cached (`_LIVE_PREFIXES`, `infrastructure/cache/redis.py:34`).

### Read cache

Only public read models are cached in Redis (salon detail, services and staff; the catalog; walk-in QR pages). Keys are versioned as `read-model:v2:{snapshot}:{epoch}:{key}`. **Every database commit rotates a single global epoch** (`infrastructure/db/session.py:45-50` → `redis.py:66-91`), which invalidates every cached read for every salon at once. This errs safely toward freshness. Its cost is examined in §10 (PERF-01).

### Error contract

One envelope, `{"error": {"code", "message", "details"}}`, built in `backend/app/core/exceptions.py:276-285`. There are 39 typed error codes, mapped to HTTP status once globally (`exceptions.py:296`, registered at `main.py:113`). No route raises a raw `HTTPException`. The contract is published in [`docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md`](../../../docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md) §5 and [`docs/Customer-App-Backend-API-Document.md`](../../../docs/Customer-App-Backend-API-Document.md).

### Clients

There are exactly three frontends: the customer app, the owner app and one website (`docs/FRONTEND_INTEGRATION_PROMPTS.md:7-9`). The website runs the full customer flow and the full owner flow on the same `/v1` APIs and server-side logic as the apps, and also holds the QR booking page, the home page and the private super-admin workspace. `CLAUDE.md` counts the website's surfaces separately and says "four clients"; see DOC-07.

### 3.1 Website flow coverage

The website must run the same workflows and business logic as the apps. The APIs are client-agnostic, so no website-only copy of business logic is needed. The 2026-10-22 source scan ([frontend-api-usage-2026-10-22.md](frontend-api-usage-2026-10-22.md) §6) shows where the website stands today:

- public discovery, QR booking and super-admin are wired;
- the customer account is partly wired (bookings and account deletion; not profile or notifications);
- the owner workspace calls **no** backend route yet.

| Website surface | Backend support today | Notes and gaps |
|---|---|---|
| Home | Public discovery: `GET /v1/salons`, `/v1/catalog/*` | No auth needed |
| Customer flow (no app needed) | Supabase sign-in; `GET /v1/salons`, `/v1/salons/{id}`, `/services`, `/staff`, `/v1/availability`; `POST /v1/bookings`; `GET /v1/bookings`, `POST /v1/bookings/{id}/cancel`; `/v1/notifications`; `/v1/profiles/me`; `/v1/account/deletion/*` | Web bookings are stored as `source = "app"` because `BookingSource` has no web value (`domain/entities/booking.py:20`). A new value needs a reviewed migration and is an owner decision, needed only if analytics must separate web from app. Web push is not verified: device registration accepts a free-text `platform` (`schemas/platform.py:726`). |
| QR booking | `GET /v1/walkin/{qr_token}`, `POST …/verify-phone`, `POST …/bookings` | Website sign-in route is an open decision (`docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §4). An account whose role is owner cannot complete the QR booking (`docs/FRONTEND_INTEGRATION_PROMPTS.md`). |
| Owner workspace | `POST /v1/auth/owner-access`; `PATCH /v1/salons/me`, `POST …/complete-profile`, `GET …/setup-status`; status through `approval_status`, `rejection_reason` and notifications; after approval, every `/v1/salons/me/*` route | "Live" status means polling; there is no push feed to the website. **Gap, not built:** a multi-message super-admin to owner review thread. Today there is one `rejection_reason`, a resubmit and one decision notification (`backend/docs/SALON_APPROVAL.md`). A thread needs a new table, a reviewed migration and endpoints, and must be scoped and planned separately before any code. |
| Super-admin | `/v1/admin/*` with `aal2` | |

## 4. API inventory summary

The full table is in §17. Totals: **140 routes**, of which 136 are under `/v1` and 4 are the unversioned health routes (`/health`, `/health/db`, `/health/redis`, `/health/ready`). The health routes are unversioned deliberately: `AGENTS.md` rule 37 keeps health checks at `/health`.

| Group | Routes | Auth model | Notes |
|---|---|---|---|
| Public discovery | 10 | None | Salons, nearby, detail, services, staff, catalog, availability, payment and subscription config. Cached read models except availability. |
| Auth and account | 10 | Actor; deletion status uses an HMAC `X-Status-Token` | `auth/me`, refresh, forgot-password, owner-access, profile, avatar upload URL, four deletion routes |
| Customer | 3 | Actor | Customer profile read and update, salon report |
| Owner workspace | 36 | Actor, with ownership enforced in the use case | Salon, settings, payout, setup, QR, images, holidays, services, staff, languages, blocks, closures, earnings, settlement |
| Booking | 17 | Actor | Create, list, get, quote, state commands, payment record, action requests |
| Walk-in / QR | 4 | Public, except booking creation | Router-wide 32-hex token check (`walkin.py:29-39`) |
| Payments and refunds | 6 | Actor (customer for intent and confirm, owner for refund) | Online gateway flows; dormant until a provider is configured |
| Subscriptions (owner billing) | 7 | Actor | Plans, state, access-state, checkout, verify, cancel, history |
| Media | 6 | Signed token, or actor for the upload-URL issuers | Signed PUT sink plus result read; three upload-URL issuers |
| Notifications and support | 9 | Actor; support reply requires owner or super_admin | |
| Admin | 27 | `require_role(super_admin)` plus `aal2`, except one route (SEC-05) | Served from three modules (`router.py:29,36,47`) |
| Webhooks | 1 | Provider signature over the raw body | Mounted only when a provider is enabled (`router.py:50-54`) |
| Health | 4 | None | |

**Methods:** POST 64, GET 56, PATCH 11, DELETE 6, PUT 3.

**Authentication:** 21 routes have no auth dependency, all of them deliberately (public discovery, signed-token media, the webhook, deletion status, the QR page, health). 28 use `require_role`. The remaining 91 only authenticate, and push role and ownership checks into the use-case layer, as `AGENTS.md` rule 13 requires. Section 8 confirms that this use-case enforcement holds for the sampled high-risk routes.

**Contract hygiene at a glance:**

- Every route declares an explicit status code.
- Four `DELETE` routes returning 204 have no `response_model` (AGENTS.md rule 16; API-11).
- 13 routes read `Idempotency-Key`; §9 explains which ones require it.
- Path IDs are typed as `UUID` in `support.py`, `subscriptions.py`, `account_deletion.py` and part of `admin.py`, and as raw `str` everywhere else (ERR-01).

## 5. HTTP method findings

Each route was judged against the brief's standard, not against "every write must be PATCH". **Most of the 64 POST routes are correct**, and §5.2 lists them so they are not re-litigated. Only two method findings survived verification, and neither justifies a breaking change, because clients may already call these routes.

### 5.1 Findings

**API-01: `PUT /v1/salons/me/payout-account` has PATCH semantics** (Medium, Proven)

- *Evidence:* `owner.py:166` declares PUT. Its body, `OwnerPayoutAccountRequest` in `schemas/platform.py`, documents itself as *"Partial update of the owner's payout destination (merge semantics). Omitted fields keep their stored value; an explicit `null` clears the field."* Every field is optional.
- *Why it is semantically wrong:* PUT promises that the body is the complete new representation, so an omitted field means "absent". Here an omitted field means "keep". A client or SDK that follows PUT semantics will keep stale data it intended to drop. For example, sending only the bank fields to switch an owner from UPI to bank transfer leaves the old `upi_id` on the payout record: the owner believes the UPI was removed, but the backend still holds it. This is a payout-destination record, so the impact grows when payouts go live (payout holds are approved but not built; see `docs/agent-memory/shared/roadmap.md`).
- *Safe alternative:* add `PATCH /v1/salons/me/payout-account`, bound to the **same** handler with the same merge semantics. Keep PUT as a deprecated alias with unchanged behaviour. Do **not** convert PUT to true full replacement: clients that may already send partial bodies would then silently clear fields, which is worse than the current mismatch. Document in the owner API document that omitting a field never clears it.

**API-03: `POST …/deactivate` duplicates `PATCH {"is_active": false}`** (Low, Proven)

- *Evidence:* `deactivate_category` is literally `return await self.update_category(category_id, {"is_active": False})` (`platform_repository.py:3381-3384`). `CategoryUpdateRequest`, `SubcategoryUpdateRequest` and `PlanUpdateRequest` all accept `is_active` (`schemas/admin.py:128,169`; `schemas/subscription.py:56`). The same applies to the subcategory and subscription-plan deactivate routes.
- *Why it matters:* two routes, one behaviour. An explicit deactivate command is a reasonable POST, so neither is wrong. But the admin client has two ways to do the same thing, and only the PATCH form can also reactivate.
- *Recommendation:* keep both. Document `PATCH is_active` as canonical for catalog and plans. Reserve deactivate commands for cases where deactivation has extra effects, such as the admin salon case in §5.2.

### 5.2 POST routes that are correct and must stay POST

| Route(s) | Why POST is correct |
|---|---|
| `POST /v1/bookings`, `POST /v1/walkin/{qr_token}/bookings` | Resource creation through `create_booking()`, idempotency-protected |
| `POST /v1/bookings/{id}/approve`, `/reject`, `/check-in`, `/no-show`, `/complete`, `/delay`, `/cancel`, `/cancel/barber` | State-machine commands, not field edits. A database trigger enforces the legal transitions (`migrations/sql/0035_booking_checkout_safety.sql:109-110`). |
| `POST /v1/bookings/{id}/payment`, `…/payments/intent`, `/confirm`, `/refresh`, `/cancel`, `…/payments/{pid}/refund` | Money commands with idempotency and provider side effects |
| `POST /v1/booking-action-requests/{id}/respond`, `POST /v1/bookings/{id}/payment-confirmation-requests`, `…/cancellation-requests` | Workflow commands that create request records |
| `POST /v1/salons/me/closures` | Bulk command that cancels the affected bookings in one transaction |
| `POST /v1/admin/salons/{id}/approve`, `/reject` | Approval workflow commands, idempotent on repeat (`backend/docs/SALON_APPROVAL.md`) |
| `POST /v1/admin/salons/{id}/deactivate` | Compound command: soft-deletes the salon **and** bans the owner's Supabase Auth account (`admin.py:202-218`). It cannot be expressed as a field PATCH. |
| `POST /v1/salons/me/complete-profile` | Submit-for-approval command |
| `POST /v1/auth/owner-access`, `/refresh`, `/forgot-password`, `POST /v1/walkin/{token}/verify-phone` | Authentication commands |
| `POST /v1/account/deletion/challenges`, `…/verify`, `POST /v1/account/deletion` | Deletion workflow commands (`backend/docs/ACCOUNT_DELETION.md`) |
| `POST /v1/webhooks/{provider}` | Webhook receipt |
| `POST /v1/salons/me/subscription/checkout`, `/verify`, `/cancel` | Billing commands with provider side effects |
| `POST /v1/bookings/quote`, `POST /v1/salons/me/closures/preview` | Safe computations with structured bodies; POST is acceptable. See PERF-01: they are throttled and committed as if they were mutations. |
| `POST /v1/notifications/{id}/read`, `POST /v1/notifications/read-all` | Idempotent "mark" commands. `PATCH /notifications/{id}` would be the textbook form for the single case, but the command form is common and correct in effect, and `read-all` has no single resource to PATCH. Do not change. |
| `POST /v1/devices` (returns 200) | Register-or-reactivate upsert keyed by token (`notifications.py:79-89`). 200 is correct for an upsert that may not create anything. |
| `POST /v1/salons/me/staff/{id}/services` (returns 200) | Creates an assignment, so 201 would be more precise. Changing it now would break clients that branch on 200. Do not change. |

### 5.3 PUT and DELETE

- `PUT /v1/salons/me/staff/{sid}/services/{ssid}/languages` (`owner.py:693`) **is** a true idempotent set of a collection. PUT is correct.
- `PUT /v1/media/uploads/{token}` (`media.py:45`) is a signed upload of an object to a server-chosen key. PUT is correct.
- DELETE is used for soft deletes, which is acceptable, but with two different response conventions (API-04, §6).

## 6. Endpoint duplication and contract inconsistencies

**API-02: explicit `null` means four different things across PATCH endpoints** (Medium, Proven)

Routes pass `payload.model_dump(exclude_unset=True)`, so an explicit `null` sent by a client **does** reach the repository. What happens next depends on the endpoint:

| Behaviour on `{"field": null}` | Where | Evidence |
|---|---|---|
| **Silently ignored**; returns 200 with the old value | Owner salon, salon images, staff, admin salon, categories, subcategories, subscription plans | Each repository filters `{k: v for k, v in values.items() if v is not None}`: `platform_repository.py:852-860`, `:985-991`, `:1303-1309`, `:3223-3229`, `:3355-3363`, `:3456-3460`; `subscription_repository.py:57-58` |
| **Clears the field** | Profile, including `full_name`, whose schema says `min_length=1` but whose column is nullable | `platform_repository.py:164` writes every key; `profiles.full_name` is nullable (`migrations/sql/001_supabase_schema.sql:61`) |
| **Clears** optional fields, **422** on required ones | Owner services | `_service_write_values` plus the null check (`platform_repository.py:1199-1218`) |
| **Clears** (documented merge semantics) | Payout account | `OwnerPayoutAccountRequest` docstring |

*Why it matters:* a client "clear this field" action on any endpoint in the first row (an image caption, a staff specialization, a category description) silently does nothing and reports success. Separately, a client can blank a customer's name through the profile endpoint, which the schema intended to forbid.

*Recommendation:* do not change behaviour globally. Clients may already send `null` meaning "no change" on the first-row endpoints. Instead:

1. Document the current per-endpoint behaviour in the client API documents now (Phase A).
2. Where product needs a "clear" action, adopt the per-field policy that `_service_write_values` already implements: an explicit writable set, nullable fields clearable, required fields rejected with 422.
3. Make profile `full_name` reject `null`, matching its schema intent.

**API-04: three conventions for "soft delete"** (Low, Proven)

| Convention | Routes |
|---|---|
| `DELETE` → 204, no body | `/v1/salons/me/images/{id}`, `/holidays/{id}`, `/blocks/{id}`, `/v1/devices/{token}` |
| `DELETE` → 200 with the deactivated resource | `/v1/salons/me/services/{id}` (`owner.py:507`), `/staff/{id}` (`owner.py:584`) |
| `POST …/deactivate` → 200 | Admin categories, subcategories, plans and salons |

All are valid HTTP. The cost is client inconsistency. Keep them (clients may already call them) and state one convention for new routes: DELETE → 204 for owned objects, a POST command when there are side effects.

**API-05: three current-actor profile endpoints and two `ProfileResponse` classes** (Medium, Proven)

- *Reads:* `GET /v1/auth/me` (`auth.py:58`), `GET /v1/profiles/me` (`profiles.py:22`), `GET /v1/customer/profile` (`customer.py:39`).
- *Updates:* `PATCH /v1/profiles/me` (`profiles.py:43`) and `PATCH /v1/customer/profile` (`customer.py:51`). Both call the same `CustomerUseCases.update_profile`, so their behaviour is identical. This was verified; there is no avatar-cleanup divergence.
- *Avatar:* signed-PUT flow (`profiles.py:70`) and direct multipart upload (`media.py:20`).
- *Schemas:* `schemas/auth.py` declares `role: Role` (an enum in OpenAPI), while `schemas/platform.py:82` declares `role: str`. Generated clients therefore get two incompatible types for the same profile.

*Recommendation:* keep every route. Mark `GET/PATCH /v1/profiles/me` as canonical in the API documents, and mark the `customer/profile` pair as aliases. Converge on one `ProfileResponse` by typing `schemas/platform.py:82` as `Role`; the JSON on the wire is unchanged (ENUM-01).

**API-06: similarly named but distinct commands** (Low, Proven)

`/bookings/{id}/cancel` (customer cancel), `/cancel/barber` (owner cancel with a reason code) and `/cancellation-requests` (customer asks the owner) are **different** commands, as `backend/docs/BOOKING_FLOW.md` documents. The same holds for `/bookings/{id}/payment` (owner records a manual payment), `/payments/confirm` (online gateway confirmation) and `/payment-confirmation-requests` (customer asks the owner to confirm). They are not duplicates. The singular `/payment` next to plural `/payments/*` is a naming trap only. Recommendation: a one-line description of each in the API documents. No route change.

**API-07: `GET /v1/salons` and `GET /v1/salons/nearby` overlap** (Low, Proven)

Both return `list[SalonSummaryResponse]` with almost the same filters (`customer.py:68`, `:133`). `nearby` additionally accepts `latitude`/`longitude` as aliases of `lat`/`lng` and fixes `surface="all"`. Keep both; document `nearby` as a convenience alias and stop adding filters to it separately.

**API-08: structural naming inconsistencies** (Low, Proven)

- `/v1/admin/*` is served from three modules (`router.py:29,36,47`), which makes admin routes harder to find and review.
- Singular and plural nouns are mixed for the same resource: `/v1/account/deletion` vs `/v1/admin/account-deletions`; `/v1/customer/profile` vs `/v1/profiles/me`.
- OpenAPI tags mix styles (`"account deletion"`, `"salon owner"` vs `"admin"`, `"salons"`).

None of these justifies renaming a route that clients may call. Apply one naming rule to new routes (plural collections, `/me` for the actor's own resource).

**API-11: OpenAPI does not describe some responses accurately** (Low, Proven)

- Four 204 `DELETE` routes omit `response_model` (`notifications.py:92`, `owner.py:369,432,758`), against `AGENTS.md` rule 16. The fix is an explicit `response_model=None`.
- `GET /v1/salons/me/qr` declares `QrCodeUrlResponse` (`owner.py:240`) but returns a raw `JSONResponse` with an extra `cached` key (`owner.py:281`) or an SVG `Response` (`owner.py:271`). The OpenAPI schema therefore omits the `cached` field and the SVG media type.
- `ReportRequest` and `ReportResponse` are defined inside `routes/reports.py:20,29` rather than under `schemas/`.
- Routes whose use case *requires* `Idempotency-Key` still declare the header optional (ERR-04), so generated clients treat it as optional and then receive 400.

### 6.1 Deprecation candidates (evidence from the three frontend repos)

Decision of 2026-10-22: mark duplicates now, remove them later. The three frontend repositories were scanned on 2026-10-22; the full evidence is in [frontend-api-usage-2026-10-22.md](frontend-api-usage-2026-10-22.md). C = customer app, O = owner app, W = website.

| Route | Callers | Recommendation |
|---|---|---|
| `GET /v1/profiles/me` | none | **Removal candidate.** No client reads it; the customer app reads `/v1/customer/profile` and every client reads `/v1/auth/me`. |
| `GET /v1/admin/catalog/languages` | none | **Removal candidate.** No client calls it. |
| `GET /v1/auth/me` | C, O, W | Keep: every client uses it |
| `GET` and `PATCH /v1/customer/profile`; multipart `POST /v1/customer/profile/avatar` | C | Keep: the customer app depends on them |
| `PATCH /v1/profiles/me`; signed `POST /v1/profiles/me/avatar-upload-url` | O | Keep: the owner app depends on them |
| `GET /v1/salons/nearby` | C, W | Keep: both clients use it |
| Admin `POST …/deactivate` and `PATCH` with `is_active` (categories, subcategories, plans) | W uses both | Keep both |
| `PUT /v1/salons/me/payout-account` | O | Keep; add the `PATCH` alias (API-01) before any change |

So the two profile pairs are not interchangeable duplicates today: each client uses a different pair. Converging them means first migrating one client, then removing the pair it no longer calls.

**Not duplicates, keep:** `/cancel`, `/cancel/barber` and `/cancellation-requests`; `/payment`, `/payments/confirm` and `/payment-confirmation-requests`; `/payout-account` (local record) and `/settlement-account` (provider).

**Removal procedure:** (1) confirm the route has no caller in the usage matrix; (2) add a deprecation note in OpenAPI and the client API documents; (3) watch server logs until the route has zero calls, because old app builds still installed on phones are not in the scan; (4) remove it in its own pull request.

**Related finding from the same scan:** the clients call 9 routes that do not exist in the backend. All of them come from the unbuilt `MARKETPLACE_CONTRACT.md` design (evidence for DOC-06). The one to fix first is the customer app's `GET /v1/salons/{id}/payment-options`: it fails with 404 on every booking-confirm screen and its parser expects a different shape from the `payment_options` field the backend ships. Online payment is intentionally off in that app today, so nothing is broken for users yet. See §3 of the usage document.

## 7. Enum and validation findings

### 7.1 What already exists (do not duplicate)

The domain layer already defines **27 `StrEnum` types** in `backend/app/domain/entities/`, including `Role`, `BookingStatus`, `BookingSource`, `PaymentStatus`, `PaymentPreference`, `ManualMethod`, `LedgerStatus`, `RefundStatus`, `PaymentState`, `WebhookStatus`, `OnboardingStatus`, `SubscriptionStatus`, `BillingInterval`, `BillingStatus`, `EntitlementState` and `PayoutStatus`. Several have Postgres enum counterparts (`booking_status` and `booking_source` are cast in SQL at `platform_repository.py:1523-1531` and `:1941-1949`).

The HTTP schemas already use `Literal` types correctly in many places: the booking status and source filters (`routes/bookings.py:102-104`), approval status (`schemas/admin.py:51`), cancellation reason codes (`schemas/platform.py:624-645`), `payment_mode` (`schemas/payment.py:33,37,122`), `payment_options` (`schemas/platform.py:101`), block type (`schemas/platform.py:773`) and the account-deletion stage and status (`schemas/account_deletion.py:9-10`).

**No finding below proposes a new enum.** Each one reuses an existing type.

Do not tighten `payment_status` beyond `unpaid|paid`: that is a recorded design rule (`backend/docs/PAYMENTS.md`, design rule 2), and the richer state is the derived `payment_state`.

### 7.2 Classification

**A. Must be an enum or strict finite value**

| Field | Location | Current state | Finding |
|---|---|---|---|
| Role (request side) | `require_role`, `deps.py:124` | `Role` enum | Correct |
| Role (response) | `schemas/auth.py:35` vs `schemas/platform.py:82` | `Role` vs plain `str` | ENUM-01 |
| Booking `status`, `source`, `payment_status`, `payment_preference`, `payment_state`, `payment_mode` (response) | `schemas/platform.py:505-522` | Plain `str`; the request side and filters use `Literal` | ENUM-01 |
| Action-request status and decision (response) | `schemas/platform.py:541-546`; `schemas/booking_actions.py:49,111` | Plain `str`, although `BookingActionStatus` and `BookingActionDecision` exist in the same module (`:11-12`) | ENUM-01 |
| Ledger `status`, `purpose`, `channel`, `settlement_model`; refund `status`; `onboarding_status` | `schemas/payment.py:21,65,106-114,160,177,206` | Plain `str`; the matching domain enums exist | ENUM-01 |
| Subscription `billing_interval`, `status`, `entitlement_state`, `event_type` | `schemas/subscription.py:24,98-99`; `schemas/subscription_billing.py:44,69,100,122` | Plain `str`; `Literal` forms exist in the same modules | ENUM-01 |
| `block_type` (response) | `schemas/platform.py:791` | Plain `str`; the request side is a `Literal` (`:773`) | ENUM-01 |
| Notification `type` | `schemas/platform.py:700` | Plain `str`. The backend emits a closed set: `approval_status`, `booking_cancelled`, `booking_cancelled_closure`, `payment_received` | ENUM-01. A `Literal` is safe only if older rows hold no other value; verify first. |
| Webhook `provider` path parameter | `webhooks.py:33` | Raw `str` | **Correct as is.** The resolver allow-lists enabled providers and returns 404 for anything else (`payments.py` use case, `ingest`). Providers are configuration-driven, so an enum would add nothing. |
| Payment instrument, manual method | `schemas/payment.py:110-111` | Plain `str` | ENUM-01 |

**B. Must remain free text** (correctly not enums)

Support subject and body (`schemas/support.py:11-24`, bounded at 1–200 and 1–5000), booking `notes`, rejection and cancellation explanations (`reason_text` max 500), salon and catalog `description`, address fields, search terms (`search` max 80 on public discovery), report `reason` and `details`. Two gaps exist within this class: ENUM-04 (missing `max_length`).

**C. Needs bounded validation, not an enum**

| Field | Location | Current constraint | Finding |
|---|---|---|---|
| Walk-in phone and OTP | `schemas/walkin.py:69-70` | **None** | ENUM-02 (and SEC-01) |
| Booking `customer_phone` | `schemas/platform.py:476` | **None** | ENUM-02 |
| Profile phone | `schemas/platform.py:44-74` | Custom Indian-mobile validator that normalises to `+91…` | Correct; reuse it |
| Payee KYC phone, PAN, IFSC, account number | `schemas/payment.py:222-227` | Patterns | Correct |
| UPI ID | `schemas/payment.py:228` vs `schemas/platform.py:849` | Two **different** regexes (`{2,64}@{2,32}` vs `{2,255}@{2,64}`) | ENUM-05 |
| Salon `timezone` | `schemas/platform.py:247` (owner), `schemas/admin.py:22,95` (admin) | **None**: any string | ENUM-03 |
| QR token | `walkin.py:29-39` | 32 lowercase hex, router-wide; failure → 404 `qr_not_found` | Correct |
| Idempotency key | 13 route headers | Unbounded at the header; 8–200 enforced in four downstream places | ERR-04 |
| Currency | `schemas/subscription.py:44,54` | `^[A-Z]{3}$` on plan input; the other occurrences are response-only | Acceptable |
| Language codes | `schemas/platform.py` (staff-service languages) | `list[str]`, no pattern | ENUM-04 |
| URLs (avatar, image, photo) | `schemas/platform.py:45,146,156,177` and others | Validated as hosted media references by the use case (`validate_media_reference`); `photo_url` on services is `HttpUrl` with max 2048 | Acceptable. Media publication is enforced server-side (`backend/docs/IMAGE_MEDIA.md`). |
| Device `token`, `platform`, `device_name` | `schemas/platform.py:725-727` | **None** | ENUM-04 |
| Path IDs | owner, bookings, payments, booking-actions, notifications routes | Raw `str` | ERR-01 |

### 7.3 Findings

**ENUM-01: response fields declared `str` where an existing enum applies** (Medium, Proven)

- *Field and location:* see class A above. The largest case is `BookingResponse` (`schemas/platform.py:505-546`).
- *Why:* OpenAPI publishes these fields as free strings, so generated clients cannot branch exhaustively on booking or payment state, and a new backend value appears without warning. Both client API documents tell clients to treat `/openapi.json` as the type source.
- *API compatibility:* **wire-identical.** The JSON values do not change; only the OpenAPI schema gains an `enum` list.
- *Database impact:* none, provided every stored value is in the enum. `booking_status` and `booking_source` are Postgres enums, so they are guaranteed. Text-backed columns (notification `type`, ledger fields) need a one-off `select distinct` check before tightening. Otherwise a legacy value would fail response validation and return 500.
- *Frontend impact:* regenerated clients get narrower types. That is beneficial, but it may surface compile errors where client code compares against misspelt strings.
- *Migration path:* type each response field with the existing domain `StrEnum` or schema `Literal`. Start with the fields backed by Postgres enums, then text fields after the distinct-value check. Add a contract test asserting the OpenAPI enum lists. No database migration.

**ENUM-02: phone inputs on the booking and walk-in paths are unvalidated** (Medium, Proven)

- *Field and location:* `WalkInVerifyPhoneRequest.phone` and `otp` (`schemas/walkin.py:69-70`); `BookingCreateRequest.customer_phone` (`schemas/platform.py:476`).
- *Why:* the walk-in phone is the OTP rate-limit key, so missing normalisation is what makes SEC-01 exploitable. The booking phone is stored and shown to the salon. The profile path already validates and normalises (`schemas/platform.py:46-74`).
- *API compatibility:* **normalise, do not reject**, so that clients sending any reasonable format keep working. Reject only values with fewer than 10 digits.
- *Database and frontend impact:* no migration; no client change.
- *Migration path:* extract the profile validator into a shared function, apply it to these fields, and key the OTP limiter on its output (SEC-01).

**ENUM-03: salon `timezone` accepts any string and is used in slot SQL** (Medium, Proven by code path)

- *Field and location:* `OwnerSalonUpdateRequest.timezone` (`schemas/platform.py:247`), `AdminCreateSalonRequest.timezone` and `AdminUpdateSalonRequest.timezone` (`schemas/admin.py:22,95`). No `CHECK` constraint exists on `salons.timezone` in the baseline or any migration. The slot logic evaluates `(p_date + v_open) at time zone v_tz` (`migrations/sql/0035_booking_checkout_safety.sql:244`).
- *Why:* a typo such as `Asia/Kolkatta`, saved by an owner in the workspace, makes Postgres raise `time zone … not recognized` on every availability and booking request for that salon. That surfaces as a generic 500 to all its customers, with nothing telling the owner why.
- *API compatibility:* rejecting an invalid IANA name with 422 only affects requests that would currently break the salon. Valid values are unaffected.
- *Database impact:* none for the application-level fix. Before deploying it, run `select id, timezone from salons where timezone not in (select name from pg_timezone_names)` to find already-broken rows. A `CHECK` constraint would need a migration and is optional.
- *Frontend impact:* none, if the owner app offers a picker. Free-text entry would start seeing 422.

**ENUM-04: free text and device fields without `max_length`** (Low, Proven)

`notes` (`schemas/platform.py:478`), image `caption` (`:157,268,277`), `title` (`:286,296`), service and staff `name`, `specialization` and `experience` (`:352-395`), blocked-slot `reason` (`:774`), admin `description` (`schemas/admin.py:37,116,138`), device `token`, `platform` and `device_name` (`schemas/platform.py:725-727`), and language codes. The global request-size limits bound the worst case, but a single field can still store several hundred kilobytes and then be rendered on every booking card. Add `max_length` values matching the client UI limits. This is non-breaking for normal input.

**ENUM-05: two different UPI ID patterns** (Low, Proven)

`schemas/payment.py:228` allows `{2,64}@{2,32}`; `schemas/platform.py:849` allows `{2,255}@{2,64}`. A UPI ID accepted on the owner payout account can be rejected on provider settlement registration. Pick one pattern and share it.

## 8. Authentication, authorization and privacy findings

### 8.1 What was verified as correct

These were traced to the SQL and are recorded as Informational (INFO-01 to INFO-05), so they need no further review.

- **Tenant isolation on owner by-ID operations.** Every sampled operation resolves the actor's salon via `get_owner_salon(actor_id)` and constrains the write with `salon_id = :salon_id`. A miss raises `NotFoundError`, so another tenant's object is indistinguishable from a missing one (404, not 403). This covers image update and delete (`platform_repository.py:546-558`, `:979-1006`), holiday delete (`:1059-1078`), staff update (`:1298-1326`), staff-service assignment and listing (`:1333-1400`), service update (`:1208-1236`) and blocked-slot delete (`:3664-3676`).
- **Booking access.** `get_booking` admits only the booking's customer, the salon owner or active staff (`platform_repository.py:1860-1870`). Status transitions lock the row `for update` under an owner-or-staff predicate, or a customer predicate for customer-only actions (`:1888-1920`). Action-request responses use the same scoping (`:2528-2562`). Manual payment recording locks the booking under an owner-or-staff predicate (`:2208-2240`).
- **Money routes.** Payment intent: if the actor is not the booking's customer, 404 (`use_cases/payments.py:315-317`). Refund: owner role, approved workspace, booking owner and payment-to-booking scoping, each failing as 403 or 404 (`:663-678`). The refund `amount` is the one client-supplied amount the design allows, bounded in SQL by the captured payment (`backend/docs/PAYMENTS.md:65-66`; schema `gt=0`).
- **Signed uploads.** The upload token is an HMAC over `{bucket, path, mime, expires}` with a 300-second expiry. The path is server-generated and contains the salon or actor namespace plus a fresh UUID (`infrastructure/r2/storage.py:121-123`, `:333-338`). A token cannot be retargeted at another tenant's object without the signing secret.
- **Webhooks.** An unknown or disabled provider gets 404 from the resolver. The body read is bounded even when `Content-Length` is missing or wrong (`webhooks.py:51-60`). The signature is verified over the raw bytes **before** parsing; a bad signature writes nothing. Replays are deduplicated by `(provider, event reference)` (`use_cases/payments.py`, `ingest`).
- **Owner self-promotion.** `grant_owner_role` updates only `role = 'customer'` rows to `owner` (`profile_repository.py:32-57`). Staff and super-admins are untouched, and the promoted owner receives a new, unapproved salon. No path reaches an existing salon.
- **Domain errors never leak SQL.** The `SQLAlchemyError` and catch-all handlers return fixed messages (`core/exceptions.py:373-401`), and validation details are sanitised (`:322-332`).

### 8.2 Findings

**SEC-01: the walk-in OTP send limit can be bypassed per phone number** (High, Proven)

- *Evidence:* `POST /v1/walkin/{qr_token}/verify-phone` (`walkin.py:134-165`) is unauthenticated. Its only gate is a valid QR token, which is printed on the salon wall. The send branch rate-limits on `f"rate:otp:{payload.phone}"` (`walkin.py:152`), using the **raw, unvalidated** phone string (`schemas/walkin.py:69`). `+919876543210`, `919876543210`, `+91 98765 43210` and `+91-98765-43210` therefore each get their own 5-per-minute bucket, while Supabase delivers to the same handset. The codebase already knows phone spellings vary: account erasure clears `rate:otp:{variant}` for several spellings via `phone_key_variants()` (`use_cases/account_erasure.py:49-57`, `:325-326`).
- *Compounding factors:* the limiter fails **open** when Redis is unavailable or unset (`infrastructure/cache/redis.py:270`, `:281`), and there is no per-IP or per-QR-token limit.
- *Why it matters:* SMS cost and harassment of a third party's phone (SMS pumping). The team already treats SMS-trigger abuse as a real risk: it deliberately did **not** add a salon-ID OTP endpoint for exactly this reason (`docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §4). The existing QR endpoint has the same exposure.
- *Not verified:* the Supabase project's own SMS rate limits bound the real cost; they are not visible from the repository.
- *Recommendation:* key the limiter on the normalised phone (ENUM-02). Add a secondary per-IP and per-QR-token limit. Back the OTP limiter with the existing Postgres `api_rate_limits` throttle, which fails closed (`support_repository.py:13-25`), instead of Redis. No migration, no client change.

**SEC-02: per-IP limits may collapse to one shared bucket behind a proxy** (High — deployment verification required; Concern)

- *Evidence:* the password-reset throttle keys on `request.client.host` (`auth.py:35`; 10 per hour per IP). Upload admission keys on `scope["client"][0]` (`infrastructure/media/admission.py:82-83`; 30 per minute per IP, per process). uvicorn is started without `--forwarded-allow-ips` (`Dockerfile:32`), and `FORWARDED_ALLOW_IPS` is set nowhere in the repository. uvicorn trusts `X-Forwarded-For` only from `127.0.0.1` by default.
- *Why it matters:* behind Cloud Run (a Mumbai staging service exists) or any load balancer, the client address seen is the proxy's. All users then share one bucket: **10 password-reset requests per hour for the whole platform**, and 30 upload grants per minute per instance. One abusive client can lock everyone out of password reset. On the GCP VM with Docker's default NAT, the real client IP is probably preserved, which is why this is a concern rather than proven.
- *How to verify:* on isolated staging, compare safe, redacted request metadata: the peer address uvicorn sees, and the `X-Forwarded-For` chain. Do not log full headers, tokens or user data.
- *Recommendation (deployment owner; not an immediate code change):*
  - uvicorn honours `X-Forwarded-For` only when the connecting peer is in the configured trusted-proxy list (`--forwarded-allow-ips` / `FORWARDED_ALLOW_IPS`).
  - A wrong trust setting is a security risk. **Do not set it blindly, and never to `*`.** With a too-wide setting, any caller can send a forged `X-Forwarded-For` header and pick the client IP the application sees. That defeats every IP-based limit, including the password-reset and upload limits.
  - First verify the actual Cloud Run or proxy request path and the trusted peer addresses on isolated staging (see *How to verify*). Then configure the smallest trusted proxy or network scope that covers only the real proxy.
  - If the topology cannot give a safe trusted-peer boundary, keep application IP limiting conservative and move the abuse limit to Cloud Armor or platform-level rate limiting.
  - Record the verified result in `backend/docs/DOCKER_DEPLOYMENT.md`.

**SEC-03: OTP verification has no application-level attempt limit** (Medium, Concern)

The rate limit applies only when `otp` is absent (`walkin.py:151`). The verify branch (`:157-163`) passes any number of guesses straight to Supabase. Whether brute-forcing a 6-digit code is practical depends on Supabase's own verify throttling, which was not verified. Apply a per-phone attempt limit (for example 5 per 10 minutes) on the normalised phone, using the same mechanism as SEC-01.

**SEC-04: `get_booking` has an unscoped branch for a null actor** (Low, Proven)

The access predicate begins with `cast(:actor_id as uuid) is null or …` (`platform_repository.py:1862`), so a call with `actor_id=None` reads any booking. The only such caller today is the post-creation read-back (`:1566`), which passes the creating actor, so this cannot be reached from a request. It is a latent footgun. Remove the null branch and give internal callers an explicit, separately named method.

**SEC-05: `GET /v1/admin/catalog/languages` is open to any signed-in user** (Low, Proven)

`admin.py:382-393` uses `get_current_actor` rather than `require_role`, and its docstring states this is intentional reference data. There is no leak. The `/admin` path and tag make the route look unprotected to reviewers and audit tools. Document it as public reference data, or alias it under `/v1/catalog/languages`; do not remove the existing path.

### 8.3 Not re-raised (recorded decisions)

The following are intentional and documented. They are listed in §16 and are not findings: the unauthenticated webhook route; the deletion-status route authenticated by `X-Status-Token`; QR tokens without expiry or a rotation endpoint; no salon-ID OTP endpoint; plaintext payout bank numbers (a known recorded gap, `backend/docs/PAYMENT_DECISIONS.md` gap 9); single-operator `aal2` financial repair without two-person approval (`decisions.md` #6).

## 9. Error, status-code and idempotency findings

### 9.1 What holds

One envelope is used everywhere (`core/exceptions.py:276-285`); 39 typed codes are mapped once (`:296`); no route raises a raw `HTTPException`; and 500 responses carry fixed messages. These are confirmed correct (INFO-07). The `StarletteHTTPException` handler adds a top-level `detail` key for backwards compatibility (`:361-365`). That is a deliberate variant and should be left alone.

### 9.2 Findings

**ERR-02: booking creation turns every failure into a 409, including outages** (High, Proven)

- *Evidence:* `create_booking` wraps the whole operation in `except Exception` (`platform_repository.py:1571`) and classifies the error by **substring of the message** (`:1576-1590`). Any message containing `"slot"` or `"available"` becomes 409 `slot_unavailable`. Anything unrecognised becomes 409 `conflict`. A lost connection, a pool timeout, a statement timeout, an invalid salon timezone (ENUM-03) or a programming error is therefore reported to the client as a booking conflict. (Corrected 2026-10-22: manual payment recording at `:2195-2206` does **not** share this defect. It maps only the overcollection error and re-raises everything else.)
- *Why it matters:* the published contract guarantees `slot_unavailable` is a "real slot conflict only" and tells clients to refresh availability and pick another slot (`docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §5). During a database incident, customers are sent round that loop instead of being told to retry later. Because no 5xx is returned, the platform's most important write path produces no server-error signal in Sentry or in the timing metrics.
- *Recommendation (implemented 2026-10-22, uncommitted; see below):* the booking SQL rejects a request on purpose with two error codes:
  - `P0001`: plain `raise exception '…'` in `create_booking`, including the overlap error, which it catches and re-raises with the text "That slot was just taken" (`migrations/sql/001_supabase_schema.sql:950`, `:985-986`);
  - `23514`: the `guard_booking_checkout` trigger from migration 0035, for `salon_not_accepting_bookings`, `pay_at_salon_temporarily_blocked` and `pay_at_salon_daily_limit` (`migrations/sql/0035_booking_checkout_safety.sql:83`, `:99`, `:104`).

  The error code alone cannot tell these business errors apart, so the message mapping stays, but **only** for those two codes. Every other exception is re-raised, and the global `SQLAlchemyError` handler returns 500. Real business errors keep exactly their current codes and messages. Raising explicit, distinct `ERRCODE` values from the SQL would remove the message matching entirely, but needs a reviewed migration and can come later.
- *Status:* fixed in the working tree, not committed. `_is_business_error` in `platform_repository.py` gates the mapping. Covered by `tests/unit/test_booking_error_classification.py`, whose cases include outages, timeouts, a unique violation, and the three 23514 trigger errors. The full suite passes (1,239 passed, 90 skipped, 0 failed). An independent review caught the 23514 case before it shipped.
- *Tests:* the real-Postgres booking-contract suite (`tests/integration/test_booking_contract_sql.py`, which runs in CI) should assert that an overlap returns `slot_unavailable` and that a forced connection error returns 500.

**ERR-01: malformed path IDs return 500 "Please try again"** (Medium, Proven by code path)

- *Evidence:* owner, booking, payment, booking-action and notification routes take path IDs as raw `str` (Appendix, §17). The only application-level UUID check in the codebase covers the `ids` filter on salon listing (`platform_repository.py:232`). A non-UUID value is therefore bound straight into SQL against a `uuid` column. asyncpg rejects it with a `DataError`, which the global `SQLAlchemyError` handler turns into 500 `internal_error`, *"A database error occurred. Please try again."* (`core/exceptions.py:373-386`). Booking creation is the exception: there, ERR-02 turns it into a 409 instead.
- *Why it matters:* a permanent client error is reported as a server error, pollutes 5xx alerting, and the message invites the client to retry a request that can never succeed. The same module is inconsistent with itself: `admin.py:126,137,152,166` type `salon_id` as `UUID`, and `admin.py:181,202` do not.
- *Not verified:* executing a request; this was derived from the code path and asyncpg's documented codec behaviour.
- *Recommendation:* type path IDs as `UUID` in the route signatures. FastAPI then returns 422 `validation_error` through the shared envelope. Valid clients are unaffected; only malformed IDs change, from 500 to 422.

**ERR-04: `Idempotency-Key` is documented as required on money POSTs but is optional on booking-family operations** (Medium, Proven)

- *Evidence:* `backend/docs/AUTHORIZATION.md` states that every money POST needs `Idempotency-Key`.
  - Online payment and subscription-checkout use cases do require it (`use_cases/payments.py:226-233`, `use_cases/subscription_billing.py:233-236`).
  - Booking-family operations skip idempotency entirely when the header is absent: `begin_booking_operation` returns `None` (`platform_repository.py:1593-1595`). This covers booking create, QR booking create, check-in, no-show, complete, and **manual payment recording** (`POST /v1/bookings/{id}/payment`).
  - All 13 routes declare the header as optional in OpenAPI (`Header(default=None, …)`), including the ones whose use case rejects a missing key with 400.
- *Verified non-impact:* a retried manual payment **cannot** double-count. The booking row is locked `for update`, and a second attempt hits `payment_status == 'paid'` → 409 *"Payment has already been recorded"* (`platform_repository.py:2208-2245`), behind a database overcollection guard. A retried booking creation hits the overlap constraint. The real effect is that a client retrying after a lost response gets a 409 error instead of the replayed success.
- *Recommendation:* (a) mark the header `required` in OpenAPI on the routes whose use case already requires it. Wire behaviour is unchanged; only the documentation becomes accurate. (b) Correct `AUTHORIZATION.md` to say what the code does today. (c) Separately decide whether to require the key on booking-family routes. Enforcing it is breaking for clients that may not send it, so do it only after server logs show every client sends it.

**ERR-03: two error codes for "idempotency key reused"** (Low, Proven)

Payments return 409 `idempotency_key_reuse` (`core/exceptions.py:247`); bookings return 422 `idempotency_key_reused` (`:130`). Both are published (`docs/Customer-App-Backend-API-Document.md`; `docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §5), so clients must handle both. Do not change either. Document them side by side and use one code for any new route.

### 9.3 Retry behaviour summary

| Situation | Response today | Safe for the client to retry? |
|---|---|---|
| Online payment POST without key | 400 `idempotency_key_required` | Yes, with a key |
| Same key, different body | 409 `idempotency_key_reuse` / 422 `idempotency_key_reused` | No (correct) |
| Same key while the first call is in flight | 409 `idempotency_in_progress` | Yes, after a delay (correct) |
| Booking or payment-record retry without key after success | 409 | It says "failed", but the operation succeeded (ERR-04) |
| Malformed path ID | 500 "Please try again" | No, but the message says yes (ERR-01) |
| Database outage during booking create | 409 `slot_unavailable` or `conflict` | Unclear; the client is told to choose another slot (ERR-02) |

## 10. Data, transaction and concurrency findings

### 10.1 What holds (verified)

- **Double-booking is prevented by the database, not by Python.** `bookings_no_overlap` is a GiST exclusion constraint over `(staff_id, tstzrange(start_datetime, end_datetime))`. It was originally scoped to `pending`/`confirmed` (`migrations/sql/001_supabase_schema.sql:526-530`), and migration 0035 extended it to `checked_in` (`migrations/sql/0035_booking_checkout_safety.sql:58-62`). The same migration adds a database trigger that enforces the legal status transitions (`:109-110`) and append-only audit tables.
- **`AGENTS.md` rules 22–25 are met.** `create_booking()` has a single call site (`platform_repository.py:1523-1531`); availability comes only from `get_available_slots()` (`:1453`, `:1635`); there is no Python insert into or delete from `bookings` or `booking_services`. Direct `UPDATE bookings` statements are post-creation state changes, each guarded by a status predicate and an access predicate (`:1941-1949`, `:2045-2050`, `:2092-2112`, `:2627-2638`, `:2965-2977`).
- **Hard delete is confined to verified erasure** (`account_deletion_repository.py:799-845`) and to idempotency bookkeeping. Platform data uses `is_active`, which satisfies `AGENTS.md` rule 26.
- **The idempotency ledger is actor-isolated.** It has a unique key on `(actor_id, scope, idempotency_key)` with `on conflict do nothing`, plus fingerprint comparison (`payment_repository.py:58-112`). The QR booking scope also binds the salon and a hash of the token (`use_cases/walkin.py:65`).
- **CPU-heavy image processing runs off the event loop**, in a bounded executor (`infrastructure/media/pillow_processor.py:72-75`).

### 10.2 Findings

**DATA-01: SQL column names are built from dictionary keys without an allow-list** (Medium, Proven, not currently exploitable)

- *Evidence:* 10 statements in 9 methods build column names with `f"{key} = :{key}"` (or an `INSERT` column list) from the keys of the incoming dict: `platform_repository.py:164` (profile; every key, no filter), `:860` (owner salon), `:903` and `:924` (onboarding insert and update), `:991` (image), `:1309` (staff), `:3229` (admin salon), `:3363` (category), `:3460` (subcategory), and `subscription_repository.py:58` (plan). The local variable is often named `allowed`, but it only drops `None` values; it is not an allow-list. The helper `_sql_assignment` is documented as *"Return a safe assignment fragment for a writable column"* (`:136-139`), but it does not check that the key is a writable column. The one guarded site is `update_owner_service` (`:1214-1220`), which goes through `_service_write_values`.
- *Why it is safe today:* every caller passes `payload.model_dump(...)` of a Pydantic model, and no schema uses `extra="allow"` (verified across `app/`). The keys are therefore always declared field names.
- *Why it matters:* the safety depends on a convention the repository does not enforce. One future caller passing a dict that contains user-controlled keys (merged JSON, query parameters, a webhook payload) would allow SQL injection through an identifier. The lexical guard test `tests/test_sql_bind_params.py` scans only `platform_repository.py`, and it does not detect this pattern.
- *Recommendation:* reuse the pattern that already exists in the same file. `_service_write_values` (`platform_repository.py:1199-1206`) intersects the keys with a constant writable set and raises `ValidationError("Unsupported service fields")` for anything else. Apply a constant set per update method, and extend the guard test to all repositories. No migration, no client impact.

**DATA-02: unbounded list endpoints** (Medium, Proven)

- `GET /v1/bookings`: the query parameter is `limit: Query(None, ge=1, le=200)` (`routes/bookings.py`), and the repository adds `LIMIT` only when `limit` is not `None` (`platform_repository.py:1690-1693`). An owner client that omits `limit` receives every booking the salon has ever had. Each row carries five correlated sub-selects for the latest action requests (`:1717-1738`). A salon taking 30 bookings a day accumulates about 11,000 rows a year.
- `GET /v1/notifications`: no pagination at all (`list_notifications`, ordered by `created_at desc` with no limit).
- Owner lists of services, staff, holidays and blocks have no pagination, but per-salon cardinality is small and bounded. Not a finding.
- *Recommendation:* apply a server default when `limit` is omitted. The wire format is a bare JSON array, so add pagination metadata as response headers (`X-Total-Count`, or `Link`) rather than changing the shape. Use a generous default (the existing maximum of 200) so current clients keep working, and coordinate with the owner app before lowering it. Add an optional `limit`/`offset` to notifications with the same default.

**PERF-01: any authenticated mutation flushes the whole public read cache** (Medium; mechanism Proven, impact a Concern)

- *Evidence:* `MeasuredAsyncSession.commit()` rotates one global read-model epoch after **every** commit (`infrastructure/db/session.py:45-50` → `infrastructure/cache/redis.py:66-91`). `get_authenticated_session` commits the rate-limit row on every POST, PUT, PATCH and DELETE before the route runs (`deps.py:113-120`). That includes read-only computations sent as POST: `POST /v1/bookings/quote`, which has a raised budget of 120 per minute precisely because it is frequent, and `POST /v1/salons/me/closures/preview`.
- *Effect:* any signed-in user requesting a quote anywhere invalidates every salon's cached detail, services and staff, the catalog, and every QR page. Each cache **hit** also costs one database round trip for the snapshot check (`redis.py:148-165`). Under real write traffic, the cache probably returns few hits while still adding Redis and database round trips.
- *Correctness:* unaffected. The design errs toward freshness, as `backend/docs/ARCHITECTURE.md` intends.
- *How to verify:* add a hit/miss counter to the timing metrics and read it on staging under a booking load.
- *Recommendation (post-launch, after measurement):* run the throttle write on a connection that does not use `MeasuredAsyncSession`, so rate-limit bookkeeping does not rotate the read-model epoch, and exempt pure computations (quote, preview) from the mutation throttle family. Do not weaken the epoch design itself.

**PERF-02: QR images are rendered on the event loop by an unauthenticated route** (Medium, Concern)

`GET /v1/walkin/{qr_token}/qr` calls `make_qr_png` or `make_qr_svg` synchronously inside the async handler (`walkin.py:119-126`), with `scale` up to 30. The route has no rate limit and sends no `Cache-Control`, so every scan or page refresh re-renders the image. Every render blocks all other requests on that worker. The owner QR route does the same for SVG (`owner.py:271`). The token's image never changes, so the fix is cheap: render through `run_in_threadpool` and send `Cache-Control: public, max-age=86400`. *How to verify:* time one PNG render at scale 30.

**DATA-03: `api_rate_limits` is never pruned** (Low, Proven)

The throttle upserts one row per bucket (`support_repository.py:13-25`). Buckets include `reset:email:<address>` for any address a caller submits, and nothing deletes old rows. Growth is slow but unbounded. Add a periodic delete of rows whose window expired more than a day ago to an existing worker.

**DATA-04: commits happen at three layers** (Low, Proven)

There are commits in a route (`routes/auth.py`), in use cases (`use_cases/payments.py`, 12) and in repositories (`platform_repository.py`, 48), and the auth dependency itself commits (`deps.py:119`). Nothing found here causes a defect today; `payment_repository.py:38-41` correctly re-arms the audit actor after each commit. But it makes transaction boundaries hard to review: a multi-step operation can only be judged atomic by reading every callee. Adopt "the use case owns the commit" for **new** code. Existing code is covered by the deferred refactor (`decisions.md` #7).

### 10.3 Not verified

The concurrency claims above come from schema and SQL, not from concurrent execution in this audit. Real-Postgres evidence for booking overlap and customer-isolated idempotency exists from 2026-10-21 (`docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §7) and runs in CI (§12).

## 11. Architecture and maintainability findings

### 11.1 Scope note

`docs/agent-memory/shared/decisions.md` #7 (2026-10-21) already decided several things in this area. Splitting `PlatformRepository` (3,871 lines) and `OwnerUseCases` is **deferred** to a separately approved refactor. `application/ports/email_gateway.py` stays as a future port. `http_exception_handler` stays. No change is to be driven by the dependency graph. This audit does not re-raise any of those decisions. The findings below are proven by reading imports and call sites, not inferred from the graph. Where a finding belongs inside the deferred refactor, it says so.

### 11.2 What holds

- **Domain purity (`AGENTS.md` rule 12):** no module in `app/domain/` imports FastAPI, SQLAlchemy, Pydantic, Supabase, Firebase, httpx, `app.api` or `app.infrastructure` (verified with grep).
- **One error mapping (rule 17):** see §9.1.
- **Authorization in use cases (rule 13):** it holds for the sampled routes (§8.1), with the reservation noted in ARCH-01.
- **The webhook route's conditional mount** (`router.py:50-54`) changes the API surface by configuration. That is documented (`backend/docs/AUTHORIZATION.md`) and asserted by `tests/test_api_contract.py:28`. It is not a hidden flag.

### 11.3 Findings

**ARCH-01: use cases import concrete infrastructure classes** (Low, Proven)

`application` should depend only on ports, but 8 use-case modules import infrastructure directly:

- `PlatformRepository` (`use_cases/platform.py:26`, `admin.py:15`, `walkin.py:9`)
- `PaymentRepository` and the provider resolvers (`payments.py:64-69`)
- the subscription repositories and resolvers (`subscription.py:9`, `subscription_billing.py:51-54`)
- `outbox_worker` (`booking_actions.py:88,126`; `platform.py:1080,1145`)

Several of these have no port at all. Many repository methods also embed access predicates in SQL (for example the owner-or-staff checks in `platform_repository.py:1908-1909` and `:2092-2112`). That is effective, but it means policy is split between the use case and the repository. **Recommendation:** fold this into the already-deferred refactor as one of its acceptance criteria. Do not do it as standalone work now.

**ARCH-02: cache invalidation in route handlers is redundant and inconsistent** (Low, Proven)

Owner and admin route handlers call `cache.delete` and `delete_prefix` after use-case calls (`routes/owner.py:99,139-140,478-480,501-503,523-525,559,580,600`; `routes/admin.py:255,277-278,297-298,337,359,378`). Because every commit already rotates the global epoch (§10, PERF-01), these calls are not needed for correctness. They are also inconsistent: service writes flush every `walkin:qr:` key, while staff writes do not, even though the walk-in page lists staff (`schemas/walkin.py:59`). A reviewer will read this as a missing-invalidation bug. It is not one; this audit checked. **Recommendation:** add a one-line comment at each site stating that the epoch handles correctness and the delete only drops payloads early, or remove the calls once PERF-01 is settled. Either way, keep cache policy out of route handlers in new code.

**ARCH-03: inconsistent dependency wiring that defeats test overrides** (Low, Proven)

Most routes build use cases through small `_use_cases(session)` helpers. Three places bypass FastAPI dependency injection, so `app.dependency_overrides` cannot replace the collaborator in tests:

- `customer.py:36` calls `get_storage_gateway()` directly.
- `walkin.py:156` constructs `SupabaseAuthGateway(settings)` inline.
- `auth.py:33` opens its own `AsyncSessionLocal()` inside the forgot-password handler. That one is deliberate, so the throttle commits even if the provider call fails, but it is invisible to session overrides.

The walk-in OTP flow also lives entirely in the route, with no use case. **Recommendation:** route these through `Depends(...)` (`deps.py` already provides `get_auth_gateway`), and move OTP send and verify, with the SEC-01 and SEC-03 limits, into a use case.

### 11.4 Documentation drift

None of these is an existing decision. They are drift found while cross-checking.

| ID | Severity | Drift | Evidence |
|---|---|---|---|
| DOC-01 | Low | `CLAUDE.md` tells agents to use `graphify-out/wiki/index.md`, which does not exist; the graph is stale (built from `54c09ff`, while `HEAD` is `828d73b`) | `graphify-out/GRAPH_REPORT.md` header |
| DOC-02 | Low | Broken link to `cloud-run-cold-start-remediation-plan-2026-10-20.md` | `backend/docs/verification/cloud-run-startup-profile-2026-10-20.md:3` |
| DOC-03 | Medium | `docs/README.md`, the entry point mandated by `AGENTS.md` rule 2, omits most binding documents: `MARKETPLACE_CONTRACT.md`, `SUBSCRIPTIONS.md`, `PAYMENT_DECISIONS.md`, `ACCOUNT_DELETION.md`, `IMAGE_MEDIA.md`, `IMAGE_VARIANTS.md`, backend `SALON_APPROVAL.md`, and the `verification/` and `migrations/` trees | `docs/README.md` |
| DOC-04 | Low | Two live files named `SALON_APPROVAL.md` on different subjects (`docs/` covers discovery ranking and has no H1; `backend/docs/` is the approval contract) | both files |
| DOC-05 | Low | Verification commands disagree across four documents: `AGENTS.md` rule 49 uses `./.venv/bin/python` (fails on the Windows hosts in use); `backend/docs/SALON_APPROVAL.md` uses `./.venv/Scripts/python.exe`; `shared/gotchas.md` #14 uses `backend/.venv/Scripts/python.exe`; `backend/docs/ACCOUNT_DELETION.md` uses `./.env1/Scripts/python` (an apparent typo) | those files |
| DOC-06 | Medium | `backend/docs/MARKETPLACE_CONTRACT.md` reads as a wire contract, but almost none of it is implemented (only `access-state` exists, `subscription_billing.py:91`). Its §3 `GET /v1/salons/{id}/payment-options` conflicts with the shipped per-response `payment_options` block (`schemas/platform.py:101-119`; `docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §2). A client team could implement against routes that do not exist. | file header and §3 |
| DOC-07 | Low | `CLAUDE.md` says four clients; `docs/FRONTEND_INTEGRATION_PROMPTS.md:7-9` says three repositories (the website holds the customer flow, QR booking, owner workspace and super-admin) | those files |
| DOC-08 | Low | `backend/docs/PAYMENTS.md` and `IMAGE_MEDIA.md` each declare themselves partly superseded without marking which passages still hold | file headers |
| DOC-09 | (counted under ERR-04) | `AUTHORIZATION.md` says every money POST requires `Idempotency-Key`; the code requires it only on online-payment routes (ERR-04) | §9 |
| DOC-10 | Low | Repository hygiene: `.gitignore` is left in an unresolved merge state (`git status` shows `UU`, with no conflict markers in the content); a stray tracked `salonsalon-backend/.codegraph/` directory sits at the repository root; this report's requested file name uses SCREAMING_SNAKE, while the other 28 reviews in this directory use `kebab-case-YYYY-MM-DD.md` | `git status`, `git ls-files` |
| DOC-11 | Informational | The baseline `migrations/sql/001_supabase_schema.sql:526-530` still shows the original overlap predicate; the effective definition is in migration 0035. Readers who treat the baseline as current (rule 20) should know later migrations amend it. | §10.1 |

## 12. Test coverage and verification gaps

Tests were inspected, not run. The latest recorded run is 1,221 passed, 90 skipped and 0 failed, on 2026-10-21 (`docs/agent-memory/SESSIONS.md`). The three known Windows CRLF failures are expected sealed evidence (`shared/gotchas.md` #13) and are not a finding.

### 12.1 Shape of the suite

- 93 test files: 65 under `tests/unit/`, 13 under `tests/integration/`, and 4 at the top level (API contract, auth, health, and the SQL bind-parameter guard).
- Unit tests mock `PlatformRepository` outright (`tests/conftest.py`; stated in `tests/test_sql_bind_params.py:2-7`). Raw-SQL behaviour is therefore exercised only by the integration suites.
- Every integration suite is skipped unless an environment variable points it at a disposable database.

### 12.2 Findings

**TEST-01: several real-Postgres suites never run in CI, including account erasure** (High, Proven)

- *Evidence:* `.github/workflows/backend.yml` starts a Postgres 18 service but sets only `MIGRATION_TEST_DB` (`backend.yml:35-49`). Running in CI: the migration chain, payment ledger, booking contract, checkout safety and subscription-billing suites. **Never run in CI:**

| Suite | Gate variable | What it protects |
|---|---|---|
| `integration/test_account_deletion_sql.py` | `ACCOUNT_DELETION_TEST_DB` | The only sanctioned hard-delete path, and the "no PII remains" assertions in `backend/docs/ACCOUNT_DELETION.md` |
| `integration/test_media_reference_locking.py` | `MEDIA_TEST_DB` | Media reference guards from migration 0020 |
| `integration/test_salon_approval_migration.py` | `SALON_APPROVAL_DB_TESTS` | The approval gate behind public visibility |
| `integration/test_website_migration.py`, `test_service_presentation_migration.py` | `WEBSITE_TEST_DB`, `SERVICE_PRESENTATION_TEST_DB` | Website and service-presentation migrations |
| `integration/test_redis_recovery_sql.py` | `RECOVERY_TEST_DB`, `RECOVERY_TEST_REDIS` | Cross-process cache coherence (4 of its 20 tests also need Playwright) |

- *Why it matters:* a regression in erasure SQL, which handles PII deletion and refunds, can merge with a green CI.
- *Not verified:* whether these suites are excluded on purpose (for example because they need a migration head that CI cannot reach; see the 0038–0040 hold in `shared/gotchas.md`). No recorded decision says so.
- *Recommendation:* point the other gate variables at the existing CI service. First confirm each suite isolates itself in its own disposable database, as the checkout-safety suite does (`test_checkout_safety_sql.py:3`). Where a suite truly cannot run in CI, record that as a decision.

**TEST-02: high-risk routes and mechanisms without route-level tests** (Medium, Proven)

There is no test file for these routes or modules:

- `routes/webhooks.py` (provider flows are tested below the route)
- `routes/reports.py`, `routes/support.py`, `routes/profiles.py`, `routes/notifications.py`
- the blanket mutation throttle in `deps.py:113-120`, and `api_rate_limits`

The error-handler layer is barely covered. `tests/test_api_contract.py` has two tests, and only one checks the envelope (validation errors). Nothing asserts the `HTTPException` envelope, the `SQLAlchemyError` 500 shape, the CORS headers on the catch-all, or the code catalogue in `core/exceptions.py`. **Add these alongside the fixes they protect:**

- a malformed path ID returns 422 (ERR-01)
- an outage during booking creation returns 500 (ERR-02)
- phone spellings share one OTP bucket (SEC-01)
- an invalid timezone returns 422 (ENUM-03)
- an unknown repository key raises `ValidationError` (DATA-01)

**TEST-03: owner self-promotion is untested** (Medium, Proven)

No test references `grant_owner_role` (`profile_repository.py:32-57`) or the role-predicate guarantee that staff and super-admins are never rewritten. This is the system's only role-escalation path, and its safety rests on one SQL predicate. Add a real-Postgres test asserting that customer → owner works, and that staff, super-admin and inactive profiles are unchanged.

### 12.3 Strong coverage worth noting

- Booking overlap and customer-isolated idempotency (`integration/test_booking_contract_sql.py`, in CI)
- Payment ledger, checkout safety and subscription billing SQL (in CI)
- Admin MFA (`unit/test_admin_mfa.py`)
- Approval gating
- Media admission over HTTP
- Public discovery and the QR contract
- Account-deletion API and use cases (unit)

### 12.4 OpenAPI accuracy

`tests/test_api_contract.py:8` asserts that 17 paths exist; it does not assert schemas. Known inaccuracies are listed in API-11 and ERR-04. A snapshot test of `/openapi.json` would make every contract change visible in review. That matters because the client API documents tell clients to treat `/openapi.json` as the type source.

## 13. Findings table

Effort: **S** is under half a day, **M** is one to three days, **L** is more than three days. Status gives the evidence label (Proven or Concern) and the recommendation class. "Frontend impact" assumes a client may already call the route.

| ID | Severity | Area | File/route | Finding | Why it matters | Recommendation | Migration needed | Frontend impact | Effort | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| SEC-01 | High | Security / rate limit | `POST /v1/walkin/{qr_token}/verify-phone`; `walkin.py:150-154`; `schemas/walkin.py:69` | OTP send limit keyed on the raw phone string; spelling variants bypass it; Redis limiter fails open; no per-IP or per-QR limit | SMS cost and harassment via a public, printed QR token | Key on the normalised phone; add per-IP and per-QR limits; use the fail-closed Postgres throttle | No | None | S | Proven · Fix before production |
| SEC-02 | High | Security / rate limit | `auth.py:35`; `media/admission.py:82-83`; `Dockerfile:32` | Per-IP limits use the peer address; uvicorn does not trust forwarded headers; `FORWARDED_ALLOW_IPS` unset | Behind a proxy, one shared bucket: 10 password resets per hour platform-wide | Deployment owner verifies the proxy path and trusted peers on isolated staging, then trusts only the smallest real proxy scope (never `*`); otherwise use Cloud Armor or platform rate limiting | No | None | S | Concern · Deployment verification required (deployment owner) |
| ERR-02 | High | Errors / reliability | `POST /v1/bookings`; `platform_repository.py:1571-1590` | `except Exception` plus message-substring matching turns outages, timeouts and bad data into 409 `slot_unavailable`/`conflict` | Breaks the published "real slot conflict only" guarantee; hides 5xx on the main write path | Map messages only for business error codes `P0001` and `23514`; re-raise everything else | No | Clients see 500 instead of 409 during real failures | M | Proven · Fixed in working tree (uncommitted) |
| TEST-01 | High | Tests / CI | `.github/workflows/backend.yml:35-49` | CI sets only `MIGRATION_TEST_DB`; erasure, media-locking, approval, website, service-presentation and Redis-recovery suites never run | PII-erasure SQL regressions can merge with a green CI | Set the other gate variables against the CI service, or record why not | No | None | S | Proven · Fix before production |
| SEC-03 | Medium | Security | `walkin.py:157-163` | OTP verification has no app-level attempt limit | Brute-force resistance depends on unverified Supabase settings | Per-phone attempt limit on the normalised phone | No | None | S | Concern · Fix before production |
| API-01 | Medium | HTTP method | `PUT /v1/salons/me/payout-account`; `owner.py:166` | PUT with documented merge (PATCH) semantics | A PUT-following client keeps a payout destination it meant to remove | Add PATCH alias on the same handler; deprecate PUT; never switch PUT to replacement | No | Optional switch to PATCH | S | Proven · Fix before production |
| API-02 | Medium | Contract | PATCH endpoints; `platform_repository.py:852-860,985-991,1303-1309,3223-3229,3355-3363,3456-3460`; `subscription_repository.py:57-58` | Explicit `null` is ignored, clears, or returns 422 depending on endpoint; profile `full_name` can be nulled | "Clear" actions silently do nothing and still return 200 | Document per endpoint now; adopt the `_service_write_values` per-field policy where clearing is needed | No | Documentation; later, clear actions start working | S (docs) / M | Proven · Fix before frontend real API wiring (docs) |
| API-05 | Medium | Duplication | `auth.py:58`, `profiles.py:22,43,70`, `customer.py:39,51`, `media.py:20`; `schemas/platform.py:82` | Three profile reads, two updates, two avatar paths; two `ProfileResponse` classes (`Role` vs `str`) | Generated clients get two types for one resource | Mark `/v1/profiles/me` canonical; unify the response type | No | Regenerated types converge | S | Proven · Safe post-launch improvement |
| ENUM-01 | Medium | Enums | `schemas/platform.py:82,505-546,700,791`; `schemas/payment.py`; `schemas/subscription*.py` | Response fields typed `str` although domain enums and `Literal`s exist | OpenAPI clients cannot branch exhaustively on booking or payment state | Type with existing enums after a `select distinct` check on text columns | No | Narrower generated types; same JSON | M | Proven · Fix before production |
| ENUM-02 | Medium | Validation | `schemas/walkin.py:69-70`; `schemas/platform.py:476` | Walk-in phone, OTP and booking `customer_phone` unvalidated | Enables SEC-01; inconsistent stored phone data | Normalise with the existing profile validator (do not reject) | No | None | S | Proven · Fix before production |
| ENUM-03 | Medium | Validation | `PATCH /v1/salons/me`, admin salon create and update; `schemas/platform.py:247`; `schemas/admin.py:22,95`; `0035…sql:244` | Salon `timezone` accepts any string and is used in slot SQL | A typo makes availability and booking return errors for every customer of that salon | Validate against IANA names; pre-check existing rows | No (optional CHECK later) | Free-text timezone entry would see 422 | S | Proven · Fix before production |
| ERR-01 | Medium | Status codes | Raw-`str` path IDs in owner, bookings, payments, booking-actions, notifications routes | Malformed ID returns 500 "Please try again" | Client errors counted as server errors; message invites futile retries | Type path parameters as `UUID` (gives 422) | No | Malformed IDs get 422 instead of 500 | S | Proven · Fix before production |
| ERR-04 | Medium | Idempotency | 13 `Idempotency-Key` routes; `platform_repository.py:1593-1595`; `AUTHORIZATION.md` | Key required on online money routes but optional on booking-family routes, including manual payment record; OpenAPI marks it optional everywhere | A retry after success returns 409 "failed" (no double count, verified); docs and OpenAPI are wrong | Mark required in OpenAPI where enforced; correct the docs; enforce on booking routes only after logs show every client sends it | No | Documentation now; enforcement later | S | Proven · Fix before frontend real API wiring (docs/OpenAPI) |
| DATA-01 | Medium | SQL safety | 10 sites in 9 methods, e.g. `platform_repository.py:164,860,903,924,991,3229,3363`; `subscription_repository.py:58` | SQL column names built from dict keys with no allow-list | Safe only because every caller passes a Pydantic dump; latent injection risk | Constant writable set per method (reuse `_service_write_values`, `:1199-1206`); widen the guard test | No | None | M | Proven · Fix before production |
| DATA-02 | Medium | Data / performance | `GET /v1/bookings` (`platform_repository.py:1690-1693`), `GET /v1/notifications` | No limit when `limit` is omitted; notifications are never paginated | Response size grows with history; five sub-selects per booking row | Server default (200) plus pagination headers; optional limit on notifications | No | Clients that need everything must page | S | Proven · Fix before production |
| PERF-01 | Medium | Performance | `session.py:45-50`; `deps.py:113-120`; `POST /v1/bookings/quote` | Every commit (including the throttle row on quotes) rotates the global cache epoch | Public cache hit rate probably near zero under load; extra round trips | Measure hit rate; keep throttle writes off the epoch-rotating session; exempt pure computations | No | None | M | Concern · Safe post-launch improvement |
| PERF-02 | Medium | Performance | `GET /v1/walkin/{qr_token}/qr` (`walkin.py:119-126`); `owner.py:271` | QR render runs on the event loop; unauthenticated; no `Cache-Control` | Each render blocks the worker; easy to amplify | `run_in_threadpool`; long-lived `Cache-Control` | No | None | S | Concern · Fix before production |
| TEST-02 | Medium | Tests | webhooks, reports, support, profiles, notifications routes; `deps.py` throttle; `core/exceptions.py` | No route-level tests; one envelope test only | Contract regressions undetected | Add tests together with the Phase B fixes | No | None | M | Proven · Fix before production |
| TEST-03 | Medium | Tests / auth | `profile_repository.py:32-57`; `POST /v1/auth/owner-access` | The only role-escalation path is untested | Its safety rests on one SQL predicate | Real-Postgres test of the role matrix | No | None | S | Proven · Fix before production |
| DOC-03 | Medium | Docs | `docs/README.md` | The mandated entry point omits most binding documents | Agents and engineers miss the rules they are bound by | Add the missing documents to the index | No | None | S | Proven · Fix before production |
| DOC-06 | Medium | Docs | `backend/docs/MARKETPLACE_CONTRACT.md` | Reads as a contract but is mostly unimplemented; payment-options shape conflicts with the shipped design | Client teams may build against routes that do not exist | Mark as forward design per section; point §3 to the shipped `payment_options` | No | Prevents wasted client work | S | Proven · Fix before frontend real API wiring |
| SEC-04 | Low | Security | `platform_repository.py:1862` | `get_booking` admits any booking when `actor_id` is null | Latent; not reachable from a request today | Remove the null branch; separate internal method | No | None | S | Proven · Safe post-launch improvement |
| SEC-05 | Low | Security / naming | `GET /v1/admin/catalog/languages` (`admin.py:382`) | Any signed-in user, under an `/admin` path | Looks unprotected to reviewers; no leak | Document as public reference data, or add a `/v1/catalog/languages` alias | No | None | S | Proven · Safe post-launch improvement |
| API-03 | Low | HTTP method | Admin category, subcategory and plan `…/deactivate` | Identical to `PATCH {"is_active": false}` (`platform_repository.py:3381-3384`) | Two ways to do one thing | Document PATCH as canonical; keep both | No | None | S | Proven · Do not change routes |
| API-04 | Low | Contract | Owner and admin soft-delete routes | Three soft-delete conventions (204 / 200 with body / POST deactivate) | Client inconsistency | Keep; one convention for new routes | No | None | S | Proven · Safe post-launch improvement |
| API-06 | Low | Naming | `/bookings/{id}/cancel`, `/cancel/barber`, `/cancellation-requests`, `/payment`, `/payments/*`, `/payment-confirmation-requests` | Distinct commands with confusable names | Integration mistakes | One-line description of each in the API documents | No | None | S | Proven · Do not change routes |
| API-07 | Low | Duplication | `GET /v1/salons`, `/v1/salons/nearby` (`customer.py:68,133`) | Overlapping contracts and duplicate coordinate aliases | Two filter sets to maintain | Document `nearby` as an alias | No | None | S | Proven · Safe post-launch improvement |
| API-08 | Low | Naming | `router.py:29,36,47`; tags; singular/plural paths | `/v1/admin` spread over three modules; mixed naming | Review and discoverability | Naming rule for new routes; no renames | No | None | S | Proven · Safe post-launch improvement |
| API-11 | Low | OpenAPI | `notifications.py:92`; `owner.py:240,271,281,369,432,758`; `reports.py:20,29` | Missing `response_model` on four 204 routes; QR model declared but not applied; schemas inside route files | OpenAPI inaccurate for generated clients | `response_model=None`; a real QR response model; move schemas | No | Regenerated types become accurate | S | Proven · Fix before frontend real API wiring |
| ENUM-04 | Low | Validation | `schemas/platform.py:157,268,277,286,296,352-395,478,725-727,774`; `schemas/admin.py:37,116,138` | Free text and device fields without `max_length` | Oversized stored values | Add `max_length` matching UI limits | No | None for normal input | S | Proven · Safe post-launch improvement |
| ENUM-05 | Low | Validation | `schemas/payment.py:228` vs `schemas/platform.py:849` | Two different UPI patterns | A value accepted in one place is rejected in another | One shared pattern | No | None | S | Proven · Safe post-launch improvement |
| ERR-03 | Low | Errors | `core/exceptions.py:130,247` | `idempotency_key_reused` (422) and `idempotency_key_reuse` (409) | Clients must handle both | Document side by side; one code for new routes | No | None | S | Proven · Do not change codes |
| DATA-03 | Low | Data | `support_repository.py:13-25` | `api_rate_limits` never pruned | Slow unbounded growth | Periodic delete in an existing worker | No | None | S | Proven · Safe post-launch improvement |
| DATA-04 | Low | Transactions | `routes/auth.py`, `use_cases/payments.py`, `platform_repository.py`, `deps.py:119` | Commits at three layers | Atomicity is hard to review | Use case owns the commit, for new code | No | None | S | Proven · Safe post-launch improvement |
| ARCH-01 | Low | Layering | 8 use-case modules (§11.3) | Use cases import concrete infrastructure classes | Weakens the port boundary and testability | Make it an acceptance criterion of the deferred refactor | No | None | L | Proven · Safe post-launch improvement |
| ARCH-02 | Low | Layering | `routes/owner.py`, `routes/admin.py` cache calls | Redundant, inconsistent cache deletes in route handlers | Looks like a bug; cache policy in the API layer | Comment or remove after PERF-01 | No | None | S | Proven · Safe post-launch improvement |
| ARCH-03 | Low | DI / testability | `customer.py:36`, `walkin.py:156`, `auth.py:33` | Collaborators built outside `Depends` | Test overrides do not apply | Wire through `Depends`; OTP flow into a use case | No | None | S | Proven · Safe post-launch improvement |
| DOC-01 | Low | Docs | `CLAUDE.md`; `graphify-out/` | Wiki referenced but missing; graph stale | Agents act on stale structure | Rebuild the graph; fix the reference | No | None | S | Proven · Safe post-launch improvement |
| DOC-02 | Low | Docs | `verification/cloud-run-startup-profile-2026-10-20.md:3` | Broken link | Unverifiable reference | Fix or remove the link | No | None | S | Proven · Safe post-launch improvement |
| DOC-04 | Low | Docs | `docs/SALON_APPROVAL.md`, `backend/docs/SALON_APPROVAL.md` | Same name, different subjects | Confusion | Rename the `docs/` file to match its subject | No | None | S | Proven · Safe post-launch improvement |
| DOC-05 | Low | Docs | `AGENTS.md` rule 49 and three other documents | Verification commands disagree; one typo | Copy-paste failures on Windows | One per-OS command block | No | None | S | Proven · Safe post-launch improvement |
| DOC-07 | Low | Docs | `CLAUDE.md`; `FRONTEND_INTEGRATION_PROMPTS.md:7-9` | Four clients vs three repositories | Minor confusion | Say "three repositories; the website has five surfaces" | No | None | S | Proven · Safe post-launch improvement |
| DOC-08 | Low | Docs | `backend/docs/PAYMENTS.md`, `IMAGE_MEDIA.md` | Partly superseded without inline markers | Readers follow outdated passages | Mark superseded passages inline | No | None | S | Proven · Safe post-launch improvement |
| DOC-10 | Low | Hygiene | `.gitignore`; `salonsalon-backend/`; this file name | Unresolved merge state; stray tracked directory; naming convention | Hygiene | `git add .gitignore` after review; remove the stray directory | No | None | S | Proven · Safe post-launch improvement |
| INFO-01 | Informational | Authorization | Owner by-ID operations (§8.1) | Salon-scoped writes; 404 for other tenants | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-02 | Informational | Data | `bookings_no_overlap`; 0035 trigger; `create_booking()` | Database-enforced overlap (including `checked_in`) and transitions | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-03 | Informational | Webhooks | `webhooks.py:33-66`; `ingest` | Bounded body, signature before parse, dedupe | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-04 | Informational | Media | `r2/storage.py:121-123,333-338` | HMAC-signed, path-bound, 300-second upload token | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-05 | Informational | Authorization | `profile_repository.py:32-57` | Promotion only from customer; new, unapproved salon | Confirmed correct (test it: TEST-03) | None | No | None | – | Do not change / already correct |
| INFO-06 | Informational | HTTP method | Command routes (§5.2) | Workflow, money and auth commands are correctly POST | Prevents churn | None | No | None | – | Do not change / already correct |
| INFO-07 | Informational | Errors | `core/exceptions.py` | One envelope, central mapping, no SQL leakage | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-08 | Informational | Idempotency | `payment_repository.py:58-112`; `use_cases/payments.py:226-233` | Actor-isolated ledger; online money requires a key | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-09 | Informational | Layering | `app/domain/` | Domain is framework-free | Confirmed correct | None | No | None | – | Do not change / already correct |
| INFO-10 | Informational | Performance / money | `pillow_processor.py:72-75`; `PaymentRefundRequest` | Image processing off the loop; refund amount bounded in SQL | Confirmed correct | None | No | None | – | Do not change / already correct |
| DOC-11 | Informational | Docs | `001_supabase_schema.sql:526-530` | Baseline shows the pre-0035 overlap predicate | Readers should know migrations amend the baseline | Optional note in the baseline header | No | None | – | Do not change / already correct |

**Totals:** Critical 0 · High 4 · Medium 17 · Low 23 · Informational 11.

## 14. Recommended remediation roadmap

**No item needs a database migration.** Every Phase A and Phase B item is application code, configuration, CI or documentation, so each can be rolled back by reverting its pull request. Following `AGENTS.md` rule 47, each item below should be its own branch and pull request.

### 14.0 First implementation priority plan (not implemented)

Ordered by risk. Nothing here has been started. Each item is its own branch and pull request.

| # | Item | Responsibility | Migration | Frontend compatibility | Required tests | Rollback |
|---|---|---|---|---|---|---|
| 1 | **ERR-02 (done in working tree, uncommitted):** booking errors must not turn outages into 409 `slot_unavailable`. Apply the message mapping only to business error codes `P0001` and `23514`; re-raise everything else | Code | No. Explicit `ERRCODE` values in the SQL functions would be a later migration. | Real conflicts keep their codes; only genuine failures change from 409 to 500 | Real-PostgreSQL booking-contract suite (runs in CI): overlap gives `slot_unavailable`; an injected database failure gives 500 | Revert the pull request |
| 2 | **SEC-01 / SEC-03:** normalised-phone OTP send throttle on the fail-closed Postgres limiter; verification-attempt limit per phone; secondary per-IP and per-QR limits | Code | No | Same inputs accepted (normalised, not rejected); only abusive volume gets 429 | Unit and HTTP tests: phone spellings share one bucket; verify attempts are capped; throttle holds with Redis down | Revert the pull request |
| 3 | **TEST-01:** real-PostgreSQL account-erasure suite (and the other skipped suites) in CI | Code for the CI file; backend owner confirms each suite isolates its own database | No | None | The suites themselves, running in CI | Remove the added environment variables |
| 4 | **ERR-01 / ENUM-03:** `UUID` path parameters; IANA timezone validation | Code. Deployment owner runs the read-only `pg_timezone_names` pre-check on each database before release | No | Valid input unchanged; malformed IDs move from 500 to 422; invalid timezones get 422 | One malformed-ID test per router; invalid-timezone test | Revert the pull request |
| 5 | **DATA-01:** explicit writable-column allow-lists at the 10 sites, reusing `_service_write_values` (`platform_repository.py:1199-1206`); widen the guard test to all repositories | Code | No | Identical for every current schema field; unknown keys give 422 | Unknown key raises `ValidationError`; guard test covers all repositories | Revert the pull request |

SEC-02 is a separate deployment-owner check and is not part of this code sequence.

**Progress on 2026-10-22 (working tree, uncommitted):** task 1 (ERR-02) is implemented and reviewed. Beyond the plan, two account-deletion changes were made: the `checked_in` customer blocker, and the closed-salon month-end statement endpoints. The financial purge after review is a design only ([ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md](../ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md)). **The new real-PostgreSQL tests for the statement have not been run:** they are skipped locally, and CI does not set `ACCOUNT_DELETION_TEST_DB` (finding TEST-01), so no pipeline runs them yet. Fixing TEST-01 is therefore a prerequisite for trusting this SQL.

### Phase A: must fix before frontend uses real APIs

Client integration status is mixed and unverified (§2), so this phase is limited to **contract-accuracy fixes that are safe whichever clients already call the API**. Each one is documentation or OpenAPI only, with no behaviour change.

| Item | Affected routes and files | Migration | Backward compatibility | Tests | Rollback |
|---|---|---|---|---|---|
| **API-02** Document null semantics | All PATCH routes; `docs/Customer-App-Backend-API-Document.md`, `docs/Salon-Owner-App-Backend-API-Document.md` | No | Documentation only | None | Revert the doc commit |
| **ERR-04 (a, b)** Mark `Idempotency-Key` required in OpenAPI where the use case enforces it; correct `AUTHORIZATION.md` | `routes/payments.py:81,106,135,154,191,244`; `routes/subscription_billing.py:117`; `routes/support.py:27,44` (8–200 already enforced in `use_cases/support.py:17`); `backend/docs/AUTHORIZATION.md` | No | Wire behaviour unchanged; requests without a key already get 400 | `test_api_contract.py`: assert `required: true` for these headers | Revert |
| **API-11** Accurate OpenAPI | `notifications.py:92`; `owner.py:240-281,369,432,758`; `reports.py:20,29` | No | Responses unchanged; the QR model gains a `cached` field to match current output | OpenAPI snapshot test | Revert |
| **DOC-06** Mark `MARKETPLACE_CONTRACT.md` as forward design | `backend/docs/MARKETPLACE_CONTRACT.md` | No | Documentation only | None | Revert |
| **ERR-03** Document both idempotency-reuse codes side by side | Both client API documents | No | Documentation only | None | Revert |

### Phase B: must fix before production

| Item | Affected routes and files | Migration | Backward compatibility | Tests | Rollback |
|---|---|---|---|---|---|
| **SEC-01, SEC-03, ENUM-02** OTP limits on the normalised phone | `routes/walkin.py:134-165`; `schemas/walkin.py:69-70`; `schemas/platform.py:46-74,476` (extract a shared normaliser); `support_repository.py` (throttle) | No | Same inputs accepted (normalised, not rejected); only abusive volume sees 429 | Spelling variants share one bucket; verify branch limited; limiter works with Redis down | Revert; the old limiter returns |
| **SEC-02** Verify the proxy path before trusting forwarded headers (**deployment owner**) | Deployment environment (`FORWARDED_ALLOW_IPS`) only if verified safe; `backend/docs/DOCKER_DEPLOYMENT.md` | No | Clients unaffected | On isolated staging, compare redacted peer address and `X-Forwarded-For`; confirm a forged header from outside the trusted scope is ignored | Unset the variable |
| **ERR-02** Map messages only for business error codes `P0001` and `23514`; re-raise the rest (done in working tree, uncommitted) | `platform_repository.py:1571-1590`; optionally the booking SQL functions raise explicit `ERRCODE` values (that part **would** need a migration, so ship the application-only classification first) | No for the first step | Real conflicts keep `slot_unavailable` and the other codes; only genuine failures change from 409 to 500 | `integration/test_booking_contract_sql.py` (in CI): overlap → `slot_unavailable`; injected connection error → 500 | Revert |
| **TEST-01** Run the skipped real-Postgres suites in CI | `.github/workflows/backend.yml:46-49` | No | Not applicable | The suites themselves | Remove the variables |
| **ERR-01** `UUID` path parameters | `routes/owner.py`, `bookings.py`, `payments.py`, `booking_actions.py`, `notifications.py`, `admin.py:181,202` | No | Valid IDs unchanged; malformed IDs return 422 instead of 500 | One malformed-ID test per router | Revert |
| **ENUM-03** IANA timezone validation | `schemas/platform.py:247`; `schemas/admin.py:22,95` | No (optional `CHECK` later) | Before deploying, run `select id, timezone from salons where timezone not in (select name from pg_timezone_names)` and fix any rows; valid values unaffected | Invalid zone → 422 | Revert |
| **DATA-01** Writable-column allow-lists | The 10 sites listed in §10; `tests/test_sql_bind_params.py:31-38` | No | Identical for every current schema field; unknown keys now raise 422 | Unknown key → `ValidationError`; guard test covers all repositories | Revert |
| **DATA-02** Default list limits | `routes/bookings.py` (`limit`), `platform_repository.py:1690-1693`; notifications route and repository | No | Default 200 equals the current maximum; add `X-Total-Count`, a header-only, additive change. Tell the owner app before release. | Omitted limit returns at most 200; header present | Revert |
| **PERF-02** QR render off the loop, plus caching | `routes/walkin.py:96-127`; `routes/owner.py:247-281` | No | Same bytes; adds `Cache-Control` | Response headers asserted | Revert |
| **API-01** PATCH alias for the payout account | `routes/owner.py:166-188`; owner API document | No | PUT kept with identical behaviour; PATCH added | Both verbs give the same result; omitted field kept | Remove the alias |
| **ENUM-01** Typed response enums | `schemas/platform.py`, `schemas/payment.py`, `schemas/subscription*.py`, `schemas/booking_actions.py` | No | Same JSON; OpenAPI gains enum lists. Run `select distinct` on text-backed columns first. | OpenAPI snapshot; response validation on fixtures | Revert |
| **TEST-02, TEST-03** Route, error-envelope and role-matrix tests | `tests/` | No | Not applicable | The tests themselves | Not applicable |
| **DOC-03** Complete the `docs/README.md` index | `docs/README.md` | No | Not applicable | Markdown link check | Revert |

### Phase C: post-launch refactor

PERF-01 (after measuring the cache hit rate) · ARCH-01, ARCH-02, ARCH-03 and DATA-04 (inside the deferred `PlatformRepository`/`OwnerUseCases` refactor, `decisions.md` #7) · API-03, API-04, API-05, API-06, API-07, API-08 (documentation and conventions for new routes; no renames) · ENUM-04, ENUM-05 · DATA-03 · SEC-04, SEC-05 · DOC-01, DOC-02, DOC-04, DOC-05, DOC-07, DOC-08, DOC-10.

### Phase D: do not change; the current design is intentional

All `INFO-*` items, the correct POST commands in §5.2, the PUTs in §5.3, and every recorded decision in §16. The items in §15 should also not be changed.

## 15. Items explicitly NOT recommended to change now

### 15.1 Candidates disproved during this audit

Each of these looks like a defect at first reading. Each was traced and found **not** to be one. They are recorded so they are not raised again.

| Looks like | Why it is not a defect | Evidence |
|---|---|---|
| Staff changes leave the walk-in QR page stale (staff routes never flush `walkin:qr:`) | Every commit rotates the global read-model epoch, which invalidates every cached key | `infrastructure/db/session.py:45-50`; `redis.py:66-91` |
| A checked-in booking frees its slot (the overlap constraint covers only `pending`/`confirmed`) | That is the baseline definition. Migration 0035 extended it to `checked_in`. | `migrations/sql/0035_booking_checkout_safety.sql:58-62` |
| A retried manual payment without `Idempotency-Key` is recorded twice | Row lock plus the `payment_status = 'paid'` check returns 409; a database overcollection guard backs it up | `platform_repository.py:2208-2245` |
| `PATCH /v1/customer/profile` skips the avatar cleanup that `/v1/profiles/me` does | Both call the same use case with a storage gateway; old avatars are retired by the worker | `customer.py:36`; `use_cases/platform.py:79-114` |
| Refund accepts a client amount, against the "clients never send an amount" rule | A documented exception: the partial refund is bounded in SQL by the captured payment | `backend/docs/PAYMENTS.md:65-66` |
| `POST /v1/auth/owner-access` lets any user become an owner | Promotion only from `customer`, into a new unapproved salon; existing salons are unreachable | `profile_repository.py:32-57` |
| The unauthenticated `PUT /v1/media/uploads/{token}` allows writes to arbitrary objects | The token is an HMAC over bucket, server-chosen path, MIME type and a 300-second expiry | `r2/storage.py:121-123,333-338` |
| Dynamic SQL in update methods is injectable today | All callers pass Pydantic dumps and no schema allows extra keys (still DATA-01 as hardening) | §10, DATA-01 |
| The webhook `provider` path parameter should be an enum | The resolver allow-lists the enabled providers and returns 404 for anything else; providers are configuration-driven | `use_cases/payments.py` (`ingest`) |
| The swallowed exceptions in payment adapters | All are narrow `ValueError` fallbacks around optional field parsing | `cashfree.py:298,387`; `razorpay.py:194` |

### 15.2 Do not change, even though it is imperfect

- **No breaking renames or method changes on routes that clients may call.** That covers API-03, API-04, API-06, API-07 and API-08, `POST /notifications/{id}/read`, and the 200 on `POST /v1/salons/me/staff/{id}/services`. Add, document and deprecate; never replace in place.
- **Do not convert `PUT /payout-account` to full replacement** (API-01). It would silently clear fields for clients that may already use it.
- **Do not change null handling globally** (API-02). Some clients may send `null` meaning "no change".
- **Do not require `Idempotency-Key` on booking-family routes** until server logs show every client sends it (ERR-04).
- **Do not unify the two idempotency-reuse error codes** (ERR-03). Both are published.
- **Do not weaken the global epoch invalidation** to improve the cache hit rate (PERF-01). Change the throttle's session instead.
- **Do not split `PlatformRepository` or `OwnerUseCases` outside the approved refactor** (`decisions.md` #7).

## 16. Existing decisions and deferred work

These were checked **before** findings were written. None is raised as a new finding. Reopen any of them only through the trigger given by its source.

| Topic | Status | Source |
|---|---|---|
| Split `PlatformRepository` / `OwnerUseCases`; delete or wire `email_gateway.py`; `http_exception_handler`; `COMPOSE_ENV_FILE`; graph-inferred dead code | Deferred, or kept by decision | `docs/agent-memory/shared/decisions.md` #7 (2026-10-21) |
| Image `result_url` is a separate read-only token, never the PUT URL | Decided (a security fix) | `decisions.md` #4 |
| `media-cleanup` Compose healthcheck disabled until tested | Decided | `decisions.md` #5 |
| Financial repair by one `aal2` super-admin plus audit; no two-person approval | Decided (owner decisions U06, TA07) | `decisions.md` #6; `APPROVAL_REGISTER.md` |
| Unauthenticated `POST /v1/webhooks/{provider}` (the signature is the credential; mounted only when enabled) | Intentional | `backend/docs/AUTHORIZATION.md`; `PAYMENTS.md` |
| Deletion-status route authenticated by `X-Status-Token` (a header, kept out of access logs) | Intentional | `backend/docs/ACCOUNT_DELETION.md` |
| No account-deletion grace period; owner bookings cancelled and refunded rather than blocking; inert closed-salon shell | Owner decisions | `ACCOUNT_DELETION.md` |
| QR tokens without expiry or a rotation endpoint | Current contract | `docs/PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §3 |
| No salon-ID OTP endpoint for the website (SMS abuse risk) | Open owner decision | `PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §4 |
| No index on the salon search filters (`pg_trgm` trigger documented) | Deliberate | `PUBLIC_DISCOVERY_AND_BOOKING_CONTRACT.md` §1 |
| `payment_status` stays `unpaid\|paid`; richer state is the derived `payment_state` | Design rule | `backend/docs/PAYMENTS.md`, design rule 2 |
| Booking payment columns are a derived cache of the ledger | Design rule | `PAYMENTS.md`, design rule 1 |
| No automatic booking release on payment failure; `PAYMENT_AUTO_RELEASE_ENABLED` refused at boot | Not built, by decision | `PAYMENTS.md`; `PAYMENT_DECISIONS.md` gap 6 |
| Plaintext payout bank numbers | Known recorded gap (TA10 design-approved only) | `PAYMENT_DECISIONS.md` gap 9 |
| Commission rate configurable with no default | Decision | `PAYMENT_DECISIONS.md` |
| Subscriptions: one-time order with manual renewal; no AutoPay; no proration; refunds do not revoke access; no native in-app purchase | Decisions | `backend/docs/SUBSCRIPTIONS.md`; `MARKETPLACE_CONTRACT.md` §8 |
| Online payments dormant until a provider and credentials are configured; provider field names unverified (P01–P06) | Dormant by design | `shared/roadmap.md`; `PAYMENT_DECISIONS.md` |
| Cancellation bands, 70/30 split, payout holds, reschedule limit | Approved, not built | `shared/domain-rules.md`; U06/U07 |
| Flat cancellation fee has no default (Q25) | Open owner decision | `PHASE1_DECISION_SHEET.md` §D |
| Migrations 0038–0040 held; integration tests target 0037 | Held | `shared/gotchas.md` #11; `verification/mumbai-staging-readiness-review-2026-10-16.md` |
| Three local CRLF test failures | Expected sealed evidence; do not "fix" | `shared/gotchas.md` #13 |
| Cold start of about 8–10 s on Cloud Run; `/health/db` latency | Measured and closed | `verification/cloud-run-startup-profile-2026-10-20.md`; `verification/latency-investigation.md` |
| `access-state` is a thin stub | Documented | `docs/Salon-Owner-App-Backend-API-Document.md` |
| "Any staff" availability not implemented | Documented boundary | `docs/Salon-Owner-App-Backend-API-Document.md` |
| Multi-message super-admin to owner review thread ("changes requested") | Requested 2026-10-22, not built; needs scoping, a reviewed migration and endpoints | This report, §3.1 |
| Website runs the full customer and owner flows on the same APIs as the apps | Requested 2026-10-22; no website-only business logic | This report, §3.1 |

The full decision ledger, with owner approvals U01–U07 and about 80 statused items (Q, P, L, RP, MH, RC and TA), is `backend/docs/migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md`.

## 17. Appendix: route inventory

Generated from source at `HEAD` (`828d73b`) by parsing every route decorator in `backend/app/api/v1/routes/`, with prefixes taken from `backend/app/api/v1/router.py` and `backend/app/main.py:114`. **140 routes**: POST 64, GET 56, PATCH 11, DELETE 6, PUT 3. "actor" means authenticated with no role check; ownership is enforced in the use case. "Idem." marks routes that read an `Idempotency-Key` header (§9 explains which ones require it).

| Group | Method | Path | Handler | response_model | Status | Auth | Idem. |
|---|---|---|---|---|---|---|---|
| Public discovery | GET | `/v1/availability` | `bookings.py:48` | list[AvailabilityResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/catalog/categories` | `customer.py:275` | list[CategoryResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/catalog/categories/{category_id}/subcategories` | `customer.py:304` | list[SubcategoryResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/payments/config` | `payments.py:58` | PaymentConfigResponse | 200 | none (public) |  |
| Public discovery | GET | `/v1/salons` | `customer.py:68` | list[SalonSummaryResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/salons/nearby` | `customer.py:133` | list[SalonSummaryResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/salons/{salon_id}` | `customer.py:200` | SalonDetailResponse | 200 | none (public) |  |
| Public discovery | GET | `/v1/salons/{salon_id}/services` | `customer.py:224` | list[ServiceResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/salons/{salon_id}/staff` | `customer.py:248` | list[PublicStaffResponse] | 200 | none (public) |  |
| Public discovery | GET | `/v1/subscriptions/config` | `subscription_billing.py:48` | SubscriptionConfigResponse | 200 | none (public) |  |
| Auth/account | POST | `/v1/account/deletion` | `account_deletion.py:96` | AccountDeletionAcceptedResponse | 202 | actor |  |
| Auth/account | POST | `/v1/account/deletion/challenges` | `account_deletion.py:55` | DeletionChallengeResponse | 202 | actor |  |
| Auth/account | POST | `/v1/account/deletion/challenges/{challenge_id}/verify` | `account_deletion.py:75` | VerifiedDeletionChallengeResponse | 200 | actor |  |
| Auth/account | GET | `/v1/account/deletion/{request_id}` | `account_deletion.py:120` | AccountDeletionStatusResponse | 200 | none (X-Status-Token) |  |
| Auth/account | POST | `/v1/auth/forgot-password` | `auth.py:27` | ForgotPasswordResponse | 202 | none (public) |  |
| Auth/account | GET | `/v1/auth/me` | `auth.py:58` | ProfileResponse | 200 | actor |  |
| Auth/account | POST | `/v1/auth/owner-access` | `auth.py:71` | ProfileResponse | 200 | actor |  |
| Auth/account | POST | `/v1/auth/refresh` | `auth.py:42` | TokenResponse | 200 | none (public) |  |
| Auth/account | GET | `/v1/profiles/me` | `profiles.py:22` | ProfileResponse | 200 | actor |  |
| Auth/account | PATCH | `/v1/profiles/me` | `profiles.py:43` | ProfileResponse | 200 | actor |  |
| Customer | GET | `/v1/customer/profile` | `customer.py:39` | ProfileResponse | 200 | actor |  |
| Customer | PATCH | `/v1/customer/profile` | `customer.py:51` | ProfileResponse | 200 | actor |  |
| Customer | POST | `/v1/reports` | `reports.py:34` | ReportResponse | 201 | actor |  |
| Owner | GET | `/v1/salons/me` | `owner.py:67` | OwnerSalonResponse | 200 | actor |  |
| Owner | PATCH | `/v1/salons/me` | `owner.py:83` | OwnerSalonResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/blocks` | `owner.py:721` | list[BlockedSlotResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/blocks` | `owner.py:737` | BlockedSlotResponse | 201 | actor |  |
| Owner | DELETE | `/v1/salons/me/blocks/{block_id}` | `owner.py:758` | **missing** | 204 | actor |  |
| Owner | POST | `/v1/salons/me/closures` | `booking_actions.py:148` | ClosureApplyResponse | 201 | actor |  |
| Owner | POST | `/v1/salons/me/closures/preview` | `booking_actions.py:131` | ClosurePreviewResponse | 200 | actor |  |
| Owner | POST | `/v1/salons/me/complete-profile` | `owner.py:103` | OwnerSalonResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/earnings` | `payments.py:202` | EarningsResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/holidays` | `owner.py:399` | list[HolidayResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/holidays` | `owner.py:415` | HolidayResponse | 201 | actor |  |
| Owner | DELETE | `/v1/salons/me/holidays/{holiday_id}` | `owner.py:432` | **missing** | 204 | actor |  |
| Owner | GET | `/v1/salons/me/images` | `owner.py:318` | list[SalonImageResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/images` | `owner.py:334` | SalonImageResponse | 201 | actor |  |
| Owner | DELETE | `/v1/salons/me/images/{image_id}` | `owner.py:369` | **missing** | 204 | actor |  |
| Owner | PATCH | `/v1/salons/me/images/{image_id}` | `owner.py:351` | SalonImageResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/payout-account` | `owner.py:147` | OwnerPayoutAccountResponse | 200 | actor |  |
| Owner | PUT | `/v1/salons/me/payout-account` | `owner.py:166` | OwnerPayoutAccountResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/payout-account/history` | `owner.py:190` | list[PayoutHistoryEntryResponse] | 200 | actor |  |
| Owner | GET | `/v1/salons/me/qr` | `owner.py:247` | QrCodeUrlResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/services` | `owner.py:451` | list[ServiceResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/services` | `owner.py:462` | ServiceResponse | 201 | actor |  |
| Owner | DELETE | `/v1/salons/me/services/{service_id}` | `owner.py:507` | ServiceResponse | 200 | actor |  |
| Owner | PATCH | `/v1/salons/me/services/{service_id}` | `owner.py:484` | ServiceResponse | 200 | actor |  |
| Owner | PATCH | `/v1/salons/me/settings` | `owner.py:121` | OwnerSalonResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/settlement-account` | `payments.py:216` | SettlementAccountResponse | 200 | actor |  |
| Owner | POST | `/v1/salons/me/settlement-account/register` | `payments.py:232` | SettlementAccountResponse | 200 | actor | yes |
| Owner | GET | `/v1/salons/me/setup-status` | `owner.py:222` | OwnerSetupStatusResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/staff` | `owner.py:532` | list[StaffResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/staff` | `owner.py:543` | StaffResponse | 201 | actor |  |
| Owner | DELETE | `/v1/salons/me/staff/{staff_id}` | `owner.py:584` | StaffResponse | 200 | actor |  |
| Owner | PATCH | `/v1/salons/me/staff/{staff_id}` | `owner.py:563` | StaffResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/staff/{staff_id}/services` | `owner.py:622` | list[StaffServiceResponse] | 200 | actor |  |
| Owner | POST | `/v1/salons/me/staff/{staff_id}/services` | `owner.py:604` | StaffServiceResponse | 200 | actor |  |
| Owner | GET | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | `owner.py:675` | list[LanguageResponse] | 200 | actor |  |
| Owner | PUT | `/v1/salons/me/staff/{staff_id}/services/{staff_service_id}/languages` | `owner.py:693` | list[LanguageResponse] | 200 | actor |  |
| Booking | GET | `/v1/booking-action-requests` | `booking_actions.py:87` | list[BookingActionRequestResponse] | 200 | actor |  |
| Booking | POST | `/v1/booking-action-requests/{request_id}/respond` | `booking_actions.py:106` | BookingActionRequestResponse | 200 | actor |  |
| Booking | GET | `/v1/bookings` | `bookings.py:91` | list[BookingResponse] | 200 | actor |  |
| Booking | POST | `/v1/bookings` | `bookings.py:67` | BookingResponse | 201 | actor | yes |
| Booking | POST | `/v1/bookings/quote` | `payments.py:34` | BookingQuoteResponse | 200 | actor |  |
| Booking | GET | `/v1/bookings/{booking_id}` | `bookings.py:126` | BookingResponse | 200 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/approve` | `bookings.py:143` | BookingResponse | 200 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/cancel` | `bookings.py:226` | BookingResponse | 200 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/cancel/barber` | `bookings.py:257` | BookingResponse | 200 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/cancellation-requests` | `booking_actions.py:62` | BookingActionRequestResponse | 201 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/check-in` | `bookings.py:30` | BookingResponse | 200 | actor | yes |
| Booking | POST | `/v1/bookings/{booking_id}/complete` | `bookings.py:182` | BookingResponse | 200 | actor | yes |
| Booking | POST | `/v1/bookings/{booking_id}/delay` | `bookings.py:201` | BookingResponse | 200 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/no-show` | `bookings.py:37` | BookingResponse | 200 | actor | yes |
| Booking | POST | `/v1/bookings/{booking_id}/payment` | `bookings.py:289` | BookingResponse | 200 | actor | yes |
| Booking | POST | `/v1/bookings/{booking_id}/payment-confirmation-requests` | `booking_actions.py:36` | BookingActionRequestResponse | 201 | actor |  |
| Booking | POST | `/v1/bookings/{booking_id}/reject` | `bookings.py:161` | BookingResponse | 200 | actor |  |
| Walk-in/QR | GET | `/v1/walkin/{qr_token}` | `walkin.py:46` | WalkInSalonResponse | 200 | none (public) |  |
| Walk-in/QR | POST | `/v1/walkin/{qr_token}/bookings` | `walkin.py:168` | BookingResponse | 201 | actor | yes |
| Walk-in/QR | GET | `/v1/walkin/{qr_token}/qr` | `walkin.py:75` | None | 200 | none (public) |  |
| Walk-in/QR | POST | `/v1/walkin/{qr_token}/verify-phone` | `walkin.py:134` | WalkInVerifyPhoneResponse | 200 | none (public) |  |
| Payments/refunds | GET | `/v1/bookings/{booking_id}/payments` | `payments.py:163` | BookingPaymentsResponse | 200 | actor |  |
| Payments/refunds | POST | `/v1/bookings/{booking_id}/payments/cancel` | `payments.py:146` | BookingPaymentsResponse | 200 | actor | yes |
| Payments/refunds | POST | `/v1/bookings/{booking_id}/payments/confirm` | `payments.py:92` | BookingPaymentsResponse | 200 | actor | yes |
| Payments/refunds | POST | `/v1/bookings/{booking_id}/payments/intent` | `payments.py:71` | PaymentIntentResponse | 200 | actor | yes |
| Payments/refunds | POST | `/v1/bookings/{booking_id}/payments/refresh` | `payments.py:122` | BookingPaymentsResponse | 200 | actor | yes |
| Payments/refunds | POST | `/v1/bookings/{booking_id}/payments/{payment_id}/refund` | `payments.py:180` | BookingPaymentsResponse | 200 | actor | yes |
| Subscriptions | GET | `/v1/salons/me/access-state` | `subscription_billing.py:90` | AccessStateResponse | 200 | actor |  |
| Subscriptions | GET | `/v1/salons/me/subscription` | `subscription_billing.py:76` | SubscriptionStateResponse | 200 | actor |  |
| Subscriptions | POST | `/v1/salons/me/subscription/cancel` | `subscription_billing.py:148` | SubscriptionStateResponse | 200 | actor |  |
| Subscriptions | POST | `/v1/salons/me/subscription/checkout` | `subscription_billing.py:105` | CheckoutResponse | 200 | actor | yes |
| Subscriptions | GET | `/v1/salons/me/subscription/payments` | `subscription_billing.py:163` | list[BillingPaymentResponse] | 200 | actor |  |
| Subscriptions | POST | `/v1/salons/me/subscription/verify` | `subscription_billing.py:126` | SubscriptionStateResponse | 200 | actor |  |
| Subscriptions | GET | `/v1/subscription-plans` | `subscription_billing.py:61` | list[PurchasablePlanResponse] | 200 | actor |  |
| Media | POST | `/v1/customer/profile/avatar` | `media.py:20` | AvatarResponse | 200 | actor |  |
| Media | GET | `/v1/media/results/{token}` | `media.py:77` | ImageFamilyResponse | 200 | none (signed token) |  |
| Media | PUT | `/v1/media/uploads/{token}` | `media.py:45` | None | 204 | none (signed token) |  |
| Media | POST | `/v1/profiles/me/avatar-upload-url` | `profiles.py:70` | ImageUploadUrlResponse | 200 | actor |  |
| Media | POST | `/v1/salons/me/images/upload-url` | `owner.py:287` | ImageUploadUrlResponse | 200 | actor |  |
| Media | POST | `/v1/salons/me/staff/{staff_id}/photo-upload-url` | `owner.py:639` | ImageUploadUrlResponse | 200 | actor |  |
| Notifications/support | POST | `/v1/devices` | `notifications.py:73` | DeviceRegisterResponse | 200 | actor |  |
| Notifications/support | DELETE | `/v1/devices/{token}` | `notifications.py:92` | **missing** | 204 | actor |  |
| Notifications/support | GET | `/v1/email/events/{event_id}` | `support.py:48` | EmailEventResponse | 200 | actor |  |
| Notifications/support | GET | `/v1/notifications` | `notifications.py:24` | list[NotificationResponse] | 200 | actor |  |
| Notifications/support | POST | `/v1/notifications/read-all` | `notifications.py:57` | MarkAllNotificationsReadResponse | 200 | actor |  |
| Notifications/support | POST | `/v1/notifications/{notification_id}/read` | `notifications.py:40` | NotificationResponse | 200 | actor |  |
| Notifications/support | POST | `/v1/support/tickets` | `support.py:24` | SupportTicketResponse | 201 | actor | yes |
| Notifications/support | GET | `/v1/support/tickets/{ticket_id}` | `support.py:33` | SupportTicketResponse | 200 | role: customer, owner, super_admin |  |
| Notifications/support | POST | `/v1/support/tickets/{ticket_id}/reply` | `support.py:40` | SupportTicketResponse | 200 | role: owner, super_admin | yes |
| Admin | GET | `/v1/admin/account-deletions` | `account_deletion.py:140` | list[AdminAccountDeletionResponse] | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/catalog/categories` | `admin.py:223` | list[CategoryResponse] | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/catalog/categories` | `admin.py:240` | CategoryResponse | 201 | role: super_admin |  |
| Admin | PATCH | `/v1/admin/catalog/categories/{category_id}` | `admin.py:259` | CategoryResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/catalog/categories/{category_id}/deactivate` | `admin.py:282` | CategoryResponse | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/catalog/categories/{category_id}/subcategories` | `admin.py:302` | list[SubcategoryResponse] | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/catalog/languages` | `admin.py:382` | list[LanguageResponse] | 200 | actor |  |
| Admin | POST | `/v1/admin/catalog/subcategories` | `admin.py:322` | SubcategoryResponse | 201 | role: super_admin |  |
| Admin | PATCH | `/v1/admin/catalog/subcategories/{subcategory_id}` | `admin.py:341` | SubcategoryResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/catalog/subcategories/{subcategory_id}/deactivate` | `admin.py:363` | SubcategoryResponse | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/salons` | `admin.py:103` | list[AdminSalonResponse] | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/salons` | `admin.py:76` | AdminSalonResponse | 201 | role: super_admin |  |
| Admin | GET | `/v1/admin/salons/{salon_id}` | `admin.py:126` | AdminSalonResponse | 200 | role: super_admin |  |
| Admin | PATCH | `/v1/admin/salons/{salon_id}` | `admin.py:181` | AdminSalonResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/salons/{salon_id}/approve` | `admin.py:152` | AdminSalonResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/salons/{salon_id}/deactivate` | `admin.py:202` | AdminDeactivateSalonResponse | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/salons/{salon_id}/onboarding` | `admin.py:137` | AdminSalonOnboardingResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/salons/{salon_id}/reject` | `admin.py:166` | AdminSalonResponse | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/salons/{salon_id}/subscription` | `subscriptions.py:110` | SubscriptionResponse \| None | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/salons/{salon_id}/subscription/test` | `subscriptions.py:125` | SubscriptionResponse | 201 | role: super_admin |  |
| Admin | GET | `/v1/admin/subscription-events` | `subscriptions.py:187` | list[SubscriptionEventResponse] | 200 | role: super_admin |  |
| Admin | GET | `/v1/admin/subscription-plans` | `subscriptions.py:44` | list[PlanResponse] | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/subscription-plans` | `subscriptions.py:59` | PlanResponse | 201 | role: super_admin |  |
| Admin | PATCH | `/v1/admin/subscription-plans/{plan_id}` | `subscriptions.py:74` | PlanResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/subscription-plans/{plan_id}/deactivate` | `subscriptions.py:92` | PlanResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/subscriptions/{subscription_id}/cancel` | `subscriptions.py:154` | SubscriptionResponse | 200 | role: super_admin |  |
| Admin | POST | `/v1/admin/subscriptions/{subscription_id}/suspend` | `subscriptions.py:169` | SubscriptionResponse | 200 | role: super_admin |  |
| Webhooks | POST | `/v1/webhooks/{provider}` | `webhooks.py:33` | WebhookAckResponse | 200 | none (provider signature) |  |
| Health | GET | `/health` | `health.py:16` | HealthResponse | 200 | none (public) |  |
| Health | GET | `/health/db` | `health.py:29` | DatabaseHealthResponse | 200 | none (public) |  |
| Health | GET | `/health/ready` | `health.py:64` | HealthResponse | 200 | none (public) |  |
| Health | GET | `/health/redis` | `health.py:46` | RedisHealthResponse | 200 | none (public) |  |

Routes per group: Public discovery 10, Auth/account 10, Customer 3, Owner 36, Booking 17, Walk-in/QR 4, Payments/refunds 6, Subscriptions 7, Media 6, Notifications/support 9, Admin 27, Webhooks 1, Health 4. Total 140.
