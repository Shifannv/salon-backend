-- Prepared only: does not activate U08 or move provider money.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
ALTER TABLE public.bookings ADD COLUMN change_version integer NOT NULL DEFAULT 0 CHECK (change_version >= 0);
-- statement --
ALTER TABLE public.bookings ADD COLUMN committed_reschedules integer NOT NULL DEFAULT 0 CHECK (committed_reschedules BETWEEN 0 AND 2);
-- statement --
ALTER TABLE public.bookings ADD COLUMN service_fulfilment_amount numeric(10,2) CHECK (service_fulfilment_amount >= 0);
-- statement --
ALTER TABLE public.booking_services ADD COLUMN is_active boolean NOT NULL DEFAULT true;
-- statement --
CREATE TABLE public.booking_customer_changes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE RESTRICT,
  version integer NOT NULL CHECK (version > 0),
  idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 128),
  request jsonb NOT NULL,
  old_start timestamptz NOT NULL,
  new_start timestamptz NOT NULL,
  old_staff_id uuid NOT NULL,
  new_staff_id uuid NOT NULL,
  previous_services jsonb NOT NULL,
  committed_services jsonb NOT NULL,
  previous_total numeric(10,2) NOT NULL,
  committed_total numeric(10,2) NOT NULL,
  fulfilment_amount numeric(10,2) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (booking_id, idempotency_key),
  UNIQUE (booking_id, version)
);
-- statement --
ALTER TABLE public.booking_customer_changes ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.booking_customer_changes FROM PUBLIC, anon, authenticated;
-- statement --
REVOKE ALL ON public.booking_customer_changes FROM service_role;
-- statement --
GRANT SELECT, INSERT ON public.booking_customer_changes TO service_role;
-- statement --
CREATE FUNCTION public.guard_booking_change_history() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  RAISE EXCEPTION 'booking_change_history_is_immutable' USING ERRCODE = '23514';
END $$;
-- statement --
CREATE TRIGGER booking_changes_immutable BEFORE UPDATE OR DELETE ON public.booking_customer_changes
FOR EACH ROW EXECUTE FUNCTION public.guard_booking_change_history();
-- statement --
CREATE TRIGGER booking_changes_no_truncate BEFORE TRUNCATE ON public.booking_customer_changes
FOR EACH STATEMENT EXECUTE FUNCTION public.guard_booking_change_history();
-- statement --
REVOKE ALL ON FUNCTION public.guard_booking_change_history() FROM PUBLIC, anon, authenticated;
-- statement --
create function public.get_available_slots(
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
            then
              slot_start := v_cursor;
              slot_end := v_try_end;
              return next;
            end if;
            v_cursor := v_cursor + make_interval(mins => p_duration_minutes);
          end loop;
        end $$;

-- statement --
REVOKE ALL ON FUNCTION public.get_available_slots(uuid,date,integer,uuid) FROM PUBLIC, anon, authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.get_available_slots(uuid,date,integer,uuid) TO service_role;
-- statement --
CREATE OR REPLACE FUNCTION public.get_available_slots(p_staff_id uuid, p_date date, p_duration_minutes integer)
RETURNS TABLE(slot_start timestamptz, slot_end timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
  SELECT * FROM public.get_available_slots(p_staff_id,p_date,p_duration_minutes,NULL::uuid)
$$;
-- statement --
CREATE FUNCTION public.booking_change_quote(p_booking uuid, p_staff uuid, p_services uuid[], p_start timestamptz)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
  b public.bookings%rowtype;
  v_duration integer;
  v_price numeric(10,2);
  v_count integer;
  v_tz text;
  v_paid numeric(10,2);
  v_due numeric(10,2);
  v_prepaid boolean;
  v_lines jsonb;
  v_quote jsonb;
BEGIN
  SELECT * INTO b FROM public.bookings WHERE id = p_booking AND customer_id = auth.uid();
  IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid()
      AND is_active AND role IN ('customer', 'owner')) THEN
    RAISE EXCEPTION 'booking_not_found' USING ERRCODE = 'P0001';
  END IF;
  IF b.checkout_policy_version <> 'u08-2026-10-23-v1' THEN
    RAISE EXCEPTION 'booking_change_policy_unsupported' USING ERRCODE = 'P0001';
  END IF;
  IF b.status NOT IN ('pending', 'confirmed') THEN
    RAISE EXCEPTION 'booking_state_conflict' USING ERRCODE = 'P0001';
  END IF;
  IF b.start_datetime <= statement_timestamp() + interval '4 hours' THEN
    RAISE EXCEPTION 'booking_change_cutoff' USING ERRCODE = 'P0001';
  END IF;
  IF p_start IS NULL OR p_staff IS NULL OR p_services IS NULL OR cardinality(p_services) NOT BETWEEN 1 AND 30
     OR EXISTS (SELECT 1 FROM unnest(p_services) sid GROUP BY sid HAVING sid IS NULL OR count(*) > 1) THEN
    RAISE EXCEPTION 'invalid_booking_change' USING ERRCODE = 'P0001';
  END IF;
  IF (p_start IS DISTINCT FROM b.start_datetime OR p_staff IS DISTINCT FROM b.staff_id)
     AND b.committed_reschedules >= 2 THEN
    RAISE EXCEPTION 'booking_change_limit' USING ERRCODE = 'P0001';
  END IF;
  SELECT s.timezone INTO v_tz FROM public.staff st JOIN public.salons s ON s.id = st.salon_id
  WHERE st.id = p_staff AND st.salon_id = b.salon_id AND st.is_active AND s.accepting_bookings
    AND s.is_active AND s.profile_completed AND s.approval_status = 'approved'
    AND public.salon_booking_eligible(s.id);
  IF NOT FOUND THEN RAISE EXCEPTION 'salon_not_accepting_bookings' USING ERRCODE = 'P0001'; END IF;
  SELECT count(*), sum(coalesce(ss.duration_minutes, sv.duration_minutes)),
         sum(coalesce(ss.price_override, sv.price)) INTO v_count, v_duration, v_price
  FROM public.services sv JOIN public.staff_services ss ON ss.service_id = sv.id
    AND ss.staff_id = p_staff AND ss.is_active
  WHERE sv.id = ANY(p_services) AND sv.salon_id = b.salon_id AND sv.is_active;
  IF v_count <> cardinality(p_services) OR v_duration NOT BETWEEN 1 AND 1440 OR v_price IS NULL THEN
    RAISE EXCEPTION 'invalid_booking_change' USING ERRCODE = 'P0001';
  END IF;
  IF p_staff = b.staff_id AND (SELECT array_agg(service_id ORDER BY service_id)
      FROM public.booking_services WHERE booking_id=b.id AND is_active)
      = (SELECT array_agg(sid ORDER BY sid) FROM unnest(p_services) sid) THEN
    SELECT sum(duration_minutes),sum(price),jsonb_agg(jsonb_build_object('id',service_id,
      'name',service_name,'duration',duration_minutes,'price',price) ORDER BY service_id)
      INTO v_duration,v_price,v_lines FROM public.booking_services WHERE booking_id=b.id AND is_active;
  ELSE
    SELECT jsonb_agg(jsonb_build_object('id',sv.id,'name',sv.name,
      'duration',coalesce(ss.duration_minutes,sv.duration_minutes),'price',coalesce(ss.price_override,sv.price))
      ORDER BY sv.id) INTO v_lines FROM public.services sv JOIN public.staff_services ss
      ON ss.service_id=sv.id AND ss.staff_id=p_staff WHERE sv.id=ANY(p_services);
  END IF;
  v_paid := b.paid_amount - b.refunded_amount;
  v_prepaid := b.payment_preference <> 'pay_at_salon' AND b.payment_status = 'paid'
    AND b.payment_method = 'online' AND b.refunded_amount = 0 AND v_paid >= b.total_price
    AND NOT EXISTS (SELECT 1 FROM public.booking_payments WHERE booking_id=b.id
      AND channel='manual' AND status IN ('captured','partially_refunded','refunded'));
  IF EXISTS (SELECT 1 FROM public.payment_refunds r WHERE r.booking_id = b.id
      AND r.status NOT IN ('failed', 'cancelled')) OR (v_paid > 0 AND NOT v_prepaid)
      OR (b.payment_preference <> 'pay_at_salon' AND NOT v_prepaid)
      OR EXISTS (SELECT 1 FROM public.booking_payments WHERE booking_id=b.id AND status IN ('created','authorized')) THEN
    RAISE EXCEPTION 'booking_change_payment_reconciliation_required' USING ERRCODE = 'P0001';
  END IF;
  v_due := CASE WHEN v_prepaid THEN greatest(0, v_price - v_paid) ELSE 0 END;
  v_quote := jsonb_build_object('booking_id', b.id, 'version', b.change_version,
    'committed_reschedules', b.committed_reschedules, 'duration_minutes', v_duration,
    'service_amount', v_price, 'retained_paid_amount', v_paid,
    'additional_payment_required', v_due,
    'total_payable', CASE WHEN v_prepaid THEN greatest(v_price, v_paid) ELSE v_price END);
  RETURN v_quote || jsonb_build_object('lines',v_lines,'quote_fingerprint',
    encode(sha256(convert_to((v_quote || jsonb_build_object('staff',p_staff,'start_epoch',
      extract(epoch FROM p_start),'lines',v_lines))::text,'UTF8')),'hex'),
    'slot_available', EXISTS (SELECT 1 FROM public.get_available_slots(
      p_staff, (p_start AT TIME ZONE v_tz)::date, v_duration, b.id) g WHERE g.slot_start = p_start));
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.booking_change_quote(uuid,uuid,uuid[],timestamptz) FROM PUBLIC, anon, authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.booking_change_quote(uuid,uuid,uuid[],timestamptz) TO service_role;
-- statement --
CREATE FUNCTION public.apply_customer_booking_change(p_booking uuid, p_staff uuid, p_services uuid[],
  p_start timestamptz, p_expected_version integer, p_key text, p_quote text)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE
  b public.bookings%rowtype;
  previous public.booking_customer_changes%rowtype;
  q jsonb;
  v_request jsonb;
  v_before jsonb;
  v_after jsonb;
  v_sorted uuid[];
  v_salon uuid;
BEGIN
  -- Closure commands acquire this salon lock before booking row locks too.
  SELECT salon_id INTO v_salon FROM public.bookings WHERE id=p_booking AND customer_id=auth.uid();
  IF NOT FOUND THEN RAISE EXCEPTION 'booking_not_found' USING ERRCODE='P0001'; END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(v_salon::text,0));
  SELECT * INTO b FROM public.bookings WHERE id = p_booking AND customer_id = auth.uid() FOR UPDATE;
  IF NOT FOUND OR NOT EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid()
      AND is_active AND role IN ('customer', 'owner')) THEN
    RAISE EXCEPTION 'booking_not_found' USING ERRCODE = 'P0001';
  END IF;
  IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 128 THEN
    RAISE EXCEPTION 'invalid_booking_change' USING ERRCODE = 'P0001';
  END IF;
  SELECT array_agg(sid ORDER BY sid) INTO v_sorted FROM unnest(p_services) sid;
  v_request := jsonb_build_object('staff_id', p_staff, 'service_ids', v_sorted,
    'start_epoch', extract(epoch FROM p_start), 'expected_version', p_expected_version,'quote_fingerprint',p_quote);
  SELECT * INTO previous FROM public.booking_customer_changes WHERE booking_id = b.id AND idempotency_key = p_key;
  IF FOUND THEN
    IF previous.request <> v_request THEN RAISE EXCEPTION 'idempotency_key_reused' USING ERRCODE = 'P0001'; END IF;
    RETURN b.id;
  END IF;
  IF p_expected_version IS DISTINCT FROM b.change_version THEN
    RAISE EXCEPTION 'booking_change_version_conflict' USING ERRCODE = 'P0001';
  END IF;
  -- Freeze the chosen staff/catalog values until the transaction commits.
  PERFORM 1 FROM public.salons WHERE id=b.salon_id FOR SHARE;
  PERFORM 1 FROM public.staff WHERE id = p_staff FOR SHARE;
  PERFORM 1 FROM public.services WHERE id = ANY(p_services) ORDER BY id FOR SHARE;
  PERFORM 1 FROM public.staff_services WHERE staff_id = p_staff AND service_id = ANY(p_services)
    ORDER BY service_id FOR SHARE;
  q := public.booking_change_quote(p_booking, p_staff, p_services, p_start);
  IF p_quote IS DISTINCT FROM q->>'quote_fingerprint' THEN
    RAISE EXCEPTION 'booking_change_quote_stale' USING ERRCODE='P0001';
  END IF;
  IF NOT (q->>'slot_available')::boolean THEN RAISE EXCEPTION 'slot_unavailable' USING ERRCODE = 'P0001'; END IF;
  IF (q->>'additional_payment_required')::numeric > 0 THEN
    RAISE EXCEPTION 'additional_payment_required' USING ERRCODE = 'P0001';
  END IF;
  IF p_start = b.start_datetime AND p_staff = b.staff_id
     AND (SELECT array_agg(service_id ORDER BY service_id) FROM public.booking_services
          WHERE booking_id = b.id AND is_active) = v_sorted THEN
    RAISE EXCEPTION 'booking_change_unchanged' USING ERRCODE = 'P0001';
  END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_object('service_id', service_id, 'name', service_name,
    'duration', duration_minutes, 'price', price) ORDER BY service_id), '[]') INTO v_before
    FROM public.booking_services WHERE booking_id = b.id AND is_active;
  UPDATE public.bookings SET staff_id = p_staff, start_datetime = p_start,
    end_datetime = p_start + make_interval(mins => (q->>'duration_minutes')::integer),
    total_duration_minutes = (q->>'duration_minutes')::integer,
    total_price = (q->>'total_payable')::numeric,
    service_fulfilment_amount = (q->>'service_amount')::numeric,
    estimated_end_datetime = NULL,
    change_version = change_version + 1,
    committed_reschedules = committed_reschedules + CASE WHEN p_start <> b.start_datetime OR p_staff <> b.staff_id THEN 1 ELSE 0 END
    WHERE id = b.id;
  UPDATE public.booking_services SET is_active = false WHERE booking_id = b.id AND is_active;
  INSERT INTO public.booking_services(booking_id,service_id,service_name,duration_minutes,price,is_active)
  SELECT b.id, (line->>'id')::uuid, line->>'name',(line->>'duration')::integer,(line->>'price')::numeric,true
  FROM jsonb_array_elements(q->'lines') line
  ON CONFLICT (booking_id, service_id) DO UPDATE SET service_name = excluded.service_name,
    duration_minutes = excluded.duration_minutes, price = excluded.price, is_active = true;
  SELECT jsonb_agg(jsonb_build_object('service_id', service_id, 'name', service_name,
    'duration', duration_minutes, 'price', price) ORDER BY service_id) INTO v_after
    FROM public.booking_services WHERE booking_id = b.id AND is_active;
  INSERT INTO public.booking_customer_changes(booking_id,version,idempotency_key,request,old_start,new_start,
    old_staff_id,new_staff_id,previous_services,committed_services,previous_total,committed_total,fulfilment_amount)
  VALUES (b.id,b.change_version+1,p_key,v_request,b.start_datetime,p_start,b.staff_id,p_staff,v_before,v_after,
    b.total_price,(q->>'total_payable')::numeric,(q->>'service_amount')::numeric);
  -- Persist notifications and push work together with the change; retries do not duplicate them.
  WITH recipients AS (
    SELECT b.customer_id AS user_id UNION SELECT owner_id FROM public.salons WHERE id = b.salon_id
  ), notices AS (
    INSERT INTO public.notifications(user_id,booking_id,type,title,body)
    SELECT user_id,b.id,'booking_changed','Booking updated','The appointment services or time have changed. Open the booking for details.'
    FROM recipients WHERE user_id IS NOT NULL RETURNING id,user_id
  ) INSERT INTO public.notification_outbox(notification_id,user_id) SELECT id,user_id FROM notices;
  RETURN b.id;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.apply_customer_booking_change(uuid,uuid,uuid[],timestamptz,integer,text,text) FROM PUBLIC, anon, authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.apply_customer_booking_change(uuid,uuid,uuid[],timestamptz,integer,text,text) TO service_role;
