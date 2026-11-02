-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Payout proof. A payout can only move to 'paid' with a recorded payment: the bank or UPI reference,
-- the date and time it was paid, the method, the amount, and a proof file (screenshot or PDF) that
-- stays private in the database. Nothing here is ever edited or deleted: a mistake is fixed by a new
-- linked correction. Every reveal, payment, decline, correction and proof view is written to an
-- audit table. Additive: the only change to an existing table is one nullable snapshot column.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
-- What the platform held for the salon at the moment it asked (collected, commission, refunds,
-- available). The commission shown on a payout is therefore the one that applied then.
ALTER TABLE public.salon_payout_requests ADD COLUMN balance_snapshot jsonb;
-- statement --
CREATE TABLE public.payout_proofs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mime_type text NOT NULL CHECK (mime_type IN ('image/png', 'image/jpeg', 'image/webp', 'application/pdf')),
  size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 5242880),
  sha256 text NOT NULL CHECK (char_length(sha256) = 64),
  content bytea NOT NULL,
  uploaded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (octet_length(content) = size_bytes)
);
-- statement --
CREATE TABLE public.salon_payout_payments (
  payout_id uuid PRIMARY KEY REFERENCES public.salon_payout_requests(id) ON DELETE RESTRICT,
  reference text NOT NULL CHECK (char_length(btrim(reference)) BETWEEN 1 AND 100),
  method text NOT NULL CHECK (method IN ('upi', 'imps', 'neft', 'rtgs', 'other')),
  paid_at timestamptz NOT NULL,
  amount_paid_paise bigint NOT NULL CHECK (amount_paid_paise > 0),
  adjustment_reason text CHECK (adjustment_reason IS NULL OR char_length(btrim(adjustment_reason)) BETWEEN 3 AND 500),
  note text CHECK (note IS NULL OR char_length(note) <= 200),
  proof_id uuid NOT NULL REFERENCES public.payout_proofs(id) ON DELETE RESTRICT,
  paid_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
-- One reference, one payout: the same bank or UPI reference cannot be recorded twice.
CREATE UNIQUE INDEX salon_payout_payments_reference_key
  ON public.salon_payout_payments (lower(btrim(reference)));
-- statement --
CREATE INDEX salon_payout_payments_paid_at ON public.salon_payout_payments (paid_at DESC);
-- statement --
CREATE TABLE public.salon_payout_corrections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payout_id uuid NOT NULL REFERENCES public.salon_payout_requests(id) ON DELETE RESTRICT,
  delta_paise bigint NOT NULL CHECK (delta_paise <> 0),
  reason text NOT NULL CHECK (char_length(btrim(reason)) BETWEEN 3 AND 500),
  reference text NOT NULL CHECK (char_length(btrim(reference)) BETWEEN 1 AND 100),
  proof_id uuid NOT NULL REFERENCES public.payout_proofs(id) ON DELETE RESTRICT,
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
CREATE INDEX salon_payout_corrections_payout ON public.salon_payout_corrections (payout_id, created_at);
-- statement --
CREATE TABLE public.payout_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payout_id uuid NOT NULL REFERENCES public.salon_payout_requests(id) ON DELETE RESTRICT,
  action text NOT NULL CHECK (action IN ('reveal', 'pay', 'decline', 'correct', 'view_proof')),
  actor_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
CREATE INDEX payout_audit_payout ON public.payout_audit (payout_id, created_at);
-- statement --
-- Append-only. The one change allowed is a profile deletion blanking the actor column
-- (ON DELETE SET NULL performs that update); nothing else may change and nothing is deleted.
CREATE FUNCTION public.guard_payout_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  actors text[] := TG_ARGV;
  col text;
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'payout_records_are_never_deleted' USING ERRCODE = 'P0001';
  END IF;
  IF (to_jsonb(NEW) - actors) IS DISTINCT FROM (to_jsonb(OLD) - actors) THEN
    RAISE EXCEPTION 'payout_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  FOREACH col IN ARRAY actors LOOP
    IF (to_jsonb(NEW) -> col) IS DISTINCT FROM (to_jsonb(OLD) -> col)
       AND (to_jsonb(NEW) -> col) <> 'null'::jsonb THEN
      RAISE EXCEPTION 'payout_records_are_append_only' USING ERRCODE = 'P0001';
    END IF;
  END LOOP;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER payout_proofs_guard BEFORE UPDATE OR DELETE ON public.payout_proofs
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_append_only('uploaded_by');
-- statement --
CREATE TRIGGER salon_payout_payments_guard BEFORE UPDATE OR DELETE ON public.salon_payout_payments
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_append_only('paid_by');
-- statement --
CREATE TRIGGER salon_payout_corrections_guard BEFORE UPDATE OR DELETE ON public.salon_payout_corrections
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_append_only('created_by');
-- statement --
CREATE TRIGGER payout_audit_guard BEFORE UPDATE OR DELETE ON public.payout_audit
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_append_only('actor_id');
-- statement --
CREATE TRIGGER payout_proofs_no_truncate BEFORE TRUNCATE ON public.payout_proofs
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_append_only();
-- statement --
CREATE TRIGGER salon_payout_payments_no_truncate BEFORE TRUNCATE ON public.salon_payout_payments
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_append_only();
-- statement --
CREATE TRIGGER salon_payout_corrections_no_truncate BEFORE TRUNCATE ON public.salon_payout_corrections
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_append_only();
-- statement --
CREATE TRIGGER payout_audit_no_truncate BEFORE TRUNCATE ON public.payout_audit
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_payout_append_only();
-- statement --
-- A request can only become 'paid' once its payment (and proof) is recorded with the same reference.
-- Same body as 0053's guard, plus that one rule.
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
  ELSIF NEW.status = 'paid' THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.salon_payout_payments p
      WHERE p.payout_id = NEW.id AND p.reference = NEW.reference
    ) THEN
      RAISE EXCEPTION 'payout_paid_needs_recorded_payment' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
ALTER TABLE public.payout_proofs ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_payout_payments ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_payout_corrections ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.payout_audit ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes.
REVOKE ALL ON public.payout_proofs, public.salon_payout_payments, public.salon_payout_corrections,
  public.payout_audit FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.payout_proofs, public.salon_payout_payments, public.salon_payout_corrections,
  public.payout_audit TO postgres, service_role;
-- statement --
-- TRUNCATE skips row triggers, so the guarantee needs it taken away.
REVOKE TRUNCATE ON public.payout_proofs, public.salon_payout_payments, public.salon_payout_corrections,
  public.payout_audit FROM service_role;
