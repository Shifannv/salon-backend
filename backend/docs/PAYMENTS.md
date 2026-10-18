# Payments

## Provider-independent continuation (2026-10-18)

The [mock implementation report](verification/provider-agnostic-mock-results-2026-10-18.md)
describes the five provider ports, isolated `FakeProvider`, separate fee/reference
observations and remaining account-dependent verification. Cashfree is unavailable
until an account exists and its capabilities are verified; mock results never
verify settlement. The [current specification](verification/payment-subscription-booking-spec.md)
distinguishes approved targets from pending policy decisions and supersedes
conflicting historical assumptions below. No migration or provider is enabled.

Customer payment collection foundation. **Provider-agnostic core, dormant by default.**
`PAYMENT_PROVIDER=none` ships as the default: no money moves, no webhook route exists, and
choosing a provider later means adding credentials and (for a provider other than the
bundled reference adapter) one adapter file.

## Status: built / dormant / not built

**Built and unit-tested (no live Postgres, no live provider):**

- Migration `0026_booking_payments`: ledger `booking_payments`, `payment_refunds`,
  `payment_webhook_events`, `payment_idempotency_keys`, `payment_provider_accounts`;
  `bookings.currency/deposit_amount/paid_amount/refunded_amount`; widened
  `payment_preference` CHECK; `recompute_booking_payment_state` + triggers.
- Port `PaymentGateway`, `NullPaymentGateway`, resolver, and a complete reference adapter
  for Razorpay (`app/infrastructure/payments/razorpay.py`, one deletable file).
- Endpoints, use cases, repository, webhook route, retry/reconcile worker, Compose service.
- The existing manual receipt (`POST /v1/bookings/{id}/payment`) writes a ledger row.

**Dormant pending credentials/decisions:**

- Everything that talks to a provider. With `PAYMENT_PROVIDER=none`:
  `GET /v1/payments/config` -> 200 `enabled:false`; every money POST -> 503
  `payment_provider_not_configured`; `/v1/webhooks/{provider}` -> 404.
- The Razorpay adapter has only been exercised through `httpx.MockTransport`. Field names
  follow the provider's documentation and are **unverified against a sandbox**.

**Not built:**

- Model (B): customers paying each salon's own provider account (needs a per-salon
  credential vault). `PAYMENT_SETTLEMENT_MODEL=direct_to_salon` is refused at boot.
