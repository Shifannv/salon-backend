-- Salon-wide and per-staff daily breaks inside working_hours.
--
-- working_hours day shape (a missing or empty "breaks" means no break that day):
--   {"mon": {"open": "09:00", "close": "20:00",
--            "breaks": [{"id": "break-1", "start": "13:00", "end": "14:00"}]}, "sun": null}
--
-- Salon breaks apply to every staff member. A staff member's own working_hours breaks
-- apply on top of them. Staff without working_hours inherit the salon hours and breaks.
--
-- Shape validation lives in the API layer. No CHECK constraint is added: a NOT VALID check
-- still fires on every later UPDATE of a legacy row and would break unrelated updates.

CREATE OR REPLACE FUNCTION public.staff_break_overlaps(p_staff uuid, p_start timestamptz, p_end timestamptz)
RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER SET search_path = pg_catalog, public AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.staff st
    JOIN public.salons sl ON sl.id = st.salon_id
    CROSS JOIN LATERAL (SELECT (p_start AT TIME ZONE sl.timezone)::date AS local_date) d
    CROSS JOIN LATERAL (
      SELECT value AS brk FROM jsonb_array_elements(
        coalesce(sl.working_hours -> lower(to_char(d.local_date, 'dy')) -> 'breaks', '[]'::jsonb))
      UNION ALL
      SELECT value AS brk FROM jsonb_array_elements(
        coalesce(st.working_hours -> lower(to_char(d.local_date, 'dy')) -> 'breaks', '[]'::jsonb))
    ) b
    WHERE st.id = p_staff
      AND tstzrange((d.local_date + (b.brk ->> 'start')::time) AT TIME ZONE sl.timezone,
                    (d.local_date + (b.brk ->> 'end')::time) AT TIME ZONE sl.timezone)
          && tstzrange(p_start, p_end)
  )
$$;

-- statement --
CREATE OR REPLACE FUNCTION public.visit_break_conflict(p_start timestamptz, p_segments jsonb)
RETURNS boolean LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE part jsonb; sid uuid; duration integer; cursor_at timestamptz := p_start; ends timestamptz;
BEGIN
  FOR part IN SELECT value FROM jsonb_array_elements(p_segments) LOOP
    sid := (part->>'staff_id')::uuid;
    duration := (public.visit_service_totals(sid,
      ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(part->'service_ids')), NULL)->>'duration')::integer;
    IF duration IS NULL OR duration <= 0 THEN RETURN false; END IF;
    ends := cursor_at + make_interval(mins => duration);
    IF public.staff_break_overlaps(sid, cursor_at, ends) THEN RETURN true; END IF;
    cursor_at := ends;
  END LOOP;
  RETURN false;
EXCEPTION WHEN OTHERS THEN
  RETURN false;
END $$;

-- statement --
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
  v_salon_hours jsonb;
  v_dow text;
  v_open time;
  v_close time;
  v_cursor timestamptz;
  v_day_end timestamptz;
  v_try_end timestamptz;
  v_today date;
