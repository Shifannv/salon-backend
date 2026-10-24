-- Prepared only. No existing values, money or provider configuration is changed.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '30s';
-- statement --
CREATE OR REPLACE FUNCTION public.stamp_checkout_policy()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE selected text;
BEGIN
  IF TG_OP = 'INSERT' THEN
    selected := coalesce(nullif(current_setting('app.booking_checkout_policy_version', true), ''),
                         'customer_processing_v1');
    IF selected NOT IN ('customer_processing_v1', 'u08-2026-10-23-v1') THEN
      RAISE EXCEPTION 'unsupported_checkout_policy' USING ERRCODE = '23514';
    END IF;
    NEW.checkout_policy_version := selected;
  ELSIF NEW.checkout_policy_version IS DISTINCT FROM OLD.checkout_policy_version THEN
    RAISE EXCEPTION 'checkout_policy_is_immutable' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
-- statement --
REVOKE ALL ON FUNCTION public.stamp_checkout_policy() FROM PUBLIC, anon, authenticated;
