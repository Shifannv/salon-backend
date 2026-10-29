# Owner finance: Phase 3 (owner app) record

Date: 2026-10-29. Status: **built and tested against mocked responses; not verified against a live
backend** (the backend, migration 0051 included, is not deployed anywhere). Nothing was committed,
pushed, deployed, migrated or built for a store.

Decisions F01-F12 in the [approval register](../migrations/payment-subscription-booking-designs/APPROVAL_REGISTER.md)
govern this build.

## What the owner sees

| Where | What |
| --- | --- |
| Sidebar, "Finance" | Opens the Finance screen. There is no sixth bottom tab. |
| Finance, "Daily ledger" | One salon-local day: gross completed sales, cash received, non-cash received, still to collect, expenses, cash refunds, cash drawer (opening, expected, counted, difference), with a previous/next-day stepper that cannot go past today. |
| Finance, "Expenses" | The day's expenses and cancelling entries. Cancelling asks first and appends a mirror entry; the original is never edited or removed. |
| Finance, "History" | The last 14 days with the server's totals; a day opens in the ledger. |
| Home and Reports, "Today's finance" | Cash received, non-cash received, expenses, expected closing cash, and "View Daily Ledger". Hidden when finance is not switched on, not in the plan, or the account is not the owner. |
| Sheets | Add expense, Correct the cash drawer, Close the day. |

## Rules the build keeps

- **The app adds nothing up.** Every figure, including "Expenses" (`expenses_total_paise`) and the
  history totals, is the server's. The only arithmetic on the phone is turning typed rupees into
  integer paise (`src/lib/money.ts`, no floating point) and back into text.
- **Paise only (F01).** The repository refuses a fractional or missing amount instead of showing it.
- **No internal fields (F02).** The screens have no field for platform or salon allocation, gateway
  fees, commission percentages or other staff's earnings, and no "profit" figure. The API response
  does not carry them either. Staff earnings and commission settings are not built yet.
- **Opening cash (F03).** The first close asks for it. When the day before was not closed the
  ledger says the figure is only a suggestion; the close sheet pre-fills it, labels it "please
  confirm", and it is sent only when the owner submits. It is never assumed to be zero.
- **Owner only (F04).** A non-owner gets "Owner access only"; the Home card stays hidden.
- **Read-only after the plan ends (F05, F11).** The server sends `can_write: false`; the app hides
  every write control and says why. Past records stay visible. A missing flag counts as read-only.
- **Cash refunds (F12).** "Correct the cash drawer" is worded as an internal correction ("this is not
  how you refund a customer"). There is no refund button; the Cash Refund event comes later.
- **Provisional figures.** While the server says `needs_review`, the screens label the day
  provisional, show "Expected closing cash (provisional)" and refuse to close it.
- **Safe writes.** Buttons disable while saving. One idempotency key per distinct submission
  (`useIdempotencyKey`): the same key on a retry (the server replays), a new key as soon as any field
  changes (the server would refuse one key with two bodies). Cancelling an expense uses a stable key.
- **Never persisted.** The `finance` query root is not in the cache allowlist, so money figures are not
  written to storage. Server error text is never shown.

## Tests

`tests/screens/finance.test.tsx` (27), `todays-finance-card.test.tsx` (8), `sidebar-finance.test.tsx`
(2), `finance.repository.test.ts`, `useIdempotencyKey.test.ts`, `money.test.ts`,
`messages.test.ts`, `occurred-at.test.ts`, plus error-copy and date helper tests.

## Not verified, and why

- **Layout on a phone with real numbers.** There is no backend to answer. Only the "not available
  yet" state could be checked on the device.
- **The backend contract against a deployed API.** `EXPO_PUBLIC_API_URL` points at the production
  API, which does not have these routes. Changing that would be a guess about environment values.

## Still to do

Staff earnings and commission settings (F02, F07, F10), the Cash Refund event (F12), analytics fed
from the same server source as Finance, the retention purge (F06, blocked on the period), and deploying
the backend (migration 0051 needs its own reviewed, approved rollout).
