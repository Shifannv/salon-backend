# Payment integration: gap assessment and decision register

Status date: 2026-10-12. Providers: **Cashfree PG + Easy Split** for customer bookings,
**Razorpay** for owner subscriptions. Nothing here is enabled in production. Credentials, commercial
rules and store-policy eligibility are the owner's to supply; every unresolved rule is configuration
that fails closed (live activation refuses to start without it).

## Evidence levels used in this repo

| Level | Meaning |
|---|---|
| built | code exists |
| tested locally | unit tests against fakes / `httpx.MockTransport` |
| sandbox-tested | a real provider sandbox flow ran (none yet) |
| deployed | running in production (none of the payment code is) |

Mock tests are not sandbox evidence. Provider field names marked UNVERIFIED in code must be checked
against the provider sandbox before production.

## Gap assessment (verified against source)

1. `PaymentConfirmRequest` requires `order_ref`, `payment_ref` and `signature`: Razorpay-shaped. Cashfree
   returns no client signature, so confirmation must be a server-side status refresh.
2. Webhook routing supports one configured booking provider. Cashfree (bookings) and Razorpay
   (subscriptions) must run together with separate secrets and dedupe scoped by provider.
3. Commission is a percentage of each online payment, stored as an amount without its rate or base, and
   not reduced on refund. Commission on a full booking (deposit + cash balance) cannot be represented.
4. Subscription prices are floats in the API and domain layers; the database is `numeric(10,2)`.
5. Subscriptions are admin-only: no owner endpoints, no charge ledger, no provider-plan mapping, no
   index to resolve a provider event to a salon. A cancelled subscription still granting promotion can
   overlap a new active one.
6. Payment failure/expiry never releases a booking.
7. Overcollection: the capture is rolled back and **not recorded**; the row stays open and blocks new
   payments. Real money is unaccounted for.
8. Crash safety: payment intents, owner refunds and vendor registration call the provider before the
   local record is committed.
9. Bank account numbers are stored in plaintext (masked on read). Vendor registration sends only a
   legal name.
10. Account deletion erases provider references without cancelling a provider subscription or
    deactivating a vendor.
11. Docs disagree on whether migrations 0026/0027 ran on real Postgres (the 0025-0028 chain was applied
    to a throwaway PostgreSQL 18; no staging or production run).

## Decisions made for the initial build

| Topic | Decision | Why |
|---|---|---|
| Subscription mode | One-time Razorpay payment for a paid period with manual renewal; Razorpay Subscriptions (AutoPay) not enabled | No mandate/AFA compliance, no pre-debit notices, no dunning states for a first launch |
| Native subscription purchase | Disabled. Backend billing + a web purchase flow only | Apple 3.1.1 disallows an in-app purchase path to Razorpay; Google Play requires Play Billing for subscriptions that unlock in-app features unless an exemption applies |
| Commission | Configurable rate and base; **no default**. Live activation requires it to be set | Commercial rule not approved |
| Commission bearer | Deducted from the salon share; no customer surcharge | Documented initial model |
| Gateway fees / taxes | Recorded separately from platform commission | Provider fees must not be mistaken for commission |
| KYC data | PAN / bank details used once in memory for vendor creation; never persisted locally | Avoids a local KYC store and the encryption decision |
| Unpaid deposit bookings | Not released automatically until a payment deadline policy is approved | No approved policy |

## Decisions still needed from the business

- Commission percentage, calculation basis (full booking vs online amount), refund-time reversal.
- Who bears Cashfree PG fee, Easy Split fee (0.2% per split per Cashfree docs) and taxes.
- Settlement timing and whether vendor settlement is held until booking completion.
- Cancellation, no-show, rejection and refund policies; payment deadline for deposits.
- Subscription prices, benefits, grace period, cancellation policy.
- Treatment of QR, walk-in and salon-originated bookings.
- Whether Google Play India alternative billing or Apple in-app purchase will be adopted for owners.
- Cashfree Easy Split enablement and vendor KYC (PAN required; GSTIN above Rs 20 lakh per PAN).

## Provider facts to re-verify in sandbox (not confirmed from official pages)

Cashfree: the exact path of Get Payments, payment and refund webhook `type` names, `refund_splits`
schema, the per-order delayed-settlement field, `payment_session_id` lifetime, production activation.
Razorpay: signature hex encoding, `subscription.resumed`, per-instrument RBI limits.

## Stage 1 build status (2026-10-12)

"tested locally" = unit tests with fakes / MockTransport plus the opt-in PostgreSQL 18 integration tests.
**No item is sandbox-tested or deployed.**

| Gap | Status |
|---|---|
| 1 Razorpay-shaped confirm | built + tested locally: `payment_ref`/`signature` optional; `POST .../payments/refresh`; `confirmation` in config |
| 2 One webhook provider | built + tested locally: registry resolver, per-provider secrets, `subscription` domain recorded and ignored, dedupe per provider, bounded body |
| 3 Commission snapshot | built + tested locally (arithmetic, immutability trigger, reversal, earnings). Rate and base still have NO default; the business must decide them. Cash share carries no commission (to confirm) |
| 4 Float subscription prices | **stage 2: built + tested locally** (Decimal(10,2) in schemas/entities; DB CHECKs in 0030) |
| 5 Subscriptions | **stage 2: built + tested locally** (see "Stage 2 build status") |
| 6 Failure/expiry release | **not built**, documented; `PAYMENT_AUTO_RELEASE_ENABLED` is refused at boot |
| 7 Overcollection | built + tested locally incl. a real-PostgreSQL concurrent cash/online race; excess refundable; anomaly + ERROR log |
| 8 Crash safety | built + tested locally for intent, refund, vendor; Razorpay intents are not recoverable by id (provider-generated ids) |
| 9 Plaintext bank numbers / vendor KYC | vendor KYC never stored (built + tested); local plaintext payout account number is unchanged (still a gap) |
| 10 Deletion vs provider state | closure refunds use the row's provider; subscription wind-down built in stage 2 (renewal cancelled, orders expired, unused time flagged); vendor deactivation not built |
| 11 Migration evidence | 0026-0029 applied to a throwaway PostgreSQL 18 (chain, downgrade to 0020 and back, 0029 statements run twice); no staging/production |

