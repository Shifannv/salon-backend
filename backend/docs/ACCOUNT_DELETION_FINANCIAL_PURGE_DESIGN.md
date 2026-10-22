# Account deletion: reviewed financial purge (design, not built)

| | |
|---|---|
| **Status** | Design only. No migration file exists and none has been run. |
| **Date** | 2026-10-22 |
| **Decided by** | Product owner, 2026-10-22 (see [Decisions](#decisions)) |
| **Builds on** | [ACCOUNT_DELETION.md](ACCOUNT_DELETION.md) |
| **Needs** | A reviewed Alembic revision after `0040_fastapi_only_access`, owned by the migration owner |

## What is already built

The month-end view needs no migration, so it is built and tested:

- `GET /v1/admin/deleted-salons`: the closed-salon review queue.
- `GET /v1/admin/deleted-salons/{salon_id}/statement`: money totals per month and currency, with the platform's net commission, the salon's online net and the platform's revenue. It returns `404` for any salon that an owner deletion did not close, so it cannot read an active salon's finances.

A customer with a `checked_in` booking is now blocked from deleting the account, like a customer with an upcoming booking.

## Decisions

| Topic | Decision |
|---|---|
| Customer account | Allowed only when the customer has no current, future or pending booking. Otherwise the existing `deletion_blocked` message is shown. |
| Owner account | Personal and business data is hard-deleted at once (unchanged). The salon stays as the inert "Closed salon" shell. |
| Financial history | Kept for the super-admin's month-end review. After the super-admin marks it reviewed, only **monthly totals** remain. Every booking and payment row of that salon is hard-deleted. |
| When the delete happens | After a configurable retention period, never earlier. Personal data is never held back. |
| Audit history | May be deleted **only** by account erasure or this purge, and only for the bookings being removed. |

## Why the retention gate

Deleting the money rows is irreversible. Indian tax and accounting rules, a payment dispute, or a late refund claim can need those rows for years. The retention period is **not a legal answer this document can give**; it is an open decision (TA09/L05 in `migrations/payment-subscription-booking-designs/`) for the accountant. The design therefore:

1. Freezes the totals at review, so month-end figures survive.
2. Deletes the rows only after `FINANCIAL_RECORD_RETENTION_YEARS` have passed since the salon's last transaction.
3. Does nothing, with no default, until that setting exists. An unset value fails safe: nothing is deleted.

## Data model (proposal; names are not final)

Backend-only tables: RLS enabled, privileges revoked from `anon` and `authenticated`, granted to `service_role`, like the payment tables.

**`deleted_salon_financial_reviews`** (one row per closed salon)

| Column | Notes |
|---|---|
| `salon_id uuid primary key` | references `salons(id)` (the shell stays) |
| `closed_at timestamptz not null` | when erasure completed |
| `status text not null` | `awaiting_review`, `reviewed` or `purged` |
| `reviewed_by uuid`, `reviewed_at timestamptz` | the super-admin; `reviewed_by` is nulled if that person's account is erased |
| `retain_until timestamptz` | set at review, from the last transaction date plus the retention period; null while the setting is unset |
| `purged_at timestamptz` | |

**`salon_monthly_settlements`** (permanent; no personal data)

| Column | Notes |
|---|---|
| `salon_id uuid`, `month date`, `currency char(3)` | primary key together |
| the sums in the statement | `online_collected`, `online_refunded`, `platform_fees`, `commission_reversed`, `overcollected`, `manual_recorded`, `subscription_paid`, `subscription_refunded`, and the two counts |
| `frozen_at timestamptz` | |

Rows are insert-only; a trigger rejects update and delete.

## Flow

1. **Owner erasure** (existing step 5) inserts the review row as `awaiting_review`, in the same transaction.
2. **Review.** `POST /v1/admin/deleted-salons/{salon_id}/review` (`require_role(super_admin)`, `aal2`, `Idempotency-Key`):
   - recomputes the statement inside one transaction and inserts the monthly rows (`on conflict do nothing`);
   - sets `status = 'reviewed'`, `reviewed_by`, `reviewed_at`, and `retain_until`;
   - a repeat call returns the stored result and changes nothing.
3. **Purge.** A step in the existing `account-deletion-worker`, once per run:
   - selects reviews with `status = 'reviewed'` and `retain_until <= now()`;
   - runs the deletion below in one transaction per salon, with `app.account_erasure = 'on'`;
   - sets `status = 'purged'`.

### Purge order (per salon)

Foreign keys that reference `bookings` or the payment tables decide the order:

1. `payment_refunds`, then `payment_anomalies`, then `booking_payments` for the salon's bookings.
2. `subscription_billing_records` and the salon's `subscription_events` rows.
3. Rows that cascade from `bookings`: `booking_services`, `notifications` (and their outbox rows), `booking_action_requests`.
4. `booking_audit_events` for those bookings (see the next section).
5. `bookings` for the salon.

The salon shell, the review row and the monthly settlements stay.

### The audit-history rule

`guard_audit_immutable()` (`migrations/sql/0035_booking_checkout_safety.sql:169-178`) rejects every update and delete on `booking_audit_events`, except the erasure bypass that nulls `actor_id`. The purge needs one more narrow exception: **delete is allowed when `app.account_erasure = 'on'`**. Nothing else changes. Outside erasure and this purge, audit history stays undeletable. `0040_fastapi_only_access.sql` re-checks this function's owner and privileges, so the change must be reviewed with it.

## Customer deletion

Today a customer's past bookings are anonymised ("Deleted customer", no phone or notes) and stay. Under the decision they should disappear. Split by whether the booking is a money record:

| Booking | Action |
|---|---|
| No `booking_payments` row | Hard-delete, with its dependent rows and audit events |
| Has a payment | Stays anonymised. It is the salon's money record and is removed by the salon purge above. |

This also needs the audit-history exception, and the `COLUMN_TREATMENT` classification test must be updated.

## Configuration

`FINANCIAL_RECORD_RETENTION_YEARS`: integer, no default. Validated at startup. Documented in `backend/.env.example` by the deployment owner. While it is unset, `retain_until` stays null and the purge never runs.

## Tests required

- Role matrix on the review route: owner, staff and customer get 403; a super-admin without `aal2` gets 403.
- Review is idempotent, freezes the totals, and refuses a salon that no owner deletion closed.
- Purge does nothing when the setting is unset, when the review is not `reviewed`, or before `retain_until`.
- Purge deletes only that salon's rows; another salon's rows and all monthly settlements survive.
- Purge is re-runnable and leaves no booking, payment or audit row for the salon.
- Audit rows are still undeletable outside erasure (the existing immutability test).
- A real-PostgreSQL test of the purge order against every foreign key, on a throwaway database.
- Customer deletion removes unpaid bookings and keeps paid ones anonymised.

## Rollout and rollback

- Ship after the Mumbai migrations `0038`–`0040` pass their gates. The migration chains after `0040` and needs the migration policy, its tests and the deploy workflow to learn the new head. That is the migration owner's change.
- Deploy the migration first, then the code, then set `FINANCIAL_RECORD_RETENTION_YEARS` last, so the purge cannot run early.
- Rollback before any purge: revert the code and drop the two new tables. **After a purge nothing can be restored**, which is why the purge is gated by time and by a human review.

## Risks and open decisions

1. **Retention period (accountant):** the number of years, and whether GST invoices need a longer-lived copy than monthly totals provide. Monthly totals may not satisfy a tax audit that asks for invoice-level detail.
2. **Provider-side records:** the payment provider keeps its own transaction history. This purge does not delete it.
3. **Subscription refunds** are an operator action today. A salon with an unresolved unused-period anomaly should not be purged; the purge must skip a salon that still has an open `payment_anomalies` row.
4. **Disputes:** a salon with an open payment dispute or refund in flight must be skipped.
5. **Backups:** deleted rows remain in database backups until those expire (already listed under "Boundaries" in `ACCOUNT_DELETION.md`).
