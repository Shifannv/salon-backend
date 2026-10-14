create or replace function public.salon_booking_eligible(p_salon uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.salons s where s.id = p_salon and s.is_active
      and s.profile_completed and s.approval_status = 'approved'
      and (exists (
        select 1 from public.salon_subscriptions sub where sub.salon_id = s.id
          and sub.status in ('active', 'cancelled')
          and sub.current_period_start <= now() and sub.current_period_end > now()
      ) or exists (
        select 1 from public.salon_access a where a.salon_id = s.id
          and a.trial_started_at <= now() and a.trial_ends_at > now()
          and a.trial_limit_reached_at is null and a.bookings_counted < a.trial_booking_limit
      ))
  )
$$;
-- statement --
revoke all on function public.salon_booking_eligible(uuid) from public, anon, authenticated;
-- statement --
grant execute on function public.salon_booking_eligible(uuid) to service_role;
-- statement --
create or replace function public.start_salon_trial(p_salon_id uuid, p_at timestamptz default now())
returns void language plpgsql security definer set search_path = public as $$
begin
  insert into public.salon_access(salon_id, trial_started_at, trial_ends_at, trial_booking_limit)
    values (p_salon_id, p_at, p_at + interval '2 months', 120)
  on conflict (salon_id) do update set trial_started_at = excluded.trial_started_at,
    trial_ends_at = excluded.trial_ends_at, trial_booking_limit = 120, bookings_counted = 0
    where public.salon_access.trial_started_at is null;
end $$;
-- statement --
update public.salon_access set trial_ends_at = trial_started_at + interval '2 months',
  trial_booking_limit = 120 where trial_started_at is not null;
-- statement --
create table public.booking_audit_events (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references public.bookings(id),
  actor_id uuid references public.profiles(id) on delete set null,
  event_type text not null,
  old_state text,
  new_state text,
  created_at timestamptz not null default now()
);
-- statement --
create table public.customer_booking_restrictions (
  customer_id uuid primary key references public.profiles(id) on delete cascade,
  no_show_count integer not null default 0 check (no_show_count >= 0),
  pay_at_salon_blocked_until timestamptz
);
-- statement --
alter table public.bookings add column booking_calendar_date date;
-- statement --
update public.bookings set booking_calendar_date = (start_datetime at time zone 'Asia/Kolkata')::date;
-- statement --
create index idx_booking_pay_at_salon_day on public.bookings(customer_id, booking_calendar_date)
  where payment_preference = 'pay_at_salon' and status in ('pending', 'confirmed', 'checked_in');
-- statement --
alter table public.bookings drop constraint bookings_no_overlap;
-- statement --
alter table public.bookings add constraint bookings_no_overlap exclude using gist (
  staff_id with =, tstzrange(start_datetime, end_datetime) with &&
) where (status in ('pending', 'confirmed', 'checked_in'));
-- statement --
create index idx_salon_access_eligibility on public.salon_access(trial_ends_at)
  where trial_limit_reached_at is null;
-- statement --
create index idx_subscription_booking_eligibility on public.salon_subscriptions(salon_id, current_period_end)
  where status in ('active', 'cancelled');
-- statement --
alter table public.booking_payments add column collection_method text
  check (collection_method in ('CASH', 'UPI_DIRECT'));
