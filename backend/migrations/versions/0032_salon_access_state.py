"""Salon access state: backend-only trial facts and booking counting.

* ``salon_access`` (one row per salon, RLS on, nothing for anon/authenticated) holds the TRIAL
  FACTS only: when the trial started (first approval), its date end, a snapshot of the booking
  limit, the one-way ``trial_limit_reached_at`` stamp and the live ``bookings_counted``. It is
  deliberately NOT a column set on ``salons`` because ``salons_public_read`` is world-readable.
  The access STATE (trialing / soft_locked / subscribed_*) is never stored: the pure Python
  service ``app/domain/services/access_state.py`` derives it, so there is no second copy of the
  rules in SQL.
* The trial starts at the FIRST approval (write-once). Existing approved salons are
  grandfathered: trial start = migration time, ``bookings_counted`` = 0 (history does not
  count). Existing salons not yet approved get a row with no trial; it starts when approved.
* ``recompute_salon_trial`` counts bookings created on/after the trial start in status
  pending/confirmed/completed (any source) and stamps ``trial_limit_reached_at`` ONCE when the
  count reaches the snapshot limit. One-way: later cancellations never reopen the trial.
  Triggers on bookings (insert, counted-status change) call it. ``create_booking`` is untouched.
* Trial parameters: SQL defaults 120 bookings / 60 days; the API sets the transaction-local
  settings ``app.trial_booking_limit`` / ``app.trial_days`` (from TRIAL_BOOKING_LIMIT /
  TRIAL_DAYS) when it approves a salon, so the snapshot follows configuration. Approvals made
  outside the API use the SQL defaults.

Every statement is idempotent and its own ``op.execute``. Reviewed deploy step only.

Revision ID: 0032_salon_access_state
Revises: 0031_seed_subscription_plans
Create Date: 2026-10-13 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0032_salon_access_state"
down_revision: str | Sequence[str] | None = "0031_seed_subscription_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COUNTED = "('pending', 'confirmed', 'completed')"

_SETTING_FN = """
create or replace function public.salon_trial_setting(
  p_name text, p_default integer, p_min integer, p_max integer
) returns integer language plpgsql stable set search_path = public as $$
declare
  v_raw text := current_setting(p_name, true);
begin
  if v_raw ~ '^[0-9]{1,6}$' and v_raw::integer between p_min and p_max then
    return v_raw::integer;
  end if;
  return p_default;
end $$
"""

_START = """
create or replace function public.start_salon_trial(p_salon_id uuid, p_at timestamptz default now())
returns void language plpgsql security definer set search_path = public as $$
declare
  v_limit integer := public.salon_trial_setting('app.trial_booking_limit', 120, 1, 100000);
  v_days  integer := public.salon_trial_setting('app.trial_days', 60, 1, 3650);
begin
  insert into public.salon_access
    (salon_id, trial_started_at, trial_ends_at, trial_booking_limit)
  values (p_salon_id, p_at, p_at + make_interval(days => v_days), v_limit)
  on conflict (salon_id) do update
    set trial_started_at = excluded.trial_started_at,
        trial_ends_at = excluded.trial_ends_at,
        trial_booking_limit = excluded.trial_booking_limit,
        bookings_counted = 0,
        updated_at = now()
    where public.salon_access.trial_started_at is null;
end $$
"""

_RECOMPUTE = f"""
create or replace function public.recompute_salon_trial(p_salon_id uuid)
returns void language plpgsql security definer set search_path = public as $$
declare
  v_row   public.salon_access%rowtype;
  v_count integer;
begin
  -- Cheap exits without a lock: no row, trial not started, limit already stamped, date over.
  select * into v_row from public.salon_access where salon_id = p_salon_id;
  if not found or v_row.trial_started_at is null
     or v_row.trial_limit_reached_at is not null
     or v_row.trial_ends_at <= now() then
    if found and v_row.trial_started_at is not null and v_row.trial_ended_reason is null
       and v_row.trial_limit_reached_at is null and v_row.trial_ends_at <= now() then
      update public.salon_access set trial_ended_reason = 'date', updated_at = now()
      where salon_id = p_salon_id and trial_ended_reason is null and trial_limit_reached_at is null;
    end if;
    return;
  end if;
  select * into v_row from public.salon_access where salon_id = p_salon_id for update;
  if v_row.trial_limit_reached_at is not null or v_row.trial_ends_at <= now() then
    return;
  end if;
  -- Bounded scan: never reads more than the limit.
  select count(*) into v_count from (
    select 1 from public.bookings b
    where b.salon_id = p_salon_id and b.created_at >= v_row.trial_started_at
      and b.status in {_COUNTED}
    limit v_row.trial_booking_limit
  ) counted;
  if v_count >= v_row.trial_booking_limit then
    update public.salon_access
    set bookings_counted = v_count, trial_limit_reached_at = now(),
        trial_ended_reason = 'booking_limit', updated_at = now()
    where salon_id = p_salon_id;
  elsif v_count is distinct from v_row.bookings_counted then
    update public.salon_access set bookings_counted = v_count, updated_at = now()
    where salon_id = p_salon_id;
  end if;
