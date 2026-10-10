"""Provider-agnostic subscription and salon-promotion foundation.

Creates subscription_plans, salon_subscriptions, subscription_provider_accounts,
and subscription_events.  No payment provider is integrated; the domain model
is provider-independent by design.

Revision ID: 0018_subscription_foundation
Revises: 0017_salon_display_priority
"""

from alembic import op

revision = "0018_subscription_foundation"
down_revision = "0017_salon_display_priority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Subscription statuses ---
    op.execute("""
create type subscription_status as enum (
  'pending', 'trialing', 'active', 'past_due', 'cancelled', 'expired', 'suspended'
);
    """)

    # --- Subscription event processing ---
    op.execute("""
create type subscription_event_processing_status as enum (
  'received', 'processing', 'processed', 'failed'
);
    """)

    # --- Plans ---
    op.execute("""
create table subscription_plans (
  id              uuid primary key default gen_random_uuid(),
  code            varchar(60) not null unique,
  name            varchar(120) not null,
  description     text,
  tier            smallint not null default 0,
  ranking_weight  integer not null default 0
    constraint subscription_plans_ranking_weight_range
    check (ranking_weight between 0 and 100000),
  price_amount    numeric(10,2) not null default 0,
  currency        varchar(3) not null default 'INR',
  billing_interval varchar(20) not null default 'monthly',
  is_active       boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  updated_by      uuid references profiles(id)
);
    """)

    op.execute("""
create trigger t_subscription_plans_audit before insert or update on subscription_plans
  for each row execute function set_audit_actor();
    """)

    # --- Provider accounts (one per salon, opaque provider strings) ---
    op.execute("""
create table subscription_provider_accounts (
  id                              uuid primary key default gen_random_uuid(),
  salon_id                        uuid not null references salons(id),
  provider_name                   varchar(60),
  provider_customer_reference     varchar(400),
  provider_subscription_reference varchar(400),
  created_at                      timestamptz not null default now(),
  updated_at                      timestamptz not null default now(),
  unique (salon_id, provider_name)
);
    """)

    # --- Subscriptions ---
    op.execute("""
create table salon_subscriptions (
  id                    uuid primary key default gen_random_uuid(),
  salon_id              uuid not null references salons(id),
  plan_id               uuid not null references subscription_plans(id),
  status                subscription_status not null default 'pending',
  starts_at             timestamptz,
  current_period_start  timestamptz,
  current_period_end    timestamptz,
  cancelled_at          timestamptz,
  expires_at            timestamptz,
  grace_period_end      timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  updated_by            uuid references profiles(id)
);
    """)

    op.execute("""
create trigger t_salon_subscriptions_audit before insert or update on salon_subscriptions
  for each row execute function set_audit_actor();
    """)

    op.execute("""
create index idx_salon_subscriptions_salon_id on salon_subscriptions(salon_id);
    """)

    op.execute("""
create index idx_salon_subscriptions_status   on salon_subscriptions(status);
    """)

    # Prevent duplicate non-terminal subscriptions per salon.
    op.execute("""
create unique index uq_salon_subscriptions_active_per_salon
  on salon_subscriptions(salon_id)
  where status not in ('expired', 'cancelled', 'suspended');
    """)

    # --- Subscription events ---
    op.execute("""
create table subscription_events (
  id                           uuid primary key default gen_random_uuid(),
  salon_subscription_id        uuid references salon_subscriptions(id),
  provider_name                varchar(60),
  provider_event_reference     varchar(400),
  event_type                   varchar(80) not null,
  payload_hash                 varchar(128),
  received_at                  timestamptz not null default now(),
  processed_at                 timestamptz,
  processing_status            subscription_event_processing_status not null default 'received',
  error_message                text
);
    """)

    op.execute("""
create index idx_subscription_events_subscription
  on subscription_events(salon_subscription_id);
    """)

    # Provider event idempotency: a (provider, reference) pair is unique.
    op.execute("""
create unique index uq_subscription_events_provider_ref
  on subscription_events(provider_name, provider_event_reference)
  where provider_name is not null and provider_event_reference is not null;
    """)

    # --- Server-side eligibility function ---
    op.execute("""
create function is_subscription_promotion_active(
  p_status         subscription_status,
  p_current_start  timestamptz,
  p_current_end    timestamptz,
  p_grace_end      timestamptz,
  p_now            timestamptz default now()
)
returns boolean
language plpgsql immutable as $$
begin
  if p_status in ('active', 'trialing') then
    return p_current_start is not null
       and p_current_end is not null
       and p_now >= p_current_start
       and p_now < p_current_end;
  end if;
  if p_status = 'cancelled' then
    return p_current_end is not null
       and p_now < p_current_end;
  end if;
  if p_status = 'past_due' then
    return p_grace_end is not null
       and p_now < p_grace_end;
  end if;
  return false;
end $$;
    """)

    # --- Guard: only super admins may manage plans and subscription state ---
    op.execute("""
create function guard_subscription_admin() returns trigger
language plpgsql set search_path = public as $$
begin
  if auth.uid() is null then
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  raise exception 'Super admin required for subscription management'
    using errcode = '42501';
  return null;
end $$;
    """)

    op.execute("""
create trigger subscription_plans_guard_admin
  before insert or update or delete on subscription_plans
  for each row execute function guard_subscription_admin();
    """)
    op.execute("""
create trigger salon_subscriptions_guard_admin
  before insert or update or delete on salon_subscriptions
  for each row execute function guard_subscription_admin();
    """)


def downgrade() -> None:
    op.execute("drop trigger salon_subscriptions_guard_admin on salon_subscriptions")
    op.execute("drop trigger subscription_plans_guard_admin on subscription_plans")
    op.execute("drop function guard_subscription_admin()")
    op.execute("drop function is_subscription_promotion_active(subscription_status, timestamptz, timestamptz, timestamptz, timestamptz)")
    op.execute("drop index uq_subscription_events_provider_ref")
    op.execute("drop index idx_subscription_events_subscription")
    op.execute("drop table subscription_events")
    op.execute("drop index uq_salon_subscriptions_active_per_salon")
    op.execute("drop index idx_salon_subscriptions_status")
    op.execute("drop index idx_salon_subscriptions_salon_id")
    op.execute("drop trigger t_salon_subscriptions_audit on salon_subscriptions")
    op.execute("drop table salon_subscriptions")
    op.execute("drop table subscription_provider_accounts")
    op.execute("drop trigger t_subscription_plans_audit on subscription_plans")
    op.execute("drop table subscription_plans")
    op.execute("drop type subscription_event_processing_status")
    op.execute("drop type subscription_status")