-- statement --
alter table public.booking_payments add column collected_by_owner boolean not null default false;
-- statement --
create or replace function public.guard_booking_checkout()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_block timestamptz;
begin
  if tg_op = 'INSERT' then
    -- Lock the shared salon trial before eligibility and before create_booking inserts.
    perform 1 from public.salon_access where salon_id = new.salon_id for update;
    if not public.salon_booking_eligible(new.salon_id) then
      raise exception 'salon_not_accepting_bookings' using errcode = '23514';
    end if;
    new.payment_preference := coalesce(nullif(current_setting('app.payment_preference', true), ''),
                                     new.payment_preference, 'pay_at_salon');
  end if;
  new.booking_calendar_date := (new.start_datetime at time zone 'Asia/Kolkata')::date;
  if new.customer_id is not null and new.payment_preference = 'pay_at_salon'
    and new.status in ('pending', 'confirmed', 'checked_in')
    and (tg_op = 'INSERT' or old.status not in ('pending','confirmed','checked_in')
         or new.payment_preference is distinct from old.payment_preference
         or new.start_datetime is distinct from old.start_datetime) then
    -- A per-customer transaction lock serializes different salons/days and no-show decisions.
    perform pg_advisory_xact_lock(hashtextextended(new.customer_id::text, 3715));
    select pay_at_salon_blocked_until into v_block from public.customer_booking_restrictions
      where customer_id = new.customer_id;
    if v_block > now() then
      raise exception 'pay_at_salon_temporarily_blocked' using errcode = '23514';
    end if;
    if exists (select 1 from public.bookings b where b.customer_id = new.customer_id
      and b.id <> new.id and b.booking_calendar_date = new.booking_calendar_date
      and b.payment_preference = 'pay_at_salon' and b.status in ('pending', 'confirmed', 'checked_in')) then
      raise exception 'pay_at_salon_daily_limit' using errcode = '23514';
    end if;
  end if;
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not ((old.status = 'pending' and new.status in ('confirmed','rejected','cancelled'))
      or (old.status = 'confirmed' and new.status in ('checked_in','completed','cancelled','no_show'))
      or (old.status = 'checked_in' and new.status in ('completed','cancelled','no_show'))) then
      raise exception 'booking_state_conflict' using errcode = '23514';
    end if;
    if new.status = 'completed' and new.payment_preference = 'pay_at_salon'
      and (new.payment_status <> 'paid' or not exists (
        select 1 from public.booking_payments p where p.booking_id = new.id
          and p.channel = 'manual' and p.status = 'captured'
      )) then
      raise exception 'payment_collection_required' using errcode = '23514';
    end if;
    if (new.status = 'no_show' or (new.status = 'cancelled'
          and new.cancellation_reason like 'Customer no-show%')) and new.customer_id is not null then
      if new.start_datetime > now() then
        raise exception 'no_show_before_appointment' using errcode = '23514';
      end if;
      perform pg_advisory_xact_lock(hashtextextended(new.customer_id::text, 3715));
      insert into public.customer_booking_restrictions(customer_id, no_show_count)
        values (new.customer_id, 1)
      on conflict (customer_id) do update set
        no_show_count = case when customer_booking_restrictions.pay_at_salon_blocked_until <= now()
          then 1 else customer_booking_restrictions.no_show_count + 1 end;
      update public.customer_booking_restrictions set pay_at_salon_blocked_until = now() + interval '7 days'
        where customer_id = new.customer_id and no_show_count >= 2;
    end if;
  end if;
  return new;
end $$;
-- statement --
create trigger booking_checkout_guard before insert or update on public.bookings
  for each row execute function public.guard_booking_checkout();
-- statement --
create or replace function public.booking_append_audit()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' or new.status is distinct from old.status then
    insert into public.booking_audit_events(booking_id, actor_id, event_type, old_state, new_state)
      values (new.id, auth.uid(), case when tg_op = 'INSERT' then 'booking_created' else 'booking_transition' end,
        case when tg_op = 'UPDATE' then old.status::text else null end, new.status::text);
  end if;
  return null;
end $$;
-- statement --
create trigger booking_audit_append after insert or update on public.bookings
  for each row execute function public.booking_append_audit();
-- statement --
create or replace function public.payment_append_audit()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_op = 'INSERT' or new.status is distinct from old.status then
    insert into public.booking_audit_events(booking_id, actor_id, event_type, old_state, new_state)
      values (new.booking_id, auth.uid(), 'payment_' || new.channel,
        case when tg_op = 'UPDATE' then old.status else null end, new.status);
  end if;
  return null;
end $$;
-- statement --
create trigger payment_audit_append after insert or update on public.booking_payments
  for each row execute function public.payment_append_audit();
-- statement --
create or replace function public.guard_audit_immutable()
returns trigger language plpgsql set search_path = public as $$
begin
  -- Scoped account erasure may anonymize ONLY the actor reference, preserving the event.
  if tg_op = 'UPDATE' and current_setting('app.account_erasure', true) = 'on'
    and new.actor_id is null and (to_jsonb(new) - 'actor_id') = (to_jsonb(old) - 'actor_id') then
    return new;
  end if;
  raise exception 'audit_event_is_immutable' using errcode = '23514';
