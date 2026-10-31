-- Rolling customer booking window: salon-local today through today + 60 days.
-- Availability is hidden outside the window. create_booking repeats the guard
-- so a client cannot bypass the availability endpoint.

create or replace function public.get_available_slots(
  p_staff_id uuid,
  p_date date,
  p_duration_minutes integer
)
returns table(slot_start timestamptz, slot_end timestamptz)
language plpgsql
stable
security definer
set search_path = public
as $$
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
  v_today date;
begin
  select sl.id, sl.timezone, coalesce(st.working_hours, sl.working_hours)
    into v_salon, v_tz, v_hours
  from staff st
  join salons sl on sl.id = st.salon_id
  where st.id = p_staff_id
    and st.is_active
    and sl.is_active
    and sl.profile_completed
    and sl.approval_status = 'approved'
    and sl.accepting_bookings
    and public.salon_booking_eligible(sl.id);

  if v_tz is null then
    return;
  end if;

  v_today := (now() at time zone v_tz)::date;
  if p_date < v_today or p_date > v_today + 60 then
    return;
  end if;

  if exists (
    select 1
    from salon_holidays
    where salon_id = v_salon
      and holiday_date = p_date
      and is_active
  ) then
    return;
  end if;

  v_dow := lower(to_char(p_date, 'dy'));
  if v_hours -> v_dow ->> 'open' is null then
    return;
  end if;

  v_open := (v_hours -> v_dow ->> 'open')::time;
  v_close := (v_hours -> v_dow ->> 'close')::time;
  v_cursor := (p_date + v_open) at time zone v_tz;
  v_day_end := (p_date + v_close) at time zone v_tz;

  while v_cursor + make_interval(mins => p_duration_minutes) <= v_day_end loop
    v_try_end := v_cursor + make_interval(mins => p_duration_minutes);
    if v_cursor > now()
       and not exists (
         select 1
         from bookings b
         where b.staff_id = p_staff_id
           and b.status in ('pending', 'confirmed', 'checked_in')
           and tstzrange(b.start_datetime, b.end_datetime)
               && tstzrange(v_cursor, v_try_end)
       )
       and not exists (
         select 1
         from blocked_slots bs
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
end
$$;

-- statement --

create or replace function public.create_booking(
  p_salon_id uuid,
  p_staff_id uuid,
  p_service_ids uuid[],
  p_start timestamptz,
  p_customer_name text,
  p_customer_phone text default null,
  p_source booking_source default 'app',
  p_notes text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_duration int;
  v_price numeric(10,2);
  v_end timestamptz;
  v_mode approval_mode;
  v_status booking_status;
  v_customer uuid := auth.uid();
  v_tz text;
  v_booking uuid;
  v_accepting boolean;
  v_booking_date date;
  v_today date;
begin
  select timezone, approval_mode, accepting_bookings
    into v_tz, v_mode, v_accepting
  from salons
  where id = p_salon_id and is_active;

  if v_tz is null then
    raise exception 'Salon not found or inactive';
  end if;

  if not v_accepting then
    raise exception 'salon_not_accepting_bookings';
  end if;

  v_booking_date := (p_start at time zone v_tz)::date;
  v_today := (now() at time zone v_tz)::date;
  if p_source = 'app' and v_booking_date > v_today + 60 then
    raise exception 'booking_window_exceeded';
  end if;

  if exists (
    select 1
    from salon_holidays
    where salon_id = p_salon_id
      and holiday_date = v_booking_date
      and is_active
  ) then
    raise exception 'Salon is closed on this date';
  end if;

  if exists (
    select 1
    from unnest(p_service_ids) sid
    where not exists (
      select 1
      from staff_services ss
      join services sv on sv.id = ss.service_id
      where ss.staff_id = p_staff_id
        and ss.service_id = sid
        and ss.is_active
        and sv.salon_id = p_salon_id
        and sv.is_active
    )
  ) then
    raise exception 'One or more services are not offered by this staff member';
  end if;

  select sum(coalesce(ss.duration_minutes, sv.duration_minutes)),
         sum(coalesce(ss.price_override, sv.price))
    into v_duration, v_price
  from services sv
  left join staff_services ss
    on ss.service_id = sv.id
   and ss.staff_id = p_staff_id
   and ss.is_active
  where sv.id = any(p_service_ids)
    and sv.is_active;

  if v_duration is null then
    raise exception 'No valid services selected';
  end if;

  v_end := p_start + make_interval(mins => v_duration);
  if p_start <= now() then
    raise exception 'Cannot book a slot in the past';
  end if;

  if not exists (
    select 1
    from get_available_slots(p_staff_id, v_booking_date, v_duration) g
    where g.slot_start = p_start
  ) then
    raise exception 'Selected slot is no longer available';
  end if;

  v_status := case
    when p_source in ('manual_walkin', 'qr_walkin') then 'confirmed'
    when v_mode = 'auto' then 'confirmed'
    else 'pending'
  end;

  insert into bookings (
    salon_id, staff_id, customer_id, customer_name, customer_phone,
    phone_verified, source, status, start_datetime, end_datetime,
    total_duration_minutes, total_price, notes, created_by
  ) values (
    p_salon_id, p_staff_id,
    case when p_source = 'manual_walkin' then null else v_customer end,
    p_customer_name, p_customer_phone,
    (p_source = 'qr_walkin' and v_customer is not null),
    p_source, v_status, p_start, v_end,
    v_duration, v_price, p_notes, v_customer
  )
  returning id into v_booking;

  insert into booking_services (
    booking_id, service_id, service_name, duration_minutes, price
  )
  select v_booking, sv.id, sv.name,
         coalesce(ss.duration_minutes, sv.duration_minutes),
         coalesce(ss.price_override, sv.price)
  from services sv
  left join staff_services ss
    on ss.service_id = sv.id
   and ss.staff_id = p_staff_id
   and ss.is_active
  where sv.id = any(p_service_ids);

  return v_booking;
exception
  when exclusion_violation then
    raise exception 'That slot was just taken. Please pick another time.';
end
$$;
