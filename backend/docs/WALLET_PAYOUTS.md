# Owner wallet and manual payouts

Status: implemented and tested locally; migration 0053 is **prepared, not applied** to any database,
and is **not** in `RECONCILIATION_REVISIONS` or `STAMP_ALLOWED_REVISIONS` (no owner gate has
authorised it). Online payments are still off (`PAYMENT_PROVIDER=none`), so every balance is zero in production.

## Model
The owner asks for a payout on a day (today or later, at most 60 days ahead). The platform admin pays it
by hand and records the bank or UPI reference, or declines it with a reason. There is no instant payout and
no frequency setting. The owner is told the money is credited within 24 hours of the chosen day.

The balance is **derived**, never stored: gateway payments with `settlement_model = 'platform_collect'`
(amount less overcollected less commission), less processed non-excess refunds plus commission reversed,
minus requests that are `requested` or `paid`. Rejecting or cancelling a request returns the money with no
extra bookkeeping. Payments settled straight to the salon (`direct_to_salon`) and manual receipts are not
counted: the platform does not hold that money.

## Owner routes (owner only; staff and customers get 403)
| Route | Purpose |
|---|---|
| `GET /v1/salons/me/wallet` | `available_paise`, `requested_paise`, `paid_out_paise`, `min_payout_paise`, `online_payments_live`, `payout_account_ready`, `can_request` |
| `GET /v1/salons/me/wallet/entries?cursor&limit` | History, newest first: `earning`, `refund`, `payout` rows with status `completed/requested/paid/rejected/cancelled`, `reference`, `reject_reason`, `scheduled_for`, `can_cancel` |
| `POST /v1/salons/me/wallet/payout-requests` | `{amount_paise, scheduled_for}`; **Idempotency-Key required**; same key + body replays |
| `POST /v1/salons/me/wallet/payout-requests/{id}/cancel` | Only while `requested`; cancelling twice is safe |

Refusals carry a stable `error.code`: `insufficient_balance`, `below_minimum`, `payout_account_missing`,
`invalid_date`, `not_cancellable`, `idempotency_key_required`.

## Admin routes (super admin + MFA)
| Route | Purpose |
|---|---|
| `GET /v1/admin/wallet/payout-requests?status&cursor&limit` | Queue across salons, oldest first, with the salon name and the **masked** payout account (holder, UPI, bank, last four, IFSC) |
| `POST /v1/admin/wallet/payout-requests/{id}/mark-paid` | `{reference}` (1-100 chars). Retrying with the same reference is safe; another reference on a paid request is refused (`already_processed`) |
| `POST /v1/admin/wallet/payout-requests/{id}/reject` | `{reason}` (3-500 chars). The money returns to the owner's balance |

## Safety
- Every owner write takes the salon lock (`FOR NO KEY UPDATE`), so concurrent requests cannot spend one balance twice
  (verified on PostgreSQL 17: six simultaneous requests, exactly one accepted).
- A DB trigger freezes a request after its single move out of `requested`; rows are never deleted or truncated.
- Account numbers are never read into Python; the admin sees only the masked projection.

## Open decisions (not made in code)
1. **Minimum payout** is `MIN_PAYOUT_PAISE = 10_000` (Rs 100), a default to confirm (`domain/services/wallet.py`).
2. **How the admin gets the full account number** to pay. Only the masked view is exposed; a reviewed admin-only
   reveal (or paying from the saved UPI id) must be decided.
3. **Commission has no default rate** (`PAYMENT_DECISIONS.md`), so earnings stay zero until the business sets it.
4. **Owner push notification** when a payout is paid or declined is not sent; the wallet history shows it.
5. **Migration gate**: add 0053 to the authorised lists, with evidence, before any release.
6. **Admin website screen** for the queue is a separate website task.
