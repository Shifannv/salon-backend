# Owner payout accounts and setup checklist

Endpoints (owner router, `/v1/salons`): `GET|PUT /me/payout-account`,
`GET /me/payout-account/history`, `GET /me/setup-status`.
Request/response shapes are in `docs/Salon-Owner-App-Backend-API-Document.md`.

## Storage and security

- Table `salon_payout_accounts` (migration `0025_salon_payout_accounts`), one row per salon,
  `on delete cascade` from `salons`. It is deliberately NOT part of `salons`, which customers
  can read publicly. No public, customer, staff or admin-list payload selects from it.
- RLS is enabled with one owner-only policy (`owns_salon(salon_id)`); all privileges are
  revoked from `public`, `anon` and `authenticated` (Supabase auto-grants), so the Data API
  cannot reach it. Only the backend DB role / `service_role` can.
- A CHECK requires a UPI ID or (account number and IFSC); format CHECKs repeat the API regexes.
- Authorization is in `OwnerUseCases` (`is_owner` only). It is intentionally not gated on
  salon approval so a new owner can finish setup while pending.
- The account number is masked **inside Postgres** (`salon_payout_account_masked`,
  migration `0027`), so the full value is never read into Python on any read path. The
  PUT merge also happens in SQL (`case when :set_x then excluded.x else existing.x`), so
  Python never holds the stored number; it validates against a presence marker only.
- The API masks the account number to its last 4 digits. The 422 handler strips `input`
  for `/payout-account` so submitted values are never echoed or logged.
- Account erasure: salons are soft-deactivated (not deleted), so the FK cascade never fires.
  `_scrub_owner_business` therefore deletes the payout row explicitly.

## Audit trail (migration `0027_payout_account_audit`)

- `created_by`/`updated_by` with the shared `set_audit_actor()` trigger.
- Append-only `salon_payout_account_history`, written by trigger on every insert/update
  that changes a payout field: who, when, which fields, and before/after snapshots that hold
  the **last four digits only**. Exposed at `GET /v1/salons/me/payout-account/history`.
- `ck_payout_bank_triple`: account number and IFSC are all-or-nothing; a bank name may not
  stand alone. Clearing the account number also clears IFSC and bank name unless the
  request sets them. The migration repairs any pre-existing stray rows first.
- Read-only salon resolution: `GET` payout, history and setup-status never provision a
  salon (they previously could, and committed). `PUT` still provisions.
- Erasure: `salon_payout_account_history` cascades from `salons`, but salons are
  soft-deactivated, so account erasure deletes the account and its history rows explicitly
  (`SALON_CASCADE_TABLES` in `account_deletion_repository.py`; verified by the real-SQL
  residual-PII sweep). The history holds the holder name, UPI id, bank name, IFSC and last
  four digits, so leaving it behind would have kept banking details after deletion.
- `ck_payout_upi_format` allows 2-255 characters before the `@` (PostgreSQL's regex engine
  rejects a `{2,256}` repetition, which made every UPI payout save fail with a database error
  until this was caught by running the migrations on a real PostgreSQL).

## Status

BUILT: audit trail, SQL masking, SQL-side merge, bank-triple CHECK, read-only resolver.
DORMANT: `bank_account_fingerprint` column exists but is **not populated**; a bare hash of
a 9-18 digit number is brute-forceable, so it needs a keyed HMAC with a key held outside the
database. NOT BUILT: **encryption at rest**. The account number is still stored as
plaintext `text`; moving it out of application memory is the cheap 80%. Recommended next
step: Supabase Vault or `pgcrypto` with a key outside the table, keeping `last4` separate.
Migrations are untested against a live Postgres (none was available).
