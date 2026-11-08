-- Prepared only. Explicit reviewed migration, never API startup.
-- Payout proof retention after an owner deletes their account.
-- Kept (platform accounting records): amounts, dates, references, methods, audit trail.
-- Removed after the retention window: the proof file itself (a screenshot or PDF that can show the
-- owner's name and bank account). The file is replaced by one placeholder byte and stamped redacted_at.
-- No other change to a proof row is allowed: the table stays append-only for everything else.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
ALTER TABLE public.payout_proofs ADD COLUMN redacted_at timestamptz;
-- statement --
CREATE FUNCTION public.guard_payout_proof_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  skipped text[] := ARRAY['content', 'size_bytes', 'redacted_at', 'uploaded_by'];
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'payout_records_are_never_deleted' USING ERRCODE = 'P0001';
  END IF;
  -- The one sanctioned change: blank the file, once, and say so.
  IF OLD.redacted_at IS NULL AND NEW.redacted_at IS NOT NULL
     AND NEW.content = '\x00'::bytea AND NEW.size_bytes = 1
     AND (to_jsonb(NEW) - skipped) IS NOT DISTINCT FROM (to_jsonb(OLD) - skipped) THEN
    RETURN NEW;
  END IF;
  -- Otherwise only a profile deletion blanking uploaded_by.
  IF (to_jsonb(NEW) - 'uploaded_by') IS DISTINCT FROM (to_jsonb(OLD) - 'uploaded_by')
     OR ((to_jsonb(NEW) -> 'uploaded_by') IS DISTINCT FROM (to_jsonb(OLD) -> 'uploaded_by')
         AND (to_jsonb(NEW) -> 'uploaded_by') <> 'null'::jsonb) THEN
    RAISE EXCEPTION 'payout_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  RETURN NEW;
END $$;
-- statement --
DROP TRIGGER payout_proofs_guard ON public.payout_proofs;
-- statement --
CREATE TRIGGER payout_proofs_guard BEFORE UPDATE OR DELETE ON public.payout_proofs
  FOR EACH ROW EXECUTE FUNCTION public.guard_payout_proof_append_only();
-- statement --
-- Redacts the proof files of salons whose owner deleted their account more than p_months ago.
-- Returns how many files were removed. Safe to run repeatedly.
CREATE FUNCTION public.redact_expired_payout_proofs(p_months integer) RETURNS integer
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  removed integer;
BEGIN
  IF p_months IS NULL OR p_months < 1 THEN
    RAISE EXCEPTION 'retention_months_must_be_positive' USING ERRCODE = 'P0001';
  END IF;
  WITH expired AS (
    SELECT pp.proof_id AS id
    FROM public.salon_payout_payments pp
    JOIN public.salon_payout_requests r ON r.id = pp.payout_id
    UNION
    SELECT c.proof_id
    FROM public.salon_payout_corrections c
    JOIN public.salon_payout_requests r ON r.id = c.payout_id
  ), due AS (
    SELECT e.id FROM expired e
    WHERE NOT EXISTS (
      -- A proof is only removed when every salon that uses it was closed by an owner deletion long enough ago.
      SELECT 1 FROM (
        SELECT r.salon_id FROM public.salon_payout_payments pp
          JOIN public.salon_payout_requests r ON r.id = pp.payout_id WHERE pp.proof_id = e.id
        UNION
        SELECT r.salon_id FROM public.salon_payout_corrections c
          JOIN public.salon_payout_requests r ON r.id = c.payout_id WHERE c.proof_id = e.id
      ) s
      WHERE NOT EXISTS (
        SELECT 1 FROM public.account_deletion_requests d
        WHERE d.salon_id = s.salon_id AND d.role = 'owner' AND d.status = 'completed'
          AND d.completed_at < now() - make_interval(months => p_months)
      )
    )
  )
  UPDATE public.payout_proofs pf
  SET content = '\x00'::bytea, size_bytes = 1, redacted_at = now()
  FROM due
  WHERE pf.id = due.id AND pf.redacted_at IS NULL;
  GET DIAGNOSTICS removed = ROW_COUNT;
  RETURN removed;
END $$;
