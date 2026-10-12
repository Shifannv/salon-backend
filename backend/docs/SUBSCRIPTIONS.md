# Subscription & Promotion Foundation

> **Stage 2 (owner subscription billing) is BUILT and tested locally; nothing is sandbox-tested,
> deployed or enabled.** `SUBSCRIPTION_PROVIDER=none` is the default and live activation fails
> closed. Jump to [Owner billing (stage 2)](#owner-billing-stage-2). The sections below that
> predate it ("Current state", "Steps to add a future payment provider", "Webhook preparation")
> describe the 0018 foundation and are superseded where they say "not implemented".

## Current state (foundation, 0018)

Migration `0018_subscription_foundation` creates the database tables.
`SUBSCRIPTION_PROVIDER=none` (default) means:

- No external payment calls.
- No webhook endpoints registered.
- All subscriptions remain inactive unless explicitly created by a super admin.
- The API and all apps continue functioning normally.

Activation is manual super-admin control OR (stage 2, dormant until enabled) payment-verified
activation. Once an eligible subscription exists, its plan weight participates automatically in
discovery ordering.

## Tables created

| Table | Purpose |
|-------|---------|
| `subscription_plans` | Tier, ranking weight, price, billing interval |
| `salon_subscriptions` | Per-salon subscription state with period tracking |
| `subscription_provider_accounts` | Opaque provider references per salon |
| `subscription_events` | Idempotent event log for future webhook processing |

Indexes: plan code uniqueness, active-subscription-per-salon uniqueness (partial),
event provider/reference idempotency (partial), subscription status and salon lookups.

## Subscription statuses

`pending` → `trialing` → `active` → `past_due` → `expired`

Cancellation: any non-terminal → `cancelled`
Suspension: any non-terminal → `suspended`

## Promotion eligibility

`is_subscription_promotion_active(status, period_start, period_end, grace_end, now)`:

| Status | Eligible? |
|--------|-----------|
| `active` / `trialing` | During `[current_period_start, current_period_end)` |
| `cancelled` | Until `current_period_end` |
| `past_due` | Until `grace_period_end` |
| `expired` / `suspended` / `pending` | Never |

Invalid or missing dates → never eligible.

## Public discovery ordering

Migration `0019_discovery_placement` adds visibility and home placement. For the home
surface, exclude hidden/search-only salons and order top, normal, random, then below.
The random group uses a stable `shuffle_seed`; other groups retain the ordering below.
Search and nearby exclude hidden salons and retain the ordering below, without home
placement. Hidden discovery does not revoke an approved salon's QR or direct detail.

After visibility filter (`approved`, `active`, `profile_completed`):

1. `subscription ranking_weight DESC` (from active promotion)
2. `display_priority DESC` (super-admin manual control)
3. `distance_km ASC NULLS LAST`
4. `salon name ASC`
5. `salon ID ASC`

No subscription → weight 0 → falls back to existing ordering.

## Admin API contract

All under `/v1/admin/`, all require `super_admin` role.

### Plans

- `GET /subscription-plans` — list (optional `include_inactive`)
- `POST /subscription-plans` — create
- `PATCH /subscription-plans/{id}` — update
- `POST /subscription-plans/{id}/deactivate`

### Subscriptions

- `GET /salons/{id}/subscription` — view salon's non-terminal subscription
- `POST /salons/{id}/subscription/test` — manual/test activation (creates a record; NOT payment)
- `POST /subscriptions/{id}/cancel`
- `POST /subscriptions/{id}/suspend`

### Events

- `GET /subscription-events` — list processed events (optional `subscription_id` filter)

## What is NOT exposed

- Provider name, customer reference, subscription reference → admin-only, not in any response schema
- Ranking weight, display priority, plan tier, billing details → never in public salon responses
- Stage 2 adds owner billing endpoints and a webhook handler (see "Owner billing (stage 2)" below);
  they expose no provider references either

## Config boundary

```
SUBSCRIPTION_PROVIDER=none     # default: no external calls, billing endpoints answer 503
SUBSCRIPTION_PROVIDER=razorpay # stage 2 adapter (see "Owner billing (stage 2)")
```

## Steps to add a future payment provider (superseded: see "Adding another subscription provider")

1. Create `app/infrastructure/subscriptions/<provider>.py` implementing `SubscriptionProviderAdapter`
2. Add a webhook route in `app/api/v1/routes/webhooks.py` that:
   - Verifies signature using the adapter
   - Parses events into internal `SubscriptionEventType` commands
   - Records the event with idempotency (duplicate `provider_event_reference` is rejected)
   - Processes the command (create/renew/cancel/expire subscription)
3. Add `SUBSCRIPTION_PROVIDER=<name>` support in config
4. Register the webhook route only when the provider is configured
5. No changes needed to:
   - Customer app API models
   - Owner app API models
   - Public salon-list response shape
   - Ranking logic
   - Database domain tables

## Webhook preparation (historic; implemented in stage 2)

The event-processing contract is ready:

- Provider event references must be unique (partial unique index)
- Event processing is idempotent (duplicate inserts rejected)
- Event status is recorded (`received` → `processing` → `processed` | `failed`)
- Failed processing is retryable (status + error_message tracked)
- Raw payload storage must avoid secrets and PII
- Provider payloads must not be trusted without signature verification

## Payment provider decision (shared or separate)

Customer payments (`PAYMENTS.md`) and subscriptions share **one webhook endpoint and one
intake/idempotency table per provider**: `POST /v1/webhooks/{provider}` writes to
`payment_webhook_events`. They share nothing else: separate ports (`PaymentGateway` vs
`SubscriptionProvider`), separate credentials and webhook secrets, separate enablement
(`PAYMENT_PROVIDER` vs `SUBSCRIPTION_PROVIDER`), separate resolvers. A subscription outage never
disables Cashfree booking collection and the reverse. `payment_provider_accounts` models the salon
as *payee*; subscriptions model the salon as *payer* and the revenue is the platform's, never split.

# Owner billing (stage 2)

## Mode and store-policy posture

* **One-time order, one paid period, MANUAL renewal.** The owner pays for one period (1, 6 or 12
  months); nothing renews by itself. Provider-managed recurring billing (AutoPay) is **not built**;
  `SubscriptionProvider.supports_recurring` is the seam. Never enable both for one period.
* **Native apps do not sell.** The owner app shows no price and no purchase button (Apple 3.1.1 /
  Google Play Billing). Purchase is a **website** flow using the same Supabase JWT. The backend
  exposes billing endpoints for that site and entitlement reads for the apps.
  `GET /v1/subscriptions/config` always answers `native_purchase_allowed: false`.
* Plans, prices and benefits come only from the admin-managed `subscription_plans` table. Migration
  `0031_seed_subscription_plans` seeds Growth (349 / 1,499 / 1,999) and Premium (599 / 2,499 / 3,499)
  for 1 / 6 / 12 months (INR, as supplied) with `features` jsonb, and never overwrites an edited
  row. **GST is undecided**: `tax_inclusive` is `NULL` ("unknown"), never guessed.
* Admin manual/test activation (`/v1/admin/...`) is unchanged, admin-only, labelled manual. Frontends
  must never call it.

## Flow

```text
 website            backend                              provider            worker
   | POST checkout     |                                     |                  |
   |  {plan_id}        |-- INSERT billing row (price snapshot, receipt) COMMIT   |
   |  Idempotency-Key  |-- create order (receipt = OUR id) -->|                  |
   |<- client_payload--|<- order id --------------------------|                  |
   |-- open Checkout (key_id, order_id, amount in paise) ----->|                  |
   |   pays            |                                      |-- webhook ------>| (a) /v1/webhooks/razorpay
   |<- result (HINT)   |<-- payment.captured / order.paid ----|                  |     verify HMAC, dedupe,
   | POST verify       |-- GET order payments (server fetch) ->|                  |     store 'subscription' event
   |  {order_ref}      |-- compare amount, currency, order ---|                  |
   |                   |-- mark paid -> apply_subscription_billing_record (SQL, atomic, once)
   |<- state ----------|                                      |                  |
   |                   |        every poll: stale open orders -> same fetch+apply; expire unpaid;
   |                   |        sweep lapsed periods; re-apply paid-but-unapplied rows
```

Three independent triggers (webhook, `verify`, worker) converge on one function. None trusts a
client result: the proof is always a **server fetch from the provider** of a captured payment on
THIS order whose amount and currency equal the purchase snapshot.

## Tables (migration 0030)

`subscription_billing_records`: one row per purchase attempt. `receipt` (ours, unique, `sub_` + 32
hex) is persisted **before** the provider call; `provider_order_ref` / `provider_payment_ref` are
unique per provider and resolve a provider event to a salon. Snapshot columns (`amount`,
`currency`, `billing_interval`, `benefits`, `plan_code`, `tax_inclusive`) are written from the plan
row inside the INSERT and made **immutable by a trigger**, so a later price edit never rewrites
history. `period_start/period_end/subscription_id/applied_at` are set once by activation.
Partial unique index: **one open (`created`/`authorized`) purchase per salon**. RLS on, nothing for
`anon`/`authenticated`; `service_role`/backend only. 0030 also fixes a latent 0018/0021 defect
(`created_by` missing on `subscription_plans`/`salon_subscriptions`, which broke every write to
them through `set_audit_actor`), adds CHECKs on plan currency/interval/price (`NOT VALID`, then
validated when existing rows allow), and allows `semiannual`/`quarterly` intervals.

Billing statuses: `created -> authorized -> paid -> partially_refunded -> refunded`;
`failed`, `expired` are terminal for unpaid orders but **a late verified capture still moves them
to `paid`** (money was taken). `paid`-family never regresses (trigger).

## Activation, renewal, overlap (the SQL function)

`apply_subscription_billing_record(record, grace_days)`: serialised per salon (advisory lock +
row lock), refuses unless the record is `paid`/`partially_refunded`, returns `already_applied`
without changing anything when `applied_at` is set. Outcomes: `started`, `renewed`,
`already_applied`, `not_paid`, `blocked_suspended`, `blocked_closed`, `not_found`.

* A purchase while an `active`/`trialing`/`past_due`/`pending` row or a **cancelled-but-paid-through**
  row exists **extends that same row** (renewal): the new period starts at the existing
  `current_period_end` if it is still in the future, otherwise at `now()`. So
  `uq_salon_subscriptions_active_per_salon` is never fought and two overlapping active periods
  cannot exist. A cancelled row whose period ended, or an expired row, gets a **new** row.
* A different plan cannot be bought while a paid period runs (no proration invented): renew the
  same plan or wait for the end. After lapse any plan can be bought.
* `suspended` salons cannot start checkout; a payment that still lands is recorded as paid,
  **not applied**, and a `subscription_blocked` anomaly is raised for the operator. The same for a
  closed salon (`blocked_closed`).
* Grace is stored when a period is paid: `grace_period_end = period_end + SUBSCRIPTION_GRACE_DAYS`
  (the days are config with **no default**). `is_subscription_promotion_active` was extended so an
  `active` row whose period just ended keeps the benefit until its stored grace end. Admin rows with
  no stored grace are unchanged.
* `cancel_salon_subscription_renewal`: status `cancelled`, `cancelled_at` set (the admin cancel
  route now sets it too), paid-through access stays. Idempotent.
* `sweep_lapsed_subscriptions`: `active/trialing` past `current_period_end` -> `past_due` (grace
  still open) or `expired`; `past_due` past grace -> `expired`.
* `guard_subscription_admin` trusts these functions through `app.subscription_system` (never for
  `anon`/`authenticated`), so an owner's request can run them while direct owner writes still fail.

## Entitlement (backend-derived)

`derive_entitlement(...)` (domain, pure) mirrors the SQL function. It is the seam the later
trial/soft-lock work extends.

| State | Meaning | Benefit |
|---|---|---|
| `active` | inside a paid period | yes |
| `cancelled_paid_through` | renewal cancelled, period not over | yes |
| `grace` | period over, inside the stored grace window | yes |
| `expired` | nothing left | no |
| `suspended` | admin suspended | no |
| `none` | never purchased | no |

Expiry/lapse never blocks viewing history, handling refunds or cancelling; only the approved
premium benefit (promotion eligibility) is restricted. The API distinguishes **provider payment
verified** (`payment_verified`) from **backend entitlement applied** (`entitlement_applied`,
`entitlement_active`).

## Endpoints

See `docs/Salon-Owner-App-Backend-API-Document.md` (section "Subscription billing") for exact
JSON. Summary: `GET /v1/subscriptions/config`, `GET /v1/subscription-plans`,
`GET /v1/salons/me/subscription`, `POST /v1/salons/me/subscription/checkout` (Idempotency-Key),
`POST .../verify`, `POST .../cancel`, `GET .../payments`, `GET /v1/salons/me/access-state`.

## Webhooks

`POST /v1/webhooks/razorpay`, signed with `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET` (>= 32 chars,
separate from `RAZORPAY_WEBHOOK_SECRET`), verified over the raw bytes **before** parsing, deduped on
`X-Razorpay-Event-Id` in `payment_webhook_events` (scoped per provider), bounded body. Valid
unknown events are acknowledged 200 (`ignored`). Handled: `payment.captured`, `order.paid`,
`payment.failed`, `refund.processed`, `refund.failed`.

* captured/paid: matched to the billing row by order (then payment) reference; amount/currency in the
  event must equal the snapshot (else anomaly `subscription_amount_mismatch`, event `failed`, not
  retried); then the provider is **fetched** and the same settle path runs. If the provider does
  not show the payment yet, the event is retried with the existing backoff.
* failed: only remembers `failure_code`; the order stays payable (the payer may retry).
  Out-of-order failure after capture changes nothing.
* refund: re-reads the payment's absolute `amount_refunded` (monotonic), updates
  `refunded_amount`/status, raises an informational `subscription_refund` anomaly. **Remaining
  access is not revoked automatically** (policy decision, below).
* Booking (Cashfree) and subscription (Razorpay) events can arrive simultaneously: different
  secrets, different handlers, shared only the intake table (tested on real PostgreSQL).

Every successful activation also writes a normalised row to `subscription_events`
(`subscription_started` / `subscription_renewed`, reference `applied:<billing id>`; unique per
provider, so a replay is a no-op). No new retry columns were needed: retry state lives on the
intake row.

## Worker

`payment-webhook-worker` (same Compose service) now also runs, independently of the booking pass and
of HTTP, `reconcile_subscriptions_once`: settle stale open orders by fetching the provider, expire
unpaid ones (`expired`, or `failed` if an attempt failed), recover orders created but never
acknowledged (found by **receipt**), re-apply paid-but-unapplied rows, and sweep lapsed periods.
Failures are logged at ERROR with the stable prefix `ALERT subscription_billing` (alert on that);
there is still no worker health endpoint.

## Operator recovery

```sql
-- paid money not yet applied (blocked_*): needs a human
select b.id, b.salon_id, b.status, b.amount, b.paid_at, b.provider_payment_ref
from subscription_billing_records b where b.status in ('paid','partially_refunded') and b.applied_at is null;
-- anomalies (mismatch, duplicate payment, blocked, refunds, unused period at closure)
select kind, provider, provider_ref, salon_id, amount, detail, created_at
from payment_anomalies where kind like 'subscription\_%' and resolved_at is null order by created_at;
-- open orders stuck
select id, salon_id, status, provider_order_ref, expires_at from subscription_billing_records
where status in ('created','authorized') and updated_at < now() - interval '1 hour';
-- failed webhook events
select id, event_type, last_error_code, attempts from payment_webhook_events
where event_type = 'subscription' and processing_status = 'failed';
```

* Duplicate payment on one order / mismatch: refund the extra payment in the provider dashboard;
  the refund webhook updates the row. Nothing is extended twice.
* Blocked (suspended/closed): unsuspend and re-run `select apply_subscription_billing_record(id, <grace>)`
  or refund. A closed salon's payment is refunded by hand.
* Refunds of subscription payments are an **operator action** in the provider dashboard (the port has
  `refund(...)` and the adapter implements it, but no HTTP route exposes it).

## Account deletion / salon closure

See `ACCOUNT_DELETION.md`: an owner with a live paid subscription is blocked until they cancel
(unchanged contract, now also re-checked at confirm); closure then cancels renewal state, expires
open unpaid orders locally (the provider order cannot be cancelled), and flags any
paid-but-unused period as a `subscription_unused_period` anomaly for a refund decision.

## Configuration

`SUBSCRIPTION_PROVIDER` (`none` default | `razorpay`), `SUBSCRIPTION_RAZORPAY_KEY_ID`,
`SUBSCRIPTION_RAZORPAY_KEY_SECRET`, `SUBSCRIPTION_RAZORPAY_WEBHOOK_SECRET` (>= 32), `SUBSCRIPTION_GRACE_DAYS`
(**required when enabled, `0` allowed, no default**), `SUBSCRIPTION_ALLOW_LIVE` (required for
`rzp_live_` keys), `SUBSCRIPTION_ORDER_TTL_SECONDS` (3600), `SUBSCRIPTION_RECONCILE_AFTER_SECONDS` (600).
A missing credential, grace days, or a live key without the acknowledgement fails boot.
Webhook URL to register: `https://<api>/v1/webhooks/razorpay`, events `payment.captured`,
`order.paid`, `payment.failed`, `refund.processed`, `refund.failed`.

## Adding another subscription provider

Create `app/infrastructure/subscriptions/<name>.py` with `create_provider(settings)` returning a
`SubscriptionProvider`; add its credentials/validation to `config.py`. Nothing else changes. The
`test_decoupling_*` tests keep the provider name out of the core.

## UNVERIFIED against real Razorpay (confirm in test mode before any use)

Marked `# UNVERIFIED` in `infrastructure/subscriptions/razorpay.py`: `GET /orders?receipt=`
filtering (used to recover a timed-out order); the refund idempotency header name; webhook
signature hex encoding; auto-capture being the account setting; `order.paid` payload shape;
`amount_refunded`/`refund_status` fields on a payment; Orders `receipt` length (40) and `notes`
limits; webhook delivery/ordering behaviour. All behaviour is exercised only through fakes and
`httpx.MockTransport`.

Status: **BUILT, tested locally (fakes + real PostgreSQL 18), DORMANT, not sandbox-tested.**