New decisions made while building (challenge them):

| Topic | Decision |
|---|---|
| Cashfree order id | = our `intent_reference` (`pi_` + 32 hex), so recovery needs no extra state |
| Cashfree has no callback signature | `callback_signature` is not a capability; the SDK return is never proof; the app calls `/refresh` |
| Webhook replay window | 600 s default via `CASHFREE_WEBHOOK_TOLERANCE_SECONDS`; if Cashfree retries re-use the original timestamp, late retries are rejected and the reconcile loop covers them (UNVERIFIED) |
| Overcollection | record and flag; refund the excess first; excess refunds neither reverse commission nor unpay the booking |
| Commission on cash | none (platform never holds cash); with `booking_total` this under-collects |
| Re-registration | new vendor id per generation; account is `pending` (not payable) until `active` again |
| Registration idempotency | fingerprint excludes KYC values (low-entropy data must not be derivable from a hash) |
| Live guard | `PAYMENT_ALLOW_LIVE` must be true for Cashfree production or `rzp_live_` keys |

Unverified Cashfree items (all marked in code): payments-list path, payment/refund/vendor/settlement webhook
type names and payload keys, `x-webhook-timestamp` unit, `refund_splits` schema (off), create-vendor body
and initial status, "already exists" HTTP status (409), minimum order expiry, `payment_group` values,
`x-webhook-version` values.

## Stage 2 build status (owner subscription billing, 2026-10-13)

Same evidence levels. **Everything below is tested locally** (fakes, `httpx.MockTransport`, and real
PostgreSQL 18 for the SQL) and **none is sandbox-tested, deployed or enabled** (`SUBSCRIPTION_PROVIDER=none`).

| Item | Status |
|---|---|
| Config: separate keys, >= 32-char webhook secret, explicit grace days (0 allowed), live-key acknowledgement | built + tested |
| `SubscriptionProvider` port + `infrastructure/subscriptions/razorpay.py` (one deletable file) + null provider + resolver | built + tested |
| Migration 0030 (billing ledger, atomic idempotent activation, cancel, sweep, plan CHECKs, `created_by` fix) and 0031 (plan seed) | built; run on a throwaway PostgreSQL 18 (upgrade twice, downgrade/upgrade, statements re-applied) |
| Owner endpoints (config, plans, state, checkout, verify, cancel, history, access-state) | built + tested |
| Webhook handling (captured / order.paid / failed / refund), dedupe, forged signature, out-of-order | built + tested (real PostgreSQL) |
| Reconciliation + lapse sweep in `payment-webhook-worker` | built + tested; no worker health endpoint |
| Account-deletion wind-down + confirm-time blocker re-check | built + tested |
| Recurring (AutoPay), proration/plan change, automatic refund/revocation, GST | NOT built |

Decisions made while building (challenge them):

| Topic | Decision |
|---|---|
| Plan prices / intervals | Growth 349/1,499/1,999, Premium 599/2,499/3,499 for 1/6/12 months, as supplied; `tax_inclusive` NULL = undecided. Premium `ranking_weight` 1 vs Growth 0 is a placeholder ordering, admin-editable |
| Overlap | A purchase while a paid, cancelled-but-paid-through or past-due period exists extends the SAME `salon_subscriptions` row from `max(now, period_end)`; no second active row |
| Plan change | Refused while a paid period runs (no proration invented); allowed after lapse |
| One open order | One `created`/`authorized` purchase per salon (DB-enforced); a second checkout of the same plan resumes it, another plan gets 409 |
| Failed attempt | `payment.failed` does not close the order (payer may retry); only expiry sweeps close it as `failed`/`expired` |
| Late capture | A verified capture on an `expired`/`failed` local row is still applied (money was taken) unless the salon is suspended/closed (held + anomaly) |
| Proof | Webhooks and client results only TRIGGER a provider fetch; money is applied only from a fetched captured payment on this order with equal amount and currency |
| Refunds | Operator action in the provider dashboard; a refund updates `refunded_amount`/status but does NOT shorten or revoke access (policy needed) |
| Grace | Stored per paid period (`period_end + SUBSCRIPTION_GRACE_DAYS`); `is_subscription_promotion_active` honours it for `active` rows |
| Cancellation | Sets `cancelled` + `cancelled_at`, keeps paid-through access, idempotent, never needs the provider |
| Deletion | Live subscription blocks (existing contract, re-checked at confirm); cancel clears it; unused paid time is flagged, not refunded automatically |
| Alembic ids | `0030_subscription_billing` (the full descriptive id is 33 chars; `alembic_version.version_num` is varchar(32)) |
