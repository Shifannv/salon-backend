-- Prepared only. Review before applying. No production migration is authorized.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '60s';
-- statement --
CREATE TABLE public.salon_service_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE RESTRICT,
  name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 80),
  is_active boolean NOT NULL DEFAULT true,
  UNIQUE (id, salon_id)
);
-- statement --
CREATE UNIQUE INDEX salon_service_category_name ON public.salon_service_categories(salon_id, lower(trim(name)));
-- statement --
ALTER TABLE public.salon_service_categories ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.salon_service_categories FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE ON public.salon_service_categories TO service_role;
-- statement --
ALTER TABLE public.services ADD COLUMN menu_category_id uuid,
  ADD COLUMN selection_group text DEFAULT '__category__' CHECK (selection_group IS NULL OR length(selection_group) BETWEEN 1 AND 80);
-- statement --
INSERT INTO public.salon_service_categories(salon_id,name)
SELECT DISTINCT ON (sv.salon_id, lower(trim(coalesce(nullif(sv.category_name,''),nullif(sv.subcategory_name,''),ss.name,sc.name,'Other'))))
  sv.salon_id, trim(coalesce(nullif(sv.category_name,''),nullif(sv.subcategory_name,''),ss.name,sc.name,'Other'))
FROM public.services sv LEFT JOIN public.service_subcategories ss ON ss.id=sv.subcategory_id
LEFT JOIN public.service_categories sc ON sc.id=ss.category_id;
-- statement --
WITH labels AS (
  SELECT sv.id,sv.salon_id,
    trim(coalesce(nullif(sv.category_name,''),nullif(sv.subcategory_name,''),ss.name,sc.name,'Other')) AS name
  FROM public.services sv LEFT JOIN public.service_subcategories ss ON ss.id=sv.subcategory_id
  LEFT JOIN public.service_categories sc ON sc.id=ss.category_id
)
UPDATE public.services sv SET menu_category_id=mc.id
FROM labels l JOIN public.salon_service_categories mc
  ON mc.salon_id=l.salon_id AND lower(trim(mc.name))=lower(trim(l.name))
WHERE sv.id=l.id;
-- statement --
ALTER TABLE public.services ADD CONSTRAINT services_menu_category_salon_fk
  FOREIGN KEY (menu_category_id,salon_id) REFERENCES public.salon_service_categories(id,salon_id);
-- statement --
CREATE INDEX services_menu_category ON public.services(menu_category_id);
-- statement --
CREATE FUNCTION public.assign_menu_category() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE label text;
BEGIN
  IF TG_OP='INSERT' OR NEW.category_name IS DISTINCT FROM OLD.category_name
     OR NEW.subcategory_name IS DISTINCT FROM OLD.subcategory_name OR NEW.subcategory_id IS DISTINCT FROM OLD.subcategory_id THEN
    SELECT trim(coalesce(nullif(NEW.category_name,''),nullif(NEW.subcategory_name,''),ss.name,sc.name,'Other')) INTO label
    FROM (SELECT 1) seed LEFT JOIN public.service_subcategories ss ON ss.id=NEW.subcategory_id
    LEFT JOIN public.service_categories sc ON sc.id=ss.category_id;
    INSERT INTO public.salon_service_categories(salon_id,name) VALUES(NEW.salon_id,label)
      ON CONFLICT (salon_id,lower(trim(name))) DO UPDATE SET is_active=true
      RETURNING id INTO NEW.menu_category_id;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER services_menu_category BEFORE INSERT OR UPDATE ON public.services
FOR EACH ROW EXECUTE FUNCTION public.assign_menu_category();
-- statement --
ALTER TABLE public.bookings ADD COLUMN is_multi_staff boolean NOT NULL DEFAULT false,
  ADD COLUMN itinerary jsonb NOT NULL DEFAULT '[]'::jsonb;