begin
  select sl.id, sl.timezone, coalesce(st.working_hours, sl.working_hours), sl.working_hours
    into v_salon, v_tz, v_hours, v_salon_hours
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
       and not exists (
         select 1
         from jsonb_array_elements(coalesce(v_salon_hours -> v_dow -> 'breaks', '[]'::jsonb)) brk
         where tstzrange((p_date + (brk ->> 'start')::time) at time zone v_tz,
                         (p_date + (brk ->> 'end')::time) at time zone v_tz)
               && tstzrange(v_cursor, v_try_end)
       )
       and not exists (
         select 1
         from jsonb_array_elements(coalesce(v_hours -> v_dow -> 'breaks', '[]'::jsonb)) brk
         where tstzrange((p_date + (brk ->> 'start')::time) at time zone v_tz,
                         (p_date + (brk ->> 'end')::time) at time zone v_tz)
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
create or replace function public.get_available_slots(
          p_staff_id uuid,
          p_date date,
          p_duration_minutes int,
          p_exclude_booking_id uuid
        )
        returns table (slot_start timestamptz, slot_end timestamptz)
        language plpgsql stable security definer set search_path = public as $$
        declare
          v_salon uuid;
          v_tz text;
          v_hours jsonb;
          v_salon_hours jsonb;
          v_dow text;
          v_open time;
          v_close time;
          v_cursor timestamptz;
          v_day_end timestamptz;
          v_try_end timestamptz;
        begin
          if p_duration_minutes is null or p_duration_minutes not between 1 and 1440 then return; end if;
          if p_exclude_booking_id is not null and not exists (
            select 1 from public.bookings where id = p_exclude_booking_id
              and customer_id = auth.uid() and status in ('pending', 'confirmed')
          ) then
            raise exception 'booking_not_found' using errcode = 'P0001';
          end if;
          select sl.id, sl.timezone, coalesce(st.working_hours, sl.working_hours), sl.working_hours
            into v_salon, v_tz, v_hours, v_salon_hours
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
                   and (p_exclude_booking_id is null or b.id <> p_exclude_booking_id)
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
       and not exists (
         select 1
         from jsonb_array_elements(coalesce(v_salon_hours -> v_dow -> 'breaks', '[]'::jsonb)) brk
         where tstzrange((p_date + (brk ->> 'start')::time) at time zone v_tz,
                         (p_date + (brk ->> 'end')::time) at time zone v_tz)
               && tstzrange(v_cursor, v_try_end)
       )
       and not exists (
         select 1
         from jsonb_array_elements(coalesce(v_hours -> v_dow -> 'breaks', '[]'::jsonb)) brk
         where tstzrange((p_date + (brk ->> 'start')::time) at time zone v_tz,
                         (p_date + (brk ->> 'end')::time) at time zone v_tz)
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
CREATE OR REPLACE FUNCTION public.visit_plan(p_salon uuid,p_start timestamptz,p_segments jsonb,p_exclude uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE part jsonb; sid uuid; ids uuid[]; cursor_at timestamptz:=p_start; ends timestamptz;
  duration integer; amount numeric; total numeric:=0; result jsonb:='[]'; n integer:=0;
  seen uuid[]:='{}'; groups text[]:='{}'; grp text; tz text; hours jsonb; local_day date; dow text;
BEGIN
  IF p_exclude IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.bookings WHERE id=p_exclude
    AND customer_id=auth.uid() AND salon_id=p_salon AND status IN ('pending','confirmed')) THEN
    RAISE EXCEPTION 'booking_not_found' USING ERRCODE='P0001';
  END IF;
  IF jsonb_typeof(p_segments)<>'array' OR jsonb_array_length(p_segments) NOT BETWEEN 1 AND 30 THEN
    RAISE EXCEPTION 'invalid_visit_services' USING ERRCODE='23514';
  END IF;
  FOR part IN SELECT value FROM jsonb_array_elements(p_segments) LOOP
    sid:=(part->>'staff_id')::uuid;
    ids:=ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(part->'service_ids'));
    IF cardinality(ids) NOT BETWEEN 1 AND 30 OR seen&&ids OR
       cardinality(ids)<>(SELECT count(DISTINCT x) FROM unnest(ids)x) THEN
      RAISE EXCEPTION 'invalid_visit_services' USING ERRCODE='23514';
    END IF;
    seen:=seen||ids;
    IF cardinality(seen)>30 THEN RAISE EXCEPTION 'invalid_visit_services' USING ERRCODE='23514'; END IF;
    SELECT sl.timezone,coalesce(st.working_hours,sl.working_hours) INTO tz,hours
    FROM public.staff st JOIN public.salons sl ON sl.id=st.salon_id
    WHERE st.id=sid AND st.salon_id=p_salon AND st.is_active AND sl.is_active AND sl.profile_completed
      AND sl.approval_status='approved' AND sl.accepting_bookings AND public.salon_booking_eligible(sl.id);
    IF tz IS NULL THEN RETURN NULL; END IF;
    IF (SELECT count(*) FROM public.services sv JOIN public.staff_services ss ON ss.service_id=sv.id
        JOIN public.service_subcategories sub ON sub.id=sv.subcategory_id
        JOIN public.service_categories cat ON cat.id=sub.category_id
        WHERE sv.id=ANY(ids) AND sv.salon_id=p_salon AND sv.is_active AND sub.is_active AND cat.is_active
        AND ss.staff_id=sid AND ss.is_active)<>cardinality(ids) THEN
      RAISE EXCEPTION 'One or more services are not offered by this staff member';
    END IF;
    FOR grp IN SELECT CASE WHEN selection_group='__category__' THEN coalesce(menu_category_id::text,subcategory_id::text) ELSE coalesce(menu_category_id::text,subcategory_id::text)||':'||selection_group END
      FROM public.services WHERE id=ANY(ids) AND selection_group IS NOT NULL LOOP
      IF grp=ANY(groups) THEN RAISE EXCEPTION 'invalid_service_selection' USING ERRCODE='23514'; END IF;
      groups:=array_append(groups,grp);
    END LOOP;
    SELECT (q->>'duration')::integer,(q->>'amount')::numeric INTO duration,amount
    FROM (SELECT public.visit_service_totals(sid,ids,p_exclude) q) totals;
    ends:=cursor_at+make_interval(mins=>duration);
    local_day:=(cursor_at AT TIME ZONE tz)::date; dow:=lower(to_char(local_day,'dy'));
    IF cursor_at<=now() OR local_day<(now() AT TIME ZONE tz)::date
      OR local_day>(now() AT TIME ZONE tz)::date+60
      OR hours->dow->>'open' IS NULL OR hours->dow->>'close' IS NULL
      OR cursor_at<(local_day+(hours->dow->>'open')::time) AT TIME ZONE tz
      OR ends>(local_day+(hours->dow->>'close')::time) AT TIME ZONE tz
      OR EXISTS(SELECT 1 FROM public.salon_holidays WHERE salon_id=p_salon AND holiday_date=local_day AND is_active)
      OR EXISTS(SELECT 1 FROM public.blocked_slots WHERE (staff_id=sid OR(staff_id IS NULL AND salon_id=p_salon))
        AND tstzrange(start_datetime,end_datetime)&&tstzrange(cursor_at,ends))
      OR EXISTS(SELECT 1 FROM public.booking_staff_reservations r WHERE r.staff_id=sid AND (p_exclude IS NULL OR r.booking_id<>p_exclude)
        AND r.status IN ('pending','confirmed','checked_in') AND tstzrange(r.start_datetime,r.end_datetime)&&tstzrange(cursor_at,ends))
      OR public.staff_break_overlaps(sid,cursor_at,ends)
    THEN RETURN NULL; END IF;
    result:=result||jsonb_build_array(jsonb_build_object('ordinal',n,'staff_id',sid,'service_ids',ids,
      'slot_start',cursor_at,'slot_end',ends,'price',amount,'duration_minutes',duration));
    n:=n+1;cursor_at:=ends;total:=total+amount;
  END LOOP;
  RETURN jsonb_build_object('segments',result,'slot_start',p_start,'slot_end',cursor_at,'total_price',total);
END $$;

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

  if public.staff_break_overlaps(p_staff_id, p_start, v_end) then
    raise exception 'break_conflict' using errcode = 'P0001';
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

-- statement --
CREATE OR REPLACE FUNCTION public.create_booking(p_salon uuid,p_segments jsonb,p_start timestamptz,p_name text,
  p_phone text,p_source booking_source,p_notes text)
RETURNS uuid LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE plan jsonb; part jsonb; first_part jsonb; bid uuid; ids uuid[]; sid uuid;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(p_salon::text,0));
  PERFORM 1 FROM public.salons WHERE id=p_salon FOR SHARE;
  -- Freeze catalog/assignments before snapshotting prices and durations. Same deterministic order for every visit.
  PERFORM 1 FROM public.staff WHERE id IN(SELECT (value->>'staff_id')::uuid FROM jsonb_array_elements(p_segments)) ORDER BY id FOR SHARE;
  PERFORM 1 FROM public.services WHERE id IN(SELECT x::uuid FROM jsonb_array_elements(p_segments) entry(value),
    jsonb_array_elements_text(entry.value->'service_ids')x) ORDER BY id FOR SHARE;
  PERFORM 1 FROM public.staff_services WHERE (staff_id,service_id) IN(
    SELECT (entry.value->>'staff_id')::uuid,x::uuid FROM jsonb_array_elements(p_segments)entry(value),
    jsonb_array_elements_text(entry.value->'service_ids')x) ORDER BY staff_id,service_id FOR SHARE;
  plan:=public.visit_plan(p_salon,p_start,p_segments);
  IF plan IS NULL THEN
    IF public.visit_break_conflict(p_start,p_segments) THEN
      RAISE EXCEPTION 'break_conflict' USING ERRCODE='P0001';
    END IF;
    RAISE EXCEPTION 'Selected slot is no longer available';
  END IF;
  first_part:=plan->'segments'->0;
  ids:=ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(first_part->'service_ids'));
  bid:=public.create_booking(p_salon,(first_part->>'staff_id')::uuid,ids,p_start,p_name,p_phone,p_source,p_notes);
  IF jsonb_array_length(p_segments)=1 THEN
    UPDATE public.bookings SET itinerary=plan->'segments' WHERE id=bid;
    RETURN bid;
  END IF;
  UPDATE public.bookings SET is_multi_staff=true,end_datetime=(plan->>'slot_end')::timestamptz,
    total_duration_minutes=extract(epoch FROM ((plan->>'slot_end')::timestamptz-p_start))/60,
    total_price=(plan->>'total_price')::numeric,service_fulfilment_amount=(plan->>'total_price')::numeric WHERE id=bid;
  FOR part IN SELECT value FROM jsonb_array_elements(plan->'segments') LOOP
    sid:=(part->>'staff_id')::uuid;
    ids:=ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(part->'service_ids'));
    INSERT INTO public.booking_segments(booking_id,ordinal,staff_id,service_ids,start_datetime,end_datetime)
      VALUES(bid,(part->>'ordinal')::int,sid,ids,(part->>'slot_start')::timestamptz,(part->>'slot_end')::timestamptz);
    IF (part->>'ordinal')::int>0 THEN
      INSERT INTO public.booking_services(booking_id,service_id,service_name,duration_minutes,price)
        SELECT bid,sv.id,sv.name,coalesce(ss.duration_minutes,sv.duration_minutes),coalesce(ss.price_override,sv.price)
        FROM public.services sv JOIN public.staff_services ss ON ss.service_id=sv.id
        WHERE sv.id=ANY(ids) AND ss.staff_id=sid AND ss.is_active;
      INSERT INTO public.booking_service_staff(booking_id,service_id,revision,salon_id,staff_id,changed_by)
        SELECT bid,x,1,p_salon,sid,auth.uid() FROM unnest(ids)x;
    END IF;
  END LOOP;
  UPDATE public.bookings SET itinerary=plan->'segments' WHERE id=bid;
  RETURN bid;
EXCEPTION WHEN exclusion_violation THEN RAISE EXCEPTION 'Selected slot is no longer available';
END $$;
