# Account Deletion

Permanent, self-service deletion for **customer** and **owner** accounts. One trusted
backend workflow serves both mobile apps and the public deletion web page. Clients never
hold service-role credentials and never pick which account is deleted: the account is the
verified JWT `sub`.

Status: implemented; SQL **verified against a throwaway PostgreSQL 18** with the full
migration chain (`tests/integration/test_account_deletion_sql.py`, opt-in via
`ACCOUNT_DELETION_TEST_DB`). **Not staging-tested, not production-verified**, and the
refund path has only ever run against a fake gateway (no payment provider is configured).

Owner decisions this design implements: the salon becomes an **anonymised shell** (other
customers keep their booking history); there is **no grace period**; an owner's **future
bookings are cancelled and refunded**, they do not block deletion.

## Flow

1. `POST /v1/account/deletion/challenges` - sends a one-time code through Supabase Auth to
   the account's own **provider-verified** email or phone (looked up server-side with the
   service role, never taken from the request). `contact` is optional; if sent it must match.
   For an owner the 202 also carries `bookings_to_cancel` - how many upcoming bookings
   confirming will cancel - so the app can say so before the user commits.
2. `POST /v1/account/deletion/challenges/{id}/verify` - Supabase verifies the code; the
   backend asserts the returned user id equals the JWT `sub`, discards the provider session,
   and returns a one-time `confirmation_token`. **Nothing is deleted yet.**
3. `POST /v1/account/deletion` with `confirm: "DELETE"` - atomically locks the account and
   queues erasure. The JWT stops working immediately (`profiles.is_active = false`) and the
   owner's salons are deactivated, so no new booking can be made.
4. `GET /v1/account/deletion/{request_id}` with header `X-Status-Token` - progress. The JWT is
   dead after step 3, so this uses the token returned in step 3 (a header, so it stays out of
   access logs). The token is an HMAC derived from the secret and the request id; it does not
   expire and remains usable as long as the deletion request row exists (retained indefinitely).
   A wrong token or unknown request id both return 404 with no differentiation.
   The response has `status` (`pending|processing|completed|failed`) and a coarse `stage`:
   `queued -> refunding -> waiting_for_refunds -> erasing -> completed` (owners; customers
   go `queued -> erasing -> completed`). While refunds settle `status` stays `pending`
   (not `failed`) and `stage` is `waiting_for_refunds`.

Challenge guarantees: bound to user + purpose + channel + contact hash; HMAC-only storage
(no plaintext OTP or tokens); 10 min expiry; 5 attempts total (resends do not reset them);
60 s resend cooldown; 3 resends; 5 challenges/hour; single use; DB-enforced (Redis limiting
fails open so is not relied on). Errors: 400 `invalid_verification_code`, 404 for another
user's challenge, 409 `deletion_blocked`, 422 `contact_mismatch`, 429, 503 if
`ACCOUNT_DELETION_SECRET` is unset outside local/test.

## Blockers (409 `deletion_blocked`)

An **owner's open bookings and pending requests no longer block anything** - the worker
cancels, notifies, resolves and refunds them (next section). What still blocks:

| Account | Blocker | `details` key |
|---|---|---|
| Customer | pending/confirmed bookings ending in the future | `open_bookings` |
| Customer | their own pending booking-action requests | `pending_requests` |
| Owner | an active/trialing/past-due subscription **and** `SUBSCRIPTION_PROVIDER != none` (challenge start **and again at confirm**, so a subscription bought in between cannot bypass it) | `active_subscriptions` |

A customer resolves their own bookings through the normal cancel flow, then retries.
(Cancelling a customer's own future bookings on their behalf was not requested and is not
done.) A refund in flight is never a blocker. The customer checks run at challenge start and
again inside the confirm transaction. The owner subscription check runs at challenge start and
is repeated in the confirm use case (stage 2: a purchase made after the challenge started must not
slip through). Cancelling the subscription (`POST /v1/salons/me/subscription/cancel`, paid-through access
remains) clears the blocker; it is a `cancelled` row, not an active one.

```json
{
  "error": {
    "code": "deletion_blocked",
    "message": "Cancel your upcoming bookings and resolve pending requests before deleting your account",
    "details": { "open_bookings": 2, "pending_requests": 1 }
  }
}
```

Only non-zero counts are included. A booking with status `pending` (awaiting salon approval)
counts as open for a customer.

## Account lock and session revocation

At confirm time the following happen **atomically** in a single transaction:

