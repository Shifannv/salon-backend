# Roadmap

Source: `docs/features.md`. Verify against the running release.

## Built
Auth and profiles, customer discovery and nearby search, owner workspace (services, staff, holidays, closures, QR), super-admin approval and placement, DB-backed availability and booking, booking actions and cancellation cutoff, notifications and push, walk-in QR booking, payment ledger and refunds, account deletion (SQL-verified, not staging-tested), support and email outbox, image variants (WebP families, committed 28bf921, local only, no live R2 or staging check).

## Dormant
Online payments (Cashfree and Razorpay adapters) until `PAYMENT_PROVIDER` and credentials are set. The account-deletion refund path until a provider exists.

## Not built
Cancellation penalty/no-show payout, reschedule limit and payout-hold services (rules approved, see domain-rules.md; no migrations or code yet), subscription payments and checkout, analytics and admin activity history, the public web account-deletion page (lives in the website repo), per-salon provider credentials, automatic booking release on payment failure, the reviewed financial purge of closed salons and the super-admin to owner review thread (designs: backend/docs/ACCOUNT_DELETION_FINANCIAL_PURGE_DESIGN.md, .plans/salon-review-thread-spec.md).