- Any platform-held disbursement. Collecting into the platform's own account and paying
  salons out is a licensed activity in India (RBI PA/PG directions) and is deliberately not
  implemented. The only supported "platform collects" form is provider-side split
  settlement (funds stay in the provider's escrow and the provider splits at source).
- Customer/owner push notifications on online capture or refund (the manual path still
  notifies).
- Provider fee and tax capture (columns exist, unpopulated), automatic booking release.
- Authorise-then-capture flows (the adapter assumes provider auto-capture).
- Payment-failure UI contract beyond the ledger fields (`instrument`, `failure_code`).

## Design rules

1. **The ledger is the source of truth.** `booking_payments` holds money. Booking columns
   `payment_status`, `payment_method`, `paid_amount`, `refunded_amount` are a *derived
   cache* written only by `recompute_booking_payment_state` (a trigger on the booking
   columns raises `booking_payment_columns_are_derived` for anyone else).
2. **Enums are not widened.** `payment_status` stays `unpaid|paid`, `payment_method`
   `cash|online`. Richer state is derived in responses as `payment_state`
   (`unpaid|partially_paid|paid|refunded`); the real instrument lives on the ledger row.
   New status columns are `text` + `CHECK`.
3. **Amounts never leave Postgres.** `create_booking` computes `total_price`;
   `deposit_amount` is derived in SQL from `total_price * PAYMENT_ADVANCE_PERCENT / 100`.
   Intent amounts are read from the booking; clients never send one (only an optional
   partial-refund amount, bounded in SQL by the captured payment).
4. **Idempotency is DB-backed** (`payment_idempotency_keys`, 24h, sha256 request
   fingerprint). Redis is unusable here: 60 s TTL and a silent no-op without `REDIS_URL`.
   Every money-mutating POST requires `Idempotency-Key` (8-200 chars). Same key + same
   body replays the stored response; same key + different body -> 409
   `idempotency_key_reuse`.
5. **Shared webhook intake, separate domain logs.** One `POST /v1/webhooks/{provider}` and
   one `payment_webhook_events` table for all providers. `subscription_events` remains the
   subscription domain log; see `SUBSCRIPTIONS.md`.
6. **One resolver seam.** `PaymentGatewayResolver.resolve(salon_id)` is the only place that
   reads `payment_provider`/`payment_settlement_model`. A future per-salon gateway is a
   different adapter *instance* returned here, not a different call site.

## Endpoints

| Method and path | Who | Notes |
|---|---|---|
| `GET /v1/payments/config` | anyone | Always 200. `enabled:false` when unconfigured. Replaces the customer app's hardcoded "UPI is not available yet". |
| `POST /v1/bookings/{id}/payments/intent` | customer (own booking) | `Idempotency-Key`. Optional `{purpose}`. Amount server-derived. 409 if one open intent exists. |
| `POST /v1/bookings/{id}/payments/confirm` | customer | `Idempotency-Key`. Verifies callback signature, then asks the provider for the amount. Mismatch fails the row, never marks paid. |
| `POST /v1/bookings/{id}/payments/cancel` | customer | `Idempotency-Key`. Cancels the open intent. |
| `GET /v1/bookings/{id}/payments` | customer or salon | Ledger, refunds, derived `payment_state`. |
| `POST /v1/bookings/{id}/payments/{payment_id}/refund` | owner | `Idempotency-Key`. Online payments only; cash is settled with the customer. Provider refund key is deterministic. |
| `GET /v1/salons/me/earnings` | owner | Ledger-derived totals. |
| `GET /v1/salons/me/settlement-account` | owner | Payee account state (model A). |
| `POST /v1/salons/me/settlement-account/register` | owner | `Idempotency-Key`. Needs saved payout details. |
| `GET /v1/salons/me/payout-account/history` | owner | Payout change audit trail (see `PAYOUT_ACCOUNTS.md`). |
| `POST /v1/webhooks/{provider}` | provider | No auth; registered only when a provider is configured. |
| `POST /v1/bookings/{id}/payment` | owner/staff | Unchanged contract; now writes a manual ledger row. New 409 `payment_in_progress` while an online intent is open. |

`BookingCreateRequest.payment_preference` now accepts `pay_at_salon|pay_advance|pay_full`.
`BookingResponse` gains `currency`, `deposit_amount`, `paid_amount`, `refunded_amount`,
`payment_state` (additive). `POST /v1/booking-action-requests/{id}/respond` accepts an
optional `payment_method` (default `cash`), fixing the old hardcoded `'cash'`.

## Webhook handling

1. Reject bodies over `PAYMENT_WEBHOOK_MAX_BODY_BYTES` (413).
2. Verify the signature over the **raw bytes before any parse** (400, nothing stored).
3. Normalise; unknown events are stored `ignored` and answered **200** (a 4xx makes
   providers disable the hook).
4. `insert ... on conflict do nothing` is the replay gate; commit; answer 200.
5. Process in a background task; `payment-webhook-worker` retries anything that failed or
   was left `processing` (exponential backoff, capped at `PAYMENT_WEBHOOK_MAX_ATTEMPTS`).
6. Out-of-order (lower-rank) events are ignored. A *late capture* after a row expired is
   deliberately accepted: money really moved.
7. Amount/currency mismatch fails the ledger row (`failure_code=amount_mismatch`), fails the
   event without retry, logs at ERROR, and never marks the booking paid.

The worker's second pass calls `fetch_payment` for open intents older than
`PAYMENT_RECONCILE_AFTER_SECONDS`, the only defence against a lost webhook; intents past
`expires_at` with no provider payment are marked `expired`.

## Operational landmines

- **Over-collection is recorded, loudly** (since migration 0029; see "Overcollection" below). Only a
  manual cash receipt that would exceed the total is still refused (`payment_overcollection`,
  SQLSTATE 23514).
- `stamp_booking_lifecycle` stamps `payment_recorded_by` from `auth.uid()`, which is NULL on
  the worker session. Gateway attribution therefore lives on `booking_payments.recorded_by`
  and the recompute sets `payment_recorded_at` itself.
- A manual receipt while an online intent is open is refused (409 `payment_in_progress`).
- Downgrading `0026` destroys the ledger.

## Configuration

See `.env.example`. `validate_payment_settings` fails boot in **every** environment for:
unknown provider; `direct_to_salon`; missing provider credentials; `platform_collect`
without the provider's split-settlement feature enabled.

## Verification status (be honest)

- Unit tests cover config rules, the dormant 503 path, webhook intake (forged, replayed, stale, simultaneous
  providers), signatures, status mapping, request shapes, timeouts, commission arithmetic, refund reversal,
  overcollection, crash/timeout recovery for intents, refunds and vendor registration, and authorization.
- `tests/integration/test_payment_ledger_sql.py` (opt-in: `MIGRATION_TEST_DB=postgresql://.../postgres` on a
  disposable local server) runs the real Alembic chain to 0029 and exercises the ledger SQL, triggers and
  locking on PostgreSQL 18, including a concurrent cash receipt versus an online capture.
- **Not verified:** any staging or production database, RLS as an application role, and every real provider
  call (Razorpay and Cashfree are mock-tested only).

## Adding another provider

1. Add `app/infrastructure/payments/<name>.py` with a `create_gateway(settings)` factory.
2. Add its credentials to `Settings` and `validate_payment_settings`.
3. Set `PAYMENT_PROVIDER=<name>`. No core, schema, or app change.

---

# Stage 1 additions (Cashfree, multi-provider routing, monetary policy)

## Evidence levels

| Level | Meaning | Stage 1 status |
|---|---|---|
| built | code exists | everything below |
| tested locally | unit tests with fakes / `httpx.MockTransport`, plus `tests/integration/test_payment_ledger_sql.py` against a throwaway PostgreSQL 18 | everything below |
| sandbox-tested | a real provider sandbox flow ran | **none** |
| deployed | running in production | **none** |

Every Cashfree field name marked `# UNVERIFIED: confirm in Cashfree sandbox` in
`app/infrastructure/payments/cashfree.py` must be checked in the sandbox first. Mock tests are not sandbox evidence.

## Providers and configuration

`PAYMENT_PROVIDER` is `none` (default, dormant), `razorpay` or `cashfree`. Cashfree needs
`CASHFREE_CLIENT_ID`, `CASHFREE_CLIENT_SECRET`, `CASHFREE_EASY_SPLIT_ENABLED=true` (platform_collect) and,
for production, `CASHFREE_ENVIRONMENT=production` **and** `PAYMENT_ALLOW_LIVE=true`. A real provider with
platform_collect also refuses to boot without `PAYMENT_PLATFORM_FEE_PERCENT` and `PAYMENT_COMMISSION_BASE`
(no default exists). `PAYMENT_AUTO_RELEASE_ENABLED=true` is refused: it is not built.

## Gateway registry and webhook routing

`PaymentGatewayResolver` keeps gateways by provider name: `resolve()` = the gateway for NEW payments;
`for_provider(name)` = the gateway that HOLDS an existing row. Refunds, confirmations, refresh,
reconciliation and closure refunds always use the row's own provider and never fall back to the configured
one (a provider that is not enabled is refused with 503, not substituted).

`POST /v1/webhooks/{provider}` exists when a payment provider is configured or `SUBSCRIPTION_PROVIDER` is
enabled (subscription billing: see `SUBSCRIPTIONS.md`, "Owner billing (stage 2)"). It accepts a provider only if it is independently enabled (404 otherwise), reads a bounded body
(413), verifies the signature with that provider's own secret/algorithm over the raw bytes before parsing
(400, nothing stored), and dedupes by `(provider_name, provider_event_reference)`.
A body signed with the subscription secret is the `subscription` domain: parsed by the SEPARATE
`SubscriptionProvider` port, stored with `event_type = 'subscription'` (`received`, or `ignored` for an
unknown kind) and applied by the subscription billing handler (see `SUBSCRIPTIONS.md`); it never touches
booking money. Event kinds: payment, refund, vendor
(account), settlement (failed/reversed become `payment_anomalies`), subscription (applied by the billing handler),
unknown valid events (acknowledged 200). Stored payloads contain identifiers, amounts and sanitised codes only.

Cashfree specifics: signature = Base64(HMAC-SHA256(client_secret, timestamp + raw body)) (base64, not hex),
`x-webhook-timestamp` must be within `CASHFREE_WEBHOOK_TOLERANCE_SECONDS` (default 86400, the maximum) of now. The window is wide on purpose: Cashfree retries for a long time and may reuse the original timestamp, and replays are already stopped by the HMAC plus per-provider event-id dedupe. Payment event
references are `TYPE:cf_payment_id` (state is monotone, so a repeat is a true duplicate); vendor and
settlement references hash the body (a vendor flipping back to a prior status is a new event).

## Confirmation contract

* `POST /v1/bookings/{id}/payments/refresh` `{order_ref}` (new): the backend asks the provider for the order's
  payments and applies them. Works for every provider; nothing the client sends is trusted.
* `POST /v1/bookings/{id}/payments/confirm`: `payment_ref`/`signature` are now optional. A provider with a
  signed client callback (Razorpay) still requires and verifies them; a provider without one (Cashfree, its
  SDK callback is not proof) treats the call as a refresh and ignores the supplied values.
* `GET /v1/payments/config` gains `confirmation: "callback" | "refresh"` so the app knows which to call.
* Only the booking's customer may call either (others get 404), `Idempotency-Key` is required, the lock on the
  booking is not held while the provider is called.

## Commission snapshot (migration 0029)

At intent time the backend writes on the ledger row: `commission_rate_percent`, `commission_base`
(`online_amount` | `booking_total`), `platform_commission_amount` and `commission_policy_version`, computed from
configuration and the booking row (never client input). A trigger forbids changing them afterwards.
`online_amount`: rate x this payment. `booking_total`: rate x the booking total, allocated across the booking's
online payments (never above the total, never above the payment). Cash received at the salon carries no
commission because the platform never holds that money, so with `booking_total` the commission on a cash-paid
share is not collected (a business decision to confirm). A refund records `commission_reversal_amount`
(proportional; the refund that exhausts the payment reverses exactly the remainder). `GET /v1/salons/me/earnings`
reads only the snapshot and reversals. Provider fees/taxes live in separate nullable columns
(`provider_fee_amount`, `provider_tax_amount`), never mixed with commission and **not populated yet**.
The legacy `platform_fee_amount` column is kept (backfilled into the new column) and no longer used.

## Overcollection

When an online capture exceeds what the booking is still owed (cash recorded first, or a second online
payment), the capture is recorded: `booking_payments.overcollected_amount` holds the excess, the booking's
`paid_amount` excludes it (never paid twice), an ERROR `OVERCOLLECTION ...` is logged, a
`payment_anomalies` row is written, and the row leaves the open set so the reconcile loop stops. The owner
refunds the excess with the normal refund API: omitting `amount` refunds the excess first; refunding more
than the excess while excess remains is refused with 422; an excess refund reverses no commission and does not
unpay the booking. Cash recorded after an online capture is still refused by the database. The database
serialises the cash receipt and the capture on the booking row lock (verified on PostgreSQL).

## Crash safety

Identity first, commit, then the provider call; no lock or transaction is held across a remote call.

| Operation | Persisted before the call | Unknown outcome (timeout / 5xx) | Definitive 4xx |
|---|---|---|---|
| Create intent | row + deterministic `order_ref` (Cashfree: the `intent_reference`) | one lookup by that id; else the row stays open and unacknowledged (`provider_order_confirmed_at` null), the idempotency key is released, a retry of the same booking/purpose/amount resumes it, and the worker reconciles by order id (recovers a payment the provider took) | row `failed`, booking freed |
| Owner refund | `payment_refunds` row with deterministic `refund_ref` | row stays `created` (reserves the amount); a retry with the same key re-sends the same provider refund id; the worker resolves it by that id | row `failed`, amount freed |
| Vendor registration | `payment_provider_accounts` row, vendor id, status `pending` | stays `pending`; retry reuses the same vendor id (idempotent at the provider) | `needs_action` + audit row |

Limitation: Razorpay order ids are provider-generated, so a timeout there cannot be recovered by id; the row
expires after `PAYMENT_INTENT_TTL_SECONDS` (an orphan unpaid order is harmless; a paid-but-unmatched one is
an `unmatched` webhook for a human).

## Vendor onboarding

`POST /v1/salons/me/settlement-account/register` takes contact, PAN, account/business type and bank
(account number + IFSC) or UPI. The values are used once in memory, never persisted, logged, echoed in 422s
(the scrubbing now covers this path as it does `/payout-account`) or returned. The idempotency fingerprint
deliberately excludes them. Only vendor id, status and canned requirement text are stored. States:
`not_started | pending | needs_action | active | rejected | suspended`. Re-registering from any non-pending
status starts a new generation (new vendor id), resets the account to `pending` (the salon cannot take online
payments until the provider reports `active` again) and writes `payment_provider_account_audit`. The old
vendor is not deleted at the provider (manual clean-up). Status changes from webhooks are audited too.

## Order failure / expiry

Not built. A failed or expired payment leaves the booking as it was; nothing releases it
(`PAYMENT_AUTO_RELEASE_ENABLED` is refused at boot). It needs an approved deadline policy first.

## Known gaps (stage 1)

Provider fee/tax capture; automatic booking release; Razorpay order recovery by receipt; `refund_splits`
(off, schema unverified); deletion of superseded vendors; commission on cash; real Postgres/provider runs on
staging; sandbox verification of every `UNVERIFIED` Cashfree item.
