"""Gateway-fee snapshot on payments and cancellation facts on refunds.

* ``booking_payments`` gains ``gateway_fee_percent`` / ``gateway_fee_amount``: the fee the SALON
  bears, snapshotted once at intent time (the 0029 immutability idiom is extended to them). It
  is separate from the platform commission (0 in this model) and from the provider's actual
  ``provider_fee_amount``. A manual row never carries a gateway fee.
* ``payment_refunds`` gains ``kind`` (who initiated it), ``deduction_amount`` (what a customer
  cancellation kept; immutable) and ``attempts`` (bounded re-drive of a refund whose provider
  call failed or timed out, always with the SAME refund id).

Every statement is idempotent and its own ``op.execute`` (asyncpg prepares one statement per
call). Reviewed deploy step only.

Revision ID: 0033_payment_fee_snapshot
Revises: 0032_salon_access_state
Create Date: 2026-10-13 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0033_payment_fee_snapshot"
down_revision: str | Sequence[str] | None = "0032_salon_access_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sql(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


# 0029 bodies plus the new immutability clauses.
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
  -- So is the gateway-fee snapshot borne by the salon.
  if new.gateway_fee_percent is distinct from old.gateway_fee_percent
     or new.gateway_fee_amount is distinct from old.gateway_fee_amount then
    raise exception 'booking_payment_gateway_fee_snapshot_is_immutable' using errcode = '23514';
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
  if tg_op = 'UPDATE' and (new.kind is distinct from old.kind
                           or new.deduction_amount is distinct from old.deduction_amount
                           or new.amount is distinct from old.amount) then
    raise exception 'payment_refund_snapshot_is_immutable' using errcode = '23514';
  end if;
  select amount, overcollected_amount, platform_commission_amount
    into v_amount, v_excess, v_commission
  from public.booking_payments where id = new.payment_id;
  select coalesce(sum(r.amount), 0), coalesce(sum(r.commission_reversal_amount), 0)
    into v_committed, v_reversed
  from public.payment_refunds r
  where r.payment_id = new.payment_id and r.status <> 'failed'
    and r.applies_to_excess = new.applies_to_excess
    and (tg_op = 'INSERT' or r.id <> new.id);
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

# Verbatim 0029 bodies, restored on downgrade.
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

_LEGACY_REFUND_GUARD = """
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
  select coalesce(sum(r.amount), 0), coalesce(sum(r.commission_reversal_amount), 0)
    into v_committed, v_reversed
  from public.payment_refunds r
  where r.payment_id = new.payment_id and r.status <> 'failed'
    and r.applies_to_excess = new.applies_to_excess
    and (tg_op = 'INSERT' or r.id <> new.id);
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


def upgrade() -> None:
    """Add the gateway-fee snapshot, refund kind/deduction/attempts and their guards."""

    _sql(
        """
        alter table public.booking_payments
          add column if not exists gateway_fee_percent numeric(7,4),
          add column if not exists gateway_fee_amount numeric(10,2) not null default 0
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_gateway_fee",
        """
        alter table public.booking_payments add constraint ck_booking_payments_gateway_fee
          check (gateway_fee_amount >= 0
                 and gateway_fee_amount + platform_commission_amount <= amount
                 and (gateway_fee_percent is null
                      or (gateway_fee_percent >= 0 and gateway_fee_percent <= 100))
                 and (channel = 'gateway' or gateway_fee_amount = 0))
        """,
        """
        alter table public.payment_refunds
          add column if not exists kind text not null default 'owner',
          add column if not exists deduction_amount numeric(10,2) not null default 0,
          add column if not exists attempts integer not null default 0
        """,
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_kind",
        """
        alter table public.payment_refunds add constraint ck_payment_refunds_kind
          check (kind in ('owner', 'customer_cancellation', 'salon_cancellation', 'closure'))
        """,
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_deduction",
        """
        alter table public.payment_refunds add constraint ck_payment_refunds_deduction
          check (deduction_amount >= 0 and attempts >= 0
                 and (kind = 'customer_cancellation' or deduction_amount = 0))
        """,
        _PAYMENT_GUARD,
        _REFUND_GUARD,
    )


def downgrade() -> None:
    """Drop the additions. Loses the gateway-fee snapshot and the refund kind/deduction."""

    _sql(
        _LEGACY_PAYMENT_GUARD,
        _LEGACY_REFUND_GUARD,
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_deduction",
        "alter table public.payment_refunds drop constraint if exists ck_payment_refunds_kind",
        """
        alter table public.payment_refunds
          drop column if exists attempts,
          drop column if exists deduction_amount,
          drop column if exists kind
        """,
        "alter table public.booking_payments drop constraint if exists ck_booking_payments_gateway_fee",
        """
        alter table public.booking_payments
          drop column if exists gateway_fee_amount,
          drop column if exists gateway_fee_percent
        """,
    )
