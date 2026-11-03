-- Prepared only. Explicit reviewed migration, never API startup. Not applied to Mumbai, staging or production.
-- Bank account number encrypted at rest. The API encrypts the number with a key kept outside the
-- database (PAYOUT_ENCRYPTION_KEY) before it is written, and keeps its last four digits in their
-- own column so masking, history and the owner and admin screens keep working without ever
-- decrypting. Additive and order-safe: it can be applied before the key exists, and existing
-- plaintext rows stay valid until scripts/encrypt_payout_accounts.py converts them.
SET LOCAL lock_timeout='5s';
-- statement --
SET LOCAL statement_timeout='60s';
-- statement --
ALTER TABLE public.salon_payout_accounts ADD COLUMN IF NOT EXISTS bank_account_last4 text;
-- statement --
ALTER TABLE public.salon_payout_accounts DROP CONSTRAINT IF EXISTS ck_payout_account_format;
-- statement --
-- Either the legacy 9-18 digits or the encrypted form.
ALTER TABLE public.salon_payout_accounts ADD CONSTRAINT ck_payout_account_format CHECK (
  bank_account_number IS NULL
  OR bank_account_number ~ '^[0-9]{9,18}$'
  OR (bank_account_number ~ '^enc:v1:[A-Za-z0-9_=-]+$' AND char_length(bank_account_number) BETWEEN 60 AND 800)
);
-- statement --
ALTER TABLE public.salon_payout_accounts ADD CONSTRAINT ck_payout_last4_format CHECK (
  bank_account_last4 IS NULL OR bank_account_last4 ~ '^[0-9]{4}$'
);
-- statement --
-- An encrypted number cannot be masked, so its last four digits must be stored with it.
ALTER TABLE public.salon_payout_accounts ADD CONSTRAINT ck_payout_encrypted_has_last4 CHECK (
  bank_account_number IS NULL OR bank_account_number !~ '^enc:' OR bank_account_last4 IS NOT NULL
);
-- statement --
CREATE OR REPLACE FUNCTION public.payout_account_snapshot(r public.salon_payout_accounts)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path = public AS $$
  SELECT jsonb_build_object(
    'account_holder_name', r.account_holder_name,
    'upi_id', r.upi_id,
    'bank_name', r.bank_name,
    'ifsc', r.ifsc,
    'bank_account_last4', coalesce(
      r.bank_account_last4,
      CASE WHEN r.bank_account_number ~ '^[0-9]{9,18}$' THEN right(r.bank_account_number, 4) END)
  )
$$;
-- statement --
CREATE OR REPLACE FUNCTION public.salon_payout_account_masked(p_salon_id uuid)
RETURNS TABLE (
  account_holder_name text,
  upi_id              text,
  bank_name           text,
  bank_account_last4  text,
  ifsc                text,
  created_at          timestamptz,
  updated_at          timestamptz
) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT p.account_holder_name, p.upi_id, p.bank_name,
         coalesce(
           p.bank_account_last4,
           CASE WHEN p.bank_account_number ~ '^[0-9]{9,18}$' THEN right(p.bank_account_number, 4) END),
         p.ifsc, p.created_at, p.updated_at
  FROM public.salon_payout_accounts p
  WHERE p.salon_id = p_salon_id
$$;
-- statement --
REVOKE ALL ON FUNCTION public.salon_payout_account_masked(uuid) FROM PUBLIC, anon, authenticated;
-- statement --
GRANT EXECUTE ON FUNCTION public.salon_payout_account_masked(uuid) TO postgres, service_role;
