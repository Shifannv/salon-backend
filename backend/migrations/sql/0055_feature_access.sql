-- Prepared only. Explicit reviewed migration, never API startup.
-- Super-admin controlled feature access: a catalogue of lockable features, a Trial/Growth/Premium
-- matrix, per-salon overrides with optional expiry, and editable plan descriptions.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='30s';
-- statement --
CREATE TABLE public.feature_catalog (
  key text PRIMARY KEY CHECK (key ~ '^[a-z][a-z0-9_]{1,63}$'),
  label text NOT NULL CHECK (length(btrim(label)) BETWEEN 1 AND 80),
  description text NOT NULL DEFAULT '' CHECK (length(description) <= 400),
  sort_order integer NOT NULL DEFAULT 0,
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
CREATE TABLE public.feature_plan_access (
  feature_key text NOT NULL REFERENCES public.feature_catalog(key) ON DELETE CASCADE,
  audience text NOT NULL CHECK (audience IN ('trial', 'growth', 'premium')),
  enabled boolean NOT NULL,
  updated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (feature_key, audience)
);
-- statement --
CREATE TABLE public.salon_feature_overrides (
  salon_id uuid NOT NULL REFERENCES public.salons(id) ON DELETE CASCADE,
  feature_key text NOT NULL REFERENCES public.feature_catalog(key) ON DELETE CASCADE,
  enabled boolean NOT NULL,
  expires_at timestamptz,
  note text CHECK (note IS NULL OR length(note) <= 200),
  set_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (salon_id, feature_key)
);
-- statement --
CREATE INDEX salon_feature_overrides_feature_idx ON public.salon_feature_overrides(feature_key);
-- statement --
CREATE TABLE public.plan_tier_content (
  tier text PRIMARY KEY CHECK (tier IN ('growth', 'premium')),
  headline text NOT NULL DEFAULT '' CHECK (length(headline) <= 120),
  description text NOT NULL DEFAULT '' CHECK (length(description) <= 600),
  bullets jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(bullets) = 'array'),
  updated_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
ALTER TABLE public.feature_catalog ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.feature_plan_access ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.salon_feature_overrides ENABLE ROW LEVEL SECURITY;
-- statement --
ALTER TABLE public.plan_tier_content ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.feature_catalog, public.feature_plan_access,
  public.salon_feature_overrides, public.plan_tier_content
  FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE, DELETE ON public.feature_catalog, public.feature_plan_access,
  public.salon_feature_overrides, public.plan_tier_content TO service_role;
-- statement --
INSERT INTO public.feature_catalog(key, label, description, sort_order) VALUES
  ('split_bill', 'Staff split bill', 'Split one bill across the staff who worked on it.', 10),
  ('daily_ledger', 'Daily ledger', 'A day-by-day cash book of sales, cash, UPI and refunds.', 20),
  ('expenses', 'Expenses', 'Record one-off and repeating salon expenses.', 30),
  ('finance_page', 'Finance page', 'The Finance area that holds the ledger, expenses and history.', 40),
  ('reports', 'Reports', 'Revenue, bookings and staff reports.', 50),
  ('staff_earnings', 'Staff earnings', 'Commission and earnings for each staff member.', 60),
  ('wallet', 'Wallet', 'Balance, payouts and wallet transactions.', 70),
  ('rank_boost', 'Search rank boost', 'Show the salon higher in customer search.', 80),
  ('smart_slot_filler', 'Smart slot filler', 'Suggest customers for empty slots.', 90),
  ('sms_alerts', 'SMS alerts', 'Send booking alerts by SMS.', 100);
-- statement --
INSERT INTO public.feature_plan_access(feature_key, audience, enabled)
SELECT c.key, a.audience,
  CASE a.audience
    WHEN 'premium' THEN true
    WHEN 'trial' THEN true
    ELSE c.key NOT IN ('split_bill', 'rank_boost', 'smart_slot_filler', 'sms_alerts')
  END
FROM public.feature_catalog c CROSS JOIN (VALUES ('trial'), ('growth'), ('premium')) AS a(audience);
-- statement --
INSERT INTO public.plan_tier_content(tier, headline, description, bullets) VALUES
  ('growth', 'Run the salon day to day', 'Everything to manage bookings, staff and the daily books.', '[]'::jsonb),
  ('premium', 'Grow faster', 'Everything in Growth plus tools that bring in more customers.', '[]'::jsonb);
