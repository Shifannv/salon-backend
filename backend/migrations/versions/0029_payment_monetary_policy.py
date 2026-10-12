"""Payment monetary policy: commission snapshot, overcollection, anomalies, audit.

* ``booking_payments`` gains an immutable commission snapshot (rate, base, amount, policy
  version) written once at intent time, nullable provider fee/tax columns that are kept apart
  from the platform commission, ``overcollected_amount`` (excess captured beyond what the booking
  was owed) and ``provider_order_confirmed_at`` (crash-safety marker: the provider acknowledged
  the order).
* ``payment_refunds`` gains ``commission_reversal_amount`` (the proportional share of the
  snapshot returned) and ``applies_to_excess`` (a refund of the overcollected part, which must
  not reduce the booking's paid state).
* ``recompute_booking_payment_state`` no longer needs a capture to be refused: excess money is
  recorded on the row and excluded from the booking's paid cache. The ``payment_overcollection``
  exception stays as a last-resort guard (manual cash that would exceed the total).
* ``payment_anomalies``: operator-visible rows (overcollection, amount mismatch, settlement
  failure, refund on hold). ``payment_provider_account_audit``: every payee registration and
  status change.
* ``payment_provider_accounts.registration_generation`` supports re-registration after a bank
  detail change without storing any bank detail.

Every statement is idempotent (``if not exists`` / ``or replace`` / drop-then-create) and is its
own ``op.execute`` because asyncpg prepares one statement per call. Reviewed deploy step only.

Revision ID: 0029_payment_monetary_policy
Revises: 0028_account_erasure_hardening
Create Date: 2026-10-12 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029_payment_monetary_policy"
down_revision: str | Sequence[str] | None = "0028_account_erasure_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TABLES = ("payment_anomalies", "payment_provider_account_audit")


def _sql(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


# ------------------------------------------------------------------ new functions
_RECOMPUTE = """
create or replace function public.recompute_booking_payment_state(p_booking_id uuid)
returns void language plpgsql set search_path = public as $$
declare
  v_total     numeric(10,2);
  v_paid      numeric(10,2);
  v_refunded  numeric(10,2);
  v_count     integer;
  v_net       numeric(10,2);
  v_method    text;
  v_at        timestamptz;
  v_by        uuid;
  v_new       public.payment_status;
begin
  select total_price into v_total from public.bookings where id = p_booking_id for update;
  if not found then
    return;
  end if;

  -- Money collected beyond what the booking was owed (overcollected_amount) is recorded on
  -- its ledger row but never counts towards the booking's paid state.
  select coalesce(sum(p.amount - p.overcollected_amount), 0), count(*) into v_paid, v_count
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded');

  -- A refund of the excess does not reduce the paid state either.
  select coalesce(sum(r.amount), 0) into v_refunded
  from public.payment_refunds r
  where r.booking_id = p_booking_id and r.status = 'processed' and not r.applies_to_excess;

  v_net := v_paid - v_refunded;
  if v_net > v_total then
    raise exception 'payment_overcollection'
      using errcode = '23514',
            detail = format('booking %s: net collected %s exceeds total %s',
                            p_booking_id, v_net, v_total);
  end if;

  v_new := case when v_count > 0 and v_net >= v_total then 'paid' else 'unpaid' end;

  select case when p.channel = 'gateway' then 'online' else coalesce(p.method, 'cash') end,
         p.captured_at, p.recorded_by
    into v_method, v_at, v_by
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded')
    and p.amount > p.overcollected_amount
  order by p.captured_at desc nulls last, p.created_at desc
  limit 1;

  perform set_config('app.payment_recompute', 'on', true);
  update public.bookings
  set paid_amount = v_paid,
      refunded_amount = v_refunded,
      payment_status = v_new,
      payment_method = case when v_count > 0 and (v_net > 0 or v_new = 'paid')
                            then v_method::public.payment_method else null end,
      payment_recorded_at = case when v_new = 'paid'
                                 then coalesce(v_at, payment_recorded_at, now()) else null end,
      payment_recorded_by = case when v_new = 'paid'
                                 then coalesce(v_by, payment_recorded_by) else null end
  where id = p_booking_id;
  perform set_config('app.payment_recompute', 'off', true);
