-- Prepared only. Apply explicitly after review; never at application startup.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
CREATE TABLE public.pay_at_salon_booking_policy (
  singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
  per_date integer NOT NULL CHECK(per_date BETWEEN 1 AND 20),
  upcoming integer NOT NULL CHECK(upcoming BETWEEN 1 AND 50),
  rolling_week integer NOT NULL CHECK(rolling_week BETWEEN 1 AND 100)
);
-- statement --
INSERT INTO public.pay_at_salon_booking_policy VALUES(true,3,5,8);
-- statement --
ALTER TABLE public.pay_at_salon_booking_policy ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.pay_at_salon_booking_policy FROM PUBLIC,anon,authenticated,service_role;
-- statement --
GRANT SELECT ON public.pay_at_salon_booking_policy TO service_role;
-- statement --
ALTER TABLE public.bookings ADD COLUMN pay_at_salon_quota_released boolean NOT NULL DEFAULT false;
-- statement --
-- Restore quota for known salon-caused terminal bookings, never customer cancellations.
UPDATE public.bookings b SET pay_at_salon_quota_released=true
WHERE b.status='rejected' OR (b.status='cancelled' AND EXISTS(
 SELECT 1 FROM public.booking_financial_outcomes f WHERE f.booking_id=b.id AND f.kind='salon_cancellation'));
-- statement --
CREATE INDEX bookings_customer_quota_created ON public.bookings(customer_id,created_at)
 WHERE payment_preference='pay_at_salon' AND NOT pay_at_salon_quota_released;
-- statement --
create or replace function public.guard_booking_checkout()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_block timestamptz; limits public.pay_at_salon_booking_policy%rowtype;
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
    SELECT * INTO STRICT limits FROM public.pay_at_salon_booking_policy WHERE singleton;
    IF (SELECT count(*) FROM public.bookings b WHERE b.customer_id=new.customer_id AND b.id<>new.id
       AND b.booking_calendar_date=new.booking_calendar_date AND b.payment_preference='pay_at_salon'
       AND b.status NOT IN ('cancelled','rejected') AND NOT b.pay_at_salon_quota_released)>=limits.per_date THEN
      RAISE EXCEPTION 'pay_at_salon_daily_limit' USING ERRCODE='23514';
    END IF;
    IF new.start_datetime>now() AND (SELECT count(*) FROM public.bookings b
       WHERE b.customer_id=new.customer_id AND b.id<>new.id AND b.payment_preference='pay_at_salon'
       AND b.status IN ('pending','confirmed','checked_in') AND b.start_datetime>now())>=limits.upcoming THEN
      RAISE EXCEPTION 'pay_at_salon_upcoming_limit' USING ERRCODE='23514';
    END IF;
    IF TG_OP='INSERT' AND (SELECT count(*) FROM public.bookings b
       WHERE b.customer_id=new.customer_id AND b.payment_preference='pay_at_salon'
       AND NOT b.pay_at_salon_quota_released AND b.created_at>now()-interval '7 days')>=limits.rolling_week THEN
      RAISE EXCEPTION 'pay_at_salon_weekly_limit' USING ERRCODE='23514';
    END IF;
  end if;
  -- Release a weekly credit only for an actual salon-caused cancellation/rejection.
  IF TG_OP='INSERT' THEN new.pay_at_salon_quota_released:=false;
  ELSE
    new.pay_at_salon_quota_released:=old.pay_at_salon_quota_released OR new.status='rejected' OR
      (new.status='cancelled' AND old.status<>new.status AND
       coalesce(current_setting('app.booking_cancel_origin',true)='salon',false));
  END IF;
  -- Every booking is for the account holder. Different staff/salons cannot overlap.
  IF new.customer_id IS NOT NULL AND new.status IN ('pending','confirmed','checked_in')
    AND (TG_OP='INSERT' OR new.start_datetime IS DISTINCT FROM old.start_datetime
      OR new.end_datetime IS DISTINCT FROM old.end_datetime) THEN
    PERFORM pg_advisory_xact_lock(hashtextextended(new.customer_id::text,3715));
    IF EXISTS(SELECT 1 FROM public.bookings b WHERE b.customer_id=new.customer_id AND b.id<>new.id
      AND b.status IN ('pending','confirmed','checked_in')
      AND tstzrange(b.start_datetime,b.end_datetime)&&tstzrange(new.start_datetime,new.end_datetime)) THEN
      RAISE EXCEPTION 'customer_booking_overlap' USING ERRCODE='23514';
    END IF;
  END IF;
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
-- Old cancellation approval requests are history; customers now cancel directly.
UPDATE public.booking_action_requests SET status='resolved',decision='invalidated',
 decision_reason='Cancellation no longer requires salon approval; cancel directly before the appointment starts.',
 resolved_at=now() WHERE kind='cancellation' AND status='pending';

