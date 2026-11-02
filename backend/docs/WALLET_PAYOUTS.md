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
| `POST /v1/admin/wallet/payout-requests/{id}/mark-paid` | **Multipart, with proof** (see Payout proof below). Retrying with the same reference is safe; another reference on a paid request is refused (`already_processed`) |
| `POST /v1/admin/wallet/payout-requests/{id}/reveal-account` | The salon's full bank or UPI details, **only while the request is waiting**, `Cache-Control: no-store`. Each look is logged (admin id, request id) without the account |
| `POST /v1/admin/wallet/payout-requests/{id}/reject` | `{reason}` (3-500 chars). The money returns to the owner's balance |

## Safety
- Every owner write takes the salon lock (`FOR NO KEY UPDATE`), so concurrent requests cannot spend one balance twice
  (verified on PostgreSQL 17: six simultaneous requests, exactly one accepted).
- A DB trigger freezes a request after its single move out of `requested`; rows are never deleted or truncated.
- The queue shows only the masked account. The full number is read into Python in exactly one place, `reveal-account`: super admin + MFA, request still waiting, never cached, never logged.

## Open decisions (not made in code)
1. **Minimum payout** is set by the super admin (see below). `MIN_PAYOUT_PAISE = 10_000` (Rs 100) is only the built-in default.
2. **Admin reveal** (decided: the admin sees the full details to pay). Built as `reveal-account`; each look is written to `payout_audit` (migration 0057) as well as logged.
3. **Commission has no default rate** (`PAYMENT_DECISIONS.md`): the super admin sets it (see below); until then no online payment is accepted.
4. **Owner push notification** when a payout is paid or declined is sent (`payout_update`), best effort; the wallet history also shows it.
5. **Migration gate**: add 0053 to the authorised lists, with evidence, before any release.
6. **Admin website screen** for the queue is a separate website task.

## Super-admin payment settings (migration 0056, prepared, not applied)
| Route | Purpose |
|---|---|
| `GET/PUT /v1/admin/payment-settings` | Commission rate (0-100, two decimals), what it is taken from (`online_amount` or `booking_total`), and the minimum payout (Rs 1 to Rs 10,00,000). Rate and base are set together or both cleared. Returns the rate a new payment would use and where it comes from |
| `GET/PUT/DELETE /v1/admin/salons/{id}/commission-rate` | An optional rate for one salon (0 is a real rate); the base stays the platform's |

- Rate for a new payment: salon rate, else platform rate, else the environment value. Base: platform, else environment. With no rate or no base the payment is refused; nothing is defaulted.
- A change applies to new payments only. Each payment keeps the rate, base and policy version it was charged at (`booking_payments` snapshot columns). The policy version (`db-N`, `db-N-salon`) rises with every change of rate or base.
- The wallet enforces and shows the admin's minimum payout; the built-in default applies until one is set.
- Every change is logged (admin id, old and new values). A durable audit table is not built.

## Payout proof (migration 0057, prepared, not applied)
A payout can only become `paid` with a recorded payment and a proof file. The database refuses the move otherwise
(`payout_paid_needs_recorded_payment`).

| Route (super admin) | Purpose |
|---|---|
| `POST /v1/admin/wallet/payout-requests/{id}/mark-paid` | Multipart: `reference` (1-100, unique across payouts, case/space-insensitive), `method` (`upi\|imps\|neft\|rtgs\|other`), `paid_at` (with time zone, not future, not before the request), `amount_paid_paise`, `adjustment_reason` (required when the amount differs from the request), optional `note` (200), `proof` (PNG, JPG, WebP or PDF, at most 5 MB, type read from the file's first bytes). One transaction: proof, payment, move to paid, audit row. Same reference again returns the stored payment. No `Idempotency-Key` needed |
| `GET .../payout-requests/{id}` | Detail: salon, owner, amounts, masked account, `balance_at_request` (collected, commission, refunds, available when the owner asked), payment, corrections, timeline |
| `GET .../payout-requests/{id}/proof` | The proof file itself (bytes, `Cache-Control: no-store`). Audited. Not a public URL |
| `POST .../payout-requests/{id}/corrections` | Multipart: `delta_paise` (+ more paid, - less), `reason`, `reference`, `proof`. Only on a paid payout; the paid record is never edited |
| `GET .../payout-requests/{id}/corrections/{cid}/proof` | A correction's proof file |
| `GET /v1/admin/wallet/payout-reconciliation?from&to` | Per Indian calendar day: requested, paid (actual), the requested amount of what was paid, difference, declined. At most 92 days |

- Proof files are stored in PostgreSQL (`payout_proofs.content`, bytea) so a file and its payment commit together or not at all: no orphan files, no separate store to secure. Volume is a few files a day.
- `payout_proofs`, `salon_payout_payments`, `salon_payout_corrections` and `payout_audit` are append-only (update, delete and truncate refused; a profile deletion may only blank the actor column).
- Owner wallet entries gain `paid_at` and `method`; the owner never receives the proof file.
- Payout requests keep a `balance_snapshot` taken when the owner asked, so the commission shown later is the one that applied then.
- Not built: a second admin approving large payouts (single admin today).
- Deploy order: apply 0057 before the code that reads it (the owner wallet history joins `salon_payout_payments`).
