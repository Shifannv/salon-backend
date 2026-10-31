# Domain rules

Source: `backend/docs/BOOKING_FLOW.md`, `AUTHORIZATION.md`, `ACCOUNT_DELETION.md`, `domain/entities/`.

## Roles
`customer`, `owner`, `staff`, `super_admin`. Role is read from `profiles`, never from JWT claims. `super_admin` needs `aal2` when `ADMIN_REQUIRE_MFA=true` (403 `mfa_required`). Ownership checks are in use cases; RLS is defense in depth.

## Booking
- Create only via Postgres `create_booking`; availability only via `get_available_slots`.
- Sources: `app`, `manual_walkin`, `qr_walkin`.
- Statuses in code: pending, confirmed, checked_in, no_show, rejected, completed, cancelled. Core flow: pending -> confirmed -> completed; pending -> rejected; pending/confirmed -> cancelled.
- Slot taken between availability and create -> 409. Client refetches availability.
- `salons.accepting_bookings=false` blocks all sources (409 `salon_not_accepting_bookings`).
- Customer cancellation is immediate before `CUSTOMER_CANCELLATION_CUTOFF_MINUTES`; after it, it is a request the salon decides.

## Payments
Ledger rows in `booking_payments`; a trigger recomputes `payment_status`, `paid_amount`, `refunded_amount`. Preferences: pay_at_salon, pay_advance, pay_full. Cash plus online beyond the total is refused (`payment_overcollection`). Online collection is DORMANT until `PAYMENT_PROVIDER` is set. Webhooks: `POST /v1/webhooks/{provider}`; the signature over the raw body is the only credential.

## Public salon visibility
`approval_status='approved'` AND `is_active` AND `profile_completed` for all public reads (list, search, nearby, details, services, staff, QR).

## Account deletion
Only customer and owner. Target is the JWT `sub`. Verification code, `DELETE` confirmation, immediate lockout, then durable background erasure by the account-deletion worker. Bookings are kept anonymized; an owner's salon becomes an inert "Closed salon" shell. Hard delete is allowed only here.

## Cancellation, no-show and payout holds (owner-approved U08 target; not released)
Source of truth: latest U08 amendment in `backend/docs/verification/payment-subscription-booking-spec.md`; historical U06/U07 remain applicable where not superseded. Local calculations/attendance guards do not activate money movement.
- Customer penalties: >=48 h min(INR20, captured); >=12 and <48 h 5%; >4 and <12 h 35%; exactly4 h or less 100%. Base is the captured amount before provider fees. Refund = captured minus penalty. Positive retained pool after actual non-refundable provider costs splits70% salon/30% platform, platform half-up to paise and residue to salon. A cost shortage is absorbed by platform, never deducted from the promised customer refund. Unknown provider cost keeps payout pending.
- Confirmed no-show (after start plus 10-minute grace, owner/staff confirms with actor/time/reason, customer notified) is treated as under-4-hour. Owner/admin cancellation before check-in: full async refund, platform bears non-recoverable fees, no salon payout unless separately approved.
- Reschedule: max two committed reschedules per booking, count never resets, secure new slot before releasing old, cancellation band uses the new start time.
- Changes require >4 h before the current start and newly valid SQL availability; no renewed salon approval. Prepaid cheaper changes retain the payment; upgrades require verified additional funds before commit. Unpaid Pay at Salon changes owe the new service price, including cheaper changes. Already-collected/advance money is not the unpaid case. Initial booking approval remains separate.
- New checkout has no separate processing surcharge and completed prepaid services have zero platform service commission. Preserve legacy policy/fee snapshots; provider-controlled funds require admin-approved release, with no internal split/provider-cost fields exposed to owners.
- Payout hold: customer cancellation `max(cancellation_time + 48 h, appointment_start)`; no-show `max(confirmation_time, start + 10 min) + 48 h`; blocked during dispute or fee uncertainty; admin cannot shorten it.
- Still open: checked-in cancellation remedy, TA06, TA09, dispute scope and provider evidence. The flat fee is now explicitly INR20 capped at captured; do not reopen that answered question.

## Subscription plan prices (owner-confirmed, 31 October 2026)
Authoritative production values (MCP-verified against live DB):
- growth_1m: ₹499 | growth_6m: ₹2,000 | growth_12m: ₹2,999
- premium_1m: ₹699 | premium_6m: ₹2,875 | premium_12m: ₹5,032

`premium_1m=699` is authoritative; any local source showing 599 is stale and must be updated.
Canonical test constant: `backend/tests/prices.py`. Harness expects 499/2000/2999.
0049 SQL migration sets 1675/2932 on a fresh DB from 0031 seed — that is historically correct for 0049 SQL tests, not the live price.

## Migration state (31 October 2026 — Gate B COMPLETE)
- Production alembic_version: `0050_plan_price_valid_until` (confirmed via MCP 2026-10-31)
- Gate B COMPLETE: 0041-0048 applied via alembic upgrade, 0049 stamped, 0050 applied
- All post-gate-b checks PASS: description/category columns dropped, triggers attached, prices verified
- Prices: growth_1m=499, growth_6m=2000, growth_12m=2999, premium_1m=699, premium_6m=2875, premium_12m=5032
- STAMP_ALLOWED_REVISIONS = {0040, 0049} (source code; 0049 was stamped this session)
- Gate C: 0051 additive (can apply); 0052 rewrites get_available_slots() — client compatibility required first
- `.claude/settings.json`: mcp__supabase__apply_migration moved to `allow` list (was `ask`)
- `migration_policy.py` patched: single-element tuple unwrap for Alembic 1.20 stamp compatibility
- backend/.env has two invalid values: EMAIL_WORKER_POLL_SECONDS=10N (should be 10), WALKIN_BASE_URL is JSON array (needs single URL)