-- statement --
CREATE FUNCTION public.visit_service_totals(p_staff uuid,p_ids uuid[],p_booking uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE saved boolean; result jsonb;
BEGIN
 SELECT EXISTS(SELECT 1 FROM public.bookings b WHERE b.id=p_booking AND b.customer_id=auth.uid() AND
   ((NOT b.is_multi_staff AND b.staff_id=p_staff AND
      (SELECT array_agg(service_id ORDER BY service_id) FROM public.booking_services WHERE booking_id=b.id AND is_active)
      =(SELECT array_agg(x ORDER BY x) FROM unnest(p_ids)x)) OR
    EXISTS(SELECT 1 FROM jsonb_array_elements(b.itinerary) part WHERE (part->>'staff_id')::uuid=p_staff
      AND ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(part->'service_ids') ORDER BY value)
          =(SELECT array_agg(x ORDER BY x) FROM unnest(p_ids)x)))) INTO saved;
 IF saved THEN
   SELECT jsonb_build_object('duration',sum(duration_minutes),'amount',sum(price),'lines',
    jsonb_agg(jsonb_build_object('id',service_id,'name',service_name,'duration',duration_minutes,'price',price) ORDER BY service_id))
    INTO result FROM public.booking_services WHERE booking_id=p_booking AND is_active AND service_id=ANY(p_ids);
 ELSE
   SELECT jsonb_build_object('duration',sum(coalesce(ss.duration_minutes,sv.duration_minutes)),
    'amount',sum(coalesce(ss.price_override,sv.price)),'lines',jsonb_agg(jsonb_build_object(
     'id',sv.id,'name',sv.name,'duration',coalesce(ss.duration_minutes,sv.duration_minutes),
     'price',coalesce(ss.price_override,sv.price)) ORDER BY sv.id)) INTO result
   FROM public.services sv JOIN public.staff_services ss ON ss.service_id=sv.id
   WHERE sv.id=ANY(p_ids) AND ss.staff_id=p_staff AND ss.is_active;
 END IF;
 RETURN result;
END $$;
-- statement --
CREATE FUNCTION public.visit_plan(p_salon uuid,p_start timestamptz,p_segments jsonb,p_exclude uuid)
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
    THEN RETURN NULL; END IF;
    result:=result||jsonb_build_array(jsonb_build_object('ordinal',n,'staff_id',sid,'service_ids',ids,
      'slot_start',cursor_at,'slot_end',ends,'price',amount,'duration_minutes',duration));
    n:=n+1;cursor_at:=ends;total:=total+amount;
  END LOOP;
  RETURN jsonb_build_object('segments',result,'slot_start',p_start,'slot_end',cursor_at,'total_price',total);
END $$;

-- statement --
CREATE OR REPLACE FUNCTION public.visit_plan(p_salon uuid,p_start timestamptz,p_segments jsonb)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
 SELECT public.visit_plan(p_salon,p_start,p_segments,NULL::uuid)
