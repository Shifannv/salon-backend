-- Prepared only. Explicit reviewed migration, never API startup.
-- 1. New salons get a 60 day / 500 booking free trial (was 2 months / 120 bookings).
--    Trials already running keep the limits they started with.
-- 2. Admin-set per-salon plan prices. No row means the plan's normal price.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='30s';
-- statement --
CREATE OR REPLACE FUNCTION public.start_salon_trial(p_salon_id uuid, p_at timestamptz DEFAULT now())
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' AS $$
begin
  insert into public.salon_access(salon_id, trial_started_at, trial_ends_at, trial_booking_limit)
    values (p_salon_id, p_at, p_at + interval '60 days', 500)
  on conflict (salon_id) do update set trial_started_at = excluded.trial_started_at,
    trial_ends_at = excluded.trial_ends_at, trial_booking_limit = 500, bookings_counted = 0
    where public.salon_access.trial_started_at is null;
end $$;
-- statement --
ALTER TABLE public.salon_access ALTER COLUMN trial_booking_limit SET DEFAULT 500;
-- statement --
CREATE TABLE public.salon_plan_prices (
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES public.subscription_plans(id) ON DELETE RESTRICT,
  price_amount numeric(10,2) NOT NULL CHECK (price_amount > 0),
  set_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (salon_id, plan_id)
);
-- statement --
CREATE INDEX salon_plan_prices_plan_idx ON public.salon_plan_prices(plan_id);
-- statement --
ALTER TABLE public.salon_plan_prices ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.salon_plan_prices FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE, DELETE ON public.salon_plan_prices TO service_role;
-- statement --
-- 3. Default discount pricing: 6 months = 20% off monthly, 12 months = 30% off monthly,
--    rounded to the rupee.
--    Guard: only update if the price still equals the 0031 seed value, so an admin edit is
--    never overwritten. Monthly prices stay unchanged.
UPDATE public.subscription_plans SET price_amount = 1675.00
  WHERE code = 'growth_6m' AND price_amount = 1499.00;
-- statement --
UPDATE public.subscription_plans SET price_amount = 2932.00
  WHERE code = 'growth_12m' AND price_amount = 1999.00;
-- statement --
UPDATE public.subscription_plans SET price_amount = 2875.00
  WHERE code = 'premium_6m' AND price_amount = 2499.00;
-- statement --
UPDATE public.subscription_plans SET price_amount = 5032.00
  WHERE code = 'premium_12m' AND price_amount = 3499.00;
