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
`payout_requests_pending`. The server decides; the website only shows it and checks the typed salon name.

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
fails the job stays `cleanup_pending` and repeating the same `DELETE` finishes it. Nothing retries it
automatically yet.

## Not covered

- `payment_webhook_events` and `payment_idempotency_keys` are not keyed by salon and are not deleted.
- Deleting money records conflicts with the retention stance in `ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md`.
  This was chosen explicitly ("no trace"); confirm with the accountant before production use.
- The refund provider call happens inside the request. A salon with very many open online payments should be
  prepared in more than one call.