end $$
"""

_PAYMENT_GUARD = """
create or replace function public.tg_booking_payments_guard()
returns trigger language plpgsql set search_path = public as $$
begin
  if new.booking_id is distinct from old.booking_id
     or new.amount is distinct from old.amount
     or new.intent_reference is distinct from old.intent_reference
     or new.channel is distinct from old.channel then
    raise exception 'booking_payment_identity_is_immutable' using errcode = '23514';
  end if;
  -- The commission snapshot is written once, at intent time, and never recomputed.
  if new.commission_rate_percent is distinct from old.commission_rate_percent
     or new.commission_base is distinct from old.commission_base
     or new.platform_commission_amount is distinct from old.platform_commission_amount
     or new.commission_policy_version is distinct from old.commission_policy_version then
    raise exception 'booking_payment_commission_snapshot_is_immutable' using errcode = '23514';
  end if;
  -- The excess is decided at the moment of capture and fixed afterwards.
  if old.status in ('captured', 'partially_refunded', 'refunded')
     and new.overcollected_amount is distinct from old.overcollected_amount then
    raise exception 'booking_payment_overcollection_is_immutable' using errcode = '23514';
  end if;
  if old.status in ('captured', 'partially_refunded', 'refunded')
     and new.status in ('created', 'authorized', 'failed', 'cancelled', 'expired') then
    raise exception 'booking_payment_status_regression' using errcode = '23514';
  end if;
  return new;
end $$
"""

_REFUND_GUARD = """
create or replace function public.tg_payment_refunds_guard()
returns trigger language plpgsql set search_path = public as $$
declare
  v_amount     numeric(10,2);
  v_excess     numeric(10,2);
  v_commission numeric(10,2);
  v_committed  numeric(10,2);
  v_reversed   numeric(10,2);
  v_cap        numeric(10,2);
begin
  select amount, overcollected_amount, platform_commission_amount
    into v_amount, v_excess, v_commission
  from public.booking_payments where id = new.payment_id;
  -- Regular refunds are bounded by the part of the payment the booking owed; excess refunds
  -- by the excess. Together they never exceed the payment.
  select coalesce(sum(r.amount), 0), coalesce(sum(r.commission_reversal_amount), 0)
    into v_committed, v_reversed
  from public.payment_refunds r
  where r.payment_id = new.payment_id and r.status <> 'failed'
    and r.applies_to_excess = new.applies_to_excess
    and (tg_op = 'INSERT' or r.id <> new.id);
  -- (computed first: a CASE inside an IF condition would end the condition at its own THEN)
  v_cap := case when new.applies_to_excess then v_excess else v_amount - v_excess end;
  if new.status <> 'failed' then
    if v_committed + new.amount > v_cap then
      raise exception 'refund_exceeds_payment' using errcode = '23514';
    end if;
    if v_reversed + new.commission_reversal_amount > v_commission then
      raise exception 'commission_reversal_exceeds_snapshot' using errcode = '23514';
    end if;
  end if;
  return new;
end $$
"""

# Verbatim 0026 bodies, restored on downgrade.
_LEGACY_RECOMPUTE = """
create or replace function public.recompute_booking_payment_state(p_booking_id uuid)
returns void language plpgsql set search_path = public as $$
declare
  v_total     numeric(10,2);
  v_paid      numeric(10,2);
  v_refunded  numeric(10,2);
  v_count     integer;
  v_net       numeric(10,2);
  v_method    text;
  v_at        timestamptz;
  v_by        uuid;
  v_new       public.payment_status;
begin
  select total_price into v_total from public.bookings where id = p_booking_id for update;
  if not found then
    return;
  end if;

  select coalesce(sum(p.amount), 0), count(*) into v_paid, v_count
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded');

  select coalesce(sum(r.amount), 0) into v_refunded
  from public.payment_refunds r
  where r.booking_id = p_booking_id and r.status = 'processed';

  v_net := v_paid - v_refunded;
  if v_net > v_total then
    raise exception 'payment_overcollection'
      using errcode = '23514',
            detail = format('booking %s: net collected %s exceeds total %s',
                            p_booking_id, v_net, v_total);
  end if;

  v_new := case when v_count > 0 and v_net >= v_total then 'paid' else 'unpaid' end;

  select case when p.channel = 'gateway' then 'online' else coalesce(p.method, 'cash') end,
         p.captured_at, p.recorded_by
    into v_method, v_at, v_by
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded')
  order by p.captured_at desc nulls last, p.created_at desc
  limit 1;

  perform set_config('app.payment_recompute', 'on', true);
  update public.bookings
  set paid_amount = v_paid,
      refunded_amount = v_refunded,
      payment_status = v_new,
      payment_method = case when v_count > 0 and (v_net > 0 or v_new = 'paid')
                            then v_method::public.payment_method else null end,
      payment_recorded_at = case when v_new = 'paid'
                                 then coalesce(v_at, payment_recorded_at, now()) else null end,
      payment_recorded_by = case when v_new = 'paid'
                                 then coalesce(v_by, payment_recorded_by) else null end
  where id = p_booking_id;
  perform set_config('app.payment_recompute', 'off', true);
