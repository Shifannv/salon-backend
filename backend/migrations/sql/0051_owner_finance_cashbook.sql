-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Owner finance cash book: expenses, audited cash adjustments and day-close records.
-- Additive: no existing table or column changes. Receipts, refunds and sales are READ from
-- booking_payments, payment_refunds and bookings; nothing is copied into a second ledger.
-- Money is integer paise. Every table is append-only: a correction is a new row.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
CREATE TABLE public.salon_expenses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE RESTRICT,
  entry_type text NOT NULL CHECK (entry_type IN ('expense','reversal')),
  reverses_id uuid REFERENCES public.salon_expenses(id) ON DELETE RESTRICT,
  category text NOT NULL CHECK (category IN ('supplies','rent','utilities','salary_advance','maintenance','other')),
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  payment_method text NOT NULL CHECK (payment_method IN ('cash','non_cash')),
  occurred_at timestamptz NOT NULL,
  note text CHECK (note IS NULL OR char_length(note) <= 500),
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 200),
  request_hash text NOT NULL CHECK (char_length(request_hash) = 64),
  CHECK ((entry_type = 'reversal') = (reverses_id IS NOT NULL)),
  UNIQUE (salon_id, idempotency_key),
  UNIQUE (reverses_id)
);
-- statement --
CREATE INDEX salon_expenses_salon_occurred ON public.salon_expenses (salon_id, occurred_at);
-- statement --
CREATE TABLE public.salon_cash_adjustments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE RESTRICT,
  direction text NOT NULL CHECK (direction IN ('in','out')),
  amount_paise bigint NOT NULL CHECK (amount_paise > 0),
  reason text NOT NULL CHECK (char_length(btrim(reason)) BETWEEN 3 AND 500),
  occurred_at timestamptz NOT NULL,
  reverses_id uuid REFERENCES public.salon_cash_adjustments(id) ON DELETE RESTRICT,
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 200),
  request_hash text NOT NULL CHECK (char_length(request_hash) = 64),
  UNIQUE (salon_id, idempotency_key),
  UNIQUE (reverses_id)
);
-- statement --
CREATE INDEX salon_cash_adjustments_salon_occurred ON public.salon_cash_adjustments (salon_id, occurred_at);
-- statement --
CREATE TABLE public.salon_day_closes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE RESTRICT,
  local_date date NOT NULL,
  revision integer NOT NULL CHECK (revision >= 1),
  opening_cash_paise bigint NOT NULL CHECK (opening_cash_paise >= 0),
  expected_cash_paise bigint NOT NULL,
  actual_cash_paise bigint NOT NULL CHECK (actual_cash_paise >= 0),
  difference_paise bigint GENERATED ALWAYS AS (actual_cash_paise - expected_cash_paise) STORED,
  difference_reason text,
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 200),
  request_hash text NOT NULL CHECK (char_length(request_hash) = 64),
  CHECK (actual_cash_paise = expected_cash_paise OR char_length(btrim(coalesce(difference_reason, ''))) >= 3),
  UNIQUE (salon_id, local_date, revision),
  UNIQUE (salon_id, idempotency_key)
);
-- statement --
-- Append-only. The only permitted UPDATEs are the two that account erasure needs:
--   1. created_by -> NULL (the profile is deleted; ON DELETE SET NULL performs this update), and
--   2. redacting free text (note, reason, difference_reason) while app.finance_redaction = 'on'.
-- Every other column is frozen, and DELETE is never allowed. difference_paise is excluded from the
-- comparison only because it is a stored generated column that PostgreSQL computes AFTER BEFORE
-- triggers run; it derives from actual_cash_paise and expected_cash_paise, which stay frozen.
CREATE FUNCTION public.guard_finance_append_only() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  free_text constant text[] = ARRAY['note','reason','difference_reason'];
  frozen_new jsonb;
  frozen_old jsonb;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'finance_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  frozen_new := to_jsonb(NEW) - 'created_by' - 'difference_paise' - free_text;
  frozen_old := to_jsonb(OLD) - 'created_by' - 'difference_paise' - free_text;
  IF frozen_new IS DISTINCT FROM frozen_old THEN
    RAISE EXCEPTION 'finance_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.created_by IS DISTINCT FROM OLD.created_by AND NEW.created_by IS NOT NULL THEN
    RAISE EXCEPTION 'finance_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  IF (to_jsonb(NEW) -> 'note' IS DISTINCT FROM to_jsonb(OLD) -> 'note'
      OR to_jsonb(NEW) -> 'reason' IS DISTINCT FROM to_jsonb(OLD) -> 'reason'
      OR to_jsonb(NEW) -> 'difference_reason' IS DISTINCT FROM to_jsonb(OLD) -> 'difference_reason')
     AND current_setting('app.finance_redaction', true) IS DISTINCT FROM 'on' THEN
    RAISE EXCEPTION 'finance_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_expenses_append_only BEFORE UPDATE OR DELETE ON public.salon_expenses
  FOR EACH ROW EXECUTE FUNCTION public.guard_finance_append_only();
