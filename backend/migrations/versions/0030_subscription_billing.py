"""Owner subscription billing: purchase ledger and atomic, idempotent activation.

* ``subscription_billing_records`` - one row per purchase attempt/payment. It snapshots the
  plan price, currency, interval and benefits AT PURCHASE TIME (a trigger makes the snapshot
  immutable), so later plan edits never rewrite history. ``provider_order_ref`` /
  ``provider_payment_ref`` are unique per provider and resolve a provider event to a salon.
  ``applied_at`` makes activation idempotent.
* ``apply_subscription_billing_record`` applies a PAID record to ``salon_subscriptions``
  atomically (advisory lock per salon + row lock) and exactly once. A purchase made while an
  active, past-due or cancelled-but-paid-through period exists EXTENDS that same row from its
  paid-through date, so ``uq_salon_subscriptions_active_per_salon`` is never fought and two
  overlapping active periods can never exist.
* ``cancel_salon_subscription_renewal`` / ``sweep_lapsed_subscriptions`` keep status
  bookkeeping inside SQL so the admin-only ``guard_subscription_admin`` trigger can recognise
  the trusted backend path (``app.subscription_system``) without opening a hole for owners.
* ``is_subscription_promotion_active`` also honours a stored grace window on ``active`` rows
  whose period has just ended (grace is stored when a period is paid; no default exists).
* Fixes a latent 0018/0021 defect: ``subscription_plans`` and ``salon_subscriptions`` lacked the
  ``created_by`` column that ``set_audit_actor`` writes, so inserts and updates failed.
* Plans: ``features`` (benefits jsonb) and ``tax_inclusive`` (NULL = undecided), CHECKs on
  currency/interval/price (``not valid`` first, then validated only when existing data allows).

Every statement is idempotent and its own ``op.execute`` (asyncpg prepares one at a time).
Reviewed deploy step only.

Revision ID: 0030_subscription_billing
Revises: 0029_payment_monetary_policy
Create Date: 2026-10-13 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0030_subscription_billing"
down_revision: str | Sequence[str] | None = "0029_payment_monetary_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ANOMALY_KINDS_OLD = (
    "'overcollection', 'amount_mismatch', 'settlement_failed', "
    "'settlement_reversed', 'refund_onhold', 'refund_failed'"
)
_ANOMALY_KINDS_NEW = _ANOMALY_KINDS_OLD + (
    ", 'subscription_amount_mismatch', 'subscription_duplicate_payment', "
    "'subscription_blocked', 'subscription_refund', 'subscription_unused_period'"
)


def _sql(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


def _validate(constraint: str) -> str:
    return f"""
    do $$ begin
      alter table public.subscription_plans validate constraint {constraint};
    exception when check_violation then
      raise notice 'existing subscription_plans rows violate {constraint}; left NOT VALID';
    end $$
    """


_PROMOTION_FN = """
create or replace function public.is_subscription_promotion_active(
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
    if p_current_start is not null and p_current_end is not null
       and p_now >= p_current_start and p_now < p_current_end then
      return true;
    end if;
    -- A paid period stores its grace window; just-ended periods keep the benefit until then.
    return p_current_end is not null and p_grace_end is not null
       and p_now >= p_current_end and p_now < p_grace_end;
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
end $$
"""

_PROMOTION_FN_LEGACY = """
create or replace function public.is_subscription_promotion_active(
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
end $$
"""

_GUARD = """
create or replace function public.guard_subscription_admin() returns trigger
language plpgsql set search_path = public as $$
begin
  if auth.uid() is null then
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  -- The backend's own SQL functions (payment activation, cancel, lapse sweep) run on behalf
  -- of an owner. Never honoured for the browser-facing roles.
  if current_setting('app.subscription_system', true) = 'on'
     and current_user not in ('anon', 'authenticated') then
    return new;
  end if;
  raise exception 'Super admin required for subscription management'
    using errcode = '42501';
  return null;
end $$
"""

_GUARD_LEGACY = """
create or replace function public.guard_subscription_admin() returns trigger
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
end $$
"""

_BILLING_GUARD = """
create or replace function public.tg_subscription_billing_guard()
returns trigger language plpgsql set search_path = public as $$
begin
  if new.salon_id is distinct from old.salon_id
     or new.plan_id is distinct from old.plan_id
     or new.provider is distinct from old.provider
     or new.receipt is distinct from old.receipt
     or new.amount is distinct from old.amount
     or new.currency is distinct from old.currency
     or new.billing_interval is distinct from old.billing_interval
     or new.benefits is distinct from old.benefits
     or new.plan_code is distinct from old.plan_code then
    raise exception 'subscription_billing_snapshot_is_immutable' using errcode = '23514';
  end if;
  if old.provider_order_ref is not null
     and new.provider_order_ref is distinct from old.provider_order_ref then
    raise exception 'subscription_billing_order_is_immutable' using errcode = '23514';
  end if;
  if old.provider_payment_ref is not null
     and new.provider_payment_ref is distinct from old.provider_payment_ref then
    raise exception 'subscription_billing_payment_is_immutable' using errcode = '23514';
  end if;
  if old.applied_at is not null
     and (new.applied_at is distinct from old.applied_at
          or new.period_start is distinct from old.period_start
          or new.period_end is distinct from old.period_end
          or new.subscription_id is distinct from old.subscription_id) then
    raise exception 'subscription_billing_application_is_immutable' using errcode = '23514';
  end if;
  if old.status in ('paid', 'partially_refunded', 'refunded')
     and new.status in ('created', 'authorized', 'failed', 'expired') then
    raise exception 'subscription_billing_status_regression' using errcode = '23514';
  end if;
  if old.status = 'refunded' and new.status in ('paid', 'partially_refunded') then
    raise exception 'subscription_billing_status_regression' using errcode = '23514';
  end if;
  return new;
end $$
"""

_APPLY = """
create or replace function public.apply_subscription_billing_record(
  p_record_id uuid, p_grace_days integer
) returns text language plpgsql set search_path = public as $$
declare
  v_rec     public.subscription_billing_records%rowtype;
  v_sub     public.salon_subscriptions%rowtype;
  v_owner   uuid;
  v_months  integer;
  v_now     timestamptz := now();
  v_base    timestamptz;
  v_start   timestamptz;
  v_end     timestamptz;
  v_grace   timestamptz;
  v_sub_id  uuid;
  v_outcome text;
begin
  if p_grace_days is null or p_grace_days < 0 then
    raise exception 'grace_days_required' using errcode = '22023';
  end if;
  select * into v_rec from public.subscription_billing_records where id = p_record_id;
  if not found then
    return 'not_found';
  end if;
  -- One writer per salon, then re-read the record under its row lock.
  perform pg_advisory_xact_lock(hashtextextended('subscription:' || v_rec.salon_id::text, 0));
  select * into v_rec from public.subscription_billing_records
  where id = p_record_id for update;
  if v_rec.applied_at is not null then
    return 'already_applied';
  end if;
  if v_rec.status not in ('paid', 'partially_refunded') then
    return 'not_paid';
  end if;
  select owner_id into v_owner from public.salons where id = v_rec.salon_id;
  if v_owner is null then
    return 'blocked_closed';
  end if;
  v_months := case v_rec.billing_interval
    when 'monthly' then 1 when 'quarterly' then 3 when 'semiannual' then 6 when 'yearly' then 12
  end;
  if v_months is null then
    raise exception 'unknown_billing_interval' using errcode = '22023';
  end if;

  perform set_config('app.subscription_system', 'on', true);
  select * into v_sub from public.salon_subscriptions
  where salon_id = v_rec.salon_id order by created_at desc, id desc limit 1 for update;

  if found and v_sub.status = 'suspended' then
    perform set_config('app.subscription_system', 'off', true);
    return 'blocked_suspended';
  end if;

  if found and (v_sub.status in ('pending', 'trialing', 'active', 'past_due')
                or (v_sub.status = 'cancelled' and v_sub.current_period_end > v_now)) then
    -- Renewal: extend the SAME row from its paid-through date (or from now when it lapsed).
    if v_sub.current_period_end is not null and v_sub.current_period_end > v_now then
      v_base := v_sub.current_period_end;
      v_start := coalesce(v_sub.current_period_start, v_now);
    else
      v_base := v_now;
      v_start := v_now;
    end if;
    v_end := v_base + make_interval(months => v_months);
    v_grace := v_end + make_interval(days => p_grace_days);
    v_outcome := case when v_sub.current_period_end is null then 'started' else 'renewed' end;
    update public.salon_subscriptions
    set plan_id = v_rec.plan_id, status = 'active',
        starts_at = coalesce(starts_at, v_start),
        current_period_start = v_start, current_period_end = v_end,
        cancelled_at = null, expires_at = null, grace_period_end = v_grace
    where id = v_sub.id;
    v_sub_id := v_sub.id;
  else
    v_base := v_now;
    v_start := v_now;
    v_end := v_now + make_interval(months => v_months);
    v_grace := v_end + make_interval(days => p_grace_days);
    v_outcome := 'started';
    insert into public.salon_subscriptions
      (salon_id, plan_id, status, starts_at, current_period_start, current_period_end,
       grace_period_end)
    values (v_rec.salon_id, v_rec.plan_id, 'active', v_now, v_start, v_end, v_grace)
    returning id into v_sub_id;
  end if;

  update public.subscription_billing_records
  set period_start = v_base, period_end = v_end, applied_at = v_now, subscription_id = v_sub_id
  where id = v_rec.id;
  perform set_config('app.subscription_system', 'off', true);
  return v_outcome;
end $$
"""

_CANCEL = """
create or replace function public.cancel_salon_subscription_renewal(p_salon_id uuid)
returns text language plpgsql set search_path = public as $$
declare
  v_sub public.salon_subscriptions%rowtype;
begin
  perform pg_advisory_xact_lock(hashtextextended('subscription:' || p_salon_id::text, 0));
  select * into v_sub from public.salon_subscriptions
  where salon_id = p_salon_id order by created_at desc, id desc limit 1 for update;
  if not found then
    return 'none';
  end if;
  if v_sub.status = 'cancelled' then
    return 'already_cancelled';
  end if;
  if v_sub.status in ('expired', 'suspended') then
    return 'not_cancellable';
  end if;
  perform set_config('app.subscription_system', 'on', true);
  update public.salon_subscriptions
  set status = 'cancelled', cancelled_at = now()
  where id = v_sub.id;
  perform set_config('app.subscription_system', 'off', true);
  return 'cancelled';
end $$
"""

_SWEEP = """
create or replace function public.sweep_lapsed_subscriptions()
returns integer language plpgsql set search_path = public as $$
declare
  n integer := 0;
  c integer;
begin
  perform set_config('app.subscription_system', 'on', true);
  -- Period over and a stored grace window still open -> past_due; otherwise expired.
  update public.salon_subscriptions
  set status = cast(case when grace_period_end is not null and grace_period_end > now()
                         then 'past_due' else 'expired' end as subscription_status),
      expires_at = case when grace_period_end is not null and grace_period_end > now()
                        then expires_at else now() end
  where status in ('active', 'trialing') and current_period_end is not null
    and current_period_end <= now();
  get diagnostics c = row_count;
  n := n + c;
  update public.salon_subscriptions
  set status = 'expired', expires_at = now()
  where status = 'past_due'
    and coalesce(grace_period_end, current_period_end) is not null
    and coalesce(grace_period_end, current_period_end) <= now();
  get diagnostics c = row_count;
  n := n + c;
  perform set_config('app.subscription_system', 'off', true);
  return n;
end $$
"""


def upgrade() -> None:
    # ---------------------------------------------------- latent 0018/0021 audit-column bug
    # ``set_audit_actor`` (0021) writes ``created_by`` and ``updated_by``; 0018 gave these two
    # tables only ``updated_by``, so every INSERT/UPDATE on them failed with 'record "new" has
    # no field "created_by"'. Additive and kept on downgrade (the trigger needs it).
    _sql(
        "alter table public.subscription_plans add column if not exists created_by uuid references public.profiles(id)",
        "alter table public.salon_subscriptions add column if not exists created_by uuid references public.profiles(id)",
    )

    # ------------------------------------------------------------------ plan columns
    _sql(
        """
        alter table public.subscription_plans
          add column if not exists features jsonb not null default '{}'::jsonb,
          add column if not exists tax_inclusive boolean
        """,
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_currency",
        """
        alter table public.subscription_plans add constraint ck_subscription_plans_currency
          check (currency ~ '^[A-Z]{3}$') not valid
        """,
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_interval",
        """
        alter table public.subscription_plans add constraint ck_subscription_plans_interval
          check (billing_interval in ('monthly', 'quarterly', 'semiannual', 'yearly')) not valid
        """,
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_price",
        """
        alter table public.subscription_plans add constraint ck_subscription_plans_price
          check (price_amount >= 0) not valid
        """,
        _validate("ck_subscription_plans_currency"),
        _validate("ck_subscription_plans_interval"),
        _validate("ck_subscription_plans_price"),
    )

    # --------------------------------------------------------------- billing ledger
    _sql(
        """
        create table if not exists public.subscription_billing_records (
          id                   uuid primary key default gen_random_uuid(),
          salon_id             uuid not null references public.salons(id),
          plan_id              uuid not null references public.subscription_plans(id),
          plan_code            text not null,
          provider             text not null,
          receipt              text not null check (char_length(receipt) between 8 and 40),
          provider_order_ref   text,
          provider_payment_ref text,
          status               text not null default 'created'
            check (status in ('created', 'authorized', 'paid', 'failed', 'expired',
                              'refunded', 'partially_refunded')),
          amount               numeric(10,2) not null check (amount > 0),
          currency             varchar(3) not null check (currency ~ '^[A-Z]{3}$'),
          billing_interval     text not null
            check (billing_interval in ('monthly', 'quarterly', 'semiannual', 'yearly')),
          tax_amount           numeric(10,2) check (tax_amount is null or tax_amount >= 0),
          tax_inclusive        boolean,
          benefits             jsonb not null default '{}'::jsonb,
          refunded_amount      numeric(10,2) not null default 0
            check (refunded_amount >= 0 and refunded_amount <= amount),
          period_start         timestamptz,
          period_end           timestamptz,
          subscription_id      uuid references public.salon_subscriptions(id),
          expires_at           timestamptz not null,
          paid_at              timestamptz,
          applied_at           timestamptz,
          failure_code         text check (failure_code is null or char_length(failure_code) <= 120),
          created_by           uuid references public.profiles(id),
          updated_by           uuid references public.profiles(id),
          created_at           timestamptz not null default now(),
          updated_at           timestamptz not null default now(),
          constraint uq_subscription_billing_receipt unique (receipt),
          constraint ck_subscription_billing_period
            check ((period_start is null and period_end is null)
                   or (period_start is not null and period_end > period_start)),
          constraint ck_subscription_billing_applied
            check (applied_at is null or (period_end is not null and subscription_id is not null)),
          constraint ck_subscription_billing_paid_ref
            check (status not in ('paid', 'partially_refunded', 'refunded')
                   or provider_payment_ref is not null)
        )
        """,
        """
        create unique index if not exists uq_subscription_billing_order
          on public.subscription_billing_records(provider, provider_order_ref)
          where provider_order_ref is not null
        """,
        """
        create unique index if not exists uq_subscription_billing_payment
          on public.subscription_billing_records(provider, provider_payment_ref)
          where provider_payment_ref is not null
        """,
        # One open purchase per salon: a second checkout resumes it instead of stacking orders.
        """
        create unique index if not exists uq_subscription_billing_open_per_salon
          on public.subscription_billing_records(salon_id)
          where status in ('created', 'authorized')
        """,
        """
        create index if not exists idx_subscription_billing_salon
          on public.subscription_billing_records(salon_id, created_at desc)
        """,
        """
        create index if not exists idx_subscription_billing_open
          on public.subscription_billing_records(updated_at)
          where status in ('created', 'authorized')
        """,
        """
        create index if not exists idx_subscription_billing_unapplied
          on public.subscription_billing_records(updated_at)
          where status in ('paid', 'partially_refunded') and applied_at is null
        """,
        "drop trigger if exists t_subscription_billing_records_updated on public.subscription_billing_records",
        """
        create trigger t_subscription_billing_records_updated
          before update on public.subscription_billing_records
          for each row execute function set_updated_at()
        """,
        "drop trigger if exists t_subscription_billing_records_audit on public.subscription_billing_records",
        """
        create trigger t_subscription_billing_records_audit
          before insert or update on public.subscription_billing_records
          for each row execute function set_audit_actor()
        """,
        _BILLING_GUARD,
        "drop trigger if exists subscription_billing_guard on public.subscription_billing_records",
        """
        create trigger subscription_billing_guard
          before update on public.subscription_billing_records
          for each row execute function public.tg_subscription_billing_guard()
        """,
        "alter table public.subscription_billing_records enable row level security",
        "revoke all on public.subscription_billing_records from public, anon, authenticated",
        "grant all on public.subscription_billing_records to postgres, service_role",
    )

    # ------------------------------------------------------- functions and anomalies
    _sql(
        _PROMOTION_FN,
        _GUARD,
        _APPLY,
        _CANCEL,
        _SWEEP,
        "revoke execute on function public.apply_subscription_billing_record(uuid, integer) from public, anon, authenticated",
        "revoke execute on function public.cancel_salon_subscription_renewal(uuid) from public, anon, authenticated",
        "revoke execute on function public.sweep_lapsed_subscriptions() from public, anon, authenticated",
        "alter table public.payment_anomalies drop constraint if exists payment_anomalies_kind_check",
        f"""
        alter table public.payment_anomalies add constraint payment_anomalies_kind_check
          check (kind in ({_ANOMALY_KINDS_NEW}))
        """,
    )


def downgrade() -> None:
    """Drop the billing ledger. Loses every purchase record; subscriptions rows are kept."""

    _sql(
        "drop function if exists public.sweep_lapsed_subscriptions()",
        "drop function if exists public.cancel_salon_subscription_renewal(uuid)",
        "drop function if exists public.apply_subscription_billing_record(uuid, integer)",
        "delete from public.payment_anomalies where kind like 'subscription\\_%'",
        "alter table public.payment_anomalies drop constraint if exists payment_anomalies_kind_check",
        f"""
        alter table public.payment_anomalies add constraint payment_anomalies_kind_check
          check (kind in ({_ANOMALY_KINDS_OLD}))
        """,
        _GUARD_LEGACY,
        _PROMOTION_FN_LEGACY,
        "drop table if exists public.subscription_billing_records",
        "drop function if exists public.tg_subscription_billing_guard()",
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_price",
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_interval",
        "alter table public.subscription_plans drop constraint if exists ck_subscription_plans_currency",
        """
        alter table public.subscription_plans
          drop column if exists tax_inclusive,
          drop column if exists features
        """,
    )
