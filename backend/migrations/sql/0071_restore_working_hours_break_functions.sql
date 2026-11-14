-- Repair schema drift where Alembic history reached 0070 but the 0067
-- break helper and conflict function were missing or stale.
-- This is a forward-only function repair; it changes no rows or table shape.

SET LOCAL lock_timeout = '5s';
-- statement --

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