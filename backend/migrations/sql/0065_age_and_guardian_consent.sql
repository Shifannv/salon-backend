-- Prepared only. Explicit reviewed migration, never API startup.
-- Date of birth (customers) and a guardian's approval for 13 to 17 year olds.
-- The date of birth can be set once; changing it later needs a support correction, so a teenager
-- cannot make themselves an adult. The guardian's phone number is stored only as a keyed hash plus
-- its last four digits, and the one-time code only as a hash.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
ALTER TABLE public.profiles ADD COLUMN date_of_birth date
  CHECK (date_of_birth IS NULL OR date_of_birth >= DATE '1900-01-01');
-- statement --
CREATE TABLE public.guardian_consents (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  guardian_phone_hash  text NOT NULL CHECK (char_length(guardian_phone_hash) = 64),
  guardian_phone_last4 text NOT NULL CHECK (guardian_phone_last4 ~ '^[0-9]{4}$'),
  status               text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'revoked')),
  code_hash            text CHECK (code_hash IS NULL OR char_length(code_hash) = 64),
  code_expires_at      timestamptz,
  attempts             integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  sends                integer NOT NULL DEFAULT 0 CHECK (sends >= 0),
  last_sent_at         timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now(),
  approved_at          timestamptz,
  revoked_at           timestamptz,
  CHECK ((status = 'approved') = (approved_at IS NOT NULL)),
  CHECK ((status = 'revoked') = (revoked_at IS NOT NULL))
);
-- statement --
-- One open request or approval per person; a revoked one is history.
CREATE UNIQUE INDEX guardian_consents_one_open ON public.guardian_consents (user_id)
  WHERE status IN ('pending', 'approved');
-- statement --
CREATE INDEX guardian_consents_user ON public.guardian_consents (user_id, created_at DESC);
-- statement --
ALTER TABLE public.guardian_consents ENABLE ROW LEVEL SECURITY;
-- statement --
REVOKE ALL ON public.guardian_consents FROM PUBLIC, anon, authenticated, service_role;
-- statement --
GRANT SELECT, INSERT, UPDATE ON public.guardian_consents TO service_role;
-- statement --
CREATE POLICY guardian_consents_backend_read ON public.guardian_consents
  FOR SELECT TO service_role USING (true);
-- statement --
CREATE POLICY guardian_consents_backend_write ON public.guardian_consents
  FOR INSERT TO service_role WITH CHECK (true);
-- statement --
CREATE POLICY guardian_consents_backend_update ON public.guardian_consents
  FOR UPDATE TO service_role USING (true) WITH CHECK (true);
