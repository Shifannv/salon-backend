# Admin salon deletion

A super admin can permanently delete one salon and everything that hangs off it. This is separate from
the owner's own account deletion (`ACCOUNT_DELETION.md`), which keeps financial rows. Here the money
records are removed too, but only after nothing is owed either way.

Migration: `0058_admin_salon_erasure` (prepared, not applied anywhere).

## Endpoints (super admin, aal2)

| Call | Purpose |
|---|---|
| `GET /v1/admin/salons/{id}/deletion-readiness` | Open bookings, refunds due, refunds in flight, payout owed, pending payout requests, `can_delete`, `blockers`. Read only. |
| `POST /v1/admin/salons/{id}/deletion/prepare` `{ "refund_mode": "auto" \| "manual" }` | Hides the salon from customers, cancels open bookings and tells each customer, then settles refunds. Safe to repeat. Returns the readiness. |
| `DELETE /v1/admin/salons/{id}` | Erases the salon. `204`. `409 salon_not_ready_for_deletion` while anything is owed. `404` once erased. |

`blockers` values: `open_bookings`, `refunds_due`, `refunds_pending`, `payout_balance`,
`payout_requests_pending`, `payments_pending`. The response includes `payments_pending_count` for
created/authorized gateway payments. Closing a booking does not falsely mark its provider order cancelled.
Wait for provider reconciliation before erasing. The server decides; the website checks the typed salon name.

## Refunds

- `auto`: each captured online payment on an open or closure-cancelled booking is refunded once through the
  provider that holds it. The provider idempotency key is the one the owner flow uses
  (`closure_refund_provider_key`), so a salon refunded here can never be refunded twice later.
  A provider failure leaves the refund `failed` and the salon blocked; call prepare again to retry.
- `manual`: the admin refunded outside the system. The refund is recorded `processed` with
  `refund_ref = 'manual'` and `requested_by` = the admin, so the ledger agrees.
- A refund the provider accepted but has not confirmed (`created`) shows as `refunds_pending` and blocks
  deletion until the payment webhook marks it processed.

## Payouts

Never settled automatically. The owner's balance is `available_paise` from the wallet
(`app/domain/services/wallet.py`); any amount above zero, or any `requested` payout request, blocks. The
admin clears it on the Payouts screen.

## What the erase does

`public.erase_salon(uuid)` runs in one transaction and is callable only by the backend role:

1. Locks the salon row, refuses an unknown id (`salon_not_found`).
2. Switches off only the row-level DELETE triggers (the append-only guards) of the tables it deletes from,
   for the length of its own transaction. A rollback restores them; they are enabled again at the end.
   TRUNCATE guards and every other trigger are untouched. This takes a SHARE ROW EXCLUSIVE lock on those
   tables (writes wait, reads continue); `lock_timeout` is 5 s, so a busy moment fails fast and is retried.
3. Deletes children first (payout, finance, booking, staff, subscription, support, catalog rows), then the
   salon. Images, holidays, blocked slots, payout accounts, access, plan prices and overrides cascade.
4. Writes a tombstone to `salon_erasure_jobs`: opaque salon id, status, step state. No name, phone or
   amount. It makes a repeat DELETE safe and lets a late provider event for an erased salon be recognised.

`tests/integration/test_admin_salon_erasure_sql.py` walks the foreign-key graph: a new table with a
non-cascading reference toward salons fails the build until `erase_salon` handles it.

## After the database commit

Files (`salon-images/`, `staff-photos/`, avatars), cache prefixes (`salon:{id}:`, `walkin:qr:`) and logins are
cleaned up. The owner's profile and Supabase Auth user are removed only when they own no other salon, are
not staff anywhere and have no bookings as a customer; staff logins follow the same rule. If this part
fails the job stays `cleanup_pending`, DELETE returns 503, and repeating the same `DELETE` finishes it.
Readiness remains available for an incomplete job even after the salon rows are gone. Cache failures are
strict. Only the actual owner's owner-role profile and staff-role logins are candidates; linked customers,
superadmins and unrelated owners are preserved. Current roles and remaining memberships are checked again
under a profile row lock. Missing profiles remain retryable after an Auth failure. The verified initiating
admin is retained in `step_state.initiated_by`. Nothing retries cleanup automatically yet.

Before the final readiness check, the application locks the erase tables in a fixed order through the
commit, so a concurrent capture cannot slip between readiness and erase. Ordinary reads continue. If a
writer or row-locking reader is active, NOWAIT returns a retryable 409 before erasure; it never waits
while holding part of the table-lock set. This brief operation blocks writes across these tables.

## Disposable local demo

This uses development test helpers and a synthetic admin identity; never deploy the demo launcher.
It creates a new database without dropping or reusing another database. Production configuration and
the existing port-8000 owner-app test server are not used. No external Auth, storage or provider calls run.

Start a dedicated `postgres:18` container with a loopback published port and the development-only password
`local-erase-test-only`. From `backend/`, run:

```powershell
./.venv/Scripts/python.exe -m scripts.dev_admin_erasure --postgres-port <published-port> --port 8001
```

From the website's `walking-customer-web/`, run `node scripts/dev-admin-erasure.mjs`, then open
`http://localhost:3101/superadmin/salons`. Website authentication remains the normal admin session;
only data requests go to this isolated backend. Its two synthetic salons demonstrate direct erasure
and cancellation-before-erasure. The demo retains its disposable database until its container is removed.

## Not covered

- `payment_webhook_events` and `payment_idempotency_keys` are not keyed by salon and are not deleted.
- Deleting money records conflicts with the retention stance in `ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md`.
  This was chosen explicitly ("no trace"); confirm with the accountant before production use.
- The refund provider call happens inside the request. A salon with very many open online payments should be
  prepared in more than one call.
