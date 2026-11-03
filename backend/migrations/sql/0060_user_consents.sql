-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Consent records: which Terms and Privacy Policy version a person accepted and when, their
-- "13 or older" statement, and their marketing choice. Append-only in practice: a change is a
-- new row, and the newest row per kind is the current answer. Additive: one new private table.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
CREATE TABLE public.user_consents (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  seq        bigint GENERATED ALWAYS AS IDENTITY,
  user_id    uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  kind       text NOT NULL CHECK (kind IN ('terms', 'privacy', 'age_13_plus', 'marketing')),
  version    text NOT NULL CHECK (char_length(version) BETWEEN 1 AND 40),
  granted    boolean NOT NULL,
  source     text NOT NULL CHECK (source IN ('customer_app', 'owner_app', 'walkin_web')),
  created_at timestamptz NOT NULL DEFAULT now()
);
-- statement --
CREATE INDEX user_consents_latest ON public.user_consents (user_id, kind, seq DESC);
-- statement --
ALTER TABLE public.user_consents ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.user_consents FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT ON public.user_consents TO service_role;
-- statement --
CREATE POLICY user_consents_backend_read ON public.user_consents
  FOR SELECT TO service_role USING (true);
-- statement --
CREATE POLICY user_consents_backend_append ON public.user_consents
  FOR INSERT TO service_role WITH CHECK (true);
