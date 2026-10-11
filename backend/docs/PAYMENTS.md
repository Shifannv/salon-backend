# Payments

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
- Commission policy beyond a flat `PAYMENT_PLATFORM_FEE_PERCENT` recorded per payment.
- Customer/owner push notifications on online capture or refund (the manual path still
  notifies).
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

- **Over-collection is refused, loudly.** If cash and an online capture both land,
  `recompute_booking_payment_state` raises `payment_overcollection` (SQLSTATE 23514). The
  capture event goes to `failed` (not retried). A human issues a refund. This is deliberate;
  see `RUNBOOK.md`.
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

- 585 unit tests pass; they cover the config rules, dormant 503 path, replayed webhook,
  bad signature writing nothing, amount mismatch, idempotency replay/mismatch, HMAC vectors,
  paise rounding, worker claim/backoff SQL shape, migration SQL shape, and the decoupling
  rule (the provider's name appears only in its adapter and `config.py`).
- **Not verified against a real Postgres:** migrations `0026`/`0027`, the recompute
  function, triggers, RLS, and every raw SQL statement's runtime behaviour. No disposable
  database was available (a local server was listening but rejected the default
  credentials). Run `alembic upgrade head` on staging, then the opt-in integration tests,
  before any app build depends on this.
- **Not verified against a real provider.**

## Adding another provider

1. Add `app/infrastructure/payments/<name>.py` with a `create_gateway(settings)` factory.
2. Add its credentials to `Settings` and `validate_payment_settings`.
3. Set `PAYMENT_PROVIDER=<name>`. No core, schema, or app change.