-- statement --
CREATE TABLE public.booking_segments (
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE RESTRICT,
  ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 29),
  staff_id uuid NOT NULL REFERENCES public.staff(id) ON DELETE RESTRICT,
  service_ids uuid[] NOT NULL CHECK(cardinality(service_ids) BETWEEN 1 AND 30),
  start_datetime timestamptz NOT NULL,
  end_datetime timestamptz NOT NULL CHECK(end_datetime>start_datetime),
  is_active boolean NOT NULL DEFAULT true,
  PRIMARY KEY(booking_id,ordinal),
  EXCLUDE USING gist(staff_id WITH =,tstzrange(start_datetime,end_datetime) WITH &&) WHERE(is_active)
);
-- statement --
CREATE INDEX booking_segments_staff ON public.booking_segments(staff_id);
-- statement --
ALTER TABLE public.booking_segments ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.booking_segments FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE ON public.booking_segments TO service_role;
-- statement --
ALTER TABLE public.bookings DROP CONSTRAINT bookings_no_overlap;
-- statement --
ALTER TABLE public.bookings ADD CONSTRAINT bookings_no_overlap EXCLUDE USING gist
  (staff_id WITH =,tstzrange(start_datetime,end_datetime) WITH &&)
  WHERE(status IN ('pending','confirmed','checked_in') AND NOT is_multi_staff);
-- statement --
CREATE VIEW public.booking_staff_reservations WITH(security_invoker=true) AS
SELECT id AS booking_id,staff_id,start_datetime,end_datetime,status FROM public.bookings WHERE NOT is_multi_staff
UNION ALL
SELECT b.id,s.staff_id,s.start_datetime,s.end_datetime,b.status FROM public.booking_segments s
JOIN public.bookings b ON b.id=s.booking_id WHERE b.is_multi_staff AND s.is_active;
-- statement --
REVOKE ALL ON public.booking_staff_reservations FROM PUBLIC, anon, authenticated;
-- statement --
GRANT SELECT ON public.booking_staff_reservations TO service_role;
-- statement --
CREATE FUNCTION public.guard_visit_reservation() RETURNS trigger
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
    IF TG_OP='UPDATE' AND OLD.is_multi_staff AND
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
    IF TG_OP='UPDATE' AND (to_jsonb(NEW)-'is_active') IS DISTINCT FROM (to_jsonb(OLD)-'is_active') THEN
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
CREATE TRIGGER aaa_visit_guard BEFORE INSERT OR UPDATE ON public.bookings
FOR EACH ROW EXECUTE FUNCTION public.guard_visit_reservation();
-- statement --
CREATE TRIGGER visit_segment_guard BEFORE INSERT OR UPDATE ON public.booking_segments
FOR EACH ROW EXECUTE FUNCTION public.guard_visit_reservation();
-- statement --
CREATE FUNCTION public.sync_visit_status() RETURNS trigger LANGUAGE plpgsql
SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NEW.is_multi_staff AND (NEW.status IN ('pending','confirmed','checked_in')) IS DISTINCT FROM (OLD.status IN ('pending','confirmed','checked_in')) THEN
    UPDATE public.booking_segments SET is_active=NEW.status IN ('pending','confirmed','checked_in') WHERE booking_id=NEW.id;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER visit_status AFTER UPDATE ON public.bookings FOR EACH ROW EXECUTE FUNCTION public.sync_visit_status();
-- statement --
-- Patch the current slot authority to include each visit segment. No client/Python slot arithmetic.
DO $$ DECLARE definition text; signature text;
BEGIN
  FOREACH signature IN ARRAY ARRAY[
    'public.get_available_slots(uuid,date,integer)',
    'public.get_available_slots(uuid,date,integer,uuid)'
  ] LOOP
    SELECT pg_get_functiondef(signature::regprocedure) INTO definition;
    IF (length(definition)-length(replace(definition,'from bookings b','')))
       /length('from bookings b') <> 1 THEN
      RAISE EXCEPTION 'availability_definition_mismatch';
    END IF;
    definition:=replace(definition,'from bookings b',
      'from (select booking_id as id,staff_id,start_datetime,end_datetime,status from public.booking_staff_reservations) b');
    EXECUTE definition;
    IF position('public.booking_staff_reservations' IN pg_get_functiondef(signature::regprocedure))=0 THEN
      RAISE EXCEPTION 'availability_definition_mismatch';
    END IF;
  END LOOP;
