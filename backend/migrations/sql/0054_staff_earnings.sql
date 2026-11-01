-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Staff earnings (S1a): who did each service, commission rule versions, and one append-only earning
-- record per completed service. Additive: only two unique indexes are added to existing tables.
-- Money is integer paise. Reversal on refund, adjustments and staff payments are separate later
-- migrations (they need the cash-refund event and the "Mark as paid" design first).
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
-- Lets child rows prove they belong to the same salon as the staff member or service they point at.
CREATE UNIQUE INDEX IF NOT EXISTS staff_id_salon_id_key ON public.staff (id, salon_id);
-- statement --
CREATE UNIQUE INDEX IF NOT EXISTS services_id_salon_id_key ON public.services (id, salon_id);
-- statement --
-- Who did a service line. Current attribution is the highest revision. No row means the booking's own
-- staff member did it. A new revision is only allowed while the booking is not completed.
CREATE TABLE public.booking_service_staff (
  booking_id uuid NOT NULL,
  service_id uuid NOT NULL,
  revision integer NOT NULL CHECK (revision >= 1),
  salon_id uuid NOT NULL REFERENCES public.salons(id),
  staff_id uuid NOT NULL,
  changed_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (booking_id, service_id, revision),
  FOREIGN KEY (booking_id, service_id) REFERENCES public.booking_services(booking_id, service_id) ON DELETE RESTRICT,
  FOREIGN KEY (staff_id, salon_id) REFERENCES public.staff(id, salon_id) ON DELETE RESTRICT
);
-- statement --
CREATE INDEX booking_service_staff_staff ON public.booking_service_staff (staff_id);
-- statement --
CREATE INDEX booking_service_staff_salon ON public.booking_service_staff (salon_id);
-- statement --
CREATE INDEX booking_service_staff_changed_by ON public.booking_service_staff (changed_by) WHERE changed_by IS NOT NULL;
-- statement --
CREATE FUNCTION public.guard_booking_service_staff() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  b_salon uuid;
  b_status text;
  last_revision integer;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    IF TG_OP = 'UPDATE' AND NEW.changed_by IS NULL AND OLD.changed_by IS NOT NULL
       AND (to_jsonb(NEW) - 'changed_by') IS NOT DISTINCT FROM (to_jsonb(OLD) - 'changed_by') THEN
      RETURN NEW; -- deleting the profile that made the change clears who it was, nothing else
    END IF;
    RAISE EXCEPTION 'staff_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  SELECT salon_id, status::text INTO b_salon, b_status FROM public.bookings WHERE id = NEW.booking_id FOR SHARE;
  IF b_salon IS DISTINCT FROM NEW.salon_id THEN
    RAISE EXCEPTION 'attribution_wrong_salon' USING ERRCODE = 'P0001';
  END IF;
  IF b_status NOT IN ('pending', 'confirmed', 'checked_in') THEN
    RAISE EXCEPTION 'attribution_after_completion' USING ERRCODE = 'P0001';
  END IF;
  SELECT coalesce(max(revision), 0) INTO last_revision FROM public.booking_service_staff
    WHERE booking_id = NEW.booking_id AND service_id = NEW.service_id;
  IF NEW.revision <> last_revision + 1 THEN
    RAISE EXCEPTION 'attribution_revision_out_of_order' USING ERRCODE = 'P0001';
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER booking_service_staff_guard BEFORE INSERT OR UPDATE OR DELETE ON public.booking_service_staff
  FOR EACH ROW EXECUTE FUNCTION public.guard_booking_service_staff();
-- statement --
-- A commission rule, one version at a time. staff_id / service_id NULL mean "any". Rules are never
-- edited: a change is a new version, and "stop paying commission" is a new NONE version.
CREATE TABLE public.staff_commission_rule_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id),
  staff_id uuid,
  service_id uuid,
  version integer NOT NULL CHECK (version >= 1),
  commission_type text NOT NULL CHECK (commission_type IN ('NONE', 'FIXED_PER_SERVICE', 'PERCENT_OF_SERVICE_VALUE')),
  rate_basis_points integer CHECK (rate_basis_points BETWEEN 0 AND 10000),
  fixed_amount_paise bigint CHECK (fixed_amount_paise >= 0),
  effective_from timestamptz NOT NULL,
  created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 8 AND 200),
  request_hash text NOT NULL CHECK (char_length(request_hash) = 64),
  FOREIGN KEY (staff_id, salon_id) REFERENCES public.staff(id, salon_id),
  FOREIGN KEY (service_id, salon_id) REFERENCES public.services(id, salon_id),
  UNIQUE (salon_id, idempotency_key),
  CHECK ((commission_type = 'NONE' AND rate_basis_points IS NULL AND fixed_amount_paise IS NULL)
      OR (commission_type = 'FIXED_PER_SERVICE' AND rate_basis_points IS NULL AND fixed_amount_paise IS NOT NULL)
      OR (commission_type = 'PERCENT_OF_SERVICE_VALUE' AND fixed_amount_paise IS NULL AND rate_basis_points IS NOT NULL))
);
-- statement --
-- One version number per scope, so two owners saving at once cannot both be version 2.
CREATE UNIQUE INDEX staff_commission_rule_scope_version ON public.staff_commission_rule_versions
  (salon_id, coalesce(staff_id, '00000000-0000-0000-0000-000000000000'::uuid),
   coalesce(service_id, '00000000-0000-0000-0000-000000000000'::uuid), version);
