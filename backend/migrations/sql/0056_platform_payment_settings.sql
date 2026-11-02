-- Prepared only. Explicit reviewed migration, never API startup.
-- Super-admin controlled payment settings: the platform commission rate and what it is taken from,
-- the minimum payout, and an optional commission rate for one salon. Rate and base are NULL until an
-- admin sets them: there is deliberately no default commission (the minimum payout does have a default).
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='30s';
-- statement --
CREATE TABLE public.platform_payment_settings (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  commission_rate_percent numeric(5,2) CHECK (commission_rate_percent BETWEEN 0 AND 100),
  commission_base text CHECK (commission_base IN ('online_amount', 'booking_total')),
  min_payout_paise bigint NOT NULL DEFAULT 10000 CHECK (min_payout_paise BETWEEN 100 AND 100000000),
  CONSTRAINT platform_payment_settings_rate_with_base CHECK ((commission_rate_percent IS NULL) = (commission_base IS NULL)),
  policy_version integer NOT NULL DEFAULT 1 CHECK (policy_version >= 1),
  updated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
INSERT INTO public.platform_payment_settings (singleton) VALUES (true);
-- statement --
CREATE TABLE public.salon_commission_overrides (
  salon_id uuid PRIMARY KEY REFERENCES public.salons(id) ON DELETE CASCADE,
  commission_rate_percent numeric(5,2) NOT NULL CHECK (commission_rate_percent BETWEEN 0 AND 100),
  note text CHECK (note IS NULL OR length(note) <= 200),
  set_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
-- Every change to the rate or the base is a new policy version, so a payment's snapshot says which
-- policy it was charged under. The settings row itself is never deleted.
CREATE FUNCTION public.guard_platform_payment_settings() RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
BEGIN
  IF TG_OP IN ('DELETE', 'TRUNCATE') THEN
    RAISE EXCEPTION 'payment_settings_are_never_deleted' USING ERRCODE = 'P0001';
  END IF;
  IF NEW.commission_rate_percent IS DISTINCT FROM OLD.commission_rate_percent
     OR NEW.commission_base IS DISTINCT FROM OLD.commission_base THEN
    NEW.policy_version := OLD.policy_version + 1;
  ELSE
    NEW.policy_version := OLD.policy_version;
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END $$;
-- statement --
CREATE TRIGGER platform_payment_settings_guard BEFORE UPDATE OR DELETE ON public.platform_payment_settings
  FOR EACH ROW EXECUTE FUNCTION public.guard_platform_payment_settings();
-- statement --
CREATE TRIGGER platform_payment_settings_no_truncate BEFORE TRUNCATE ON public.platform_payment_settings
  FOR EACH STATEMENT EXECUTE FUNCTION public.guard_platform_payment_settings();
-- statement --
ALTER TABLE public.platform_payment_settings ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_commission_overrides ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.platform_payment_settings, public.salon_commission_overrides
  FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, UPDATE ON public.platform_payment_settings TO service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE, DELETE ON public.salon_commission_overrides TO service_role;