END $$;
-- statement --
CREATE FUNCTION public.visit_plan(p_salon uuid,p_start timestamptz,p_segments jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE part jsonb; sid uuid; ids uuid[]; cursor_at timestamptz:=p_start; ends timestamptz;
  duration integer; amount numeric; total numeric:=0; result jsonb:='[]'; n integer:=0;
  seen uuid[]:='{}'; groups text[]:='{}'; grp text; tz text; hours jsonb; local_day date; dow text;
BEGIN
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
    SELECT sum(coalesce(ss.duration_minutes,sv.duration_minutes)),sum(coalesce(ss.price_override,sv.price))
      INTO duration,amount FROM public.services sv JOIN public.staff_services ss ON ss.service_id=sv.id
      WHERE sv.id=ANY(ids) AND ss.staff_id=sid AND ss.is_active;
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
      OR EXISTS(SELECT 1 FROM public.booking_staff_reservations r WHERE r.staff_id=sid
        AND r.status IN ('pending','confirmed','checked_in') AND tstzrange(r.start_datetime,r.end_datetime)&&tstzrange(cursor_at,ends))
    THEN RETURN NULL; END IF;
    result:=result||jsonb_build_array(jsonb_build_object('ordinal',n,'staff_id',sid,'service_ids',ids,
      'slot_start',cursor_at,'slot_end',ends,'price',amount,'duration_minutes',duration));
    n:=n+1;cursor_at:=ends;total:=total+amount;
  END LOOP;
  RETURN jsonb_build_object('segments',result,'slot_start',p_start,'slot_end',cursor_at,'total_price',total);
END $$;
-- statement --
CREATE FUNCTION public.get_available_slots(p_salon uuid,p_date date,p_segments jsonb,p_consecutive boolean)
RETURNS TABLE(slot_start timestamptz,slot_end timestamptz,segments jsonb,total_price numeric)
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE first_part jsonb:=p_segments->0; duration integer; candidate record; plan jsonb;
BEGIN
  SELECT sum(coalesce(ss.duration_minutes,sv.duration_minutes)) INTO duration
  FROM public.services sv JOIN public.staff_services ss ON ss.service_id=sv.id
  WHERE ss.staff_id=(first_part->>'staff_id')::uuid AND ss.is_active AND sv.is_active
    AND sv.id IN(SELECT value::uuid FROM jsonb_array_elements_text(first_part->'service_ids'));
  IF duration IS NULL OR duration<=0 THEN RETURN; END IF;
  FOR candidate IN SELECT * FROM public.get_available_slots((first_part->>'staff_id')::uuid,p_date,duration) LOOP
    plan:=public.visit_plan(p_salon,candidate.slot_start,p_segments);
    IF plan IS NOT NULL THEN
      slot_start:=candidate.slot_start;slot_end:=(plan->>'slot_end')::timestamptz;
      segments:=plan->'segments';total_price:=(plan->>'total_price')::numeric;RETURN NEXT;
    END IF;
  END LOOP;
END $$;
-- statement --
CREATE FUNCTION public.create_booking(p_salon uuid,p_segments jsonb,p_start timestamptz,p_name text,
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
  IF plan IS NULL THEN RAISE EXCEPTION 'Selected slot is no longer available'; END IF;
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
-- statement --
REVOKE ALL ON FUNCTION public.assign_menu_category(),public.guard_visit_reservation(),public.sync_visit_status(),
  public.visit_plan(uuid,timestamptz,jsonb),public.get_available_slots(uuid,date,jsonb,boolean),
  public.create_booking(uuid,jsonb,timestamptz,text,text,booking_source,text) FROM PUBLIC,anon,authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.visit_plan(uuid,timestamptz,jsonb),public.get_available_slots(uuid,date,jsonb,boolean),
  public.create_booking(uuid,jsonb,timestamptz,text,text,booking_source,text) TO service_role;

-- statement --
-- Enforce alternative-service rules for existing owner/walk-in/single-staff callers too.
CREATE FUNCTION public.guard_service_selection() RETURNS trigger LANGUAGE plpgsql
SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NEW.is_active AND EXISTS(
    SELECT 1 FROM public.booking_services bs JOIN public.services other ON other.id=bs.service_id
      JOIN public.services chosen ON chosen.id=NEW.service_id
    WHERE bs.booking_id=NEW.booking_id AND bs.service_id<>NEW.service_id AND bs.is_active
      AND chosen.selection_group IS NOT NULL AND other.selection_group IS NOT NULL
      AND CASE WHEN chosen.selection_group='__category__' THEN coalesce(chosen.menu_category_id::text,chosen.subcategory_id::text) ELSE coalesce(chosen.menu_category_id::text,chosen.subcategory_id::text)||':'||chosen.selection_group END
        = CASE WHEN other.selection_group='__category__' THEN coalesce(other.menu_category_id::text,other.subcategory_id::text) ELSE coalesce(other.menu_category_id::text,other.subcategory_id::text)||':'||other.selection_group END
  ) THEN RAISE EXCEPTION 'invalid_service_selection' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER booking_service_selection BEFORE INSERT ON public.booking_services FOR EACH ROW EXECUTE FUNCTION public.guard_service_selection();
-- statement --
REVOKE ALL ON FUNCTION public.guard_service_selection() FROM PUBLIC,anon,authenticated;

-- statement --
CREATE FUNCTION public.guard_visit_attribution() RETURNS trigger LANGUAGE plpgsql
SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF EXISTS(SELECT 1 FROM public.bookings WHERE id=NEW.booking_id AND is_multi_staff)
    AND NOT EXISTS(SELECT 1 FROM public.booking_segments WHERE booking_id=NEW.booking_id
      AND staff_id=NEW.staff_id AND NEW.service_id=ANY(service_ids)) THEN
    RAISE EXCEPTION 'visit_change_requires_full_itinerary' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER visit_attribution_guard BEFORE INSERT ON public.booking_service_staff
FOR EACH ROW EXECUTE FUNCTION public.guard_visit_attribution();
-- statement --
REVOKE ALL ON FUNCTION public.guard_visit_attribution() FROM PUBLIC,anon,authenticated;

-- statement --
-- Registry labels duplicate owner-entered catalog text, not financial evidence. Scrub
-- the new copy and custom selection labels during the existing verified owner erasure.
CREATE FUNCTION public.scrub_closed_menu_categories() RETURNS trigger LANGUAGE plpgsql
SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF current_setting('app.account_erasure',true)='on' AND NOT NEW.is_active AND NEW.name='Closed salon' THEN
    UPDATE public.services SET selection_group=NULL WHERE salon_id=NEW.id AND selection_group IS NOT NULL;
    UPDATE public.salon_service_categories SET name='Removed category '||id::text,is_active=false WHERE salon_id=NEW.id;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER closed_menu_categories AFTER UPDATE ON public.salons FOR EACH ROW EXECUTE FUNCTION public.scrub_closed_menu_categories();
-- statement --
REVOKE ALL ON FUNCTION public.scrub_closed_menu_categories() FROM PUBLIC,anon,authenticated;

-- statement --
-- Preserve the existing explicitly confirmed admin-erasure operation for the new children.
-- Refuse unexpected prior function bodies rather than silently leaving RESTRICT references behind.
DO $$ DECLARE definition text; marker text;
BEGIN
  SELECT pg_get_functiondef('public.erase_salon(uuid)'::regprocedure) INTO definition;
  FOREACH marker IN ARRAY ARRAY[
    'DELETE FROM public.bookings WHERE salon_id = p_salon;',
    'DELETE FROM public.staff WHERE salon_id = p_salon;',
    '''staff_services'', ''services'', ''staff'', ''salons'''
  ] LOOP
    IF (length(definition)-length(replace(definition,marker,'')))/length(marker)<>1 THEN
      RAISE EXCEPTION 'salon_erasure_definition_mismatch';
    END IF;
  END LOOP;
  definition:=replace(definition,'DELETE FROM public.bookings WHERE salon_id = p_salon;',
    'DELETE FROM public.booking_segments WHERE booking_id IN (SELECT id FROM public.bookings WHERE salon_id = p_salon);'
    || E'\n  DELETE FROM public.bookings WHERE salon_id = p_salon;');
  definition:=replace(definition,'DELETE FROM public.staff WHERE salon_id = p_salon;',
    'DELETE FROM public.salon_service_categories WHERE salon_id = p_salon;'
    || E'\n  DELETE FROM public.staff WHERE salon_id = p_salon;');
  definition:=replace(definition,'''staff_services'', ''services'', ''staff'', ''salons''',
    '''staff_services'', ''services'', ''salon_service_categories'', ''booking_segments'', ''staff'', ''salons''');
  EXECUTE definition;
END $$;
