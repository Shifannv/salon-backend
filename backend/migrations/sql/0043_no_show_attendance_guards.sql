-- Prepared only. No booking data is rewritten and no financial policy is activated.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
CREATE OR REPLACE FUNCTION public.guard_no_show_attendance()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND (NEW.status = 'no_show'
          OR (NEW.status = 'cancelled' AND NEW.cancellation_reason LIKE 'Customer no-show%')) THEN
    IF OLD.status = 'checked_in' THEN
      RAISE EXCEPTION 'no_show_after_check_in' USING ERRCODE = '23514';
    END IF;
    IF statement_timestamp() < NEW.start_datetime + interval '10 minutes' THEN
      RAISE EXCEPTION 'no_show_grace_period' USING ERRCODE = '23514';
    END IF;
    IF NEW.cancellation_reason IS NULL OR NEW.cancellation_reason !~ '[^[:space:]]' THEN
      RAISE EXCEPTION 'no_show_reason_required' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.guard_no_show_attendance() FROM PUBLIC, anon, authenticated;
-- statement --
DROP TRIGGER IF EXISTS booking_no_show_attendance_guard ON public.bookings;
-- statement --
CREATE TRIGGER booking_no_show_attendance_guard BEFORE UPDATE ON public.bookings
FOR EACH ROW EXECUTE FUNCTION public.guard_no_show_attendance();
