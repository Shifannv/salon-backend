# Database plan

Local implementation now includes migrations 0034–0037, tested locally, for checked-in/no-show
states, trial/daily/no-show booking guards, immutable audits, support/email outbox and processing
charge snapshots. They have only been applied to disposable local databases; deployment requires
human review and staging validation. The v3 raw SQL baseline remains unchanged. See
[migration and API contract](../backend/docs/PRODUCTION_VERIFICATION.md).

Supabase Postgres stores profiles, salons, catalog data, staff, bookings,
notifications, device tokens, blocked slots, holidays, images, and salon reports.

The schema starts with `backend/migrations/001_supabase_schema.sql`. Alembic revision
`0001_baseline` applies that file, and later revisions apply required incremental
changes. Existing migration history must not be deleted or rewritten after deployment.

Current app-contract additions include soft deletion for salon holidays
(`0011_holiday_soft_delete`), booking completion estimates
(`0012_booking_delay`), and transactional booking action requests
(`0013_booking_action_requests`), and salon super admin approval
(`0015_salon_admin_approval`). See the [approval guide](../backend/docs/SALON_APPROVAL.md)
for schema verification and deployment steps.

Later revisions add service presentation (`0016_service_presentation`), admin display
priority (`0017_salon_display_priority`), manual subscription foundation
(`0018_subscription_foundation`), and discovery visibility/home placement
(`0019_discovery_placement`). Code using these fields requires the reviewed migrations
before deployment; the unchanged v3 baseline remains the starting point.

Revision `0020_media_reference_guards` is prepared for review and explicit deployment.
It coordinates media-reference writes with cleanup using transaction advisory locks
and requires Supabase client roles to assign new hosted image URLs through the backend.
It does not rewrite stored URLs. The cleanup worker refuses to delete objects until
all seven reference guards are installed. See the backend image integration report
for verification limits; this revision has not been applied as part of that work.

Rules:

- Apply schema changes only through reviewed Alembic revisions.
- Create bookings only through the Postgres `create_booking` function.
- Read availability only through `get_available_slots`.
- Use `is_active` for soft deletion where the schema supports it.
- Keep RLS enabled and mirror its access rules in application use cases.
- Set transaction-local `request.jwt.claims` for authenticated database work so audit
  triggers receive the verified actor ID.
- Never expose raw database errors, SQL, or constraint names through HTTP responses.

See [the migration guide](../backend/migrations/README.md) for safe commands.

## Account deletion (revision `0021_account_deletion`)

Adds `account_deletion_challenges` (per-user, hashed contact/confirmation, attempt and expiry
state, one live row per user) and `account_deletion_requests` (durable erasure outbox and
PII-free ledger, no foreign key to `profiles`). Relaxes `NOT NULL` on `salons.owner_id` and
`booking_action_requests.requested_by`, teaches `set_audit_actor()` to stand down inside the
erasure transaction (`app.account_erasure`), and adds `erase_profile_references(uuid)` which
nulls every no-action foreign key to `profiles(id)`. Requires `0020` first.

**`0028_account_erasure_hardening`** replaces `erase_profile_references` so it also nulls
`ON DELETE RESTRICT` keys, and adds a partial index `idx_account_deletion_requests_open_age`
(`requested_at where status <> 'completed'`) for the stale-request query. No new columns: the
cancel/refund/settle phases are boolean keys in `account_deletion_requests.step_state`
(`bookings_cancelled`, `refunds_issued`, `refunds_settled`, plus the existing erase steps, and
`salon_ids` / `staff_profile_ids` until completion). Salons are soft-deactivated, so every
`ON DELETE CASCADE` FK to `salons(id)` (`salon_images`, `salon_holidays`, `blocked_slots`,
`salon_payout_accounts`, `salon_payout_account_history`) is emptied by explicit deletes in
`account_deletion_repository.py`; a unit test fails when a migration adds one that is not
listed. Closure refunds are `payment_refunds` rows with `idempotency_key = 'salon_closed'`.

## Payments and payout audit (migrations 0026, 0027)

New tables: `booking_payments` (ledger), `payment_refunds`, `payment_webhook_events`,
`payment_idempotency_keys`, `payment_provider_accounts`, `salon_payout_account_history`.
New `bookings` columns: `currency`, `deposit_amount`, `paid_amount`, `refunded_amount`
(a derived cache of the ledger; `payment_preference` CHECK widened to
`pay_at_salon|pay_advance|pay_full`). Functions: `recompute_booking_payment_state`,
`salon_payout_account_masked`. All new status columns are `text` + `CHECK`; the
`payment_status`/`payment_method` enums are unchanged. New tables are RLS-enabled with
anon/authenticated privileges revoked.

BUILT: schema as migrations. NOT VERIFIED: never run against a live Postgres. NOT BUILT:
column encryption of `salon_payout_accounts.bank_account_number`.
