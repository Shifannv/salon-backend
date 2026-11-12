-- Prepared only. Explicit reviewed migration, never API startup. Not applied to staging or production.
-- Automatic payout through a payout provider (Cashfree Payouts today). The super admin may pay a payout request either
-- by hand (0057: reference + proof) or by sending the transfer through the provider. Money safety lives here, not
-- only in Python:
--   * one transfer per request may be 'pending' or 'success' at any time (partial unique index);
--   * while a transfer is pending or successful, the owner cannot cancel, the admin cannot reject, and
--     nobody can mark the request paid by hand;
--   * a request becomes 'paid' by transfer only after that transfer reached 'success';
--   * a payment sent by Cashfree has no proof file: the provider record (transfer id, UTR) replaces it.
-- Additive. Existing rows keep source 'manual' and their proof.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
-- A provider-sent payment has no proof file; a manual one still must have one.
ALTER TABLE public.salon_payout_payments ALTER COLUMN proof_id DROP NOT NULL;
-- statement --
ALTER TABLE public.salon_payout_payments
  ADD COLUMN source text NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'transfer'));
-- statement --
ALTER TABLE public.salon_payout_payments ADD COLUMN transfer_id text;
-- statement --
ALTER TABLE public.salon_payout_payments ADD CONSTRAINT salon_payout_payments_source_proof CHECK (
  (source = 'manual' AND proof_id IS NOT NULL AND transfer_id IS NULL)
  OR (source = 'transfer' AND transfer_id IS NOT NULL)
);
-- statement --
CREATE TABLE public.salon_payout_transfers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id uuid NOT NULL REFERENCES public.salon_payout_requests(id) ON DELETE RESTRICT,
  -- Our id at the provider. Deterministic (request + attempt), so a lost reply is looked up, not re-sent.
  transfer_id text NOT NULL CHECK (transfer_id ~ '^[A-Za-z0-9_-]{1,40}$'),
  beneficiary_id text NOT NULL CHECK (beneficiary_id ~ '^[A-Za-z0-9_-]{1,50}$'),
  mode text NOT NULL CHECK (mode IN ('upi', 'imps')),
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'reversed')),
  provider_status text CHECK (provider_status IS NULL OR char_length(provider_status) <= 60),
  cf_transfer_id text CHECK (cf_transfer_id IS NULL OR char_length(cf_transfer_id) <= 60),
  utr text CHECK (utr IS NULL OR char_length(utr) <= 100),
  failure_reason text CHECK (failure_reason IS NULL OR char_length(failure_reason) <= 200),
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
CREATE UNIQUE INDEX salon_payout_transfers_transfer_id_key ON public.salon_payout_transfers (transfer_id);
-- statement --
-- The core invariant: never two live transfers for one request, so the money cannot be sent twice.
CREATE UNIQUE INDEX salon_payout_transfers_one_live_per_request
  ON public.salon_payout_transfers (request_id) WHERE status IN ('pending', 'success');
-- statement --
CREATE INDEX salon_payout_transfers_request ON public.salon_payout_transfers (request_id, created_at);
-- statement --
-- A transfer is created only for a waiting request and for exactly its amount. After that only the
-- provider-reported fields move, and only along pending -> success|failed, success -> reversed and
-- failed -> success (the provider is the source of truth: a late success after a recorded failure is real money).
-- Nothing is deleted. A profile deletion may blank created_by.
CREATE FUNCTION public.guard_payout_transfer() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  mutable constant text[] = ARRAY['status', 'provider_status', 'cf_transfer_id', 'utr', 'failure_reason', 'updated_at', 'created_by'];
  req record;
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'payout_records_are_never_deleted' USING ERRCODE = 'P0001';
  END IF;
  IF TG_OP = 'INSERT' THEN
    -- FOR SHARE: wait for any cancel / decline / payment of this request that is still uncommitted, then
    -- see its result. Without it two transactions could each miss the other and leave a closed request
    -- with a live transfer.
    SELECT status, amount_paise INTO req FROM public.salon_payout_requests WHERE id = NEW.request_id FOR SHARE;
    IF req.status IS DISTINCT FROM 'requested' THEN
      RAISE EXCEPTION 'payout_transfer_needs_waiting_request' USING ERRCODE = 'P0001';
    END IF;
    IF req.amount_paise <> NEW.amount_paise THEN
      RAISE EXCEPTION 'payout_transfer_amount_must_match_request' USING ERRCODE = 'P0001';
    END IF;
    IF NEW.status <> 'pending' THEN
      RAISE EXCEPTION 'payout_transfer_must_start_pending' USING ERRCODE = 'P0001';
    END IF;
    RETURN NEW;
  END IF;
  IF (to_jsonb(NEW) - mutable) IS DISTINCT FROM (to_jsonb(OLD) - mutable) THEN
    RAISE EXCEPTION 'payout_transfer_fields_are_frozen' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.created_by IS DISTINCT FROM OLD.created_by AND NEW.created_by IS NOT NULL THEN
    RAISE EXCEPTION 'payout_transfer_fields_are_frozen' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
       (OLD.status = 'pending' AND NEW.status IN ('success', 'failed'))
    OR (OLD.status = 'success' AND NEW.status = 'reversed')
    OR (OLD.status = 'failed' AND NEW.status = 'success')
  ) THEN
    RAISE EXCEPTION 'payout_transfer_status_is_final' USING ERRCODE = 'P0001';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_payout_transfers_guard BEFORE INSERT OR UPDATE OR DELETE ON public.salon_payout_transfers
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_transfer();
-- statement --
CREATE TRIGGER salon_payout_transfers_no_truncate BEFORE TRUNCATE ON public.salon_payout_transfers
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_transfer();
-- statement --
ALTER TABLE public.salon_payout_transfers ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes.
REVOKE ALL ON public.salon_payout_transfers FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.salon_payout_transfers TO postgres, service_role;
-- statement --
REVOKE TRUNCATE ON public.salon_payout_transfers FROM service_role;
-- statement --
-- Provider events have no admin: payout_audit.actor_id is already nullable.
ALTER TABLE public.payout_audit DROP CONSTRAINT payout_audit_action_check;
-- statement --
ALTER TABLE public.payout_audit ADD CONSTRAINT payout_audit_action_check CHECK (action IN (
  'reveal', 'pay', 'decline', 'correct', 'view_proof',
  'send_transfer', 'transfer_success', 'transfer_failed', 'transfer_reversed', 'transfer_conflict'));
