-- REVIEW DRAFT ONLY. Not executed; not part of the Alembic revision chain.
-- Destination: wqjlgpnbiapcrlkxumcp only, AFTER verified schema-only restore.
-- Do not run on Sydney. Verify project identity outside SQL before connecting.
-- Apply via psql --single-transaction --variable=ON_ERROR_STOP=1.
-- Inspect destination catalog before approval; do not suppress unexplained errors.

-- The restored 0024 function must be SECURITY DEFINER, owned by postgres, with
-- fixed search_path=public. It assigns roles from raw_app_meta_data only and
-- defaults to customer. Display fields may come from raw_user_meta_data.
-- Auth signup may have no JWT subject: NEW.id is the profile identity here.
-- An auth.uid() equality requirement would break legitimate Auth-trigger execution.
-- Verify no untrusted role has CREATE privilege on public before applying.

DO $review$
DECLARE
    function_oid oid := to_regprocedure('public.handle_new_user()');
BEGIN
    IF function_oid IS NULL THEN
        RAISE EXCEPTION 'Missing restored signup function; stop restore review';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_roles r ON r.oid = p.proowner
        WHERE p.oid = function_oid AND p.prosecdef
          AND p.prorettype = 'trigger'::regtype AND r.rolname = 'postgres'
          AND p.proconfig @> ARRAY['search_path=public']::text[]
    ) THEN
        RAISE EXCEPTION 'Signup function security differs from reviewed backup';
    END IF;
    -- Require full function-body comparison with reviewed backup as a separate gate.
    IF EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'auth.users'::regclass
          AND tgname = 't_on_auth_user_created'
    ) THEN
        RAISE EXCEPTION 'Signup trigger already exists; inspect definition before proceeding';
    END IF;
END
$review$;

REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO postgres, service_role;

CREATE TRIGGER t_on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- API transactions use privileged server DB credentials plus use-case ownership
-- checks and transaction-local actor claims. Existing postgres ownership and
-- service_role grants remain in place. Keep authenticated SELECT for scoped
-- reads/Realtime; existing ownership policies still determine accessible rows.
-- Removing table privileges is additional protection, not a substitute for RLS.
REVOKE ALL PRIVILEGES ON TABLE public.bookings, public.booking_services
    FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.bookings, public.booking_services TO authenticated;

-- Existing backup already enables RLS on these tables. Fail if it does not.
DO $review$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid IN ('public.bookings'::regclass, 'public.booking_services'::regclass)
          AND NOT relrowsecurity
    ) THEN
        RAISE EXCEPTION 'Restored booking tables lack RLS; stop and inspect';
    END IF;
END
$review$;

-- This hardening intentionally differs from the source ACLs and adds the omitted
-- Auth trigger. Document those differences in schema comparison. Do not claim
-- byte-for-byte source equality or stamp merely because object counts match.
-- No seed rows, business data, auth users or Alembic stamp are included.
