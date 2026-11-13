-- statement --
SET LOCAL lock_timeout = '5s';
-- statement --
CREATE TABLE IF NOT EXISTS public.booking_no_show_warnings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE CASCADE,
  staff_id uuid REFERENCES public.staff(id) ON DELETE SET NULL,
  warned_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  grace_minutes smallint NOT NULL CHECK (grace_minutes IN (5, 10, 15)),
  warned_at timestamptz NOT NULL DEFAULT now(),
  deadline_at timestamptz NOT NULL,
  customer_response text CHECK (customer_response IN ('on_the_way', 'not_coming')),
  response_reason_code text,
  response_reason_text text,
  responded_at timestamptz,
  resolved_at timestamptz,
  resolution text CHECK (resolution IN ('arrived', 'no_show', 'customer_cancelled', 'withdrawn')),
  CHECK (deadline_at > warned_at),
  CHECK ((resolved_at IS NULL) = (resolution IS NULL))
);
-- statement --
-- One open warning per booking.
CREATE UNIQUE INDEX IF NOT EXISTS booking_no_show_warnings_one_open
  ON public.booking_no_show_warnings (booking_id) WHERE resolved_at IS NULL;
-- statement --
-- Worker lookup: warnings that ran out with no customer reply.
CREATE INDEX IF NOT EXISTS booking_no_show_warnings_due
  ON public.booking_no_show_warnings (deadline_at)
  WHERE resolved_at IS NULL AND customer_response IS NULL;
-- statement --
CREATE INDEX IF NOT EXISTS booking_no_show_warnings_salon_open
  ON public.booking_no_show_warnings (salon_id) WHERE resolved_at IS NULL;
-- statement --
ALTER TABLE public.booking_no_show_warnings ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.booking_no_show_warnings FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.booking_no_show_warnings TO postgres, service_role;
-- statement --
REVOKE TRUNCATE ON public.booking_no_show_warnings FROM service_role;
-- statement --
-- A no-show is allowed ten minutes after the start (existing rule) or once a salon warning has run out.
CREATE OR REPLACE FUNCTION public.guard_no_show_attendance()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND (NEW.status = 'no_show'
          OR (NEW.status = 'cancelled' AND NEW.cancellation_reason LIKE 'Customer no-show%')) THEN
    IF OLD.status = 'checked_in' THEN
      RAISE EXCEPTION 'no_show_after_check_in' USING ERRCODE = '23514';
    END IF;
    IF statement_timestamp() < NEW.start_datetime + interval '10 minutes'
       AND NOT EXISTS (
         SELECT 1 FROM public.booking_no_show_warnings w
         WHERE w.booking_id = NEW.id
           AND w.resolved_at IS NULL
           AND w.deadline_at <= statement_timestamp()
       ) THEN
      RAISE EXCEPTION 'no_show_grace_period' USING ERRCODE = '23514';
    END IF;
    IF NEW.cancellation_reason IS NULL OR NEW.cancellation_reason !~ '[^[:space:]]' THEN
      RAISE EXCEPTION 'no_show_reason_required' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