$$;
-- statement --
CREATE FUNCTION public.get_available_slots(p_salon uuid,p_date date,p_segments jsonb,p_consecutive boolean,p_exclude uuid)
RETURNS TABLE(slot_start timestamptz,slot_end timestamptz,segments jsonb,total_price numeric)
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE duration integer; candidate record; plan jsonb; first_part jsonb:=p_segments->0;
BEGIN
 IF p_exclude IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.bookings WHERE id=p_exclude
   AND customer_id=auth.uid() AND salon_id=p_salon AND status IN ('pending','confirmed')) THEN
   RAISE EXCEPTION 'booking_not_found' USING ERRCODE='P0001';
 END IF;
 duration:=(public.visit_service_totals((first_part->>'staff_id')::uuid,
   ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(first_part->'service_ids')),p_exclude)->>'duration')::integer;
 IF duration IS NULL OR duration<=0 THEN RETURN; END IF;
 FOR candidate IN SELECT * FROM public.get_available_slots((first_part->>'staff_id')::uuid,p_date,duration,p_exclude) LOOP
   plan:=public.visit_plan(p_salon,candidate.slot_start,p_segments,p_exclude);
   IF plan IS NOT NULL THEN
     slot_start:=candidate.slot_start;slot_end:=(plan->>'slot_end')::timestamptz;
     segments:=plan->'segments';total_price:=(plan->>'total_price')::numeric;RETURN NEXT;
   END IF;
 END LOOP;
END $$;
-- statement --
CREATE FUNCTION public.booking_visit_change_quote(p_booking uuid,p_segments jsonb,p_start timestamptz)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE b public.bookings%rowtype; plan jsonb; quote jsonb; paid numeric; prepaid boolean; price numeric;
 old_assignments jsonb; assignments jsonb; changed boolean;
