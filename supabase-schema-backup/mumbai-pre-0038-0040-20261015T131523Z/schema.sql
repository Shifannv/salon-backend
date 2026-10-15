--
-- PostgreSQL database dump
--

\restrict WDMI3oL7KWgzb7CbfJESqKmw6pnBH9FLLVWR4IZ82l4x3EvAuuTUiqwRMYK8DFK

-- Dumped from database version 17.11
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "auth";


ALTER SCHEMA "auth" OWNER TO "supabase_admin";

--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA "extensions";


ALTER SCHEMA "extensions" OWNER TO "postgres";

--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "graphql";


ALTER SCHEMA "graphql" OWNER TO "supabase_admin";

--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "graphql_public";


ALTER SCHEMA "graphql_public" OWNER TO "supabase_admin";

--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: pgbouncer
--

CREATE SCHEMA "pgbouncer";


ALTER SCHEMA "pgbouncer" OWNER TO "pgbouncer";

--
-- Name: SCHEMA "public"; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA "public" IS 'standard public schema';


--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "realtime";


ALTER SCHEMA "realtime" OWNER TO "supabase_admin";

--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "storage";


ALTER SCHEMA "storage" OWNER TO "supabase_admin";

--
-- Name: supabase_migrations; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA "supabase_migrations";


ALTER SCHEMA "supabase_migrations" OWNER TO "postgres";

--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA "vault";


ALTER SCHEMA "vault" OWNER TO "supabase_admin";

--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "btree_gist" WITH SCHEMA "public";


--
-- Name: EXTENSION "btree_gist"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "btree_gist" IS 'support for indexing common datatypes in GiST';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";


--
-- Name: EXTENSION "pg_stat_statements"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "pg_stat_statements" IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";


--
-- Name: EXTENSION "pgcrypto"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "pgcrypto" IS 'cryptographic functions';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";


--
-- Name: EXTENSION "supabase_vault"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "supabase_vault" IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."aal_level" AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


ALTER TYPE "auth"."aal_level" OWNER TO "supabase_auth_admin";

--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."code_challenge_method" AS ENUM (
    's256',
    'plain'
);


ALTER TYPE "auth"."code_challenge_method" OWNER TO "supabase_auth_admin";

--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."factor_status" AS ENUM (
    'unverified',
    'verified'
);


ALTER TYPE "auth"."factor_status" OWNER TO "supabase_auth_admin";

--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."factor_type" AS ENUM (
    'totp',
    'webauthn',
    'phone',
    'recovery_code'
);


ALTER TYPE "auth"."factor_type" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_authorization_status; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."oauth_authorization_status" AS ENUM (
    'pending',
    'approved',
    'denied',
    'expired'
);


ALTER TYPE "auth"."oauth_authorization_status" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_client_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."oauth_client_type" AS ENUM (
    'public',
    'confidential'
);


ALTER TYPE "auth"."oauth_client_type" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_registration_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."oauth_registration_type" AS ENUM (
    'dynamic',
    'manual'
);


ALTER TYPE "auth"."oauth_registration_type" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_response_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."oauth_response_type" AS ENUM (
    'code'
);


ALTER TYPE "auth"."oauth_response_type" OWNER TO "supabase_auth_admin";

--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE "auth"."one_time_token_type" AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


ALTER TYPE "auth"."one_time_token_type" OWNER TO "supabase_auth_admin";

--
-- Name: approval_mode; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."approval_mode" AS ENUM (
    'auto',
    'manual'
);


ALTER TYPE "public"."approval_mode" OWNER TO "postgres";

--
-- Name: booking_source; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."booking_source" AS ENUM (
    'app',
    'manual_walkin',
    'qr_walkin'
);


ALTER TYPE "public"."booking_source" OWNER TO "postgres";

--
-- Name: booking_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."booking_status" AS ENUM (
    'pending',
    'confirmed',
    'rejected',
    'completed',
    'cancelled',
    'checked_in',
    'no_show'
);


ALTER TYPE "public"."booking_status" OWNER TO "postgres";

--
-- Name: payment_method; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."payment_method" AS ENUM (
    'cash',
    'online'
);


ALTER TYPE "public"."payment_method" OWNER TO "postgres";

--
-- Name: payment_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."payment_status" AS ENUM (
    'unpaid',
    'paid'
);


ALTER TYPE "public"."payment_status" OWNER TO "postgres";

--
-- Name: salon_approval_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."salon_approval_status" AS ENUM (
    'pending',
    'approved',
    'rejected'
);


ALTER TYPE "public"."salon_approval_status" OWNER TO "postgres";

--
-- Name: subscription_event_processing_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."subscription_event_processing_status" AS ENUM (
    'received',
    'processing',
    'processed',
    'failed'
);


ALTER TYPE "public"."subscription_event_processing_status" OWNER TO "postgres";

--
-- Name: subscription_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."subscription_status" AS ENUM (
    'pending',
    'trialing',
    'active',
    'past_due',
    'cancelled',
    'expired',
    'suspended'
);


ALTER TYPE "public"."subscription_status" OWNER TO "postgres";

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE "public"."user_role" AS ENUM (
    'super_admin',
    'owner',
    'staff',
    'customer'
);


ALTER TYPE "public"."user_role" OWNER TO "postgres";

--
-- Name: action; Type: TYPE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TYPE "realtime"."action" AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


ALTER TYPE "realtime"."action" OWNER TO "supabase_realtime_admin";

--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TYPE "realtime"."equality_op" AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in',
    'like',
    'ilike',
    'is',
    'match',
    'imatch',
    'isdistinct'
);


ALTER TYPE "realtime"."equality_op" OWNER TO "supabase_realtime_admin";

--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TYPE "realtime"."user_defined_filter" AS (
	"column_name" "text",
	"op" "realtime"."equality_op",
	"value" "text",
	"negate" boolean
);


ALTER TYPE "realtime"."user_defined_filter" OWNER TO "supabase_realtime_admin";

--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TYPE "realtime"."wal_column" AS (
	"name" "text",
	"type_name" "text",
	"type_oid" "oid",
	"value" "jsonb",
	"is_pkey" boolean,
	"is_selectable" boolean
);


ALTER TYPE "realtime"."wal_column" OWNER TO "supabase_realtime_admin";

--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TYPE "realtime"."wal_rls" AS (
	"wal" "jsonb",
	"is_rls_enabled" boolean,
	"subscription_ids" "uuid"[],
	"errors" "text"[]
);


ALTER TYPE "realtime"."wal_rls" OWNER TO "supabase_realtime_admin";

--
-- Name: buckettype; Type: TYPE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TYPE "storage"."buckettype" AS ENUM (
    'STANDARD',
    'ANALYTICS',
    'VECTOR'
);


ALTER TYPE "storage"."buckettype" OWNER TO "supabase_storage_admin";

--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION "auth"."email"() RETURNS "text"
    LANGUAGE "sql" STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


ALTER FUNCTION "auth"."email"() OWNER TO "supabase_auth_admin";

--
-- Name: FUNCTION "email"(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION "auth"."email"() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';


--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION "auth"."jwt"() RETURNS "jsonb"
    LANGUAGE "sql" STABLE
    AS $$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


ALTER FUNCTION "auth"."jwt"() OWNER TO "supabase_auth_admin";

--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION "auth"."role"() RETURNS "text"
    LANGUAGE "sql" STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


ALTER FUNCTION "auth"."role"() OWNER TO "supabase_auth_admin";

--
-- Name: FUNCTION "role"(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION "auth"."role"() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION "auth"."uid"() RETURNS "uuid"
    LANGUAGE "sql" STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


ALTER FUNCTION "auth"."uid"() OWNER TO "supabase_auth_admin";

--
-- Name: FUNCTION "uid"(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION "auth"."uid"() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."grant_pg_cron_access"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
    revoke trigger on cron.job_run_details from postgres;
  END IF;
END;
$$;


ALTER FUNCTION "extensions"."grant_pg_cron_access"() OWNER TO "supabase_admin";

--
-- Name: FUNCTION "grant_pg_cron_access"(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION "extensions"."grant_pg_cron_access"() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."grant_pg_graphql_access"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $_$
begin
    if not exists (
        select 1
        from pg_catalog.pg_event_trigger_ddl_commands() ev
        join pg_catalog.pg_extension e on ev.objid = e.oid
        where e.extname = 'pg_graphql'
    ) then
        return;
    end if;

    drop function if exists graphql_public.graphql;
    create or replace function graphql_public.graphql(
        "operationName" text default null,
        query text default null,
        variables jsonb default null,
        extensions jsonb default null
    )
        returns jsonb
        language sql
    as $$
        select graphql.resolve(
            query := query,
            variables := coalesce(variables, '{}'),
            "operationName" := "operationName",
            extensions := extensions
        );
    $$;

    -- Attach the wrapper to the extension so DROP EXTENSION cascades to it,
    -- which in turn triggers set_graphql_placeholder to reinstall the "not enabled" stub.
    alter extension pg_graphql add function graphql_public.graphql(text, text, jsonb, jsonb);

    grant usage on schema graphql to postgres, anon, authenticated, service_role;
    grant execute on function graphql.resolve to postgres, anon, authenticated, service_role;
    grant usage on schema graphql to postgres with grant option;
    grant usage on schema graphql_public to postgres with grant option;
end;
$_$;


ALTER FUNCTION "extensions"."grant_pg_graphql_access"() OWNER TO "supabase_admin";

--
-- Name: FUNCTION "grant_pg_graphql_access"(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION "extensions"."grant_pg_graphql_access"() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."grant_pg_net_access"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    IF EXISTS (
      SELECT FROM pg_extension
      WHERE extname = 'pg_net'
      -- all versions in use on existing projects as of 2025-02-20
      -- version 0.12.0 onwards don't need these applied
      AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8.0', '0.10.0', '0.11.0')
    ) THEN
      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

      ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
      ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

      REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
      REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

      GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION "extensions"."grant_pg_net_access"() OWNER TO "supabase_admin";

--
-- Name: FUNCTION "grant_pg_net_access"(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION "extensions"."grant_pg_net_access"() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."pgrst_ddl_watch"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


ALTER FUNCTION "extensions"."pgrst_ddl_watch"() OWNER TO "supabase_admin";

--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."pgrst_drop_watch"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


ALTER FUNCTION "extensions"."pgrst_drop_watch"() OWNER TO "supabase_admin";

--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION "extensions"."set_graphql_placeholder"() RETURNS "event_trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
            set search_path to ''
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


ALTER FUNCTION "extensions"."set_graphql_placeholder"() OWNER TO "supabase_admin";

--
-- Name: FUNCTION "set_graphql_placeholder"(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION "extensions"."set_graphql_placeholder"() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: graphql("text", "text", "jsonb", "jsonb"); Type: FUNCTION; Schema: graphql_public; Owner: supabase_admin
--

CREATE FUNCTION "graphql_public"."graphql"("operationName" "text" DEFAULT NULL::"text", "query" "text" DEFAULT NULL::"text", "variables" "jsonb" DEFAULT NULL::"jsonb", "extensions" "jsonb" DEFAULT NULL::"jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    AS $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;


ALTER FUNCTION "graphql_public"."graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb") OWNER TO "supabase_admin";

--
-- Name: get_auth("text"); Type: FUNCTION; Schema: pgbouncer; Owner: supabase_admin
--

CREATE FUNCTION "pgbouncer"."get_auth"("p_usename" "text") RETURNS TABLE("username" "text", "password" "text")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO ''
    AS $_$
  BEGIN
      RAISE DEBUG 'PgBouncer auth request: %', p_usename;

      RETURN QUERY
      SELECT
          rolname::text,
          CASE WHEN rolvaliduntil < now()
              THEN null
              ELSE rolpassword::text
          END
      FROM pg_authid
      WHERE rolname=$1 and rolcanlogin;
  END;
  $_$;


ALTER FUNCTION "pgbouncer"."get_auth"("p_usename" "text") OWNER TO "supabase_admin";

--
-- Name: app_role(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."app_role"() RETURNS "public"."user_role"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select role from profiles where id = auth.uid();
$$;


ALTER FUNCTION "public"."app_role"() OWNER TO "postgres";

--
-- Name: apply_subscription_billing_record("uuid", integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) RETURNS "text"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
declare
  v_rec     public.subscription_billing_records%rowtype;
  v_sub     public.salon_subscriptions%rowtype;
  v_owner   uuid;
  v_months  integer;
  v_now     timestamptz := now();
  v_base    timestamptz;
  v_start   timestamptz;
  v_end     timestamptz;
  v_grace   timestamptz;
  v_sub_id  uuid;
  v_outcome text;
begin
  if p_grace_days is null or p_grace_days < 0 then
    raise exception 'grace_days_required' using errcode = '22023';
  end if;
  select * into v_rec from public.subscription_billing_records where id = p_record_id;
  if not found then
    return 'not_found';
  end if;
  -- One writer per salon, then re-read the record under its row lock.
  perform pg_advisory_xact_lock(hashtextextended('subscription:' || v_rec.salon_id::text, 0));
  select * into v_rec from public.subscription_billing_records
  where id = p_record_id for update;
  if v_rec.applied_at is not null then
    return 'already_applied';
  end if;
  if v_rec.status not in ('paid', 'partially_refunded') then
    return 'not_paid';
  end if;
  select owner_id into v_owner from public.salons where id = v_rec.salon_id;
  if v_owner is null then
    return 'blocked_closed';
  end if;
  v_months := case v_rec.billing_interval
    when 'monthly' then 1 when 'quarterly' then 3 when 'semiannual' then 6 when 'yearly' then 12
  end;
  if v_months is null then
    raise exception 'unknown_billing_interval' using errcode = '22023';
  end if;

  perform set_config('app.subscription_system', 'on', true);
  select * into v_sub from public.salon_subscriptions
  where salon_id = v_rec.salon_id order by created_at desc, id desc limit 1 for update;

  if found and v_sub.status = 'suspended' then
    perform set_config('app.subscription_system', 'off', true);
    return 'blocked_suspended';
  end if;

  if found and (v_sub.status in ('pending', 'trialing', 'active', 'past_due')
                or (v_sub.status = 'cancelled' and v_sub.current_period_end > v_now)) then
    -- Renewal: extend the SAME row from its paid-through date (or from now when it lapsed).
    if v_sub.current_period_end is not null and v_sub.current_period_end > v_now then
      v_base := v_sub.current_period_end;
      v_start := coalesce(v_sub.current_period_start, v_now);
    else
      v_base := v_now;
      v_start := v_now;
    end if;
    v_end := v_base + make_interval(months => v_months);
    v_grace := v_end + make_interval(days => p_grace_days);
    v_outcome := case when v_sub.current_period_end is null then 'started' else 'renewed' end;
    update public.salon_subscriptions
    set plan_id = v_rec.plan_id, status = 'active',
        starts_at = coalesce(starts_at, v_start),
        current_period_start = v_start, current_period_end = v_end,
        cancelled_at = null, expires_at = null, grace_period_end = v_grace
    where id = v_sub.id;
    v_sub_id := v_sub.id;
  else
    v_base := v_now;
    v_start := v_now;
    v_end := v_now + make_interval(months => v_months);
    v_grace := v_end + make_interval(days => p_grace_days);
    v_outcome := 'started';
    insert into public.salon_subscriptions
      (salon_id, plan_id, status, starts_at, current_period_start, current_period_end,
       grace_period_end)
    values (v_rec.salon_id, v_rec.plan_id, 'active', v_now, v_start, v_end, v_grace)
    returning id into v_sub_id;
  end if;

  update public.subscription_billing_records
  set period_start = v_base, period_end = v_end, applied_at = v_now, subscription_id = v_sub_id
  where id = v_rec.id;
  perform set_config('app.subscription_system', 'off', true);
  return v_outcome;
end $$;


ALTER FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) OWNER TO "postgres";

--
-- Name: booking_append_audit(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."booking_append_audit"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  if tg_op = 'INSERT' or new.status is distinct from old.status then
    insert into public.booking_audit_events(booking_id, actor_id, event_type, old_state, new_state)
      values (new.id, auth.uid(), case when tg_op = 'INSERT' then 'booking_created' else 'booking_transition' end,
        case when tg_op = 'UPDATE' then old.status::text else null end, new.status::text);
  end if;
  return null;
end $$;


ALTER FUNCTION "public"."booking_append_audit"() OWNER TO "postgres";

--
-- Name: cancel_salon_subscription_renewal("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") RETURNS "text"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
declare
  v_sub public.salon_subscriptions%rowtype;
begin
  perform pg_advisory_xact_lock(hashtextextended('subscription:' || p_salon_id::text, 0));
  select * into v_sub from public.salon_subscriptions
  where salon_id = p_salon_id order by created_at desc, id desc limit 1 for update;
  if not found then
    return 'none';
  end if;
  if v_sub.status = 'cancelled' then
    return 'already_cancelled';
  end if;
  if v_sub.status in ('expired', 'suspended') then
    return 'not_cancellable';
  end if;
  perform set_config('app.subscription_system', 'on', true);
  update public.salon_subscriptions
  set status = 'cancelled', cancelled_at = now()
  where id = v_sub.id;
  perform set_config('app.subscription_system', 'off', true);
  return 'cancelled';
end $$;


ALTER FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") OWNER TO "postgres";

--
-- Name: create_booking("uuid", "uuid", "uuid"[], timestamp with time zone, "text", "text", "public"."booking_source", "text"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text" DEFAULT NULL::"text", "p_source" "public"."booking_source" DEFAULT 'app'::"public"."booking_source", "p_notes" "text" DEFAULT NULL::"text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
        declare
          v_duration int;
          v_price numeric(10,2);
          v_end timestamptz;
          v_mode approval_mode;
          v_status booking_status;
          v_customer uuid := auth.uid();
          v_tz text;
          v_booking uuid;
          v_accepting boolean;
        begin
          select timezone, approval_mode, accepting_bookings into v_tz, v_mode, v_accepting
          from salons where id = p_salon_id and is_active;

          if v_tz is null then
            raise exception 'Salon not found or inactive';
          end if;

          if not v_accepting then
            raise exception 'salon_not_accepting_bookings';
          end if;

          if exists (
            select 1 from salon_holidays
            where salon_id = p_salon_id
              and holiday_date = (p_start at time zone v_tz)::date
              and is_active
          ) then
            raise exception 'Salon is closed on this date';
          end if;

          if exists (
            select 1 from unnest(p_service_ids) sid
            where not exists (
              select 1 from staff_services ss
              join services sv on sv.id = ss.service_id
              where ss.staff_id = p_staff_id and ss.service_id = sid
                and ss.is_active and sv.salon_id = p_salon_id and sv.is_active
            )
          ) then
            raise exception 'One or more services are not offered by this staff member';
          end if;

          select sum(coalesce(ss.duration_minutes, sv.duration_minutes)),
                 sum(coalesce(ss.price_override, sv.price))
            into v_duration, v_price
          from services sv
          left join staff_services ss
            on ss.service_id = sv.id and ss.staff_id = p_staff_id and ss.is_active
          where sv.id = any(p_service_ids) and sv.is_active;

          if v_duration is null then
            raise exception 'No valid services selected';
          end if;

          v_end := p_start + make_interval(mins => v_duration);
          if p_start <= now() then
            raise exception 'Cannot book a slot in the past';
          end if;

          if not exists (
            select 1
            from get_available_slots(
              p_staff_id,
              (p_start at time zone v_tz)::date,
              v_duration
            ) g
            where g.slot_start = p_start
          ) then
            raise exception 'Selected slot is no longer available';
          end if;

          v_status := case
            when p_source in ('manual_walkin', 'qr_walkin') then 'confirmed'
            when v_mode = 'auto' then 'confirmed'
            else 'pending'
          end;

          insert into bookings (
            salon_id, staff_id, customer_id, customer_name, customer_phone,
            phone_verified, source, status, start_datetime, end_datetime,
            total_duration_minutes, total_price, notes, created_by
          ) values (
            p_salon_id, p_staff_id,
            case when p_source = 'manual_walkin' then null else v_customer end,
            p_customer_name, p_customer_phone,
            (p_source = 'qr_walkin' and v_customer is not null),
            p_source, v_status, p_start, v_end,
            v_duration, v_price, p_notes, v_customer
          )
          returning id into v_booking;

          insert into booking_services (
            booking_id, service_id, service_name, duration_minutes, price
          )
          select v_booking, sv.id, sv.name,
                 coalesce(ss.duration_minutes, sv.duration_minutes),
                 coalesce(ss.price_override, sv.price)
          from services sv
          left join staff_services ss
            on ss.service_id = sv.id and ss.staff_id = p_staff_id and ss.is_active
          where sv.id = any(p_service_ids);

          return v_booking;
        exception
          when exclusion_violation then
            raise exception 'That slot was just taken. Please pick another time.';
        end $$;


ALTER FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text") OWNER TO "postgres";

--
-- Name: deactivate_device_token("text"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."deactivate_device_token"("p_token" "text") RETURNS "void"
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  update device_tokens set is_active = false
  where token = p_token and user_id = auth.uid();
$$;


ALTER FUNCTION "public"."deactivate_device_token"("p_token" "text") OWNER TO "postgres";

--
-- Name: demote_other_main_images(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."demote_other_main_images"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if new.is_main then
    update salon_images set is_main = false
    where salon_id = new.salon_id and id <> new.id and is_main;
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."demote_other_main_images"() OWNER TO "postgres";

--
-- Name: effective_duration("uuid", "uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") RETURNS integer
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
  select coalesce(ss.duration_minutes, sv.duration_minutes)
  from services sv
  left join staff_services ss
    on ss.service_id = sv.id and ss.staff_id = p_staff_id and ss.is_active
  where sv.id = p_service_id;
$$;


ALTER FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") OWNER TO "postgres";

--
-- Name: enqueue_booking_email(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."enqueue_booking_email"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
            declare v_email text; v_event text;
            begin
              select email into v_email from public.profiles where id = new.customer_id;
              if v_email is null then return null; end if;
              if tg_op = 'INSERT' and new.status = 'confirmed' then v_event := 'booking_confirmation';
              elsif tg_op = 'UPDATE' and new.status is distinct from old.status then
                if new.status = 'confirmed' then v_event := 'booking_confirmation';
                elsif new.status in ('cancelled','rejected') then v_event := 'booking_cancellation'; end if;
              end if;
              if v_event is not null then
                insert into public.email_events(user_id,event_key,event_type,recipient,subject,body)
                  values (new.customer_id, v_event || ':' || new.id::text, v_event, v_email,
                    case when v_event = 'booking_confirmation' then 'Booking confirmed' else 'Booking cancelled' end,
                    case when v_event = 'booking_confirmation' then 'Your appointment has been confirmed.'
                      else 'Your appointment has been cancelled. Please check your bookings for details.' end)
                  on conflict (event_key) do nothing;
              end if;
              return null;
            end $$;


ALTER FUNCTION "public"."enqueue_booking_email"() OWNER TO "postgres";

--
-- Name: enqueue_verified_payment_receipt(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."enqueue_verified_payment_receipt"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
            declare v_email text;
            begin
              if new.channel <> 'gateway' or new.status <> 'captured' then return null; end if;
              if tg_op = 'UPDATE' and old.status = 'captured' then return null; end if;
              select email into v_email from public.profiles where id = new.payer_id;
              if v_email is not null then
                insert into public.email_events(user_id,event_key,event_type,recipient,subject,body)
                  values (new.payer_id,'payment_receipt:' || new.id::text,'payment_receipt',v_email,
                    'Payment received','Your online payment has been verified. Your receipt is available in your bookings.')
                  on conflict(event_key) do nothing;
              end if;
              return null;
            end $$;


ALTER FUNCTION "public"."enqueue_verified_payment_receipt"() OWNER TO "postgres";

--
-- Name: erase_profile_references("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."erase_profile_references"("p_user" "uuid") RETURNS integer
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_catalog'
    AS $_$
    declare
      fk record;
      touched integer := 0;
      n integer;
    begin
      perform set_config('app.account_erasure', 'on', true);
      for fk in
        select c.conrelid::regclass as tbl, a.attname as col
        from pg_constraint c
        join pg_attribute a
          on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
        where c.contype = 'f'
          and c.confrelid = 'public.profiles'::regclass
          and c.confdeltype in ('a', 'r')
          and array_length(c.conkey, 1) = 1
      loop
        execute format('update %s set %I = null where %I = $1', fk.tbl, fk.col, fk.col)
          using p_user;
        get diagnostics n = row_count;
        touched := touched + n;
      end loop;
      return touched;
    end $_$;


ALTER FUNCTION "public"."erase_profile_references"("p_user" "uuid") OWNER TO "postgres";

--
-- Name: get_active_tokens("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") RETURNS TABLE("token" "text", "platform" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select d.token, d.platform
  from device_tokens d
  join profiles p on p.id = d.user_id
  where d.user_id = p_user_id and d.is_active and p.is_active;
$$;


ALTER FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") OWNER TO "postgres";

--
-- Name: get_available_slots("uuid", "date", integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) RETURNS TABLE("slot_start" timestamp with time zone, "slot_end" timestamp with time zone)
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
        declare
          v_salon uuid;
          v_tz text;
          v_hours jsonb;
          v_dow text;
          v_open time;
          v_close time;
          v_cursor timestamptz;
          v_day_end timestamptz;
          v_try_end timestamptz;
        begin
          select sl.id, sl.timezone, coalesce(st.working_hours, sl.working_hours)
            into v_salon, v_tz, v_hours
          from staff st
          join salons sl on sl.id = st.salon_id
          where st.id = p_staff_id
            and st.is_active
            and sl.is_active
            and sl.profile_completed and sl.approval_status = 'approved'
            and sl.accepting_bookings and public.salon_booking_eligible(sl.id);

          if v_tz is null then return; end if;

          if exists (
            select 1 from salon_holidays
            where salon_id = v_salon
              and holiday_date = p_date
              and is_active
          ) then
            return;
          end if;

          v_dow := lower(to_char(p_date, 'dy'));
          if v_hours -> v_dow ->> 'open' is null then return; end if;

          v_open := (v_hours -> v_dow ->> 'open')::time;
          v_close := (v_hours -> v_dow ->> 'close')::time;
          v_cursor := (p_date + v_open) at time zone v_tz;
          v_day_end := (p_date + v_close) at time zone v_tz;

          while v_cursor + make_interval(mins => p_duration_minutes) <= v_day_end loop
            v_try_end := v_cursor + make_interval(mins => p_duration_minutes);
            if v_cursor > now()
               and not exists (
                 select 1 from bookings b
                 where b.staff_id = p_staff_id
                   and b.status in ('pending', 'confirmed', 'checked_in')
                   and tstzrange(b.start_datetime, b.end_datetime)
                       && tstzrange(v_cursor, v_try_end)
               )
               and not exists (
                 select 1 from blocked_slots bs
                 where (bs.staff_id = p_staff_id
                        or (bs.staff_id is null and bs.salon_id = v_salon))
                   and tstzrange(bs.start_datetime, bs.end_datetime)
                       && tstzrange(v_cursor, v_try_end)
               )
            then
              slot_start := v_cursor;
              slot_end := v_try_end;
              return next;
            end if;
            v_cursor := v_cursor + make_interval(mins => p_duration_minutes);
          end loop;
        end $$;


ALTER FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) OWNER TO "postgres";

--
-- Name: get_salon_by_qr("text"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") RETURNS TABLE("id" "uuid", "name" "text", "description" "text", "city" "text", "timezone" "text", "approval_mode" "public"."approval_mode")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select s.id, s.name, s.description, s.city, s.timezone, s.approval_mode
  from salons s
  where s.qr_token = p_qr_token
    and s.is_active
    and s.profile_completed and s.approval_status = 'approved';
$$;


ALTER FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") OWNER TO "postgres";

--
-- Name: guard_audit_immutable(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_audit_immutable"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  -- Scoped account erasure may anonymize ONLY the actor reference, preserving the event.
  if tg_op = 'UPDATE' and current_setting('app.account_erasure', true) = 'on'
    and new.actor_id is null and (to_jsonb(new) - 'actor_id') = (to_jsonb(old) - 'actor_id') then
    return new;
  end if;
  raise exception 'audit_event_is_immutable' using errcode = '23514';
end $$;


ALTER FUNCTION "public"."guard_audit_immutable"() OWNER TO "postgres";

--
-- Name: guard_booking_against_closure(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_booking_against_closure"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        declare
          v_timezone text;
        begin
          perform pg_advisory_xact_lock(hashtextextended(new.salon_id::text, 0));

          select timezone into v_timezone from salons where id = new.salon_id;
          if exists (
            select 1 from salon_holidays h
            where h.salon_id = new.salon_id
              and h.is_active
              and tstzrange(new.start_datetime, new.end_datetime, '[)')
                  && tstzrange(
                    (h.holiday_date + time '00:00') at time zone v_timezone,
                    (h.holiday_date + interval '1 day') at time zone v_timezone,
                    '[)'
                  )
          ) or exists (
            select 1 from blocked_slots bs
            where (bs.staff_id = new.staff_id
                   or (bs.staff_id is null and bs.salon_id = new.salon_id))
              and tstzrange(bs.start_datetime, bs.end_datetime, '[)')
                  && tstzrange(new.start_datetime, new.end_datetime, '[)')
          ) then
            raise exception 'Selected slot is closed by the salon';
          end if;
          return new;
        end $$;


ALTER FUNCTION "public"."guard_booking_against_closure"() OWNER TO "postgres";

--
-- Name: guard_booking_checkout(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_booking_checkout"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
declare v_block timestamptz;
begin
  if tg_op = 'INSERT' then
    -- Lock the shared salon trial before eligibility and before create_booking inserts.
    perform 1 from public.salon_access where salon_id = new.salon_id for update;
    if not public.salon_booking_eligible(new.salon_id) then
      raise exception 'salon_not_accepting_bookings' using errcode = '23514';
    end if;
    new.payment_preference := coalesce(nullif(current_setting('app.payment_preference', true), ''),
                                     new.payment_preference, 'pay_at_salon');
  end if;
  new.booking_calendar_date := (new.start_datetime at time zone 'Asia/Kolkata')::date;
  if new.customer_id is not null and new.payment_preference = 'pay_at_salon'
    and new.status in ('pending', 'confirmed', 'checked_in')
    and (tg_op = 'INSERT' or old.status not in ('pending','confirmed','checked_in')
         or new.payment_preference is distinct from old.payment_preference
         or new.start_datetime is distinct from old.start_datetime) then
    -- A per-customer transaction lock serializes different salons/days and no-show decisions.
    perform pg_advisory_xact_lock(hashtextextended(new.customer_id::text, 3715));
    select pay_at_salon_blocked_until into v_block from public.customer_booking_restrictions
      where customer_id = new.customer_id;
    if v_block > now() then
      raise exception 'pay_at_salon_temporarily_blocked' using errcode = '23514';
    end if;
    if exists (select 1 from public.bookings b where b.customer_id = new.customer_id
      and b.id <> new.id and b.booking_calendar_date = new.booking_calendar_date
      and b.payment_preference = 'pay_at_salon' and b.status in ('pending', 'confirmed', 'checked_in')) then
      raise exception 'pay_at_salon_daily_limit' using errcode = '23514';
    end if;
  end if;
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not ((old.status = 'pending' and new.status in ('confirmed','rejected','cancelled'))
      or (old.status = 'confirmed' and new.status in ('checked_in','completed','cancelled','no_show'))
      or (old.status = 'checked_in' and new.status in ('completed','cancelled','no_show'))) then
      raise exception 'booking_state_conflict' using errcode = '23514';
    end if;
    if new.status = 'completed' and new.payment_preference = 'pay_at_salon'
      and (new.payment_status <> 'paid' or not exists (
        select 1 from public.booking_payments p where p.booking_id = new.id
          and p.channel = 'manual' and p.status = 'captured'
      )) then
      raise exception 'payment_collection_required' using errcode = '23514';
    end if;
    if (new.status = 'no_show' or (new.status = 'cancelled'
          and new.cancellation_reason like 'Customer no-show%')) and new.customer_id is not null then
      if new.start_datetime > now() then
        raise exception 'no_show_before_appointment' using errcode = '23514';
      end if;
      perform pg_advisory_xact_lock(hashtextextended(new.customer_id::text, 3715));
      insert into public.customer_booking_restrictions(customer_id, no_show_count)
        values (new.customer_id, 1)
      on conflict (customer_id) do update set
        no_show_count = case when customer_booking_restrictions.pay_at_salon_blocked_until <= now()
          then 1 else customer_booking_restrictions.no_show_count + 1 end;
      update public.customer_booking_restrictions set pay_at_salon_blocked_until = now() + interval '7 days'
        where customer_id = new.customer_id and no_show_count >= 2;
    end if;
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."guard_booking_checkout"() OWNER TO "postgres";

--
-- Name: guard_booking_payment_columns(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_booking_payment_columns"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        begin
          if (new.payment_status is distinct from old.payment_status
              or new.payment_method is distinct from old.payment_method
              or new.paid_amount is distinct from old.paid_amount
              or new.refunded_amount is distinct from old.refunded_amount)
             and coalesce(current_setting('app.payment_recompute', true), '') <> 'on' then
            raise exception 'booking_payment_columns_are_derived' using errcode = '42501';
          end if;
          return new;
        end $$;


ALTER FUNCTION "public"."guard_booking_payment_columns"() OWNER TO "postgres";

--
-- Name: guard_booking_salon_approval(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_booking_salon_approval"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  perform 1 from salons where id = new.salon_id
    and is_active and profile_completed and approval_status = 'approved' for share;
  if not found then
    raise exception 'Salon is not approved for business' using errcode = '42501';
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."guard_booking_salon_approval"() OWNER TO "postgres";

--
-- Name: guard_collection_snapshot(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_collection_snapshot"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if tg_op = 'UPDATE' and (new.collection_method is distinct from old.collection_method
    or new.collected_by_owner is distinct from old.collected_by_owner
    or new.online_processing_charge is distinct from old.online_processing_charge
    or (new.recorded_by is distinct from old.recorded_by
        and not (coalesce(current_setting('app.account_erasure', true), '') = 'on' and new.recorded_by is null))
    or new.method is distinct from old.method and new.channel = 'manual') then
    raise exception 'payment_collection_snapshot_is_immutable' using errcode = '23514';
  end if;
  if tg_op = 'INSERT' and new.channel = 'manual' then
    new.collection_method := coalesce(new.collection_method,
      case when new.method = 'cash' then 'CASH' else 'UPI_DIRECT' end);
    new.collected_by_owner := exists(select 1 from public.salons s
      where s.id = new.salon_id and s.owner_id = new.recorded_by);
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."guard_collection_snapshot"() OWNER TO "postgres";

--
-- Name: guard_media_reference(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_media_reference"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'pg_catalog'
    AS $_$
        declare
          media_url text;
          previous_url text;
        begin
          media_url := to_jsonb(new) ->> tg_argv[0];
          if tg_op = 'UPDATE' then
            previous_url := to_jsonb(old) ->> tg_argv[0];
          end if;
          if media_url is null then return new; end if;
          if tg_table_name = 'profiles' and (
             media_url in ('avatar:curly', 'avatar:beard', 'avatar:geek') or
             media_url ~ '^__char__char-([1-9]|1[0-5])$'
          ) then return new; end if;
          perform pg_advisory_xact_lock(hashtextextended(media_url, 0));
          if media_url is distinct from previous_url and
             current_user in ('anon', 'authenticated') then
            raise exception 'Use the backend image upload API to assign media'
              using errcode = '42501';
          end if;
          return new;
        end;
        $_$;


ALTER FUNCTION "public"."guard_media_reference"() OWNER TO "postgres";

--
-- Name: guard_salon_approval(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_salon_approval"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if auth.uid() is null then
    -- Trusted migration/maintenance sessions have no authenticated actor.
    -- Data API roles must never bypass the guard by omitting their subject.
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated salon actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  if tg_op = 'INSERT' then
    if new.approval_status <> 'pending' or new.approved_at is not null
       or new.approved_by is not null or new.rejection_reason is not null then
      raise exception 'Super admin approval required' using errcode = '42501';
    end if;
  elsif row(new.approval_status, new.approved_at, new.approved_by, new.rejection_reason)
        is distinct from row(old.approval_status, old.approved_at,
                             old.approved_by, old.rejection_reason) then
    if not (old.owner_id = auth.uid() and new.owner_id = old.owner_id
            and old.approval_status = 'rejected' and new.approval_status = 'pending'
            and new.profile_completed and new.approved_at is null
            and new.approved_by is null and new.rejection_reason is null) then
      raise exception 'Super admin approval required' using errcode = '42501';
    end if;
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."guard_salon_approval"() OWNER TO "postgres";

--
-- Name: guard_salon_discovery_placement(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_salon_discovery_placement"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        begin
          if auth.uid() is null then
            if current_user in ('anon', 'authenticated') then
              raise exception 'Authenticated salon actor required' using errcode = '42501';
            end if;
            return new;
          end if;
          if is_super_admin() then return new; end if;
          if (tg_op = 'INSERT' and
               (new.discovery_visibility <> 'listed' or new.home_placement <> 'normal'))
             or (tg_op = 'UPDATE' and
               (new.discovery_visibility is distinct from old.discovery_visibility
                or new.home_placement is distinct from old.home_placement)) then
            raise exception 'Super admin required to change discovery placement'
              using errcode = '42501';
          end if;
          return new;
        end $$;


ALTER FUNCTION "public"."guard_salon_discovery_placement"() OWNER TO "postgres";

--
-- Name: guard_salon_display_priority(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_salon_display_priority"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if auth.uid() is null then
    -- Trusted migration/maintenance sessions have no authenticated actor.
    -- Data API roles must never bypass the guard by omitting their subject.
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated salon actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  if (tg_op = 'INSERT' and new.display_priority <> 0)
     or (tg_op = 'UPDATE' and new.display_priority is distinct from old.display_priority) then
    raise exception 'Super admin required to change display priority' using errcode = '42501';
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."guard_salon_display_priority"() OWNER TO "postgres";

--
-- Name: guard_subscription_admin(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."guard_subscription_admin"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if auth.uid() is null then
    if current_user in ('anon', 'authenticated') then
      raise exception 'Authenticated actor required' using errcode = '42501';
    end if;
    return new;
  end if;
  if is_super_admin() then return new; end if;
  -- The backend's own SQL functions (payment activation, cancel, lapse sweep) run on behalf
  -- of an owner. Never honoured for the browser-facing roles.
  if current_setting('app.subscription_system', true) = 'on'
     and current_user not in ('anon', 'authenticated') then
    return new;
  end if;
  raise exception 'Super admin required for subscription management'
    using errcode = '42501';
  return null;
end $$;


ALTER FUNCTION "public"."guard_subscription_admin"() OWNER TO "postgres";

--
-- Name: handle_new_user(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."handle_new_user"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
        begin
          insert into public.profiles (id, email, phone, full_name, avatar_url, role)
          values (
            new.id,
            new.email,
            new.phone,
            coalesce(new.raw_user_meta_data ->> 'full_name',
                     new.raw_user_meta_data ->> 'name', ''),
            coalesce(new.raw_user_meta_data ->> 'avatar_url',
                     new.raw_user_meta_data ->> 'picture'),
            case
              when new.raw_app_meta_data ->> 'role' in
                   ('super_admin', 'owner', 'staff', 'customer')
                then (new.raw_app_meta_data ->> 'role')::user_role
              else 'customer'::user_role
            end
          )
          on conflict (id) do nothing;
          return new;
        end $$;


ALTER FUNCTION "public"."handle_new_user"() OWNER TO "postgres";

--
-- Name: is_subscription_promotion_active("public"."subscription_status", timestamp with time zone, timestamp with time zone, timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone DEFAULT "now"()) RETURNS boolean
    LANGUAGE "plpgsql" IMMUTABLE
    SET "search_path" TO 'public'
    AS $$
begin
  if p_status in ('active', 'trialing') then
    if p_current_start is not null and p_current_end is not null
       and p_now >= p_current_start and p_now < p_current_end then
      return true;
    end if;
    -- A paid period stores its grace window; just-ended periods keep the benefit until then.
    return p_current_end is not null and p_grace_end is not null
       and p_now >= p_current_end and p_now < p_grace_end;
  end if;
  if p_status = 'cancelled' then
    return p_current_end is not null
       and p_now < p_current_end;
  end if;
  if p_status = 'past_due' then
    return p_grace_end is not null
       and p_now < p_grace_end;
  end if;
  return false;
end $$;


ALTER FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) OWNER TO "postgres";

--
-- Name: is_super_admin(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."is_super_admin"() RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select coalesce((select role = 'super_admin' from profiles where id = auth.uid()), false);
$$;


ALTER FUNCTION "public"."is_super_admin"() OWNER TO "postgres";

--
-- Name: owns_salon("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."owns_salon"("p_salon_id" "uuid") RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select exists (
    select 1 from salons
    where id = p_salon_id and owner_id = auth.uid() and is_active
  );
$$;


ALTER FUNCTION "public"."owns_salon"("p_salon_id" "uuid") OWNER TO "postgres";

--
-- Name: payment_append_audit(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."payment_append_audit"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  if tg_op = 'INSERT' or new.status is distinct from old.status then
    insert into public.booking_audit_events(booking_id, actor_id, event_type, old_state, new_state)
      values (new.booking_id, auth.uid(), 'payment_' || new.channel,
        case when tg_op = 'UPDATE' then old.status else null end, new.status);
  end if;
  return null;
end $$;


ALTER FUNCTION "public"."payment_append_audit"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";

--
-- Name: salon_payout_accounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_payout_accounts" (
    "salon_id" "uuid" NOT NULL,
    "account_holder_name" "text" NOT NULL,
    "upi_id" "text",
    "bank_name" "text",
    "bank_account_number" "text",
    "ifsc" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "bank_account_fingerprint" "text",
    CONSTRAINT "ck_payout_account_format" CHECK ((("bank_account_number" IS NULL) OR ("bank_account_number" ~ '^[0-9]{9,18}$'::"text"))),
    CONSTRAINT "ck_payout_bank_triple" CHECK (((("bank_account_number" IS NULL) AND ("ifsc" IS NULL) AND ("bank_name" IS NULL)) OR (("bank_account_number" IS NOT NULL) AND ("ifsc" IS NOT NULL)))),
    CONSTRAINT "ck_payout_has_destination" CHECK ((("upi_id" IS NOT NULL) OR (("bank_account_number" IS NOT NULL) AND ("ifsc" IS NOT NULL)))),
    CONSTRAINT "ck_payout_ifsc_format" CHECK ((("ifsc" IS NULL) OR ("ifsc" ~ '^[A-Z]{4}0[A-Z0-9]{6}$'::"text"))),
    CONSTRAINT "ck_payout_upi_format" CHECK ((("upi_id" IS NULL) OR ("upi_id" ~ '^[A-Za-z0-9._-]{2,255}@[A-Za-z]{2,64}$'::"text"))),
    CONSTRAINT "salon_payout_accounts_account_holder_name_check" CHECK ((("char_length"("account_holder_name") >= 2) AND ("char_length"("account_holder_name") <= 100))),
    CONSTRAINT "salon_payout_accounts_bank_name_check" CHECK ((("bank_name" IS NULL) OR ("char_length"("bank_name") <= 100)))
);


ALTER TABLE "public"."salon_payout_accounts" OWNER TO "postgres";

--
-- Name: payout_account_snapshot("public"."salon_payout_accounts"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") RETURNS "jsonb"
    LANGUAGE "sql" IMMUTABLE
    SET "search_path" TO 'public'
    AS $$
          select jsonb_build_object(
            'account_holder_name', r.account_holder_name,
            'upi_id', r.upi_id,
            'bank_name', r.bank_name,
            'ifsc', r.ifsc,
            'bank_account_last4', right(r.bank_account_number, 4)
          )
        $$;


ALTER FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") OWNER TO "postgres";

--
-- Name: recompute_booking_payment_state("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
declare
  v_total     numeric(10,2);
  v_paid      numeric(10,2);
  v_refunded  numeric(10,2);
  v_count     integer;
  v_net       numeric(10,2);
  v_method    text;
  v_at        timestamptz;
  v_by        uuid;
  v_new       public.payment_status;
begin
  select total_price into v_total from public.bookings where id = p_booking_id for update;
  if not found then
    return;
  end if;

  -- Money collected beyond what the booking was owed (overcollected_amount) is recorded on
  -- its ledger row but never counts towards the booking's paid state.
  select coalesce(sum(case when p.amount > 0 then round((p.amount - p.overcollected_amount) * p.service_amount / p.amount, 2) else 0 end), 0), count(*) into v_paid, v_count
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded');

  -- A refund of the excess does not reduce the paid state either.
  select coalesce(round(sum(case when p.amount > 0 then r.amount * p.service_amount / p.amount else 0 end), 2), 0) into v_refunded
  from public.payment_refunds r join public.booking_payments p on p.id = r.payment_id
  where r.booking_id = p_booking_id and r.status = 'processed' and not r.applies_to_excess;

  v_net := v_paid - v_refunded;
  if v_net > v_total then
    raise exception 'payment_overcollection'
      using errcode = '23514',
            detail = format('booking %s: net collected %s exceeds total %s',
                            p_booking_id, v_net, v_total);
  end if;

  v_new := case when v_count > 0 and v_net >= v_total then 'paid' else 'unpaid' end;

  select case when p.channel = 'gateway' then 'online' else coalesce(p.method, 'cash') end,
         p.captured_at, p.recorded_by
    into v_method, v_at, v_by
  from public.booking_payments p
  where p.booking_id = p_booking_id
    and p.status in ('captured', 'partially_refunded', 'refunded')
    and p.amount > p.overcollected_amount
  order by p.captured_at desc nulls last, p.created_at desc
  limit 1;

  perform set_config('app.payment_recompute', 'on', true);
  update public.bookings
  set paid_amount = v_paid,
      refunded_amount = v_refunded,
      payment_status = v_new,
      payment_method = case when v_count > 0 and (v_net > 0 or v_new = 'paid')
                            then v_method::public.payment_method else null end,
      payment_recorded_at = case when v_new = 'paid'
                                 then coalesce(v_at, payment_recorded_at, now()) else null end,
      payment_recorded_by = case when v_new = 'paid'
                                 then coalesce(v_by, payment_recorded_by) else null end
  where id = p_booking_id;
  perform set_config('app.payment_recompute', 'off', true);
end $$;


ALTER FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") OWNER TO "postgres";

--
-- Name: recompute_salon_trial("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
declare
  v_row   public.salon_access%rowtype;
  v_count integer;
begin
  -- Cheap exits without a lock: no row, trial not started, limit already stamped, date over.
  select * into v_row from public.salon_access where salon_id = p_salon_id;
  if not found or v_row.trial_started_at is null
     or v_row.trial_limit_reached_at is not null
     or v_row.trial_ends_at <= now() then
    if found and v_row.trial_started_at is not null and v_row.trial_ended_reason is null
       and v_row.trial_limit_reached_at is null and v_row.trial_ends_at <= now() then
      update public.salon_access set trial_ended_reason = 'date', updated_at = now()
      where salon_id = p_salon_id and trial_ended_reason is null and trial_limit_reached_at is null;
    end if;
    return;
  end if;
  select * into v_row from public.salon_access where salon_id = p_salon_id for update;
  if v_row.trial_limit_reached_at is not null or v_row.trial_ends_at <= now() then
    return;
  end if;
  -- Bounded scan: never reads more than the limit.
  select count(*) into v_count from (
    select 1 from public.bookings b
    where b.salon_id = p_salon_id and b.created_at >= v_row.trial_started_at
    limit v_row.trial_booking_limit
  ) counted;
  if v_count >= v_row.trial_booking_limit then
    update public.salon_access
    set bookings_counted = v_count, trial_limit_reached_at = now(),
        trial_ended_reason = 'booking_limit', updated_at = now()
    where salon_id = p_salon_id;
  elsif v_count is distinct from v_row.bookings_counted then
    update public.salon_access set bookings_counted = v_count, updated_at = now()
    where salon_id = p_salon_id;
  end if;
end $$;


ALTER FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") OWNER TO "postgres";

--
-- Name: register_device_token("text", "text", "text"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text" DEFAULT NULL::"text", "p_device_name" "text" DEFAULT NULL::"text") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
declare v_id uuid;
begin
  insert into device_tokens (user_id, token, platform, device_name, is_active, last_seen_at)
  values (auth.uid(), p_token, p_platform, p_device_name, true, now())
  on conflict (token) do update
    set user_id      = auth.uid(),
        is_active    = true,
        platform     = coalesce(excluded.platform, device_tokens.platform),
        device_name  = coalesce(excluded.device_name, device_tokens.device_name),
        last_seen_at = now()
  returning id into v_id;
  return v_id;
end $$;


ALTER FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") OWNER TO "postgres";

--
-- Name: salon_booking_eligible("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select exists (
    select 1 from public.salons s where s.id = p_salon and s.is_active
      and s.profile_completed and s.approval_status = 'approved'
      and (exists (
        select 1 from public.salon_subscriptions sub where sub.salon_id = s.id
          and sub.status in ('active', 'cancelled')
          and sub.current_period_start <= now() and sub.current_period_end > now()
      ) or exists (
        select 1 from public.salon_access a where a.salon_id = s.id
          and a.trial_started_at <= now() and a.trial_ends_at > now()
          and a.trial_limit_reached_at is null and a.bookings_counted < a.trial_booking_limit
      ))
  )
$$;


ALTER FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") OWNER TO "postgres";

--
-- Name: salon_payout_account_masked("uuid"); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") RETURNS TABLE("account_holder_name" "text", "upi_id" "text", "bank_name" "text", "bank_account_last4" "text", "ifsc" "text", "created_at" timestamp with time zone, "updated_at" timestamp with time zone)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
          select p.account_holder_name, p.upi_id, p.bank_name,
                 right(p.bank_account_number, 4), p.ifsc, p.created_at, p.updated_at
          from public.salon_payout_accounts p
          where p.salon_id = p_salon_id
        $$;


ALTER FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") OWNER TO "postgres";

--
-- Name: salon_trial_setting("text", integer, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) RETURNS integer
    LANGUAGE "plpgsql" STABLE
    SET "search_path" TO 'public'
    AS $_$
declare
  v_raw text := current_setting(p_name, true);
begin
  if v_raw ~ '^[0-9]{1,6}$' and v_raw::integer between p_min and p_max then
    return v_raw::integer;
  end if;
  return p_default;
end $_$;


ALTER FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) OWNER TO "postgres";

--
-- Name: set_audit_actor(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."set_audit_actor"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        begin
          if coalesce(current_setting('app.account_erasure', true), '') = 'on'
             and current_user not in ('anon', 'authenticated') then
            return new;
          end if;
          if tg_op = 'INSERT' then
            new.created_by := coalesce(new.created_by, auth.uid());
            new.updated_by := coalesce(new.updated_by, auth.uid());
          else
            new.updated_by := coalesce(auth.uid(), old.updated_by);
            new.created_by := old.created_by;
          end if;
          return new;
        end $$;


ALTER FUNCTION "public"."set_audit_actor"() OWNER TO "postgres";

--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  new.updated_at := now();
  return new;
end $$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

--
-- Name: stamp_booking_lifecycle(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."stamp_booking_lifecycle"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if new.status is distinct from old.status then
    case new.status
      when 'confirmed' then
        new.approved_by := coalesce(new.approved_by, auth.uid());
        new.approved_at := coalesce(new.approved_at, now());
      when 'rejected' then
        new.rejected_by := coalesce(new.rejected_by, auth.uid());
        new.rejected_at := coalesce(new.rejected_at, now());
      when 'completed' then
        new.completed_by := coalesce(new.completed_by, auth.uid());
        new.completed_at := coalesce(new.completed_at, now());
      when 'cancelled' then
        new.cancelled_by := coalesce(new.cancelled_by, auth.uid());
        new.cancelled_at := coalesce(new.cancelled_at, now());
      else null;
    end case;
  end if;

  if new.payment_status = 'paid' and old.payment_status <> 'paid' then
    new.payment_recorded_by := coalesce(new.payment_recorded_by, auth.uid());
    new.payment_recorded_at := coalesce(new.payment_recorded_at, now());
  end if;

  return new;
end $$;


ALTER FUNCTION "public"."stamp_booking_lifecycle"() OWNER TO "postgres";

--
-- Name: stamp_checkout_policy(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."stamp_checkout_policy"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if tg_op = 'INSERT' then new.checkout_policy_version := 'customer_processing_v1';
  elsif new.checkout_policy_version is distinct from old.checkout_policy_version then
    raise exception 'checkout_policy_is_immutable' using errcode = '23514';
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."stamp_checkout_policy"() OWNER TO "postgres";

--
-- Name: stamp_notification_read_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."stamp_notification_read_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        begin
          if new.read = true and old.read = false and new.read_at is null then
            new.read_at := now();
          end if;
          return new;
        end;
        $$;


ALTER FUNCTION "public"."stamp_notification_read_at"() OWNER TO "postgres";

--
-- Name: start_salon_trial("uuid", timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone DEFAULT "now"()) RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  insert into public.salon_access(salon_id, trial_started_at, trial_ends_at, trial_booking_limit)
    values (p_salon_id, p_at, p_at + interval '2 months', 120)
  on conflict (salon_id) do update set trial_started_at = excluded.trial_started_at,
    trial_ends_at = excluded.trial_ends_at, trial_booking_limit = 120, bookings_counted = 0
    where public.salon_access.trial_started_at is null;
end $$;


ALTER FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone) OWNER TO "postgres";

--
-- Name: sweep_lapsed_subscriptions(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."sweep_lapsed_subscriptions"() RETURNS integer
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
declare
  n integer := 0;
  c integer;
begin
  perform set_config('app.subscription_system', 'on', true);
  -- Period over and a stored grace window still open -> past_due; otherwise expired.
  update public.salon_subscriptions
  set status = cast(case when grace_period_end is not null and grace_period_end > now()
                         then 'past_due' else 'expired' end as subscription_status),
      expires_at = case when grace_period_end is not null and grace_period_end > now()
                        then expires_at else now() end
  where status in ('active', 'trialing') and current_period_end is not null
    and current_period_end <= now();
  get diagnostics c = row_count;
  n := n + c;
  update public.salon_subscriptions
  set status = 'expired', expires_at = now()
  where status = 'past_due'
    and coalesce(grace_period_end, current_period_end) is not null
    and coalesce(grace_period_end, current_period_end) <= now();
  get diagnostics c = row_count;
  n := n + c;
  perform set_config('app.subscription_system', 'off', true);
  return n;
end $$;


ALTER FUNCTION "public"."sweep_lapsed_subscriptions"() OWNER TO "postgres";

--
-- Name: tg_booking_payments_guard(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_booking_payments_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if new.booking_id is distinct from old.booking_id
     or new.amount is distinct from old.amount
     or new.intent_reference is distinct from old.intent_reference
     or new.channel is distinct from old.channel then
    raise exception 'booking_payment_identity_is_immutable' using errcode = '23514';
  end if;
  -- The commission snapshot is written once, at intent time, and never recomputed.
  if new.commission_rate_percent is distinct from old.commission_rate_percent
     or new.commission_base is distinct from old.commission_base
     or new.platform_commission_amount is distinct from old.platform_commission_amount
     or new.commission_policy_version is distinct from old.commission_policy_version then
    raise exception 'booking_payment_commission_snapshot_is_immutable' using errcode = '23514';
  end if;
  -- So is the gateway-fee snapshot borne by the salon.
  if new.gateway_fee_percent is distinct from old.gateway_fee_percent
     or new.gateway_fee_amount is distinct from old.gateway_fee_amount then
    raise exception 'booking_payment_gateway_fee_snapshot_is_immutable' using errcode = '23514';
  end if;
  -- The excess is decided at the moment of capture and fixed afterwards.
  if old.status in ('captured', 'partially_refunded', 'refunded')
     and new.overcollected_amount is distinct from old.overcollected_amount then
    raise exception 'booking_payment_overcollection_is_immutable' using errcode = '23514';
  end if;
  if old.status in ('captured', 'partially_refunded', 'refunded')
     and new.status in ('created', 'authorized', 'failed', 'cancelled', 'expired') then
    raise exception 'booking_payment_status_regression' using errcode = '23514';
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."tg_booking_payments_guard"() OWNER TO "postgres";

--
-- Name: tg_booking_payments_recompute(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_booking_payments_recompute"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        begin
          if tg_op = 'DELETE' then
            perform public.recompute_booking_payment_state(old.booking_id);
            return old;
          end if;
          perform public.recompute_booking_payment_state(new.booking_id);
          return new;
        end $$;


ALTER FUNCTION "public"."tg_booking_payments_recompute"() OWNER TO "postgres";

--
-- Name: tg_bookings_recompute_trial(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_bookings_recompute_trial"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  perform public.recompute_salon_trial(new.salon_id);
  return null;
end $$;


ALTER FUNCTION "public"."tg_bookings_recompute_trial"() OWNER TO "postgres";

--
-- Name: tg_payment_refunds_guard(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_payment_refunds_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
declare
  v_amount     numeric(10,2);
  v_excess     numeric(10,2);
  v_commission numeric(10,2);
  v_committed  numeric(10,2);
  v_reversed   numeric(10,2);
  v_cap        numeric(10,2);
begin
  if tg_op = 'UPDATE' and (new.kind is distinct from old.kind
                           or new.deduction_amount is distinct from old.deduction_amount
                           or new.amount is distinct from old.amount) then
    raise exception 'payment_refund_snapshot_is_immutable' using errcode = '23514';
  end if;
  select amount, overcollected_amount, platform_commission_amount
    into v_amount, v_excess, v_commission
  from public.booking_payments where id = new.payment_id;
  select coalesce(sum(r.amount), 0), coalesce(sum(r.commission_reversal_amount), 0)
    into v_committed, v_reversed
  from public.payment_refunds r
  where r.payment_id = new.payment_id and r.status <> 'failed'
    and r.applies_to_excess = new.applies_to_excess
    and (tg_op = 'INSERT' or r.id <> new.id);
  v_cap := case when new.applies_to_excess then v_excess else v_amount - v_excess end;
  if new.status <> 'failed' then
    if v_committed + new.amount > v_cap then
      raise exception 'refund_exceeds_payment' using errcode = '23514';
    end if;
    if v_reversed + new.commission_reversal_amount > v_commission then
      raise exception 'commission_reversal_exceeds_snapshot' using errcode = '23514';
    end if;
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."tg_payment_refunds_guard"() OWNER TO "postgres";

--
-- Name: tg_payment_refunds_recompute(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_payment_refunds_recompute"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        declare
          v_booking uuid := coalesce(new.booking_id, old.booking_id);
          v_payment uuid := coalesce(new.payment_id, old.payment_id);
          v_amount  numeric(10,2);
          v_status  text;
          v_done    numeric(10,2);
          v_next    text;
        begin
          select amount, status into v_amount, v_status
          from public.booking_payments where id = v_payment;
          select coalesce(sum(r.amount), 0) into v_done
          from public.payment_refunds r where r.payment_id = v_payment and r.status = 'processed';
          v_next := case when v_done = 0 then 'captured'
                         when v_done >= v_amount then 'refunded'
                         else 'partially_refunded' end;
          if v_status in ('captured', 'partially_refunded', 'refunded') and v_status <> v_next then
            -- booking_payments' own trigger recomputes the booking.
            update public.booking_payments set status = v_next where id = v_payment;
          else
            perform public.recompute_booking_payment_state(v_booking);
          end if;
          return coalesce(new, old);
        end $$;


ALTER FUNCTION "public"."tg_payment_refunds_recompute"() OWNER TO "postgres";

--
-- Name: tg_salon_payout_account_history(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_salon_payout_account_history"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
        declare
          v_fields text[];
        begin
          if tg_op = 'INSERT' then
            insert into public.salon_payout_account_history
              (salon_id, changed_by, action, changed_fields, before_state, after_state)
            values (new.salon_id, coalesce(new.updated_by, auth.uid()), 'created',
                    array['account_holder_name', 'upi_id', 'bank_name', 'bank_account_number', 'ifsc'],
                    null, public.payout_account_snapshot(new));
            return new;
          end if;
          v_fields := array_remove(array[
            case when new.account_holder_name is distinct from old.account_holder_name
                 then 'account_holder_name' end,
            case when new.upi_id is distinct from old.upi_id then 'upi_id' end,
            case when new.bank_name is distinct from old.bank_name then 'bank_name' end,
            case when new.bank_account_number is distinct from old.bank_account_number
                 then 'bank_account_number' end,
            case when new.ifsc is distinct from old.ifsc then 'ifsc' end
          ], null);
          if coalesce(array_length(v_fields, 1), 0) > 0 then
            insert into public.salon_payout_account_history
              (salon_id, changed_by, action, changed_fields, before_state, after_state)
            values (new.salon_id, coalesce(new.updated_by, auth.uid()), 'updated', v_fields,
                    public.payout_account_snapshot(old), public.payout_account_snapshot(new));
          end if;
          return new;
        end $$;


ALTER FUNCTION "public"."tg_salon_payout_account_history"() OWNER TO "postgres";

--
-- Name: tg_salons_access_row(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_salons_access_row"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  insert into public.salon_access (salon_id) values (new.id) on conflict (salon_id) do nothing;
  if new.approval_status = 'approved' then
    perform public.start_salon_trial(new.id);
  end if;
  return null;
end $$;


ALTER FUNCTION "public"."tg_salons_access_row"() OWNER TO "postgres";

--
-- Name: tg_subscription_billing_guard(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION "public"."tg_subscription_billing_guard"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  if new.salon_id is distinct from old.salon_id
     or new.plan_id is distinct from old.plan_id
     or new.provider is distinct from old.provider
     or new.receipt is distinct from old.receipt
     or new.amount is distinct from old.amount
     or new.currency is distinct from old.currency
     or new.billing_interval is distinct from old.billing_interval
     or new.benefits is distinct from old.benefits
     or new.plan_code is distinct from old.plan_code then
    raise exception 'subscription_billing_snapshot_is_immutable' using errcode = '23514';
  end if;
  if old.provider_order_ref is not null
     and new.provider_order_ref is distinct from old.provider_order_ref then
    raise exception 'subscription_billing_order_is_immutable' using errcode = '23514';
  end if;
  if old.provider_payment_ref is not null
     and new.provider_payment_ref is distinct from old.provider_payment_ref then
    raise exception 'subscription_billing_payment_is_immutable' using errcode = '23514';
  end if;
  if old.applied_at is not null
     and (new.applied_at is distinct from old.applied_at
          or new.period_start is distinct from old.period_start
          or new.period_end is distinct from old.period_end
          or new.subscription_id is distinct from old.subscription_id) then
    raise exception 'subscription_billing_application_is_immutable' using errcode = '23514';
  end if;
  if old.status in ('paid', 'partially_refunded', 'refunded')
     and new.status in ('created', 'authorized', 'failed', 'expired') then
    raise exception 'subscription_billing_status_regression' using errcode = '23514';
  end if;
  if old.status = 'refunded' and new.status in ('paid', 'partially_refunded') then
    raise exception 'subscription_billing_status_regression' using errcode = '23514';
  end if;
  return new;
end $$;


ALTER FUNCTION "public"."tg_subscription_billing_guard"() OWNER TO "postgres";

--
-- Name: apply_rls("jsonb", integer); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer DEFAULT (1024 * 1024)) RETURNS SETOF "realtime"."wal_rls"
    LANGUAGE "plpgsql"
    AS $$
declare
    -- Regclass of the table e.g. public.notes
    entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

    -- I, U, D, T: insert, update ...
    action realtime.action = (
        case wal ->> 'action'
            when 'I' then 'INSERT'
            when 'U' then 'UPDATE'
            when 'D' then 'DELETE'
            else 'ERROR'
        end
    );

    -- Is row level security enabled for the table
    is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

    subscriptions realtime.subscription[] = array_agg(subs)
        from
            realtime.subscription subs
        where
            subs.entity = entity_
            -- Filter by action early - only get subscriptions interested in this action
            -- action_filter column can be: '*' (all), 'INSERT', 'UPDATE', or 'DELETE'
            and (subs.action_filter = '*' or subs.action_filter = action::text);

    -- Subscription vars
    working_role regrole;
    working_selected_columns text[];
    claimed_role regrole;
    claims jsonb;

    subscription_id uuid;
    subscription_has_access bool;
    visible_to_subscription_ids uuid[] = '{}';

    -- structured info for wal's columns
    columns realtime.wal_column[];
    -- previous identity values for update/delete
    old_columns realtime.wal_column[];

    error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

    -- Primary jsonb output for record
    output jsonb;

    -- Loop record for iterating unique roles (outer loop)
    role_record record;
    -- Loop record for iterating unique selected_columns within a role (inner loop)
    cols_record record;
    -- Subscription ids visible at the role level (before fanning out by selected_columns)
    visible_role_sub_ids uuid[] = '{}';

begin
    perform set_config('role', null, true);

    columns =
        array_agg(
            (
                x->>'name',
                x->>'type',
                x->>'typeoid',
                realtime.cast(
                    (x->'value') #>> '{}',
                    coalesce(
                        (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                        (x->>'type')::regtype
                    )
                ),
                (pks ->> 'name') is not null,
                true
            )::realtime.wal_column
        )
        from
            jsonb_array_elements(wal -> 'columns') x
            left join jsonb_array_elements(wal -> 'pk') pks
                on (x ->> 'name') = (pks ->> 'name');

    old_columns =
        array_agg(
            (
                x->>'name',
                x->>'type',
                x->>'typeoid',
                realtime.cast(
                    (x->'value') #>> '{}',
                    coalesce(
                        (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                        (x->>'type')::regtype
                    )
                ),
                (pks ->> 'name') is not null,
                true
            )::realtime.wal_column
        )
        from
            jsonb_array_elements(wal -> 'identity') x
            left join jsonb_array_elements(wal -> 'pk') pks
                on (x ->> 'name') = (pks ->> 'name');

    for role_record in
        select claims_role
        from (select distinct claims_role from unnest(subscriptions)) t
        order by claims_role::text
    loop
        working_role := role_record.claims_role;

        -- Update `is_selectable` for columns and old_columns (once per role)
        columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(columns) c;

        old_columns =
                array_agg(
                    (
                        c.name,
                        c.type_name,
                        c.type_oid,
                        c.value,
                        c.is_pkey,
                        pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                    )::realtime.wal_column
                )
                from
                    unnest(old_columns) c;

        if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
            -- Fan out 400 error per distinct selected_columns for this role
            for cols_record in
                select selected_columns
                from (select distinct selected_columns from unnest(subscriptions) s where s.claims_role = working_role) t
                order by coalesce(array_to_string(selected_columns, ','), '')
            loop
                working_selected_columns := cols_record.selected_columns;
                return next (
                    jsonb_build_object(
                        'schema', wal ->> 'schema',
                        'table', wal ->> 'table',
                        'type', action
                    ),
                    is_rls_enabled,
                    (select array_agg(s.subscription_id) from unnest(subscriptions) as s where s.claims_role = working_role and (s.selected_columns is not distinct from working_selected_columns)),
                    array['Error 400: Bad Request, no primary key']
                )::realtime.wal_rls;
            end loop;

        -- The claims role does not have SELECT permission to the primary key of entity
        elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
            -- Fan out 401 error per distinct selected_columns for this role
            for cols_record in
                select selected_columns
                from (select distinct selected_columns from unnest(subscriptions) s where s.claims_role = working_role) t
                order by coalesce(array_to_string(selected_columns, ','), '')
            loop
                working_selected_columns := cols_record.selected_columns;
                return next (
                    jsonb_build_object(
                        'schema', wal ->> 'schema',
                        'table', wal ->> 'table',
                        'type', action
                    ),
                    is_rls_enabled,
                    (select array_agg(s.subscription_id) from unnest(subscriptions) as s where s.claims_role = working_role and (s.selected_columns is not distinct from working_selected_columns)),
                    array['Error 401: Unauthorized']
                )::realtime.wal_rls;
            end loop;

        else
            -- Create the prepared statement (once per role)
            if is_rls_enabled and action <> 'DELETE' then
                if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                    deallocate walrus_rls_stmt;
                end if;
                execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
            end if;

            -- Collect all visible subscription IDs for this role (filter check + RLS check)
            visible_role_sub_ids = '{}';

            for subscription_id, claims in (
                    select
                        subs.subscription_id,
                        subs.claims
                    from
                        unnest(subscriptions) subs
                    where
                        subs.entity = entity_
                        and subs.claims_role = working_role
                        and (
                            realtime.is_visible_through_filters(columns, subs.filters)
                            or (
                              action = 'DELETE'
                              and realtime.is_visible_through_filters(old_columns, subs.filters)
                            )
                        )
            ) loop

                if not is_rls_enabled or action = 'DELETE' then
                    visible_role_sub_ids = visible_role_sub_ids || subscription_id;
                else
                    -- Check if RLS allows the role to see the record
                    perform
                        -- Trim leading and trailing quotes from working_role because set_config
                        -- doesn't recognize the role as valid if they are included
                        set_config('role', trim(both '"' from working_role::text), true),
                        set_config('request.jwt.claims', claims::text, true);

                    execute 'execute walrus_rls_stmt' into subscription_has_access;

                    -- Reset the role on every FOR..LOOP batch execution.
                    -- The first batch of 10 rows is pre-fetched using the current connection role (PG internal behaviour)
                    -- then we have to reset it again otherwise it would use the role defined in the `set_config` above
                    -- to fetch the remaining rows when rows>10, which could be a user-defined role that lacks execution grants.
                    -- The flow is:
                    --   1. run batch with conn role
                    --   2. set_config working_role
                    --   3. execute walrus
                    --   4. reset role (revert)
                    --   5. repeat
                    perform set_config('role', null, true);

                    if subscription_has_access then
                        visible_role_sub_ids = visible_role_sub_ids || subscription_id;
                    end if;
                end if;
            end loop;

            perform set_config('role', null, true);

            -- Inner loop: per distinct selected_columns for this role
            for cols_record in
                select selected_columns
                from (select distinct selected_columns from unnest(subscriptions) s where s.claims_role = working_role) t
                order by coalesce(array_to_string(selected_columns, ','), '')
            loop
                working_selected_columns := cols_record.selected_columns;

                output = jsonb_build_object(
                    'schema', wal ->> 'schema',
                    'table', wal ->> 'table',
                    'type', action,
                    'commit_timestamp', to_char(
                        ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                        'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
                    ),
                    'columns', (
                        select
                            jsonb_agg(
                                jsonb_build_object(
                                    'name', pa.attname,
                                    'type', pt.typname
                                )
                                order by pa.attnum asc
                            )
                        from
                            pg_attribute pa
                            join pg_type pt
                                on pa.atttypid = pt.oid
                            left join (
                                select unnest(conkey) as pkey_attnum
                                from pg_constraint
                                where conrelid = entity_ and contype = 'p'
                            ) pk on pk.pkey_attnum = pa.attnum
                        where
                            attrelid = entity_
                            and attnum > 0
                            and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
                            and (working_selected_columns is null or pa.attname = any(working_selected_columns) or pk.pkey_attnum is not null)
                    )
                )
                -- Add "record" key for insert and update
                || case
                    when action in ('INSERT', 'UPDATE') then
                        jsonb_build_object(
                            'record',
                            (
                                select
                                    jsonb_object_agg(
                                        -- if unchanged toast, get column name and value from old record
                                        coalesce((c).name, (oc).name),
                                        case
                                            when (c).name is null then (oc).value
                                            else (c).value
                                        end
                                    )
                                from
                                    unnest(columns) c
                                    full outer join unnest(old_columns) oc
                                        on (c).name = (oc).name
                                where
                                    coalesce((c).is_selectable, (oc).is_selectable)
                                    and (working_selected_columns is null or coalesce((c).name, (oc).name) = any(working_selected_columns) or coalesce((c).is_pkey, (oc).is_pkey))
                                    and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            )
                        )
                    else '{}'::jsonb
                end
                -- Add "old_record" key for update and delete
                || case
                    when action = 'UPDATE' then
                        jsonb_build_object(
                                'old_record',
                                (
                                    select jsonb_object_agg((c).name, (c).value)
                                    from unnest(old_columns) c
                                    where
                                        (c).is_selectable
                                        and (working_selected_columns is null or (c).name = any(working_selected_columns) or (c).is_pkey)
                                        and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                                )
                            )
                    when action = 'DELETE' then
                        jsonb_build_object(
                            'old_record',
                            (
                                select jsonb_object_agg((c).name, (c).value)
                                from unnest(old_columns) c
                                where
                                    (c).is_selectable
                                    and (working_selected_columns is null or (c).name = any(working_selected_columns) or (c).is_pkey)
                                    and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                                    and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                            )
                        )
                    else '{}'::jsonb
                end;

                -- Filter visible_role_sub_ids to those matching the current selected_columns group
                visible_to_subscription_ids = coalesce(
                    (
                        select array_agg(s.subscription_id)
                        from unnest(subscriptions) s
                        where s.claims_role = working_role
                          and (s.selected_columns is not distinct from working_selected_columns)
                          and s.subscription_id = any(visible_role_sub_ids)
                    ),
                    '{}'::uuid[]
                );

                return next (
                    output,
                    is_rls_enabled,
                    visible_to_subscription_ids,
                    case
                        when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                        else '{}'
                    end
                )::realtime.wal_rls;
            end loop;

        end if;
    end loop;

    perform set_config('role', null, true);
end;
$$;


ALTER FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) OWNER TO "supabase_realtime_admin";

--
-- Name: authorize("text", "text", "text", "text", "text", "text"[], "text"[]); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."authorize"("role_name" "text", "topic_name" "text", "claims" "text", "sub" "text", "headers" "text", "read_extensions" "text"[], "write_extensions" "text"[], OUT "read_allowed" boolean[], OUT "write_allowed" boolean[]) RETURNS "record"
    LANGUAGE "plpgsql"
    AS $$
declare
  probe_ids uuid[];
  ext text;
  allowed boolean;
begin
  -- The probe inserts are rolled back, but they still give the transaction an xid, so it ends
  -- in a commit. Nothing durable was written, so skip waiting on the WAL flush and sync standbys.
  -- Set outside the block below, whose rollback would undo it.
  perform set_config('synchronous_commit', 'off', true);

  -- The RAISE at the end of this block rolls back everything in it.
  begin
    probe_ids := array(select gen_random_uuid() from unnest(read_extensions));

    insert into realtime.messages (id, topic, extension, inserted_at, updated_at)
    select p.id, topic_name, p.extension, now() at time zone 'utc', now() at time zone 'utc'
    from unnest(probe_ids, read_extensions) as p(id, extension);

    perform set_config('role', role_name, true),
            set_config('realtime.topic', topic_name, true),
            set_config('request.jwt.claims', claims, true),
            set_config('request.jwt.claim.sub', sub, true),
            set_config('request.jwt.claim.role', role_name, true),
            set_config('request.headers', headers, true);

    read_allowed := array(
      select exists(select 1 from realtime.messages m where m.id = p.id)
      from unnest(probe_ids) with ordinality as p(id, n)
      order by p.n);

    write_allowed := '{}';

    foreach ext in array write_extensions loop
      begin
        insert into realtime.messages (topic, extension, inserted_at, updated_at)
        values (topic_name, ext, now() at time zone 'utc', now() at time zone 'utc');

        allowed := true;
      exception when insufficient_privilege then
        allowed := false;
      end;

      write_allowed := write_allowed || allowed;
    end loop;

    raise sqlstate 'RTA01';
  exception when sqlstate 'RTA01' then
    null;
  end;
end;
$$;


ALTER FUNCTION "realtime"."authorize"("role_name" "text", "topic_name" "text", "claims" "text", "sub" "text", "headers" "text", "read_extensions" "text"[], "write_extensions" "text"[], OUT "read_allowed" boolean[], OUT "write_allowed" boolean[]) OWNER TO "supabase_realtime_admin";

--
-- Name: broadcast_changes("text", "text", "text", "text", "text", "record", "record", "text"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."broadcast_changes"("topic_name" "text", "event_name" "text", "operation" "text", "table_name" "text", "table_schema" "text", "new" "record", "old" "record", "level" "text" DEFAULT 'ROW'::"text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


ALTER FUNCTION "realtime"."broadcast_changes"("topic_name" "text", "event_name" "text", "operation" "text", "table_name" "text", "table_schema" "text", "new" "record", "old" "record", "level" "text") OWNER TO "supabase_realtime_admin";

--
-- Name: build_prepared_statement_sql("text", "regclass", "realtime"."wal_column"[]); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) RETURNS "text"
    LANGUAGE "sql"
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


ALTER FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) OWNER TO "supabase_realtime_admin";

--
-- Name: cast("text", "regtype"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") RETURNS "jsonb"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
declare
  res jsonb;
begin
  if type_::text = 'bytea' then
    return to_jsonb(val);
  end if;
  execute format('select to_jsonb(%L::'|| type_::text || ')', val) into res;
  return res;
end
$$;


ALTER FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") OWNER TO "supabase_realtime_admin";

--
-- Name: check_equality_op("realtime"."equality_op", "regtype", "text", "text"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") RETURNS boolean
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
/*
Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
*/
declare
    op_symbol text = (
        case
            when op = 'eq' then '='
            when op = 'neq' then '!='
            when op = 'lt' then '<'
            when op = 'lte' then '<='
            when op = 'gt' then '>'
            when op = 'gte' then '>='
            when op = 'in' then '= any'
            else 'UNKNOWN OP'
        end
    );
    res boolean;
begin
    execute format(
        'select %L::'|| type_::text || ' ' || op_symbol
        || ' ( %L::'
        || (
            case
                when op = 'in' then type_::text || '[]'
                else type_::text end
        )
        || ')', val_1, val_2) into res;
    return res;
end;
$$;


ALTER FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") OWNER TO "supabase_realtime_admin";

--
-- Name: check_equality_op("realtime"."equality_op", "regtype", "text", "text", boolean); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) RETURNS boolean
    LANGUAGE "plpgsql" STABLE
    AS $$
declare
    op_symbol text;
    res boolean;
begin
    -- IS DISTINCT FROM / IS NOT DISTINCT FROM: infix, both sides typed literals
    if op = 'isdistinct' then
        execute format(
            'select %L::%s %s %L::%s',
            val_1,
            type_::text,
            case when negate then 'IS NOT DISTINCT FROM' else 'IS DISTINCT FROM' end,
            val_2,
            type_::text
        ) into res;
        return res;
    end if;

    -- IS requires a keyword RHS (NULL, TRUE, FALSE, UNKNOWN), not a typed literal
    if op = 'is' then
        if val_2 not in ('null', 'true', 'false', 'unknown') then
            raise exception 'invalid value for is filter: must be null, true, false, or unknown';
        end if;
        execute format(
            'select %L::%s %s %s',
            val_1,
            type_::text,
            case when negate then 'IS NOT' else 'IS' end,
            upper(val_2)
        ) into res;
        return res;
    end if;

    op_symbol = case
        when op = 'eq'    then '='
        when op = 'neq'   then '!='
        when op = 'lt'    then '<'
        when op = 'lte'   then '<='
        when op = 'gt'    then '>'
        when op = 'gte'   then '>='
        when op = 'in'    then '= any'
        when op = 'like'   then 'LIKE'
        when op = 'ilike'  then 'ILIKE'
        when op = 'match'  then '~'
        when op = 'imatch' then '~*'
        else null
    end;

    if op_symbol is null then
        raise exception 'unsupported equality operator: %', op::text;
    end if;

    execute format(
        'select %L::%s %s (%L::%s)',
        val_1,
        type_::text,
        op_symbol,
        val_2,
        case when op = 'in' then type_::text || '[]' else type_::text end
    ) into res;

    return case when negate then not res else res end;
end;
$$;


ALTER FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) OWNER TO "supabase_realtime_admin";

--
-- Name: is_visible_through_filters("realtime"."wal_column"[], "realtime"."user_defined_filter"[]); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) RETURNS boolean
    LANGUAGE "sql" STABLE
    AS $$
    select
        filters is null
        or array_length(filters, 1) is null
        or coalesce(
            count(col.name) = count(1)
            and sum(
                realtime.check_equality_op(
                    op:=f.op,
                    type_:=coalesce(col.type_oid::regtype, col.type_name::regtype),
                    val_1:=col.value #>> '{}',
                    val_2:=f.value,
                    negate:=coalesce(f.negate, false)
                )::int
            ) filter (where col.name is not null) = count(col.name),
            false
        )
    from
        unnest(filters) f
        left join unnest(columns) col
            on f.column_name = col.name;
$$;


ALTER FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) OWNER TO "supabase_realtime_admin";

--
-- Name: list_changes("name", "name", integer, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."list_changes"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) RETURNS TABLE("wal" "jsonb", "is_rls_enabled" boolean, "subscription_ids" "uuid"[], "errors" "text"[], "slot_changes_count" bigint)
    LANGUAGE "sql"
    SET "log_min_messages" TO 'fatal'
    AS $$
  WITH pub AS (
    SELECT
      concat_ws(
        ',',
        CASE WHEN bool_or(pubinsert) THEN 'insert' ELSE NULL END,
        CASE WHEN bool_or(pubupdate) THEN 'update' ELSE NULL END,
        CASE WHEN bool_or(pubdelete) THEN 'delete' ELSE NULL END
      ) AS w2j_actions,
      coalesce(
        string_agg(
          realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
          ','
        ) filter (WHERE ppt.tablename IS NOT NULL),
        ''
      ) AS w2j_add_tables
    FROM pg_publication pp
    LEFT JOIN pg_publication_tables ppt ON pp.pubname = ppt.pubname
    WHERE pp.pubname = publication
    GROUP BY pp.pubname
    LIMIT 1
  ),
  -- MATERIALIZED ensures pg_logical_slot_get_changes is called exactly once
  w2j AS MATERIALIZED (
    SELECT x.*, pub.w2j_add_tables
    FROM pub,
         pg_logical_slot_get_changes(
           slot_name, null, max_changes,
           'include-pk', 'true',
           'include-transaction', 'false',
           'include-timestamp', 'true',
           'include-type-oids', 'true',
           'format-version', '2',
           'actions', pub.w2j_actions,
           'add-tables', pub.w2j_add_tables
         ) x
  ),
  slot_count AS (
    SELECT count(*)::bigint AS cnt
    FROM w2j
    WHERE w2j.w2j_add_tables <> ''
  ),
  rls_filtered AS (
    SELECT xyz.wal, xyz.is_rls_enabled, xyz.subscription_ids, xyz.errors
    FROM w2j,
         realtime.apply_rls(
           wal := w2j.data::jsonb,
           max_record_bytes := max_record_bytes
         ) xyz(wal, is_rls_enabled, subscription_ids, errors)
    WHERE w2j.w2j_add_tables <> ''
      AND xyz.subscription_ids[1] IS NOT NULL
  )
  SELECT rf.wal, rf.is_rls_enabled, rf.subscription_ids, rf.errors, sc.cnt
  FROM rls_filtered rf, slot_count sc

  UNION ALL

  SELECT null, null, null, null, sc.cnt
  FROM slot_count sc
  WHERE NOT EXISTS (SELECT 1 FROM rls_filtered)
$$;


ALTER FUNCTION "realtime"."list_changes"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) OWNER TO "supabase_realtime_admin";

--
-- Name: list_changes_sync("name", "name", integer, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."list_changes_sync"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) RETURNS TABLE("wal" "jsonb", "is_rls_enabled" boolean, "subscription_ids" "uuid"[], "errors" "text"[], "slot_changes_count" bigint)
    LANGUAGE "sql"
    SET "log_min_messages" TO 'fatal'
    AS $$
  WITH pub AS (
    SELECT
      concat_ws(
        ',',
        CASE WHEN bool_or(pubinsert) THEN 'insert' ELSE NULL END,
        CASE WHEN bool_or(pubupdate) THEN 'update' ELSE NULL END,
        CASE WHEN bool_or(pubdelete) THEN 'delete' ELSE NULL END
      ) AS w2j_actions,
      coalesce(
        string_agg(
          realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
          ','
        ) filter (WHERE ppt.tablename IS NOT NULL),
        ''
      ) AS w2j_add_tables
    FROM pg_publication pp
    LEFT JOIN pg_publication_tables ppt ON pp.pubname = ppt.pubname
    WHERE pp.pubname = publication
    GROUP BY pp.pubname
    LIMIT 1
  ),
  -- MATERIALIZED ensures the slot is read exactly once.
  consumed AS MATERIALIZED (
    SELECT x.*, pub.w2j_add_tables
    FROM pub,
         realtime.settled_changes(
           slot_name, max_changes,
           'include-pk', 'true',
           'include-transaction', 'false',
           'include-timestamp', 'true',
           'include-type-oids', 'true',
           'format-version', '2',
           'actions', pub.w2j_actions,
           'add-tables', pub.w2j_add_tables
         ) x
  ),
  slot_count AS (
    SELECT count(*)::bigint AS cnt
    FROM consumed
    WHERE consumed.w2j_add_tables <> ''
  ),
  rls_filtered AS (
    SELECT xyz.wal, xyz.is_rls_enabled, xyz.subscription_ids, xyz.errors
    FROM consumed,
         realtime.apply_rls(
           wal := consumed.data::jsonb,
           max_record_bytes := max_record_bytes
         ) xyz(wal, is_rls_enabled, subscription_ids, errors)
    WHERE consumed.w2j_add_tables <> ''
      AND xyz.subscription_ids[1] IS NOT NULL
  )
  SELECT rf.wal, rf.is_rls_enabled, rf.subscription_ids, rf.errors, sc.cnt
  FROM rls_filtered rf, slot_count sc

  UNION ALL

  SELECT null, null, null, null, sc.cnt
  FROM slot_count sc
  WHERE NOT EXISTS (SELECT 1 FROM rls_filtered)
$$;


ALTER FUNCTION "realtime"."list_changes_sync"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) OWNER TO "supabase_realtime_admin";

--
-- Name: quote_wal2json("regclass"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."quote_wal2json"("entity" "regclass") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE STRICT
    AS $$
  SELECT
    realtime.wal2json_escape_identifier(nsp.nspname::text)
    || '.'
    || realtime.wal2json_escape_identifier(pc.relname::text)
  FROM pg_class pc
  JOIN pg_namespace nsp ON pc.relnamespace = nsp.oid
  WHERE pc.oid = entity
$$;


ALTER FUNCTION "realtime"."quote_wal2json"("entity" "regclass") OWNER TO "supabase_realtime_admin";

--
-- Name: send("jsonb", "text", "text", boolean); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."send"("payload" "jsonb", "event" "text", "topic" "text", "private" boolean DEFAULT true) RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  generated_id uuid;
  final_payload jsonb;
BEGIN
  BEGIN
    generated_id := gen_random_uuid();

    -- Check if payload has an 'id' key, if not, add the generated UUID
    IF payload ? 'id' THEN
      final_payload := payload;
    ELSE
      final_payload := jsonb_set(payload, '{id}', to_jsonb(generated_id));
    END IF;

    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    INSERT INTO realtime.messages (id, payload, event, topic, private, extension)
    VALUES (generated_id, final_payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING 'WarnSendingBroadcastMessage: %', SQLERRM;
  END;
END;
$$;


ALTER FUNCTION "realtime"."send"("payload" "jsonb", "event" "text", "topic" "text", "private" boolean) OWNER TO "supabase_realtime_admin";

--
-- Name: send_binary("bytea", "text", "text", boolean); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."send_binary"("payload" "bytea", "event" "text", "topic" "text", "private" boolean DEFAULT true) RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
  generated_id uuid;
BEGIN
  BEGIN
    generated_id := gen_random_uuid();

    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    INSERT INTO realtime.messages (id, binary_payload, event, topic, private, extension)
    VALUES (generated_id, payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING 'WarnSendingBroadcastMessage: %', SQLERRM;
  END;
END;
$$;


ALTER FUNCTION "realtime"."send_binary"("payload" "bytea", "event" "text", "topic" "text", "private" boolean) OWNER TO "supabase_realtime_admin";

--
-- Name: settled_changes("name", integer, "text"[]); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."settled_changes"("slot_name" "name", "max_changes" integer, VARIADIC "opts" "text"[]) RETURNS TABLE("lsn" "pg_lsn", "xid" "xid", "data" "text")
    LANGUAGE "plpgsql"
    AS $$
declare
  upto pg_lsn;
  total bigint;
  xids xid[];
  starts bigint[];
  snapshot pg_snapshot;
  running_xids xid[];
  xmax_age int;
  cut bigint;
begin
  -- Each statement in a volatile function takes its own snapshot, which is what lets the
  -- check below see a writer that was still in flight when the peek ran. Under REPEATABLE
  -- READ the snapshot never advances, so a deferred change would never be released.
  if current_setting('transaction_isolation') <> 'read committed' then
    raise exception 'realtime.settled_changes requires READ COMMITTED';
  end if;

  -- The peek and the read below cover the same WAL, so the read cannot reach a commit the
  -- check never saw.
  upto := pg_current_wal_flush_lsn();

  -- One entry per transaction, in commit order: its xid and the position of its first
  -- change. The peek uses the caller's own options, so max_changes counts exactly what the
  -- read counts. A non-transactional logical message is emitted as soon as it is decoded,
  -- tagged with the xid of whatever transaction wrote it, so it does not mark where that
  -- transaction starts.
  select coalesce(sum(g.n), 0),
         array_agg(g.x order by g.first) filter (where g.first is not null),
         array_agg(g.first order by g.first) filter (where g.first is not null)
    into total, xids, starts
    from (
      select p.xid as x, count(*) as n,
             min(p.ord) filter (where not case
               when starts_with(p.data, '{"action":"M"') then (p.data::jsonb->>'transactional')::boolean is false
               else false
             end) as first
      from pg_logical_slot_peek_changes(slot_name, upto, max_changes, variadic opts)
           with ordinality as p(lsn, xid, data, ord)
      group by p.xid
    ) g;

  -- Nothing for the caller, but the slot still has to move past what the peek covered.
  if total = 0 then
    perform pg_replication_slot_advance(slot_name, upto);
    return;
  end if;

  if xids is not null then
    -- Taken after the peek is materialized, so a writer that was still in flight during
    -- decoding is guaranteed to show up here.
    snapshot := pg_current_snapshot();

    -- A commit record reaches the WAL before the writer leaves the proc array, so a change
    -- can be decoded while its row is invisible. apply_rls would resolve a policy against a
    -- row it cannot see and authorize it for nobody, while the read consumed it regardless.
    --
    -- xip lists transactions running when the snapshot was taken. It does not cover a writer
    -- whose xid sits at or beyond xmax, which never appears there, so the horizon is checked
    -- too. age() counts backwards from the current xid and so compares correctly across
    -- wraparound.
    select coalesce(array_agg(running.x::xid), array[]::xid[])
      into running_xids
      from pg_snapshot_xip(snapshot) running(x);
    xmax_age := age(pg_snapshot_xmax(snapshot)::xid);

    select min(u.s) into cut
      from unnest(xids, starts) as u(x, s)
      where u.x = any(running_xids) or age(u.x) <= xmax_age;
  end if;

  -- The read stops right after the commit that brings its count to upto_nchanges, so the
  -- count of changes in front of the first unsettled transaction stops it just before that
  -- transaction.
  if cut is null then
    return query
      select p.* from pg_logical_slot_get_changes(slot_name, upto, max_changes, variadic opts) p;
  elsif cut > 1 then
    return query
      select p.* from pg_logical_slot_get_changes(slot_name, upto, (cut - 1)::int, variadic opts) p;
  end if;
end;
$$;


ALTER FUNCTION "realtime"."settled_changes"("slot_name" "name", "max_changes" integer, VARIADIC "opts" "text"[]) OWNER TO "supabase_realtime_admin";

--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."subscription_check_filters"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
declare
    col_names text[] = coalesce(
            array_agg(a.attname order by a.attnum),
            '{}'::text[]
        )
        from
            pg_catalog.pg_attribute a
        where
            a.attrelid = new.entity
            and a.attnum > 0
            and not a.attisdropped
            and pg_catalog.has_column_privilege(
                (new.claims ->> 'role'),
                a.attrelid,
                a.attnum,
                'SELECT'
            );
    filter realtime.user_defined_filter;
    col_type regtype;
    in_val jsonb;
    selected_col text;
begin
    for filter in select * from unnest(new.filters) loop
        if not filter.column_name = any(col_names) then
            raise exception 'invalid column for filter %', filter.column_name;
        end if;

        col_type = (
            select atttypid::regtype
            from pg_catalog.pg_attribute
            where attrelid = new.entity
                  and attname = filter.column_name
        );
        if col_type is null then
            raise exception 'failed to lookup type for column %', filter.column_name;
        end if;

        if filter.op = 'in'::realtime.equality_op then
            in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
            if coalesce(jsonb_array_length(in_val), 0) > 100 then
                raise exception 'too many values for `in` filter. Maximum 100';
            end if;
        elsif filter.op = 'is'::realtime.equality_op then
            -- `is` requires a keyword RHS rather than a typed literal
            if filter.value not in ('null', 'true', 'false', 'unknown') then
                raise exception 'invalid value for is filter: must be null, true, false, or unknown';
            end if;
            -- IS NULL works for any type, but IS TRUE/FALSE/UNKNOWN require a boolean
            -- operand. Reject the non-null keywords on non-boolean columns here so they
            -- don't abort apply_rls at WAL time.
            if filter.value <> 'null' and col_type <> 'boolean'::regtype then
                raise exception 'is % filter requires a boolean column, got %', filter.value, col_type::text;
            end if;
        elsif filter.op in ('like'::realtime.equality_op, 'ilike'::realtime.equality_op) then
            -- like/ilike apply the text pattern operator (~~); reject column types that
            -- have no such operator instead of failing at WAL time
            if not exists (
                select 1 from pg_catalog.pg_operator
                where oprname = '~~' and oprleft = col_type
            ) then
                raise exception 'operator % requires a text-compatible column type, got %', filter.op::text, col_type::text;
            end if;
        elsif filter.op in ('match'::realtime.equality_op, 'imatch'::realtime.equality_op) then
            -- match/imatch apply the regex operators ~ / ~*; reject column types that have
            -- no such operator (e.g. integer) instead of failing at WAL time, mirroring the
            -- like/ilike guard above.
            if not exists (
                select 1 from pg_catalog.pg_operator
                where oprname = case when filter.op = 'imatch'::realtime.equality_op then '~*' else '~' end
                  and oprleft = col_type
                  and oprright = col_type
                  and oprresult = 'boolean'::regtype
            ) then
                raise exception 'operator % requires a text-compatible column type, got %', filter.op::text, col_type::text;
            end if;
            -- validate the regex eagerly so a bad pattern is rejected here, not inside
            -- apply_rls where it would abort the WAL stream for the entity
            begin
                perform '' ~ filter.value;
            exception when others then
                raise exception 'invalid regular expression for % filter: %', filter.op::text, sqlerrm;
            end;
        else
            -- eq/neq/lt/lte/gt/gte: value must be coercable to the type
            perform realtime.cast(filter.value, col_type);
        end if;
    end loop;

    if new.selected_columns is not null then
        for selected_col in select * from unnest(new.selected_columns) loop
            if not selected_col = any(col_names) then
                raise exception 'invalid column for select %', selected_col;
            end if;
        end loop;
    end if;

    -- Apply consistent order to filters so the unique constraint can't be tricked by a
    -- different filter order. negate is part of the sort key.
    new.filters = coalesce(
        array_agg(f order by f.column_name, f.op, f.value, f.negate),
        '{}'
    ) from unnest(new.filters) f;

    -- Normalize selected_columns order so ARRAY['a','b'] and ARRAY['b','a'] are treated
    -- as the same subscription group in apply_rls. Preserve an empty array as '{}'
    -- ("primary keys only") so it stays distinct from NULL ("all columns"); array_agg
    -- over an empty set would otherwise collapse '{}' back to NULL.
    if new.selected_columns is not null then
        new.selected_columns = coalesce(
            (
                select array_agg(c order by c)
                from unnest(new.selected_columns) c
            ),
            '{}'::text[]
        );
    end if;

    return new;
end;
$$;


ALTER FUNCTION "realtime"."subscription_check_filters"() OWNER TO "supabase_realtime_admin";

--
-- Name: to_regrole("text"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."to_regrole"("role_name" "text") RETURNS "regrole"
    LANGUAGE "sql" IMMUTABLE
    AS $$ select role_name::regrole $$;


ALTER FUNCTION "realtime"."to_regrole"("role_name" "text") OWNER TO "supabase_realtime_admin";

--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."topic"() RETURNS "text"
    LANGUAGE "sql" STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


ALTER FUNCTION "realtime"."topic"() OWNER TO "supabase_realtime_admin";

--
-- Name: wal2json_escape_identifier("text"); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION "realtime"."wal2json_escape_identifier"("name" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE STRICT
    AS $$
  -- Prefix `\`, `,`, `.`, and any whitespace with `\`
  SELECT regexp_replace(name, '([\\,.[:space:]])', '\\\1', 'g')
$$;


ALTER FUNCTION "realtime"."wal2json_escape_identifier"("name" "text") OWNER TO "supabase_realtime_admin";

--
-- Name: allow_any_operation("text"[]); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."allow_any_operation"("expected_operations" "text"[]) RETURNS boolean
    LANGUAGE "sql" STABLE
    AS $$
  WITH current_operation AS (
    SELECT storage.operation() AS raw_operation
  ),
  normalized AS (
    SELECT CASE
      WHEN raw_operation LIKE 'storage.%' THEN substr(raw_operation, 9)
      ELSE raw_operation
    END AS current_operation
    FROM current_operation
  )
  SELECT EXISTS (
    SELECT 1
    FROM normalized n
    CROSS JOIN LATERAL unnest(expected_operations) AS expected_operation
    WHERE expected_operation IS NOT NULL
      AND expected_operation <> ''
      AND n.current_operation = CASE
        WHEN expected_operation LIKE 'storage.%' THEN substr(expected_operation, 9)
        ELSE expected_operation
      END
  );
$$;


ALTER FUNCTION "storage"."allow_any_operation"("expected_operations" "text"[]) OWNER TO "supabase_storage_admin";

--
-- Name: allow_only_operation("text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."allow_only_operation"("expected_operation" "text") RETURNS boolean
    LANGUAGE "sql" STABLE
    AS $$
  WITH current_operation AS (
    SELECT storage.operation() AS raw_operation
  ),
  normalized AS (
    SELECT
      CASE
        WHEN raw_operation LIKE 'storage.%' THEN substr(raw_operation, 9)
        ELSE raw_operation
      END AS current_operation,
      CASE
        WHEN expected_operation LIKE 'storage.%' THEN substr(expected_operation, 9)
        ELSE expected_operation
      END AS requested_operation
    FROM current_operation
  )
  SELECT CASE
    WHEN requested_operation IS NULL OR requested_operation = '' THEN FALSE
    ELSE COALESCE(current_operation = requested_operation, FALSE)
  END
  FROM normalized;
$$;


ALTER FUNCTION "storage"."allow_only_operation"("expected_operation" "text") OWNER TO "supabase_storage_admin";

--
-- Name: can_insert_object("text", "text", "uuid", "jsonb"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."can_insert_object"("bucketid" "text", "name" "text", "owner" "uuid", "metadata" "jsonb") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


ALTER FUNCTION "storage"."can_insert_object"("bucketid" "text", "name" "text", "owner" "uuid", "metadata" "jsonb") OWNER TO "supabase_storage_admin";

--
-- Name: enforce_bucket_lifecycle_service_role(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."enforce_bucket_lifecycle_service_role"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'pg_catalog'
    AS $$
BEGIN
  IF current_user::text IS DISTINCT FROM TG_ARGV[0]
     AND (
       OLD.lifecycle_configuration IS DISTINCT FROM NEW.lifecycle_configuration
       OR OLD.lifecycle_configuration_generation IS DISTINCT FROM NEW.lifecycle_configuration_generation
     ) THEN
    -- AFTER runs only after caller RLS has accepted the proposed row. The API
    -- recognizes this specific error after rolling back its permission probe;
    -- direct non-service writes still fail and cannot persist the change.
    RAISE EXCEPTION 'bucket control columns may only be changed by the configured storage service role'
      USING ERRCODE = 'PST01',
            SCHEMA = TG_TABLE_SCHEMA,
            TABLE = TG_TABLE_NAME,
            CONSTRAINT = TG_NAME;
  END IF;

  RETURN NULL;
END;
$$;


ALTER FUNCTION "storage"."enforce_bucket_lifecycle_service_role"() OWNER TO "supabase_storage_admin";

--
-- Name: enforce_bucket_name_length(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."enforce_bucket_name_length"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
    if length(new.name) > 100 then
        raise exception 'bucket name "%" is too long (% characters). Max is 100.', new.name, length(new.name);
    end if;
    return new;
end;
$$;


ALTER FUNCTION "storage"."enforce_bucket_name_length"() OWNER TO "supabase_storage_admin";

--
-- Name: extension("text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."extension"("name" "text") RETURNS "text"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
DECLARE
    _parts text[];
    _filename text;
BEGIN
    -- Split on "/" to get path segments
    SELECT string_to_array(name, '/') INTO _parts;
    -- Get the last path segment (the actual filename)
    SELECT _parts[array_length(_parts, 1)] INTO _filename;
    -- Extract extension: reverse, split on '.', then reverse again
    RETURN reverse(split_part(reverse(_filename), '.', 1));
END
$$;


ALTER FUNCTION "storage"."extension"("name" "text") OWNER TO "supabase_storage_admin";

--
-- Name: filename("text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."filename"("name" "text") RETURNS "text"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
DECLARE
    _parts text[];
BEGIN
    SELECT string_to_array(name, '/') INTO _parts;
    RETURN _parts[array_length(_parts, 1)];
END
$$;


ALTER FUNCTION "storage"."filename"("name" "text") OWNER TO "supabase_storage_admin";

--
-- Name: foldername("text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."foldername"("name" "text") RETURNS "text"[]
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
DECLARE
    _parts text[];
BEGIN
    -- Split on "/" to get path segments
    SELECT string_to_array(name, '/') INTO _parts;
    -- Return everything except the last segment
    RETURN _parts[1 : array_length(_parts,1) - 1];
END
$$;


ALTER FUNCTION "storage"."foldername"("name" "text") OWNER TO "supabase_storage_admin";

--
-- Name: get_common_prefix("text", "text", "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."get_common_prefix"("p_key" "text", "p_prefix" "text", "p_delimiter" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE
    AS $$
SELECT CASE
    WHEN p_delimiter <> ''
         AND position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1)) > 0
    THEN left(
        p_key,
        length(p_prefix)
            + position(p_delimiter IN substring(p_key FROM length(p_prefix) + 1))
            + length(p_delimiter) - 1
    )
    ELSE NULL
END;
$$;


ALTER FUNCTION "storage"."get_common_prefix"("p_key" "text", "p_prefix" "text", "p_delimiter" "text") OWNER TO "supabase_storage_admin";

--
-- Name: get_size_by_bucket("text", "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."get_size_by_bucket"("noncurrent_versions" "text" DEFAULT 'include'::"text", "delete_markers" "text" DEFAULT 'include'::"text") RETURNS TABLE("size" bigint, "bucket_id" "text")
    LANGUAGE "plpgsql" STABLE
    AS $$
BEGIN
    -- COALESCE first: NULL NOT IN (...) evaluates to NULL (not TRUE), so a
    -- bare NOT IN check silently leaves an explicit NULL argument unreset.
    noncurrent_versions := COALESCE(noncurrent_versions, 'include');
    delete_markers := COALESCE(delete_markers, 'include');
    IF noncurrent_versions NOT IN ('exclude', 'only', 'include') THEN
        noncurrent_versions := 'include';
    END IF;
    IF delete_markers NOT IN ('exclude', 'only', 'include') THEN
        delete_markers := 'include';
    END IF;

    return query
        select sum((metadata->>'size')::bigint)::bigint as size, obj.bucket_id
        from "storage".objects as obj
        where (noncurrent_versions != 'exclude' OR obj.archived_at IS NULL)
          and (noncurrent_versions != 'only' OR obj.archived_at IS NOT NULL)
          and (delete_markers != 'exclude' OR NOT obj.is_delete_marker)
          and (delete_markers != 'only' OR obj.is_delete_marker)
        group by obj.bucket_id;
END
$$;


ALTER FUNCTION "storage"."get_size_by_bucket"("noncurrent_versions" "text", "delete_markers" "text") OWNER TO "supabase_storage_admin";

--
-- Name: list_multipart_uploads_with_delimiter("text", "text", "text", integer, "text", "text", "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."list_multipart_uploads_with_delimiter"("bucket_id" "text", "prefix_param" "text", "delimiter_param" "text", "max_keys" integer DEFAULT 100, "next_key_token" "text" DEFAULT ''::"text", "next_upload_token" "text" DEFAULT ''::"text", "raw_prefix_param" "text" DEFAULT NULL::"text") RETURNS TABLE("key" "text", "id" "text", "created_at" timestamp with time zone)
    LANGUAGE "sql" STABLE
    AS $_$
WITH candidates AS (
    SELECT
        upload.key AS object_key,
        CASE
            WHEN position($3 IN substring(upload.key FROM length(coalesce($7, $2)) + 1)) > 0
            THEN left(
                upload.key,
                length(coalesce($7, $2))
                    + position($3 IN substring(upload.key FROM length(coalesce($7, $2)) + 1))
                    + length($3) - 1
            )
            ELSE upload.key
        END AS result_key,
        upload.id,
        upload.created_at,
        position($3 IN substring(upload.key FROM length(coalesce($7, $2)) + 1)) > 0 AS is_common_prefix
    FROM storage.s3_multipart_uploads AS upload
    WHERE upload.bucket_id = $1
      AND upload.key COLLATE "C" LIKE $2 || '%'
), filtered AS (
    SELECT candidate.*
    FROM candidates AS candidate
    WHERE $5 = ''
       OR candidate.result_key COLLATE "C" > $5
       OR (
           candidate.result_key COLLATE "C" = $5
           AND NOT candidate.is_common_prefix
           AND $6 <> ''
           -- A completed or aborted marker repeats the remaining same-key uploads.
           AND COALESCE(
               (candidate.created_at, candidate.id COLLATE "C") > (
                   SELECT marker.created_at, marker.id COLLATE "C"
                   FROM storage.s3_multipart_uploads AS marker
                   WHERE marker.bucket_id = $1
                     AND marker.key COLLATE "C" = $5
                     AND marker.id = $6
               ),
               TRUE
           )
       )
), ranked AS (
    SELECT
        filtered.*,
        row_number() OVER (
            PARTITION BY filtered.result_key COLLATE "C"
            ORDER BY filtered.created_at, filtered.id COLLATE "C"
        ) AS prefix_rank
    FROM filtered
)
SELECT ranked.result_key, ranked.id, ranked.created_at
FROM ranked
WHERE NOT ranked.is_common_prefix OR ranked.prefix_rank = 1
ORDER BY ranked.result_key COLLATE "C", ranked.created_at, ranked.id COLLATE "C"
LIMIT $4;
$_$;


ALTER FUNCTION "storage"."list_multipart_uploads_with_delimiter"("bucket_id" "text", "prefix_param" "text", "delimiter_param" "text", "max_keys" integer, "next_key_token" "text", "next_upload_token" "text", "raw_prefix_param" "text") OWNER TO "supabase_storage_admin";

--
-- Name: list_objects_with_delimiter("text", "text", "text", integer, "text", "text", "text", "text", "text", timestamp with time zone, "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."list_objects_with_delimiter"("_bucket_id" "text", "prefix_param" "text", "delimiter_param" "text", "max_keys" integer DEFAULT 100, "start_after" "text" DEFAULT ''::"text", "next_token" "text" DEFAULT ''::"text", "sort_order" "text" DEFAULT 'asc'::"text", "noncurrent_versions" "text" DEFAULT 'exclude'::"text", "delete_markers" "text" DEFAULT 'exclude'::"text", "next_token_archived_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "next_token_version" "text" DEFAULT ''::"text") RETURNS TABLE("name" "text", "id" "uuid", "metadata" "jsonb", "updated_at" timestamp with time zone, "created_at" timestamp with time zone, "last_accessed_at" timestamp with time zone, "version" "text", "archived_at" timestamp with time zone, "is_delete_marker" boolean, "is_versioned" boolean)
    LANGUAGE "plpgsql" STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;

    -- Configuration
    v_is_asc BOOLEAN;
    v_prefix TEXT;
    v_start TEXT;
    v_start_relative TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;
    v_version_filter TEXT;

    -- true when noncurrent_versions can return >1 row per name; keeps them
    -- ordered most-recent-first and lets pagination resume mid-key
    v_multi_row BOOLEAN;
    v_name_order TEXT;
    v_exact_range_predicate TEXT;
    v_strict_range_predicate TEXT;
    v_inclusive_range_predicate TEXT;

    -- Seek state for the current name. archived_at is normalized to JavaScript's
    -- millisecond precision and version breaks ties within the same millisecond.
    -- Current rows use 'infinity'; NULL means no tiebreak has been established.
    v_next_seek TEXT;
    v_next_seek_at TIMESTAMPTZ;
    v_next_seek_version TEXT;
    v_next_seek_strict BOOLEAN := false;
    v_cursor_is_folder BOOLEAN;
    v_count INT := 0;
    v_previous_seek TEXT;
    v_previous_seek_at TIMESTAMPTZ;
    v_previous_seek_version TEXT;
    v_previous_count INT;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;
    v_batch_query_strict TEXT;
    v_delete_marker_peek_query TEXT;
    v_delete_marker_peek_query_strict TEXT;

BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_is_asc := lower(coalesce(sort_order, 'asc')) = 'asc';
    v_prefix := coalesce(prefix_param, '');
    v_start := CASE WHEN coalesce(next_token, '') <> '' THEN next_token ELSE coalesce(start_after, '') END;
    v_file_batch_size := LEAST(GREATEST(max_keys * 2, 100), 1000);
    v_next_seek_at := NULL;
    v_next_seek_version := '';

    -- COALESCE first: NULL NOT IN (...) evaluates to NULL (not TRUE), so a
    -- bare NOT IN check silently leaves an explicit NULL argument unreset.
    noncurrent_versions := COALESCE(noncurrent_versions, 'exclude');
    delete_markers := COALESCE(delete_markers, 'exclude');
    IF noncurrent_versions NOT IN ('exclude', 'only', 'include') THEN
        noncurrent_versions := 'exclude';
    END IF;
    IF delete_markers NOT IN ('exclude', 'only', 'include') THEN
        delete_markers := 'exclude';
    END IF;

    v_multi_row := noncurrent_versions IN ('only', 'include');
    v_name_order := CASE WHEN v_is_asc THEN 'ASC' ELSE 'DESC' END;

    v_version_filter := '';
    IF noncurrent_versions = 'exclude' THEN
        v_version_filter := v_version_filter || ' AND o.archived_at IS NULL';
    ELSIF noncurrent_versions = 'only' THEN
        v_version_filter := v_version_filter || ' AND o.archived_at IS NOT NULL';
    END IF;
    IF delete_markers = 'exclude' THEN
        v_version_filter := v_version_filter || ' AND NOT o.is_delete_marker';
    ELSIF delete_markers = 'only' THEN
        v_version_filter := v_version_filter || ' AND o.is_delete_marker';
    END IF;

    -- Calculate upper bound for prefix filtering (bytewise, using COLLATE "C")
    IF v_prefix = '' THEN
        v_upper_bound := NULL;
    ELSE
        v_upper_bound := left(v_prefix, -1) || chr(ascii(right(v_prefix, 1)) + 1);
    END IF;

    -- Keep caller-provided cursors inside the requested prefix range.
    IF v_start <> '' AND v_upper_bound IS NOT NULL THEN
        IF v_is_asc THEN
            IF v_start COLLATE "C" < v_prefix COLLATE "C" THEN
                v_start := '';
            ELSIF v_start COLLATE "C" >= v_upper_bound COLLATE "C" THEN
                RETURN;
            END IF;
        ELSE
            IF v_start COLLATE "C" < v_prefix COLLATE "C" THEN
                RETURN;
            ELSIF v_start COLLATE "C" >= v_upper_bound COLLATE "C" THEN
                v_start := '';
            END IF;
        END IF;
    END IF;

    v_start_relative := substring(v_start FROM length(v_prefix) + 1);

    -- Direction affects only the indexed name range and its ordering. Cursor
    -- state transitions and within-key version ordering stay shared.
    IF v_is_asc THEN
        v_exact_range_predicate := 'TRUE';
        v_strict_range_predicate := 'o.name COLLATE "C" > $2';
        v_inclusive_range_predicate := 'o.name COLLATE "C" >= $2';
        IF v_upper_bound IS NOT NULL THEN
            v_exact_range_predicate := 'o.name COLLATE "C" < $3';
            v_strict_range_predicate := v_strict_range_predicate || ' AND o.name COLLATE "C" < $3';
            v_inclusive_range_predicate := v_inclusive_range_predicate || ' AND o.name COLLATE "C" < $3';
        END IF;
    ELSE
        v_exact_range_predicate := 'TRUE';
        v_strict_range_predicate := 'o.name COLLATE "C" < $2';
        v_inclusive_range_predicate := 'o.name COLLATE "C" < $2';
        IF v_prefix <> '' THEN
            v_exact_range_predicate := 'o.name COLLATE "C" >= $3';
            v_strict_range_predicate := v_strict_range_predicate || ' AND o.name COLLATE "C" >= $3';
            v_inclusive_range_predicate := v_inclusive_range_predicate || ' AND o.name COLLATE "C" >= $3';
        END IF;
    END IF;

    -- Build batch query (dynamic SQL - called infrequently, amortized over many rows)
    -- The multi-row order matches the externally serialized cursor exactly:
    -- archived_at at millisecond precision, then version as the final tiebreak.
    --
    -- When v_multi_row, the seek is a keyset tuple comparison ("name > $2 OR
    -- (name = $2 AND tiebreak)") - Postgres won't split that OR into indexable
    -- form (confirmed even with fully literal values), so as one WHERE clause
    -- it forces a full bucket scan filtered row-by-row. Splitting it into two
    -- independently-indexable branches (exact name match with the tiebreak
    -- filter, vs. strictly-past names) combined with UNION ALL lets each
    -- branch keep name as a real index condition; the outer ORDER BY/LIMIT
    -- re-merges them into the same page the single query used to produce.
    IF v_multi_row THEN
        v_batch_query := format(
            $sql$
            SELECT *
            FROM (
                (
                    SELECT o.name, o.id, o.updated_at, o.created_at,
                           o.last_accessed_at, o.metadata, o.version,
                           o.archived_at, o.is_delete_marker, o.is_versioned
                    FROM storage.objects o
                    WHERE o.bucket_id = $1
                      AND o.name COLLATE "C" = $2
                      AND %s
                      AND NOT $7::boolean
                      AND (
                          $5::timestamptz IS NULL
                          OR COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) < $5
                          OR (
                              COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) = $5
                              AND COALESCE(o.version, '') > $6
                          )
                      )
                      %s
                    ORDER BY
                        COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC,
                        COALESCE(o.version, '') ASC
                    LIMIT $4
                )
                UNION ALL
                (
                    SELECT o.name, o.id, o.updated_at, o.created_at,
                           o.last_accessed_at, o.metadata, o.version,
                           o.archived_at, o.is_delete_marker, o.is_versioned
                    FROM storage.objects o
                    WHERE o.bucket_id = $1
                      AND %s
                      %s
                    ORDER BY
                        o.name COLLATE "C" %s,
                        COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC,
                        COALESCE(o.version, '') ASC
                    LIMIT $4
                )
            ) sub
            ORDER BY
                sub.name COLLATE "C" %s,
                COALESCE(date_trunc('milliseconds', sub.archived_at), 'infinity'::timestamptz) DESC,
                COALESCE(sub.version, '') ASC
            LIMIT $4
            $sql$,
            v_exact_range_predicate,
            v_version_filter,
            v_strict_range_predicate,
            v_version_filter,
            v_name_order,
            v_name_order
        );
    ELSE
        v_batch_query := format(
            $sql$
            SELECT o.name, o.id, o.updated_at, o.created_at,
                   o.last_accessed_at, o.metadata, o.version,
                   o.archived_at, o.is_delete_marker, o.is_versioned
            FROM storage.objects o
            WHERE o.bucket_id = $1
              AND %s
              %s
            ORDER BY o.name COLLATE "C" %s, o.archived_at DESC
            LIMIT $4
            $sql$,
            v_inclusive_range_predicate,
            v_version_filter,
            v_name_order
        );

        -- Strict counterpart of the query above: used once the single-row
        -- ASC batch advance (below) has left v_next_seek pointing at the
        -- last row already emitted, so an inclusive predicate would
        -- re-match it forever. Only single-row mode ever sets strict mode,
        -- so this variant is never needed when v_multi_row.
        v_batch_query_strict := format(
            $sql$
            SELECT o.name, o.id, o.updated_at, o.created_at,
                   o.last_accessed_at, o.metadata, o.version,
                   o.archived_at, o.is_delete_marker, o.is_versioned
            FROM storage.objects o
            WHERE o.bucket_id = $1
              AND %s
              %s
            ORDER BY o.name COLLATE "C" %s, o.archived_at DESC
            LIMIT $4
            $sql$,
            v_strict_range_predicate,
            v_version_filter,
            v_name_order
        );
    END IF;

    -- The static peek predicates cannot use the partial delete-marker index
    -- once PL/pgSQL switches to a generic plan because whether
    -- is_delete_marker is required remains parameter-dependent. Reuse the
    -- already-specialized batch query with a one-row limit for this sparse
    -- filter so the plan sees a literal `o.is_delete_marker` predicate.
    IF delete_markers = 'only' THEN
        v_delete_marker_peek_query :=
            'SELECT marker_page.name FROM (' || v_batch_query || ') marker_page LIMIT 1';
        IF NOT v_multi_row THEN
            v_delete_marker_peek_query_strict :=
                'SELECT marker_page.name FROM (' || v_batch_query_strict || ') marker_page LIMIT 1';
        END IF;
    END IF;

    -- ========================================================================
    -- SEEK INITIALIZATION: Determine starting position
    -- ========================================================================
    IF v_start = '' THEN
        IF v_is_asc THEN
            v_next_seek := v_prefix;
        ELSE
            -- DESC without cursor performs one specialized initial seek so
            -- partial current-version and delete-marker indexes remain available.
            EXECUTE format(
                'SELECT o.name FROM storage.objects o WHERE o.bucket_id = $1%s%s ORDER BY o.name COLLATE "C" DESC LIMIT 1',
                CASE WHEN v_upper_bound IS NOT NULL
                    THEN ' AND o.name COLLATE "C" >= $2 AND o.name COLLATE "C" < $3'
                    ELSE ''
                END,
                v_version_filter
            )
            INTO v_next_seek
            USING _bucket_id, v_prefix, v_upper_bound;

            IF v_next_seek IS NOT NULL THEN
                v_next_seek := v_next_seek || delimiter_param;
            ELSE
                RETURN;
            END IF;
        END IF;
    ELSE
        -- Folder continuation tokens retain their trailing delimiter. A
        -- delimiter-less startAfter is always a literal key boundary.
        v_cursor_is_folder := delimiter_param <> ''
            AND v_start_relative <> ''
            AND right(v_start_relative, length(delimiter_param)) = delimiter_param;

        IF v_cursor_is_folder THEN
            v_next_seek := CASE
                WHEN right(v_start, length(delimiter_param)) = delimiter_param
                    THEN v_start
                ELSE v_start || delimiter_param
            END;
            IF v_is_asc THEN
                v_next_seek := left(v_next_seek, -1)
                    || chr(ascii(right(v_next_seek, 1)) + 1);
            END IF;
            v_next_seek_strict := NOT v_is_asc;
        ELSE
            -- leaf object: when v_multi_row, stay on v_start with the
            -- caller-supplied tiebreak so a page boundary mid-key resumes
            -- that key's remaining rows instead of skipping them. Truncate
            -- to milliseconds like every other v_next_seek_at assignment -
            -- harmless today since object.ts's cursor always round-trips
            -- through JS Date first, but this shouldn't rely on that.
            IF v_multi_row THEN
                v_next_seek := v_start;
                v_next_seek_at := date_trunc('milliseconds', next_token_archived_at);
                v_next_seek_version := coalesce(next_token_version, '');
                v_next_seek_strict := coalesce(next_token, '') = '';
            ELSIF v_is_asc THEN
                v_next_seek := v_start;
                v_next_seek_strict := true;
            ELSE
                v_next_seek := v_start;
            END IF;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= max_keys;

        v_previous_seek := v_next_seek;
        v_previous_seek_at := v_next_seek_at;
        v_previous_seek_version := v_next_seek_version;
        v_previous_count := v_count;

        -- STEP 1: PEEK using STATIC SQL (plan cached, very fast)
        -- v_multi_row is branched here (rather than folded into the WHERE
        -- clause as a bound parameter) so each concrete query keeps an
        -- unconditional seek predicate - once PL/pgSQL switches to its
        -- cached generic plan (after 5 calls), a parameter-gated
        -- "(NOT v_multi_row AND name >= $x) OR (v_multi_row AND ...)"
        -- predicate stops the planner from using name as an index
        -- condition at all, degrading every subsequent peek to a full
        -- index scan filtered row-by-row instead of a bounded range scan.
        -- v_multi_row's seek predicate is a keyset tuple comparison
        -- ("name > x OR (name = x AND tiebreak)") - Postgres does not
        -- split this OR into indexable form even with fully literal
        -- values, so it falls back to a full scan filtered row-by-row.
        -- Splitting it into two independently-indexable branches (exact
        -- name match with the tiebreak filter, vs. strictly-past name)
        -- combined with UNION ALL lets each branch keep name as a real
        -- index condition; the outer ORDER BY/LIMIT picks whichever of
        -- the (at most 2) rows sorts first.
        IF delete_markers = 'only' THEN
            EXECUTE CASE WHEN v_next_seek_strict AND NOT v_multi_row
                THEN v_delete_marker_peek_query_strict
                ELSE v_delete_marker_peek_query
            END
                INTO v_peek_name
                USING _bucket_id, v_next_seek,
                    CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix) ELSE v_prefix END,
                    1, v_next_seek_at, v_next_seek_version, v_next_seek_strict;
        ELSIF v_multi_row THEN
            IF v_is_asc THEN
                IF v_upper_bound IS NOT NULL THEN
                    SELECT sub.name INTO v_peek_name FROM (
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" = v_next_seek
                           AND o.name COLLATE "C" < v_upper_bound
                           AND NOT v_next_seek_strict
                           AND (v_next_seek_at IS NULL
                                OR COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) < v_next_seek_at
                                OR (COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) = v_next_seek_at
                                    AND COALESCE(o.version, '') > v_next_seek_version))
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC, COALESCE(o.version, '') ASC LIMIT 1)
                        UNION ALL
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" > v_next_seek AND o.name COLLATE "C" < v_upper_bound
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY o.name COLLATE "C" ASC LIMIT 1)
                    ) sub ORDER BY sub.name COLLATE "C" ASC LIMIT 1;
                ELSE
                    SELECT sub.name INTO v_peek_name FROM (
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" = v_next_seek
                           AND NOT v_next_seek_strict
                           AND (v_next_seek_at IS NULL
                                OR COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) < v_next_seek_at
                                OR (COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) = v_next_seek_at
                                    AND COALESCE(o.version, '') > v_next_seek_version))
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC, COALESCE(o.version, '') ASC LIMIT 1)
                        UNION ALL
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" > v_next_seek
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY o.name COLLATE "C" ASC LIMIT 1)
                    ) sub ORDER BY sub.name COLLATE "C" ASC LIMIT 1;
                END IF;
            ELSE
                IF v_upper_bound IS NOT NULL THEN
                    SELECT sub.name INTO v_peek_name FROM (
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" = v_next_seek
                           AND o.name COLLATE "C" >= v_prefix
                           AND NOT v_next_seek_strict
                           AND (v_next_seek_at IS NULL
                                OR COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) < v_next_seek_at
                                OR (COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) = v_next_seek_at
                                    AND COALESCE(o.version, '') > v_next_seek_version))
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC, COALESCE(o.version, '') ASC LIMIT 1)
                        UNION ALL
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek AND o.name COLLATE "C" >= v_prefix
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY o.name COLLATE "C" DESC LIMIT 1)
                    ) sub ORDER BY sub.name COLLATE "C" DESC LIMIT 1;
                ELSE
                    SELECT sub.name INTO v_peek_name FROM (
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" = v_next_seek
                           AND NOT v_next_seek_strict
                           AND (v_next_seek_at IS NULL
                                OR COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) < v_next_seek_at
                                OR (COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) = v_next_seek_at
                                    AND COALESCE(o.version, '') > v_next_seek_version))
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY COALESCE(date_trunc('milliseconds', o.archived_at), 'infinity'::timestamptz) DESC, COALESCE(o.version, '') ASC LIMIT 1)
                        UNION ALL
                        (SELECT o.name FROM storage.objects o
                         WHERE o.bucket_id = _bucket_id AND o.name COLLATE "C" < v_next_seek
                           AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                           AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                           AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                           AND (delete_markers != 'only' OR o.is_delete_marker)
                         ORDER BY o.name COLLATE "C" DESC LIMIT 1)
                    ) sub ORDER BY sub.name COLLATE "C" DESC LIMIT 1;
                END IF;
            END IF;
        ELSE
            -- Single-row mode is always noncurrent_versions='exclude'. Keep
            -- this predicate literal so generic plans use the current index.
            IF v_is_asc THEN
                IF v_next_seek_strict AND v_upper_bound IS NOT NULL THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" > v_next_seek
                      AND o.name COLLATE "C" < v_upper_bound
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" ASC LIMIT 1;
                ELSIF v_next_seek_strict THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" > v_next_seek
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" ASC LIMIT 1;
                ELSIF v_upper_bound IS NOT NULL THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" >= v_next_seek
                      AND o.name COLLATE "C" < v_upper_bound
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" ASC LIMIT 1;
                ELSE
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" >= v_next_seek
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" ASC LIMIT 1;
                END IF;
            ELSE
                IF v_upper_bound IS NOT NULL THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" < v_next_seek
                      AND o.name COLLATE "C" >= v_prefix
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" DESC LIMIT 1;
                ELSE
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = _bucket_id
                      AND o.name COLLATE "C" < v_next_seek
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                      AND (delete_markers != 'only' OR o.is_delete_marker)
                    ORDER BY o.name COLLATE "C" DESC LIMIT 1;
                END IF;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(v_peek_name, v_prefix, delimiter_param);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Emit and skip to next folder (no heap access needed)
            name := v_common_prefix;
            id := NULL;
            updated_at := NULL;
            created_at := NULL;
            last_accessed_at := NULL;
            metadata := NULL;
            version := NULL;
            archived_at := NULL;
            is_delete_marker := NULL;
            is_versioned := NULL;
            RETURN NEXT;
            v_count := v_count + 1;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := left(v_common_prefix, -1)
                    || chr(ascii(right(v_common_prefix, 1)) + 1);
            ELSE
                v_next_seek := v_common_prefix;
            END IF;
            v_next_seek_at := NULL;
            v_next_seek_version := '';
            v_next_seek_strict := NOT v_is_asc;
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE CASE WHEN v_next_seek_strict AND NOT v_multi_row THEN v_batch_query_strict ELSE v_batch_query END
                USING _bucket_id, v_next_seek,
                CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix) ELSE v_prefix END, v_file_batch_size, v_next_seek_at, v_next_seek_version,
                v_next_seek_strict
            LOOP
                v_common_prefix := storage.get_common_prefix(v_current.name, v_prefix, delimiter_param);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it. Reset
                    -- strict mode too it may have been set by an earlier
                    -- row in this same batch (see the single-row ASC advance
                    -- below), and v_next_seek here is the folder-triggering
                    -- row's own name, which the next peek must find inclusively.
                    v_next_seek := CASE
                        WHEN v_is_asc THEN v_current.name
                        ELSE v_current.name || delimiter_param
                    END;
                    v_next_seek_at := NULL;
                    v_next_seek_version := '';
                    v_next_seek_strict := false;
                    EXIT;
                END IF;

                -- Emit file
                name := v_current.name;
                id := v_current.id;
                updated_at := v_current.updated_at;
                created_at := v_current.created_at;
                last_accessed_at := v_current.last_accessed_at;
                metadata := v_current.metadata;
                version := v_current.version;
                archived_at := v_current.archived_at;
                is_delete_marker := v_current.is_delete_marker;
                is_versioned := v_current.is_versioned;
                RETURN NEXT;
                v_count := v_count + 1;

                -- when v_multi_row, stay on this name and record its
                -- archived_at as the new tiebreak so remaining rows for the
                -- same key are picked up before moving to the next name
                IF v_multi_row THEN
                    v_next_seek := v_current.name;
                    v_next_seek_at := COALESCE(date_trunc('milliseconds', v_current.archived_at), 'infinity'::timestamptz);
                    v_next_seek_version := COALESCE(v_current.version, '');
                    v_next_seek_strict := false;
                ELSIF v_is_asc THEN
                    -- Appending the delimiter as a fake lexical successor
                    -- would skip a real key like `name || '!'` (or any
                    -- character sorting below the delimiter), which sorts
                    -- between `name` and `name || delimiter`. Track the real
                    -- name and mark the next comparison strict instead.
                    v_next_seek := v_current.name;
                    v_next_seek_strict := true;
                ELSE
                    v_next_seek := v_current.name;
                END IF;

                EXIT WHEN v_count >= max_keys;
            END LOOP;
        END IF;

        IF v_count = v_previous_count
           AND v_next_seek IS NOT DISTINCT FROM v_previous_seek
           AND v_next_seek_at IS NOT DISTINCT FROM v_previous_seek_at
           AND v_next_seek_version IS NOT DISTINCT FROM v_previous_seek_version THEN
            RAISE EXCEPTION 'storage.list_objects_with_delimiter made no progress at seek (%, %, %)',
                v_next_seek, v_next_seek_at, v_next_seek_version;
        END IF;
    END LOOP;
END;
$_$;


ALTER FUNCTION "storage"."list_objects_with_delimiter"("_bucket_id" "text", "prefix_param" "text", "delimiter_param" "text", "max_keys" integer, "start_after" "text", "next_token" "text", "sort_order" "text", "noncurrent_versions" "text", "delete_markers" "text", "next_token_archived_at" timestamp with time zone, "next_token_version" "text") OWNER TO "supabase_storage_admin";

--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."operation"() RETURNS "text"
    LANGUAGE "plpgsql" STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


ALTER FUNCTION "storage"."operation"() OWNER TO "supabase_storage_admin";

--
-- Name: protect_bucket_control_columns(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."protect_bucket_control_columns"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'pg_catalog'
    AS $$
DECLARE
  configuration_changed boolean;
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.lifecycle_configuration IS NOT NULL
       OR NEW.lifecycle_configuration_generation IS NOT NULL THEN
      IF NOT pg_has_role(current_user, TG_ARGV[0], 'MEMBER') THEN
        RAISE EXCEPTION 'only members of the configured storage service role may insert lifecycle policy state'
          USING ERRCODE = '42501',
                HINT = format(
                  'Insert with both lifecycle columns NULL and configure lifecycle through the Storage API afterward, or insert as a member of %I.',
                  TG_ARGV[0]
                );
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  configuration_changed =
    OLD.lifecycle_configuration IS DISTINCT FROM NEW.lifecycle_configuration
    OR OLD.lifecycle_configuration_generation IS DISTINCT FROM NEW.lifecycle_configuration_generation;

  IF NOT configuration_changed THEN
    RETURN NEW;
  END IF;

  IF NEW.type IS DISTINCT FROM 'STANDARD' THEN
    RAISE EXCEPTION 'bucket versioning and lifecycle controls require a Standard bucket'
      USING ERRCODE = '0A000';
  END IF;

  IF NEW.lifecycle_configuration IS NULL
     AND NEW.lifecycle_configuration_generation IS NULL THEN
    RETURN NEW;
  END IF;

  IF NEW.lifecycle_configuration IS NULL
     OR NEW.lifecycle_configuration_generation IS NULL
     OR OLD.lifecycle_configuration IS NOT DISTINCT FROM NEW.lifecycle_configuration
     OR OLD.lifecycle_configuration_generation IS NOT DISTINCT FROM NEW.lifecycle_configuration_generation THEN
    RAISE EXCEPTION 'a changed lifecycle policy requires a new non-null generation'
      USING ERRCODE = '22023';
  END IF;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "storage"."protect_bucket_control_columns"() OWNER TO "supabase_storage_admin";

--
-- Name: protect_delete(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."protect_delete"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    -- Check if storage.allow_delete_query is set to 'true'
    IF COALESCE(current_setting('storage.allow_delete_query', true), 'false') != 'true' THEN
        RAISE EXCEPTION 'Direct deletion from storage tables is not allowed. Use the Storage API instead.'
            USING HINT = 'This prevents accidental data loss from orphaned objects.',
                  ERRCODE = '42501';
    END IF;
    RETURN NULL;
END;
$$;


ALTER FUNCTION "storage"."protect_delete"() OWNER TO "supabase_storage_admin";

--
-- Name: search("text", "text", integer, integer, integer, "text", "text", "text", "text", "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."search"("prefix" "text", "bucketname" "text", "limits" integer DEFAULT 100, "levels" integer DEFAULT 1, "offsets" integer DEFAULT 0, "search" "text" DEFAULT ''::"text", "sortcolumn" "text" DEFAULT 'name'::"text", "sortorder" "text" DEFAULT 'asc'::"text", "noncurrent_versions" "text" DEFAULT 'exclude'::"text", "delete_markers" "text" DEFAULT 'exclude'::"text") RETURNS TABLE("name" "text", "id" "uuid", "updated_at" timestamp with time zone, "created_at" timestamp with time zone, "last_accessed_at" timestamp with time zone, "metadata" "jsonb", "version" "text", "archived_at" timestamp with time zone, "is_delete_marker" boolean, "is_versioned" boolean)
    LANGUAGE "plpgsql" STABLE
    AS $_$
DECLARE
    v_peek_name TEXT;
    v_current RECORD;
    v_common_prefix TEXT;
    v_delimiter CONSTANT TEXT := '/';

    -- Configuration
    v_limit INT;
    v_prefix TEXT;
    v_prefix_lower TEXT;
    v_prefix_len INT;
    v_prefix_start INT;
    v_combined_levels INT;
    v_is_asc BOOLEAN;
    v_order_by TEXT;
    v_sort_order TEXT;
    v_upper_bound TEXT;
    v_file_batch_size INT;
    v_version_filter TEXT;
    v_multi_row BOOLEAN;

    -- Dynamic SQL for batch query only
    v_batch_query TEXT;
    v_delete_marker_peek_query TEXT;
    v_delete_marker_peek_query_strict TEXT;

    -- Seek state
    v_next_seek TEXT;
    v_next_seek_at TIMESTAMPTZ;
    v_next_seek_version TEXT;
    v_next_seek_strict BOOLEAN := false;
    v_count INT := 0;
    v_skipped INT := 0;
    v_previous_seek TEXT;
    v_previous_seek_at TIMESTAMPTZ;
    v_previous_seek_version TEXT;
    v_previous_count INT;
    v_previous_skipped INT;
BEGIN
    -- ========================================================================
    -- INITIALIZATION
    -- ========================================================================
    v_limit := LEAST(coalesce(limits, 100), 1500);
    v_prefix := coalesce(prefix, '') || coalesce(search, '');
    v_prefix_lower := lower(v_prefix);
    v_prefix_len := length(coalesce(prefix, ''));
    v_prefix_start := coalesce(array_length(string_to_array(coalesce(prefix, ''), v_delimiter), 1), 1);
    v_combined_levels := coalesce(array_length(string_to_array(v_prefix, v_delimiter), 1), 1);
    v_is_asc := lower(coalesce(sortorder, 'asc')) = 'asc';
    v_file_batch_size := LEAST(GREATEST(v_limit * 2, 100), 1000);
    v_next_seek_at := NULL;
    v_next_seek_version := '';

    -- COALESCE first: NULL NOT IN (...) evaluates to NULL (not TRUE), so a
    -- bare NOT IN check silently leaves an explicit NULL argument unreset.
    noncurrent_versions := COALESCE(noncurrent_versions, 'exclude');
    delete_markers := COALESCE(delete_markers, 'exclude');
    IF noncurrent_versions NOT IN ('exclude', 'only', 'include') THEN
        noncurrent_versions := 'exclude';
    END IF;
    IF delete_markers NOT IN ('exclude', 'only', 'include') THEN
        delete_markers := 'exclude';
    END IF;

    v_multi_row := noncurrent_versions IN ('only', 'include');

    v_version_filter := '';
    IF noncurrent_versions = 'exclude' THEN
        v_version_filter := v_version_filter || ' AND o.archived_at IS NULL';
    ELSIF noncurrent_versions = 'only' THEN
        v_version_filter := v_version_filter || ' AND o.archived_at IS NOT NULL';
    END IF;
    IF delete_markers = 'exclude' THEN
        v_version_filter := v_version_filter || ' AND NOT o.is_delete_marker';
    ELSIF delete_markers = 'only' THEN
        v_version_filter := v_version_filter || ' AND o.is_delete_marker';
    END IF;

    -- Validate sort column
    CASE lower(coalesce(sortcolumn, 'name'))
        WHEN 'name' THEN v_order_by := 'name';
        WHEN 'updated_at' THEN v_order_by := 'updated_at';
        WHEN 'created_at' THEN v_order_by := 'created_at';
        WHEN 'last_accessed_at' THEN v_order_by := 'last_accessed_at';
        ELSE v_order_by := 'name';
    END CASE;

    v_sort_order := CASE WHEN v_is_asc THEN 'asc' ELSE 'desc' END;

    -- ========================================================================
    -- NON-NAME SORTING: Use path_tokens approach
    -- ========================================================================
    IF v_order_by != 'name' THEN
        RETURN QUERY EXECUTE format(
            $sql$
            WITH folders AS (
                SELECT array_to_string(path_tokens[$1:$2], '/') AS folder
                FROM storage.objects
                WHERE objects.name ILIKE $3 || '%%'
                  AND bucket_id = $4
                  AND array_length(objects.path_tokens, 1) <> $2
                  AND ($7 != 'exclude' OR objects.archived_at IS NULL)
                  AND ($7 != 'only' OR objects.archived_at IS NOT NULL)
                  AND ($8 != 'exclude' OR NOT objects.is_delete_marker)
                  AND ($8 != 'only' OR objects.is_delete_marker)
                GROUP BY folder
                ORDER BY folder %s
            )
            (SELECT folder AS "name",
                   NULL::uuid AS id,
                   NULL::timestamptz AS updated_at,
                   NULL::timestamptz AS created_at,
                   NULL::timestamptz AS last_accessed_at,
                   NULL::jsonb AS metadata,
                   NULL::text AS version,
                   NULL::timestamptz AS archived_at,
                   NULL::boolean AS is_delete_marker,
                   NULL::boolean AS is_versioned FROM folders)
            UNION ALL
            (SELECT array_to_string(path_tokens[$1:$2], '/') AS "name",
                   id, updated_at, created_at, last_accessed_at, metadata,
                   version, archived_at, is_delete_marker, is_versioned
             FROM storage.objects
             WHERE objects.name ILIKE $3 || '%%'
               AND bucket_id = $4
               AND array_length(objects.path_tokens, 1) = $2
               AND ($7 != 'exclude' OR objects.archived_at IS NULL)
               AND ($7 != 'only' OR objects.archived_at IS NOT NULL)
               AND ($8 != 'exclude' OR NOT objects.is_delete_marker)
               AND ($8 != 'only' OR objects.is_delete_marker)
             -- name, then version, as tiebreaks so two versions of the same
             -- key tying on the sort column still sort deterministically
             ORDER BY %I %s, name COLLATE "C" %s, COALESCE(version, '') %s)
            LIMIT $5 OFFSET $6
            $sql$, v_sort_order, v_order_by, v_sort_order, v_sort_order, v_sort_order
        ) USING v_prefix_start, v_combined_levels, v_prefix, bucketname, v_limit, offsets, noncurrent_versions, delete_markers;
        RETURN;
    END IF;

    -- ========================================================================
    -- NAME SORTING: Hybrid skip-scan with batch optimization
    -- ========================================================================

    -- Calculate upper bound for prefix filtering
    IF v_prefix_lower = '' THEN
        v_upper_bound := NULL;
    ELSIF right(v_prefix_lower, 1) = v_delimiter THEN
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(v_delimiter) + 1);
    ELSE
        v_upper_bound := left(v_prefix_lower, -1) || chr(ascii(right(v_prefix_lower, 1)) + 1);
    END IF;

    -- Build a resume-safe batch query. The exact-name branch returns remaining
    -- versions after the current (archived_at, version) boundary; the strict
    -- name branch returns subsequent keys. UNION ALL keeps both predicates
    -- independently indexable.
    IF v_is_asc THEN
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT * FROM (' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" = $2 AND ($5::timestamptz IS NULL OR COALESCE(o.archived_at, ''infinity''::timestamptz) < $5 OR (COALESCE(o.archived_at, ''infinity''::timestamptz) = $5 AND COALESCE(o.version, '''') > $6))' ||
                v_version_filter || ' ORDER BY COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4) UNION ALL ' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" > $2 AND lower(o.name) COLLATE "C" < $3' || v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" ASC, COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4)' ||
                ') sub ORDER BY lower(sub.name) COLLATE "C" ASC, COALESCE(sub.archived_at, ''infinity''::timestamptz) DESC, COALESCE(sub.version, '''') ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT * FROM (' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" = $2 AND ($5::timestamptz IS NULL OR COALESCE(o.archived_at, ''infinity''::timestamptz) < $5 OR (COALESCE(o.archived_at, ''infinity''::timestamptz) = $5 AND COALESCE(o.version, '''') > $6))' ||
                v_version_filter || ' ORDER BY COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4) UNION ALL ' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" > $2' || v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" ASC, COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4)' ||
                ') sub ORDER BY lower(sub.name) COLLATE "C" ASC, COALESCE(sub.archived_at, ''infinity''::timestamptz) DESC, COALESCE(sub.version, '''') ASC LIMIT $4';
        END IF;
    ELSE
        IF v_upper_bound IS NOT NULL THEN
            v_batch_query := 'SELECT * FROM (' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" = $2 AND ($5::timestamptz IS NULL OR COALESCE(o.archived_at, ''infinity''::timestamptz) < $5 OR (COALESCE(o.archived_at, ''infinity''::timestamptz) = $5 AND COALESCE(o.version, '''') > $6))' ||
                v_version_filter || ' ORDER BY COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4) UNION ALL ' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2 AND lower(o.name) COLLATE "C" >= $3' || v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" DESC, COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4)' ||
                ') sub ORDER BY lower(sub.name) COLLATE "C" DESC, COALESCE(sub.archived_at, ''infinity''::timestamptz) DESC, COALESCE(sub.version, '''') ASC LIMIT $4';
        ELSE
            v_batch_query := 'SELECT * FROM (' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" = $2 AND ($5::timestamptz IS NULL OR COALESCE(o.archived_at, ''infinity''::timestamptz) < $5 OR (COALESCE(o.archived_at, ''infinity''::timestamptz) = $5 AND COALESCE(o.version, '''') > $6))' ||
                v_version_filter || ' ORDER BY COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4) UNION ALL ' ||
                '(SELECT o.name, o.id, o.updated_at, o.created_at, o.last_accessed_at, o.metadata, o.version, o.archived_at, o.is_delete_marker, o.is_versioned FROM storage.objects o ' ||
                'WHERE o.bucket_id = $1 AND lower(o.name) COLLATE "C" < $2' || v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" DESC, COALESCE(o.archived_at, ''infinity''::timestamptz) DESC, COALESCE(o.version, '''') ASC LIMIT $4)' ||
                ') sub ORDER BY lower(sub.name) COLLATE "C" DESC, COALESCE(sub.archived_at, ''infinity''::timestamptz) DESC, COALESCE(sub.version, '''') ASC LIMIT $4';
        END IF;
    END IF;

    -- Keep the delete-marker predicate literal so the cached generic
    -- plan can use idx_objects_delete_markers during the main-loop peek.
    IF delete_markers = 'only' THEN
        IF v_multi_row THEN
            v_delete_marker_peek_query :=
                'SELECT marker_page.name FROM (' || v_batch_query || ') marker_page LIMIT 1';
        ELSIF v_is_asc THEN
            -- Two separate literal query strings, not one gated by a bound
            -- boolean: folding "$n AND op1 OR NOT $n AND op2" into a single
            -- query defeats the generic plan's ability to push either
            -- comparison into the index. Branching in PL/pgSQL control flow
            -- instead keeps each query's index condition intact.
            v_delete_marker_peek_query :=
                'SELECT o.name FROM storage.objects o WHERE o.bucket_id = $1 ' ||
                'AND lower(o.name) COLLATE "C" >= $2' ||
                CASE WHEN v_upper_bound IS NOT NULL
                    THEN ' AND lower(o.name) COLLATE "C" < $3'
                    ELSE ''
                END ||
                v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1';
            -- Strict variant: used once the single-row ASC batch advance
            -- (below) has left v_next_seek pointing at the last row already
            -- emitted, so a plain >= would re-match it forever.
            v_delete_marker_peek_query_strict :=
                'SELECT o.name FROM storage.objects o WHERE o.bucket_id = $1 ' ||
                'AND lower(o.name) COLLATE "C" > $2' ||
                CASE WHEN v_upper_bound IS NOT NULL
                    THEN ' AND lower(o.name) COLLATE "C" < $3'
                    ELSE ''
                END ||
                v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1';
        ELSE
            v_delete_marker_peek_query :=
                'SELECT o.name FROM storage.objects o WHERE o.bucket_id = $1 ' ||
                'AND lower(o.name) COLLATE "C" < $2' ||
                CASE WHEN v_upper_bound IS NOT NULL
                    THEN ' AND lower(o.name) COLLATE "C" >= $3'
                    ELSE ''
                END ||
                v_version_filter ||
                ' ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1';
        END IF;
    END IF;

    -- Initialize seek position
    IF v_is_asc THEN
        v_next_seek := v_prefix_lower;
    ELSE
        -- DESC performs one specialized initial seek so partial current-version
        -- and delete-marker indexes remain available.
        EXECUTE format(
            'SELECT o.name FROM storage.objects o WHERE o.bucket_id = $1%s%s ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1',
            CASE WHEN v_upper_bound IS NOT NULL
                THEN ' AND lower(o.name) COLLATE "C" >= $2 AND lower(o.name) COLLATE "C" < $3'
                ELSE ''
            END,
            v_version_filter
        )
        INTO v_peek_name
        USING bucketname, v_prefix_lower, v_upper_bound;

        IF v_peek_name IS NOT NULL THEN
            v_next_seek := lower(v_peek_name) || v_delimiter;
        ELSE
            RETURN;
        END IF;
    END IF;

    -- ========================================================================
    -- MAIN LOOP: Hybrid peek-then-batch algorithm
    -- Uses STATIC SQL for peek (hot path) and DYNAMIC SQL for batch and
    -- the delete-marker-only path
    -- ========================================================================
    LOOP
        EXIT WHEN v_count >= v_limit;

        v_previous_seek := v_next_seek;
        v_previous_seek_at := v_next_seek_at;
        v_previous_seek_version := v_next_seek_version;
        v_previous_count := v_count;
        v_previous_skipped := v_skipped;

        -- STEP 1: PEEK
        v_peek_name := NULL;
        IF delete_markers = 'only' THEN
            EXECUTE CASE WHEN v_next_seek_strict
                THEN v_delete_marker_peek_query_strict
                ELSE v_delete_marker_peek_query
            END
                INTO v_peek_name
                USING bucketname, v_next_seek,
                    CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix_lower) ELSE v_prefix_lower END,
                    1, v_next_seek_at, v_next_seek_version;
        ELSIF v_multi_row AND v_next_seek_at IS NOT NULL THEN
            SELECT o.name INTO v_peek_name
            FROM storage.objects o
            WHERE o.bucket_id = bucketname
              AND lower(o.name) COLLATE "C" = v_next_seek
              AND (COALESCE(o.archived_at, 'infinity'::timestamptz) < v_next_seek_at
                   OR (COALESCE(o.archived_at, 'infinity'::timestamptz) = v_next_seek_at
                       AND COALESCE(o.version, '') > v_next_seek_version))
              AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
              AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
              AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
              AND (delete_markers != 'only' OR o.is_delete_marker)
            ORDER BY COALESCE(o.archived_at, 'infinity'::timestamptz) DESC,
                     COALESCE(o.version, '') ASC
            LIMIT 1;

            -- The current key is exhausted. Clear its version boundary and
            -- make the following ASC name peek strict. Appending '/' is not a
            -- valid lexical successor because keys ending in characters such
            -- as '!' sort between the exhausted name and name || '/'.
            IF v_peek_name IS NULL THEN
                IF v_is_asc THEN
                    v_next_seek_strict := true;
                END IF;
                v_next_seek_at := NULL;
                v_next_seek_version := '';
            END IF;
        END IF;

        -- Single-row mode is always noncurrent_versions='exclude'. Keep the
        -- current-row predicate literal so generic plans use the current index.
        IF delete_markers != 'only' AND v_peek_name IS NULL AND NOT v_multi_row THEN
            IF v_is_asc THEN
                IF v_next_seek_strict AND v_upper_bound IS NOT NULL THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" > v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                    ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
                ELSIF v_next_seek_strict THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" > v_next_seek
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                    ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
                ELSIF v_upper_bound IS NOT NULL THEN
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                    ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
                ELSE
                    SELECT o.name INTO v_peek_name FROM storage.objects o
                    WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek
                      AND o.archived_at IS NULL
                      AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                    ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
                END IF;
            ELSIF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                  AND o.archived_at IS NULL
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek
                  AND o.archived_at IS NULL
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            END IF;
        ELSIF delete_markers != 'only' AND v_peek_name IS NULL AND v_is_asc THEN
            IF v_next_seek_strict AND v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" > v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            ELSIF v_next_seek_strict THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" > v_next_seek
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            ELSIF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek AND lower(o.name) COLLATE "C" < v_upper_bound
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" >= v_next_seek
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" ASC LIMIT 1;
            END IF;
        ELSIF delete_markers != 'only' AND v_peek_name IS NULL THEN
            IF v_upper_bound IS NOT NULL THEN
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek AND lower(o.name) COLLATE "C" >= v_prefix_lower
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            ELSE
                SELECT o.name INTO v_peek_name FROM storage.objects o
                WHERE o.bucket_id = bucketname AND lower(o.name) COLLATE "C" < v_next_seek
                  AND (noncurrent_versions != 'exclude' OR o.archived_at IS NULL)
                  AND (noncurrent_versions != 'only' OR o.archived_at IS NOT NULL)
                  AND (delete_markers != 'exclude' OR NOT o.is_delete_marker)
                  AND (delete_markers != 'only' OR o.is_delete_marker)
                ORDER BY lower(o.name) COLLATE "C" DESC LIMIT 1;
            END IF;
        END IF;

        EXIT WHEN v_peek_name IS NULL;

        -- If the peek landed on a different key than we were tracking, any
        -- version boundary belongs to the OLD key and must not leak into the
        -- new one - e.g. the deleteMarkers='only' peek doesn't know or care
        -- whether it's continuing the same key or jumping to a new one, so
        -- it never clears these itself.
        IF lower(v_peek_name) IS DISTINCT FROM v_next_seek THEN
            v_next_seek_at := NULL;
            v_next_seek_version := '';
        END IF;

        -- The peek is authoritative for the next key to process. This is
        -- especially important after exhausting a multi-version key: the
        -- version boundary has been cleared, so executing the batch against
        -- a stale v_next_seek would replay every version of that old key.
        v_next_seek := lower(v_peek_name);
        v_next_seek_strict := false;

        -- STEP 2: Check if this is a FOLDER or FILE
        v_common_prefix := storage.get_common_prefix(lower(v_peek_name), v_prefix_lower, v_delimiter);

        IF v_common_prefix IS NOT NULL THEN
            -- FOLDER: Handle offset, emit if needed, skip to next folder
            IF v_skipped < offsets THEN
                v_skipped := v_skipped + 1;
            ELSE
                name := substring(rtrim(storage.get_common_prefix(v_peek_name, v_prefix, v_delimiter), v_delimiter) from v_prefix_len + 1);
                id := NULL;
                updated_at := NULL;
                created_at := NULL;
                last_accessed_at := NULL;
                metadata := NULL;
                version := NULL;
                archived_at := NULL;
                is_delete_marker := NULL;
                is_versioned := NULL;
                RETURN NEXT;
                v_count := v_count + 1;
            END IF;

            -- Advance seek past the folder range
            IF v_is_asc THEN
                v_next_seek := lower(left(v_common_prefix, -1)) || chr(ascii(v_delimiter) + 1);
            ELSE
                v_next_seek := lower(v_common_prefix);
            END IF;
            v_next_seek_at := NULL;
            v_next_seek_version := '';
        ELSE
            -- FILE: Batch fetch using DYNAMIC SQL (overhead amortized over many rows)
            -- For ASC: upper_bound is the exclusive upper limit (< condition)
            -- For DESC: prefix_lower is the inclusive lower limit (>= condition)
            FOR v_current IN EXECUTE v_batch_query
                USING bucketname, v_next_seek,
                    CASE WHEN v_is_asc THEN COALESCE(v_upper_bound, v_prefix_lower) ELSE v_prefix_lower END, v_file_batch_size,
                    v_next_seek_at, v_next_seek_version
            LOOP
                v_common_prefix := storage.get_common_prefix(lower(v_current.name), v_prefix_lower, v_delimiter);

                IF v_common_prefix IS NOT NULL THEN
                    -- Hit a folder: exit batch, let peek handle it. Reset
                    -- strict mode too - it may have been set by an earlier
                    -- row in this same batch (see the single-row ASC advance
                    -- below), and v_next_seek here is the folder-triggering
                    -- row's own name, which the next peek must find inclusively.
                    v_next_seek := CASE
                        WHEN v_is_asc THEN lower(v_current.name)
                        ELSE lower(v_current.name) || v_delimiter
                    END;
                    v_next_seek_at := NULL;
                    v_next_seek_version := '';
                    v_next_seek_strict := false;
                    EXIT;
                END IF;

                -- Handle offset skipping
                IF v_skipped < offsets THEN
                    v_skipped := v_skipped + 1;
                ELSE
                    -- Emit file
                    name := substring(v_current.name from v_prefix_len + 1);
                    id := v_current.id;
                    updated_at := v_current.updated_at;
                    created_at := v_current.created_at;
                    last_accessed_at := v_current.last_accessed_at;
                    metadata := v_current.metadata;
                    version := v_current.version;
                    archived_at := v_current.archived_at;
                    is_delete_marker := v_current.is_delete_marker;
                    is_versioned := v_current.is_versioned;
                    RETURN NEXT;
                    v_count := v_count + 1;
                END IF;

                -- Multi-row mode must remain on this key until all of its
                -- versions have crossed the internal batch boundary.
                IF v_multi_row THEN
                    v_next_seek := lower(v_current.name);
                    v_next_seek_at := COALESCE(v_current.archived_at, 'infinity'::timestamptz);
                    v_next_seek_version := COALESCE(v_current.version, '');
                ELSIF v_is_asc THEN
                    -- Appending the delimiter as a fake lexical successor would
                    -- skip a real key like `name || '!'` (or any character
                    -- sorting below the delimiter), which sorts between `name`
                    -- and `name || delimiter`. Track the real name and mark the
                    -- next comparison strict instead - same fix as the
                    -- exhausted-key case above.
                    v_next_seek := lower(v_current.name);
                    v_next_seek_strict := true;
                ELSE
                    v_next_seek := lower(v_current.name);
                END IF;

                EXIT WHEN v_count >= v_limit;
            END LOOP;
        END IF;

        IF v_count = v_previous_count
           AND v_skipped = v_previous_skipped
           AND v_next_seek IS NOT DISTINCT FROM v_previous_seek
           AND v_next_seek_at IS NOT DISTINCT FROM v_previous_seek_at
           AND v_next_seek_version IS NOT DISTINCT FROM v_previous_seek_version THEN
            RAISE EXCEPTION 'storage.search made no progress at seek (%, %, %)',
                v_next_seek, v_next_seek_at, v_next_seek_version;
        END IF;
    END LOOP;
END;
$_$;


ALTER FUNCTION "storage"."search"("prefix" "text", "bucketname" "text", "limits" integer, "levels" integer, "offsets" integer, "search" "text", "sortcolumn" "text", "sortorder" "text", "noncurrent_versions" "text", "delete_markers" "text") OWNER TO "supabase_storage_admin";

--
-- Name: search_by_timestamp("text", "text", integer, integer, "text", "text", "text", "text", "text", "text", "text"); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."search_by_timestamp"("p_prefix" "text", "p_bucket_id" "text", "p_limit" integer, "p_level" integer, "p_start_after" "text", "p_sort_order" "text", "p_sort_column" "text", "p_sort_column_after" "text", "noncurrent_versions" "text" DEFAULT 'exclude'::"text", "delete_markers" "text" DEFAULT 'exclude'::"text", "p_start_after_version" "text" DEFAULT ''::"text") RETURNS TABLE("key" "text", "name" "text", "id" "uuid", "updated_at" timestamp with time zone, "created_at" timestamp with time zone, "last_accessed_at" timestamp with time zone, "metadata" "jsonb", "version" "text", "archived_at" timestamp with time zone, "is_delete_marker" boolean, "is_versioned" boolean)
    LANGUAGE "plpgsql" STABLE
    AS $_$
DECLARE
    v_cursor_op text;
    v_query text;
    v_prefix text;
    v_prefix_pattern text;
    v_sort_order text;
    v_sort_column text;
    v_version_tiebreak text;
BEGIN
    v_prefix := coalesce(p_prefix, '');
    -- Keep the raw prefix for common-prefix calculations and escape only LIKE metacharacters.
    v_prefix_pattern := replace(v_prefix, chr(92), chr(92) || chr(92));
    v_prefix_pattern := replace(v_prefix_pattern, '%', chr(92) || '%');
    v_prefix_pattern := replace(v_prefix_pattern, '_', chr(92) || '_');

    -- COALESCE first: NULL NOT IN (...) evaluates to NULL (not TRUE), so a
    -- bare NOT IN check silently leaves an explicit NULL argument unreset.
    noncurrent_versions := COALESCE(noncurrent_versions, 'exclude');
    delete_markers := COALESCE(delete_markers, 'exclude');
    IF noncurrent_versions NOT IN ('exclude', 'only', 'include') THEN
        noncurrent_versions := 'exclude';
    END IF;
    IF delete_markers NOT IN ('exclude', 'only', 'include') THEN
        delete_markers := 'exclude';
    END IF;

    -- $9 is only populated in multi-row mode; it's always '' otherwise, so
    -- only use each row's real version as a tiebreak in multi-row mode.
    v_version_tiebreak := CASE WHEN noncurrent_versions IN ('only', 'include') THEN 'COALESCE(version, '''')' ELSE '''''' END;

    -- Defense-in-depth: this function is independently reachable and must
    -- not trust p_sort_order/p_sort_column to already be validated by a
    -- caller. Normalize to the same strict allow-list storage.search_v2
    -- uses before interpolating anything into dynamic SQL below.
    v_sort_order := lower(coalesce(p_sort_order, 'asc'));
    IF v_sort_order NOT IN ('asc', 'desc') THEN
        v_sort_order := 'asc';
    END IF;

    v_sort_column := lower(coalesce(p_sort_column, 'updated_at'));
    IF v_sort_column NOT IN ('updated_at', 'created_at') THEN
        v_sort_column := 'updated_at';
    END IF;

    IF v_sort_order = 'asc' THEN
        v_cursor_op := '>';
    ELSE
        v_cursor_op := '<';
    END IF;

    v_query := format($sql$
        WITH raw_objects AS (
            SELECT
                o.name AS obj_name,
                o.id AS obj_id,
                o.updated_at AS obj_updated_at,
                o.created_at AS obj_created_at,
                o.last_accessed_at AS obj_last_accessed_at,
                o.metadata AS obj_metadata,
                o.version AS obj_version,
                o.archived_at AS obj_archived_at,
                o.is_delete_marker AS obj_is_delete_marker,
                o.is_versioned AS obj_is_versioned,
                storage.get_common_prefix(o.name, $1, '/') AS common_prefix
            FROM storage.objects o
            WHERE o.bucket_id = $2
              AND o.name COLLATE "C" LIKE $10 || '%%'
              AND ($7 != 'exclude' OR o.archived_at IS NULL)
              AND ($7 != 'only' OR o.archived_at IS NOT NULL)
              AND ($8 != 'exclude' OR NOT o.is_delete_marker)
              AND ($8 != 'only' OR o.is_delete_marker)
        ),
        -- Aggregate common prefixes (folders)
        -- Both created_at and updated_at use MIN(obj_created_at) to match the old prefixes table behavior
        aggregated_prefixes AS (
            SELECT
                common_prefix AS name,
                NULL::uuid AS id,
                MIN(obj_created_at) AS updated_at,
                MIN(obj_created_at) AS created_at,
                NULL::timestamptz AS last_accessed_at,
                NULL::jsonb AS metadata,
                NULL::text AS version,
                NULL::timestamptz AS archived_at,
                NULL::boolean AS is_delete_marker,
                NULL::boolean AS is_versioned,
                TRUE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NOT NULL
            GROUP BY common_prefix
        ),
        leaf_objects AS (
            SELECT
                obj_name AS name,
                obj_id AS id,
                obj_updated_at AS updated_at,
                obj_created_at AS created_at,
                obj_last_accessed_at AS last_accessed_at,
                obj_metadata AS metadata,
                obj_version AS version,
                obj_archived_at AS archived_at,
                obj_is_delete_marker AS is_delete_marker,
                obj_is_versioned AS is_versioned,
                FALSE AS is_prefix
            FROM raw_objects
            WHERE common_prefix IS NULL
        ),
        combined AS (
            SELECT * FROM aggregated_prefixes
            UNION ALL
            SELECT * FROM leaf_objects
        ),
        filtered AS (
            SELECT *
            FROM combined
            WHERE (
                $5 = ''
                OR ROW(
                    COALESCE(date_trunc('milliseconds', %I), 'epoch'::timestamptz),
                    name COLLATE "C",
                    %s
                ) %s ROW(
                    -- truncated the same way as the stored value above
                    date_trunc('milliseconds', COALESCE(NULLIF($6, '')::timestamptz, 'epoch'::timestamptz)),
                    $5,
                    $9
                )
            )
        )
        SELECT
            split_part(name, '/', $3) AS key,
            name,
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata,
            version,
            archived_at,
            is_delete_marker,
            is_versioned
        FROM filtered
        ORDER BY
            COALESCE(date_trunc('milliseconds', %I), 'epoch'::timestamptz) %s,
            name COLLATE "C" %s,
            COALESCE(version, '') %s
        LIMIT $4
    $sql$,
        v_sort_column,
        v_version_tiebreak,
        v_cursor_op,
        v_sort_column,
        v_sort_order,
        v_sort_order,
        v_sort_order
    );

    -- version is the third tiebreak component for two versions of the same
    -- key tying on both timestamp and name (see filtered CTE / ORDER BY above)
    RETURN QUERY EXECUTE v_query
    USING v_prefix, p_bucket_id, p_level, p_limit, p_start_after, p_sort_column_after, noncurrent_versions, delete_markers, coalesce(p_start_after_version, ''), v_prefix_pattern;
END;
$_$;


ALTER FUNCTION "storage"."search_by_timestamp"("p_prefix" "text", "p_bucket_id" "text", "p_limit" integer, "p_level" integer, "p_start_after" "text", "p_sort_order" "text", "p_sort_column" "text", "p_sort_column_after" "text", "noncurrent_versions" "text", "delete_markers" "text", "p_start_after_version" "text") OWNER TO "supabase_storage_admin";

--
-- Name: search_v2("text", "text", integer, integer, "text", "text", "text", "text", "text", "text", timestamp with time zone, "text", boolean); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."search_v2"("prefix" "text", "bucket_name" "text", "limits" integer DEFAULT 100, "levels" integer DEFAULT 1, "start_after" "text" DEFAULT ''::"text", "sort_order" "text" DEFAULT 'asc'::"text", "sort_column" "text" DEFAULT 'name'::"text", "sort_column_after" "text" DEFAULT ''::"text", "noncurrent_versions" "text" DEFAULT 'exclude'::"text", "delete_markers" "text" DEFAULT 'exclude'::"text", "start_after_archived_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "start_after_version" "text" DEFAULT ''::"text", "start_after_is_continuation" boolean DEFAULT false) RETURNS TABLE("key" "text", "name" "text", "id" "uuid", "updated_at" timestamp with time zone, "created_at" timestamp with time zone, "last_accessed_at" timestamp with time zone, "metadata" "jsonb", "version" "text", "archived_at" timestamp with time zone, "is_delete_marker" boolean, "is_versioned" boolean)
    LANGUAGE "plpgsql" STABLE
    AS $$
DECLARE
    v_sort_col text;
    v_sort_ord text;
    v_limit int;
BEGIN
    -- Cap limit to maximum of 1500 records
    v_limit := LEAST(coalesce(limits, 100), 1500);

    -- Validate and normalize sort_order
    v_sort_ord := lower(coalesce(sort_order, 'asc'));
    IF v_sort_ord NOT IN ('asc', 'desc') THEN
        v_sort_ord := 'asc';
    END IF;

    -- Validate and normalize sort_column
    v_sort_col := lower(coalesce(sort_column, 'name'));
    IF v_sort_col NOT IN ('name', 'updated_at', 'created_at') THEN
        v_sort_col := 'name';
    END IF;

    -- Route to appropriate implementation
    IF v_sort_col = 'name' THEN
        -- Use list_objects_with_delimiter for name sorting (most efficient: O(k * log n))
        RETURN QUERY
        SELECT
            split_part(l.name, '/', levels) AS key,
            l.name AS name,
            l.id,
            l.updated_at,
            l.created_at,
            l.last_accessed_at,
            l.metadata,
            l.version,
            l.archived_at,
            l.is_delete_marker,
            l.is_versioned
        FROM storage.list_objects_with_delimiter(
            bucket_name,
            coalesce(prefix, ''),
            '/',
            v_limit,
            CASE WHEN start_after_is_continuation THEN '' ELSE start_after END,
            CASE WHEN start_after_is_continuation THEN start_after ELSE '' END,
            v_sort_ord,
            noncurrent_versions,
            delete_markers,
            start_after_archived_at,
            start_after_version
        ) l;
    ELSE
        -- Use aggregation approach for timestamp sorting
        -- Not efficient for large datasets but supports correct pagination
        RETURN QUERY SELECT * FROM storage.search_by_timestamp(
            prefix, bucket_name, v_limit, levels, start_after,
            v_sort_ord, v_sort_col, sort_column_after,
            noncurrent_versions, delete_markers, start_after_version
        );
    END IF;
END;
$$;


ALTER FUNCTION "storage"."search_v2"("prefix" "text", "bucket_name" "text", "limits" integer, "levels" integer, "start_after" "text", "sort_order" "text", "sort_column" "text", "sort_column_after" "text", "noncurrent_versions" "text", "delete_markers" "text", "start_after_archived_at" timestamp with time zone, "start_after_version" "text", "start_after_is_continuation" boolean) OWNER TO "supabase_storage_admin";

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION "storage"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW; 
END;
$$;


ALTER FUNCTION "storage"."update_updated_at_column"() OWNER TO "supabase_storage_admin";

--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."audit_log_entries" (
    "instance_id" "uuid",
    "id" "uuid" NOT NULL,
    "payload" json,
    "created_at" timestamp with time zone,
    "ip_address" character varying(64) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE "auth"."audit_log_entries" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "audit_log_entries"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."audit_log_entries" IS 'Auth: Audit trail for user actions.';


--
-- Name: custom_oauth_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."custom_oauth_providers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "provider_type" "text" NOT NULL,
    "identifier" "text" NOT NULL,
    "name" "text" NOT NULL,
    "client_id" "text" NOT NULL,
    "client_secret" "text" NOT NULL,
    "acceptable_client_ids" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "scopes" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "pkce_enabled" boolean DEFAULT true NOT NULL,
    "attribute_mapping" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "authorization_params" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "enabled" boolean DEFAULT true NOT NULL,
    "email_optional" boolean DEFAULT false NOT NULL,
    "issuer" "text",
    "discovery_url" "text",
    "skip_nonce_check" boolean DEFAULT false NOT NULL,
    "cached_discovery" "jsonb",
    "discovery_cached_at" timestamp with time zone,
    "authorization_url" "text",
    "token_url" "text",
    "userinfo_url" "text",
    "jwks_uri" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "custom_claims_allowlist" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    CONSTRAINT "custom_oauth_providers_authorization_url_https" CHECK ((("authorization_url" IS NULL) OR ("authorization_url" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_authorization_url_length" CHECK ((("authorization_url" IS NULL) OR ("char_length"("authorization_url") <= 2048))),
    CONSTRAINT "custom_oauth_providers_client_id_length" CHECK ((("char_length"("client_id") >= 1) AND ("char_length"("client_id") <= 512))),
    CONSTRAINT "custom_oauth_providers_discovery_url_length" CHECK ((("discovery_url" IS NULL) OR ("char_length"("discovery_url") <= 2048))),
    CONSTRAINT "custom_oauth_providers_identifier_format" CHECK (("identifier" ~ '^[a-z0-9][a-z0-9:-]{0,48}[a-z0-9]$'::"text")),
    CONSTRAINT "custom_oauth_providers_issuer_length" CHECK ((("issuer" IS NULL) OR (("char_length"("issuer") >= 1) AND ("char_length"("issuer") <= 2048)))),
    CONSTRAINT "custom_oauth_providers_jwks_uri_https" CHECK ((("jwks_uri" IS NULL) OR ("jwks_uri" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_jwks_uri_length" CHECK ((("jwks_uri" IS NULL) OR ("char_length"("jwks_uri") <= 2048))),
    CONSTRAINT "custom_oauth_providers_name_length" CHECK ((("char_length"("name") >= 1) AND ("char_length"("name") <= 100))),
    CONSTRAINT "custom_oauth_providers_oauth2_requires_endpoints" CHECK ((("provider_type" <> 'oauth2'::"text") OR (("authorization_url" IS NOT NULL) AND ("token_url" IS NOT NULL) AND ("userinfo_url" IS NOT NULL)))),
    CONSTRAINT "custom_oauth_providers_oidc_discovery_url_https" CHECK ((("provider_type" <> 'oidc'::"text") OR ("discovery_url" IS NULL) OR ("discovery_url" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_oidc_issuer_https" CHECK ((("provider_type" <> 'oidc'::"text") OR ("issuer" IS NULL) OR ("issuer" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_oidc_requires_issuer" CHECK ((("provider_type" <> 'oidc'::"text") OR ("issuer" IS NOT NULL))),
    CONSTRAINT "custom_oauth_providers_provider_type_check" CHECK (("provider_type" = ANY (ARRAY['oauth2'::"text", 'oidc'::"text"]))),
    CONSTRAINT "custom_oauth_providers_token_url_https" CHECK ((("token_url" IS NULL) OR ("token_url" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_token_url_length" CHECK ((("token_url" IS NULL) OR ("char_length"("token_url") <= 2048))),
    CONSTRAINT "custom_oauth_providers_userinfo_url_https" CHECK ((("userinfo_url" IS NULL) OR ("userinfo_url" ~~ 'https://%'::"text"))),
    CONSTRAINT "custom_oauth_providers_userinfo_url_length" CHECK ((("userinfo_url" IS NULL) OR ("char_length"("userinfo_url") <= 2048)))
);


ALTER TABLE "auth"."custom_oauth_providers" OWNER TO "supabase_auth_admin";

--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."flow_state" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid",
    "auth_code" "text",
    "code_challenge_method" "auth"."code_challenge_method",
    "code_challenge" "text",
    "provider_type" "text" NOT NULL,
    "provider_access_token" "text",
    "provider_refresh_token" "text",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "authentication_method" "text" NOT NULL,
    "auth_code_issued_at" timestamp with time zone,
    "invite_token" "text",
    "referrer" "text",
    "oauth_client_state_id" "uuid",
    "linking_target_id" "uuid",
    "email_optional" boolean DEFAULT false NOT NULL
);


ALTER TABLE "auth"."flow_state" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "flow_state"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."flow_state" IS 'Stores metadata for all OAuth/SSO login flows';


--
-- Name: identities; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."identities" (
    "provider_id" "text" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "identity_data" "jsonb" NOT NULL,
    "provider" "text" NOT NULL,
    "last_sign_in_at" timestamp with time zone,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "email" "text" GENERATED ALWAYS AS ("lower"(("identity_data" ->> 'email'::"text"))) STORED,
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL
);


ALTER TABLE "auth"."identities" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "identities"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."identities" IS 'Auth: Stores identities associated to a user.';


--
-- Name: COLUMN "identities"."email"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."identities"."email" IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


--
-- Name: instances; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."instances" (
    "id" "uuid" NOT NULL,
    "uuid" "uuid",
    "raw_base_config" "text",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone
);


ALTER TABLE "auth"."instances" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "instances"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."instances" IS 'Auth: Manages users across multiple sites.';


--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."mfa_amr_claims" (
    "session_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "authentication_method" "text" NOT NULL,
    "id" "uuid" NOT NULL
);


ALTER TABLE "auth"."mfa_amr_claims" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "mfa_amr_claims"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."mfa_amr_claims" IS 'auth: stores authenticator method reference claims for multi factor authentication';


--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."mfa_challenges" (
    "id" "uuid" NOT NULL,
    "factor_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "verified_at" timestamp with time zone,
    "ip_address" "inet" NOT NULL,
    "otp_code" "text",
    "web_authn_session_data" "jsonb"
);


ALTER TABLE "auth"."mfa_challenges" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "mfa_challenges"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."mfa_challenges" IS 'auth: stores metadata about challenge requests made';


--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."mfa_factors" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "friendly_name" "text",
    "factor_type" "auth"."factor_type" NOT NULL,
    "status" "auth"."factor_status" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "secret" "text",
    "phone" "text",
    "last_challenged_at" timestamp with time zone,
    "web_authn_credential" "jsonb",
    "web_authn_aaguid" "uuid",
    "last_webauthn_challenge_data" "jsonb"
);


ALTER TABLE "auth"."mfa_factors" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "mfa_factors"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."mfa_factors" IS 'auth: stores metadata about factors';


--
-- Name: COLUMN "mfa_factors"."last_webauthn_challenge_data"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."mfa_factors"."last_webauthn_challenge_data" IS 'Stores the latest WebAuthn challenge data including attestation/assertion for customer verification';


--
-- Name: mfa_recovery_code_sets; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."mfa_recovery_code_sets" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "mfa_factor_id" "uuid" NOT NULL,
    "failed_verification_count" integer DEFAULT 0 NOT NULL,
    "verification_locked_until" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "mfa_recovery_code_sets_failed_verification_count_check" CHECK (("failed_verification_count" >= 0))
);


ALTER TABLE "auth"."mfa_recovery_code_sets" OWNER TO "supabase_auth_admin";

--
-- Name: mfa_recovery_codes; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."mfa_recovery_codes" (
    "id" "uuid" NOT NULL,
    "mfa_recovery_code_set_id" "uuid" NOT NULL,
    "code_hash" "text" NOT NULL,
    "consumed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "auth"."mfa_recovery_codes" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_authorizations; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."oauth_authorizations" (
    "id" "uuid" NOT NULL,
    "authorization_id" "text" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "user_id" "uuid",
    "redirect_uri" "text" NOT NULL,
    "scope" "text" NOT NULL,
    "state" "text",
    "resource" "text",
    "code_challenge" "text",
    "code_challenge_method" "auth"."code_challenge_method",
    "response_type" "auth"."oauth_response_type" DEFAULT 'code'::"auth"."oauth_response_type" NOT NULL,
    "status" "auth"."oauth_authorization_status" DEFAULT 'pending'::"auth"."oauth_authorization_status" NOT NULL,
    "authorization_code" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone DEFAULT ("now"() + '00:03:00'::interval) NOT NULL,
    "approved_at" timestamp with time zone,
    "nonce" "text",
    CONSTRAINT "oauth_authorizations_authorization_code_length" CHECK (("char_length"("authorization_code") <= 255)),
    CONSTRAINT "oauth_authorizations_code_challenge_length" CHECK (("char_length"("code_challenge") <= 128)),
    CONSTRAINT "oauth_authorizations_expires_at_future" CHECK (("expires_at" > "created_at")),
    CONSTRAINT "oauth_authorizations_nonce_length" CHECK (("char_length"("nonce") <= 255)),
    CONSTRAINT "oauth_authorizations_redirect_uri_length" CHECK (("char_length"("redirect_uri") <= 2048)),
    CONSTRAINT "oauth_authorizations_resource_length" CHECK (("char_length"("resource") <= 2048)),
    CONSTRAINT "oauth_authorizations_scope_length" CHECK (("char_length"("scope") <= 4096)),
    CONSTRAINT "oauth_authorizations_state_length" CHECK (("char_length"("state") <= 4096))
);


ALTER TABLE "auth"."oauth_authorizations" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_client_states; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."oauth_client_states" (
    "id" "uuid" NOT NULL,
    "provider_type" "text" NOT NULL,
    "code_verifier" "text",
    "created_at" timestamp with time zone NOT NULL
);


ALTER TABLE "auth"."oauth_client_states" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "oauth_client_states"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."oauth_client_states" IS 'Stores OAuth states for third-party provider authentication flows where Supabase acts as the OAuth client.';


--
-- Name: oauth_clients; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."oauth_clients" (
    "id" "uuid" NOT NULL,
    "client_secret_hash" "text",
    "registration_type" "auth"."oauth_registration_type" NOT NULL,
    "redirect_uris" "text" NOT NULL,
    "grant_types" "text" NOT NULL,
    "client_name" "text",
    "client_uri" "text",
    "logo_uri" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "deleted_at" timestamp with time zone,
    "client_type" "auth"."oauth_client_type" DEFAULT 'confidential'::"auth"."oauth_client_type" NOT NULL,
    "token_endpoint_auth_method" "text" NOT NULL,
    CONSTRAINT "oauth_clients_client_name_length" CHECK (("char_length"("client_name") <= 1024)),
    CONSTRAINT "oauth_clients_client_uri_length" CHECK (("char_length"("client_uri") <= 2048)),
    CONSTRAINT "oauth_clients_logo_uri_length" CHECK (("char_length"("logo_uri") <= 2048)),
    CONSTRAINT "oauth_clients_token_endpoint_auth_method_check" CHECK (("token_endpoint_auth_method" = ANY (ARRAY['client_secret_basic'::"text", 'client_secret_post'::"text", 'none'::"text"])))
);


ALTER TABLE "auth"."oauth_clients" OWNER TO "supabase_auth_admin";

--
-- Name: oauth_consents; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."oauth_consents" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "scopes" "text" NOT NULL,
    "granted_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "revoked_at" timestamp with time zone,
    CONSTRAINT "oauth_consents_revoked_after_granted" CHECK ((("revoked_at" IS NULL) OR ("revoked_at" >= "granted_at"))),
    CONSTRAINT "oauth_consents_scopes_length" CHECK (("char_length"("scopes") <= 2048)),
    CONSTRAINT "oauth_consents_scopes_not_empty" CHECK (("char_length"(TRIM(BOTH FROM "scopes")) > 0))
);


ALTER TABLE "auth"."oauth_consents" OWNER TO "supabase_auth_admin";

--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."one_time_tokens" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "token_type" "auth"."one_time_token_type" NOT NULL,
    "token_hash" "text" NOT NULL,
    "relates_to" "text" NOT NULL,
    "created_at" timestamp without time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp without time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone,
    CONSTRAINT "one_time_tokens_token_hash_check" CHECK (("char_length"("token_hash") > 0))
);


ALTER TABLE "auth"."one_time_tokens" OWNER TO "supabase_auth_admin";

--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."refresh_tokens" (
    "instance_id" "uuid",
    "id" bigint NOT NULL,
    "token" character varying(255),
    "user_id" character varying(255),
    "revoked" boolean,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "parent" character varying(255),
    "session_id" "uuid"
);


ALTER TABLE "auth"."refresh_tokens" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "refresh_tokens"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."refresh_tokens" IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: supabase_auth_admin
--

CREATE SEQUENCE "auth"."refresh_tokens_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "auth"."refresh_tokens_id_seq" OWNER TO "supabase_auth_admin";

--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: supabase_auth_admin
--

ALTER SEQUENCE "auth"."refresh_tokens_id_seq" OWNED BY "auth"."refresh_tokens"."id";


--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."saml_providers" (
    "id" "uuid" NOT NULL,
    "sso_provider_id" "uuid" NOT NULL,
    "entity_id" "text" NOT NULL,
    "metadata_xml" "text" NOT NULL,
    "metadata_url" "text",
    "attribute_mapping" "jsonb",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "name_id_format" "text",
    CONSTRAINT "entity_id not empty" CHECK (("char_length"("entity_id") > 0)),
    CONSTRAINT "metadata_url not empty" CHECK ((("metadata_url" = NULL::"text") OR ("char_length"("metadata_url") > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK (("char_length"("metadata_xml") > 0))
);


ALTER TABLE "auth"."saml_providers" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "saml_providers"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."saml_providers" IS 'Auth: Manages SAML Identity Provider connections.';


--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."saml_relay_states" (
    "id" "uuid" NOT NULL,
    "sso_provider_id" "uuid" NOT NULL,
    "request_id" "text" NOT NULL,
    "for_email" "text",
    "redirect_to" "text",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "flow_state_id" "uuid",
    CONSTRAINT "request_id not empty" CHECK (("char_length"("request_id") > 0))
);


ALTER TABLE "auth"."saml_relay_states" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "saml_relay_states"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."saml_relay_states" IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."schema_migrations" (
    "version" character varying(255) NOT NULL
);


ALTER TABLE "auth"."schema_migrations" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "schema_migrations"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."schema_migrations" IS 'Auth: Manages updates to the auth system.';


--
-- Name: scim_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."scim_tokens" (
    "id" "uuid" NOT NULL,
    "sso_provider_id" "uuid" NOT NULL,
    "token_hash" "text" NOT NULL,
    "prefix" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone,
    "revoked_at" timestamp with time zone,
    "last_used_at" timestamp with time zone,
    CONSTRAINT "scim_tokens_expires_at_future" CHECK ((("expires_at" IS NULL) OR ("expires_at" > "created_at"))),
    CONSTRAINT "scim_tokens_revoked_after_created" CHECK ((("revoked_at" IS NULL) OR ("revoked_at" >= "created_at"))),
    CONSTRAINT "scim_tokens_token_hash_check" CHECK (("token_hash" ~ '^[0-9a-f]{64}$'::"text"))
);


ALTER TABLE "auth"."scim_tokens" OWNER TO "supabase_auth_admin";

--
-- Name: scim_users; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."scim_users" (
    "id" "uuid" NOT NULL,
    "sso_provider_id" "uuid" NOT NULL,
    "user_id" "uuid",
    "resource" "jsonb" NOT NULL,
    "user_name" "text" GENERATED ALWAYS AS ("lower"(("resource" ->> 'userName'::"text"))) STORED NOT NULL,
    "external_id" "text" GENERATED ALWAYS AS (("resource" ->> 'externalId'::"text")) STORED,
    "active" boolean GENERATED ALWAYS AS (COALESCE((("resource" ->> 'active'::"text"))::boolean, true)) STORED NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "deleted_at" timestamp with time zone
);


ALTER TABLE "auth"."scim_users" OWNER TO "supabase_auth_admin";

--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."sessions" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "factor_id" "uuid",
    "aal" "auth"."aal_level",
    "not_after" timestamp with time zone,
    "refreshed_at" timestamp without time zone,
    "user_agent" "text",
    "ip" "inet",
    "tag" "text",
    "oauth_client_id" "uuid",
    "refresh_token_hmac_key" "text",
    "refresh_token_counter" bigint,
    "scopes" "text",
    CONSTRAINT "sessions_scopes_length" CHECK (("char_length"("scopes") <= 4096))
);


ALTER TABLE "auth"."sessions" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "sessions"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."sessions" IS 'Auth: Stores session data associated to a user.';


--
-- Name: COLUMN "sessions"."not_after"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."sessions"."not_after" IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';


--
-- Name: COLUMN "sessions"."refresh_token_hmac_key"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."sessions"."refresh_token_hmac_key" IS 'Holds a HMAC-SHA256 key used to sign refresh tokens for this session.';


--
-- Name: COLUMN "sessions"."refresh_token_counter"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."sessions"."refresh_token_counter" IS 'Holds the ID (counter) of the last issued refresh token.';


--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."sso_domains" (
    "id" "uuid" NOT NULL,
    "sso_provider_id" "uuid" NOT NULL,
    "domain" "text" NOT NULL,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK (("char_length"("domain") > 0))
);


ALTER TABLE "auth"."sso_domains" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "sso_domains"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."sso_domains" IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."sso_providers" (
    "id" "uuid" NOT NULL,
    "resource_id" "text",
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "disabled" boolean,
    CONSTRAINT "resource_id not empty" CHECK ((("resource_id" = NULL::"text") OR ("char_length"("resource_id") > 0)))
);


ALTER TABLE "auth"."sso_providers" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "sso_providers"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."sso_providers" IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


--
-- Name: COLUMN "sso_providers"."resource_id"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."sso_providers"."resource_id" IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."users" (
    "instance_id" "uuid",
    "id" "uuid" NOT NULL,
    "aud" character varying(255),
    "role" character varying(255),
    "email" character varying(255),
    "encrypted_password" character varying(255),
    "email_confirmed_at" timestamp with time zone,
    "invited_at" timestamp with time zone,
    "confirmation_token" character varying(255),
    "confirmation_sent_at" timestamp with time zone,
    "recovery_token" character varying(255),
    "recovery_sent_at" timestamp with time zone,
    "email_change_token_new" character varying(255),
    "email_change" character varying(255),
    "email_change_sent_at" timestamp with time zone,
    "last_sign_in_at" timestamp with time zone,
    "raw_app_meta_data" "jsonb",
    "raw_user_meta_data" "jsonb",
    "is_super_admin" boolean,
    "created_at" timestamp with time zone,
    "updated_at" timestamp with time zone,
    "phone" "text" DEFAULT NULL::character varying,
    "phone_confirmed_at" timestamp with time zone,
    "phone_change" "text" DEFAULT ''::character varying,
    "phone_change_token" character varying(255) DEFAULT ''::character varying,
    "phone_change_sent_at" timestamp with time zone,
    "confirmed_at" timestamp with time zone GENERATED ALWAYS AS (LEAST("email_confirmed_at", "phone_confirmed_at")) STORED,
    "email_change_token_current" character varying(255) DEFAULT ''::character varying,
    "email_change_confirm_status" smallint DEFAULT 0,
    "banned_until" timestamp with time zone,
    "reauthentication_token" character varying(255) DEFAULT ''::character varying,
    "reauthentication_sent_at" timestamp with time zone,
    "is_sso_user" boolean DEFAULT false NOT NULL,
    "deleted_at" timestamp with time zone,
    "is_anonymous" boolean DEFAULT false NOT NULL,
    CONSTRAINT "users_email_change_confirm_status_check" CHECK ((("email_change_confirm_status" >= 0) AND ("email_change_confirm_status" <= 2)))
);


ALTER TABLE "auth"."users" OWNER TO "supabase_auth_admin";

--
-- Name: TABLE "users"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE "auth"."users" IS 'Auth: Stores user login data within a secure schema.';


--
-- Name: COLUMN "users"."is_sso_user"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN "auth"."users"."is_sso_user" IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


--
-- Name: webauthn_challenges; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."webauthn_challenges" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "challenge_type" "text" NOT NULL,
    "session_data" "jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    CONSTRAINT "webauthn_challenges_challenge_type_check" CHECK (("challenge_type" = ANY (ARRAY['signup'::"text", 'registration'::"text", 'authentication'::"text"])))
);


ALTER TABLE "auth"."webauthn_challenges" OWNER TO "supabase_auth_admin";

--
-- Name: webauthn_credentials; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE "auth"."webauthn_credentials" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "credential_id" "bytea" NOT NULL,
    "public_key" "bytea" NOT NULL,
    "attestation_type" "text" DEFAULT ''::"text" NOT NULL,
    "aaguid" "uuid",
    "sign_count" bigint DEFAULT 0 NOT NULL,
    "transports" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "backup_eligible" boolean DEFAULT false NOT NULL,
    "backed_up" boolean DEFAULT false NOT NULL,
    "friendly_name" "text" DEFAULT ''::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_used_at" timestamp with time zone
);


ALTER TABLE "auth"."webauthn_credentials" OWNER TO "supabase_auth_admin";

--
-- Name: account_deletion_challenges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."account_deletion_challenges" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "purpose" "text" DEFAULT 'account_deletion'::"text" NOT NULL,
    "channel" "text" NOT NULL,
    "contact_hash" "text" NOT NULL,
    "status" "text" DEFAULT 'sent'::"text" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "max_attempts" integer DEFAULT 5 NOT NULL,
    "resend_count" integer DEFAULT 0 NOT NULL,
    "last_sent_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "verified_at" timestamp with time zone,
    "confirmation_hash" "text",
    "confirmation_expires_at" timestamp with time zone,
    "consumed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "account_deletion_challenges_attempts_check" CHECK (("attempts" >= 0)),
    CONSTRAINT "account_deletion_challenges_channel_check" CHECK (("channel" = ANY (ARRAY['email'::"text", 'phone'::"text"]))),
    CONSTRAINT "account_deletion_challenges_max_attempts_check" CHECK (("max_attempts" > 0)),
    CONSTRAINT "account_deletion_challenges_purpose_check" CHECK (("purpose" = 'account_deletion'::"text")),
    CONSTRAINT "account_deletion_challenges_resend_count_check" CHECK (("resend_count" >= 0)),
    CONSTRAINT "account_deletion_challenges_status_check" CHECK (("status" = ANY (ARRAY['sent'::"text", 'verified'::"text", 'consumed'::"text", 'expired'::"text"])))
);


ALTER TABLE "public"."account_deletion_challenges" OWNER TO "postgres";

--
-- Name: account_deletion_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."account_deletion_requests" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "role" "text" NOT NULL,
    "salon_id" "uuid",
    "salon_name" "text",
    "salon_city" "text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "step_state" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "media_keys" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "next_attempt_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_error_code" "text",
    "requested_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "completed_at" timestamp with time zone,
    CONSTRAINT "account_deletion_requests_attempts_check" CHECK (("attempts" >= 0)),
    CONSTRAINT "account_deletion_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."account_deletion_requests" OWNER TO "postgres";

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."alembic_version" (
    "version_num" character varying(32) NOT NULL
);


ALTER TABLE "public"."alembic_version" OWNER TO "postgres";

--
-- Name: api_rate_limits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."api_rate_limits" (
    "bucket_hash" "text" NOT NULL,
    "window_start" timestamp with time zone DEFAULT "now"() NOT NULL,
    "attempts" integer DEFAULT 1 NOT NULL
);


ALTER TABLE "public"."api_rate_limits" OWNER TO "postgres";

--
-- Name: blocked_slots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."blocked_slots" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "staff_id" "uuid",
    "salon_id" "uuid",
    "start_datetime" timestamp with time zone NOT NULL,
    "end_datetime" timestamp with time zone NOT NULL,
    "block_type" "text" DEFAULT 'other'::"text" NOT NULL,
    "reason" "text",
    "is_full_day" boolean DEFAULT false NOT NULL,
    "is_recurring" boolean DEFAULT false NOT NULL,
    "recurrence_rule" "text",
    "recurrence_end" "date",
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "blocked_scope_check" CHECK ((("staff_id" IS NOT NULL) OR ("salon_id" IS NOT NULL))),
    CONSTRAINT "blocked_slots_block_type_check" CHECK (("block_type" = ANY (ARRAY['leave'::"text", 'break'::"text", 'lunch'::"text", 'training'::"text", 'holiday'::"text", 'other'::"text"]))),
    CONSTRAINT "blocked_slots_check" CHECK (("end_datetime" > "start_datetime"))
);

ALTER TABLE ONLY "public"."blocked_slots" REPLICA IDENTITY FULL;


ALTER TABLE "public"."blocked_slots" OWNER TO "postgres";

--
-- Name: booking_action_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."booking_action_requests" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "booking_id" "uuid" NOT NULL,
    "kind" "text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "reason" "text",
    "decision" "text",
    "decision_reason" "text",
    "requested_by" "uuid",
    "resolved_by" "uuid",
    "resolved_at" timestamp with time zone,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "booking_action_requests_check" CHECK (((("status" = 'pending'::"text") AND ("decision" IS NULL) AND ("resolved_by" IS NULL) AND ("resolved_at" IS NULL)) OR (("status" = 'resolved'::"text") AND ("decision" IS NOT NULL) AND ("resolved_at" IS NOT NULL)))),
    CONSTRAINT "booking_action_requests_check1" CHECK ((("decision" IS NULL) OR ("decision" = 'invalidated'::"text") OR (("kind" = 'payment_confirmation'::"text") AND ("decision" = ANY (ARRAY['received'::"text", 'not_received'::"text"]))) OR (("kind" = 'cancellation'::"text") AND ("decision" = ANY (ARRAY['approve'::"text", 'decline'::"text"]))))),
    CONSTRAINT "booking_action_requests_check2" CHECK ((("decision" IS DISTINCT FROM 'decline'::"text") OR (("decision_reason" IS NOT NULL) AND ("length"(TRIM(BOTH FROM "decision_reason")) > 0)))),
    CONSTRAINT "booking_action_requests_decision_check" CHECK ((("decision" IS NULL) OR ("decision" = ANY (ARRAY['received'::"text", 'not_received'::"text", 'approve'::"text", 'decline'::"text", 'invalidated'::"text"])))),
    CONSTRAINT "booking_action_requests_decision_reason_check" CHECK ((("decision_reason" IS NULL) OR ("length"("decision_reason") <= 500))),
    CONSTRAINT "booking_action_requests_kind_check" CHECK (("kind" = ANY (ARRAY['payment_confirmation'::"text", 'cancellation'::"text"]))),
    CONSTRAINT "booking_action_requests_reason_check" CHECK ((("reason" IS NULL) OR ("length"("reason") <= 500))),
    CONSTRAINT "booking_action_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'resolved'::"text"])))
);

ALTER TABLE ONLY "public"."booking_action_requests" REPLICA IDENTITY FULL;


ALTER TABLE "public"."booking_action_requests" OWNER TO "postgres";

--
-- Name: booking_audit_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."booking_audit_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "booking_id" "uuid" NOT NULL,
    "actor_id" "uuid",
    "event_type" "text" NOT NULL,
    "old_state" "text",
    "new_state" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."booking_audit_events" OWNER TO "postgres";

--
-- Name: booking_payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."booking_payments" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "booking_id" "uuid" NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "payer_id" "uuid",
    "recorded_by" "uuid",
    "channel" "text" NOT NULL,
    "purpose" "text" NOT NULL,
    "settlement_model" "text" DEFAULT 'offline'::"text" NOT NULL,
    "provider" "text",
    "method" "text",
    "instrument" "text",
    "amount" numeric(10,2) NOT NULL,
    "platform_fee_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "currency" "text" DEFAULT 'INR'::"text" NOT NULL,
    "status" "text" DEFAULT 'created'::"text" NOT NULL,
    "intent_reference" "text" NOT NULL,
    "order_ref" "text",
    "payment_ref" "text",
    "failure_code" "text",
    "expires_at" timestamp with time zone,
    "authorized_at" timestamp with time zone,
    "captured_at" timestamp with time zone,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "commission_rate_percent" numeric(7,4),
    "commission_base" "text",
    "platform_commission_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "commission_policy_version" "text",
    "provider_fee_amount" numeric(10,2),
    "provider_tax_amount" numeric(10,2),
    "overcollected_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "provider_order_confirmed_at" timestamp with time zone,
    "gateway_fee_percent" numeric(7,4),
    "gateway_fee_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "collection_method" "text",
    "collected_by_owner" boolean DEFAULT false NOT NULL,
    "online_processing_charge" numeric(10,2) DEFAULT 0 NOT NULL,
    "service_amount" numeric(10,2) GENERATED ALWAYS AS (("amount" - "online_processing_charge")) STORED,
    "provider_session_id" "text",
    CONSTRAINT "booking_payments_amount_check" CHECK (("amount" >= (0)::numeric)),
    CONSTRAINT "booking_payments_channel_check" CHECK (("channel" = ANY (ARRAY['manual'::"text", 'gateway'::"text"]))),
    CONSTRAINT "booking_payments_check" CHECK ((("online_processing_charge" >= (0)::numeric) AND ("online_processing_charge" <= "amount") AND (("channel" = 'gateway'::"text") OR ("online_processing_charge" = (0)::numeric)))),
    CONSTRAINT "booking_payments_collection_method_check" CHECK (("collection_method" = ANY (ARRAY['CASH'::"text", 'UPI_DIRECT'::"text"]))),
    CONSTRAINT "booking_payments_currency_check" CHECK (("currency" ~ '^[A-Z]{3}$'::"text")),
    CONSTRAINT "booking_payments_failure_code_check" CHECK ((("failure_code" IS NULL) OR ("char_length"("failure_code") <= 120))),
    CONSTRAINT "booking_payments_instrument_check" CHECK ((("instrument" IS NULL) OR ("instrument" = ANY (ARRAY['upi'::"text", 'card'::"text", 'netbanking'::"text", 'wallet'::"text", 'other'::"text"])))),
    CONSTRAINT "booking_payments_method_check" CHECK ((("method" IS NULL) OR ("method" = ANY (ARRAY['cash'::"text", 'online'::"text"])))),
    CONSTRAINT "booking_payments_platform_fee_amount_check" CHECK (("platform_fee_amount" >= (0)::numeric)),
    CONSTRAINT "booking_payments_purpose_check" CHECK (("purpose" = ANY (ARRAY['deposit'::"text", 'balance'::"text", 'full'::"text"]))),
    CONSTRAINT "booking_payments_settlement_model_check" CHECK (("settlement_model" = ANY (ARRAY['offline'::"text", 'platform_collect'::"text", 'direct_to_salon'::"text"]))),
    CONSTRAINT "booking_payments_status_check" CHECK (("status" = ANY (ARRAY['created'::"text", 'authorized'::"text", 'captured'::"text", 'failed'::"text", 'cancelled'::"text", 'expired'::"text", 'partially_refunded'::"text", 'refunded'::"text"]))),
    CONSTRAINT "ck_booking_payments_commission_amount" CHECK ((("platform_commission_amount" >= (0)::numeric) AND ("platform_commission_amount" <= "amount") AND (("commission_rate_percent" IS NULL) OR (("commission_rate_percent" >= (0)::numeric) AND ("commission_rate_percent" <= (100)::numeric))))),
    CONSTRAINT "ck_booking_payments_commission_base" CHECK ((("commission_base" IS NULL) OR ("commission_base" = ANY (ARRAY['online_amount'::"text", 'booking_total'::"text"])))),
    CONSTRAINT "ck_booking_payments_gateway_amount_positive" CHECK ((("channel" = 'manual'::"text") OR ("amount" > (0)::numeric))),
    CONSTRAINT "ck_booking_payments_gateway_fee" CHECK ((("gateway_fee_amount" >= (0)::numeric) AND (("gateway_fee_amount" + "platform_commission_amount") <= "amount") AND (("gateway_fee_percent" IS NULL) OR (("gateway_fee_percent" >= (0)::numeric) AND ("gateway_fee_percent" <= (100)::numeric))) AND (("channel" = 'gateway'::"text") OR ("gateway_fee_amount" = (0)::numeric)))),
    CONSTRAINT "ck_booking_payments_manual_is_settled" CHECK ((("channel" = 'gateway'::"text") OR (("status" = 'captured'::"text") AND ("method" IS NOT NULL)))),
    CONSTRAINT "ck_booking_payments_overcollected" CHECK ((("overcollected_amount" >= (0)::numeric) AND ("overcollected_amount" <= "amount"))),
    CONSTRAINT "ck_booking_payments_provider_costs" CHECK (((("provider_fee_amount" IS NULL) OR ("provider_fee_amount" >= (0)::numeric)) AND (("provider_tax_amount" IS NULL) OR ("provider_tax_amount" >= (0)::numeric)))),
    CONSTRAINT "ck_booking_payments_provider_matches_channel" CHECK ((("channel" = 'manual'::"text") = ("provider" IS NULL)))
);


ALTER TABLE "public"."booking_payments" OWNER TO "postgres";

--
-- Name: booking_services; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."booking_services" (
    "booking_id" "uuid" NOT NULL,
    "service_id" "uuid" NOT NULL,
    "service_name" "text" NOT NULL,
    "duration_minutes" integer NOT NULL,
    "price" numeric(10,2) NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid"
);


ALTER TABLE "public"."booking_services" OWNER TO "postgres";

--
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."bookings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "staff_id" "uuid" NOT NULL,
    "customer_id" "uuid",
    "customer_name" "text" NOT NULL,
    "customer_phone" "text",
    "phone_verified" boolean DEFAULT false NOT NULL,
    "source" "public"."booking_source" DEFAULT 'app'::"public"."booking_source" NOT NULL,
    "status" "public"."booking_status" DEFAULT 'pending'::"public"."booking_status" NOT NULL,
    "start_datetime" timestamp with time zone NOT NULL,
    "end_datetime" timestamp with time zone NOT NULL,
    "total_duration_minutes" integer NOT NULL,
    "total_price" numeric(10,2) NOT NULL,
    "payment_status" "public"."payment_status" DEFAULT 'unpaid'::"public"."payment_status" NOT NULL,
    "payment_method" "public"."payment_method",
    "rejection_reason" "text",
    "notes" "text",
    "approved_by" "uuid",
    "approved_at" timestamp with time zone,
    "rejected_by" "uuid",
    "rejected_at" timestamp with time zone,
    "completed_by" "uuid",
    "completed_at" timestamp with time zone,
    "cancelled_by" "uuid",
    "cancelled_at" timestamp with time zone,
    "payment_recorded_by" "uuid",
    "payment_recorded_at" timestamp with time zone,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "cancellation_reason_code" "text",
    "cancellation_reason_text" "text",
    "estimated_end_datetime" timestamp with time zone,
    "payment_preference" "text",
    "cancellation_reason" "text",
    "currency" "text" DEFAULT 'INR'::"text" NOT NULL,
    "deposit_amount" numeric(10,2),
    "paid_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "refunded_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "booking_calendar_date" "date",
    "checkout_policy_version" "text" DEFAULT 'legacy'::"text" NOT NULL,
    CONSTRAINT "bookings_check" CHECK (("end_datetime" > "start_datetime")),
    CONSTRAINT "bookings_check2" CHECK ((("status" <> 'rejected'::"public"."booking_status") OR ("rejection_reason" IS NOT NULL))),
    CONSTRAINT "bookings_currency_format_check" CHECK (("currency" ~ '^[A-Z]{3}$'::"text")),
    CONSTRAINT "bookings_customer_or_walkin_check" CHECK ((("customer_id" IS NOT NULL) OR ("source" = 'manual_walkin'::"public"."booking_source") OR ("customer_name" = 'Deleted customer'::"text"))),
    CONSTRAINT "bookings_deposit_amount_check" CHECK ((("deposit_amount" IS NULL) OR (("deposit_amount" >= (0)::numeric) AND ("deposit_amount" <= "total_price")))),
    CONSTRAINT "bookings_paid_amounts_check" CHECK ((("paid_amount" >= (0)::numeric) AND ("refunded_amount" >= (0)::numeric) AND ("refunded_amount" <= "paid_amount"))),
    CONSTRAINT "bookings_payment_preference_check" CHECK ((("payment_preference" IS NULL) OR ("payment_preference" = ANY (ARRAY['pay_at_salon'::"text", 'pay_advance'::"text", 'pay_full'::"text"])))),
    CONSTRAINT "bookings_total_duration_minutes_check" CHECK (("total_duration_minutes" > 0)),
    CONSTRAINT "bookings_total_price_check" CHECK (("total_price" >= (0)::numeric))
);

ALTER TABLE ONLY "public"."bookings" REPLICA IDENTITY FULL;


ALTER TABLE "public"."bookings" OWNER TO "postgres";

--
-- Name: customer_booking_restrictions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."customer_booking_restrictions" (
    "customer_id" "uuid" NOT NULL,
    "no_show_count" integer DEFAULT 0 NOT NULL,
    "pay_at_salon_blocked_until" timestamp with time zone,
    CONSTRAINT "customer_booking_restrictions_no_show_count_check" CHECK (("no_show_count" >= 0))
);


ALTER TABLE "public"."customer_booking_restrictions" OWNER TO "postgres";

--
-- Name: device_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."device_tokens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "token" "text" NOT NULL,
    "platform" "text",
    "device_name" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "last_seen_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."device_tokens" OWNER TO "postgres";

--
-- Name: email_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."email_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "event_key" "text" NOT NULL,
    "event_type" "text" NOT NULL,
    "recipient" "text" NOT NULL,
    "subject" "text" NOT NULL,
    "body" "text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "provider_message_id" "text",
    "last_error_code" "text",
    "next_attempt_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "locked_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "sent_at" timestamp with time zone,
    CONSTRAINT "email_events_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'sent'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."email_events" OWNER TO "postgres";

--
-- Name: languages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."languages" (
    "code" "text" NOT NULL,
    "name" "text" NOT NULL
);


ALTER TABLE "public"."languages" OWNER TO "postgres";

--
-- Name: notification_deliveries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."notification_deliveries" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "notification_id" "uuid" NOT NULL,
    "device_token_id" "uuid" NOT NULL,
    "delivered" boolean DEFAULT false NOT NULL,
    "error" "text",
    "attempted_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."notification_deliveries" OWNER TO "postgres";

--
-- Name: notification_outbox; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."notification_outbox" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "notification_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "next_attempt_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_error" "text",
    "processed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "notification_outbox_attempts_check" CHECK (("attempts" >= 0)),
    CONSTRAINT "notification_outbox_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processed'::"text"])))
);


ALTER TABLE "public"."notification_outbox" OWNER TO "postgres";

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."notifications" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "booking_id" "uuid",
    "type" "text",
    "title" "text" NOT NULL,
    "body" "text",
    "read" boolean DEFAULT false NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "read_at" timestamp with time zone,
    "data" "jsonb"
);


ALTER TABLE "public"."notifications" OWNER TO "postgres";

--
-- Name: payment_anomalies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_anomalies" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "kind" "text" NOT NULL,
    "provider" "text",
    "provider_ref" "text",
    "salon_id" "uuid",
    "booking_id" "uuid",
    "payment_id" "uuid",
    "amount" numeric(10,2),
    "detail" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "resolved_at" timestamp with time zone,
    "resolved_by" "uuid",
    CONSTRAINT "payment_anomalies_detail_check" CHECK ((("detail" IS NULL) OR ("char_length"("detail") <= 300))),
    CONSTRAINT "payment_anomalies_kind_check" CHECK (("kind" = ANY (ARRAY['overcollection'::"text", 'amount_mismatch'::"text", 'settlement_failed'::"text", 'settlement_reversed'::"text", 'refund_onhold'::"text", 'refund_failed'::"text", 'subscription_amount_mismatch'::"text", 'subscription_duplicate_payment'::"text", 'subscription_blocked'::"text", 'subscription_refund'::"text", 'subscription_unused_period'::"text"])))
);


ALTER TABLE "public"."payment_anomalies" OWNER TO "postgres";

--
-- Name: payment_idempotency_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_idempotency_keys" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "actor_id" "uuid" NOT NULL,
    "scope" "text" NOT NULL,
    "idempotency_key" "text" NOT NULL,
    "request_fingerprint" "text" NOT NULL,
    "response_status" integer,
    "response_body" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    CONSTRAINT "payment_idempotency_keys_idempotency_key_check" CHECK ((("char_length"("idempotency_key") >= 8) AND ("char_length"("idempotency_key") <= 200)))
);


ALTER TABLE "public"."payment_idempotency_keys" OWNER TO "postgres";

--
-- Name: payment_provider_account_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_provider_account_audit" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "provider" "text" NOT NULL,
    "action" "text" NOT NULL,
    "previous_status" "text",
    "new_status" "text",
    "vendor_ref" "text",
    "actor_id" "uuid",
    "detail" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "payment_provider_account_audit_action_check" CHECK (("action" = ANY (ARRAY['registered'::"text", 're_registered'::"text", 'status_changed'::"text", 'register_failed'::"text"]))),
    CONSTRAINT "payment_provider_account_audit_detail_check" CHECK ((("detail" IS NULL) OR ("char_length"("detail") <= 300)))
);


ALTER TABLE "public"."payment_provider_account_audit" OWNER TO "postgres";

--
-- Name: payment_provider_accounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_provider_accounts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "provider" "text" NOT NULL,
    "provider_account_ref" "text",
    "onboarding_status" "text" DEFAULT 'not_started'::"text" NOT NULL,
    "requirements" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "registration_generation" integer DEFAULT 1 NOT NULL,
    CONSTRAINT "ck_payment_provider_accounts_generation" CHECK (("registration_generation" >= 1)),
    CONSTRAINT "payment_provider_accounts_onboarding_status_check" CHECK (("onboarding_status" = ANY (ARRAY['not_started'::"text", 'pending'::"text", 'needs_action'::"text", 'active'::"text", 'rejected'::"text", 'suspended'::"text"])))
);


ALTER TABLE "public"."payment_provider_accounts" OWNER TO "postgres";

--
-- Name: payment_refunds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_refunds" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "payment_id" "uuid" NOT NULL,
    "booking_id" "uuid" NOT NULL,
    "provider" "text",
    "refund_ref" "text",
    "amount" numeric(10,2) NOT NULL,
    "status" "text" DEFAULT 'created'::"text" NOT NULL,
    "reason" "text",
    "idempotency_key" "text" NOT NULL,
    "failure_code" "text",
    "requested_by" "uuid",
    "processed_at" timestamp with time zone,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "commission_reversal_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "applies_to_excess" boolean DEFAULT false NOT NULL,
    "kind" "text" DEFAULT 'owner'::"text" NOT NULL,
    "deduction_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    CONSTRAINT "ck_payment_refunds_deduction" CHECK ((("deduction_amount" >= (0)::numeric) AND ("attempts" >= 0) AND (("kind" = 'customer_cancellation'::"text") OR ("deduction_amount" = (0)::numeric)))),
    CONSTRAINT "ck_payment_refunds_kind" CHECK (("kind" = ANY (ARRAY['owner'::"text", 'customer_cancellation'::"text", 'salon_cancellation'::"text", 'closure'::"text"]))),
    CONSTRAINT "ck_payment_refunds_reversal" CHECK ((("commission_reversal_amount" >= (0)::numeric) AND ("commission_reversal_amount" <= "amount") AND ((NOT "applies_to_excess") OR ("commission_reversal_amount" = (0)::numeric)))),
    CONSTRAINT "payment_refunds_amount_check" CHECK (("amount" > (0)::numeric)),
    CONSTRAINT "payment_refunds_failure_code_check" CHECK ((("failure_code" IS NULL) OR ("char_length"("failure_code") <= 120))),
    CONSTRAINT "payment_refunds_idempotency_key_check" CHECK ((("char_length"("idempotency_key") >= 1) AND ("char_length"("idempotency_key") <= 200))),
    CONSTRAINT "payment_refunds_reason_check" CHECK ((("reason" IS NULL) OR ("char_length"("reason") <= 500))),
    CONSTRAINT "payment_refunds_status_check" CHECK (("status" = ANY (ARRAY['created'::"text", 'processed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."payment_refunds" OWNER TO "postgres";

--
-- Name: payment_webhook_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."payment_webhook_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "provider_name" "text" NOT NULL,
    "provider_event_reference" "text" NOT NULL,
    "event_type" "text" NOT NULL,
    "payload_hash" "text" NOT NULL,
    "normalized" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "processing_status" "text" DEFAULT 'received'::"text" NOT NULL,
    "attempts" integer DEFAULT 0 NOT NULL,
    "next_attempt_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "locked_at" timestamp with time zone,
    "last_error_code" "text",
    "received_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "processed_at" timestamp with time zone,
    CONSTRAINT "payment_webhook_events_attempts_check" CHECK (("attempts" >= 0)),
    CONSTRAINT "payment_webhook_events_last_error_code_check" CHECK ((("last_error_code" IS NULL) OR ("char_length"("last_error_code") <= 120))),
    CONSTRAINT "payment_webhook_events_processing_status_check" CHECK (("processing_status" = ANY (ARRAY['received'::"text", 'processing'::"text", 'processed'::"text", 'ignored'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."payment_webhook_events" OWNER TO "postgres";

--
-- Name: profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."profiles" (
    "id" "uuid" NOT NULL,
    "role" "public"."user_role" DEFAULT 'customer'::"public"."user_role" NOT NULL,
    "full_name" "text",
    "email" "text",
    "phone" "text",
    "phone_verified" boolean DEFAULT false NOT NULL,
    "avatar_url" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."profiles" OWNER TO "postgres";

--
-- Name: salon_access; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_access" (
    "salon_id" "uuid" NOT NULL,
    "trial_started_at" timestamp with time zone,
    "trial_ends_at" timestamp with time zone,
    "trial_booking_limit" integer DEFAULT 120 NOT NULL,
    "trial_limit_reached_at" timestamp with time zone,
    "trial_ended_reason" "text",
    "bookings_counted" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "ck_salon_access_started" CHECK ((("trial_started_at" IS NOT NULL) OR (("trial_limit_reached_at" IS NULL) AND ("trial_ended_reason" IS NULL)))),
    CONSTRAINT "ck_salon_access_window" CHECK ((("trial_ends_at" IS NULL) OR (("trial_started_at" IS NOT NULL) AND ("trial_ends_at" > "trial_started_at")))),
    CONSTRAINT "salon_access_bookings_counted_check" CHECK (("bookings_counted" >= 0)),
    CONSTRAINT "salon_access_trial_booking_limit_check" CHECK ((("trial_booking_limit" >= 1) AND ("trial_booking_limit" <= 100000))),
    CONSTRAINT "salon_access_trial_ended_reason_check" CHECK (("trial_ended_reason" = ANY (ARRAY['booking_limit'::"text", 'date'::"text"])))
);


ALTER TABLE "public"."salon_access" OWNER TO "postgres";

--
-- Name: salon_holidays; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_holidays" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "holiday_date" "date" NOT NULL,
    "title" "text",
    "is_recurring" boolean DEFAULT false NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "reason" "text"
);


ALTER TABLE "public"."salon_holidays" OWNER TO "postgres";

--
-- Name: salon_images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_images" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "url" "text" NOT NULL,
    "caption" "text",
    "is_main" boolean DEFAULT false NOT NULL,
    "sort_order" integer DEFAULT 0 NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL
);


ALTER TABLE "public"."salon_images" OWNER TO "postgres";

--
-- Name: salon_payout_account_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_payout_account_history" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "changed_by" "uuid",
    "changed_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "action" "text" NOT NULL,
    "changed_fields" "text"[] DEFAULT '{}'::"text"[] NOT NULL,
    "before_state" "jsonb",
    "after_state" "jsonb" NOT NULL,
    CONSTRAINT "salon_payout_account_history_action_check" CHECK (("action" = ANY (ARRAY['created'::"text", 'updated'::"text"])))
);


ALTER TABLE "public"."salon_payout_account_history" OWNER TO "postgres";

--
-- Name: salon_reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_reports" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "reporter_id" "uuid" NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "reason" "text" NOT NULL,
    "details" "text" DEFAULT ''::"text" NOT NULL,
    "status" "text" DEFAULT 'received'::"text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "salon_reports_details_check" CHECK (("length"("details") <= 5000)),
    CONSTRAINT "salon_reports_reason_check" CHECK ((("length"(TRIM(BOTH FROM "reason")) >= 1) AND ("length"(TRIM(BOTH FROM "reason")) <= 200))),
    CONSTRAINT "salon_reports_status_check" CHECK (("status" = 'received'::"text"))
);


ALTER TABLE "public"."salon_reports" OWNER TO "postgres";

--
-- Name: salon_subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salon_subscriptions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "plan_id" "uuid" NOT NULL,
    "status" "public"."subscription_status" DEFAULT 'pending'::"public"."subscription_status" NOT NULL,
    "starts_at" timestamp with time zone,
    "current_period_start" timestamp with time zone,
    "current_period_end" timestamp with time zone,
    "cancelled_at" timestamp with time zone,
    "expires_at" timestamp with time zone,
    "grace_period_end" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_by" "uuid",
    "created_by" "uuid"
);


ALTER TABLE "public"."salon_subscriptions" OWNER TO "postgres";

--
-- Name: salons; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."salons" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "owner_id" "uuid",
    "name" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "address" "text",
    "city" "text",
    "lat" double precision,
    "lng" double precision,
    "timezone" "text" DEFAULT 'Asia/Kolkata'::"text" NOT NULL,
    "working_hours" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "approval_mode" "public"."approval_mode" DEFAULT 'manual'::"public"."approval_mode" NOT NULL,
    "slot_interval_minutes" integer DEFAULT 15 NOT NULL,
    "qr_token" "text" DEFAULT "encode"("extensions"."gen_random_bytes"(16), 'hex'::"text") NOT NULL,
    "profile_completed" boolean DEFAULT false NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "qr_image_url" "text",
    "approval_status" "public"."salon_approval_status" DEFAULT 'pending'::"public"."salon_approval_status" NOT NULL,
    "approved_at" timestamp with time zone,
    "approved_by" "uuid",
    "rejection_reason" "text",
    "display_priority" integer DEFAULT 0 NOT NULL,
    "discovery_visibility" "text" DEFAULT 'listed'::"text" NOT NULL,
    "home_placement" "text" DEFAULT 'normal'::"text" NOT NULL,
    "accepting_bookings" boolean DEFAULT true NOT NULL,
    CONSTRAINT "salons_discovery_visibility_check" CHECK (("discovery_visibility" = ANY (ARRAY['listed'::"text", 'search_only'::"text", 'hidden'::"text"]))),
    CONSTRAINT "salons_display_priority_range" CHECK ((("display_priority" >= 0) AND ("display_priority" <= 100000))),
    CONSTRAINT "salons_home_placement_check" CHECK (("home_placement" = ANY (ARRAY['top'::"text", 'normal'::"text", 'below'::"text", 'random'::"text"]))),
    CONSTRAINT "salons_slot_interval_minutes_check" CHECK (("slot_interval_minutes" > 0))
);


ALTER TABLE "public"."salons" OWNER TO "postgres";

--
-- Name: service_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."service_categories" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "image_url" "text",
    "description" "text",
    "sort_order" integer DEFAULT 0 NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."service_categories" OWNER TO "postgres";

--
-- Name: service_subcategories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."service_subcategories" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "category_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "image_url" "text",
    "description" "text",
    "sort_order" integer DEFAULT 0 NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."service_subcategories" OWNER TO "postgres";

--
-- Name: services; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."services" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "subcategory_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "duration_minutes" integer NOT NULL,
    "price" numeric(10,2) NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "category_name" character varying(80),
    "subcategory_name" character varying(80),
    "photo_url" "text",
    CONSTRAINT "services_duration_minutes_check" CHECK (("duration_minutes" > 0)),
    CONSTRAINT "services_price_check" CHECK (("price" >= (0)::numeric))
);


ALTER TABLE "public"."services" OWNER TO "postgres";

--
-- Name: staff; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."staff" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "profile_id" "uuid",
    "name" "text" NOT NULL,
    "photo_url" "text",
    "specialization" "text",
    "working_hours" "jsonb",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "experience" "text"
);


ALTER TABLE "public"."staff" OWNER TO "postgres";

--
-- Name: staff_service_languages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."staff_service_languages" (
    "staff_service_id" "uuid" NOT NULL,
    "language_code" "text" NOT NULL
);


ALTER TABLE "public"."staff_service_languages" OWNER TO "postgres";

--
-- Name: staff_services; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."staff_services" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "staff_id" "uuid" NOT NULL,
    "service_id" "uuid" NOT NULL,
    "duration_minutes" integer,
    "price_override" numeric(10,2),
    "specialization" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "staff_services_duration_minutes_check" CHECK ((("duration_minutes" IS NULL) OR ("duration_minutes" > 0))),
    CONSTRAINT "staff_services_price_override_check" CHECK ((("price_override" IS NULL) OR ("price_override" >= (0)::numeric)))
);


ALTER TABLE "public"."staff_services" OWNER TO "postgres";

--
-- Name: subscription_billing_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."subscription_billing_records" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "plan_id" "uuid" NOT NULL,
    "plan_code" "text" NOT NULL,
    "provider" "text" NOT NULL,
    "receipt" "text" NOT NULL,
    "provider_order_ref" "text",
    "provider_payment_ref" "text",
    "status" "text" DEFAULT 'created'::"text" NOT NULL,
    "amount" numeric(10,2) NOT NULL,
    "currency" character varying(3) NOT NULL,
    "billing_interval" "text" NOT NULL,
    "tax_amount" numeric(10,2),
    "tax_inclusive" boolean,
    "benefits" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "refunded_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "period_start" timestamp with time zone,
    "period_end" timestamp with time zone,
    "subscription_id" "uuid",
    "expires_at" timestamp with time zone NOT NULL,
    "paid_at" timestamp with time zone,
    "applied_at" timestamp with time zone,
    "failure_code" "text",
    "created_by" "uuid",
    "updated_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "ck_subscription_billing_applied" CHECK ((("applied_at" IS NULL) OR (("period_end" IS NOT NULL) AND ("subscription_id" IS NOT NULL)))),
    CONSTRAINT "ck_subscription_billing_paid_ref" CHECK ((("status" <> ALL (ARRAY['paid'::"text", 'partially_refunded'::"text", 'refunded'::"text"])) OR ("provider_payment_ref" IS NOT NULL))),
    CONSTRAINT "ck_subscription_billing_period" CHECK (((("period_start" IS NULL) AND ("period_end" IS NULL)) OR (("period_start" IS NOT NULL) AND ("period_end" > "period_start")))),
    CONSTRAINT "subscription_billing_records_amount_check" CHECK (("amount" > (0)::numeric)),
    CONSTRAINT "subscription_billing_records_billing_interval_check" CHECK (("billing_interval" = ANY (ARRAY['monthly'::"text", 'quarterly'::"text", 'semiannual'::"text", 'yearly'::"text"]))),
    CONSTRAINT "subscription_billing_records_check" CHECK ((("refunded_amount" >= (0)::numeric) AND ("refunded_amount" <= "amount"))),
    CONSTRAINT "subscription_billing_records_currency_check" CHECK ((("currency")::"text" ~ '^[A-Z]{3}$'::"text")),
    CONSTRAINT "subscription_billing_records_failure_code_check" CHECK ((("failure_code" IS NULL) OR ("char_length"("failure_code") <= 120))),
    CONSTRAINT "subscription_billing_records_receipt_check" CHECK ((("char_length"("receipt") >= 8) AND ("char_length"("receipt") <= 40))),
    CONSTRAINT "subscription_billing_records_status_check" CHECK (("status" = ANY (ARRAY['created'::"text", 'authorized'::"text", 'paid'::"text", 'failed'::"text", 'expired'::"text", 'refunded'::"text", 'partially_refunded'::"text"]))),
    CONSTRAINT "subscription_billing_records_tax_amount_check" CHECK ((("tax_amount" IS NULL) OR ("tax_amount" >= (0)::numeric)))
);


ALTER TABLE "public"."subscription_billing_records" OWNER TO "postgres";

--
-- Name: subscription_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."subscription_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_subscription_id" "uuid",
    "provider_name" character varying(60),
    "provider_event_reference" character varying(400),
    "event_type" character varying(80) NOT NULL,
    "payload_hash" character varying(128),
    "received_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "processed_at" timestamp with time zone,
    "processing_status" "public"."subscription_event_processing_status" DEFAULT 'received'::"public"."subscription_event_processing_status" NOT NULL,
    "error_message" "text"
);


ALTER TABLE "public"."subscription_events" OWNER TO "postgres";

--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."subscription_plans" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "code" character varying(60) NOT NULL,
    "name" character varying(120) NOT NULL,
    "description" "text",
    "tier" smallint DEFAULT 0 NOT NULL,
    "ranking_weight" integer DEFAULT 0 NOT NULL,
    "price_amount" numeric(10,2) DEFAULT 0 NOT NULL,
    "currency" character varying(3) DEFAULT 'INR'::character varying NOT NULL,
    "billing_interval" character varying(20) DEFAULT 'monthly'::character varying NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_by" "uuid",
    "created_by" "uuid",
    "features" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "tax_inclusive" boolean,
    CONSTRAINT "ck_subscription_plans_currency" CHECK ((("currency")::"text" ~ '^[A-Z]{3}$'::"text")),
    CONSTRAINT "ck_subscription_plans_interval" CHECK ((("billing_interval")::"text" = ANY (ARRAY[('monthly'::character varying)::"text", ('quarterly'::character varying)::"text", ('semiannual'::character varying)::"text", ('yearly'::character varying)::"text"]))),
    CONSTRAINT "ck_subscription_plans_price" CHECK (("price_amount" >= (0)::numeric)),
    CONSTRAINT "subscription_plans_ranking_weight_range" CHECK ((("ranking_weight" >= 0) AND ("ranking_weight" <= 100000)))
);


ALTER TABLE "public"."subscription_plans" OWNER TO "postgres";

--
-- Name: subscription_provider_accounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."subscription_provider_accounts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "provider_name" character varying(60),
    "provider_customer_reference" character varying(400),
    "provider_subscription_reference" character varying(400),
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."subscription_provider_accounts" OWNER TO "postgres";

--
-- Name: support_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."support_messages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ticket_id" "uuid" NOT NULL,
    "author_id" "uuid",
    "body" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "support_messages_body_check" CHECK ((("char_length"("body") >= 1) AND ("char_length"("body") <= 5000)))
);


ALTER TABLE "public"."support_messages" OWNER TO "postgres";

--
-- Name: support_tickets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."support_tickets" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "customer_id" "uuid" NOT NULL,
    "salon_id" "uuid",
    "subject" "text" NOT NULL,
    "status" "text" DEFAULT 'open'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "support_tickets_status_check" CHECK (("status" = ANY (ARRAY['open'::"text", 'replied'::"text", 'closed'::"text"]))),
    CONSTRAINT "support_tickets_subject_check" CHECK ((("char_length"("subject") >= 1) AND ("char_length"("subject") <= 200)))
);


ALTER TABLE "public"."support_tickets" OWNER TO "postgres";

--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TABLE "realtime"."messages" (
    "topic" "text" NOT NULL,
    "extension" "text" NOT NULL,
    "payload" "jsonb",
    "event" "text",
    "private" boolean DEFAULT false,
    "updated_at" timestamp without time zone DEFAULT "now"() NOT NULL,
    "inserted_at" timestamp without time zone DEFAULT "now"() NOT NULL,
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "binary_payload" "bytea",
    "skip_broadcast" boolean DEFAULT false NOT NULL
)
PARTITION BY RANGE ("inserted_at");


ALTER TABLE "realtime"."messages" OWNER TO "supabase_realtime_admin";

--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE "realtime"."schema_migrations" (
    "version" bigint NOT NULL,
    "inserted_at" timestamp(0) without time zone DEFAULT "now"()
);


ALTER TABLE "realtime"."schema_migrations" OWNER TO "supabase_admin";

--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TABLE "realtime"."subscription" (
    "id" bigint NOT NULL,
    "subscription_id" "uuid" NOT NULL,
    "entity" "regclass" NOT NULL,
    "filters" "realtime"."user_defined_filter"[] DEFAULT '{}'::"realtime"."user_defined_filter"[] NOT NULL,
    "claims" "jsonb" NOT NULL,
    "claims_role" "regrole" GENERATED ALWAYS AS ("realtime"."to_regrole"(("claims" ->> 'role'::"text"))) STORED NOT NULL,
    "created_at" timestamp without time zone DEFAULT "timezone"('utc'::"text", "now"()) NOT NULL,
    "action_filter" "text" DEFAULT '*'::"text",
    "selected_columns" "text"[],
    CONSTRAINT "subscription_action_filter_check" CHECK (("action_filter" = ANY (ARRAY['*'::"text", 'INSERT'::"text", 'UPDATE'::"text", 'DELETE'::"text"])))
);


ALTER TABLE "realtime"."subscription" OWNER TO "supabase_realtime_admin";

--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE "realtime"."subscription" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "realtime"."subscription_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."buckets" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "owner" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "public" boolean DEFAULT false,
    "avif_autodetection" boolean DEFAULT false,
    "file_size_limit" bigint,
    "allowed_mime_types" "text"[],
    "owner_id" "text",
    "type" "storage"."buckettype" DEFAULT 'STANDARD'::"storage"."buckettype" NOT NULL,
    "versioning_status" "text" DEFAULT 'DISABLED'::"text" NOT NULL,
    "lifecycle_configuration" "jsonb",
    "lifecycle_configuration_generation" "uuid",
    CONSTRAINT "buckets_lifecycle_configuration_pair_check" CHECK ((("lifecycle_configuration" IS NULL) = ("lifecycle_configuration_generation" IS NULL))),
    CONSTRAINT "buckets_lifecycle_configuration_shape_check" CHECK ((("lifecycle_configuration" IS NULL) OR (("jsonb_typeof"("lifecycle_configuration") = 'object'::"text") AND ("lifecycle_configuration" ? 'rules'::"text") AND
CASE
    WHEN ("jsonb_typeof"(("lifecycle_configuration" -> 'rules'::"text")) = 'array'::"text") THEN (("jsonb_array_length"(("lifecycle_configuration" -> 'rules'::"text")) >= 1) AND ("jsonb_array_length"(("lifecycle_configuration" -> 'rules'::"text")) <= 1000))
    ELSE false
END))),
    CONSTRAINT "buckets_lifecycle_configuration_standard_only_check" CHECK ((("type" = 'STANDARD'::"storage"."buckettype") OR (("lifecycle_configuration" IS NULL) AND ("lifecycle_configuration_generation" IS NULL)))),
    CONSTRAINT "buckets_versioning_dark_check" CHECK (("versioning_status" = 'DISABLED'::"text")),
    CONSTRAINT "buckets_versioning_standard_only_check" CHECK ((("type" = 'STANDARD'::"storage"."buckettype") OR ("versioning_status" = 'DISABLED'::"text"))),
    CONSTRAINT "buckets_versioning_status_check" CHECK (("versioning_status" = ANY (ARRAY['DISABLED'::"text", 'ENABLED'::"text", 'SUSPENDED'::"text"])))
);


ALTER TABLE "storage"."buckets" OWNER TO "supabase_storage_admin";

--
-- Name: COLUMN "buckets"."owner"; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN "storage"."buckets"."owner" IS 'Field is deprecated, use owner_id instead';


--
-- Name: buckets_analytics; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."buckets_analytics" (
    "name" "text" NOT NULL,
    "type" "storage"."buckettype" DEFAULT 'ANALYTICS'::"storage"."buckettype" NOT NULL,
    "format" "text" DEFAULT 'ICEBERG'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "deleted_at" timestamp with time zone
);


ALTER TABLE "storage"."buckets_analytics" OWNER TO "supabase_storage_admin";

--
-- Name: buckets_vectors; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."buckets_vectors" (
    "id" "text" NOT NULL,
    "type" "storage"."buckettype" DEFAULT 'VECTOR'::"storage"."buckettype" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "storage"."buckets_vectors" OWNER TO "supabase_storage_admin";

--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."migrations" (
    "id" integer NOT NULL,
    "name" character varying(100) NOT NULL,
    "hash" character varying(40) NOT NULL,
    "executed_at" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "storage"."migrations" OWNER TO "supabase_storage_admin";

--
-- Name: objects; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."objects" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "bucket_id" "text",
    "name" "text",
    "owner" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "last_accessed_at" timestamp with time zone DEFAULT "now"(),
    "metadata" "jsonb",
    "path_tokens" "text"[] GENERATED ALWAYS AS ("string_to_array"("name", '/'::"text")) STORED,
    "version" "text",
    "owner_id" "text",
    "user_metadata" "jsonb",
    "archived_at" timestamp with time zone,
    "is_delete_marker" boolean DEFAULT false NOT NULL,
    "is_versioned" boolean DEFAULT false NOT NULL
);


ALTER TABLE "storage"."objects" OWNER TO "supabase_storage_admin";

--
-- Name: COLUMN "objects"."owner"; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN "storage"."objects"."owner" IS 'Field is deprecated, use owner_id instead';


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."s3_multipart_uploads" (
    "id" "text" NOT NULL,
    "in_progress_size" bigint DEFAULT 0 NOT NULL,
    "upload_signature" "text" NOT NULL,
    "bucket_id" "text" NOT NULL,
    "key" "text" NOT NULL COLLATE "pg_catalog"."C",
    "version" "text" NOT NULL,
    "owner_id" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "user_metadata" "jsonb",
    "metadata" "jsonb"
);


ALTER TABLE "storage"."s3_multipart_uploads" OWNER TO "supabase_storage_admin";

--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."s3_multipart_uploads_parts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "upload_id" "text" NOT NULL,
    "size" bigint DEFAULT 0 NOT NULL,
    "part_number" integer NOT NULL,
    "bucket_id" "text" NOT NULL,
    "key" "text" NOT NULL COLLATE "pg_catalog"."C",
    "etag" "text" NOT NULL,
    "owner_id" "text",
    "version" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "storage"."s3_multipart_uploads_parts" OWNER TO "supabase_storage_admin";

--
-- Name: vector_indexes; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE "storage"."vector_indexes" (
    "id" "text" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL COLLATE "pg_catalog"."C",
    "bucket_id" "text" NOT NULL,
    "data_type" "text" NOT NULL,
    "dimension" integer NOT NULL,
    "distance_metric" "text" NOT NULL,
    "metadata_configuration" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "storage"."vector_indexes" OWNER TO "supabase_storage_admin";

--
-- Name: schema_migrations; Type: TABLE; Schema: supabase_migrations; Owner: postgres
--

CREATE TABLE "supabase_migrations"."schema_migrations" (
    "version" "text" NOT NULL,
    "statements" "text"[],
    "name" "text",
    "created_by" "text",
    "idempotency_key" "text",
    "rollback" "text"[]
);


ALTER TABLE "supabase_migrations"."schema_migrations" OWNER TO "postgres";

--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."refresh_tokens" ALTER COLUMN "id" SET DEFAULT "nextval"('"auth"."refresh_tokens_id_seq"'::"regclass");


--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_amr_claims"
    ADD CONSTRAINT "amr_id_pk" PRIMARY KEY ("id");


--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."audit_log_entries"
    ADD CONSTRAINT "audit_log_entries_pkey" PRIMARY KEY ("id");


--
-- Name: custom_oauth_providers custom_oauth_providers_identifier_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."custom_oauth_providers"
    ADD CONSTRAINT "custom_oauth_providers_identifier_key" UNIQUE ("identifier");


--
-- Name: custom_oauth_providers custom_oauth_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."custom_oauth_providers"
    ADD CONSTRAINT "custom_oauth_providers_pkey" PRIMARY KEY ("id");


--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."flow_state"
    ADD CONSTRAINT "flow_state_pkey" PRIMARY KEY ("id");


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."identities"
    ADD CONSTRAINT "identities_pkey" PRIMARY KEY ("id");


--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."identities"
    ADD CONSTRAINT "identities_provider_id_provider_unique" UNIQUE ("provider_id", "provider");


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."instances"
    ADD CONSTRAINT "instances_pkey" PRIMARY KEY ("id");


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_amr_claims"
    ADD CONSTRAINT "mfa_amr_claims_session_id_authentication_method_pkey" UNIQUE ("session_id", "authentication_method");


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_challenges"
    ADD CONSTRAINT "mfa_challenges_pkey" PRIMARY KEY ("id");


--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_factors"
    ADD CONSTRAINT "mfa_factors_last_challenged_at_key" UNIQUE ("last_challenged_at");


--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_factors"
    ADD CONSTRAINT "mfa_factors_pkey" PRIMARY KEY ("id");


--
-- Name: mfa_recovery_code_sets mfa_recovery_code_sets_mfa_factor_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_code_sets"
    ADD CONSTRAINT "mfa_recovery_code_sets_mfa_factor_id_key" UNIQUE ("mfa_factor_id");


--
-- Name: mfa_recovery_code_sets mfa_recovery_code_sets_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_code_sets"
    ADD CONSTRAINT "mfa_recovery_code_sets_pkey" PRIMARY KEY ("id");


--
-- Name: mfa_recovery_code_sets mfa_recovery_code_sets_user_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_code_sets"
    ADD CONSTRAINT "mfa_recovery_code_sets_user_id_key" UNIQUE ("user_id");


--
-- Name: mfa_recovery_codes mfa_recovery_codes_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_codes"
    ADD CONSTRAINT "mfa_recovery_codes_pkey" PRIMARY KEY ("id");


--
-- Name: oauth_authorizations oauth_authorizations_authorization_code_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_authorizations"
    ADD CONSTRAINT "oauth_authorizations_authorization_code_key" UNIQUE ("authorization_code");


--
-- Name: oauth_authorizations oauth_authorizations_authorization_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_authorizations"
    ADD CONSTRAINT "oauth_authorizations_authorization_id_key" UNIQUE ("authorization_id");


--
-- Name: oauth_authorizations oauth_authorizations_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_authorizations"
    ADD CONSTRAINT "oauth_authorizations_pkey" PRIMARY KEY ("id");


--
-- Name: oauth_client_states oauth_client_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_client_states"
    ADD CONSTRAINT "oauth_client_states_pkey" PRIMARY KEY ("id");


--
-- Name: oauth_clients oauth_clients_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_clients"
    ADD CONSTRAINT "oauth_clients_pkey" PRIMARY KEY ("id");


--
-- Name: oauth_consents oauth_consents_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_consents"
    ADD CONSTRAINT "oauth_consents_pkey" PRIMARY KEY ("id");


--
-- Name: oauth_consents oauth_consents_user_client_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_consents"
    ADD CONSTRAINT "oauth_consents_user_client_unique" UNIQUE ("user_id", "client_id");


--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."one_time_tokens"
    ADD CONSTRAINT "one_time_tokens_pkey" PRIMARY KEY ("id");


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_pkey" PRIMARY KEY ("id");


--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_token_unique" UNIQUE ("token");


--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_providers"
    ADD CONSTRAINT "saml_providers_entity_id_key" UNIQUE ("entity_id");


--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_providers"
    ADD CONSTRAINT "saml_providers_pkey" PRIMARY KEY ("id");


--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_relay_states"
    ADD CONSTRAINT "saml_relay_states_pkey" PRIMARY KEY ("id");


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."schema_migrations"
    ADD CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version");


--
-- Name: scim_tokens scim_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."scim_tokens"
    ADD CONSTRAINT "scim_tokens_pkey" PRIMARY KEY ("id");


--
-- Name: scim_users scim_users_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."scim_users"
    ADD CONSTRAINT "scim_users_pkey" PRIMARY KEY ("id");


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sessions"
    ADD CONSTRAINT "sessions_pkey" PRIMARY KEY ("id");


--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sso_domains"
    ADD CONSTRAINT "sso_domains_pkey" PRIMARY KEY ("id");


--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sso_providers"
    ADD CONSTRAINT "sso_providers_pkey" PRIMARY KEY ("id");


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."users"
    ADD CONSTRAINT "users_phone_key" UNIQUE ("phone");


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");


--
-- Name: webauthn_challenges webauthn_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."webauthn_challenges"
    ADD CONSTRAINT "webauthn_challenges_pkey" PRIMARY KEY ("id");


--
-- Name: webauthn_credentials webauthn_credentials_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."webauthn_credentials"
    ADD CONSTRAINT "webauthn_credentials_pkey" PRIMARY KEY ("id");


--
-- Name: account_deletion_challenges account_deletion_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_deletion_challenges"
    ADD CONSTRAINT "account_deletion_challenges_pkey" PRIMARY KEY ("id");


--
-- Name: account_deletion_requests account_deletion_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_deletion_requests"
    ADD CONSTRAINT "account_deletion_requests_pkey" PRIMARY KEY ("id");


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."alembic_version"
    ADD CONSTRAINT "alembic_version_pkc" PRIMARY KEY ("version_num");


--
-- Name: api_rate_limits api_rate_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."api_rate_limits"
    ADD CONSTRAINT "api_rate_limits_pkey" PRIMARY KEY ("bucket_hash");


--
-- Name: blocked_slots blocked_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_pkey" PRIMARY KEY ("id");


--
-- Name: booking_action_requests booking_action_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_pkey" PRIMARY KEY ("id");


--
-- Name: booking_audit_events booking_audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_pkey" PRIMARY KEY ("id");


--
-- Name: booking_payments booking_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_pkey" PRIMARY KEY ("id");


--
-- Name: booking_services booking_services_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_pkey" PRIMARY KEY ("booking_id", "service_id");


--
-- Name: bookings bookings_no_overlap; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_no_overlap" EXCLUDE USING "gist" ("staff_id" WITH =, "tstzrange"("start_datetime", "end_datetime") WITH &&) WHERE (("status" = ANY (ARRAY['pending'::"public"."booking_status", 'confirmed'::"public"."booking_status", 'checked_in'::"public"."booking_status"])));


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_pkey" PRIMARY KEY ("id");


--
-- Name: customer_booking_restrictions customer_booking_restrictions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."customer_booking_restrictions"
    ADD CONSTRAINT "customer_booking_restrictions_pkey" PRIMARY KEY ("customer_id");


--
-- Name: device_tokens device_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_pkey" PRIMARY KEY ("id");


--
-- Name: device_tokens device_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_token_key" UNIQUE ("token");


--
-- Name: email_events email_events_event_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_event_key_key" UNIQUE ("event_key");


--
-- Name: email_events email_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_pkey" PRIMARY KEY ("id");


--
-- Name: languages languages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."languages"
    ADD CONSTRAINT "languages_pkey" PRIMARY KEY ("code");


--
-- Name: notification_deliveries notification_deliveries_notification_id_device_token_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_notification_id_device_token_id_key" UNIQUE ("notification_id", "device_token_id");


--
-- Name: notification_deliveries notification_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_pkey" PRIMARY KEY ("id");


--
-- Name: notification_outbox notification_outbox_notification_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_notification_id_key" UNIQUE ("notification_id");


--
-- Name: notification_outbox notification_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_pkey" PRIMARY KEY ("id");


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");


--
-- Name: payment_anomalies payment_anomalies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_pkey" PRIMARY KEY ("id");


--
-- Name: payment_idempotency_keys payment_idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_idempotency_keys"
    ADD CONSTRAINT "payment_idempotency_keys_pkey" PRIMARY KEY ("id");


--
-- Name: payment_provider_account_audit payment_provider_account_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_pkey" PRIMARY KEY ("id");


--
-- Name: payment_provider_accounts payment_provider_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_pkey" PRIMARY KEY ("id");


--
-- Name: payment_refunds payment_refunds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_pkey" PRIMARY KEY ("id");


--
-- Name: payment_webhook_events payment_webhook_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_webhook_events"
    ADD CONSTRAINT "payment_webhook_events_pkey" PRIMARY KEY ("id");


--
-- Name: profiles profiles_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_email_key" UNIQUE ("email");


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");


--
-- Name: salon_access salon_access_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_access"
    ADD CONSTRAINT "salon_access_pkey" PRIMARY KEY ("salon_id");


--
-- Name: salon_holidays salon_holidays_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_pkey" PRIMARY KEY ("id");


--
-- Name: salon_images salon_images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_pkey" PRIMARY KEY ("id");


--
-- Name: salon_payout_account_history salon_payout_account_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_pkey" PRIMARY KEY ("id");


--
-- Name: salon_payout_accounts salon_payout_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_pkey" PRIMARY KEY ("salon_id");


--
-- Name: salon_reports salon_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_pkey" PRIMARY KEY ("id");


--
-- Name: salon_subscriptions salon_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_pkey" PRIMARY KEY ("id");


--
-- Name: salons salons_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_pkey" PRIMARY KEY ("id");


--
-- Name: salons salons_qr_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_qr_token_key" UNIQUE ("qr_token");


--
-- Name: service_categories service_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_pkey" PRIMARY KEY ("id");


--
-- Name: service_categories service_categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_slug_key" UNIQUE ("slug");


--
-- Name: service_subcategories service_subcategories_category_id_slug_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_category_id_slug_key" UNIQUE ("category_id", "slug");


--
-- Name: service_subcategories service_subcategories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_pkey" PRIMARY KEY ("id");


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_pkey" PRIMARY KEY ("id");


--
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_pkey" PRIMARY KEY ("id");


--
-- Name: staff_service_languages staff_service_languages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_pkey" PRIMARY KEY ("staff_service_id", "language_code");


--
-- Name: staff_services staff_services_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_pkey" PRIMARY KEY ("id");


--
-- Name: staff_services staff_services_staff_id_service_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_staff_id_service_id_key" UNIQUE ("staff_id", "service_id");


--
-- Name: subscription_billing_records subscription_billing_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_pkey" PRIMARY KEY ("id");


--
-- Name: subscription_events subscription_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_events"
    ADD CONSTRAINT "subscription_events_pkey" PRIMARY KEY ("id");


--
-- Name: subscription_plans subscription_plans_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_code_key" UNIQUE ("code");


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_pkey" PRIMARY KEY ("id");


--
-- Name: subscription_provider_accounts subscription_provider_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_pkey" PRIMARY KEY ("id");


--
-- Name: subscription_provider_accounts subscription_provider_accounts_salon_id_provider_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_salon_id_provider_name_key" UNIQUE ("salon_id", "provider_name");


--
-- Name: support_messages support_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_pkey" PRIMARY KEY ("id");


--
-- Name: support_tickets support_tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_pkey" PRIMARY KEY ("id");


--
-- Name: booking_payments uq_booking_payments_intent_reference; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_intent_reference" UNIQUE ("intent_reference");


--
-- Name: booking_payments uq_booking_payments_provider_order; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_provider_order" UNIQUE ("provider", "order_ref");


--
-- Name: booking_payments uq_booking_payments_provider_payment; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_provider_payment" UNIQUE ("provider", "payment_ref");


--
-- Name: payment_anomalies uq_payment_anomalies_ref; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "uq_payment_anomalies_ref" UNIQUE ("kind", "provider", "provider_ref");


--
-- Name: payment_idempotency_keys uq_payment_idempotency; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_idempotency_keys"
    ADD CONSTRAINT "uq_payment_idempotency" UNIQUE ("actor_id", "scope", "idempotency_key");


--
-- Name: payment_provider_accounts uq_payment_provider_accounts_salon; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "uq_payment_provider_accounts_salon" UNIQUE ("salon_id", "provider");


--
-- Name: payment_refunds uq_payment_refunds_idempotency; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "uq_payment_refunds_idempotency" UNIQUE ("payment_id", "idempotency_key");


--
-- Name: payment_refunds uq_payment_refunds_provider_ref; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "uq_payment_refunds_provider_ref" UNIQUE ("provider", "refund_ref");


--
-- Name: payment_webhook_events uq_payment_webhook_events_provider_ref; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_webhook_events"
    ADD CONSTRAINT "uq_payment_webhook_events_provider_ref" UNIQUE ("provider_name", "provider_event_reference");


--
-- Name: subscription_billing_records uq_subscription_billing_receipt; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "uq_subscription_billing_receipt" UNIQUE ("receipt");


--
-- Name: messages messages_payload_exclusive; Type: CHECK CONSTRAINT; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE "realtime"."messages"
    ADD CONSTRAINT "messages_payload_exclusive" CHECK ((("payload" IS NULL) OR ("binary_payload" IS NULL))) NOT VALID;


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE ONLY "realtime"."messages"
    ADD CONSTRAINT "messages_pkey" PRIMARY KEY ("id", "inserted_at");


--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE ONLY "realtime"."subscription"
    ADD CONSTRAINT "pk_subscription" PRIMARY KEY ("id");


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY "realtime"."schema_migrations"
    ADD CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version");


--
-- Name: buckets_analytics buckets_analytics_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."buckets_analytics"
    ADD CONSTRAINT "buckets_analytics_pkey" PRIMARY KEY ("id");


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."buckets"
    ADD CONSTRAINT "buckets_pkey" PRIMARY KEY ("id");


--
-- Name: buckets_vectors buckets_vectors_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."buckets_vectors"
    ADD CONSTRAINT "buckets_vectors_pkey" PRIMARY KEY ("id");


--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."migrations"
    ADD CONSTRAINT "migrations_name_key" UNIQUE ("name");


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."migrations"
    ADD CONSTRAINT "migrations_pkey" PRIMARY KEY ("id");


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."objects"
    ADD CONSTRAINT "objects_pkey" PRIMARY KEY ("id");


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."s3_multipart_uploads_parts"
    ADD CONSTRAINT "s3_multipart_uploads_parts_pkey" PRIMARY KEY ("id");


--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."s3_multipart_uploads"
    ADD CONSTRAINT "s3_multipart_uploads_pkey" PRIMARY KEY ("id");


--
-- Name: vector_indexes vector_indexes_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."vector_indexes"
    ADD CONSTRAINT "vector_indexes_pkey" PRIMARY KEY ("id");


--
-- Name: schema_migrations schema_migrations_idempotency_key_key; Type: CONSTRAINT; Schema: supabase_migrations; Owner: postgres
--

ALTER TABLE ONLY "supabase_migrations"."schema_migrations"
    ADD CONSTRAINT "schema_migrations_idempotency_key_key" UNIQUE ("idempotency_key");


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: supabase_migrations; Owner: postgres
--

ALTER TABLE ONLY "supabase_migrations"."schema_migrations"
    ADD CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version");


--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "audit_logs_instance_id_idx" ON "auth"."audit_log_entries" USING "btree" ("instance_id");


--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "confirmation_token_idx" ON "auth"."users" USING "btree" ("confirmation_token") WHERE (("confirmation_token")::"text" !~ '^[0-9 ]*$'::"text");


--
-- Name: custom_oauth_providers_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "custom_oauth_providers_created_at_idx" ON "auth"."custom_oauth_providers" USING "btree" ("created_at");


--
-- Name: custom_oauth_providers_enabled_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "custom_oauth_providers_enabled_idx" ON "auth"."custom_oauth_providers" USING "btree" ("enabled");


--
-- Name: custom_oauth_providers_identifier_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "custom_oauth_providers_identifier_idx" ON "auth"."custom_oauth_providers" USING "btree" ("identifier");


--
-- Name: custom_oauth_providers_provider_type_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "custom_oauth_providers_provider_type_idx" ON "auth"."custom_oauth_providers" USING "btree" ("provider_type");


--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "email_change_token_current_idx" ON "auth"."users" USING "btree" ("email_change_token_current") WHERE (("email_change_token_current")::"text" !~ '^[0-9 ]*$'::"text");


--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "email_change_token_new_idx" ON "auth"."users" USING "btree" ("email_change_token_new") WHERE (("email_change_token_new")::"text" !~ '^[0-9 ]*$'::"text");


--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "factor_id_created_at_idx" ON "auth"."mfa_factors" USING "btree" ("user_id", "created_at");


--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "flow_state_created_at_idx" ON "auth"."flow_state" USING "btree" ("created_at" DESC);


--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "identities_email_idx" ON "auth"."identities" USING "btree" ("email" "text_pattern_ops");


--
-- Name: INDEX "identities_email_idx"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX "auth"."identities_email_idx" IS 'Auth: Ensures indexed queries on the email column';


--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "identities_user_id_idx" ON "auth"."identities" USING "btree" ("user_id");


--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_auth_code" ON "auth"."flow_state" USING "btree" ("auth_code");


--
-- Name: idx_oauth_client_states_created_at; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_oauth_client_states_created_at" ON "auth"."oauth_client_states" USING "btree" ("created_at");


--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_user_id_auth_method" ON "auth"."flow_state" USING "btree" ("user_id", "authentication_method");


--
-- Name: idx_users_created_at_desc; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_users_created_at_desc" ON "auth"."users" USING "btree" ("created_at" DESC);


--
-- Name: idx_users_email; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_users_email" ON "auth"."users" USING "btree" ("email");


--
-- Name: idx_users_last_sign_in_at_desc; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_users_last_sign_in_at_desc" ON "auth"."users" USING "btree" ("last_sign_in_at" DESC);


--
-- Name: idx_users_name; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "idx_users_name" ON "auth"."users" USING "btree" ((("raw_user_meta_data" ->> 'name'::"text"))) WHERE (("raw_user_meta_data" ->> 'name'::"text") IS NOT NULL);


--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "mfa_challenge_created_at_idx" ON "auth"."mfa_challenges" USING "btree" ("created_at" DESC);


--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "mfa_factors_user_friendly_name_unique" ON "auth"."mfa_factors" USING "btree" ("friendly_name", "user_id") WHERE (TRIM(BOTH FROM "friendly_name") <> ''::"text");


--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "mfa_factors_user_id_idx" ON "auth"."mfa_factors" USING "btree" ("user_id");


--
-- Name: mfa_recovery_codes_set_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "mfa_recovery_codes_set_id_idx" ON "auth"."mfa_recovery_codes" USING "btree" ("mfa_recovery_code_set_id");


--
-- Name: oauth_auth_pending_exp_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "oauth_auth_pending_exp_idx" ON "auth"."oauth_authorizations" USING "btree" ("expires_at") WHERE ("status" = 'pending'::"auth"."oauth_authorization_status");


--
-- Name: oauth_clients_deleted_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "oauth_clients_deleted_at_idx" ON "auth"."oauth_clients" USING "btree" ("deleted_at");


--
-- Name: oauth_consents_active_client_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "oauth_consents_active_client_idx" ON "auth"."oauth_consents" USING "btree" ("client_id") WHERE ("revoked_at" IS NULL);


--
-- Name: oauth_consents_active_user_client_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "oauth_consents_active_user_client_idx" ON "auth"."oauth_consents" USING "btree" ("user_id", "client_id") WHERE ("revoked_at" IS NULL);


--
-- Name: oauth_consents_user_order_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "oauth_consents_user_order_idx" ON "auth"."oauth_consents" USING "btree" ("user_id", "granted_at" DESC);


--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "one_time_tokens_relates_to_hash_idx" ON "auth"."one_time_tokens" USING "hash" ("relates_to");


--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "one_time_tokens_token_hash_hash_idx" ON "auth"."one_time_tokens" USING "hash" ("token_hash");


--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "one_time_tokens_user_id_token_type_key" ON "auth"."one_time_tokens" USING "btree" ("user_id", "token_type");


--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "reauthentication_token_idx" ON "auth"."users" USING "btree" ("reauthentication_token") WHERE (("reauthentication_token")::"text" !~ '^[0-9 ]*$'::"text");


--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "recovery_token_idx" ON "auth"."users" USING "btree" ("recovery_token") WHERE (("recovery_token")::"text" !~ '^[0-9 ]*$'::"text");


--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "refresh_tokens_instance_id_idx" ON "auth"."refresh_tokens" USING "btree" ("instance_id");


--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "refresh_tokens_instance_id_user_id_idx" ON "auth"."refresh_tokens" USING "btree" ("instance_id", "user_id");


--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "refresh_tokens_parent_idx" ON "auth"."refresh_tokens" USING "btree" ("parent");


--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "refresh_tokens_session_id_revoked_idx" ON "auth"."refresh_tokens" USING "btree" ("session_id", "revoked");


--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "refresh_tokens_updated_at_idx" ON "auth"."refresh_tokens" USING "btree" ("updated_at" DESC);


--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "saml_providers_sso_provider_id_idx" ON "auth"."saml_providers" USING "btree" ("sso_provider_id");


--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "saml_relay_states_created_at_idx" ON "auth"."saml_relay_states" USING "btree" ("created_at" DESC);


--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "saml_relay_states_for_email_idx" ON "auth"."saml_relay_states" USING "btree" ("for_email");


--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "saml_relay_states_sso_provider_id_idx" ON "auth"."saml_relay_states" USING "btree" ("sso_provider_id");


--
-- Name: scim_tokens_expires_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_tokens_expires_at_idx" ON "auth"."scim_tokens" USING "btree" ("expires_at");


--
-- Name: scim_tokens_revoked_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_tokens_revoked_at_idx" ON "auth"."scim_tokens" USING "btree" ("revoked_at");


--
-- Name: scim_tokens_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_tokens_sso_provider_id_idx" ON "auth"."scim_tokens" USING "btree" ("sso_provider_id");


--
-- Name: scim_tokens_token_hash_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "scim_tokens_token_hash_key" ON "auth"."scim_tokens" USING "btree" ("token_hash");


--
-- Name: scim_users_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_created_at_idx" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "created_at", "id") WHERE ("deleted_at" IS NULL);


--
-- Name: scim_users_deleted_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_deleted_at_idx" ON "auth"."scim_users" USING "btree" ("deleted_at");


--
-- Name: scim_users_external_id_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "scim_users_external_id_key" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "external_id") WHERE (("external_id" IS NOT NULL) AND ("deleted_at" IS NULL));


--
-- Name: scim_users_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_id_idx" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "id") WHERE ("deleted_at" IS NULL);


--
-- Name: scim_users_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_sso_provider_id_idx" ON "auth"."scim_users" USING "btree" ("sso_provider_id");


--
-- Name: scim_users_updated_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_updated_at_idx" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "updated_at", "id") WHERE ("deleted_at" IS NULL);


--
-- Name: scim_users_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_user_id_idx" ON "auth"."scim_users" USING "btree" ("user_id");


--
-- Name: scim_users_user_name_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "scim_users_user_name_idx" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "user_name" COLLATE "C", "id") WHERE ("deleted_at" IS NULL);


--
-- Name: scim_users_user_name_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "scim_users_user_name_key" ON "auth"."scim_users" USING "btree" ("sso_provider_id", "user_name") WHERE ("deleted_at" IS NULL);


--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "sessions_not_after_idx" ON "auth"."sessions" USING "btree" ("not_after" DESC);


--
-- Name: sessions_oauth_client_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "sessions_oauth_client_id_idx" ON "auth"."sessions" USING "btree" ("oauth_client_id");


--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "sessions_user_id_idx" ON "auth"."sessions" USING "btree" ("user_id");


--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "sso_domains_domain_idx" ON "auth"."sso_domains" USING "btree" ("lower"("domain"));


--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "sso_domains_sso_provider_id_idx" ON "auth"."sso_domains" USING "btree" ("sso_provider_id");


--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "sso_providers_resource_id_idx" ON "auth"."sso_providers" USING "btree" ("lower"("resource_id"));


--
-- Name: sso_providers_resource_id_pattern_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "sso_providers_resource_id_pattern_idx" ON "auth"."sso_providers" USING "btree" ("resource_id" "text_pattern_ops");


--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "unique_phone_factor_per_user" ON "auth"."mfa_factors" USING "btree" ("user_id", "phone");


--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "user_id_created_at_idx" ON "auth"."sessions" USING "btree" ("user_id", "created_at");


--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "users_email_partial_key" ON "auth"."users" USING "btree" ("email") WHERE ("is_sso_user" = false);


--
-- Name: INDEX "users_email_partial_key"; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX "auth"."users_email_partial_key" IS 'Auth: A partial unique index that applies only when is_sso_user is false';


--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "users_instance_id_email_idx" ON "auth"."users" USING "btree" ("instance_id", "lower"(("email")::"text"));


--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "users_instance_id_idx" ON "auth"."users" USING "btree" ("instance_id");


--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "users_is_anonymous_idx" ON "auth"."users" USING "btree" ("is_anonymous");


--
-- Name: webauthn_challenges_expires_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "webauthn_challenges_expires_at_idx" ON "auth"."webauthn_challenges" USING "btree" ("expires_at");


--
-- Name: webauthn_challenges_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "webauthn_challenges_user_id_idx" ON "auth"."webauthn_challenges" USING "btree" ("user_id");


--
-- Name: webauthn_credentials_credential_id_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX "webauthn_credentials_credential_id_key" ON "auth"."webauthn_credentials" USING "btree" ("credential_id");


--
-- Name: webauthn_credentials_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX "webauthn_credentials_user_id_idx" ON "auth"."webauthn_credentials" USING "btree" ("user_id");


--
-- Name: idx_account_deletion_requests_due; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_account_deletion_requests_due" ON "public"."account_deletion_requests" USING "btree" ("status", "next_attempt_at") WHERE ("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'failed'::"text"]));


--
-- Name: idx_account_deletion_requests_open_age; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_account_deletion_requests_open_age" ON "public"."account_deletion_requests" USING "btree" ("requested_at") WHERE ("status" <> 'completed'::"text");


--
-- Name: idx_account_deletion_requests_requested; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_account_deletion_requests_requested" ON "public"."account_deletion_requests" USING "btree" ("requested_at" DESC);


--
-- Name: idx_blocked_salon_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_blocked_salon_time" ON "public"."blocked_slots" USING "btree" ("salon_id", "start_datetime", "end_datetime");


--
-- Name: idx_blocked_staff_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_blocked_staff_time" ON "public"."blocked_slots" USING "btree" ("staff_id", "start_datetime", "end_datetime");


--
-- Name: idx_booking_action_requests_booking; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_action_requests_booking" ON "public"."booking_action_requests" USING "btree" ("booking_id", "kind", "created_at" DESC);


--
-- Name: idx_booking_action_requests_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_action_requests_pending" ON "public"."booking_action_requests" USING "btree" ("status", "created_at");


--
-- Name: idx_booking_audit_history; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_audit_history" ON "public"."booking_audit_events" USING "btree" ("booking_id", "created_at");


--
-- Name: idx_booking_pay_at_salon_day; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_pay_at_salon_day" ON "public"."bookings" USING "btree" ("customer_id", "booking_calendar_date") WHERE (("payment_preference" = 'pay_at_salon'::"text") AND ("status" = ANY (ARRAY['pending'::"public"."booking_status", 'confirmed'::"public"."booking_status", 'checked_in'::"public"."booking_status"])));


--
-- Name: idx_booking_payments_booking; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_payments_booking" ON "public"."booking_payments" USING "btree" ("booking_id");


--
-- Name: idx_booking_payments_payer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_payments_payer" ON "public"."booking_payments" USING "btree" ("payer_id");


--
-- Name: idx_booking_payments_reconcile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_payments_reconcile" ON "public"."booking_payments" USING "btree" ("updated_at") WHERE (("channel" = 'gateway'::"text") AND ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"])));


--
-- Name: idx_booking_payments_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_payments_salon" ON "public"."booking_payments" USING "btree" ("salon_id", "created_at" DESC);


--
-- Name: idx_booking_services_service_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_booking_services_service_id" ON "public"."booking_services" USING "btree" ("service_id");


--
-- Name: idx_bookings_approved_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_approved_by" ON "public"."bookings" USING "btree" ("approved_by");


--
-- Name: idx_bookings_completed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_completed_by" ON "public"."bookings" USING "btree" ("completed_by");


--
-- Name: idx_bookings_customer; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_customer" ON "public"."bookings" USING "btree" ("customer_id");


--
-- Name: idx_bookings_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_pending" ON "public"."bookings" USING "btree" ("salon_id") WHERE ("status" = 'pending'::"public"."booking_status");


--
-- Name: idx_bookings_salon_day; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_salon_day" ON "public"."bookings" USING "btree" ("salon_id", "start_datetime");


--
-- Name: idx_bookings_staff_day; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_staff_day" ON "public"."bookings" USING "btree" ("staff_id", "start_datetime");


--
-- Name: idx_bookings_status_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_status_time" ON "public"."bookings" USING "btree" ("salon_id", "status", "start_datetime");


--
-- Name: idx_bookings_trial_count; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_bookings_trial_count" ON "public"."bookings" USING "btree" ("salon_id", "created_at");


--
-- Name: idx_deliveries_notification; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_deliveries_notification" ON "public"."notification_deliveries" USING "btree" ("notification_id");


--
-- Name: idx_device_tokens_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_device_tokens_active" ON "public"."device_tokens" USING "btree" ("user_id") WHERE "is_active";


--
-- Name: idx_email_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_email_pending" ON "public"."email_events" USING "btree" ("next_attempt_at") WHERE ("status" = ANY (ARRAY['pending'::"text", 'processing'::"text"]));


--
-- Name: idx_email_user_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_email_user_status" ON "public"."email_events" USING "btree" ("user_id", "created_at" DESC);


--
-- Name: idx_notification_deliveries_device_token_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_notification_deliveries_device_token_id" ON "public"."notification_deliveries" USING "btree" ("device_token_id");


--
-- Name: idx_notification_outbox_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_notification_outbox_pending" ON "public"."notification_outbox" USING "btree" ("next_attempt_at", "created_at") WHERE ("status" = 'pending'::"text");


--
-- Name: idx_notification_outbox_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_notification_outbox_user_id" ON "public"."notification_outbox" USING "btree" ("user_id");


--
-- Name: idx_notifications_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_notifications_booking_id" ON "public"."notifications" USING "btree" ("booking_id");


--
-- Name: idx_notifications_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_notifications_user" ON "public"."notifications" USING "btree" ("user_id", "read", "created_at" DESC);


--
-- Name: idx_payment_account_audit_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_account_audit_salon" ON "public"."payment_provider_account_audit" USING "btree" ("salon_id", "created_at" DESC);


--
-- Name: idx_payment_anomalies_open; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_anomalies_open" ON "public"."payment_anomalies" USING "btree" ("created_at") WHERE ("resolved_at" IS NULL);


--
-- Name: idx_payment_idempotency_expiry; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_idempotency_expiry" ON "public"."payment_idempotency_keys" USING "btree" ("expires_at");


--
-- Name: idx_payment_refunds_booking; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_refunds_booking" ON "public"."payment_refunds" USING "btree" ("booking_id");


--
-- Name: idx_payment_refunds_open; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_refunds_open" ON "public"."payment_refunds" USING "btree" ("updated_at") WHERE ("status" = 'created'::"text");


--
-- Name: idx_payment_webhook_events_due; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_payment_webhook_events_due" ON "public"."payment_webhook_events" USING "btree" ("next_attempt_at") WHERE ("processing_status" = ANY (ARRAY['received'::"text", 'processing'::"text", 'failed'::"text"]));


--
-- Name: idx_profiles_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_profiles_created_by" ON "public"."profiles" USING "btree" ("created_by");


--
-- Name: idx_profiles_phone; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_profiles_phone" ON "public"."profiles" USING "btree" ("phone");


--
-- Name: idx_profiles_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_profiles_role" ON "public"."profiles" USING "btree" ("role");


--
-- Name: idx_salon_access_eligibility; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_access_eligibility" ON "public"."salon_access" USING "btree" ("trial_ends_at") WHERE ("trial_limit_reached_at" IS NULL);


--
-- Name: idx_salon_holidays; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_holidays" ON "public"."salon_holidays" USING "btree" ("salon_id", "holiday_date");


--
-- Name: idx_salon_images_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_images_active" ON "public"."salon_images" USING "btree" ("salon_id", "is_active", "sort_order");


--
-- Name: idx_salon_images_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_images_salon" ON "public"."salon_images" USING "btree" ("salon_id", "sort_order");


--
-- Name: idx_salon_payout_history_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_payout_history_salon" ON "public"."salon_payout_account_history" USING "btree" ("salon_id", "changed_at" DESC);


--
-- Name: idx_salon_subscriptions_plan_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_subscriptions_plan_id" ON "public"."salon_subscriptions" USING "btree" ("plan_id");


--
-- Name: idx_salon_subscriptions_salon_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_subscriptions_salon_id" ON "public"."salon_subscriptions" USING "btree" ("salon_id");


--
-- Name: idx_salon_subscriptions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salon_subscriptions_status" ON "public"."salon_subscriptions" USING "btree" ("status");


--
-- Name: idx_salons_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salons_active" ON "public"."salons" USING "btree" ("is_active", "profile_completed");


--
-- Name: idx_salons_approval_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salons_approval_status" ON "public"."salons" USING "btree" ("approval_status");


--
-- Name: idx_salons_city; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salons_city" ON "public"."salons" USING "btree" ("city");


--
-- Name: idx_salons_owner; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salons_owner" ON "public"."salons" USING "btree" ("owner_id");


--
-- Name: idx_salons_updated_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_salons_updated_by" ON "public"."salons" USING "btree" ("updated_by");


--
-- Name: idx_services_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_services_salon" ON "public"."services" USING "btree" ("salon_id", "is_active");


--
-- Name: idx_services_subcategory; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_services_subcategory" ON "public"."services" USING "btree" ("subcategory_id") WHERE "is_active";


--
-- Name: idx_services_updated_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_services_updated_by" ON "public"."services" USING "btree" ("updated_by");


--
-- Name: idx_ssl_language; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_ssl_language" ON "public"."staff_service_languages" USING "btree" ("language_code");


--
-- Name: idx_staff_profile_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_staff_profile_id" ON "public"."staff" USING "btree" ("profile_id");


--
-- Name: idx_staff_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_staff_salon" ON "public"."staff" USING "btree" ("salon_id", "is_active");


--
-- Name: idx_staff_services_service; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_staff_services_service" ON "public"."staff_services" USING "btree" ("service_id") WHERE "is_active";


--
-- Name: idx_staff_services_staff; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_staff_services_staff" ON "public"."staff_services" USING "btree" ("staff_id") WHERE "is_active";


--
-- Name: idx_subcategories_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subcategories_category" ON "public"."service_subcategories" USING "btree" ("category_id", "is_active");


--
-- Name: idx_subscription_billing_open; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subscription_billing_open" ON "public"."subscription_billing_records" USING "btree" ("updated_at") WHERE ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"]));


--
-- Name: idx_subscription_billing_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subscription_billing_salon" ON "public"."subscription_billing_records" USING "btree" ("salon_id", "created_at" DESC);


--
-- Name: idx_subscription_billing_unapplied; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subscription_billing_unapplied" ON "public"."subscription_billing_records" USING "btree" ("updated_at") WHERE (("status" = ANY (ARRAY['paid'::"text", 'partially_refunded'::"text"])) AND ("applied_at" IS NULL));


--
-- Name: idx_subscription_booking_eligibility; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subscription_booking_eligibility" ON "public"."salon_subscriptions" USING "btree" ("salon_id", "current_period_end") WHERE ("status" = ANY (ARRAY['active'::"public"."subscription_status", 'cancelled'::"public"."subscription_status"]));


--
-- Name: idx_subscription_events_subscription; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_subscription_events_subscription" ON "public"."subscription_events" USING "btree" ("salon_subscription_id");


--
-- Name: idx_support_customer_history; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_support_customer_history" ON "public"."support_tickets" USING "btree" ("customer_id", "created_at" DESC);


--
-- Name: idx_support_message_thread; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_support_message_thread" ON "public"."support_messages" USING "btree" ("ticket_id", "created_at");


--
-- Name: salon_reports_reporter_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "salon_reports_reporter_idx" ON "public"."salon_reports" USING "btree" ("reporter_id", "created_at");


--
-- Name: salon_reports_salon_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "salon_reports_salon_idx" ON "public"."salon_reports" USING "btree" ("salon_id", "created_at");


--
-- Name: uq_account_deletion_challenge_live; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_account_deletion_challenge_live" ON "public"."account_deletion_challenges" USING "btree" ("user_id") WHERE ("status" = ANY (ARRAY['sent'::"text", 'verified'::"text"]));


--
-- Name: uq_account_deletion_request_open; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_account_deletion_request_open" ON "public"."account_deletion_requests" USING "btree" ("user_id") WHERE ("status" <> 'completed'::"text");


--
-- Name: uq_booking_action_requests_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_booking_action_requests_pending" ON "public"."booking_action_requests" USING "btree" ("booking_id", "kind") WHERE ("status" = 'pending'::"text");


--
-- Name: uq_booking_payments_one_open_intent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_booking_payments_one_open_intent" ON "public"."booking_payments" USING "btree" ("booking_id") WHERE (("channel" = 'gateway'::"text") AND ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"])));


--
-- Name: uq_salon_holidays_active_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_salon_holidays_active_date" ON "public"."salon_holidays" USING "btree" ("salon_id", "holiday_date") WHERE "is_active";


--
-- Name: uq_salon_main_image; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_salon_main_image" ON "public"."salon_images" USING "btree" ("salon_id") WHERE "is_main";


--
-- Name: uq_salon_subscriptions_active_per_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_salon_subscriptions_active_per_salon" ON "public"."salon_subscriptions" USING "btree" ("salon_id") WHERE ("status" <> ALL (ARRAY['expired'::"public"."subscription_status", 'cancelled'::"public"."subscription_status", 'suspended'::"public"."subscription_status"]));


--
-- Name: uq_subscription_billing_open_per_salon; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_subscription_billing_open_per_salon" ON "public"."subscription_billing_records" USING "btree" ("salon_id") WHERE ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"]));


--
-- Name: uq_subscription_billing_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_subscription_billing_order" ON "public"."subscription_billing_records" USING "btree" ("provider", "provider_order_ref") WHERE ("provider_order_ref" IS NOT NULL);


--
-- Name: uq_subscription_billing_payment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_subscription_billing_payment" ON "public"."subscription_billing_records" USING "btree" ("provider", "provider_payment_ref") WHERE ("provider_payment_ref" IS NOT NULL);


--
-- Name: uq_subscription_events_provider_ref; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "uq_subscription_events_provider_ref" ON "public"."subscription_events" USING "btree" ("provider_name", "provider_event_reference") WHERE (("provider_name" IS NOT NULL) AND ("provider_event_reference" IS NOT NULL));


--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE INDEX "ix_realtime_subscription_entity" ON "realtime"."subscription" USING "btree" ("entity");


--
-- Name: messages_inserted_at_topic_index; Type: INDEX; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE INDEX "messages_inserted_at_topic_index" ON ONLY "realtime"."messages" USING "btree" ("inserted_at" DESC, "topic") WHERE (("extension" = 'broadcast'::"text") AND ("private" IS TRUE));


--
-- Name: subscription_subscription_id_entity_filters_action_filter_selec; Type: INDEX; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE UNIQUE INDEX "subscription_subscription_id_entity_filters_action_filter_selec" ON "realtime"."subscription" USING "btree" ("subscription_id", "entity", "filters", "action_filter", COALESCE("selected_columns", '{}'::"text"[]));


--
-- Name: bname; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "bname" ON "storage"."buckets" USING "btree" ("name");


--
-- Name: buckets_analytics_unique_name_idx; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "buckets_analytics_unique_name_idx" ON "storage"."buckets_analytics" USING "btree" ("name") WHERE ("deleted_at" IS NULL);


--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX "idx_multipart_uploads_list" ON "storage"."s3_multipart_uploads" USING "btree" ("bucket_id", "key", "created_at");


--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX "idx_objects_bucket_id_name" ON "storage"."objects" USING "btree" ("bucket_id", "name" COLLATE "C");


--
-- Name: idx_objects_bucket_id_name_lower; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX "idx_objects_bucket_id_name_lower" ON "storage"."objects" USING "btree" ("bucket_id", "lower"("name") COLLATE "C");


--
-- Name: idx_objects_current_version; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "idx_objects_current_version" ON "storage"."objects" USING "btree" ("bucket_id", "name" COLLATE "C") WHERE ("archived_at" IS NULL);


--
-- Name: idx_objects_delete_markers; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX "idx_objects_delete_markers" ON "storage"."objects" USING "btree" ("bucket_id", "name" COLLATE "C") WHERE "is_delete_marker";


--
-- Name: idx_objects_null_version; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "idx_objects_null_version" ON "storage"."objects" USING "btree" ("bucket_id", "name" COLLATE "C") WHERE (NOT "is_versioned");


--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX "name_prefix_search" ON "storage"."objects" USING "btree" ("name" "text_pattern_ops");


--
-- Name: objects_bucket_id_name_version_key; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "objects_bucket_id_name_version_key" ON "storage"."objects" USING "btree" ("bucket_id", "name" COLLATE "C", "version") NULLS NOT DISTINCT;


--
-- Name: vector_indexes_name_bucket_id_idx; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX "vector_indexes_name_bucket_id_idx" ON "storage"."vector_indexes" USING "btree" ("name", "bucket_id");


--
-- Name: users t_on_auth_user_created; Type: TRIGGER; Schema: auth; Owner: supabase_auth_admin
--

CREATE TRIGGER "t_on_auth_user_created" AFTER INSERT ON "auth"."users" FOR EACH ROW EXECUTE FUNCTION "public"."handle_new_user"();


--
-- Name: bookings booking_audit_append; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "booking_audit_append" AFTER INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."booking_append_audit"();


--
-- Name: booking_audit_events booking_audit_immutable; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "booking_audit_immutable" BEFORE DELETE OR UPDATE ON "public"."booking_audit_events" FOR EACH ROW EXECUTE FUNCTION "public"."guard_audit_immutable"();


--
-- Name: bookings booking_checkout_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "booking_checkout_guard" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_checkout"();


--
-- Name: bookings booking_email_outbox; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "booking_email_outbox" AFTER INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."enqueue_booking_email"();


--
-- Name: bookings bookings_guard_salon_approval; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "bookings_guard_salon_approval" BEFORE INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_salon_approval"();


--
-- Name: bookings checkout_policy_stamp; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "checkout_policy_stamp" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_checkout_policy"();


--
-- Name: profiles media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('avatar_url');


--
-- Name: salon_images media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('url');


--
-- Name: salons media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('qr_image_url');


--
-- Name: service_categories media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('image_url');


--
-- Name: service_subcategories media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('image_url');


--
-- Name: services media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('photo_url');


--
-- Name: staff media_reference_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('photo_url');


--
-- Name: booking_payments payment_audit_append; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "payment_audit_append" AFTER INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."payment_append_audit"();


--
-- Name: booking_payments payment_collection_snapshot; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "payment_collection_snapshot" BEFORE INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."guard_collection_snapshot"();


--
-- Name: salon_subscriptions salon_subscriptions_guard_admin; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "salon_subscriptions_guard_admin" BEFORE INSERT OR DELETE OR UPDATE ON "public"."salon_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."guard_subscription_admin"();


--
-- Name: salons salons_guard_approval; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "salons_guard_approval" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_approval"();


--
-- Name: salons salons_guard_discovery_placement; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "salons_guard_discovery_placement" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_discovery_placement"();


--
-- Name: salons salons_guard_display_priority; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "salons_guard_display_priority" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_display_priority"();


--
-- Name: subscription_billing_records subscription_billing_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "subscription_billing_guard" BEFORE UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."tg_subscription_billing_guard"();


--
-- Name: subscription_plans subscription_plans_guard_admin; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "subscription_plans_guard_admin" BEFORE INSERT OR DELETE OR UPDATE ON "public"."subscription_plans" FOR EACH ROW EXECUTE FUNCTION "public"."guard_subscription_admin"();


--
-- Name: blocked_slots t_blocked_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_blocked_audit" BEFORE INSERT OR UPDATE ON "public"."blocked_slots" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: blocked_slots t_blocked_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_blocked_updated" BEFORE UPDATE ON "public"."blocked_slots" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: booking_action_requests t_booking_action_requests_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_action_requests_audit" BEFORE INSERT OR UPDATE ON "public"."booking_action_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: booking_action_requests t_booking_action_requests_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_action_requests_updated" BEFORE UPDATE ON "public"."booking_action_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: booking_payments t_booking_payments_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_payments_audit" BEFORE INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: booking_payments t_booking_payments_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_payments_guard" BEFORE UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."tg_booking_payments_guard"();


--
-- Name: booking_payments t_booking_payments_recompute; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_payments_recompute" AFTER INSERT OR DELETE OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."tg_booking_payments_recompute"();


--
-- Name: booking_payments t_booking_payments_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_payments_updated" BEFORE UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: booking_services t_booking_services_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_booking_services_audit" BEFORE INSERT OR UPDATE ON "public"."booking_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: bookings t_bookings_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_audit" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: bookings t_bookings_closure_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_closure_guard" BEFORE INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_against_closure"();


--
-- Name: bookings t_bookings_lifecycle; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_lifecycle" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_booking_lifecycle"();


--
-- Name: bookings t_bookings_payment_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_payment_guard" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_payment_columns"();


--
-- Name: bookings t_bookings_trial_insert; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_trial_insert" AFTER INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."tg_bookings_recompute_trial"();


--
-- Name: bookings t_bookings_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_bookings_updated" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: service_categories t_categories_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_categories_audit" BEFORE INSERT OR UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: service_categories t_categories_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_categories_updated" BEFORE UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: notification_outbox t_notification_outbox_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_notification_outbox_updated" BEFORE UPDATE ON "public"."notification_outbox" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: payment_provider_accounts t_payment_provider_accounts_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_provider_accounts_audit" BEFORE INSERT OR UPDATE ON "public"."payment_provider_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: payment_provider_accounts t_payment_provider_accounts_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_provider_accounts_updated" BEFORE UPDATE ON "public"."payment_provider_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: payment_refunds t_payment_refunds_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_refunds_audit" BEFORE INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: payment_refunds t_payment_refunds_guard; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_refunds_guard" BEFORE INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."tg_payment_refunds_guard"();


--
-- Name: payment_refunds t_payment_refunds_recompute; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_refunds_recompute" AFTER INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."tg_payment_refunds_recompute"();


--
-- Name: payment_refunds t_payment_refunds_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_payment_refunds_updated" BEFORE UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: profiles t_profiles_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_profiles_audit" BEFORE INSERT OR UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: profiles t_profiles_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_profiles_updated" BEFORE UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: salon_holidays t_salon_holidays_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_holidays_audit" BEFORE INSERT OR UPDATE ON "public"."salon_holidays" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: salon_holidays t_salon_holidays_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_holidays_updated" BEFORE UPDATE ON "public"."salon_holidays" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: salon_images t_salon_images_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_images_audit" BEFORE INSERT OR UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: salon_images t_salon_images_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_images_updated" BEFORE UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: salon_images t_salon_main_image; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_main_image" BEFORE INSERT OR UPDATE OF "is_main" ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."demote_other_main_images"();


--
-- Name: salon_payout_accounts t_salon_payout_accounts_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_payout_accounts_audit" BEFORE INSERT OR UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: salon_payout_accounts t_salon_payout_accounts_history; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_payout_accounts_history" AFTER INSERT OR UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."tg_salon_payout_account_history"();


--
-- Name: salon_payout_accounts t_salon_payout_accounts_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_payout_accounts_updated" BEFORE UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: salon_subscriptions t_salon_subscriptions_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salon_subscriptions_audit" BEFORE INSERT OR UPDATE ON "public"."salon_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: salons t_salons_access_approved; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salons_access_approved" AFTER UPDATE OF "approval_status" ON "public"."salons" FOR EACH ROW WHEN ((("new"."approval_status" = 'approved'::"public"."salon_approval_status") AND ("old"."approval_status" IS DISTINCT FROM "new"."approval_status"))) EXECUTE FUNCTION "public"."tg_salons_access_row"();


--
-- Name: salons t_salons_access_insert; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salons_access_insert" AFTER INSERT ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."tg_salons_access_row"();


--
-- Name: salons t_salons_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salons_audit" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: salons t_salons_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_salons_updated" BEFORE UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: services t_services_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_services_audit" BEFORE INSERT OR UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: services t_services_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_services_updated" BEFORE UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: staff t_staff_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_staff_audit" BEFORE INSERT OR UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: staff_services t_staff_services_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_staff_services_audit" BEFORE INSERT OR UPDATE ON "public"."staff_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: staff_services t_staff_services_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_staff_services_updated" BEFORE UPDATE ON "public"."staff_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: staff t_staff_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_staff_updated" BEFORE UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: service_subcategories t_subcategories_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_subcategories_audit" BEFORE INSERT OR UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: service_subcategories t_subcategories_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_subcategories_updated" BEFORE UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: subscription_billing_records t_subscription_billing_records_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_subscription_billing_records_audit" BEFORE INSERT OR UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: subscription_billing_records t_subscription_billing_records_updated; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_subscription_billing_records_updated" BEFORE UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();


--
-- Name: subscription_plans t_subscription_plans_audit; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "t_subscription_plans_audit" BEFORE INSERT OR UPDATE ON "public"."subscription_plans" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();


--
-- Name: notifications trg_notification_read_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "trg_notification_read_at" BEFORE UPDATE ON "public"."notifications" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_notification_read_at"();


--
-- Name: booking_payments verified_payment_email; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER "verified_payment_email" AFTER INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."enqueue_verified_payment_receipt"();


--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TRIGGER "tr_check_filters" BEFORE INSERT OR UPDATE ON "realtime"."subscription" FOR EACH ROW EXECUTE FUNCTION "realtime"."subscription_check_filters"();


--
-- Name: buckets enforce_bucket_name_length_trigger; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "enforce_bucket_name_length_trigger" BEFORE INSERT OR UPDATE OF "name" ON "storage"."buckets" FOR EACH ROW EXECUTE FUNCTION "storage"."enforce_bucket_name_length"();


--
-- Name: buckets protect_bucket_control_insert; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "protect_bucket_control_insert" BEFORE INSERT ON "storage"."buckets" FOR EACH ROW EXECUTE FUNCTION "storage"."protect_bucket_control_columns"('service_role');


--
-- Name: buckets protect_bucket_control_update; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "protect_bucket_control_update" BEFORE UPDATE OF "lifecycle_configuration", "lifecycle_configuration_generation" ON "storage"."buckets" FOR EACH ROW EXECUTE FUNCTION "storage"."protect_bucket_control_columns"();


--
-- Name: buckets protect_bucket_control_update_role; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "protect_bucket_control_update_role" AFTER UPDATE OF "lifecycle_configuration", "lifecycle_configuration_generation" ON "storage"."buckets" FOR EACH ROW EXECUTE FUNCTION "storage"."enforce_bucket_lifecycle_service_role"('service_role');


--
-- Name: buckets protect_buckets_delete; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "protect_buckets_delete" BEFORE DELETE ON "storage"."buckets" FOR EACH STATEMENT EXECUTE FUNCTION "storage"."protect_delete"();


--
-- Name: objects protect_objects_delete; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "protect_objects_delete" BEFORE DELETE ON "storage"."objects" FOR EACH STATEMENT EXECUTE FUNCTION "storage"."protect_delete"();


--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER "update_objects_updated_at" BEFORE UPDATE ON "storage"."objects" FOR EACH ROW EXECUTE FUNCTION "storage"."update_updated_at_column"();


--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."identities"
    ADD CONSTRAINT "identities_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_amr_claims"
    ADD CONSTRAINT "mfa_amr_claims_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "auth"."sessions"("id") ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_challenges"
    ADD CONSTRAINT "mfa_challenges_auth_factor_id_fkey" FOREIGN KEY ("factor_id") REFERENCES "auth"."mfa_factors"("id") ON DELETE CASCADE;


--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_factors"
    ADD CONSTRAINT "mfa_factors_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: mfa_recovery_code_sets mfa_recovery_code_sets_mfa_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_code_sets"
    ADD CONSTRAINT "mfa_recovery_code_sets_mfa_factor_id_fkey" FOREIGN KEY ("mfa_factor_id") REFERENCES "auth"."mfa_factors"("id") ON DELETE CASCADE;


--
-- Name: mfa_recovery_code_sets mfa_recovery_code_sets_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_code_sets"
    ADD CONSTRAINT "mfa_recovery_code_sets_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: mfa_recovery_codes mfa_recovery_codes_mfa_recovery_code_set_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."mfa_recovery_codes"
    ADD CONSTRAINT "mfa_recovery_codes_mfa_recovery_code_set_id_fkey" FOREIGN KEY ("mfa_recovery_code_set_id") REFERENCES "auth"."mfa_recovery_code_sets"("id") ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_authorizations"
    ADD CONSTRAINT "oauth_authorizations_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE;


--
-- Name: oauth_authorizations oauth_authorizations_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_authorizations"
    ADD CONSTRAINT "oauth_authorizations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_consents"
    ADD CONSTRAINT "oauth_consents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE;


--
-- Name: oauth_consents oauth_consents_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."oauth_consents"
    ADD CONSTRAINT "oauth_consents_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."one_time_tokens"
    ADD CONSTRAINT "one_time_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."refresh_tokens"
    ADD CONSTRAINT "refresh_tokens_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "auth"."sessions"("id") ON DELETE CASCADE;


--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_providers"
    ADD CONSTRAINT "saml_providers_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_relay_states"
    ADD CONSTRAINT "saml_relay_states_flow_state_id_fkey" FOREIGN KEY ("flow_state_id") REFERENCES "auth"."flow_state"("id") ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."saml_relay_states"
    ADD CONSTRAINT "saml_relay_states_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE;


--
-- Name: scim_tokens scim_tokens_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."scim_tokens"
    ADD CONSTRAINT "scim_tokens_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE;


--
-- Name: scim_users scim_users_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."scim_users"
    ADD CONSTRAINT "scim_users_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE;


--
-- Name: scim_users scim_users_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."scim_users"
    ADD CONSTRAINT "scim_users_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE SET NULL;


--
-- Name: sessions sessions_oauth_client_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sessions"
    ADD CONSTRAINT "sessions_oauth_client_id_fkey" FOREIGN KEY ("oauth_client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sessions"
    ADD CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."sso_domains"
    ADD CONSTRAINT "sso_domains_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE;


--
-- Name: webauthn_challenges webauthn_challenges_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."webauthn_challenges"
    ADD CONSTRAINT "webauthn_challenges_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: webauthn_credentials webauthn_credentials_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY "auth"."webauthn_credentials"
    ADD CONSTRAINT "webauthn_credentials_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: account_deletion_challenges account_deletion_challenges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_deletion_challenges"
    ADD CONSTRAINT "account_deletion_challenges_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: blocked_slots blocked_slots_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: blocked_slots blocked_slots_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: blocked_slots blocked_slots_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id") ON DELETE CASCADE;


--
-- Name: blocked_slots blocked_slots_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_action_requests booking_action_requests_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;


--
-- Name: booking_action_requests booking_action_requests_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_action_requests booking_action_requests_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_requested_by_fkey" FOREIGN KEY ("requested_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_action_requests booking_action_requests_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_action_requests booking_action_requests_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_audit_events booking_audit_events_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "public"."profiles"("id") ON DELETE SET NULL;


--
-- Name: booking_audit_events booking_audit_events_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");


--
-- Name: booking_payments booking_payments_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");


--
-- Name: booking_payments booking_payments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_payments booking_payments_payer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_payer_id_fkey" FOREIGN KEY ("payer_id") REFERENCES "public"."profiles"("id");


--
-- Name: booking_payments booking_payments_recorded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_recorded_by_fkey" FOREIGN KEY ("recorded_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_payments booking_payments_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: booking_payments booking_payments_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_services booking_services_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;


--
-- Name: booking_services booking_services_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: booking_services booking_services_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_service_id_fkey" FOREIGN KEY ("service_id") REFERENCES "public"."services"("id");


--
-- Name: booking_services booking_services_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_approved_by_fkey" FOREIGN KEY ("approved_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_cancelled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_cancelled_by_fkey" FOREIGN KEY ("cancelled_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_completed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_completed_by_fkey" FOREIGN KEY ("completed_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_payment_recorded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_payment_recorded_by_fkey" FOREIGN KEY ("payment_recorded_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_rejected_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_rejected_by_fkey" FOREIGN KEY ("rejected_by") REFERENCES "public"."profiles"("id");


--
-- Name: bookings bookings_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: bookings bookings_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id");


--
-- Name: bookings bookings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: customer_booking_restrictions customer_booking_restrictions_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."customer_booking_restrictions"
    ADD CONSTRAINT "customer_booking_restrictions_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: device_tokens device_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: email_events email_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: notification_deliveries notification_deliveries_device_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_device_token_id_fkey" FOREIGN KEY ("device_token_id") REFERENCES "public"."device_tokens"("id") ON DELETE CASCADE;


--
-- Name: notification_deliveries notification_deliveries_notification_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "public"."notifications"("id") ON DELETE CASCADE;


--
-- Name: notification_outbox notification_outbox_notification_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "public"."notifications"("id") ON DELETE CASCADE;


--
-- Name: notification_outbox notification_outbox_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: notifications notifications_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: payment_anomalies payment_anomalies_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");


--
-- Name: payment_anomalies payment_anomalies_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "public"."booking_payments"("id");


--
-- Name: payment_anomalies payment_anomalies_resolved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "public"."profiles"("id");


--
-- Name: payment_anomalies payment_anomalies_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: payment_provider_account_audit payment_provider_account_audit_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "public"."profiles"("id");


--
-- Name: payment_provider_account_audit payment_provider_account_audit_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: payment_provider_accounts payment_provider_accounts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: payment_provider_accounts payment_provider_accounts_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: payment_provider_accounts payment_provider_accounts_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: payment_refunds payment_refunds_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");


--
-- Name: payment_refunds payment_refunds_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: payment_refunds payment_refunds_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "public"."booking_payments"("id");


--
-- Name: payment_refunds payment_refunds_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_requested_by_fkey" FOREIGN KEY ("requested_by") REFERENCES "public"."profiles"("id");


--
-- Name: payment_refunds payment_refunds_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: profiles profiles_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: profiles profiles_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;


--
-- Name: profiles profiles_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_access salon_access_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_access"
    ADD CONSTRAINT "salon_access_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: salon_holidays salon_holidays_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_holidays salon_holidays_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: salon_holidays salon_holidays_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_images salon_images_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_images salon_images_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: salon_images salon_images_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_payout_account_history salon_payout_account_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_changed_by_fkey" FOREIGN KEY ("changed_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_payout_account_history salon_payout_account_history_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: salon_payout_accounts salon_payout_accounts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_payout_accounts salon_payout_accounts_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;


--
-- Name: salon_payout_accounts salon_payout_accounts_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_reports salon_reports_reporter_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_reporter_id_fkey" FOREIGN KEY ("reporter_id") REFERENCES "public"."profiles"("id");


--
-- Name: salon_reports salon_reports_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: salon_subscriptions salon_subscriptions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: salon_subscriptions salon_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "public"."subscription_plans"("id");


--
-- Name: salon_subscriptions salon_subscriptions_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: salon_subscriptions salon_subscriptions_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: salons salons_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_approved_by_fkey" FOREIGN KEY ("approved_by") REFERENCES "public"."profiles"("id");


--
-- Name: salons salons_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: salons salons_owner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "public"."profiles"("id");


--
-- Name: salons salons_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: service_categories service_categories_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: service_categories service_categories_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: service_subcategories service_subcategories_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "public"."service_categories"("id");


--
-- Name: service_subcategories service_subcategories_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: service_subcategories service_subcategories_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: services services_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: services services_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: services services_subcategory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_subcategory_id_fkey" FOREIGN KEY ("subcategory_id") REFERENCES "public"."service_subcategories"("id");


--
-- Name: services services_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: staff staff_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: staff staff_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "public"."profiles"("id");


--
-- Name: staff staff_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: staff_service_languages staff_service_languages_language_code_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_language_code_fkey" FOREIGN KEY ("language_code") REFERENCES "public"."languages"("code");


--
-- Name: staff_service_languages staff_service_languages_staff_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_staff_service_id_fkey" FOREIGN KEY ("staff_service_id") REFERENCES "public"."staff_services"("id") ON DELETE CASCADE;


--
-- Name: staff_services staff_services_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: staff_services staff_services_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_service_id_fkey" FOREIGN KEY ("service_id") REFERENCES "public"."services"("id") ON DELETE CASCADE;


--
-- Name: staff_services staff_services_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id") ON DELETE CASCADE;


--
-- Name: staff_services staff_services_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: staff staff_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: subscription_billing_records subscription_billing_records_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: subscription_billing_records subscription_billing_records_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "public"."subscription_plans"("id");


--
-- Name: subscription_billing_records subscription_billing_records_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: subscription_billing_records subscription_billing_records_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "public"."salon_subscriptions"("id");


--
-- Name: subscription_billing_records subscription_billing_records_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: subscription_events subscription_events_salon_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_events"
    ADD CONSTRAINT "subscription_events_salon_subscription_id_fkey" FOREIGN KEY ("salon_subscription_id") REFERENCES "public"."salon_subscriptions"("id");


--
-- Name: subscription_plans subscription_plans_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");


--
-- Name: subscription_plans subscription_plans_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");


--
-- Name: subscription_provider_accounts subscription_provider_accounts_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: support_messages support_messages_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "public"."profiles"("id") ON DELETE SET NULL;


--
-- Name: support_messages support_messages_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_ticket_id_fkey" FOREIGN KEY ("ticket_id") REFERENCES "public"."support_tickets"("id") ON DELETE CASCADE;


--
-- Name: support_tickets support_tickets_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;


--
-- Name: support_tickets support_tickets_salon_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");


--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."objects"
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id");


--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."s3_multipart_uploads"
    ADD CONSTRAINT "s3_multipart_uploads_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id");


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."s3_multipart_uploads_parts"
    ADD CONSTRAINT "s3_multipart_uploads_parts_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id");


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."s3_multipart_uploads_parts"
    ADD CONSTRAINT "s3_multipart_uploads_parts_upload_id_fkey" FOREIGN KEY ("upload_id") REFERENCES "storage"."s3_multipart_uploads"("id") ON DELETE CASCADE;


--
-- Name: vector_indexes vector_indexes_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY "storage"."vector_indexes"
    ADD CONSTRAINT "vector_indexes_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets_vectors"("id");


--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."audit_log_entries" ENABLE ROW LEVEL SECURITY;

--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."flow_state" ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."identities" ENABLE ROW LEVEL SECURITY;

--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."instances" ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."mfa_amr_claims" ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."mfa_challenges" ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."mfa_factors" ENABLE ROW LEVEL SECURITY;

--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."one_time_tokens" ENABLE ROW LEVEL SECURITY;

--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."refresh_tokens" ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."saml_providers" ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."saml_relay_states" ENABLE ROW LEVEL SECURITY;

--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."schema_migrations" ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."sessions" ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."sso_domains" ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."sso_providers" ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE "auth"."users" ENABLE ROW LEVEL SECURITY;

--
-- Name: account_deletion_challenges; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."account_deletion_challenges" ENABLE ROW LEVEL SECURITY;

--
-- Name: account_deletion_requests; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."account_deletion_requests" ENABLE ROW LEVEL SECURITY;

--
-- Name: alembic_version; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."alembic_version" ENABLE ROW LEVEL SECURITY;

--
-- Name: api_rate_limits; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."api_rate_limits" ENABLE ROW LEVEL SECURITY;

--
-- Name: blocked_slots blocked_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "blocked_owner_write" ON "public"."blocked_slots" USING (((("staff_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "blocked_slots"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) OR (("salon_id" IS NOT NULL) AND "public"."owns_salon"("salon_id")))) WITH CHECK (((("staff_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "blocked_slots"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) OR (("salon_id" IS NOT NULL) AND "public"."owns_salon"("salon_id"))));


--
-- Name: blocked_slots blocked_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "blocked_read" ON "public"."blocked_slots" FOR SELECT USING (true);


--
-- Name: blocked_slots; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."blocked_slots" ENABLE ROW LEVEL SECURITY;

--
-- Name: booking_action_requests; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."booking_action_requests" ENABLE ROW LEVEL SECURITY;

--
-- Name: booking_action_requests booking_action_requests_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "booking_action_requests_read" ON "public"."booking_action_requests" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM ("public"."bookings" "b"
     JOIN "public"."salons" "s" ON (("s"."id" = "b"."salon_id")))
  WHERE (("b"."id" = "booking_action_requests"."booking_id") AND (("b"."customer_id" = "auth"."uid"()) OR ("s"."owner_id" = "auth"."uid"()) OR (EXISTS ( SELECT 1
           FROM "public"."staff" "access_staff"
          WHERE (("access_staff"."salon_id" = "b"."salon_id") AND ("access_staff"."profile_id" = "auth"."uid"()) AND "access_staff"."is_active"))) OR "public"."is_super_admin"())))));


--
-- Name: booking_audit_events; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."booking_audit_events" ENABLE ROW LEVEL SECURITY;

--
-- Name: booking_payments; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."booking_payments" ENABLE ROW LEVEL SECURITY;

--
-- Name: booking_payments booking_payments_parties_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "booking_payments_parties_read" ON "public"."booking_payments" FOR SELECT USING ((("payer_id" = "auth"."uid"()) OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: booking_services; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."booking_services" ENABLE ROW LEVEL SECURITY;

--
-- Name: booking_services booking_services_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "booking_services_read" ON "public"."booking_services" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."bookings" "b"
  WHERE (("b"."id" = "booking_services"."booking_id") AND (("b"."customer_id" = "auth"."uid"()) OR "public"."owns_salon"("b"."salon_id") OR "public"."is_super_admin"())))));


--
-- Name: bookings; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."bookings" ENABLE ROW LEVEL SECURITY;

--
-- Name: bookings bookings_customer_cancel; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "bookings_customer_cancel" ON "public"."bookings" FOR UPDATE USING (("customer_id" = "auth"."uid"())) WITH CHECK (("customer_id" = "auth"."uid"()));


--
-- Name: bookings bookings_owner_update; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "bookings_owner_update" ON "public"."bookings" FOR UPDATE USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: bookings bookings_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "bookings_read" ON "public"."bookings" FOR SELECT USING ((("customer_id" = "auth"."uid"()) OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: bookings bookings_staff_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "bookings_staff_read" ON "public"."bookings" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM "public"."staff" "access_staff"
  WHERE (("access_staff"."salon_id" = "bookings"."salon_id") AND ("access_staff"."profile_id" = "auth"."uid"()) AND "access_staff"."is_active"))));


--
-- Name: service_categories categories_admin_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "categories_admin_write" ON "public"."service_categories" USING ("public"."is_super_admin"()) WITH CHECK ("public"."is_super_admin"());


--
-- Name: service_categories categories_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "categories_read" ON "public"."service_categories" FOR SELECT USING (("is_active" OR "public"."is_super_admin"()));


--
-- Name: customer_booking_restrictions; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."customer_booking_restrictions" ENABLE ROW LEVEL SECURITY;

--
-- Name: notification_deliveries deliveries_own; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "deliveries_own" ON "public"."notification_deliveries" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."notifications" "n"
  WHERE (("n"."id" = "notification_deliveries"."notification_id") AND ("n"."user_id" = "auth"."uid"())))));


--
-- Name: device_tokens; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."device_tokens" ENABLE ROW LEVEL SECURITY;

--
-- Name: device_tokens device_tokens_own; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "device_tokens_own" ON "public"."device_tokens" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));


--
-- Name: email_events; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."email_events" ENABLE ROW LEVEL SECURITY;

--
-- Name: languages; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."languages" ENABLE ROW LEVEL SECURITY;

--
-- Name: languages languages_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "languages_read" ON "public"."languages" FOR SELECT USING (true);


--
-- Name: notification_deliveries; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."notification_deliveries" ENABLE ROW LEVEL SECURITY;

--
-- Name: notification_outbox; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."notification_outbox" ENABLE ROW LEVEL SECURITY;

--
-- Name: notifications; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."notifications" ENABLE ROW LEVEL SECURITY;

--
-- Name: notifications notifications_own; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "notifications_own" ON "public"."notifications" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));


--
-- Name: payment_anomalies; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_anomalies" ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_idempotency_keys; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_idempotency_keys" ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_provider_account_audit; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_provider_account_audit" ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_provider_account_audit payment_provider_account_audit_owner_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "payment_provider_account_audit_owner_read" ON "public"."payment_provider_account_audit" FOR SELECT USING (("public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: payment_provider_accounts; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_provider_accounts" ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_provider_accounts payment_provider_accounts_owner_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "payment_provider_accounts_owner_read" ON "public"."payment_provider_accounts" FOR SELECT USING (("public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: payment_refunds; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_refunds" ENABLE ROW LEVEL SECURITY;

--
-- Name: payment_refunds payment_refunds_parties_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "payment_refunds_parties_read" ON "public"."payment_refunds" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."booking_payments" "p"
  WHERE (("p"."id" = "payment_refunds"."payment_id") AND (("p"."payer_id" = "auth"."uid"()) OR "public"."owns_salon"("p"."salon_id") OR "public"."is_super_admin"())))));


--
-- Name: payment_webhook_events; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."payment_webhook_events" ENABLE ROW LEVEL SECURITY;

--
-- Name: profiles; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."profiles" ENABLE ROW LEVEL SECURITY;

--
-- Name: profiles profiles_self_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "profiles_self_read" ON "public"."profiles" FOR SELECT USING ((("id" = "auth"."uid"()) OR "public"."is_super_admin"()));


--
-- Name: profiles profiles_self_update; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "profiles_self_update" ON "public"."profiles" FOR UPDATE USING (("id" = "auth"."uid"()));


--
-- Name: salon_access; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_access" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_holidays; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_holidays" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_holidays salon_holidays_approval_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_holidays_approval_read" ON "public"."salon_holidays" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "salon_holidays"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));


--
-- Name: salon_holidays salon_holidays_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_holidays_owner_write" ON "public"."salon_holidays" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: salon_holidays salon_holidays_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_holidays_read" ON "public"."salon_holidays" FOR SELECT USING (true);


--
-- Name: salon_images; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_images" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_images salon_images_approval_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_images_approval_read" ON "public"."salon_images" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "salon_images"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));


--
-- Name: salon_images salon_images_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_images_owner_write" ON "public"."salon_images" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: salon_images salon_images_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_images_read" ON "public"."salon_images" FOR SELECT USING (true);


--
-- Name: salon_payout_account_history; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_payout_account_history" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_payout_accounts; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_payout_accounts" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_payout_accounts salon_payout_accounts_owner; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_payout_accounts_owner" ON "public"."salon_payout_accounts" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: salon_payout_account_history salon_payout_history_owner_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_payout_history_owner_read" ON "public"."salon_payout_account_history" FOR SELECT USING ("public"."owns_salon"("salon_id"));


--
-- Name: salon_reports; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_reports" ENABLE ROW LEVEL SECURITY;

--
-- Name: salon_reports salon_reports_self_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salon_reports_self_read" ON "public"."salon_reports" FOR SELECT TO "authenticated" USING ((("reporter_id" = "auth"."uid"()) AND "is_active"));


--
-- Name: salon_subscriptions; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salon_subscriptions" ENABLE ROW LEVEL SECURITY;

--
-- Name: salons; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."salons" ENABLE ROW LEVEL SECURITY;

--
-- Name: salons salons_owner_update; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salons_owner_update" ON "public"."salons" FOR UPDATE USING (("owner_id" = "auth"."uid"())) WITH CHECK ((("owner_id" = "auth"."uid"()) AND ("is_active" = ( SELECT "s"."is_active"
   FROM "public"."salons" "s"
  WHERE ("s"."id" = "salons"."id")))));


--
-- Name: salons salons_public_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "salons_public_read" ON "public"."salons" FOR SELECT USING ((("is_active" AND "profile_completed" AND ("approval_status" = 'approved'::"public"."salon_approval_status")) OR ("owner_id" = "auth"."uid"()) OR "public"."is_super_admin"()));


--
-- Name: service_categories; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."service_categories" ENABLE ROW LEVEL SECURITY;

--
-- Name: service_subcategories; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."service_subcategories" ENABLE ROW LEVEL SECURITY;

--
-- Name: services; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."services" ENABLE ROW LEVEL SECURITY;

--
-- Name: services services_approval_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "services_approval_read" ON "public"."services" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "services"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));


--
-- Name: services services_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "services_owner_write" ON "public"."services" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: services services_public_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "services_public_read" ON "public"."services" FOR SELECT USING (("is_active" OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: staff_service_languages ssl_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "ssl_owner_write" ON "public"."staff_service_languages" USING ((EXISTS ( SELECT 1
   FROM ("public"."staff_services" "ss"
     JOIN "public"."staff" "st" ON (("st"."id" = "ss"."staff_id")))
  WHERE (("ss"."id" = "staff_service_languages"."staff_service_id") AND "public"."owns_salon"("st"."salon_id"))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."staff_services" "ss"
     JOIN "public"."staff" "st" ON (("st"."id" = "ss"."staff_id")))
  WHERE (("ss"."id" = "staff_service_languages"."staff_service_id") AND "public"."owns_salon"("st"."salon_id")))));


--
-- Name: staff_service_languages ssl_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "ssl_read" ON "public"."staff_service_languages" FOR SELECT USING (true);


--
-- Name: staff; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."staff" ENABLE ROW LEVEL SECURITY;

--
-- Name: staff staff_approval_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "staff_approval_read" ON "public"."staff" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "staff"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));


--
-- Name: staff staff_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "staff_owner_write" ON "public"."staff" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));


--
-- Name: staff staff_public_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "staff_public_read" ON "public"."staff" FOR SELECT USING (("is_active" OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));


--
-- Name: staff_service_languages; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."staff_service_languages" ENABLE ROW LEVEL SECURITY;

--
-- Name: staff_services; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."staff_services" ENABLE ROW LEVEL SECURITY;

--
-- Name: staff_services staff_services_owner_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "staff_services_owner_write" ON "public"."staff_services" USING ((EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "staff_services"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "staff_services"."staff_id") AND "public"."owns_salon"("s"."salon_id")))));


--
-- Name: staff_services staff_services_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "staff_services_read" ON "public"."staff_services" FOR SELECT USING (true);


--
-- Name: service_subcategories subcategories_admin_write; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "subcategories_admin_write" ON "public"."service_subcategories" USING ("public"."is_super_admin"()) WITH CHECK ("public"."is_super_admin"());


--
-- Name: service_subcategories subcategories_read; Type: POLICY; Schema: public; Owner: postgres
--

CREATE POLICY "subcategories_read" ON "public"."service_subcategories" FOR SELECT USING (("is_active" OR "public"."is_super_admin"()));


--
-- Name: subscription_billing_records; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."subscription_billing_records" ENABLE ROW LEVEL SECURITY;

--
-- Name: subscription_events; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."subscription_events" ENABLE ROW LEVEL SECURITY;

--
-- Name: subscription_plans; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."subscription_plans" ENABLE ROW LEVEL SECURITY;

--
-- Name: subscription_provider_accounts; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."subscription_provider_accounts" ENABLE ROW LEVEL SECURITY;

--
-- Name: support_messages; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."support_messages" ENABLE ROW LEVEL SECURITY;

--
-- Name: support_tickets; Type: ROW SECURITY; Schema: public; Owner: postgres
--

ALTER TABLE "public"."support_tickets" ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE "realtime"."messages" ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."buckets" ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_analytics; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."buckets_analytics" ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets_vectors; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."buckets_vectors" ENABLE ROW LEVEL SECURITY;

--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."migrations" ENABLE ROW LEVEL SECURITY;

--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."objects" ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."s3_multipart_uploads" ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."s3_multipart_uploads_parts" ENABLE ROW LEVEL SECURITY;

--
-- Name: vector_indexes; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE "storage"."vector_indexes" ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: postgres
--

CREATE PUBLICATION "supabase_realtime" WITH (publish = 'insert, update, delete, truncate');


ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";

--
-- Name: supabase_realtime blocked_slots; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."blocked_slots";


--
-- Name: supabase_realtime booking_action_requests; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."booking_action_requests";


--
-- Name: supabase_realtime bookings; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."bookings";


--
-- Name: SCHEMA "auth"; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA "auth" TO "anon";
GRANT USAGE ON SCHEMA "auth" TO "authenticated";
GRANT USAGE ON SCHEMA "auth" TO "service_role";
GRANT ALL ON SCHEMA "auth" TO "supabase_auth_admin";
GRANT ALL ON SCHEMA "auth" TO "dashboard_user";
GRANT USAGE ON SCHEMA "auth" TO "postgres";


--
-- Name: SCHEMA "extensions"; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA "extensions" TO "anon";
GRANT USAGE ON SCHEMA "extensions" TO "authenticated";
GRANT USAGE ON SCHEMA "extensions" TO "service_role";
GRANT ALL ON SCHEMA "extensions" TO "dashboard_user";


--
-- Name: SCHEMA "public"; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";


--
-- Name: SCHEMA "realtime"; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA "realtime" TO "postgres" WITH GRANT OPTION;
GRANT USAGE ON SCHEMA "realtime" TO "anon";
GRANT USAGE ON SCHEMA "realtime" TO "service_role";
GRANT ALL ON SCHEMA "realtime" TO "supabase_realtime_admin";
GRANT USAGE ON SCHEMA "realtime" TO "authenticated";


--
-- Name: SCHEMA "storage"; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA "storage" TO "postgres" WITH GRANT OPTION;
GRANT USAGE ON SCHEMA "storage" TO "anon";
GRANT USAGE ON SCHEMA "storage" TO "authenticated";
GRANT USAGE ON SCHEMA "storage" TO "service_role";
GRANT ALL ON SCHEMA "storage" TO "supabase_storage_admin" WITH GRANT OPTION;
GRANT ALL ON SCHEMA "storage" TO "dashboard_user";


--
-- Name: SCHEMA "vault"; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA "vault" TO "postgres" WITH GRANT OPTION;
GRANT USAGE ON SCHEMA "vault" TO "service_role";


--
-- Name: FUNCTION "gbtreekey16_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey16_out"("public"."gbtreekey16"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "service_role";


--
-- Name: FUNCTION "gbtreekey2_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey2_out"("public"."gbtreekey2"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "service_role";


--
-- Name: FUNCTION "gbtreekey32_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey32_out"("public"."gbtreekey32"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "service_role";


--
-- Name: FUNCTION "gbtreekey4_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey4_out"("public"."gbtreekey4"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "service_role";


--
-- Name: FUNCTION "gbtreekey8_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey8_out"("public"."gbtreekey8"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "service_role";


--
-- Name: FUNCTION "gbtreekey_var_in"("cstring"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "service_role";


--
-- Name: FUNCTION "gbtreekey_var_out"("public"."gbtreekey_var"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "anon";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "service_role";


--
-- Name: FUNCTION "email"(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION "auth"."email"() TO "dashboard_user";


--
-- Name: FUNCTION "jwt"(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION "auth"."jwt"() TO "postgres";
GRANT ALL ON FUNCTION "auth"."jwt"() TO "dashboard_user";


--
-- Name: FUNCTION "role"(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION "auth"."role"() TO "dashboard_user";


--
-- Name: FUNCTION "uid"(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION "auth"."uid"() TO "dashboard_user";


--
-- Name: FUNCTION "armor"("bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."armor"("bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."armor"("bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."armor"("bytea") TO "dashboard_user";


--
-- Name: FUNCTION "armor"("bytea", "text"[], "text"[]); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."armor"("bytea", "text"[], "text"[]) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."armor"("bytea", "text"[], "text"[]) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."armor"("bytea", "text"[], "text"[]) TO "dashboard_user";


--
-- Name: FUNCTION "crypt"("text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."crypt"("text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."crypt"("text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."crypt"("text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "dearmor"("text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."dearmor"("text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."dearmor"("text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."dearmor"("text") TO "dashboard_user";


--
-- Name: FUNCTION "decrypt"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."decrypt"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."decrypt"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."decrypt"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "decrypt_iv"("bytea", "bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."decrypt_iv"("bytea", "bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."decrypt_iv"("bytea", "bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."decrypt_iv"("bytea", "bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "digest"("bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."digest"("bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."digest"("bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."digest"("bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "digest"("text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."digest"("text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."digest"("text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."digest"("text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "encrypt"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."encrypt"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."encrypt"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."encrypt"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "encrypt_iv"("bytea", "bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."encrypt_iv"("bytea", "bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."encrypt_iv"("bytea", "bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."encrypt_iv"("bytea", "bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "gen_random_bytes"(integer); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."gen_random_bytes"(integer) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."gen_random_bytes"(integer) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."gen_random_bytes"(integer) TO "dashboard_user";


--
-- Name: FUNCTION "gen_random_uuid"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."gen_random_uuid"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."gen_random_uuid"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."gen_random_uuid"() TO "dashboard_user";


--
-- Name: FUNCTION "gen_salt"("text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."gen_salt"("text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."gen_salt"("text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."gen_salt"("text") TO "dashboard_user";


--
-- Name: FUNCTION "gen_salt"("text", integer); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."gen_salt"("text", integer) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."gen_salt"("text", integer) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."gen_salt"("text", integer) TO "dashboard_user";


--
-- Name: FUNCTION "grant_pg_cron_access"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION "extensions"."grant_pg_cron_access"() FROM "supabase_admin";
GRANT ALL ON FUNCTION "extensions"."grant_pg_cron_access"() TO "supabase_admin" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."grant_pg_cron_access"() TO "dashboard_user";


--
-- Name: FUNCTION "grant_pg_graphql_access"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "extensions"."grant_pg_graphql_access"() TO "postgres" WITH GRANT OPTION;


--
-- Name: FUNCTION "grant_pg_net_access"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION "extensions"."grant_pg_net_access"() FROM "supabase_admin";
GRANT ALL ON FUNCTION "extensions"."grant_pg_net_access"() TO "supabase_admin" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."grant_pg_net_access"() TO "dashboard_user";


--
-- Name: FUNCTION "hmac"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."hmac"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."hmac"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."hmac"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "hmac"("text", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."hmac"("text", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."hmac"("text", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."hmac"("text", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pg_stat_statements"("showtext" boolean, OUT "userid" "oid", OUT "dbid" "oid", OUT "toplevel" boolean, OUT "queryid" bigint, OUT "query" "text", OUT "plans" bigint, OUT "total_plan_time" double precision, OUT "min_plan_time" double precision, OUT "max_plan_time" double precision, OUT "mean_plan_time" double precision, OUT "stddev_plan_time" double precision, OUT "calls" bigint, OUT "total_exec_time" double precision, OUT "min_exec_time" double precision, OUT "max_exec_time" double precision, OUT "mean_exec_time" double precision, OUT "stddev_exec_time" double precision, OUT "rows" bigint, OUT "shared_blks_hit" bigint, OUT "shared_blks_read" bigint, OUT "shared_blks_dirtied" bigint, OUT "shared_blks_written" bigint, OUT "local_blks_hit" bigint, OUT "local_blks_read" bigint, OUT "local_blks_dirtied" bigint, OUT "local_blks_written" bigint, OUT "temp_blks_read" bigint, OUT "temp_blks_written" bigint, OUT "shared_blk_read_time" double precision, OUT "shared_blk_write_time" double precision, OUT "local_blk_read_time" double precision, OUT "local_blk_write_time" double precision, OUT "temp_blk_read_time" double precision, OUT "temp_blk_write_time" double precision, OUT "wal_records" bigint, OUT "wal_fpi" bigint, OUT "wal_bytes" numeric, OUT "jit_functions" bigint, OUT "jit_generation_time" double precision, OUT "jit_inlining_count" bigint, OUT "jit_inlining_time" double precision, OUT "jit_optimization_count" bigint, OUT "jit_optimization_time" double precision, OUT "jit_emission_count" bigint, OUT "jit_emission_time" double precision, OUT "jit_deform_count" bigint, OUT "jit_deform_time" double precision, OUT "stats_since" timestamp with time zone, OUT "minmax_stats_since" timestamp with time zone); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pg_stat_statements"("showtext" boolean, OUT "userid" "oid", OUT "dbid" "oid", OUT "toplevel" boolean, OUT "queryid" bigint, OUT "query" "text", OUT "plans" bigint, OUT "total_plan_time" double precision, OUT "min_plan_time" double precision, OUT "max_plan_time" double precision, OUT "mean_plan_time" double precision, OUT "stddev_plan_time" double precision, OUT "calls" bigint, OUT "total_exec_time" double precision, OUT "min_exec_time" double precision, OUT "max_exec_time" double precision, OUT "mean_exec_time" double precision, OUT "stddev_exec_time" double precision, OUT "rows" bigint, OUT "shared_blks_hit" bigint, OUT "shared_blks_read" bigint, OUT "shared_blks_dirtied" bigint, OUT "shared_blks_written" bigint, OUT "local_blks_hit" bigint, OUT "local_blks_read" bigint, OUT "local_blks_dirtied" bigint, OUT "local_blks_written" bigint, OUT "temp_blks_read" bigint, OUT "temp_blks_written" bigint, OUT "shared_blk_read_time" double precision, OUT "shared_blk_write_time" double precision, OUT "local_blk_read_time" double precision, OUT "local_blk_write_time" double precision, OUT "temp_blk_read_time" double precision, OUT "temp_blk_write_time" double precision, OUT "wal_records" bigint, OUT "wal_fpi" bigint, OUT "wal_bytes" numeric, OUT "jit_functions" bigint, OUT "jit_generation_time" double precision, OUT "jit_inlining_count" bigint, OUT "jit_inlining_time" double precision, OUT "jit_optimization_count" bigint, OUT "jit_optimization_time" double precision, OUT "jit_emission_count" bigint, OUT "jit_emission_time" double precision, OUT "jit_deform_count" bigint, OUT "jit_deform_time" double precision, OUT "stats_since" timestamp with time zone, OUT "minmax_stats_since" timestamp with time zone) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements"("showtext" boolean, OUT "userid" "oid", OUT "dbid" "oid", OUT "toplevel" boolean, OUT "queryid" bigint, OUT "query" "text", OUT "plans" bigint, OUT "total_plan_time" double precision, OUT "min_plan_time" double precision, OUT "max_plan_time" double precision, OUT "mean_plan_time" double precision, OUT "stddev_plan_time" double precision, OUT "calls" bigint, OUT "total_exec_time" double precision, OUT "min_exec_time" double precision, OUT "max_exec_time" double precision, OUT "mean_exec_time" double precision, OUT "stddev_exec_time" double precision, OUT "rows" bigint, OUT "shared_blks_hit" bigint, OUT "shared_blks_read" bigint, OUT "shared_blks_dirtied" bigint, OUT "shared_blks_written" bigint, OUT "local_blks_hit" bigint, OUT "local_blks_read" bigint, OUT "local_blks_dirtied" bigint, OUT "local_blks_written" bigint, OUT "temp_blks_read" bigint, OUT "temp_blks_written" bigint, OUT "shared_blk_read_time" double precision, OUT "shared_blk_write_time" double precision, OUT "local_blk_read_time" double precision, OUT "local_blk_write_time" double precision, OUT "temp_blk_read_time" double precision, OUT "temp_blk_write_time" double precision, OUT "wal_records" bigint, OUT "wal_fpi" bigint, OUT "wal_bytes" numeric, OUT "jit_functions" bigint, OUT "jit_generation_time" double precision, OUT "jit_inlining_count" bigint, OUT "jit_inlining_time" double precision, OUT "jit_optimization_count" bigint, OUT "jit_optimization_time" double precision, OUT "jit_emission_count" bigint, OUT "jit_emission_time" double precision, OUT "jit_deform_count" bigint, OUT "jit_deform_time" double precision, OUT "stats_since" timestamp with time zone, OUT "minmax_stats_since" timestamp with time zone) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements"("showtext" boolean, OUT "userid" "oid", OUT "dbid" "oid", OUT "toplevel" boolean, OUT "queryid" bigint, OUT "query" "text", OUT "plans" bigint, OUT "total_plan_time" double precision, OUT "min_plan_time" double precision, OUT "max_plan_time" double precision, OUT "mean_plan_time" double precision, OUT "stddev_plan_time" double precision, OUT "calls" bigint, OUT "total_exec_time" double precision, OUT "min_exec_time" double precision, OUT "max_exec_time" double precision, OUT "mean_exec_time" double precision, OUT "stddev_exec_time" double precision, OUT "rows" bigint, OUT "shared_blks_hit" bigint, OUT "shared_blks_read" bigint, OUT "shared_blks_dirtied" bigint, OUT "shared_blks_written" bigint, OUT "local_blks_hit" bigint, OUT "local_blks_read" bigint, OUT "local_blks_dirtied" bigint, OUT "local_blks_written" bigint, OUT "temp_blks_read" bigint, OUT "temp_blks_written" bigint, OUT "shared_blk_read_time" double precision, OUT "shared_blk_write_time" double precision, OUT "local_blk_read_time" double precision, OUT "local_blk_write_time" double precision, OUT "temp_blk_read_time" double precision, OUT "temp_blk_write_time" double precision, OUT "wal_records" bigint, OUT "wal_fpi" bigint, OUT "wal_bytes" numeric, OUT "jit_functions" bigint, OUT "jit_generation_time" double precision, OUT "jit_inlining_count" bigint, OUT "jit_inlining_time" double precision, OUT "jit_optimization_count" bigint, OUT "jit_optimization_time" double precision, OUT "jit_emission_count" bigint, OUT "jit_emission_time" double precision, OUT "jit_deform_count" bigint, OUT "jit_deform_time" double precision, OUT "stats_since" timestamp with time zone, OUT "minmax_stats_since" timestamp with time zone) TO "dashboard_user";


--
-- Name: FUNCTION "pg_stat_statements_info"(OUT "dealloc" bigint, OUT "stats_reset" timestamp with time zone); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pg_stat_statements_info"(OUT "dealloc" bigint, OUT "stats_reset" timestamp with time zone) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements_info"(OUT "dealloc" bigint, OUT "stats_reset" timestamp with time zone) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements_info"(OUT "dealloc" bigint, OUT "stats_reset" timestamp with time zone) TO "dashboard_user";


--
-- Name: FUNCTION "pg_stat_statements_reset"("userid" "oid", "dbid" "oid", "queryid" bigint, "minmax_only" boolean); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pg_stat_statements_reset"("userid" "oid", "dbid" "oid", "queryid" bigint, "minmax_only" boolean) FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements_reset"("userid" "oid", "dbid" "oid", "queryid" bigint, "minmax_only" boolean) TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pg_stat_statements_reset"("userid" "oid", "dbid" "oid", "queryid" bigint, "minmax_only" boolean) TO "dashboard_user";


--
-- Name: FUNCTION "pgp_armor_headers"("text", OUT "key" "text", OUT "value" "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_armor_headers"("text", OUT "key" "text", OUT "value" "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_armor_headers"("text", OUT "key" "text", OUT "value" "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_armor_headers"("text", OUT "key" "text", OUT "value" "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_key_id"("bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_key_id"("bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_key_id"("bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_key_id"("bytea") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt"("bytea", "bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt"("bytea", "bytea", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt"("bytea", "bytea", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt_bytea"("bytea", "bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt_bytea"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_decrypt_bytea"("bytea", "bytea", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_decrypt_bytea"("bytea", "bytea", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_encrypt"("text", "bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_encrypt"("text", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt"("text", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_encrypt_bytea"("bytea", "bytea"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_pub_encrypt_bytea"("bytea", "bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_pub_encrypt_bytea"("bytea", "bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_decrypt"("bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_decrypt"("bytea", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt"("bytea", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_decrypt_bytea"("bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_decrypt_bytea"("bytea", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_decrypt_bytea"("bytea", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_encrypt"("text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_encrypt"("text", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt"("text", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_encrypt_bytea"("bytea", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgp_sym_encrypt_bytea"("bytea", "text", "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text", "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text", "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."pgp_sym_encrypt_bytea"("bytea", "text", "text") TO "dashboard_user";


--
-- Name: FUNCTION "pgrst_ddl_watch"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "extensions"."pgrst_ddl_watch"() TO "postgres" WITH GRANT OPTION;


--
-- Name: FUNCTION "pgrst_drop_watch"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "extensions"."pgrst_drop_watch"() TO "postgres" WITH GRANT OPTION;


--
-- Name: FUNCTION "set_graphql_placeholder"(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "extensions"."set_graphql_placeholder"() TO "postgres" WITH GRANT OPTION;


--
-- Name: FUNCTION "uuid_generate_v1"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_generate_v1"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v1"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v1"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_generate_v1mc"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_generate_v1mc"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v1mc"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v1mc"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_generate_v3"("namespace" "uuid", "name" "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_generate_v3"("namespace" "uuid", "name" "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v3"("namespace" "uuid", "name" "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v3"("namespace" "uuid", "name" "text") TO "dashboard_user";


--
-- Name: FUNCTION "uuid_generate_v4"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_generate_v4"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v4"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v4"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_generate_v5"("namespace" "uuid", "name" "text"); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_generate_v5"("namespace" "uuid", "name" "text") FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v5"("namespace" "uuid", "name" "text") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_generate_v5"("namespace" "uuid", "name" "text") TO "dashboard_user";


--
-- Name: FUNCTION "uuid_nil"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_nil"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_nil"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_nil"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_ns_dns"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_ns_dns"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_ns_dns"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_ns_dns"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_ns_oid"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_ns_oid"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_ns_oid"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_ns_oid"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_ns_url"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_ns_url"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_ns_url"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_ns_url"() TO "dashboard_user";


--
-- Name: FUNCTION "uuid_ns_x500"(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION "extensions"."uuid_ns_x500"() FROM "postgres";
GRANT ALL ON FUNCTION "extensions"."uuid_ns_x500"() TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "extensions"."uuid_ns_x500"() TO "dashboard_user";


--
-- Name: FUNCTION "graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb"); Type: ACL; Schema: graphql_public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "graphql_public"."graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb") TO "postgres";
GRANT ALL ON FUNCTION "graphql_public"."graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "graphql_public"."graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "graphql_public"."graphql"("operationName" "text", "query" "text", "variables" "jsonb", "extensions" "jsonb") TO "service_role";


--
-- Name: FUNCTION "pg_reload_conf"(); Type: ACL; Schema: pg_catalog; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "pg_catalog"."pg_reload_conf"() TO "postgres" WITH GRANT OPTION;


--
-- Name: FUNCTION "get_auth"("p_usename" "text"); Type: ACL; Schema: pgbouncer; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION "pgbouncer"."get_auth"("p_usename" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "pgbouncer"."get_auth"("p_usename" "text") TO "pgbouncer";


--
-- Name: FUNCTION "app_role"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."app_role"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."app_role"() TO "service_role";


--
-- Name: FUNCTION "apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) TO "service_role";


--
-- Name: FUNCTION "booking_append_audit"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."booking_append_audit"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."booking_append_audit"() TO "service_role";


--
-- Name: FUNCTION "cancel_salon_subscription_renewal"("p_salon_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "cash_dist"("money", "money"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "postgres";
GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "anon";
GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "service_role";


--
-- Name: FUNCTION "create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text") TO "service_role";


--
-- Name: FUNCTION "date_dist"("date", "date"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "postgres";
GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "anon";
GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "authenticated";
GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "service_role";


--
-- Name: FUNCTION "deactivate_device_token"("p_token" "text"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."deactivate_device_token"("p_token" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."deactivate_device_token"("p_token" "text") TO "service_role";


--
-- Name: FUNCTION "demote_other_main_images"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."demote_other_main_images"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."demote_other_main_images"() TO "service_role";


--
-- Name: FUNCTION "effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "enqueue_booking_email"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."enqueue_booking_email"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."enqueue_booking_email"() TO "service_role";


--
-- Name: FUNCTION "enqueue_verified_payment_receipt"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."enqueue_verified_payment_receipt"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."enqueue_verified_payment_receipt"() TO "service_role";


--
-- Name: FUNCTION "erase_profile_references"("p_user" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."erase_profile_references"("p_user" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."erase_profile_references"("p_user" "uuid") TO "service_role";


--
-- Name: FUNCTION "float4_dist"(real, real); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "postgres";
GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "anon";
GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "authenticated";
GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "service_role";


--
-- Name: FUNCTION "float8_dist"(double precision, double precision); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "postgres";
GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "anon";
GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "authenticated";
GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "service_role";


--
-- Name: FUNCTION "gbt_bit_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bit_consistent"("internal", bit, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bit_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bit_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bit_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bool_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bpchar_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_bytea_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_consistent"("internal", "money", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_distance"("internal", "money", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_cash_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_consistent"("internal", "date", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_distance"("internal", "date", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_date_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_decompress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_enum_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_consistent"("internal", real, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_distance"("internal", real, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float4_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_distance"("internal", double precision, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_float8_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_inet_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_distance"("internal", smallint, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int2_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_consistent"("internal", integer, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_distance"("internal", integer, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int4_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_distance"("internal", bigint, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_int8_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_consistent"("internal", interval, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_decompress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_distance"("internal", interval, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_intv_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad8_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_macad_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_numeric_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_distance"("internal", "oid", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_oid_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_consistent"("internal", "text", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_text_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_time_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_timetz_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_ts_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_tstz_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_compress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_penalty"("internal", "internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_picksplit"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_uuid_union"("internal", "internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "service_role";


--
-- Name: FUNCTION "gbt_var_decompress"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "service_role";


--
-- Name: FUNCTION "gbt_var_fetch"("internal"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "service_role";


--
-- Name: FUNCTION "get_active_tokens"("p_user_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) TO "service_role";


--
-- Name: FUNCTION "get_salon_by_qr"("p_qr_token" "text"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") TO "service_role";


--
-- Name: FUNCTION "guard_audit_immutable"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_audit_immutable"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_audit_immutable"() TO "service_role";


--
-- Name: FUNCTION "guard_booking_against_closure"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_booking_against_closure"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_booking_against_closure"() TO "service_role";


--
-- Name: FUNCTION "guard_booking_checkout"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_booking_checkout"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_booking_checkout"() TO "service_role";


--
-- Name: FUNCTION "guard_booking_payment_columns"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_booking_payment_columns"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_booking_payment_columns"() TO "service_role";


--
-- Name: FUNCTION "guard_booking_salon_approval"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_booking_salon_approval"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_booking_salon_approval"() TO "service_role";


--
-- Name: FUNCTION "guard_collection_snapshot"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_collection_snapshot"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_collection_snapshot"() TO "service_role";


--
-- Name: FUNCTION "guard_media_reference"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_media_reference"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_media_reference"() TO "service_role";


--
-- Name: FUNCTION "guard_salon_approval"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_salon_approval"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_salon_approval"() TO "service_role";


--
-- Name: FUNCTION "guard_salon_discovery_placement"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_salon_discovery_placement"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_salon_discovery_placement"() TO "service_role";


--
-- Name: FUNCTION "guard_salon_display_priority"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_salon_display_priority"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_salon_display_priority"() TO "service_role";


--
-- Name: FUNCTION "guard_subscription_admin"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."guard_subscription_admin"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."guard_subscription_admin"() TO "service_role";


--
-- Name: FUNCTION "handle_new_user"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."handle_new_user"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."handle_new_user"() TO "service_role";


--
-- Name: FUNCTION "int2_dist"(smallint, smallint); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "postgres";
GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "anon";
GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "service_role";


--
-- Name: FUNCTION "int4_dist"(integer, integer); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "service_role";


--
-- Name: FUNCTION "int8_dist"(bigint, bigint); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "postgres";
GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "service_role";


--
-- Name: FUNCTION "interval_dist"(interval, interval); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "postgres";
GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "anon";
GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "authenticated";
GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "service_role";


--
-- Name: FUNCTION "is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) TO "service_role";


--
-- Name: FUNCTION "is_super_admin"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."is_super_admin"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."is_super_admin"() TO "service_role";


--
-- Name: FUNCTION "oid_dist"("oid", "oid"); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "service_role";


--
-- Name: FUNCTION "owns_salon"("p_salon_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."owns_salon"("p_salon_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."owns_salon"("p_salon_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "payment_append_audit"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."payment_append_audit"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."payment_append_audit"() TO "service_role";


--
-- Name: TABLE "salon_payout_accounts"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_payout_accounts" TO "service_role";


--
-- Name: FUNCTION "payout_account_snapshot"("r" "public"."salon_payout_accounts"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") TO "service_role";


--
-- Name: FUNCTION "recompute_booking_payment_state"("p_booking_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "recompute_salon_trial"("p_salon_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") TO "service_role";


--
-- Name: FUNCTION "salon_booking_eligible"("p_salon" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") TO "service_role";


--
-- Name: FUNCTION "salon_payout_account_masked"("p_salon_id" "uuid"); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) TO "service_role";


--
-- Name: FUNCTION "set_audit_actor"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."set_audit_actor"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."set_audit_actor"() TO "service_role";


--
-- Name: FUNCTION "set_updated_at"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."set_updated_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";


--
-- Name: FUNCTION "stamp_booking_lifecycle"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."stamp_booking_lifecycle"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stamp_booking_lifecycle"() TO "service_role";


--
-- Name: FUNCTION "stamp_checkout_policy"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."stamp_checkout_policy"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stamp_checkout_policy"() TO "service_role";


--
-- Name: FUNCTION "stamp_notification_read_at"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."stamp_notification_read_at"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."stamp_notification_read_at"() TO "service_role";


--
-- Name: FUNCTION "start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone) FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone) TO "service_role";


--
-- Name: FUNCTION "sweep_lapsed_subscriptions"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."sweep_lapsed_subscriptions"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."sweep_lapsed_subscriptions"() TO "service_role";


--
-- Name: FUNCTION "tg_booking_payments_guard"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_booking_payments_guard"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_booking_payments_guard"() TO "service_role";


--
-- Name: FUNCTION "tg_booking_payments_recompute"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_booking_payments_recompute"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_booking_payments_recompute"() TO "service_role";


--
-- Name: FUNCTION "tg_bookings_recompute_trial"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_bookings_recompute_trial"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_bookings_recompute_trial"() TO "service_role";


--
-- Name: FUNCTION "tg_payment_refunds_guard"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_payment_refunds_guard"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_payment_refunds_guard"() TO "service_role";


--
-- Name: FUNCTION "tg_payment_refunds_recompute"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_payment_refunds_recompute"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_payment_refunds_recompute"() TO "service_role";


--
-- Name: FUNCTION "tg_salon_payout_account_history"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_salon_payout_account_history"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_salon_payout_account_history"() TO "service_role";


--
-- Name: FUNCTION "tg_salons_access_row"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_salons_access_row"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_salons_access_row"() TO "service_role";


--
-- Name: FUNCTION "tg_subscription_billing_guard"(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION "public"."tg_subscription_billing_guard"() FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."tg_subscription_billing_guard"() TO "service_role";


--
-- Name: FUNCTION "time_dist"(time without time zone, time without time zone); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "postgres";
GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "service_role";


--
-- Name: FUNCTION "ts_dist"(timestamp without time zone, timestamp without time zone); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "postgres";
GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "service_role";


--
-- Name: FUNCTION "tstz_dist"(timestamp with time zone, timestamp with time zone); Type: ACL; Schema: public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "postgres";
GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "anon";
GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "authenticated";
GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "service_role";


--
-- Name: FUNCTION "apply_rls"("wal" "jsonb", "max_record_bytes" integer); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) TO "anon";
GRANT ALL ON FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."apply_rls"("wal" "jsonb", "max_record_bytes" integer) TO "service_role";


--
-- Name: FUNCTION "authorize"("role_name" "text", "topic_name" "text", "claims" "text", "sub" "text", "headers" "text", "read_extensions" "text"[], "write_extensions" "text"[], OUT "read_allowed" boolean[], OUT "write_allowed" boolean[]); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."authorize"("role_name" "text", "topic_name" "text", "claims" "text", "sub" "text", "headers" "text", "read_extensions" "text"[], "write_extensions" "text"[], OUT "read_allowed" boolean[], OUT "write_allowed" boolean[]) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."authorize"("role_name" "text", "topic_name" "text", "claims" "text", "sub" "text", "headers" "text", "read_extensions" "text"[], "write_extensions" "text"[], OUT "read_allowed" boolean[], OUT "write_allowed" boolean[]) TO "dashboard_user";


--
-- Name: FUNCTION "broadcast_changes"("topic_name" "text", "event_name" "text", "operation" "text", "table_name" "text", "table_schema" "text", "new" "record", "old" "record", "level" "text"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."broadcast_changes"("topic_name" "text", "event_name" "text", "operation" "text", "table_name" "text", "table_schema" "text", "new" "record", "old" "record", "level" "text") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."broadcast_changes"("topic_name" "text", "event_name" "text", "operation" "text", "table_name" "text", "table_schema" "text", "new" "record", "old" "record", "level" "text") TO "dashboard_user";


--
-- Name: FUNCTION "build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) TO "anon";
GRANT ALL ON FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."build_prepared_statement_sql"("prepared_statement_name" "text", "entity" "regclass", "columns" "realtime"."wal_column"[]) TO "service_role";


--
-- Name: FUNCTION "cast"("val" "text", "type_" "regtype"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") TO "anon";
GRANT ALL ON FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."cast"("val" "text", "type_" "regtype") TO "service_role";


--
-- Name: FUNCTION "check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") TO "anon";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text") TO "service_role";


--
-- Name: FUNCTION "check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) TO "anon";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."check_equality_op"("op" "realtime"."equality_op", "type_" "regtype", "val_1" "text", "val_2" "text", "negate" boolean) TO "service_role";


--
-- Name: FUNCTION "is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) TO "anon";
GRANT ALL ON FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."is_visible_through_filters"("columns" "realtime"."wal_column"[], "filters" "realtime"."user_defined_filter"[]) TO "service_role";


--
-- Name: FUNCTION "list_changes"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."list_changes"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."list_changes"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) TO "dashboard_user";


--
-- Name: FUNCTION "list_changes_sync"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."list_changes_sync"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."list_changes_sync"("publication" "name", "slot_name" "name", "max_changes" integer, "max_record_bytes" integer) TO "dashboard_user";


--
-- Name: FUNCTION "quote_wal2json"("entity" "regclass"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."quote_wal2json"("entity" "regclass") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."quote_wal2json"("entity" "regclass") TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."quote_wal2json"("entity" "regclass") TO "anon";
GRANT ALL ON FUNCTION "realtime"."quote_wal2json"("entity" "regclass") TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."quote_wal2json"("entity" "regclass") TO "service_role";


--
-- Name: FUNCTION "send"("payload" "jsonb", "event" "text", "topic" "text", "private" boolean); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."send"("payload" "jsonb", "event" "text", "topic" "text", "private" boolean) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."send"("payload" "jsonb", "event" "text", "topic" "text", "private" boolean) TO "dashboard_user";


--
-- Name: FUNCTION "send_binary"("payload" "bytea", "event" "text", "topic" "text", "private" boolean); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."send_binary"("payload" "bytea", "event" "text", "topic" "text", "private" boolean) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."send_binary"("payload" "bytea", "event" "text", "topic" "text", "private" boolean) TO "dashboard_user";


--
-- Name: FUNCTION "settled_changes"("slot_name" "name", "max_changes" integer, VARIADIC "opts" "text"[]); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."settled_changes"("slot_name" "name", "max_changes" integer, VARIADIC "opts" "text"[]) TO "postgres";
GRANT ALL ON FUNCTION "realtime"."settled_changes"("slot_name" "name", "max_changes" integer, VARIADIC "opts" "text"[]) TO "dashboard_user";


--
-- Name: FUNCTION "subscription_check_filters"(); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."subscription_check_filters"() TO "postgres";
GRANT ALL ON FUNCTION "realtime"."subscription_check_filters"() TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."subscription_check_filters"() TO "anon";
GRANT ALL ON FUNCTION "realtime"."subscription_check_filters"() TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."subscription_check_filters"() TO "service_role";


--
-- Name: FUNCTION "to_regrole"("role_name" "text"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."to_regrole"("role_name" "text") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."to_regrole"("role_name" "text") TO "dashboard_user";
GRANT ALL ON FUNCTION "realtime"."to_regrole"("role_name" "text") TO "anon";
GRANT ALL ON FUNCTION "realtime"."to_regrole"("role_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "realtime"."to_regrole"("role_name" "text") TO "service_role";


--
-- Name: FUNCTION "topic"(); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."topic"() TO "postgres";
GRANT ALL ON FUNCTION "realtime"."topic"() TO "dashboard_user";


--
-- Name: FUNCTION "wal2json_escape_identifier"("name" "text"); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION "realtime"."wal2json_escape_identifier"("name" "text") TO "postgres";
GRANT ALL ON FUNCTION "realtime"."wal2json_escape_identifier"("name" "text") TO "dashboard_user";


--
-- Name: FUNCTION "_crypto_aead_det_decrypt"("message" "bytea", "additional" "bytea", "key_id" bigint, "context" "bytea", "nonce" "bytea"); Type: ACL; Schema: vault; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "vault"."_crypto_aead_det_decrypt"("message" "bytea", "additional" "bytea", "key_id" bigint, "context" "bytea", "nonce" "bytea") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "vault"."_crypto_aead_det_decrypt"("message" "bytea", "additional" "bytea", "key_id" bigint, "context" "bytea", "nonce" "bytea") TO "service_role";


--
-- Name: FUNCTION "create_secret"("new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid"); Type: ACL; Schema: vault; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "vault"."create_secret"("new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "vault"."create_secret"("new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid") TO "service_role";


--
-- Name: FUNCTION "update_secret"("secret_id" "uuid", "new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid"); Type: ACL; Schema: vault; Owner: supabase_admin
--

GRANT ALL ON FUNCTION "vault"."update_secret"("secret_id" "uuid", "new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid") TO "postgres" WITH GRANT OPTION;
GRANT ALL ON FUNCTION "vault"."update_secret"("secret_id" "uuid", "new_secret" "text", "new_name" "text", "new_description" "text", "new_key_id" "uuid") TO "service_role";


--
-- Name: TABLE "audit_log_entries"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."audit_log_entries" TO "dashboard_user";
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."audit_log_entries" TO "postgres";
GRANT SELECT ON TABLE "auth"."audit_log_entries" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "custom_oauth_providers"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."custom_oauth_providers" TO "postgres";
GRANT ALL ON TABLE "auth"."custom_oauth_providers" TO "dashboard_user";


--
-- Name: TABLE "flow_state"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."flow_state" TO "postgres";
GRANT SELECT ON TABLE "auth"."flow_state" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."flow_state" TO "dashboard_user";


--
-- Name: TABLE "identities"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."identities" TO "postgres";
GRANT SELECT ON TABLE "auth"."identities" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."identities" TO "dashboard_user";


--
-- Name: TABLE "instances"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."instances" TO "dashboard_user";
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."instances" TO "postgres";
GRANT SELECT ON TABLE "auth"."instances" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "mfa_amr_claims"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."mfa_amr_claims" TO "postgres";
GRANT SELECT ON TABLE "auth"."mfa_amr_claims" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."mfa_amr_claims" TO "dashboard_user";


--
-- Name: TABLE "mfa_challenges"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."mfa_challenges" TO "postgres";
GRANT SELECT ON TABLE "auth"."mfa_challenges" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."mfa_challenges" TO "dashboard_user";


--
-- Name: TABLE "mfa_factors"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."mfa_factors" TO "postgres";
GRANT SELECT ON TABLE "auth"."mfa_factors" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."mfa_factors" TO "dashboard_user";


--
-- Name: TABLE "mfa_recovery_code_sets"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."mfa_recovery_code_sets" TO "postgres";
GRANT ALL ON TABLE "auth"."mfa_recovery_code_sets" TO "dashboard_user";


--
-- Name: TABLE "mfa_recovery_codes"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."mfa_recovery_codes" TO "postgres";
GRANT ALL ON TABLE "auth"."mfa_recovery_codes" TO "dashboard_user";


--
-- Name: TABLE "oauth_authorizations"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."oauth_authorizations" TO "postgres";
GRANT ALL ON TABLE "auth"."oauth_authorizations" TO "dashboard_user";


--
-- Name: TABLE "oauth_client_states"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."oauth_client_states" TO "postgres";
GRANT ALL ON TABLE "auth"."oauth_client_states" TO "dashboard_user";


--
-- Name: TABLE "oauth_clients"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."oauth_clients" TO "postgres";
GRANT ALL ON TABLE "auth"."oauth_clients" TO "dashboard_user";


--
-- Name: TABLE "oauth_consents"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."oauth_consents" TO "postgres";
GRANT ALL ON TABLE "auth"."oauth_consents" TO "dashboard_user";


--
-- Name: TABLE "one_time_tokens"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."one_time_tokens" TO "postgres";
GRANT SELECT ON TABLE "auth"."one_time_tokens" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."one_time_tokens" TO "dashboard_user";


--
-- Name: TABLE "refresh_tokens"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."refresh_tokens" TO "dashboard_user";
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."refresh_tokens" TO "postgres";
GRANT SELECT ON TABLE "auth"."refresh_tokens" TO "postgres" WITH GRANT OPTION;


--
-- Name: SEQUENCE "refresh_tokens_id_seq"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON SEQUENCE "auth"."refresh_tokens_id_seq" TO "dashboard_user";
GRANT ALL ON SEQUENCE "auth"."refresh_tokens_id_seq" TO "postgres";


--
-- Name: TABLE "saml_providers"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."saml_providers" TO "postgres";
GRANT SELECT ON TABLE "auth"."saml_providers" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."saml_providers" TO "dashboard_user";


--
-- Name: TABLE "saml_relay_states"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."saml_relay_states" TO "postgres";
GRANT SELECT ON TABLE "auth"."saml_relay_states" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."saml_relay_states" TO "dashboard_user";


--
-- Name: TABLE "schema_migrations"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT SELECT ON TABLE "auth"."schema_migrations" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "scim_tokens"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."scim_tokens" TO "postgres";
GRANT ALL ON TABLE "auth"."scim_tokens" TO "dashboard_user";


--
-- Name: TABLE "scim_users"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."scim_users" TO "postgres";
GRANT ALL ON TABLE "auth"."scim_users" TO "dashboard_user";


--
-- Name: TABLE "sessions"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."sessions" TO "postgres";
GRANT SELECT ON TABLE "auth"."sessions" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."sessions" TO "dashboard_user";


--
-- Name: TABLE "sso_domains"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."sso_domains" TO "postgres";
GRANT SELECT ON TABLE "auth"."sso_domains" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."sso_domains" TO "dashboard_user";


--
-- Name: TABLE "sso_providers"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."sso_providers" TO "postgres";
GRANT SELECT ON TABLE "auth"."sso_providers" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "auth"."sso_providers" TO "dashboard_user";


--
-- Name: TABLE "users"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."users" TO "dashboard_user";
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "auth"."users" TO "postgres";
GRANT SELECT ON TABLE "auth"."users" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "webauthn_challenges"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."webauthn_challenges" TO "postgres";
GRANT ALL ON TABLE "auth"."webauthn_challenges" TO "dashboard_user";


--
-- Name: TABLE "webauthn_credentials"; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE "auth"."webauthn_credentials" TO "postgres";
GRANT ALL ON TABLE "auth"."webauthn_credentials" TO "dashboard_user";


--
-- Name: TABLE "pg_stat_statements"; Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON TABLE "extensions"."pg_stat_statements" FROM "postgres";
GRANT ALL ON TABLE "extensions"."pg_stat_statements" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "extensions"."pg_stat_statements" TO "dashboard_user";


--
-- Name: TABLE "pg_stat_statements_info"; Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON TABLE "extensions"."pg_stat_statements_info" FROM "postgres";
GRANT ALL ON TABLE "extensions"."pg_stat_statements_info" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "extensions"."pg_stat_statements_info" TO "dashboard_user";


--
-- Name: TABLE "account_deletion_challenges"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."account_deletion_challenges" TO "service_role";


--
-- Name: TABLE "account_deletion_requests"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."account_deletion_requests" TO "service_role";


--
-- Name: TABLE "alembic_version"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."alembic_version" TO "service_role";


--
-- Name: TABLE "api_rate_limits"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."api_rate_limits" TO "service_role";


--
-- Name: TABLE "blocked_slots"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."blocked_slots" TO "service_role";


--
-- Name: TABLE "booking_action_requests"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."booking_action_requests" TO "service_role";


--
-- Name: TABLE "booking_audit_events"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."booking_audit_events" TO "service_role";


--
-- Name: TABLE "booking_payments"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."booking_payments" TO "service_role";


--
-- Name: TABLE "booking_services"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."booking_services" TO "service_role";


--
-- Name: TABLE "bookings"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."bookings" TO "service_role";


--
-- Name: TABLE "customer_booking_restrictions"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."customer_booking_restrictions" TO "service_role";


--
-- Name: TABLE "device_tokens"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."device_tokens" TO "service_role";


--
-- Name: TABLE "email_events"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."email_events" TO "service_role";


--
-- Name: TABLE "languages"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."languages" TO "service_role";


--
-- Name: TABLE "notification_deliveries"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."notification_deliveries" TO "service_role";


--
-- Name: TABLE "notification_outbox"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."notification_outbox" TO "service_role";


--
-- Name: TABLE "notifications"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."notifications" TO "service_role";


--
-- Name: TABLE "payment_anomalies"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_anomalies" TO "service_role";


--
-- Name: TABLE "payment_idempotency_keys"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_idempotency_keys" TO "service_role";


--
-- Name: TABLE "payment_provider_account_audit"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_provider_account_audit" TO "service_role";


--
-- Name: TABLE "payment_provider_accounts"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_provider_accounts" TO "service_role";


--
-- Name: TABLE "payment_refunds"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_refunds" TO "service_role";


--
-- Name: TABLE "payment_webhook_events"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."payment_webhook_events" TO "service_role";


--
-- Name: TABLE "profiles"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."profiles" TO "service_role";


--
-- Name: TABLE "salon_access"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_access" TO "service_role";


--
-- Name: TABLE "salon_holidays"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_holidays" TO "service_role";


--
-- Name: TABLE "salon_images"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_images" TO "service_role";


--
-- Name: TABLE "salon_payout_account_history"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_payout_account_history" TO "service_role";


--
-- Name: TABLE "salon_reports"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_reports" TO "service_role";


--
-- Name: TABLE "salon_subscriptions"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salon_subscriptions" TO "service_role";


--
-- Name: TABLE "salons"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."salons" TO "service_role";


--
-- Name: TABLE "service_categories"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."service_categories" TO "service_role";


--
-- Name: TABLE "service_subcategories"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."service_subcategories" TO "service_role";


--
-- Name: TABLE "services"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."services" TO "service_role";


--
-- Name: TABLE "staff"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."staff" TO "service_role";


--
-- Name: TABLE "staff_service_languages"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."staff_service_languages" TO "service_role";


--
-- Name: TABLE "staff_services"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."staff_services" TO "service_role";


--
-- Name: TABLE "subscription_billing_records"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."subscription_billing_records" TO "service_role";


--
-- Name: TABLE "subscription_events"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."subscription_events" TO "service_role";


--
-- Name: TABLE "subscription_plans"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."subscription_plans" TO "service_role";


--
-- Name: TABLE "subscription_provider_accounts"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."subscription_provider_accounts" TO "service_role";


--
-- Name: TABLE "support_messages"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."support_messages" TO "service_role";


--
-- Name: TABLE "support_tickets"; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE "public"."support_tickets" TO "service_role";


--
-- Name: TABLE "messages"; Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLE "realtime"."messages" TO "postgres";
GRANT SELECT,INSERT ON TABLE "realtime"."messages" TO "postgres" WITH GRANT OPTION;
GRANT ALL ON TABLE "realtime"."messages" TO "dashboard_user";
GRANT SELECT,INSERT,UPDATE ON TABLE "realtime"."messages" TO "anon";
GRANT SELECT,INSERT,UPDATE ON TABLE "realtime"."messages" TO "authenticated";
GRANT SELECT,INSERT,UPDATE ON TABLE "realtime"."messages" TO "service_role";


--
-- Name: TABLE "schema_migrations"; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE "realtime"."schema_migrations" TO "postgres";
GRANT ALL ON TABLE "realtime"."schema_migrations" TO "dashboard_user";


--
-- Name: TABLE "subscription"; Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON TABLE "realtime"."subscription" TO "postgres";
GRANT ALL ON TABLE "realtime"."subscription" TO "dashboard_user";
GRANT SELECT ON TABLE "realtime"."subscription" TO "anon";
GRANT SELECT ON TABLE "realtime"."subscription" TO "authenticated";
GRANT SELECT ON TABLE "realtime"."subscription" TO "service_role";


--
-- Name: SEQUENCE "subscription_id_seq"; Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON SEQUENCE "realtime"."subscription_id_seq" TO "postgres";
GRANT ALL ON SEQUENCE "realtime"."subscription_id_seq" TO "dashboard_user";
GRANT USAGE ON SEQUENCE "realtime"."subscription_id_seq" TO "anon";
GRANT USAGE ON SEQUENCE "realtime"."subscription_id_seq" TO "authenticated";
GRANT USAGE ON SEQUENCE "realtime"."subscription_id_seq" TO "service_role";


--
-- Name: TABLE "buckets"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

REVOKE ALL ON TABLE "storage"."buckets" FROM "supabase_storage_admin";
GRANT ALL ON TABLE "storage"."buckets" TO "supabase_storage_admin" WITH GRANT OPTION;
GRANT ALL ON TABLE "storage"."buckets" TO "service_role";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."buckets" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."buckets" TO "anon";
GRANT ALL ON TABLE "storage"."buckets" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "buckets_analytics"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE "storage"."buckets_analytics" TO "service_role";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."buckets_analytics" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."buckets_analytics" TO "anon";


--
-- Name: TABLE "buckets_vectors"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT SELECT ON TABLE "storage"."buckets_vectors" TO "service_role";
GRANT SELECT ON TABLE "storage"."buckets_vectors" TO "anon";
GRANT SELECT ON TABLE "storage"."buckets_vectors" TO "authenticated";


--
-- Name: TABLE "objects"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

REVOKE ALL ON TABLE "storage"."objects" FROM "supabase_storage_admin";
GRANT ALL ON TABLE "storage"."objects" TO "supabase_storage_admin" WITH GRANT OPTION;
GRANT ALL ON TABLE "storage"."objects" TO "service_role";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."objects" TO "authenticated";
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "storage"."objects" TO "anon";
GRANT ALL ON TABLE "storage"."objects" TO "postgres" WITH GRANT OPTION;


--
-- Name: TABLE "s3_multipart_uploads"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE "storage"."s3_multipart_uploads" TO "service_role";
GRANT SELECT ON TABLE "storage"."s3_multipart_uploads" TO "authenticated";
GRANT SELECT ON TABLE "storage"."s3_multipart_uploads" TO "anon";


--
-- Name: TABLE "s3_multipart_uploads_parts"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE "storage"."s3_multipart_uploads_parts" TO "service_role";
GRANT SELECT ON TABLE "storage"."s3_multipart_uploads_parts" TO "authenticated";
GRANT SELECT ON TABLE "storage"."s3_multipart_uploads_parts" TO "anon";


--
-- Name: TABLE "vector_indexes"; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT SELECT ON TABLE "storage"."vector_indexes" TO "service_role";
GRANT SELECT ON TABLE "storage"."vector_indexes" TO "anon";
GRANT SELECT ON TABLE "storage"."vector_indexes" TO "authenticated";


--
-- Name: TABLE "secrets"; Type: ACL; Schema: vault; Owner: supabase_admin
--

GRANT SELECT,REFERENCES,DELETE,TRUNCATE ON TABLE "vault"."secrets" TO "postgres" WITH GRANT OPTION;
GRANT SELECT,DELETE ON TABLE "vault"."secrets" TO "service_role";


--
-- Name: TABLE "decrypted_secrets"; Type: ACL; Schema: vault; Owner: supabase_admin
--

GRANT SELECT,REFERENCES,DELETE,TRUNCATE ON TABLE "vault"."decrypted_secrets" TO "postgres" WITH GRANT OPTION;
GRANT SELECT,DELETE ON TABLE "vault"."decrypted_secrets" TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON SEQUENCES TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON FUNCTIONS TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_auth_admin" IN SCHEMA "auth" GRANT ALL ON TABLES TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "extensions" GRANT ALL ON SEQUENCES TO "postgres" WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "extensions" GRANT ALL ON FUNCTIONS TO "postgres" WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "extensions" GRANT ALL ON TABLES TO "postgres" WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON SEQUENCES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON FUNCTIONS TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql" GRANT ALL ON TABLES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON SEQUENCES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON FUNCTIONS TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "graphql_public" GRANT ALL ON TABLES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT ALL ON SEQUENCES TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT ALL ON FUNCTIONS TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT REFERENCES,DELETE,TRIGGER,TRUNCATE,MAINTAIN,UPDATE ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT SELECT,INSERT ON TABLES TO "postgres" WITH GRANT OPTION;
ALTER DEFAULT PRIVILEGES FOR ROLE "supabase_admin" IN SCHEMA "realtime" GRANT ALL ON TABLES TO "dashboard_user";


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON SEQUENCES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON FUNCTIONS TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "storage" GRANT ALL ON TABLES TO "service_role";


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" REVOKE ALL ON FUNCTIONS FROM PUBLIC;


--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "issue_graphql_placeholder" ON "sql_drop"
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION "extensions"."set_graphql_placeholder"();


ALTER EVENT TRIGGER "issue_graphql_placeholder" OWNER TO "supabase_admin";

--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "issue_pg_cron_access" ON "ddl_command_end"
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION "extensions"."grant_pg_cron_access"();


ALTER EVENT TRIGGER "issue_pg_cron_access" OWNER TO "supabase_admin";

--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "issue_pg_graphql_access" ON "ddl_command_end"
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION "extensions"."grant_pg_graphql_access"();


ALTER EVENT TRIGGER "issue_pg_graphql_access" OWNER TO "supabase_admin";

--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "issue_pg_net_access" ON "ddl_command_end"
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION "extensions"."grant_pg_net_access"();


ALTER EVENT TRIGGER "issue_pg_net_access" OWNER TO "supabase_admin";

--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "pgrst_ddl_watch" ON "ddl_command_end"
   EXECUTE FUNCTION "extensions"."pgrst_ddl_watch"();


ALTER EVENT TRIGGER "pgrst_ddl_watch" OWNER TO "supabase_admin";

--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER "pgrst_drop_watch" ON "sql_drop"
   EXECUTE FUNCTION "extensions"."pgrst_drop_watch"();


ALTER EVENT TRIGGER "pgrst_drop_watch" OWNER TO "supabase_admin";

--
-- PostgreSQL database dump complete
--

\unrestrict WDMI3oL7KWgzb7CbfJESqKmw6pnBH9FLLVWR4IZ82l4x3EvAuuTUiqwRMYK8DFK