end $$
"""

_LEGACY_PAYMENT_GUARD = """
create or replace function public.tg_booking_payments_guard()
returns trigger language plpgsql set search_path = public as $$
begin
  if new.booking_id is distinct from old.booking_id
     or new.amount is distinct from old.amount
     or new.intent_reference is distinct from old.intent_reference
     or new.channel is distinct from old.channel then
    raise exception 'booking_payment_identity_is_immutable' using errcode = '23514';
  end if;
  if old.status in ('captured', 'partially_refunded', 'refunded')
     and new.status in ('created', 'authorized', 'failed', 'cancelled', 'expired') then
    raise exception 'booking_payment_status_regression' using errcode = '23514';
  end if;
  return new;
end $$
"""

_LEGACY_REFUND_GUARD = """
create or replace function public.tg_payment_refunds_guard()
returns trigger language plpgsql set search_path = public as $$
declare
  v_amount    numeric(10,2);
  v_committed numeric(10,2);
begin
  select amount into v_amount from public.booking_payments where id = new.payment_id;
  select coalesce(sum(r.amount), 0) into v_committed
  from public.payment_refunds r
  where r.payment_id = new.payment_id and r.status <> 'failed'
    and (tg_op = 'INSERT' or r.id <> new.id);
  if new.status <> 'failed' and v_committed + new.amount > v_amount then
    raise exception 'refund_exceeds_payment' using errcode = '23514';
  end if;
  return new;