-- statement --
CREATE INDEX staff_commission_rule_lookup ON public.staff_commission_rule_versions (salon_id, staff_id, service_id, effective_from);
-- statement --
CREATE INDEX staff_commission_rule_staff ON public.staff_commission_rule_versions (staff_id) WHERE staff_id IS NOT NULL;
-- statement --
CREATE INDEX staff_commission_rule_service ON public.staff_commission_rule_versions (service_id) WHERE service_id IS NOT NULL;
-- statement --
CREATE INDEX staff_commission_rule_created_by ON public.staff_commission_rule_versions (created_by) WHERE created_by IS NOT NULL;
-- statement --
-- What one completed service earned its staff member, written when the booking completes and never
-- changed. The rule that applied is copied into the row, so a later rule change cannot rewrite it.
-- A row exists for EVERY completed service, including ones that earned nothing (no rule, or NONE).
CREATE TABLE public.staff_earnings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  salon_id uuid NOT NULL REFERENCES public.salons(id),
  booking_id uuid NOT NULL,
  service_id uuid NOT NULL,
  staff_id uuid NOT NULL,
  attribution_source text NOT NULL CHECK (attribution_source IN ('booking_staff', 'attributed')),
  service_value_paise bigint NOT NULL CHECK (service_value_paise >= 0),
  amount_paise bigint NOT NULL CHECK (amount_paise >= 0),
  rule_version_id uuid REFERENCES public.staff_commission_rule_versions(id),
  commission_type text NOT NULL CHECK (commission_type IN ('NONE', 'FIXED_PER_SERVICE', 'PERCENT_OF_SERVICE_VALUE')),
  rate_basis_points integer CHECK (rate_basis_points BETWEEN 0 AND 10000),
  fixed_amount_paise bigint CHECK (fixed_amount_paise >= 0),
  completed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (booking_id, service_id),
  FOREIGN KEY (booking_id, service_id) REFERENCES public.booking_services(booking_id, service_id) ON DELETE RESTRICT,
  FOREIGN KEY (staff_id, salon_id) REFERENCES public.staff(id, salon_id) ON DELETE RESTRICT,
  CHECK (amount_paise <= service_value_paise),
  CHECK (commission_type <> 'NONE' OR amount_paise = 0),
  -- The amount follows from the copied rule and the line's value. A fixed amount never exceeds the price (F15).
  CHECK (commission_type <> 'FIXED_PER_SERVICE' OR amount_paise = least(fixed_amount_paise, service_value_paise)),
  CHECK (commission_type <> 'PERCENT_OF_SERVICE_VALUE'
         OR amount_paise = least(service_value_paise, (2 * service_value_paise * rate_basis_points + 10000) / 20000)),
  CHECK ((commission_type = 'NONE' AND rate_basis_points IS NULL AND fixed_amount_paise IS NULL)
      OR (commission_type = 'FIXED_PER_SERVICE' AND rate_basis_points IS NULL AND fixed_amount_paise IS NOT NULL)
      OR (commission_type = 'PERCENT_OF_SERVICE_VALUE' AND fixed_amount_paise IS NULL AND rate_basis_points IS NOT NULL)),
  CHECK (commission_type = 'NONE' OR rule_version_id IS NOT NULL)
);
-- statement --
CREATE INDEX staff_earnings_salon_completed ON public.staff_earnings (salon_id, completed_at);
-- statement --
CREATE INDEX staff_earnings_staff_completed ON public.staff_earnings (staff_id, completed_at);
-- statement --
CREATE INDEX staff_earnings_rule ON public.staff_earnings (rule_version_id) WHERE rule_version_id IS NOT NULL;
-- statement --
-- Same-salon proof for the booking, which has no (id, salon_id) key to point a foreign key at.
CREATE FUNCTION public.guard_staff_earning() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  b_salon uuid;
  b_status text;
  b_staff uuid;
  line_price numeric;
  line_active boolean;
  attributed uuid;
  expected_source text;
  r record;
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'staff_records_are_append_only' USING ERRCODE = 'P0001';
  END IF;
  SELECT salon_id, status::text, staff_id INTO b_salon, b_status, b_staff
    FROM public.bookings WHERE id = NEW.booking_id FOR SHARE;
  IF b_salon IS DISTINCT FROM NEW.salon_id THEN
    RAISE EXCEPTION 'earning_wrong_salon' USING ERRCODE = 'P0001';
  END IF;
  IF b_status IS DISTINCT FROM 'completed' THEN
    RAISE EXCEPTION 'earning_before_completion' USING ERRCODE = 'P0001';
  END IF;
  SELECT price, is_active INTO line_price, line_active FROM public.booking_services
    WHERE booking_id = NEW.booking_id AND service_id = NEW.service_id;
  IF line_active IS NOT TRUE THEN
    RAISE EXCEPTION 'earning_for_inactive_service' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.service_value_paise <> round(line_price * 100)::bigint THEN
    RAISE EXCEPTION 'earning_value_mismatch' USING ERRCODE = 'P0001';
  END IF;
  SELECT staff_id INTO attributed FROM public.booking_service_staff
    WHERE booking_id = NEW.booking_id AND service_id = NEW.service_id ORDER BY revision DESC LIMIT 1;
  expected_source := CASE WHEN attributed IS NOT NULL THEN 'attributed' ELSE 'booking_staff' END;
  IF NEW.staff_id IS DISTINCT FROM coalesce(attributed, b_staff)
     OR NEW.attribution_source IS DISTINCT FROM expected_source THEN
    RAISE EXCEPTION 'earning_wrong_staff' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.rule_version_id IS NOT NULL THEN
    SELECT salon_id, staff_id, service_id, commission_type, rate_basis_points, fixed_amount_paise,
           effective_from INTO r FROM public.staff_commission_rule_versions WHERE id = NEW.rule_version_id;
    IF r.salon_id IS DISTINCT FROM NEW.salon_id
       OR r.commission_type <> NEW.commission_type
       OR r.rate_basis_points IS DISTINCT FROM NEW.rate_basis_points
       OR r.fixed_amount_paise IS DISTINCT FROM NEW.fixed_amount_paise
       OR (r.staff_id IS NOT NULL AND r.staff_id <> NEW.staff_id)
       OR (r.service_id IS NOT NULL AND r.service_id <> NEW.service_id)
       OR r.effective_from > NEW.completed_at THEN
      RAISE EXCEPTION 'earning_rule_mismatch' USING ERRCODE = 'P0001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER staff_earnings_guard BEFORE INSERT OR UPDATE OR DELETE ON public.staff_earnings
  FOR EACH ROW EXECUTE FUNCTION public.guard_staff_earning();