BEGIN
 SELECT * INTO b FROM public.bookings WHERE id=p_booking AND customer_id=auth.uid();
 IF NOT FOUND OR NOT EXISTS(SELECT 1 FROM public.profiles WHERE id=auth.uid() AND is_active AND role IN ('customer','owner')) THEN
   RAISE EXCEPTION 'booking_not_found' USING ERRCODE='P0001'; END IF;
 IF b.checkout_policy_version<>'u08-2026-10-23-v1' AND NOT(b.payment_preference='pay_at_salon' AND b.paid_amount=0) THEN
   RAISE EXCEPTION 'booking_change_policy_unsupported' USING ERRCODE='P0001'; END IF;
 IF b.status NOT IN ('pending','confirmed') THEN RAISE EXCEPTION 'booking_state_conflict' USING ERRCODE='P0001'; END IF;
 IF b.start_datetime<=statement_timestamp()+interval '4 hours' THEN RAISE EXCEPTION 'booking_change_cutoff' USING ERRCODE='P0001'; END IF;
 IF p_start IS NULL OR jsonb_typeof(p_segments)<>'array' OR jsonb_array_length(p_segments) NOT BETWEEN 1 AND 30 THEN
   RAISE EXCEPTION 'invalid_booking_change' USING ERRCODE='P0001'; END IF;
 old_assignments:=CASE WHEN b.itinerary<>'[]'::jsonb THEN b.itinerary ELSE jsonb_build_array(jsonb_build_object(
   'staff_id',b.staff_id,'service_ids',(SELECT jsonb_agg(service_id ORDER BY service_id) FROM public.booking_services WHERE booking_id=b.id AND is_active))) END;
 -- Assignment changes, including a secondary professional, consume a reschedule.
 SELECT jsonb_agg(value->'staff_id' ORDER BY ordinal) INTO old_assignments FROM jsonb_array_elements(old_assignments) WITH ORDINALITY x(value,ordinal);
 SELECT jsonb_agg(value->'staff_id' ORDER BY ordinal) INTO assignments FROM jsonb_array_elements(p_segments) WITH ORDINALITY x(value,ordinal);
 changed:=p_start IS DISTINCT FROM b.start_datetime OR assignments IS DISTINCT FROM old_assignments;
 IF changed AND b.committed_reschedules>=2 THEN RAISE EXCEPTION 'booking_change_limit' USING ERRCODE='P0001'; END IF;
 -- Plan at the requested instant while excluding only this owned booking.
 plan:=public.visit_plan(b.salon_id,p_start,p_segments,b.id);
 IF plan IS NULL THEN RETURN jsonb_build_object('slot_available',false,'can_commit',false,'restriction_code','slot_unavailable','booking_id',b.id,'version',b.change_version,
  'committed_reschedules',b.committed_reschedules,'duration_minutes',0,'service_amount',0,'retained_paid_amount',0,
  'additional_payment_required',0,'total_payable',0,'quote_fingerprint',repeat('0',64),'segments','[]'::jsonb); END IF;
 SELECT jsonb_agg(jsonb_build_object('staff_id',value->'staff_id','slot_start',value->'slot_start') ORDER BY ordinal) INTO assignments
 FROM jsonb_array_elements(plan->'segments') WITH ORDINALITY x(value,ordinal);
 IF b.is_multi_staff THEN
   SELECT jsonb_agg(jsonb_build_object('staff_id',value->'staff_id','slot_start',value->'slot_start') ORDER BY ordinal) INTO old_assignments
   FROM jsonb_array_elements(b.itinerary) WITH ORDINALITY x(value,ordinal);
   changed:=changed OR assignments IS DISTINCT FROM old_assignments;
 END IF;
 IF changed AND b.committed_reschedules>=2 THEN RAISE EXCEPTION 'booking_change_limit' USING ERRCODE='P0001'; END IF;
 price:=(plan->>'total_price')::numeric;
 paid:=b.paid_amount-b.refunded_amount;
 prepaid:=b.payment_preference<>'pay_at_salon' AND b.payment_status='paid' AND b.payment_method='online'
   AND b.refunded_amount=0 AND paid>=b.total_price AND NOT EXISTS(SELECT 1 FROM public.booking_payments
     WHERE booking_id=b.id AND channel='manual' AND status IN ('captured','partially_refunded','refunded'));
 IF EXISTS(SELECT 1 FROM public.payment_refunds WHERE booking_id=b.id AND status NOT IN ('failed','cancelled'))
   OR (paid>0 AND NOT prepaid) OR (b.payment_preference<>'pay_at_salon' AND NOT prepaid)
   OR EXISTS(SELECT 1 FROM public.booking_payments WHERE booking_id=b.id AND status IN ('created','authorized')) THEN
   RAISE EXCEPTION 'booking_change_payment_reconciliation_required' USING ERRCODE='P0001'; END IF;
 quote:=jsonb_build_object('booking_id',b.id,'version',b.change_version,'committed_reschedules',b.committed_reschedules,
  'duration_minutes',(extract(epoch FROM ((plan->>'slot_end')::timestamptz-p_start))/60)::integer,'service_amount',price,
  'retained_paid_amount',paid,'additional_payment_required',CASE WHEN prepaid THEN greatest(0,price-paid) ELSE 0 END,
  'total_payable',CASE WHEN prepaid THEN greatest(price,paid) ELSE price END,'segments',plan->'segments','changes_time',changed,
  'can_commit',NOT prepaid OR price=coalesce(b.service_fulfilment_amount,(SELECT sum(bs.price) FROM public.booking_services bs WHERE bs.booking_id=b.id AND bs.is_active),b.total_price),
  'restriction_code',CASE WHEN prepaid AND price<>coalesce(b.service_fulfilment_amount,(SELECT sum(bs.price) FROM public.booking_services bs WHERE bs.booking_id=b.id AND bs.is_active),b.total_price) THEN 'prepaid_change_amount_mismatch' ELSE NULL END);
 RETURN quote||jsonb_build_object('slot_available',true,'quote_fingerprint',encode(sha256(convert_to(quote::text,'UTF8')),'hex'));
END $$;
-- statement --
CREATE FUNCTION public.apply_customer_visit_change(p_booking uuid,p_segments jsonb,p_start timestamptz,
 p_expected_version integer,p_key text,p_quote text)
RETURNS uuid LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE b public.bookings%rowtype; previous public.booking_customer_changes%rowtype; q jsonb; request jsonb;
 salon uuid; part jsonb; totals jsonb; first_staff uuid; before_lines jsonb; after_lines jsonb;