-- statement --
CREATE TRIGGER salon_cash_adjustments_append_only BEFORE UPDATE OR DELETE ON public.salon_cash_adjustments
  FOR EACH ROW EXECUTE FUNCTION public.guard_finance_append_only();
-- statement --
CREATE TRIGGER salon_day_closes_append_only BEFORE UPDATE OR DELETE ON public.salon_day_closes
  FOR EACH ROW EXECUTE FUNCTION public.guard_finance_append_only();
-- statement --
-- A reversal mirrors exactly one earlier expense: same salon, category, amount and method.
CREATE FUNCTION public.guard_expense_reversal() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE original public.salon_expenses%ROWTYPE;
BEGIN
  IF NEW.entry_type = 'reversal' THEN
    SELECT * INTO original FROM public.salon_expenses WHERE id = NEW.reverses_id;
    IF NOT FOUND OR original.entry_type <> 'expense' OR original.salon_id <> NEW.salon_id
       OR original.category <> NEW.category OR original.amount_paise <> NEW.amount_paise
       OR original.payment_method <> NEW.payment_method THEN
      RAISE EXCEPTION 'expense_reversal_mismatch' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_expenses_reversal_mirror BEFORE INSERT ON public.salon_expenses
  FOR EACH ROW EXECUTE FUNCTION public.guard_expense_reversal();
-- statement --
-- A cash adjustment reversal is the opposite movement of the same amount in the same salon.
CREATE FUNCTION public.guard_cash_adjustment_reversal() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE original public.salon_cash_adjustments%ROWTYPE;
BEGIN
  IF NEW.reverses_id IS NOT NULL THEN
    SELECT * INTO original FROM public.salon_cash_adjustments WHERE id = NEW.reverses_id;
    IF NOT FOUND OR original.salon_id <> NEW.salon_id OR original.amount_paise <> NEW.amount_paise
       OR original.direction = NEW.direction THEN
      RAISE EXCEPTION 'cash_adjustment_reversal_mismatch' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_cash_adjustments_reversal_mirror BEFORE INSERT ON public.salon_cash_adjustments
  FOR EACH ROW EXECUTE FUNCTION public.guard_cash_adjustment_reversal();
-- statement --
-- Day-close revisions are sequential per salon and local date: no gaps, no overwrites.
CREATE FUNCTION public.guard_day_close_revision() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
BEGIN
  IF NEW.revision <> coalesce((SELECT max(revision) FROM public.salon_day_closes
                                WHERE salon_id = NEW.salon_id AND local_date = NEW.local_date), 0) + 1 THEN
    RAISE EXCEPTION 'day_close_revision_gap' USING ERRCODE = 'P0001';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER salon_day_closes_revision BEFORE INSERT ON public.salon_day_closes
  FOR EACH ROW EXECUTE FUNCTION public.guard_day_close_revision();
-- statement --
ALTER TABLE public.salon_expenses ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_cash_adjustments ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_day_closes ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes.
REVOKE ALL ON public.salon_expenses, public.salon_cash_adjustments, public.salon_day_closes
  FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.salon_expenses, public.salon_cash_adjustments, public.salon_day_closes
  TO postgres, service_role;
-- statement --
REVOKE ALL ON FUNCTION public.guard_finance_append_only(), public.guard_expense_reversal(),
  public.guard_cash_adjustment_reversal(), public.guard_day_close_revision() FROM PUBLIC, anon, authenticated;
-- statement --
-- Daily-ledger read paths. booking_payments is indexed by created_at today, not captured_at.
CREATE INDEX IF NOT EXISTS idx_booking_payments_salon_captured
  ON public.booking_payments (salon_id, captured_at) WHERE captured_at IS NOT NULL;
-- statement --
CREATE INDEX IF NOT EXISTS idx_bookings_salon_completed
  ON public.bookings (salon_id, completed_at) WHERE status = 'completed';