-- statement --
CREATE FUNCTION public.guard_staff_commission_rule() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE latest timestamptz;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT max(effective_from) INTO latest FROM public.staff_commission_rule_versions
      WHERE salon_id = NEW.salon_id
        AND staff_id IS NOT DISTINCT FROM NEW.staff_id AND service_id IS NOT DISTINCT FROM NEW.service_id;
    IF latest IS NOT NULL AND NEW.effective_from < latest THEN
      RAISE EXCEPTION 'rule_effective_from_goes_backwards' USING ERRCODE = 'P0001';
    END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.created_by IS NULL AND OLD.created_by IS NOT NULL
     AND (to_jsonb(NEW) - 'created_by') IS NOT DISTINCT FROM (to_jsonb(OLD) - 'created_by') THEN
    RETURN NEW; -- deleting the profile that made the rule clears who it was, nothing else
  END IF;
  RAISE EXCEPTION 'staff_records_are_append_only' USING ERRCODE = 'P0001';
END $$;
-- statement --
CREATE TRIGGER staff_commission_rule_guard BEFORE INSERT OR UPDATE OR DELETE ON public.staff_commission_rule_versions
  FOR EACH ROW EXECUTE FUNCTION public.guard_staff_commission_rule();
-- statement --
CREATE FUNCTION public.refuse_staff_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
BEGIN
  RAISE EXCEPTION 'staff_records_are_append_only' USING ERRCODE = 'P0001';
END $$;
-- statement --
CREATE TRIGGER booking_service_staff_no_truncate BEFORE TRUNCATE ON public.booking_service_staff
  FOR EACH STATEMENT EXECUTE FUNCTION public.refuse_staff_truncate();
-- statement --
CREATE TRIGGER staff_commission_rule_no_truncate BEFORE TRUNCATE ON public.staff_commission_rule_versions
  FOR EACH STATEMENT EXECUTE FUNCTION public.refuse_staff_truncate();
-- statement --
CREATE TRIGGER staff_earnings_no_truncate BEFORE TRUNCATE ON public.staff_earnings
  FOR EACH STATEMENT EXECUTE FUNCTION public.refuse_staff_truncate();
-- statement --
REVOKE ALL ON FUNCTION public.guard_booking_service_staff(), public.guard_staff_earning(), public.guard_staff_commission_rule(), public.refuse_staff_truncate()
  FROM PUBLIC, anon, authenticated;
-- statement --
ALTER TABLE public.booking_service_staff ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.staff_commission_rule_versions ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.staff_earnings ENABLE ROW LEVEL SECURITY;
-- statement --
-- No policy: deny-all for the public roles. Only the backend's own role reads and writes. Staff must never
-- be able to read commission rules or earnings (decision F02).
REVOKE ALL ON public.booking_service_staff, public.staff_commission_rule_versions, public.staff_earnings
  FROM PUBLIC, anon, authenticated;
-- statement --
GRANT ALL ON public.booking_service_staff, public.staff_commission_rule_versions, public.staff_earnings
  TO postgres, service_role;
-- statement --
REVOKE TRUNCATE ON public.booking_service_staff, public.staff_commission_rule_versions, public.staff_earnings
  FROM service_role;