BEGIN
 SELECT salon_id INTO salon FROM public.bookings WHERE id=p_booking AND customer_id=auth.uid();
 IF NOT FOUND THEN RAISE EXCEPTION 'booking_not_found' USING ERRCODE='P0001'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(salon::text,0));
 SELECT * INTO b FROM public.bookings WHERE id=p_booking AND customer_id=auth.uid() FOR UPDATE;
 IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 128 THEN RAISE EXCEPTION 'invalid_booking_change' USING ERRCODE='P0001'; END IF;
 request:=jsonb_build_object('segments',p_segments,'start_epoch',extract(epoch FROM p_start),'expected_version',p_expected_version,'quote_fingerprint',p_quote);
 SELECT * INTO previous FROM public.booking_customer_changes WHERE booking_id=b.id AND idempotency_key=p_key;
 IF FOUND THEN
   IF (previous.request-'previous_itinerary'-'committed_itinerary')<>request THEN RAISE EXCEPTION 'idempotency_key_reused' USING ERRCODE='P0001'; END IF;
   RETURN b.id;
 END IF;
 IF p_expected_version IS DISTINCT FROM b.change_version THEN RAISE EXCEPTION 'booking_change_version_conflict' USING ERRCODE='P0001'; END IF;
 PERFORM 1 FROM public.salons WHERE id=salon FOR SHARE;
 PERFORM 1 FROM public.staff WHERE id IN(SELECT (value->>'staff_id')::uuid FROM jsonb_array_elements(p_segments)) ORDER BY id FOR SHARE;
 PERFORM 1 FROM public.services WHERE id IN(SELECT x::uuid FROM jsonb_array_elements(p_segments) entry(value),jsonb_array_elements_text(entry.value->'service_ids')x) ORDER BY id FOR SHARE;
 PERFORM 1 FROM public.staff_services WHERE (staff_id,service_id) IN(SELECT (entry.value->>'staff_id')::uuid,x::uuid
   FROM jsonb_array_elements(p_segments)entry(value),jsonb_array_elements_text(entry.value->'service_ids')x) ORDER BY staff_id,service_id FOR SHARE;
 q:=public.booking_visit_change_quote(p_booking,p_segments,p_start);
 IF NOT (q->>'slot_available')::boolean THEN RAISE EXCEPTION 'slot_unavailable' USING ERRCODE='P0001'; END IF;
 IF p_quote IS DISTINCT FROM q->>'quote_fingerprint' THEN RAISE EXCEPTION 'booking_change_quote_stale' USING ERRCODE='P0001'; END IF;
 IF (q->>'can_commit')::boolean IS DISTINCT FROM true THEN RAISE EXCEPTION 'prepaid_change_amount_mismatch' USING ERRCODE='P0001'; END IF;
 IF (q->>'additional_payment_required')::numeric>0 THEN RAISE EXCEPTION 'additional_payment_required' USING ERRCODE='P0001'; END IF;
 IF b.itinerary=q->'segments' THEN RAISE EXCEPTION 'booking_change_unchanged' USING ERRCODE='P0001'; END IF;
 SELECT jsonb_agg(jsonb_build_object('service_id',service_id,'name',service_name,'duration',duration_minutes,'price',price) ORDER BY service_id)
 INTO before_lines FROM public.booking_services WHERE booking_id=b.id AND is_active;
 -- Snapshot helper must run before deactivating the original service lines.
 SELECT jsonb_agg(jsonb_build_object('part',value,'totals',public.visit_service_totals((value->>'staff_id')::uuid,
  ARRAY(SELECT x::uuid FROM jsonb_array_elements_text(value->'service_ids')x),b.id))) INTO totals FROM jsonb_array_elements(p_segments);
 PERFORM set_config('app.visit_change_booking_id',b.id::text,true);
 UPDATE public.booking_segments SET is_active=false WHERE booking_id=b.id AND is_active;
 first_staff:=(p_segments->0->>'staff_id')::uuid;
 UPDATE public.bookings SET staff_id=first_staff,start_datetime=p_start,
   end_datetime=(q->'segments'->-1->>'slot_end')::timestamptz,
   total_duration_minutes=(q->>'duration_minutes')::integer,total_price=(q->>'total_payable')::numeric,
   service_fulfilment_amount=(q->>'service_amount')::numeric,estimated_end_datetime=NULL,
   is_multi_staff=jsonb_array_length(p_segments)>1,itinerary=q->'segments',change_version=change_version+1,
   committed_reschedules=committed_reschedules+CASE WHEN (q->>'changes_time')::boolean THEN 1 ELSE 0 END WHERE id=b.id;
 IF jsonb_array_length(p_segments)>1 THEN
   FOR part IN SELECT value FROM jsonb_array_elements(q->'segments') LOOP
     INSERT INTO public.booking_segments(booking_id,ordinal,staff_id,service_ids,start_datetime,end_datetime,is_active)
     VALUES(b.id,(part->>'ordinal')::int,(part->>'staff_id')::uuid,
       ARRAY(SELECT value::uuid FROM jsonb_array_elements_text(part->'service_ids')),
       (part->>'slot_start')::timestamptz,(part->>'slot_end')::timestamptz,true)
     ON CONFLICT(booking_id,ordinal) DO UPDATE SET staff_id=excluded.staff_id,service_ids=excluded.service_ids,
       start_datetime=excluded.start_datetime,end_datetime=excluded.end_datetime,is_active=true;
   END LOOP;
 END IF;
 UPDATE public.booking_services SET is_active=false WHERE booking_id=b.id AND is_active;
 FOR part IN SELECT value FROM jsonb_array_elements(totals) LOOP
   INSERT INTO public.booking_services(booking_id,service_id,service_name,duration_minutes,price,is_active)
   SELECT b.id,(line->>'id')::uuid,line->>'name',(line->>'duration')::int,(line->>'price')::numeric,true
   FROM jsonb_array_elements(part->'totals'->'lines')line
   ON CONFLICT(booking_id,service_id) DO UPDATE SET service_name=excluded.service_name,duration_minutes=excluded.duration_minutes,price=excluded.price,is_active=true;
   INSERT INTO public.booking_service_staff(booking_id,service_id,revision,salon_id,staff_id,changed_by)
   SELECT b.id,(line->>'id')::uuid,coalesce((SELECT max(revision) FROM public.booking_service_staff
     WHERE booking_id=b.id AND service_id=(line->>'id')::uuid),0)+1,salon,(part->'part'->>'staff_id')::uuid,auth.uid()
   FROM jsonb_array_elements(part->'totals'->'lines')line;
 END LOOP;
 SELECT jsonb_agg(jsonb_build_object('service_id',service_id,'name',service_name,'duration',duration_minutes,'price',price) ORDER BY service_id)
 INTO after_lines FROM public.booking_services WHERE booking_id=b.id AND is_active;
 INSERT INTO public.booking_customer_changes(booking_id,version,idempotency_key,request,old_start,new_start,old_staff_id,new_staff_id,
   previous_services,committed_services,previous_total,committed_total,fulfilment_amount)
 VALUES(b.id,b.change_version+1,p_key,request||jsonb_build_object('previous_itinerary',b.itinerary,'committed_itinerary',q->'segments'),b.start_datetime,p_start,b.staff_id,first_staff,
   before_lines,after_lines,b.total_price,(q->>'total_payable')::numeric,(q->>'service_amount')::numeric);
 WITH recipients AS(SELECT b.customer_id user_id UNION SELECT owner_id FROM public.salons WHERE id=salon),
 notices AS(INSERT INTO public.notifications(user_id,booking_id,type,title,body)
  SELECT user_id,b.id,'booking_changed','Booking updated','The appointment services or time have changed. Open the booking for details.'
  FROM recipients WHERE user_id IS NOT NULL RETURNING id,user_id)
 INSERT INTO public.notification_outbox(notification_id,user_id) SELECT id,user_id FROM notices;
 PERFORM set_config('app.visit_change_booking_id','',true);
 RETURN b.id;
