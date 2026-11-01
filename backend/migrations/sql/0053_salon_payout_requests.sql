-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Owner wallet payout requests: the owner asks for money to be paid out on a day; the platform admin
-- pays it by hand and records the bank or UPI reference. Additive: no existing table changes.
-- Money is integer paise. The wallet balance is NOT stored: it is derived from the payment ledger
-- minus these requests, so there is no second ledger to drift out of step.
-- A request is born 'requested' and moves exactly once to 'paid', 'rejected' or 'cancelled'. After
-- that it is frozen. Rows are never deleted.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
CREATE TABLE public.salon_payout_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE RESTRICT,
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  -- The salon-local day the owner asked to be paid on. The platform credits within 24 hours of it.
  scheduled_for date NOT NULL,
  status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested','paid','rejected','cancelled')),
  -- Entered by the admin when paying: the bank or UPI transaction reference the owner can match.
  reference text CHECK (reference IS NULL OR char_length(btrim(reference)) BETWEEN 1 AND 100),
  reject_reason text CHECK (reject_reason IS NULL OR char_length(btrim(reject_reason)) BETWEEN 3 AND 500),
  requested_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  processed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  cancelled_at timestamptz,
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 200),
  request_hash text NOT NULL CHECK (char_length(request_hash) = 64),
  CHECK ((status = 'paid') = (reference IS NOT NULL)),
  CHECK ((status = 'rejected') = (reject_reason IS NOT NULL)),
  CHECK ((status IN ('paid','rejected')) = (processed_at IS NOT NULL)),
  CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),
  UNIQUE (salon_id, idempotency_key)
);
-- statement --
CREATE INDEX salon_payout_requests_salon_created ON public.salon_payout_requests (salon_id, created_at DESC, id DESC);
-- statement --
-- The admin queue: what is still waiting, soonest day first.
CREATE INDEX salon_payout_requests_queue ON public.salon_payout_requests (scheduled_for, created_at, id)
  WHERE status = 'requested';
-- statement --
-- Frozen except for the one move out of 'requested'. A profile deletion may blank requested_by and
-- processed_by (ON DELETE SET NULL performs that update); nothing else may change after the move.
CREATE FUNCTION public.guard_payout_request() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  mutable constant text[] = ARRAY['status','reference','reject_reason','processed_by','processed_at','cancelled_at','requested_by'];
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'payout_requests_are_never_deleted' USING ERRCODE = 'P0001';
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'requested' THEN
      RAISE EXCEPTION 'payout_request_must_start_requested' USING ERRCODE = 'P0001';
    END IF;
    RETURN NEW;
  END IF;
  IF (to_jsonb(NEW) - mutable) IS DISTINCT FROM (to_jsonb(OLD) - mutable) THEN
    RAISE EXCEPTION 'payout_request_fields_are_frozen' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.requested_by IS DISTINCT FROM OLD.requested_by AND NEW.requested_by IS NOT NULL THEN
    RAISE EXCEPTION 'payout_request_fields_are_frozen' USING ERRCODE = 'P0001';
  END IF;
  IF OLD.status <> 'requested' THEN
    -- Finished: only the actor columns may be blanked.
    IF NEW.status IS DISTINCT FROM OLD.status OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.reject_reason IS DISTINCT FROM OLD.reject_reason
       OR NEW.processed_at IS DISTINCT FROM OLD.processed_at
       OR NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at
       OR (NEW.processed_by IS DISTINCT FROM OLD.processed_by AND NEW.processed_by IS NOT NULL) THEN
      RAISE EXCEPTION 'payout_request_already_finished' USING ERRCODE = 'P0001';
    END IF;
  ELSIF NEW.status = 'requested' THEN
    -- Still waiting: nothing but requested_by may change.
    IF NEW.reference IS NOT NULL OR NEW.reject_reason IS NOT NULL OR NEW.processed_at IS NOT NULL
       OR NEW.cancelled_at IS NOT NULL OR NEW.processed_by IS NOT NULL THEN
      RAISE EXCEPTION 'payout_request_fields_are_frozen' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_payout_requests_guard BEFORE INSERT OR UPDATE OR DELETE ON public.salon_payout_requests
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_request();
-- statement --
CREATE TRIGGER salon_payout_requests_no_truncate BEFORE TRUNCATE ON public.salon_payout_requests
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_request();
-- statement --
ALTER TABLE public.salon_payout_requests ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes.
REVOKE ALL ON public.salon_payout_requests FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.salon_payout_requests TO postgres, service_role;
-- statement --
-- TRUNCATE skips row triggers, so the guarantee needs it taken away.
REVOKE TRUNCATE ON public.salon_payout_requests FROM service_role;