end $$;
-- statement --
create trigger booking_audit_immutable before update or delete on public.booking_audit_events
  for each row execute function public.guard_audit_immutable();
-- statement --
create index idx_booking_audit_history on public.booking_audit_events(booking_id, created_at);
-- statement --
alter table public.booking_audit_events enable row level security;
-- statement --
alter table public.customer_booking_restrictions enable row level security;
-- statement --
revoke all on public.booking_audit_events, public.customer_booking_restrictions from public, anon, authenticated;
-- statement --
grant all on public.booking_audit_events, public.customer_booking_restrictions to service_role;
-- statement --
revoke all on function public.guard_booking_checkout(), public.booking_append_audit(), public.payment_append_audit(), public.guard_audit_immutable() from public, anon, authenticated;
-- statement --
revoke insert, update, delete on public.bookings, public.booking_services from anon, authenticated;
-- statement --
revoke execute on function public.create_booking(uuid, uuid, uuid[], timestamptz, text, text, booking_source, text) from public, anon, authenticated;

-- statement --
create or replace function get_available_slots(
          p_staff_id uuid,
          p_date date,
          p_duration_minutes int
        )
        returns table (slot_start timestamptz, slot_end timestamptz)
        language plpgsql stable security definer set search_path = public as $$
        declare
          v_salon uuid;
          v_tz text;
          v_hours jsonb;
          v_dow text;
          v_open time;
          v_close time;
          v_cursor timestamptz;
          v_day_end timestamptz;
          v_try_end timestamptz;
        begin
          select sl.id, sl.timezone, coalesce(st.working_hours, sl.working_hours)
            into v_salon, v_tz, v_hours
          from staff st
          join salons sl on sl.id = st.salon_id
          where st.id = p_staff_id
            and st.is_active
            and sl.is_active
            and sl.profile_completed and sl.approval_status = 'approved'
            and sl.accepting_bookings and public.salon_booking_eligible(sl.id);

          if v_tz is null then return; end if;

          if exists (
            select 1 from salon_holidays
            where salon_id = v_salon
              and holiday_date = p_date
              and is_active
          ) then
            return;
          end if;

          v_dow := lower(to_char(p_date, 'dy'));
          if v_hours -> v_dow ->> 'open' is null then return; end if;

          v_open := (v_hours -> v_dow ->> 'open')::time;
          v_close := (v_hours -> v_dow ->> 'close')::time;
          v_cursor := (p_date + v_open) at time zone v_tz;
          v_day_end := (p_date + v_close) at time zone v_tz;

          while v_cursor + make_interval(mins => p_duration_minutes) <= v_day_end loop
            v_try_end := v_cursor + make_interval(mins => p_duration_minutes);
            if v_cursor > now()
               and not exists (
                 select 1 from bookings b
                 where b.staff_id = p_staff_id
                   and b.status in ('pending', 'confirmed', 'checked_in')
                   and tstzrange(b.start_datetime, b.end_datetime)
                       && tstzrange(v_cursor, v_try_end)
               )
               and not exists (
                 select 1 from blocked_slots bs
                 where (bs.staff_id = p_staff_id
                        or (bs.staff_id is null and bs.salon_id = v_salon))
                   and tstzrange(bs.start_datetime, bs.end_datetime)
                       && tstzrange(v_cursor, v_try_end)
               )
            then
              slot_start := v_cursor;
              slot_end := v_try_end;
              return next;
            end if;
            v_cursor := v_cursor + make_interval(mins => p_duration_minutes);
          end loop;
        end $$;

-- statement --
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

-- statement --
drop trigger t_bookings_trial_insert on public.bookings

-- statement --
drop trigger t_bookings_trial_status on public.bookings

-- statement --
create trigger t_bookings_trial_insert after insert on public.bookings for each row execute function public.tg_bookings_recompute_trial()

-- statement --
drop index if exists public.idx_bookings_trial_count
-- statement --
create index idx_bookings_trial_count on public.bookings(salon_id, created_at)