- `profiles.is_active = false` (and the owner's salons `is_active = false`, staff deactivated)
- `device_tokens` and `notifications` for the user are deleted
- An `account_deletion_requests` row is created (the 202 carries its id and status token)

**Immediate API lock**: `get_current_actor` checks `is_active` on every authenticated
request. As soon as the transaction commits the user's JWT returns 401 on every backend
endpoint, including `GET /v1/auth/me`. This is immediate, not eventual.

**Supabase session revocation**: The Supabase Auth session/refresh-token is only revoked
in the worker's first destructive step (ban + eventual delete). Between confirm and the worker
claiming the job the user could theoretically refresh their Supabase token through Supabase's
own auth endpoints. All backend routes are blocked by the profile check, so this window
carries no practical risk for this API. If the app calls `signOut` locally the session
is also terminated on the client side.

**Re-registration**: After the Supabase Auth identity is hard-deleted by the worker, a
new sign-up with the same email or phone creates a brand-new identity (new UUID, new
profile, no link to prior history). The anonymized booking records do not re-associate.
No re-registration block is enforced; this is the expected product behaviour.

Prepared Mumbai reconciliation (not migrated/deployed): revision 0038 adopts the legacy
`bookings.cancellation_reason_code` and `cancellation_reason_text` nullable text columns.
Both are potentially personal content and are cleared to NULL on customer deletion
(their bookings) and owner deletion (all bookings in their salons), before profile
references detach. No arbitrary value is retained as a legal/audit code. Booking records
and amounts remain. The adapter change requires these columns before deployment.
See [forward reconciliation](migrations/MUMBAI_FORWARD_RECONCILIATION.md) for source/runtime proof,
non-destructive rollback and the separate execution/stamp gates.

**Confirm idempotency**: If the network swallows the 202 and the client retries, the
account is already locked so `get_current_actor` returns 401 before the route handler
runs. The app treats that 401 as confirmation that deletion was accepted and the response
was lost. If, in the rare case of a concurrent second request racing inside the lock
window, the repository returns the existing request row and the same status token is
recomputed deterministically - no second deletion is ever queued.

## Erasure (worker `account-deletion-worker`)

Durable outbox in `account_deletion_requests`; claimed with `FOR UPDATE SKIP LOCKED`,
stale claims are re-taken after 10 min, backoff 30 s doubling to 1 h, every step idempotent
and recorded as a boolean key in `step_state`. A failed request is retried and the account is
never reactivated; completion is never claimed early.

Order (**lock -> cancel -> notify -> refund -> settle -> erase**):

| # | `step_state` key | Who | What |
|---|---|---|---|
| 0 | - | confirm (API) | **lock**: account + salons inactive, request queued |
| 1 | `bookings_cancelled` | owner | **cancel + notify**, one transaction: every `pending`/`confirmed` booking with `end_datetime > now()` at the owner's salons becomes `cancelled` with `cancellation_reason = 'salon_closed'`; every open booking-action request at those salons is resolved (`invalidated`); never-attempted checkout intents are cancelled; each customer with an account gets a `booking_cancelled` notification + push-outbox row with fixed copy that names no one |
| 2 | `refunds_issued` | owner | **refund** every captured **online** payment on those bookings through the `PaymentGateway` port |
| 3 | `refunds_settled` | owner | **settle**: wait until no closure refund is still `created` |
| 4 | `auth_banned` | all | ban the user and the owner's staff logins |
| 5 | `db_erased` | all | one SQL transaction (below) |
| 6 | `media_deleted` | all | delete R2 objects under `avatars/`, `salon-images/`, `staff-photos/` unless still referenced |
| 7 | `cache_cleared` | all | Redis (below); failures now surface |
| 8 | `auth_deleted` | all | hard-delete the Supabase Auth user |
| 9 | `staff_auth_deleted` | owner | hard-delete the Auth identity of every staff login whose profile was deleted in 5 |
| - | - | all | verify (profile row and auth user absent) -> `complete_request` |

Nothing destructive (steps 4-9) starts before steps 1-3 are done.

**Cancellation copy** (never names the owner, salon or staff):
`This salon has closed, so your booking has been cancelled.` plus, when applicable,
` Any online payment you made will be refunded to your original payment method.` and/or
` A payment you made directly to the salon is not refunded by the platform.`
Walk-in bookings without an account are cancelled but cannot be notified.

**Refunds.** Only `channel = 'gateway'` payments in `captured`/`partially_refunded` with a
`payment_ref` are refunded, for the amount not already refunded. Cash / manually recorded
payments are the salon's money: the platform never refunds them and the notice says so. Each
payment gets exactly one `payment_refunds` row with `idempotency_key = 'salon_closed'`
(`unique (payment_id, idempotency_key)`), inserted *before* the provider is called, and the
provider is called with the deterministic key `sha256("<payment_id>:salon_closed")[:40]` -
so a crash, retry or second worker can never refund twice. A refund that already holds a
provider reference is never re-sent.

**Settling and failure policy.** Every refund still `created` re-queues the request
(`status = 'pending'`, `last_error_code = 'refunds_pending'`) with the usual backoff - a
refund in flight is *not* a failure and never blocks deletion. The provider's refund webhook
moves it to `processed`/`failed`. After `ACCOUNT_DELETION_REFUND_MAX_ATTEMPTS` worker claims
(default 8, about 3 hours of backoff) the right to erasure outranks reconciliation and
erasure **proceeds**:

- a refund the provider rejected (`failed`) or that could not be sent (`failure_code =
  refund_call_failed`, or `provider_unavailable` when no refund-capable provider is
  configured) is recorded in `payment_refunds` with `status = 'failed'` and logged at ERROR;
- a refund still `created` at the cap is left `created` (it may yet settle and the webhook
  can still reconcile it - marking it failed could cause a double refund) and logged at ERROR
  with its id.

Both need a human: see RUNBOOK.md ("Failed closure refunds").

**`PAYMENT_PROVIDER=none`.** No online payment can exist, so the candidate list is empty and
`refunds_issued`/`refunds_settled` are recorded as done without any provider call.

**Worker start-up checks.** The worker refuses to start (exit 1, CRITICAL log) when Supabase
admin credentials are missing, when object storage is not fully configured outside
local/test (a partial R2 config is refused everywhere), or when a configured payment provider
cannot initialise. Previously a missing `R2_BUCKET` was found *after* the database was
erased and the request retried the media step for ever. If Redis is configured but
unreachable the worker pauses (no destructive step starts; the heartbeat goes stale).

**Healthcheck.** The worker touches a heartbeat file after every poll cycle and finished
request; the Compose healthcheck (`python -m app.infrastructure.account_deletion.health`)
fails when it is older than `max(180, 6 * poll + 60)` seconds. A dead or wedged worker now
shows `unhealthy` in `docker compose ps` instead of silently leaving locked accounts intact.

**Completion notification**: Sending a confirmation email or SMS to the user on completion
is **not yet implemented**. The status endpoint and the app's local sign-out flow are the
only feedback mechanisms today.

## What the database erasure does (step 5, one transaction, re-runnable)

Everything runs inside `erase_database`, with the `app.account_erasure` audit bypass. Every
statement is an update-to-fixed-value or a delete, so a repeat is a no-op.

**Anyone (customer or owner)**
- delete the user's `notifications` (cascades `notification_outbox`/`notification_deliveries`)
  and `device_tokens`; delete `salon_reports` they filed;
- **other people's** `notifications` about this person's bookings (an owner's "X booked")
  lose title/body/data (title becomes `Booking update`) and their delivery/outbox error text;
- the person's bookings: `customer_name = 'Deleted customer'`; `customer_phone`, `notes`,
  `rejection_reason`, `cancellation_reason` cleared (a rejected booking keeps the placeholder
  `Removed` because a CHECK requires a reason; the system code `salon_closed` is kept);
- `booking_action_requests`: the person's free-text `reason` and any `decision_reason` on their
  bookings cleared (a declined decision keeps `Removed`, required by a CHECK);
- `booking_payments.payer_id` / `recorded_by` set NULL - **amounts, ids and provider
  references are retained** (financial record);
- `payment_idempotency_keys` for the user deleted (they cache full response bodies);
- every audit/actor column referencing the profile nulled (`erase_profile_references`, which
  as of 0028 also covers `ON DELETE RESTRICT` keys), then the `profiles` row deleted.

**Owner, additionally** (the salon is only *deactivated*, never deleted, so `ON DELETE
CASCADE` never fires and each table is emptied explicitly):
- deleted: `salon_images`, `salon_holidays`, `blocked_slots`, `salon_payout_accounts`,
  `salon_payout_account_history` (holder name, UPI, bank/IFSC snapshots),
  `subscription_provider_accounts`, `payment_provider_accounts`;
  a schema-guard test fails when a new cascade FK to `salons(id)` is not in the explicit
  list (`SALON_CASCADE_TABLES`);
- the salon row becomes a **shell**: `name = 'Closed salon'`; `city`, `description`,
  `address`, coordinates, QR image and `rejection_reason` cleared; `working_hours = {}`; QR
  token rotated; `owner_id` NULL; `is_active = false`. Services lose `description` and photo;
- staff: `name = 'Former staff'`, photo/`specialization`/`experience` cleared, `profile_id`
  NULL, inactive; `staff_services.specialization` cleared;
- bookings at the salon (other customers' history, **retained**): `rejection_reason` /
  `cancellation_reason` (except `salon_closed`) cleared; **walk-in bookings without an
  account** (`customer_id` NULL) lose name/phone/notes because nobody else holds that data;
  `booking_action_requests.decision_reason` cleared; `payment_refunds.reason` free text
  cleared; `booking_payments.recorded_by` NULL;
- customers' and staff members' notifications about the salon's bookings lose their text
  (the closure notices are exempt);
- `salon_reports` about the salon: `details` emptied, the reporter's `reason` kept;
  `subscription_events.error_message` cleared; `salon_subscriptions` rows are kept (dates only);
- **subscription billing wind-down** (first thing in the owner closure transaction, `cancel_open_bookings`,
  and re-run inside erasure): future renewal state `cancelled` (`cancelled_at` set), unpaid
  `created`/`authorized` subscription orders marked `expired` locally (the provider order itself cannot be
  cancelled; a payment that still lands is recorded `paid` but **never applied**, because the salon has no
  owner: outcome `blocked_closed`, anomaly `subscription_blocked`), and every paid-but-unused period raises a
  `subscription_unused_period` row in `payment_anomalies` with the unused amount for a refund decision
  (refunds of subscription payments are an operator action). `subscription_billing_records` are **retained**
  (amounts, ids, provider references; no personal data) with `created_by` nulled;
- **staff logins that exist only for this owner's salons are hard-deleted** (profile in step 5,
  Auth identity in step 9), after being banned in step 4. Guard, re-checked inside the
  transaction: role `staff`, no staff row at any salon the owner does not own, never a
  customer, never an owner. A login failing the guard stays banned but is not deleted.
  Rationale: these are separate people whose name, email, phone and avatar would otherwise be
  banned yet kept for ever, with no notice and no recovery. Downside: they lose the login with
  no warning; there is no notification to staff today.

**Redis (step 7)**: `salon:{id}:*` for **every** owned salon (ids captured at confirm in
`step_state.salon_ids`, because `owner_id` is gone after step 5), `walkin:qr:*`,
`idempotency:walkin:v2:{uid}:*` (owner and staff), `idempotency:booking:{uid}:*` (cached
booking response with name and phone), and `rate:otp:{phone}` for each spelling of the
account's phone. Errors are no longer swallowed: the step retries until Redis confirms.

**Ledger `account_deletion_requests`** on completion: `user_id`, `media_keys`,
`last_error_code` cleared, **`step_state` reset to `{}`** (it held other users' UUIDs: staff
profile ids and salon ids), `salon_name` replaced by `Closed salon`, `salon_city` NULL.
It retains role, salon id, status, attempt count and timestamps. While a request is *open*
the ledger row does hold the salon's real name/city and (in `step_state`) staff profile ids -
it is only anonymised once erasure completes.

## Data-deletion matrix

| Data | Action |
|---|---|
| Supabase Auth user, sessions | ban, then hard delete |
| Owner's staff Auth users | ban, then hard delete when their profile was deleted (guarded) |
| `profiles` row (user; owner's staff-only logins) | hard delete (referencing actor columns nulled first) |
| Avatar, salon images, staff/service photos (R2) | delete verified keys under `avatars/`, `salon-images/`, `staff-photos/` unless still referenced |
| `notifications`, `notification_outbox`, `notification_deliveries`, `device_tokens` of the user | delete |
| Others' notifications naming the person/salon | text, data and delivery errors scrubbed |
| `salon_reports` filed by the user | delete |
| Customer's past bookings | **retain, anonymise** (name "Deleted customer"; phone, notes, reasons cleared) |
| Bookings at a deleted owner's salon | **retain** for the customers' own history; owner-written text and walk-in details cleared |
| Future bookings at a deleted owner's salon | **cancelled** (`salon_closed`), customers notified, online payments refunded |
| `booking_payments` / `payment_refunds` | **retain** (amounts, ids, provider refs); `payer_id`/`recorded_by`/`requested_by` nulled; free-text reason cleared |
| `payment_idempotency_keys` | delete for the user (and the owner's staff logins) |
| Booking-action requests | resolved/invalidated if open; person's free text cleared |
| Salon (owner) | **kept as an inert shell**: "Closed salon", no city/address/coordinates/description/QR/hours, `owner_id` NULL, inactive, no reclaim path |
| Holidays, payout account + history, provider accounts, images, blocked slots | delete |
| Staff rows | "Former staff", personal fields cleared |
| Subscription rows | `salon_subscriptions` retained (dates/status only); provider customer/subscription references and event error text removed; `subscription_billing_records` retained (financial), actor nulled; renewal cancelled, unpaid orders expired, unused paid time flagged for the operator |
| Audit actor columns | NULL |
| Redis | see above |
| FCM / Expo | tokens deleted; no other provider-side user records are held |
| Ledger `account_deletion_requests` | retained for the super admin: role, salon id, status, attempts, timestamps; `step_state` emptied and salon name/city anonymised on completion |

## Boundaries (what is NOT erased)

- Supabase and R2 **backups/snapshots**, provider logs and CDN caches until they expire.
- Other users' data: customers' records inside a deleted owner's salon history, and the
  deleted customer's anonymised bookings visible to the salon. `services.name` (salon-specific
  service names) is kept because booking history refers to it.
- The payment provider's own records (the payer's card/UPI details live there, not here), and
  `payment_webhook_events.normalized` (identifiers and amounts only, by contract).
- A cash receipt: the amount and booking stay in the ledger; only the people are detached.
- Media uploaded but never registered: removed by the hourly orphan sweeper after its 24 h
  grace, not by this workflow.
- A payment captured *after* the closure refund step (a checkout already in flight when the
  salon closed) is not refunded automatically; it shows up in the runbook's intent queries.
- The `salon_closed` cancellation reason and the placeholder strings `Removed` / `Booking
  update` are system text, not personal data.

## Admin visibility

`GET /v1/admin/account-deletions` (super admin, MFA rules apply): the ledger without personal
identifiers. Each row now includes `attempts`, `last_error_code`, `next_attempt_at` and
`updated_at` so a stuck request is visible without database access. Stale-request query:
see RUNBOOK.md.

## Deployment

1. Apply reviewed migrations explicitly, in order, through `0028_account_erasure_hardening`
   (`alembic upgrade head` from `backend/`). Never from API startup. 0028 replaces
   `erase_profile_references` (now also `ON DELETE RESTRICT` keys) and adds a partial index for
   the stale-request query; it adds no columns.
2. Set `ACCOUNT_DELETION_SECRET` (>= 32 chars; `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   in `backend/.env`. Optional tunables are in `.env.example` (including
   `ACCOUNT_DELETION_REFUND_MAX_ATTEMPTS`).
3. Start the Compose service: `docker compose up -d --build` (`account-deletion-worker`; it
   needs the same `.env`: database, Supabase service role, **complete R2 settings**, Redis).
   It now has a heartbeat healthcheck - confirm `docker compose ps` shows it `healthy`.
4. Supabase dashboard: enable email OTP and put `{{ .Token }}` in the *Magic Link / Email OTP*
   template so users receive a code (not only a link); confirm an SMS provider if phone is used.

Rollback of 0021 is possible only while no account has been erased (it restores `NOT NULL`
on `salons.owner_id` / `booking_action_requests.requested_by`). 0028 downgrades cleanly.

## Public web page (Google Play) - separate website repository

Not part of this repo and **not yet built**. Requirements: stable public URL naming the app and
developer, explains what is deleted/retained (use the matrix above), Supabase sign-in, then
the four calls above with a "type DELETE" confirmation, show `deletion_blocked` guidance and
the status endpoint. Until it exists the Play requirement is not satisfied.

## Verification

Unit tests use fakes for Supabase/R2/Redis/the payment gateway (cancel, notify, refund exactly
once across a retried run, settle backoff, cap, failed refund, no provider, cache failure,
healthcheck, start-up validation, the schema guard).

`tests/integration/test_account_deletion_sql.py` runs the real SQL against a **disposable
localhost database that already has the whole migration chain applied** and a Supabase-like
`auth` schema (`auth.users`, `auth.uid()`, the `anon`/`authenticated`/`service_role` roles).
It asserts, after owner and customer erasure (each run twice), that no text/varchar/jsonb
column in any public table contains the erased people's seeded names, emails, phones,
UPI/account numbers or ids and no uuid column holds their ids; that every text/jsonb column in
the schema is classified in `COLUMN_TREATMENT` (a new column fails the test until someone
decides how erasure treats it); that every cascade FK to `salons` is erased; and the worker
loop end to end (cancel, notify, one refund across a retried run, settle, cap, erase).

```bash
ACCOUNT_DELETION_TEST_DB=postgresql+asyncpg://postgres:<password>@127.0.0.1:5432/scratch \
  ./.env1/Scripts/python -m pytest tests/integration/test_account_deletion_sql.py
```

The test inserts rows with unique markers and leaves them behind, and empties the open
deletion queue first: never point it at anything you care about.