end $$
"""


def upgrade() -> None:
    """Add the commission snapshot, overcollection record, anomalies and audit."""

    # ---------------------------------------------------------------- ledger columns
    _sql(
        """
        alter table public.booking_payments
          add column if not exists commission_rate_percent numeric(7,4),
          add column if not exists commission_base text,
          add column if not exists platform_commission_amount numeric(10,2) not null default 0,
          add column if not exists commission_policy_version text,
          add column if not exists provider_fee_amount numeric(10,2),
          add column if not exists provider_tax_amount numeric(10,2),
          add column if not exists overcollected_amount numeric(10,2) not null default 0,
          add column if not exists provider_order_confirmed_at timestamptz
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_commission_base",
        """
        alter table public.booking_payments add constraint ck_booking_payments_commission_base
          check (commission_base is null or commission_base in ('online_amount', 'booking_total'))
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_commission_amount",
        """
        alter table public.booking_payments add constraint ck_booking_payments_commission_amount
          check (platform_commission_amount >= 0 and platform_commission_amount <= amount
                 and (commission_rate_percent is null
                      or (commission_rate_percent >= 0 and commission_rate_percent <= 100)))
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_provider_costs",
        """
        alter table public.booking_payments add constraint ck_booking_payments_provider_costs
          check ((provider_fee_amount is null or provider_fee_amount >= 0)
                 and (provider_tax_amount is null or provider_tax_amount >= 0))
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_overcollected",
        """
        alter table public.booking_payments add constraint ck_booking_payments_overcollected
          check (overcollected_amount >= 0 and overcollected_amount <= amount)
        """,
        # Rows written before the snapshot existed: carry the legacy fee over as the amount.
        # They have no rate/base, which is how a reader recognises a pre-policy row.
        """
        update public.booking_payments
        set platform_commission_amount = least(platform_fee_amount, amount),
            commission_policy_version = coalesce(commission_policy_version, 'legacy')
        where channel = 'gateway' and platform_commission_amount = 0 and platform_fee_amount > 0
        """,
    )

    # ---------------------------------------------------------------- refund columns
    _sql(
        """
        alter table public.payment_refunds
          add column if not exists commission_reversal_amount numeric(10,2) not null default 0,
          add column if not exists applies_to_excess boolean not null default false
        """,
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_reversal",
        """
        alter table public.payment_refunds add constraint ck_payment_refunds_reversal
          check (commission_reversal_amount >= 0 and commission_reversal_amount <= amount
                 and (not applies_to_excess or commission_reversal_amount = 0))
        """,
    )

    # ------------------------------------------------------------ payee registration
    _sql(
        """
        alter table public.payment_provider_accounts
          add column if not exists registration_generation integer not null default 1
        """,
        "alter table public.payment_provider_accounts drop constraint if exists ck_payment_provider_accounts_generation",
        """
        alter table public.payment_provider_accounts add constraint ck_payment_provider_accounts_generation
          check (registration_generation >= 1)
        """,
        # Never any KYC/bank data: references, statuses and requirement text only.
        """
        create table if not exists public.payment_provider_account_audit (
          id              uuid primary key default gen_random_uuid(),
          salon_id        uuid not null references public.salons(id),
          provider        text not null,
          action          text not null
            check (action in ('registered', 're_registered', 'status_changed', 'register_failed')),
          previous_status text,
          new_status      text,
          vendor_ref      text,
          actor_id        uuid references public.profiles(id),
          detail          text check (detail is null or char_length(detail) <= 300),
          created_at      timestamptz not null default now()
        )
        """,
        """
        create index if not exists idx_payment_account_audit_salon
          on public.payment_provider_account_audit(salon_id, created_at desc)
        """,
    )

    # --------------------------------------------------------------------- anomalies
    _sql(
        """
        create table if not exists public.payment_anomalies (
          id           uuid primary key default gen_random_uuid(),
          kind         text not null
            check (kind in ('overcollection', 'amount_mismatch', 'settlement_failed',
                            'settlement_reversed', 'refund_onhold', 'refund_failed')),
          provider     text,
          provider_ref text,
          salon_id     uuid references public.salons(id),
          booking_id   uuid references public.bookings(id),
          payment_id   uuid references public.booking_payments(id),
          amount       numeric(10,2),
          detail       text check (detail is null or char_length(detail) <= 300),
          created_at   timestamptz not null default now(),
          resolved_at  timestamptz,
          resolved_by  uuid references public.profiles(id),
          constraint uq_payment_anomalies_ref unique (kind, provider, provider_ref)
        )
        """,
        """
        create index if not exists idx_payment_anomalies_open
          on public.payment_anomalies(created_at) where resolved_at is null
        """,
    )
    for table in _NEW_TABLES:
        _sql(
            f"alter table public.{table} enable row level security",
            f"revoke all on public.{table} from public, anon, authenticated",
            f"grant all on public.{table} to postgres, service_role",
        )
    _sql(
        "drop policy if exists payment_provider_account_audit_owner_read on public.payment_provider_account_audit",
        """
        create policy payment_provider_account_audit_owner_read on public.payment_provider_account_audit
          for select using (public.owns_salon(salon_id) or public.is_super_admin())
        """,
    )

    # ------------------------------------------------------------ replaced functions
    _sql(_RECOMPUTE, _PAYMENT_GUARD, _REFUND_GUARD)


def downgrade() -> None:
    """Remove the monetary-policy additions. Loses the snapshot, excess record and anomalies."""

    _sql(
        _LEGACY_RECOMPUTE,
        _LEGACY_PAYMENT_GUARD,
        _LEGACY_REFUND_GUARD,
        "drop table if exists public.payment_anomalies",
        "drop table if exists public.payment_provider_account_audit",
        "alter table public.payment_provider_accounts drop constraint if exists ck_payment_provider_accounts_generation",
        "alter table public.payment_provider_accounts drop column if exists registration_generation",
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_reversal",
        """
        alter table public.payment_refunds
          drop column if exists applies_to_excess,
          drop column if exists commission_reversal_amount
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_overcollected",
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_provider_costs",
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_commission_amount",
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_commission_base",
        """
        alter table public.booking_payments
          drop column if exists provider_order_confirmed_at,
          drop column if exists overcollected_amount,
          drop column if exists provider_tax_amount,
          drop column if exists provider_fee_amount,
          drop column if exists commission_policy_version,
          drop column if exists platform_commission_amount,
          drop column if exists commission_base,
          drop column if exists commission_rate_percent
        """,
    )
