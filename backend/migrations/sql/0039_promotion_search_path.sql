-- PREPARED ONLY. Configuration only; retain the body, owner and SECURITY INVOKER.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '60s';
-- statement --
DO $review$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        WHERE p.oid = to_regprocedure('public.is_subscription_promotion_active(public.subscription_status,timestamptz,timestamptz,timestamptz,timestamptz)')
          AND p.proowner = 'postgres'::regrole AND NOT p.prosecdef
          AND p.prorettype = 'boolean'::regtype AND p.provolatile = 'i'
    ) THEN
        RAISE EXCEPTION 'Promotion function identity/security differs; abort review';
    END IF;
    IF has_schema_privilege('anon', 'public', 'CREATE')
       OR has_schema_privilege('authenticated', 'public', 'CREATE') THEN
        RAISE EXCEPTION 'Client CREATE on public is incompatible with fixed search_path';
    END IF;
END
$review$;
-- statement --
ALTER FUNCTION public.is_subscription_promotion_active(
    public.subscription_status, timestamptz, timestamptz, timestamptz, timestamptz
) SET search_path = public;
