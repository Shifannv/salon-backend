# Subscription & Promotion Foundation

## Current state

Migration `0018_subscription_foundation` creates the database tables.
`SUBSCRIPTION_PROVIDER=none` (default) means:

- No external payment calls.
- No webhook endpoints registered.
- All subscriptions remain inactive unless explicitly created by a super admin.
- The API and all apps continue functioning normally.

This is **manual super-admin control only** — not automatic subscription ranking.

## Tables created

| Table | Purpose |
|-------|---------|
| `subscription_plans` | Tier, ranking weight, price, billing interval |
| `salon_subscriptions` | Per-salon subscription state with period tracking |
| `subscription_provider_accounts` | Opaque provider references per salon |
| `subscription_events` | Idempotent event log for future webhook processing |

Indexes: plan code uniqueness, active-subscription-per-salon uniqueness (partial),
event provider/reference idempotency (partial), subscription status and salon lookups.

## Subscription statuses

`pending` → `trialing` → `active` → `past_due` → `expired`

Cancellation: any non-terminal → `cancelled`
Suspension: any non-terminal → `suspended`

## Promotion eligibility

`is_subscription_promotion_active(status, period_start, period_end, grace_end, now)`:

| Status | Eligible? |
|--------|-----------|
| `active` / `trialing` | During `[current_period_start, current_period_end)` |
| `cancelled` | Until `current_period_end` |
| `past_due` | Until `grace_period_end` |
| `expired` / `suspended` / `pending` | Never |

Invalid or missing dates → never eligible.

## Public discovery ordering

After visibility filter (`approved`, `active`, `profile_completed`):

1. `subscription ranking_weight DESC` (from active promotion)
2. `display_priority DESC` (super-admin manual control)
3. `distance_km ASC NULLS LAST`
4. `salon name ASC`
5. `salon ID ASC`

No subscription → weight 0 → falls back to existing ordering.

## Admin API contract

All under `/v1/admin/`, all require `super_admin` role.

### Plans

- `GET /subscription-plans` — list (optional `include_inactive`)
- `POST /subscription-plans` — create
- `PATCH /subscription-plans/{id}` — update
- `POST /subscription-plans/{id}/deactivate`

### Subscriptions

- `GET /salons/{id}/subscription` — view salon's non-terminal subscription
- `POST /salons/{id}/subscription/test` — manual/test activation (creates a record; NOT payment)
- `POST /subscriptions/{id}/cancel`
- `POST /subscriptions/{id}/suspend`

### Events

- `GET /subscription-events` — list processed events (optional `subscription_id` filter)

## What is NOT exposed

- Provider name, customer reference, subscription reference → admin-only, not in any response schema
- Ranking weight, display priority, plan tier, billing details → never in public salon responses
- No webhook endpoints exist yet
- No payment verification exists yet

## Config boundary

```
SUBSCRIPTION_PROVIDER=none     # current default
SUBSCRIPTION_PROVIDER=stripe   # future — add adapter + webhook route
SUBSCRIPTION_PROVIDER=razorpay # future — add adapter + webhook route
```

## Steps to add a future payment provider

1. Create `app/infrastructure/subscriptions/<provider>.py` implementing `SubscriptionProviderAdapter`
2. Add a webhook route in `app/api/v1/routes/webhooks.py` that:
   - Verifies signature using the adapter
   - Parses events into internal `SubscriptionEventType` commands
   - Records the event with idempotency (duplicate `provider_event_reference` is rejected)
   - Processes the command (create/renew/cancel/expire subscription)
3. Add `SUBSCRIPTION_PROVIDER=<name>` support in config
4. Register the webhook route only when the provider is configured
5. No changes needed to:
   - Customer app API models
   - Owner app API models
   - Public salon-list response shape
   - Ranking logic
   - Database domain tables

## Webhook preparation (not yet implemented)

The event-processing contract is ready:

- Provider event references must be unique (partial unique index)
- Event processing is idempotent (duplicate inserts rejected)
- Event status is recorded (`received` → `processing` → `processed` | `failed`)
- Failed processing is retryable (status + error_message tracked)
- Raw payload storage must avoid secrets and PII
- Provider payloads must not be trusted without signature verification
