\set ON_ERROR_STOP on
DO $gate$ BEGIN IF current_database()<>'postgres' OR current_user<>'postgres' THEN RAISE EXCEPTION 'Unexpected database/user'; END IF; IF EXISTS(SELECT 1 FROM public.alembic_version) THEN RAISE EXCEPTION 'Alembic history is no longer empty'; END IF; END $gate$;
SELECT set_config('mumbai_preflight.before_hash', md5(jsonb_build_object(
 'application', (select jsonb_build_object(
 'tables',(select jsonb_object_agg(c.relname,jsonb_build_object('rls',c.relrowsecurity,'replica_identity',c.relreplident)) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'),
 'columns',(select jsonb_object_agg(c.relname||'.'||a.attname,jsonb_build_object('type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),'generated',a.attgenerated,'identity',a.attidentity)) from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where n.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped),
 'constraints',(select jsonb_object_agg(c.relname||'.'||k.conname,pg_get_constraintdef(k.oid)) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'),
 'indexes',(select jsonb_object_agg(indexname,indexdef) from pg_indexes where schemaname='public'),
 'functions',(select jsonb_object_agg(p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',jsonb_build_object('body',p.prosrc,'result',pg_get_function_result(p.oid),'language',l.lanname,'volatility',p.provolatile,'security_definer',p.prosecdef,'config',p.proconfig)) from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_language l on l.oid=p.prolang where n.nspname='public' and not exists(select 1 from pg_depend d where d.classid='pg_proc'::regclass and d.objid=p.oid and d.deptype='e')),
 'triggers',(select jsonb_object_agg(n.nspname||'.'||c.relname||'.'||t.tgname,pg_get_triggerdef(t.oid)) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where not t.tgisinternal and (n.nspname='public' or (n.nspname='auth' and c.relname='users'))),
 'policies',(select jsonb_object_agg(tablename||'.'||policyname,jsonb_build_object('cmd',cmd,'roles',roles,'permissive',permissive,'using',qual,'check',with_check)) from pg_policies where schemaname='public'),
 'enums',(select jsonb_object_agg(typname,labels) from (select t.typname,jsonb_agg(e.enumlabel order by e.enumsortorder) labels from pg_type t join pg_namespace n on n.oid=t.typnamespace join pg_enum e on e.enumtypid=t.oid where n.nspname='public' group by t.typname)x)
)),
 'relation_acls',(SELECT jsonb_agg(jsonb_build_object('oid',c.oid,'acl',c.relacl,'owner',c.relowner) ORDER BY c.oid)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'function_acls',(SELECT jsonb_agg(jsonb_build_object('oid',p.oid,'acl',p.proacl,'owner',p.proowner,'config',p.proconfig) ORDER BY p.oid)
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'column_acls',(SELECT jsonb_agg(jsonb_build_object('table',a.attrelid,'num',a.attnum,'acl',a.attacl) ORDER BY a.attrelid,a.attnum)
    FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'schema_acls',(SELECT jsonb_agg(jsonb_build_object('oid',oid,'owner',nspowner,'acl',nspacl) ORDER BY oid) FROM pg_namespace),
 'defaults',(SELECT jsonb_agg(to_jsonb(d) ORDER BY d.oid) FROM pg_default_acl d),
 'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.roleid,m.member,m.grantor) FROM pg_auth_members m),
 'alembic',(SELECT coalesce(jsonb_agg(version_num),'[]'::jsonb) FROM public.alembic_version),
 'auth_count',(SELECT count(*) FROM auth.users),
 'profiles',(SELECT count(*) FROM public.profiles),
 'bookings',(SELECT count(*) FROM public.bookings)
)::text),false) IS NOT NULL AS snapshot_captured;
BEGIN;
\echo preflight_0038_cancellation_compatibility
-- PREPARED ONLY. Not executed. Alembic owns the transaction.
-- Both arbitrary text fields are scrubbed to NULL by account deletion, not retained
-- as legal/audit identifiers. No migration-time data erasure or backfill.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '60s';
-- statement --
DO $review$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'bookings'
          AND column_name IN ('cancellation_reason_code', 'cancellation_reason_text')
          AND (data_type <> 'text' OR udt_schema <> 'pg_catalog' OR udt_name <> 'text'
               OR is_nullable <> 'YES' OR column_default IS NOT NULL
               OR is_generated <> 'NEVER' OR is_identity <> 'NO'
               OR domain_name IS NOT NULL OR collation_name IS NOT NULL)
    ) THEN
        RAISE EXCEPTION 'Cancellation compatibility definition differs; abort review';
    END IF;
END
$review$;
-- statement --
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_code text;
-- statement --
ALTER TABLE public.bookings ADD COLUMN IF NOT EXISTS cancellation_reason_text text;

\echo preflight_0039_promotion_search_path
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

\echo preflight_0040_fastapi_only_access
-- PREPARED ONLY; NOT EXECUTED. Existing named objects; NO positive/default grants.
SET LOCAL lock_timeout = '5s';
-- statement --
SET LOCAL statement_timeout = '60s';
-- statement --
-- Guard NAMED objects, extension membership, owners, RLS and column ACLs.
-- Full inventory/body/config equality is a separate pre-execution comparison gate.
DO $review$
DECLARE obj oid;
BEGIN
    obj := to_regclass('public.account_deletion_challenges');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.account_deletion_challenges';
    END IF;
    obj := to_regclass('public.account_deletion_requests');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.account_deletion_requests';
    END IF;
    obj := to_regclass('public.alembic_version');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.alembic_version';
    END IF;
    obj := to_regclass('public.api_rate_limits');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.api_rate_limits';
    END IF;
    obj := to_regclass('public.blocked_slots');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.blocked_slots';
    END IF;
    obj := to_regclass('public.booking_action_requests');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.booking_action_requests';
    END IF;
    obj := to_regclass('public.booking_audit_events');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.booking_audit_events';
    END IF;
    obj := to_regclass('public.booking_payments');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.booking_payments';
    END IF;
    obj := to_regclass('public.booking_services');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.booking_services';
    END IF;
    obj := to_regclass('public.bookings');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.bookings';
    END IF;
    obj := to_regclass('public.customer_booking_restrictions');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.customer_booking_restrictions';
    END IF;
    obj := to_regclass('public.device_tokens');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.device_tokens';
    END IF;
    obj := to_regclass('public.email_events');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.email_events';
    END IF;
    obj := to_regclass('public.languages');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.languages';
    END IF;
    obj := to_regclass('public.notification_deliveries');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.notification_deliveries';
    END IF;
    obj := to_regclass('public.notification_outbox');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.notification_outbox';
    END IF;
    obj := to_regclass('public.notifications');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.notifications';
    END IF;
    obj := to_regclass('public.payment_anomalies');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_anomalies';
    END IF;
    obj := to_regclass('public.payment_idempotency_keys');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_idempotency_keys';
    END IF;
    obj := to_regclass('public.payment_provider_account_audit');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_provider_account_audit';
    END IF;
    obj := to_regclass('public.payment_provider_accounts');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_provider_accounts';
    END IF;
    obj := to_regclass('public.payment_refunds');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_refunds';
    END IF;
    obj := to_regclass('public.payment_webhook_events');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.payment_webhook_events';
    END IF;
    obj := to_regclass('public.profiles');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.profiles';
    END IF;
    obj := to_regclass('public.salon_access');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_access';
    END IF;
    obj := to_regclass('public.salon_holidays');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_holidays';
    END IF;
    obj := to_regclass('public.salon_images');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_images';
    END IF;
    obj := to_regclass('public.salon_payout_account_history');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_payout_account_history';
    END IF;
    obj := to_regclass('public.salon_payout_accounts');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_payout_accounts';
    END IF;
    obj := to_regclass('public.salon_reports');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_reports';
    END IF;
    obj := to_regclass('public.salon_subscriptions');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salon_subscriptions';
    END IF;
    obj := to_regclass('public.salons');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.salons';
    END IF;
    obj := to_regclass('public.service_categories');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.service_categories';
    END IF;
    obj := to_regclass('public.service_subcategories');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.service_subcategories';
    END IF;
    obj := to_regclass('public.services');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.services';
    END IF;
    obj := to_regclass('public.staff');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.staff';
    END IF;
    obj := to_regclass('public.staff_service_languages');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.staff_service_languages';
    END IF;
    obj := to_regclass('public.staff_services');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.staff_services';
    END IF;
    obj := to_regclass('public.subscription_billing_records');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.subscription_billing_records';
    END IF;
    obj := to_regclass('public.subscription_events');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.subscription_events';
    END IF;
    obj := to_regclass('public.subscription_plans');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.subscription_plans';
    END IF;
    obj := to_regclass('public.subscription_provider_accounts');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.subscription_provider_accounts';
    END IF;
    obj := to_regclass('public.support_messages');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.support_messages';
    END IF;
    obj := to_regclass('public.support_tickets');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_class
        WHERE oid = obj AND relkind = 'r' AND relowner = 'postgres'::regrole AND relrowsecurity)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_class'::regclass
        AND objid = obj AND deptype = 'e')
      OR EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = obj
        AND attnum > 0 AND NOT attisdropped AND attacl IS NOT NULL) THEN
        RAISE EXCEPTION 'Review table/column ACL drift: public.support_tickets';
    END IF;
    obj := to_regprocedure('public.app_role()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.app_role()';
    END IF;
    obj := to_regprocedure('public.apply_subscription_billing_record(uuid,integer)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.apply_subscription_billing_record(uuid,integer)';
    END IF;
    obj := to_regprocedure('public.booking_append_audit()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.booking_append_audit()';
    END IF;
    obj := to_regprocedure('public.cancel_salon_subscription_renewal(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.cancel_salon_subscription_renewal(uuid)';
    END IF;
    obj := to_regprocedure('public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)';
    END IF;
    obj := to_regprocedure('public.deactivate_device_token(text)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.deactivate_device_token(text)';
    END IF;
    obj := to_regprocedure('public.demote_other_main_images()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.demote_other_main_images()';
    END IF;
    obj := to_regprocedure('public.effective_duration(uuid,uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.effective_duration(uuid,uuid)';
    END IF;
    obj := to_regprocedure('public.enqueue_booking_email()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.enqueue_booking_email()';
    END IF;
    obj := to_regprocedure('public.enqueue_verified_payment_receipt()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.enqueue_verified_payment_receipt()';
    END IF;
    obj := to_regprocedure('public.erase_profile_references(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.erase_profile_references(uuid)';
    END IF;
    obj := to_regprocedure('public.get_active_tokens(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.get_active_tokens(uuid)';
    END IF;
    obj := to_regprocedure('public.get_available_slots(uuid,date,integer)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.get_available_slots(uuid,date,integer)';
    END IF;
    obj := to_regprocedure('public.get_salon_by_qr(text)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.get_salon_by_qr(text)';
    END IF;
    obj := to_regprocedure('public.guard_audit_immutable()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_audit_immutable()';
    END IF;
    obj := to_regprocedure('public.guard_booking_against_closure()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_booking_against_closure()';
    END IF;
    obj := to_regprocedure('public.guard_booking_checkout()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_booking_checkout()';
    END IF;
    obj := to_regprocedure('public.guard_booking_payment_columns()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_booking_payment_columns()';
    END IF;
    obj := to_regprocedure('public.guard_booking_salon_approval()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_booking_salon_approval()';
    END IF;
    obj := to_regprocedure('public.guard_collection_snapshot()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_collection_snapshot()';
    END IF;
    obj := to_regprocedure('public.guard_media_reference()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_media_reference()';
    END IF;
    obj := to_regprocedure('public.guard_salon_approval()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_salon_approval()';
    END IF;
    obj := to_regprocedure('public.guard_salon_discovery_placement()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_salon_discovery_placement()';
    END IF;
    obj := to_regprocedure('public.guard_salon_display_priority()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_salon_display_priority()';
    END IF;
    obj := to_regprocedure('public.guard_subscription_admin()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.guard_subscription_admin()';
    END IF;
    obj := to_regprocedure('public.handle_new_user()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.handle_new_user()';
    END IF;
    obj := to_regprocedure('public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)';
    END IF;
    obj := to_regprocedure('public.is_super_admin()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.is_super_admin()';
    END IF;
    obj := to_regprocedure('public.owns_salon(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.owns_salon(uuid)';
    END IF;
    obj := to_regprocedure('public.payment_append_audit()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.payment_append_audit()';
    END IF;
    obj := to_regprocedure('public.payout_account_snapshot(public.salon_payout_accounts)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.payout_account_snapshot(public.salon_payout_accounts)';
    END IF;
    obj := to_regprocedure('public.recompute_booking_payment_state(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.recompute_booking_payment_state(uuid)';
    END IF;
    obj := to_regprocedure('public.recompute_salon_trial(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.recompute_salon_trial(uuid)';
    END IF;
    obj := to_regprocedure('public.register_device_token(text,text,text)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.register_device_token(text,text,text)';
    END IF;
    obj := to_regprocedure('public.salon_booking_eligible(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.salon_booking_eligible(uuid)';
    END IF;
    obj := to_regprocedure('public.salon_payout_account_masked(uuid)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.salon_payout_account_masked(uuid)';
    END IF;
    obj := to_regprocedure('public.salon_trial_setting(text,integer,integer,integer)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.salon_trial_setting(text,integer,integer,integer)';
    END IF;
    obj := to_regprocedure('public.set_audit_actor()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.set_audit_actor()';
    END IF;
    obj := to_regprocedure('public.set_updated_at()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.set_updated_at()';
    END IF;
    obj := to_regprocedure('public.stamp_booking_lifecycle()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.stamp_booking_lifecycle()';
    END IF;
    obj := to_regprocedure('public.stamp_checkout_policy()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.stamp_checkout_policy()';
    END IF;
    obj := to_regprocedure('public.stamp_notification_read_at()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.stamp_notification_read_at()';
    END IF;
    obj := to_regprocedure('public.start_salon_trial(uuid,timestamp with time zone)');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.start_salon_trial(uuid,timestamp with time zone)';
    END IF;
    obj := to_regprocedure('public.sweep_lapsed_subscriptions()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.sweep_lapsed_subscriptions()';
    END IF;
    obj := to_regprocedure('public.tg_booking_payments_guard()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_booking_payments_guard()';
    END IF;
    obj := to_regprocedure('public.tg_booking_payments_recompute()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_booking_payments_recompute()';
    END IF;
    obj := to_regprocedure('public.tg_bookings_recompute_trial()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_bookings_recompute_trial()';
    END IF;
    obj := to_regprocedure('public.tg_payment_refunds_guard()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_payment_refunds_guard()';
    END IF;
    obj := to_regprocedure('public.tg_payment_refunds_recompute()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_payment_refunds_recompute()';
    END IF;
    obj := to_regprocedure('public.tg_salon_payout_account_history()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_salon_payout_account_history()';
    END IF;
    obj := to_regprocedure('public.tg_salons_access_row()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_salons_access_row()';
    END IF;
    obj := to_regprocedure('public.tg_subscription_billing_guard()');
    IF obj IS NULL OR NOT EXISTS (SELECT 1 FROM pg_proc
        WHERE oid = obj AND proowner = 'postgres'::regrole)
      OR EXISTS (SELECT 1 FROM pg_depend WHERE classid = 'pg_proc'::regclass
        AND objid = obj AND deptype = 'e') THEN
        RAISE EXCEPTION 'Review function inventory drift: public.tg_subscription_billing_guard()';
    END IF;
END
$review$;
-- statement --
-- Capture retained effective server access, including inherited PUBLIC/client rights.
-- Transaction-local metadata only; not a table, persistent setting or future default.
DO $review$
BEGIN
    PERFORM set_config('mumbai_review.server_effective_before', (
        SELECT coalesce(jsonb_agg(right_to_keep), '[]'::jsonb)::text FROM (
            SELECT jsonb_build_object('kind', 'table', 'object', c.oid::regclass::text,
                'role', r.name, 'privilege', v.privilege) AS right_to_keep
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'),
                ('TRUNCATE'), ('REFERENCES'), ('TRIGGER'), ('MAINTAIN')) AS v(privilege)
            WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
              AND has_table_privilege(r.name, c.oid, v.privilege)
            UNION ALL
            SELECT jsonb_build_object('kind', 'sequence', 'object', c.oid::regclass::text,
                'role', r.name, 'privilege', v.privilege)
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            CROSS JOIN (VALUES ('USAGE'), ('SELECT'), ('UPDATE')) AS v(privilege)
            WHERE n.nspname = 'public' AND c.relkind = 'S'
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e')
              AND has_sequence_privilege(r.name, c.oid, v.privilege)
            UNION ALL
            SELECT jsonb_build_object('kind', 'function', 'object', p.oid::regprocedure::text,
                'role', r.name, 'privilege', 'EXECUTE')
            FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            CROSS JOIN (VALUES ('postgres'), ('service_role')) AS r(name)
            WHERE n.nspname = 'public'
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                  WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid AND d.deptype = 'e')
              AND has_function_privilege(r.name, p.oid, 'EXECUTE')
        ) AS rights
    ), true);
END
$review$;
-- statement --
-- Existing NAMED application objects only. No managed extension objects included.
-- No role, schema, default-privilege or future-object changes. RESTRICT is deliberate.
-- postgres owns these objects; its backend sessions need no additional GRANT.
REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_challenges FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.account_deletion_requests FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.api_rate_limits FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.blocked_slots FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.booking_action_requests FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.booking_audit_events FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.booking_payments FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.booking_services FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.bookings FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.customer_booking_restrictions FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.device_tokens FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.email_events FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.languages FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.notification_deliveries FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.notification_outbox FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.notifications FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_anomalies FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_idempotency_keys FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_provider_account_audit FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_provider_accounts FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_refunds FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.payment_webhook_events FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.profiles FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_access FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_holidays FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_images FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_payout_account_history FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_payout_accounts FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_reports FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salon_subscriptions FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.salons FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.service_categories FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.service_subcategories FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.services FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.staff FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.staff_service_languages FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.staff_services FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.subscription_billing_records FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.subscription_events FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.subscription_plans FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.subscription_provider_accounts FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.support_messages FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE ALL PRIVILEGES ON TABLE public.support_tickets FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.app_role() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.apply_subscription_billing_record(uuid,integer) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.booking_append_audit() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.cancel_salon_subscription_renewal(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.deactivate_device_token(text) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.demote_other_main_images() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.effective_duration(uuid,uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.enqueue_booking_email() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.enqueue_verified_payment_receipt() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.erase_profile_references(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.get_active_tokens(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.get_available_slots(uuid,date,integer) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.get_salon_by_qr(text) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_audit_immutable() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_booking_against_closure() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_booking_checkout() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_booking_payment_columns() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_booking_salon_approval() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_collection_snapshot() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_media_reference() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_salon_approval() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_salon_discovery_placement() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_salon_display_priority() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.guard_subscription_admin() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.is_super_admin() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.owns_salon(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.payment_append_audit() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.payout_account_snapshot(public.salon_payout_accounts) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.recompute_booking_payment_state(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.recompute_salon_trial(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.register_device_token(text,text,text) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.salon_booking_eligible(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.salon_payout_account_masked(uuid) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.salon_trial_setting(text,integer,integer,integer) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.set_audit_actor() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.set_updated_at() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.stamp_booking_lifecycle() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.stamp_checkout_policy() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.stamp_notification_read_at() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.start_salon_trial(uuid,timestamp with time zone) FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.sweep_lapsed_subscriptions() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_booking_payments_guard() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_booking_payments_recompute() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_bookings_recompute_trial() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_payment_refunds_guard() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_payment_refunds_recompute() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_salon_payout_account_history() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_salons_access_row() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
REVOKE EXECUTE ON FUNCTION public.tg_subscription_billing_guard() FROM PUBLIC, anon, authenticated RESTRICT;
-- statement --
DO $review$
DECLARE retained jsonb;
BEGIN
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges SELECT'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges INSERT'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges DELETE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_challenges', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_challenges MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_challenges', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_challenges MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests SELECT'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests INSERT'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests DELETE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.account_deletion_requests', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.account_deletion_requests MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.account_deletion_requests', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.account_deletion_requests MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version SELECT'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version INSERT'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version DELETE'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.alembic_version', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.alembic_version MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.alembic_version', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.alembic_version MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits SELECT'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits INSERT'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits DELETE'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.api_rate_limits', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.api_rate_limits MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.api_rate_limits', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.api_rate_limits MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots SELECT'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots INSERT'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots DELETE'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.blocked_slots', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.blocked_slots MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.blocked_slots', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.blocked_slots MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests SELECT'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests INSERT'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests DELETE'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.booking_action_requests', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_action_requests MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_action_requests', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_action_requests MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events SELECT'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events INSERT'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events DELETE'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.booking_audit_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_audit_events MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_audit_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_audit_events MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments SELECT'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments INSERT'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments DELETE'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.booking_payments', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_payments MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_payments', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_payments MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services SELECT'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services INSERT'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services DELETE'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.booking_services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.booking_services MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.booking_services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.booking_services MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings SELECT'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings INSERT'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings DELETE'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.bookings', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.bookings MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.bookings', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.bookings MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions SELECT'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions INSERT'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions DELETE'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.customer_booking_restrictions', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.customer_booking_restrictions MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.customer_booking_restrictions', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.customer_booking_restrictions MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens SELECT'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens INSERT'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens DELETE'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.device_tokens', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.device_tokens MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.device_tokens', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.device_tokens MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events SELECT'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events INSERT'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events DELETE'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.email_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.email_events MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.email_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.email_events MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages SELECT'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages INSERT'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages DELETE'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.languages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.languages MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.languages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.languages MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries SELECT'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries INSERT'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries DELETE'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.notification_deliveries', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_deliveries MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_deliveries', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_deliveries MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox SELECT'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox INSERT'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox DELETE'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.notification_outbox', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notification_outbox MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.notification_outbox', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notification_outbox MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications SELECT'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications INSERT'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications DELETE'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.notifications', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.notifications MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.notifications', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.notifications MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_anomalies', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_anomalies MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_anomalies', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_anomalies MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_idempotency_keys', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_idempotency_keys MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_idempotency_keys', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_idempotency_keys MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_account_audit', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_account_audit MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_account_audit', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_account_audit MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_provider_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_provider_accounts MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_provider_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_provider_accounts MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_refunds', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_refunds MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_refunds', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_refunds MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events SELECT'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events INSERT'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events DELETE'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.payment_webhook_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.payment_webhook_events MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.payment_webhook_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.payment_webhook_events MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles SELECT'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles INSERT'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles DELETE'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.profiles', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.profiles MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.profiles', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.profiles MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_access', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_access MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_access', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_access MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_holidays', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_holidays MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_holidays', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_holidays MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_images', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_images MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_images', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_images MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_account_history', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_account_history MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_account_history', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_account_history MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_payout_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_payout_accounts MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_payout_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_payout_accounts MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_reports', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_reports MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_reports', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_reports MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salon_subscriptions', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salon_subscriptions MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salon_subscriptions', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salon_subscriptions MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons SELECT'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons INSERT'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons DELETE'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.salons', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.salons MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.salons', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.salons MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories SELECT'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories INSERT'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories DELETE'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.service_categories', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_categories MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.service_categories', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_categories MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories SELECT'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories INSERT'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories DELETE'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.service_subcategories', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.service_subcategories MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.service_subcategories', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.service_subcategories MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services SELECT'; END IF;
    IF has_table_privilege('anon', 'public.services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services INSERT'; END IF;
    IF has_table_privilege('anon', 'public.services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services DELETE'; END IF;
    IF has_table_privilege('anon', 'public.services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.services MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.services MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff SELECT'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff INSERT'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff DELETE'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.staff', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.staff', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages SELECT'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages INSERT'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages DELETE'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.staff_service_languages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_service_languages MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_service_languages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_service_languages MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services SELECT'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services INSERT'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services DELETE'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.staff_services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.staff_services MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.staff_services', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.staff_services MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records SELECT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records INSERT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records DELETE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.subscription_billing_records', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_billing_records MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_billing_records', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_billing_records MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events SELECT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events INSERT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events DELETE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.subscription_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_events MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_events', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_events MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans SELECT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans INSERT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans DELETE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.subscription_plans', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_plans MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_plans', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_plans MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts SELECT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts INSERT'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts DELETE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.subscription_provider_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.subscription_provider_accounts MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.subscription_provider_accounts', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.subscription_provider_accounts MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages SELECT'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages INSERT'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages DELETE'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.support_messages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_messages MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.support_messages', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_messages MAINTAIN'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets SELECT'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets INSERT'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets UPDATE'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets DELETE'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets TRUNCATE'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets REFERENCES'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets TRIGGER'; END IF;
    IF has_table_privilege('anon', 'public.support_tickets', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: anon public.support_tickets MAINTAIN'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'SELECT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets SELECT'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'INSERT') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets INSERT'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'UPDATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets UPDATE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'DELETE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets DELETE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'TRUNCATE') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets TRUNCATE'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'REFERENCES') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets REFERENCES'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'TRIGGER') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets TRIGGER'; END IF;
    IF has_table_privilege('authenticated', 'public.support_tickets', 'MAINTAIN') THEN RAISE EXCEPTION 'Effective client privilege remains: authenticated public.support_tickets MAINTAIN'; END IF;
    IF has_function_privilege('anon', 'public.app_role()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.app_role()'; END IF;
    IF has_function_privilege('authenticated', 'public.app_role()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.app_role()'; END IF;
    IF has_function_privilege('anon', 'public.apply_subscription_billing_record(uuid,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.apply_subscription_billing_record(uuid,integer)'; END IF;
    IF has_function_privilege('authenticated', 'public.apply_subscription_billing_record(uuid,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.apply_subscription_billing_record(uuid,integer)'; END IF;
    IF has_function_privilege('anon', 'public.booking_append_audit()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.booking_append_audit()'; END IF;
    IF has_function_privilege('authenticated', 'public.booking_append_audit()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.booking_append_audit()'; END IF;
    IF has_function_privilege('anon', 'public.cancel_salon_subscription_renewal(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.cancel_salon_subscription_renewal(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.cancel_salon_subscription_renewal(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.cancel_salon_subscription_renewal(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)'; END IF;
    IF has_function_privilege('authenticated', 'public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.create_booking(uuid,uuid,uuid[],timestamp with time zone,text,text,public.booking_source,text)'; END IF;
    IF has_function_privilege('anon', 'public.deactivate_device_token(text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.deactivate_device_token(text)'; END IF;
    IF has_function_privilege('authenticated', 'public.deactivate_device_token(text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.deactivate_device_token(text)'; END IF;
    IF has_function_privilege('anon', 'public.demote_other_main_images()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.demote_other_main_images()'; END IF;
    IF has_function_privilege('authenticated', 'public.demote_other_main_images()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.demote_other_main_images()'; END IF;
    IF has_function_privilege('anon', 'public.effective_duration(uuid,uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.effective_duration(uuid,uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.effective_duration(uuid,uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.effective_duration(uuid,uuid)'; END IF;
    IF has_function_privilege('anon', 'public.enqueue_booking_email()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.enqueue_booking_email()'; END IF;
    IF has_function_privilege('authenticated', 'public.enqueue_booking_email()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.enqueue_booking_email()'; END IF;
    IF has_function_privilege('anon', 'public.enqueue_verified_payment_receipt()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.enqueue_verified_payment_receipt()'; END IF;
    IF has_function_privilege('authenticated', 'public.enqueue_verified_payment_receipt()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.enqueue_verified_payment_receipt()'; END IF;
    IF has_function_privilege('anon', 'public.erase_profile_references(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.erase_profile_references(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.erase_profile_references(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.erase_profile_references(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.get_active_tokens(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.get_active_tokens(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.get_active_tokens(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.get_active_tokens(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.get_available_slots(uuid,date,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.get_available_slots(uuid,date,integer)'; END IF;
    IF has_function_privilege('authenticated', 'public.get_available_slots(uuid,date,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.get_available_slots(uuid,date,integer)'; END IF;
    IF has_function_privilege('anon', 'public.get_salon_by_qr(text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.get_salon_by_qr(text)'; END IF;
    IF has_function_privilege('authenticated', 'public.get_salon_by_qr(text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.get_salon_by_qr(text)'; END IF;
    IF has_function_privilege('anon', 'public.guard_audit_immutable()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_audit_immutable()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_audit_immutable()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_audit_immutable()'; END IF;
    IF has_function_privilege('anon', 'public.guard_booking_against_closure()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_booking_against_closure()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_booking_against_closure()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_booking_against_closure()'; END IF;
    IF has_function_privilege('anon', 'public.guard_booking_checkout()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_booking_checkout()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_booking_checkout()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_booking_checkout()'; END IF;
    IF has_function_privilege('anon', 'public.guard_booking_payment_columns()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_booking_payment_columns()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_booking_payment_columns()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_booking_payment_columns()'; END IF;
    IF has_function_privilege('anon', 'public.guard_booking_salon_approval()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_booking_salon_approval()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_booking_salon_approval()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_booking_salon_approval()'; END IF;
    IF has_function_privilege('anon', 'public.guard_collection_snapshot()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_collection_snapshot()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_collection_snapshot()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_collection_snapshot()'; END IF;
    IF has_function_privilege('anon', 'public.guard_media_reference()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_media_reference()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_media_reference()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_media_reference()'; END IF;
    IF has_function_privilege('anon', 'public.guard_salon_approval()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_salon_approval()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_salon_approval()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_salon_approval()'; END IF;
    IF has_function_privilege('anon', 'public.guard_salon_discovery_placement()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_salon_discovery_placement()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_salon_discovery_placement()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_salon_discovery_placement()'; END IF;
    IF has_function_privilege('anon', 'public.guard_salon_display_priority()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_salon_display_priority()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_salon_display_priority()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_salon_display_priority()'; END IF;
    IF has_function_privilege('anon', 'public.guard_subscription_admin()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.guard_subscription_admin()'; END IF;
    IF has_function_privilege('authenticated', 'public.guard_subscription_admin()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.guard_subscription_admin()'; END IF;
    IF has_function_privilege('anon', 'public.handle_new_user()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.handle_new_user()'; END IF;
    IF has_function_privilege('authenticated', 'public.handle_new_user()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.handle_new_user()'; END IF;
    IF has_function_privilege('anon', 'public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)'; END IF;
    IF has_function_privilege('authenticated', 'public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.is_subscription_promotion_active(public.subscription_status,timestamp with time zone,timestamp with time zone,timestamp with time zone,timestamp with time zone)'; END IF;
    IF has_function_privilege('anon', 'public.is_super_admin()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.is_super_admin()'; END IF;
    IF has_function_privilege('authenticated', 'public.is_super_admin()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.is_super_admin()'; END IF;
    IF has_function_privilege('anon', 'public.owns_salon(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.owns_salon(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.owns_salon(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.owns_salon(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.payment_append_audit()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.payment_append_audit()'; END IF;
    IF has_function_privilege('authenticated', 'public.payment_append_audit()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.payment_append_audit()'; END IF;
    IF has_function_privilege('anon', 'public.payout_account_snapshot(public.salon_payout_accounts)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.payout_account_snapshot(public.salon_payout_accounts)'; END IF;
    IF has_function_privilege('authenticated', 'public.payout_account_snapshot(public.salon_payout_accounts)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.payout_account_snapshot(public.salon_payout_accounts)'; END IF;
    IF has_function_privilege('anon', 'public.recompute_booking_payment_state(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.recompute_booking_payment_state(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.recompute_booking_payment_state(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.recompute_booking_payment_state(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.recompute_salon_trial(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.recompute_salon_trial(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.recompute_salon_trial(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.recompute_salon_trial(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.register_device_token(text,text,text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.register_device_token(text,text,text)'; END IF;
    IF has_function_privilege('authenticated', 'public.register_device_token(text,text,text)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.register_device_token(text,text,text)'; END IF;
    IF has_function_privilege('anon', 'public.salon_booking_eligible(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.salon_booking_eligible(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.salon_booking_eligible(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.salon_booking_eligible(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.salon_payout_account_masked(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.salon_payout_account_masked(uuid)'; END IF;
    IF has_function_privilege('authenticated', 'public.salon_payout_account_masked(uuid)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.salon_payout_account_masked(uuid)'; END IF;
    IF has_function_privilege('anon', 'public.salon_trial_setting(text,integer,integer,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.salon_trial_setting(text,integer,integer,integer)'; END IF;
    IF has_function_privilege('authenticated', 'public.salon_trial_setting(text,integer,integer,integer)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.salon_trial_setting(text,integer,integer,integer)'; END IF;
    IF has_function_privilege('anon', 'public.set_audit_actor()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.set_audit_actor()'; END IF;
    IF has_function_privilege('authenticated', 'public.set_audit_actor()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.set_audit_actor()'; END IF;
    IF has_function_privilege('anon', 'public.set_updated_at()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.set_updated_at()'; END IF;
    IF has_function_privilege('authenticated', 'public.set_updated_at()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.set_updated_at()'; END IF;
    IF has_function_privilege('anon', 'public.stamp_booking_lifecycle()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.stamp_booking_lifecycle()'; END IF;
    IF has_function_privilege('authenticated', 'public.stamp_booking_lifecycle()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.stamp_booking_lifecycle()'; END IF;
    IF has_function_privilege('anon', 'public.stamp_checkout_policy()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.stamp_checkout_policy()'; END IF;
    IF has_function_privilege('authenticated', 'public.stamp_checkout_policy()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.stamp_checkout_policy()'; END IF;
    IF has_function_privilege('anon', 'public.stamp_notification_read_at()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.stamp_notification_read_at()'; END IF;
    IF has_function_privilege('authenticated', 'public.stamp_notification_read_at()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.stamp_notification_read_at()'; END IF;
    IF has_function_privilege('anon', 'public.start_salon_trial(uuid,timestamp with time zone)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.start_salon_trial(uuid,timestamp with time zone)'; END IF;
    IF has_function_privilege('authenticated', 'public.start_salon_trial(uuid,timestamp with time zone)', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.start_salon_trial(uuid,timestamp with time zone)'; END IF;
    IF has_function_privilege('anon', 'public.sweep_lapsed_subscriptions()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.sweep_lapsed_subscriptions()'; END IF;
    IF has_function_privilege('authenticated', 'public.sweep_lapsed_subscriptions()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.sweep_lapsed_subscriptions()'; END IF;
    IF has_function_privilege('anon', 'public.tg_booking_payments_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_booking_payments_guard()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_booking_payments_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_booking_payments_guard()'; END IF;
    IF has_function_privilege('anon', 'public.tg_booking_payments_recompute()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_booking_payments_recompute()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_booking_payments_recompute()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_booking_payments_recompute()'; END IF;
    IF has_function_privilege('anon', 'public.tg_bookings_recompute_trial()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_bookings_recompute_trial()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_bookings_recompute_trial()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_bookings_recompute_trial()'; END IF;
    IF has_function_privilege('anon', 'public.tg_payment_refunds_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_payment_refunds_guard()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_payment_refunds_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_payment_refunds_guard()'; END IF;
    IF has_function_privilege('anon', 'public.tg_payment_refunds_recompute()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_payment_refunds_recompute()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_payment_refunds_recompute()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_payment_refunds_recompute()'; END IF;
    IF has_function_privilege('anon', 'public.tg_salon_payout_account_history()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_salon_payout_account_history()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_salon_payout_account_history()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_salon_payout_account_history()'; END IF;
    IF has_function_privilege('anon', 'public.tg_salons_access_row()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_salons_access_row()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_salons_access_row()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_salons_access_row()'; END IF;
    IF has_function_privilege('anon', 'public.tg_subscription_billing_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: anon public.tg_subscription_billing_guard()'; END IF;
    IF has_function_privilege('authenticated', 'public.tg_subscription_billing_guard()', 'EXECUTE') THEN RAISE EXCEPTION 'Effective client execute remains: authenticated public.tg_subscription_billing_guard()'; END IF;

    FOR retained IN SELECT value FROM jsonb_array_elements(
        current_setting('mumbai_review.server_effective_before')::jsonb)
    LOOP
        IF NOT (CASE retained->>'kind'
            WHEN 'table' THEN has_table_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            WHEN 'sequence' THEN has_sequence_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            WHEN 'function' THEN has_function_privilege(retained->>'role', retained->>'object', retained->>'privilege')
            ELSE false END) THEN
            RAISE EXCEPTION 'Retained effective server access was lost: %', retained;
        END IF;
    END LOOP;
END
$review$;

ROLLBACK;
DO $verify$ BEGIN IF md5(jsonb_build_object(
 'application', (select jsonb_build_object(
 'tables',(select jsonb_object_agg(c.relname,jsonb_build_object('rls',c.relrowsecurity,'replica_identity',c.relreplident)) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r'),
 'columns',(select jsonb_object_agg(c.relname||'.'||a.attname,jsonb_build_object('type',format_type(a.atttypid,a.atttypmod),'not_null',a.attnotnull,'default',pg_get_expr(d.adbin,d.adrelid),'generated',a.attgenerated,'identity',a.attidentity)) from pg_attribute a join pg_class c on c.oid=a.attrelid join pg_namespace n on n.oid=c.relnamespace left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where n.nspname='public' and c.relkind='r' and a.attnum>0 and not a.attisdropped),
 'constraints',(select jsonb_object_agg(c.relname||'.'||k.conname,pg_get_constraintdef(k.oid)) from pg_constraint k join pg_class c on c.oid=k.conrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'),
 'indexes',(select jsonb_object_agg(indexname,indexdef) from pg_indexes where schemaname='public'),
 'functions',(select jsonb_object_agg(p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',jsonb_build_object('body',p.prosrc,'result',pg_get_function_result(p.oid),'language',l.lanname,'volatility',p.provolatile,'security_definer',p.prosecdef,'config',p.proconfig)) from pg_proc p join pg_namespace n on n.oid=p.pronamespace join pg_language l on l.oid=p.prolang where n.nspname='public' and not exists(select 1 from pg_depend d where d.classid='pg_proc'::regclass and d.objid=p.oid and d.deptype='e')),
 'triggers',(select jsonb_object_agg(n.nspname||'.'||c.relname||'.'||t.tgname,pg_get_triggerdef(t.oid)) from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where not t.tgisinternal and (n.nspname='public' or (n.nspname='auth' and c.relname='users'))),
 'policies',(select jsonb_object_agg(tablename||'.'||policyname,jsonb_build_object('cmd',cmd,'roles',roles,'permissive',permissive,'using',qual,'check',with_check)) from pg_policies where schemaname='public'),
 'enums',(select jsonb_object_agg(typname,labels) from (select t.typname,jsonb_agg(e.enumlabel order by e.enumsortorder) labels from pg_type t join pg_namespace n on n.oid=t.typnamespace join pg_enum e on e.enumtypid=t.oid where n.nspname='public' group by t.typname)x)
)),
 'relation_acls',(SELECT jsonb_agg(jsonb_build_object('oid',c.oid,'acl',c.relacl,'owner',c.relowner) ORDER BY c.oid)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'function_acls',(SELECT jsonb_agg(jsonb_build_object('oid',p.oid,'acl',p.proacl,'owner',p.proowner,'config',p.proconfig) ORDER BY p.oid)
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'column_acls',(SELECT jsonb_agg(jsonb_build_object('table',a.attrelid,'num',a.attnum,'acl',a.attacl) ORDER BY a.attrelid,a.attnum)
    FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
 'schema_acls',(SELECT jsonb_agg(jsonb_build_object('oid',oid,'owner',nspowner,'acl',nspacl) ORDER BY oid) FROM pg_namespace),
 'defaults',(SELECT jsonb_agg(to_jsonb(d) ORDER BY d.oid) FROM pg_default_acl d),
 'memberships',(SELECT jsonb_agg(to_jsonb(m) ORDER BY m.roleid,m.member,m.grantor) FROM pg_auth_members m),
 'alembic',(SELECT coalesce(jsonb_agg(version_num),'[]'::jsonb) FROM public.alembic_version),
 'auth_count',(SELECT count(*) FROM auth.users),
 'profiles',(SELECT count(*) FROM public.profiles),
 'bookings',(SELECT count(*) FROM public.bookings)
)::text) IS DISTINCT FROM current_setting('mumbai_preflight.before_hash') THEN RAISE EXCEPTION 'Rollback fingerprint mismatch'; END IF; END $verify$;
SELECT 'passed' AS rollback_fingerprint, count(*) AS alembic_rows FROM public.alembic_version;