END $$;
-- statement --
CREATE OR REPLACE FUNCTION public.guard_visit_reservation() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE salon uuid; b public.bookings;
BEGIN
  IF TG_TABLE_NAME='bookings' THEN
    salon:=NEW.salon_id;
    -- Pure releases, approvals and payment updates do not allocate resources. In particular,
    -- cancellation already holds the parent row, while closure holds salon then parent.
    IF TG_OP='UPDATE' AND NEW.staff_id IS NOT DISTINCT FROM OLD.staff_id
      AND NEW.start_datetime IS NOT DISTINCT FROM OLD.start_datetime AND NEW.end_datetime IS NOT DISTINCT FROM OLD.end_datetime
      AND NEW.is_multi_staff IS NOT DISTINCT FROM OLD.is_multi_staff
      AND NOT(NEW.status IN ('pending','confirmed','checked_in') AND OLD.status NOT IN ('pending','confirmed','checked_in')) THEN
      RETURN NEW;
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(salon::text,0));
    IF TG_OP='UPDATE' AND OLD.is_multi_staff AND current_setting('app.visit_change_booking_id',true) IS DISTINCT FROM NEW.id::text AND
       (NEW.staff_id IS DISTINCT FROM OLD.staff_id OR NEW.start_datetime IS DISTINCT FROM OLD.start_datetime
        OR NEW.end_datetime IS DISTINCT FROM OLD.end_datetime OR NEW.is_multi_staff IS DISTINCT FROM OLD.is_multi_staff) THEN
      RAISE EXCEPTION 'visit_change_requires_full_itinerary' USING ERRCODE='23514';
    END IF;
    IF NOT NEW.is_multi_staff AND NEW.status IN ('pending','confirmed','checked_in') AND EXISTS(
      SELECT 1 FROM public.booking_staff_reservations r WHERE r.booking_id<>NEW.id AND r.staff_id=NEW.staff_id
      AND r.status IN ('pending','confirmed','checked_in')
      AND tstzrange(r.start_datetime,r.end_datetime)&&tstzrange(NEW.start_datetime,NEW.end_datetime)
    ) THEN RAISE EXCEPTION 'Selected slot is no longer available'; END IF;
  ELSE
    SELECT * INTO b FROM public.bookings WHERE id=NEW.booking_id;
    IF TG_OP='UPDATE' AND NOT NEW.is_active
      AND (to_jsonb(NEW)-'is_active') IS NOT DISTINCT FROM (to_jsonb(OLD)-'is_active') THEN RETURN NEW; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(b.salon_id::text,0));
    IF NOT b.is_multi_staff OR NOT EXISTS(SELECT 1 FROM public.staff WHERE id=NEW.staff_id AND salon_id=b.salon_id) THEN
      RAISE EXCEPTION 'invalid_visit_staff' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' AND current_setting('app.visit_change_booking_id',true) IS DISTINCT FROM NEW.booking_id::text AND (to_jsonb(NEW)-'is_active') IS DISTINCT FROM (to_jsonb(OLD)-'is_active') THEN
      RAISE EXCEPTION 'visit_segments_are_immutable' USING ERRCODE='23514';
    END IF;
    IF NEW.is_active AND EXISTS(SELECT 1 FROM public.booking_staff_reservations r
      WHERE r.booking_id<>NEW.booking_id AND r.staff_id=NEW.staff_id
        AND r.status IN ('pending','confirmed','checked_in')
        AND tstzrange(r.start_datetime,r.end_datetime)&&tstzrange(NEW.start_datetime,NEW.end_datetime)) THEN
      RAISE EXCEPTION 'Selected slot is no longer available';
    END IF;
  END IF;
  RETURN NEW;
END $$;

-- statement --
REVOKE ALL ON FUNCTION public.visit_service_totals(uuid,uuid[],uuid),public.visit_plan(uuid,timestamptz,jsonb,uuid),
 public.get_available_slots(uuid,date,jsonb,boolean,uuid),public.booking_visit_change_quote(uuid,jsonb,timestamptz),
 public.apply_customer_visit_change(uuid,jsonb,timestamptz,integer,text,text) FROM PUBLIC,anon,authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.visit_service_totals(uuid,uuid[],uuid),public.visit_plan(uuid,timestamptz,jsonb,uuid),
 public.get_available_slots(uuid,date,jsonb,boolean,uuid),public.booking_visit_change_quote(uuid,jsonb,timestamptz),
 public.apply_customer_visit_change(uuid,jsonb,timestamptz,integer,text,text) TO service_role;