end $$
"""

_TG_BOOKING = """
create or replace function public.tg_bookings_recompute_trial()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  perform public.recompute_salon_trial(new.salon_id);
  return null;
end $$
"""

_TG_SALON = """
create or replace function public.tg_salons_access_row()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.salon_access (salon_id) values (new.id) on conflict (salon_id) do nothing;
  if new.approval_status = 'approved' then
    perform public.start_salon_trial(new.id);
  end if;
  return null;
end $$
"""


def upgrade() -> None:
    for statement in (
        """
        create table if not exists public.salon_access (
          salon_id               uuid primary key references public.salons(id) on delete cascade,
          trial_started_at       timestamptz,
          trial_ends_at          timestamptz,
          trial_booking_limit    integer not null default 120
            check (trial_booking_limit between 1 and 100000),
          trial_limit_reached_at timestamptz,
          trial_ended_reason     text check (trial_ended_reason in ('booking_limit', 'date')),
          bookings_counted       integer not null default 0 check (bookings_counted >= 0),
          created_at             timestamptz not null default now(),
          updated_at             timestamptz not null default now(),
          constraint ck_salon_access_window
            check (trial_ends_at is null
                   or (trial_started_at is not null and trial_ends_at > trial_started_at)),
          constraint ck_salon_access_started
            check (trial_started_at is not null
                   or (trial_limit_reached_at is null and trial_ended_reason is null))
        )
        """,
        "alter table public.salon_access enable row level security",
        "revoke all on public.salon_access from public, anon, authenticated",
        "grant all on public.salon_access to postgres, service_role",
        _SETTING_FN,
        _START,
        _RECOMPUTE,
        _TG_BOOKING,
        _TG_SALON,
        "revoke all on function public.salon_trial_setting(text, integer, integer, integer) from public, anon, authenticated",
        "revoke all on function public.start_salon_trial(uuid, timestamptz) from public, anon, authenticated",
        "revoke all on function public.recompute_salon_trial(uuid) from public, anon, authenticated",
        "revoke all on function public.tg_bookings_recompute_trial() from public, anon, authenticated",
        "revoke all on function public.tg_salons_access_row() from public, anon, authenticated",
        f"""
        create index if not exists idx_bookings_trial_count
          on public.bookings(salon_id, created_at) where status in {_COUNTED}
        """,
        "drop trigger if exists t_bookings_trial_insert on public.bookings",
        f"""
        create trigger t_bookings_trial_insert after insert on public.bookings
          for each row when (new.status in {_COUNTED})
          execute function public.tg_bookings_recompute_trial()
        """,
        "drop trigger if exists t_bookings_trial_status on public.bookings",
        f"""
        create trigger t_bookings_trial_status after update of status on public.bookings
          for each row when ((old.status in {_COUNTED}) is distinct from (new.status in {_COUNTED}))
          execute function public.tg_bookings_recompute_trial()
        """,
        "drop trigger if exists t_salons_access_insert on public.salons",
        """
        create trigger t_salons_access_insert after insert on public.salons
          for each row execute function public.tg_salons_access_row()
        """,
        "drop trigger if exists t_salons_access_approved on public.salons",
        """
        create trigger t_salons_access_approved after update of approval_status on public.salons
          for each row when (new.approval_status = 'approved'
                             and old.approval_status is distinct from new.approval_status)
          execute function public.tg_salons_access_row()
        """,
        # Back-fill every existing salon. Approved ones are grandfathered (start = now, count 0);
        # the rest get a row whose trial starts at approval. Re-runs change nothing.
        """
        insert into public.salon_access (salon_id) select id from public.salons
        on conflict (salon_id) do nothing
        """,
        """
        update public.salon_access a
        set trial_started_at = now(),
            trial_ends_at = now() + make_interval(
              days => public.salon_trial_setting('app.trial_days', 60, 1, 3650)),
            trial_booking_limit = public.salon_trial_setting('app.trial_booking_limit', 120, 1, 100000),
            bookings_counted = 0, updated_at = now()
        from public.salons s
        where s.id = a.salon_id and s.approval_status = 'approved' and a.trial_started_at is null
        """,
    ):
        op.execute(statement)


def downgrade() -> None:
    """Drop the trial facts and their triggers (the facts are lost; bookings are untouched)."""

    for statement in (
        "drop trigger if exists t_salons_access_approved on public.salons",
        "drop trigger if exists t_salons_access_insert on public.salons",
        "drop trigger if exists t_bookings_trial_status on public.bookings",
        "drop trigger if exists t_bookings_trial_insert on public.bookings",
        "drop index if exists public.idx_bookings_trial_count",
        "drop function if exists public.tg_salons_access_row()",
        "drop function if exists public.tg_bookings_recompute_trial()",
        "drop function if exists public.recompute_salon_trial(uuid)",
        "drop function if exists public.start_salon_trial(uuid, timestamptz)",
        "drop function if exists public.salon_trial_setting(text, integer, integer, integer)",
        "drop table if exists public.salon_access",
    ):
        op.execute(statement)
