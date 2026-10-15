-- REVIEW ONLY / NOT EXECUTED / NOT AN ALEMBIC REVISION.
-- Destination: wqjlgpnbiapcrlkxumcp, ap-south-1 ONLY.
-- Independently verify the project before connection; shared pooler host is not identity.
-- Requires separate user approval. No data/history/stamp/deployment operations.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SET LOCAL search_path = pg_catalog, public;

-- Reuse reviewed 0024 function. Do not recreate it, change its body or grant clients EXECUTE.
-- Snapshot body MD5 is a drift guard, not a replacement for reviewed source comparison.
DO $review$
DECLARE fn oid := to_regprocedure('public.handle_new_user()');
BEGIN
    IF fn IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_proc WHERE oid = fn AND proowner = 'postgres'::regrole
          AND prosecdef AND prorettype = 'trigger'::regtype
          AND proconfig = ARRAY['search_path=public']::text[]
          AND md5(prosrc) = 'bbc4006b3b60009d8f7ff6cdd89f71df'
    ) THEN RAISE EXCEPTION 'Signup function differs from reviewed backup/0024'; END IF;
    IF has_schema_privilege('anon', 'public', 'CREATE')
       OR has_schema_privilege('authenticated', 'public', 'CREATE') THEN
        RAISE EXCEPTION 'Untrusted role can create public objects';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid = 'auth.users'::regclass
        AND tgname = 't_on_auth_user_created') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'auth.users'::regclass AND tgname = 't_on_auth_user_created'
              AND NOT tgisinternal AND tgtype = 5 AND tgfoid = fn AND tgenabled = 'O'
              AND tgqual IS NULL AND tgattr::text = '' AND tgargs = ''::bytea
              AND tgconstraint = 0 AND tgparentid = 0
              AND tgoldtable IS NULL AND tgnewtable IS NULL) THEN
            RAISE EXCEPTION 'Existing signup trigger differs; never replace automatically';
        END IF;
    ELSE
        CREATE TRIGGER t_on_auth_user_created AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
    END IF;
END
$review$;
-- Existing matching trigger is retained. Expected Mumbai delta: no change.
-- No signup, INSERT, role assignment, function grant or user-data copying is performed.
COMMIT;