-- statement --
-- Same body as 0057's guard, plus the transfer rules described at the top of this file.
CREATE OR REPLACE FUNCTION public.guard_payout_request() RETURNS trigger
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
    IF NEW.status IS DISTINCT FROM OLD.status OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.reject_reason IS DISTINCT FROM OLD.reject_reason
       OR NEW.processed_at IS DISTINCT FROM OLD.processed_at
       OR NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at
       OR (NEW.processed_by IS DISTINCT FROM OLD.processed_by AND NEW.processed_by IS NOT NULL) THEN
      RAISE EXCEPTION 'payout_request_already_finished' USING ERRCODE = 'P0001';
    END IF;
  ELSIF NEW.status = 'requested' THEN
    IF NEW.reference IS NOT NULL OR NEW.reject_reason IS NOT NULL OR NEW.processed_at IS NOT NULL
       OR NEW.cancelled_at IS NOT NULL OR NEW.processed_by IS NOT NULL THEN
      RAISE EXCEPTION 'payout_request_fields_are_frozen' USING ERRCODE = 'P0001';
    END IF;
  ELSIF NEW.status IN ('cancelled', 'rejected') THEN
    -- Money may already be on its way: neither the owner nor the admin can take the request back.
    IF EXISTS (SELECT 1 FROM public.salon_payout_transfers t
               WHERE t.request_id = NEW.id AND t.status IN ('pending', 'success')) THEN
      RAISE EXCEPTION 'payout_transfer_in_progress' USING ERRCODE = 'P0001';
    END IF;
  ELSIF NEW.status = 'paid' THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.salon_payout_payments p
      WHERE p.payout_id = NEW.id AND p.reference = NEW.reference
    ) THEN
      RAISE EXCEPTION 'payout_paid_needs_recorded_payment' USING ERRCODE = 'P0001';
    END IF;
    -- A provider-sent payment counts only once its transfer succeeded.
    IF EXISTS (
      SELECT 1 FROM public.salon_payout_payments p
      WHERE p.payout_id = NEW.id AND p.source = 'transfer'
        AND NOT EXISTS (SELECT 1 FROM public.salon_payout_transfers t
                        WHERE t.request_id = NEW.id AND t.transfer_id = p.transfer_id AND t.status = 'success')
    ) THEN
      RAISE EXCEPTION 'payout_transfer_not_successful' USING ERRCODE = 'P0001';
    END IF;
    -- A by-hand payment is refused while a transfer is live: it would pay the same money twice.
    IF EXISTS (SELECT 1 FROM public.salon_payout_payments p WHERE p.payout_id = NEW.id AND p.source = 'manual')
       AND EXISTS (SELECT 1 FROM public.salon_payout_transfers t
                   WHERE t.request_id = NEW.id AND t.status IN ('pending', 'success')) THEN
      RAISE EXCEPTION 'payout_transfer_in_progress' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
-- Admin salon erasure must remove the new table before the requests it references (RESTRICT).
-- Same technique as 0061: patch the current definition and refuse any unexpected prior body.
DO $$ DECLARE definition text; marker text;
BEGIN
  SELECT pg_get_functiondef('public.erase_salon(uuid)'::regprocedure) INTO definition;
  FOREACH marker IN ARRAY ARRAY[
    'DELETE FROM public.salon_payout_payments WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);',
    '''payout_audit'', ''salon_payout_payments'''
  ] LOOP
    IF (length(definition)-length(replace(definition,marker,'')))/length(marker)<>1 THEN
      RAISE EXCEPTION 'salon_erasure_definition_mismatch';
    END IF;
  END LOOP;
  definition:=replace(definition,
    'DELETE FROM public.salon_payout_payments WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);',
    'DELETE FROM public.salon_payout_transfers WHERE request_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);'
    || E'\n  DELETE FROM public.salon_payout_payments WHERE payout_id IN (SELECT id FROM public.salon_payout_requests WHERE salon_id = p_salon);');
  definition:=replace(definition,'''payout_audit'', ''salon_payout_payments''',
    '''payout_audit'', ''salon_payout_transfers'', ''salon_payout_payments''');
  EXECUTE definition;
END $$;
