# Account Deletion

Permanent, self-service deletion for **customer** and **owner** accounts. One trusted
backend workflow serves both mobile apps and the public deletion web page. Clients never
hold service-role credentials and never pick which account is deleted: the account is the
verified JWT `sub`.

Status: implemented locally; **not staging-tested, not production-verified**. SQL in
`tests/integration/test_account_deletion_sql.py` is opt-in and has not yet been run
against PostgreSQL (see Verification).

## Flow

1. `POST /v1/account/deletion/challenges` - sends a one-time code through Supabase Auth to
   the account's own **provider-verified** email or phone (looked up server-side with the
   service role, never taken from the request). `contact` is optional; if sent it must match.
2. `POST /v1/account/deletion/challenges/{id}/verify` - Supabase verifies the code; the
   backend asserts the returned user id equals the JWT `sub`, discards the provider session,
   and returns a one-time `confirmation_token`. **Nothing is deleted yet.**
3. `POST /v1/account/deletion` with `confirm: "DELETE"` - atomically locks the account and
   queues erasure. The JWT stops working immediately (`profiles.is_active = false`).
4. `GET /v1/account/deletion/{request_id}` with header `X-Status-Token` - progress. The JWT is
   dead after step 3, so this uses the token returned in step 3 (a header, so it stays out of
   access logs).

Challenge guarantees: bound to user + purpose + channel + contact hash; HMAC-only storage
(no plaintext OTP or tokens); 10 min expiry; 5 attempts total (resends do not reset them);
60 s resend cooldown; 3 resends; 5 challenges/hour; single use; DB-enforced (Redis limiting
fails open so is not relied on). Errors: 400 `invalid_verification_code`, 404 for another
user's challenge, 409 `deletion_blocked`, 422 `contact_mismatch`, 429, 503 if
`ACCOUNT_DELETION_SECRET` is unset outside local/test.

## Blockers (409 `deletion_blocked`)

No cancellation rules are invented. Deletion is refused while the account has pending/
confirmed bookings ending in the future, or pending booking-action requests (for an owner:
across the owner's salons). For owners also while a subscription is active **and**
`SUBSCRIPTION_PROVIDER != none`. Resolve through the existing booking flows, then retry.
Checked at challenge start and again inside the confirm transaction.

## Erasure (worker `account-deletion-worker`)

Durable outbox in `account_deletion_requests`; claimed with `FOR UPDATE SKIP LOCKED`,
stale claims are re-taken after 10 min, backoff up to 1 h, every step idempotent and
recorded in `step_state`. Order: ban auth user (and the owner's staff logins) -> database
erasure -> R2 delete -> cache clear -> delete Supabase Auth user -> verify (profile row and
auth user absent) -> `completed`. Failures leave `failed` + retry; the account is never
reactivated and completion is never claimed early.

## Data-deletion matrix

| Data | Action |
|---|---|
| Supabase Auth user, sessions | ban, then hard delete |
| `profiles` row | hard delete (all referencing actor columns nulled first via `erase_profile_references`) |
| Avatar, salon images, staff/service photos (R2) | delete verified keys under `avatars/`, `salon-images/`, `staff-photos/` unless still referenced |
| `notifications`, `notification_outbox`, `notification_deliveries`, `device_tokens` | delete (at confirm) |
| `salon_reports` filed by the user | delete |
| Customer's past bookings | **retain, anonymize**: `customer_id` NULL, name "Deleted customer", phone/notes NULL. Basis: the salon's operational and financial records. |
| Booking-action requests (resolved) | retain; `requested_by` NULL, free-text `reason` cleared |
| Salon (owner) | deactivated at confirm (disappears from customer search and screens); kept as an inert shell (id, name, city) because other customers' booking history references it; address, coordinates, description, QR token/image, hours, images, blocked slots removed; `owner_id` NULL |
| Salon staff rows | deactivated, renamed "Former staff", photo/specialization removed; staff **logins are banned** (their own identities are not deleted) |
| Subscription rows | retained without personal data; no billing provider is integrated today, nothing to cancel externally |
| Audit actor columns (`created_by`/`updated_by`/`approved_by`...) | NULL |
| Redis | `salon:{id}:*`, `walkin:qr:*`, `idempotency:walkin:v2:{uid}:*` |
| FCM / Expo | tokens deleted; no other provider-side user records are held |
| Ledger `account_deletion_requests` | retained for the super admin: role, salon id/name/city, status, timestamps. **No name, email, phone, or user id** (user id is nulled on completion) |

## Boundaries (what is NOT erased)

- Supabase and R2 **backups/snapshots**, provider logs and CDN caches until they expire.
- Other users' data: customers' records inside a deleted owner's salon history, and the
  deleted customer's anonymized bookings visible to the salon.
- Media uploaded but never registered: removed by the hourly orphan sweeper after its 24 h
  grace, not by this workflow.
- Redis keys expire within their 1-5 min TTL if Redis was unreachable during the clear step.
- Staff members' own accounts are banned, not deleted.

## Admin visibility

`GET /v1/admin/account-deletions` (super admin, MFA rules apply): the PII-free ledger.

## Deployment

1. Apply reviewed migrations explicitly, in order: `0020_media_reference_guards`, then
   `0021_account_deletion` (`alembic upgrade head` from `backend/`). Never from API startup.
2. Set `ACCOUNT_DELETION_SECRET` (>= 32 chars; `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   in `backend/.env`. Optional tunables are in `.env.example`.
3. Start the new Compose service: `docker compose up -d --build` (adds `account-deletion-worker`;
   it needs the same `.env`: database, Supabase service role, R2, Redis).
4. Supabase dashboard: enable email OTP and put `{{ .Token }}` in the *Magic Link / Email OTP*
   template so users receive a code (not only a link); confirm an SMS provider if phone is used.

Rollback of 0021 is possible only while no account has been erased (it restores `NOT NULL`
on `salons.owner_id` / `booking_action_requests.requested_by`).

## Public web page (Google Play) - separate website repository

Not part of this repo and **not yet built**. Requirements: stable public URL naming the app and
developer, explains what is deleted/retained (use the matrix above), Supabase sign-in, then
the four calls above with a "type DELETE" confirmation, show `deletion_blocked` guidance and
the status endpoint. Until it exists the Play requirement is not satisfied.

## Verification

Unit tests mock Supabase/R2/Redis. `tests/integration/test_account_deletion_sql.py` exercises
the real SQL (FK nulling through the audit triggers, anonymization, locking, idempotency);
run it against a disposable localhost database:

```bash
ACCOUNT_DELETION_TEST_DB=postgresql+asyncpg://postgres:postgres@localhost:5432/scratch \
  ./.venv/bin/python -m pytest tests/integration/test_account_deletion_sql.py
```
