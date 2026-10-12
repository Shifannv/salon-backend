"""Seed the Growth and Premium subscription plans (1 / 6 / 12 months).

Idempotent: ``insert ... on conflict (code) do nothing`` never overwrites a row an admin has
edited. Prices are the plan price as supplied (INR); whether GST is included is an OPEN business
decision, so ``tax_inclusive`` stays NULL ("unknown") rather than guessing.

Benefits (``features``): Growth = unlimited_bookings, split_bill, daily_ledger. Premium = Growth +
rank_boost, smart_slot_filler, sms_alerts (``monthly_alert_cap`` 300). ``ranking_weight`` is 0 for
Growth and 1 for Premium: only the relative order matters to discovery, and an admin can edit it.

Revision ID: 0031_seed_subscription_plans
Revises: 0030_subscription_billing
Create Date: 2026-10-13 09:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0031_seed_subscription_plans"
down_revision: str | Sequence[str] | None = "0030_subscription_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GROWTH = """'{"unlimited_bookings": true, "split_bill": true, "daily_ledger": true}'::jsonb"""
_PREMIUM = (
    """'{"unlimited_bookings": true, "split_bill": true, "daily_ledger": true, """
    """"rank_boost": true, "smart_slot_filler": true, "sms_alerts": true, """
    """"monthly_alert_cap": 300}'::jsonb"""
)

_CODES = ("growth_1m", "growth_6m", "growth_12m", "premium_1m", "premium_6m", "premium_12m")


def upgrade() -> None:
    op.execute(
        f"""
        insert into public.subscription_plans
          (code, name, tier, ranking_weight, price_amount, billing_interval, features)
        values
  ('growth_1m', 'Growth - 1 month', 1, 0, 349.00, 'monthly', {_GROWTH}),
  ('growth_6m', 'Growth - 6 months', 1, 0, 1499.00, 'semiannual', {_GROWTH}),
  ('growth_12m', 'Growth - 12 months', 1, 0, 1999.00, 'yearly', {_GROWTH}),
  ('premium_1m', 'Premium - 1 month', 2, 1, 599.00, 'monthly', {_PREMIUM}),
  ('premium_6m', 'Premium - 6 months', 2, 1, 2499.00, 'semiannual', {_PREMIUM}),
  ('premium_12m', 'Premium - 12 months', 2, 1, 3499.00, 'yearly', {_PREMIUM})
        on conflict (code) do nothing
        """
    )


def downgrade() -> None:
    """Remove only seeded plans nobody has bought or subscribed to."""

    codes = ", ".join(f"'{c}'" for c in _CODES)
    op.execute(
        f"""
        delete from public.subscription_plans p
        where p.code in ({codes})
          and not exists (select 1 from public.salon_subscriptions s where s.plan_id = p.id)
          and not exists (select 1 from public.subscription_billing_records b where b.plan_id = p.id)
        """
    )
