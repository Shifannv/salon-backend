-- REJECTED PROPOSAL: NEVER APPLIED. Retains excessive client grants.
-- Superseded by migration-mumbai-schema-restricted-2026-10-15.sql.
SET statement_timeout = 0;

SET lock_timeout = 0;

SET idle_in_transaction_session_timeout = 0;

SET client_encoding = 'UTF8';

SET standard_conforming_strings = on;

SELECT pg_catalog.set_config('search_path', '', false);

SET check_function_bodies = false;

SET xmloption = content;

SET client_min_messages = warning;

SET row_security = off;

COMMENT ON SCHEMA "public" IS 'standard public schema';

CREATE EXTENSION IF NOT EXISTS "btree_gist" WITH SCHEMA "public";

CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";

CREATE TYPE "public"."approval_mode" AS ENUM (
    'auto',
    'manual'
);

ALTER TYPE "public"."approval_mode" OWNER TO "postgres";

CREATE TYPE "public"."booking_source" AS ENUM (
    'app',
    'manual_walkin',
    'qr_walkin'
);

ALTER TYPE "public"."booking_source" OWNER TO "postgres";

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

CREATE TYPE "public"."payment_method" AS ENUM (
    'cash',
    'online'
);

ALTER TYPE "public"."payment_method" OWNER TO "postgres";

CREATE TYPE "public"."payment_status" AS ENUM (
    'unpaid',
    'paid'
);

ALTER TYPE "public"."payment_status" OWNER TO "postgres";

CREATE TYPE "public"."salon_approval_status" AS ENUM (
    'pending',
    'approved',
    'rejected'
);

ALTER TYPE "public"."salon_approval_status" OWNER TO "postgres";

CREATE TYPE "public"."subscription_event_processing_status" AS ENUM (
    'received',
    'processing',
    'processed',
    'failed'
);

ALTER TYPE "public"."subscription_event_processing_status" OWNER TO "postgres";

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

CREATE TYPE "public"."user_role" AS ENUM (
    'super_admin',
    'owner',
    'staff',
    'customer'
);

ALTER TYPE "public"."user_role" OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."app_role"() RETURNS "public"."user_role"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select role from profiles where id = auth.uid();
$$;

ALTER FUNCTION "public"."app_role"() OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) RETURNS "text"
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

CREATE OR REPLACE FUNCTION "public"."booking_append_audit"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") RETURNS "text"
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

CREATE OR REPLACE FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text" DEFAULT NULL::"text", "p_source" "public"."booking_source" DEFAULT 'app'::"public"."booking_source", "p_notes" "text" DEFAULT NULL::"text") RETURNS "uuid"
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

CREATE OR REPLACE FUNCTION "public"."deactivate_device_token"("p_token" "text") RETURNS "void"
    LANGUAGE "sql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  update device_tokens set is_active = false
  where token = p_token and user_id = auth.uid();
$$;

ALTER FUNCTION "public"."deactivate_device_token"("p_token" "text") OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."demote_other_main_images"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") RETURNS integer
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

CREATE OR REPLACE FUNCTION "public"."enqueue_booking_email"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."enqueue_verified_payment_receipt"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."erase_profile_references"("p_user" "uuid") RETURNS integer
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

CREATE OR REPLACE FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") RETURNS TABLE("token" "text", "platform" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select d.token, d.platform
  from device_tokens d
  join profiles p on p.id = d.user_id
  where d.user_id = p_user_id and d.is_active and p.is_active;
$$;

ALTER FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) RETURNS TABLE("slot_start" timestamp with time zone, "slot_end" timestamp with time zone)
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

CREATE OR REPLACE FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") RETURNS TABLE("id" "uuid", "name" "text", "description" "text", "city" "text", "timezone" "text", "approval_mode" "public"."approval_mode")
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

CREATE OR REPLACE FUNCTION "public"."guard_audit_immutable"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_booking_against_closure"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_booking_checkout"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_booking_payment_columns"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_booking_salon_approval"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_collection_snapshot"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_media_reference"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_salon_approval"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_salon_discovery_placement"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_salon_display_priority"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."guard_subscription_admin"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."handle_new_user"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone DEFAULT "now"()) RETURNS boolean
    LANGUAGE "plpgsql" IMMUTABLE
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

CREATE OR REPLACE FUNCTION "public"."is_super_admin"() RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select coalesce((select role = 'super_admin' from profiles where id = auth.uid()), false);
$$;

ALTER FUNCTION "public"."is_super_admin"() OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."owns_salon"("p_salon_id" "uuid") RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  select exists (
    select 1 from salons
    where id = p_salon_id and owner_id = auth.uid() and is_active
  );
$$;

ALTER FUNCTION "public"."owns_salon"("p_salon_id" "uuid") OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."payment_append_audit"() RETURNS "trigger"
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

CREATE TABLE IF NOT EXISTS "public"."salon_payout_accounts" (
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

CREATE OR REPLACE FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") RETURNS "jsonb"
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

CREATE OR REPLACE FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") RETURNS "void"
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

CREATE OR REPLACE FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") RETURNS "void"
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

CREATE OR REPLACE FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text" DEFAULT NULL::"text", "p_device_name" "text" DEFAULT NULL::"text") RETURNS "uuid"
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

CREATE OR REPLACE FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") RETURNS boolean
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

CREATE OR REPLACE FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") RETURNS TABLE("account_holder_name" "text", "upi_id" "text", "bank_name" "text", "bank_account_last4" "text", "ifsc" "text", "created_at" timestamp with time zone, "updated_at" timestamp with time zone)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
          select p.account_holder_name, p.upi_id, p.bank_name,
                 right(p.bank_account_number, 4), p.ifsc, p.created_at, p.updated_at
          from public.salon_payout_accounts p
          where p.salon_id = p_salon_id
        $$;

ALTER FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) RETURNS integer
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

CREATE OR REPLACE FUNCTION "public"."set_audit_actor"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
begin
  new.updated_at := now();
  return new;
end $$;

ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."stamp_booking_lifecycle"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."stamp_checkout_policy"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."stamp_notification_read_at"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone DEFAULT "now"()) RETURNS "void"
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

CREATE OR REPLACE FUNCTION "public"."sweep_lapsed_subscriptions"() RETURNS integer
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

CREATE OR REPLACE FUNCTION "public"."tg_booking_payments_guard"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_booking_payments_recompute"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_bookings_recompute_trial"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
begin
  perform public.recompute_salon_trial(new.salon_id);
  return null;
end $$;

ALTER FUNCTION "public"."tg_bookings_recompute_trial"() OWNER TO "postgres";

CREATE OR REPLACE FUNCTION "public"."tg_payment_refunds_guard"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_payment_refunds_recompute"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_salon_payout_account_history"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_salons_access_row"() RETURNS "trigger"
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

CREATE OR REPLACE FUNCTION "public"."tg_subscription_billing_guard"() RETURNS "trigger"
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

CREATE TABLE IF NOT EXISTS "public"."account_deletion_challenges" (
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

CREATE TABLE IF NOT EXISTS "public"."account_deletion_requests" (
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

CREATE TABLE IF NOT EXISTS "public"."alembic_version" (
    "version_num" character varying(32) NOT NULL
);

ALTER TABLE "public"."alembic_version" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."api_rate_limits" (
    "bucket_hash" "text" NOT NULL,
    "window_start" timestamp with time zone DEFAULT "now"() NOT NULL,
    "attempts" integer DEFAULT 1 NOT NULL
);

ALTER TABLE "public"."api_rate_limits" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."blocked_slots" (
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

CREATE TABLE IF NOT EXISTS "public"."booking_action_requests" (
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

CREATE TABLE IF NOT EXISTS "public"."booking_audit_events" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "booking_id" "uuid" NOT NULL,
    "actor_id" "uuid",
    "event_type" "text" NOT NULL,
    "old_state" "text",
    "new_state" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);

ALTER TABLE "public"."booking_audit_events" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."booking_payments" (
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

CREATE TABLE IF NOT EXISTS "public"."booking_services" (
    "booking_id" "uuid" NOT NULL,
    "service_id" "uuid" NOT NULL,
    "service_name" "text" NOT NULL,
    "duration_minutes" integer NOT NULL,
    "price" numeric(10,2) NOT NULL,
    "created_by" "uuid",
    "updated_by" "uuid"
);

ALTER TABLE "public"."booking_services" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."bookings" (
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

CREATE TABLE IF NOT EXISTS "public"."customer_booking_restrictions" (
    "customer_id" "uuid" NOT NULL,
    "no_show_count" integer DEFAULT 0 NOT NULL,
    "pay_at_salon_blocked_until" timestamp with time zone,
    CONSTRAINT "customer_booking_restrictions_no_show_count_check" CHECK (("no_show_count" >= 0))
);

ALTER TABLE "public"."customer_booking_restrictions" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."device_tokens" (
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

CREATE TABLE IF NOT EXISTS "public"."email_events" (
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

CREATE TABLE IF NOT EXISTS "public"."languages" (
    "code" "text" NOT NULL,
    "name" "text" NOT NULL
);

ALTER TABLE "public"."languages" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."notification_deliveries" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "notification_id" "uuid" NOT NULL,
    "device_token_id" "uuid" NOT NULL,
    "delivered" boolean DEFAULT false NOT NULL,
    "error" "text",
    "attempted_at" timestamp with time zone DEFAULT "now"() NOT NULL
);

ALTER TABLE "public"."notification_deliveries" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."notification_outbox" (
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

CREATE TABLE IF NOT EXISTS "public"."notifications" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_anomalies" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_idempotency_keys" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_provider_account_audit" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_provider_accounts" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_refunds" (
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

CREATE TABLE IF NOT EXISTS "public"."payment_webhook_events" (
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

CREATE TABLE IF NOT EXISTS "public"."profiles" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_access" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_holidays" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_images" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_payout_account_history" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_reports" (
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

CREATE TABLE IF NOT EXISTS "public"."salon_subscriptions" (
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

CREATE TABLE IF NOT EXISTS "public"."salons" (
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

CREATE TABLE IF NOT EXISTS "public"."service_categories" (
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

CREATE TABLE IF NOT EXISTS "public"."service_subcategories" (
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

CREATE TABLE IF NOT EXISTS "public"."services" (
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

CREATE TABLE IF NOT EXISTS "public"."staff" (
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

CREATE TABLE IF NOT EXISTS "public"."staff_service_languages" (
    "staff_service_id" "uuid" NOT NULL,
    "language_code" "text" NOT NULL
);

ALTER TABLE "public"."staff_service_languages" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."staff_services" (
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

CREATE TABLE IF NOT EXISTS "public"."subscription_billing_records" (
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

CREATE TABLE IF NOT EXISTS "public"."subscription_events" (
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

CREATE TABLE IF NOT EXISTS "public"."subscription_plans" (
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
    CONSTRAINT "ck_subscription_plans_interval" CHECK ((("billing_interval")::"text" = ANY ((ARRAY['monthly'::character varying, 'quarterly'::character varying, 'semiannual'::character varying, 'yearly'::character varying])::"text"[]))),
    CONSTRAINT "ck_subscription_plans_price" CHECK (("price_amount" >= (0)::numeric)),
    CONSTRAINT "subscription_plans_ranking_weight_range" CHECK ((("ranking_weight" >= 0) AND ("ranking_weight" <= 100000)))
);

ALTER TABLE "public"."subscription_plans" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."subscription_provider_accounts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "salon_id" "uuid" NOT NULL,
    "provider_name" character varying(60),
    "provider_customer_reference" character varying(400),
    "provider_subscription_reference" character varying(400),
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);

ALTER TABLE "public"."subscription_provider_accounts" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."support_messages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ticket_id" "uuid" NOT NULL,
    "author_id" "uuid",
    "body" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "support_messages_body_check" CHECK ((("char_length"("body") >= 1) AND ("char_length"("body") <= 5000)))
);

ALTER TABLE "public"."support_messages" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "public"."support_tickets" (
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

ALTER TABLE ONLY "public"."account_deletion_challenges"
    ADD CONSTRAINT "account_deletion_challenges_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."account_deletion_requests"
    ADD CONSTRAINT "account_deletion_requests_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."alembic_version"
    ADD CONSTRAINT "alembic_version_pkc" PRIMARY KEY ("version_num");

ALTER TABLE ONLY "public"."api_rate_limits"
    ADD CONSTRAINT "api_rate_limits_pkey" PRIMARY KEY ("bucket_hash");

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_pkey" PRIMARY KEY ("booking_id", "service_id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_no_overlap" EXCLUDE USING "gist" ("staff_id" WITH =, "tstzrange"("start_datetime", "end_datetime") WITH &&) WHERE (("status" = ANY (ARRAY['pending'::"public"."booking_status", 'confirmed'::"public"."booking_status", 'checked_in'::"public"."booking_status"])));

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."customer_booking_restrictions"
    ADD CONSTRAINT "customer_booking_restrictions_pkey" PRIMARY KEY ("customer_id");

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_token_key" UNIQUE ("token");

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_event_key_key" UNIQUE ("event_key");

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."languages"
    ADD CONSTRAINT "languages_pkey" PRIMARY KEY ("code");

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_notification_id_device_token_id_key" UNIQUE ("notification_id", "device_token_id");

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_notification_id_key" UNIQUE ("notification_id");

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_idempotency_keys"
    ADD CONSTRAINT "payment_idempotency_keys_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."payment_webhook_events"
    ADD CONSTRAINT "payment_webhook_events_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_email_key" UNIQUE ("email");

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salon_access"
    ADD CONSTRAINT "salon_access_pkey" PRIMARY KEY ("salon_id");

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_pkey" PRIMARY KEY ("salon_id");

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_qr_token_key" UNIQUE ("qr_token");

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_slug_key" UNIQUE ("slug");

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_category_id_slug_key" UNIQUE ("category_id", "slug");

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_pkey" PRIMARY KEY ("staff_service_id", "language_code");

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_staff_id_service_id_key" UNIQUE ("staff_id", "service_id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."subscription_events"
    ADD CONSTRAINT "subscription_events_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_code_key" UNIQUE ("code");

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_salon_id_provider_name_key" UNIQUE ("salon_id", "provider_name");

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_intent_reference" UNIQUE ("intent_reference");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_provider_order" UNIQUE ("provider", "order_ref");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "uq_booking_payments_provider_payment" UNIQUE ("provider", "payment_ref");

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "uq_payment_anomalies_ref" UNIQUE ("kind", "provider", "provider_ref");

ALTER TABLE ONLY "public"."payment_idempotency_keys"
    ADD CONSTRAINT "uq_payment_idempotency" UNIQUE ("actor_id", "scope", "idempotency_key");

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "uq_payment_provider_accounts_salon" UNIQUE ("salon_id", "provider");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "uq_payment_refunds_idempotency" UNIQUE ("payment_id", "idempotency_key");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "uq_payment_refunds_provider_ref" UNIQUE ("provider", "refund_ref");

ALTER TABLE ONLY "public"."payment_webhook_events"
    ADD CONSTRAINT "uq_payment_webhook_events_provider_ref" UNIQUE ("provider_name", "provider_event_reference");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "uq_subscription_billing_receipt" UNIQUE ("receipt");

CREATE INDEX "idx_account_deletion_requests_due" ON "public"."account_deletion_requests" USING "btree" ("status", "next_attempt_at") WHERE ("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'failed'::"text"]));

CREATE INDEX "idx_account_deletion_requests_open_age" ON "public"."account_deletion_requests" USING "btree" ("requested_at") WHERE ("status" <> 'completed'::"text");

CREATE INDEX "idx_account_deletion_requests_requested" ON "public"."account_deletion_requests" USING "btree" ("requested_at" DESC);

CREATE INDEX "idx_blocked_salon_time" ON "public"."blocked_slots" USING "btree" ("salon_id", "start_datetime", "end_datetime");

CREATE INDEX "idx_blocked_staff_time" ON "public"."blocked_slots" USING "btree" ("staff_id", "start_datetime", "end_datetime");

CREATE INDEX "idx_booking_action_requests_booking" ON "public"."booking_action_requests" USING "btree" ("booking_id", "kind", "created_at" DESC);

CREATE INDEX "idx_booking_action_requests_pending" ON "public"."booking_action_requests" USING "btree" ("status", "created_at");

CREATE INDEX "idx_booking_audit_history" ON "public"."booking_audit_events" USING "btree" ("booking_id", "created_at");

CREATE INDEX "idx_booking_pay_at_salon_day" ON "public"."bookings" USING "btree" ("customer_id", "booking_calendar_date") WHERE (("payment_preference" = 'pay_at_salon'::"text") AND ("status" = ANY (ARRAY['pending'::"public"."booking_status", 'confirmed'::"public"."booking_status", 'checked_in'::"public"."booking_status"])));

CREATE INDEX "idx_booking_payments_booking" ON "public"."booking_payments" USING "btree" ("booking_id");

CREATE INDEX "idx_booking_payments_payer" ON "public"."booking_payments" USING "btree" ("payer_id");

CREATE INDEX "idx_booking_payments_reconcile" ON "public"."booking_payments" USING "btree" ("updated_at") WHERE (("channel" = 'gateway'::"text") AND ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"])));

CREATE INDEX "idx_booking_payments_salon" ON "public"."booking_payments" USING "btree" ("salon_id", "created_at" DESC);

CREATE INDEX "idx_booking_services_service_id" ON "public"."booking_services" USING "btree" ("service_id");

CREATE INDEX "idx_bookings_approved_by" ON "public"."bookings" USING "btree" ("approved_by");

CREATE INDEX "idx_bookings_completed_by" ON "public"."bookings" USING "btree" ("completed_by");

CREATE INDEX "idx_bookings_customer" ON "public"."bookings" USING "btree" ("customer_id");

CREATE INDEX "idx_bookings_pending" ON "public"."bookings" USING "btree" ("salon_id") WHERE ("status" = 'pending'::"public"."booking_status");

CREATE INDEX "idx_bookings_salon_day" ON "public"."bookings" USING "btree" ("salon_id", "start_datetime");

CREATE INDEX "idx_bookings_staff_day" ON "public"."bookings" USING "btree" ("staff_id", "start_datetime");

CREATE INDEX "idx_bookings_status_time" ON "public"."bookings" USING "btree" ("salon_id", "status", "start_datetime");

CREATE INDEX "idx_bookings_trial_count" ON "public"."bookings" USING "btree" ("salon_id", "created_at");

CREATE INDEX "idx_deliveries_notification" ON "public"."notification_deliveries" USING "btree" ("notification_id");

CREATE INDEX "idx_device_tokens_active" ON "public"."device_tokens" USING "btree" ("user_id") WHERE "is_active";

CREATE INDEX "idx_email_pending" ON "public"."email_events" USING "btree" ("next_attempt_at") WHERE ("status" = ANY (ARRAY['pending'::"text", 'processing'::"text"]));

CREATE INDEX "idx_email_user_status" ON "public"."email_events" USING "btree" ("user_id", "created_at" DESC);

CREATE INDEX "idx_notification_deliveries_device_token_id" ON "public"."notification_deliveries" USING "btree" ("device_token_id");

CREATE INDEX "idx_notification_outbox_pending" ON "public"."notification_outbox" USING "btree" ("next_attempt_at", "created_at") WHERE ("status" = 'pending'::"text");

CREATE INDEX "idx_notification_outbox_user_id" ON "public"."notification_outbox" USING "btree" ("user_id");

CREATE INDEX "idx_notifications_booking_id" ON "public"."notifications" USING "btree" ("booking_id");

CREATE INDEX "idx_notifications_user" ON "public"."notifications" USING "btree" ("user_id", "read", "created_at" DESC);

CREATE INDEX "idx_payment_account_audit_salon" ON "public"."payment_provider_account_audit" USING "btree" ("salon_id", "created_at" DESC);

CREATE INDEX "idx_payment_anomalies_open" ON "public"."payment_anomalies" USING "btree" ("created_at") WHERE ("resolved_at" IS NULL);

CREATE INDEX "idx_payment_idempotency_expiry" ON "public"."payment_idempotency_keys" USING "btree" ("expires_at");

CREATE INDEX "idx_payment_refunds_booking" ON "public"."payment_refunds" USING "btree" ("booking_id");

CREATE INDEX "idx_payment_refunds_open" ON "public"."payment_refunds" USING "btree" ("updated_at") WHERE ("status" = 'created'::"text");

CREATE INDEX "idx_payment_webhook_events_due" ON "public"."payment_webhook_events" USING "btree" ("next_attempt_at") WHERE ("processing_status" = ANY (ARRAY['received'::"text", 'processing'::"text", 'failed'::"text"]));

CREATE INDEX "idx_profiles_created_by" ON "public"."profiles" USING "btree" ("created_by");

CREATE INDEX "idx_profiles_phone" ON "public"."profiles" USING "btree" ("phone");

CREATE INDEX "idx_profiles_role" ON "public"."profiles" USING "btree" ("role");

CREATE INDEX "idx_salon_access_eligibility" ON "public"."salon_access" USING "btree" ("trial_ends_at") WHERE ("trial_limit_reached_at" IS NULL);

CREATE INDEX "idx_salon_holidays" ON "public"."salon_holidays" USING "btree" ("salon_id", "holiday_date");

CREATE INDEX "idx_salon_images_active" ON "public"."salon_images" USING "btree" ("salon_id", "is_active", "sort_order");

CREATE INDEX "idx_salon_images_salon" ON "public"."salon_images" USING "btree" ("salon_id", "sort_order");

CREATE INDEX "idx_salon_payout_history_salon" ON "public"."salon_payout_account_history" USING "btree" ("salon_id", "changed_at" DESC);

CREATE INDEX "idx_salon_subscriptions_plan_id" ON "public"."salon_subscriptions" USING "btree" ("plan_id");

CREATE INDEX "idx_salon_subscriptions_salon_id" ON "public"."salon_subscriptions" USING "btree" ("salon_id");

CREATE INDEX "idx_salon_subscriptions_status" ON "public"."salon_subscriptions" USING "btree" ("status");

CREATE INDEX "idx_salons_active" ON "public"."salons" USING "btree" ("is_active", "profile_completed");

CREATE INDEX "idx_salons_approval_status" ON "public"."salons" USING "btree" ("approval_status");

CREATE INDEX "idx_salons_city" ON "public"."salons" USING "btree" ("city");

CREATE INDEX "idx_salons_owner" ON "public"."salons" USING "btree" ("owner_id");

CREATE INDEX "idx_salons_updated_by" ON "public"."salons" USING "btree" ("updated_by");

CREATE INDEX "idx_services_salon" ON "public"."services" USING "btree" ("salon_id", "is_active");

CREATE INDEX "idx_services_subcategory" ON "public"."services" USING "btree" ("subcategory_id") WHERE "is_active";

CREATE INDEX "idx_services_updated_by" ON "public"."services" USING "btree" ("updated_by");

CREATE INDEX "idx_ssl_language" ON "public"."staff_service_languages" USING "btree" ("language_code");

CREATE INDEX "idx_staff_profile_id" ON "public"."staff" USING "btree" ("profile_id");

CREATE INDEX "idx_staff_salon" ON "public"."staff" USING "btree" ("salon_id", "is_active");

CREATE INDEX "idx_staff_services_service" ON "public"."staff_services" USING "btree" ("service_id") WHERE "is_active";

CREATE INDEX "idx_staff_services_staff" ON "public"."staff_services" USING "btree" ("staff_id") WHERE "is_active";

CREATE INDEX "idx_subcategories_category" ON "public"."service_subcategories" USING "btree" ("category_id", "is_active");

CREATE INDEX "idx_subscription_billing_open" ON "public"."subscription_billing_records" USING "btree" ("updated_at") WHERE ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"]));

CREATE INDEX "idx_subscription_billing_salon" ON "public"."subscription_billing_records" USING "btree" ("salon_id", "created_at" DESC);

CREATE INDEX "idx_subscription_billing_unapplied" ON "public"."subscription_billing_records" USING "btree" ("updated_at") WHERE (("status" = ANY (ARRAY['paid'::"text", 'partially_refunded'::"text"])) AND ("applied_at" IS NULL));

CREATE INDEX "idx_subscription_booking_eligibility" ON "public"."salon_subscriptions" USING "btree" ("salon_id", "current_period_end") WHERE ("status" = ANY (ARRAY['active'::"public"."subscription_status", 'cancelled'::"public"."subscription_status"]));

CREATE INDEX "idx_subscription_events_subscription" ON "public"."subscription_events" USING "btree" ("salon_subscription_id");

CREATE INDEX "idx_support_customer_history" ON "public"."support_tickets" USING "btree" ("customer_id", "created_at" DESC);

CREATE INDEX "idx_support_message_thread" ON "public"."support_messages" USING "btree" ("ticket_id", "created_at");

CREATE INDEX "salon_reports_reporter_idx" ON "public"."salon_reports" USING "btree" ("reporter_id", "created_at");

CREATE INDEX "salon_reports_salon_idx" ON "public"."salon_reports" USING "btree" ("salon_id", "created_at");

CREATE UNIQUE INDEX "uq_account_deletion_challenge_live" ON "public"."account_deletion_challenges" USING "btree" ("user_id") WHERE ("status" = ANY (ARRAY['sent'::"text", 'verified'::"text"]));

CREATE UNIQUE INDEX "uq_account_deletion_request_open" ON "public"."account_deletion_requests" USING "btree" ("user_id") WHERE ("status" <> 'completed'::"text");

CREATE UNIQUE INDEX "uq_booking_action_requests_pending" ON "public"."booking_action_requests" USING "btree" ("booking_id", "kind") WHERE ("status" = 'pending'::"text");

CREATE UNIQUE INDEX "uq_booking_payments_one_open_intent" ON "public"."booking_payments" USING "btree" ("booking_id") WHERE (("channel" = 'gateway'::"text") AND ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"])));

CREATE UNIQUE INDEX "uq_salon_holidays_active_date" ON "public"."salon_holidays" USING "btree" ("salon_id", "holiday_date") WHERE "is_active";

CREATE UNIQUE INDEX "uq_salon_main_image" ON "public"."salon_images" USING "btree" ("salon_id") WHERE "is_main";

CREATE UNIQUE INDEX "uq_salon_subscriptions_active_per_salon" ON "public"."salon_subscriptions" USING "btree" ("salon_id") WHERE ("status" <> ALL (ARRAY['expired'::"public"."subscription_status", 'cancelled'::"public"."subscription_status", 'suspended'::"public"."subscription_status"]));

CREATE UNIQUE INDEX "uq_subscription_billing_open_per_salon" ON "public"."subscription_billing_records" USING "btree" ("salon_id") WHERE ("status" = ANY (ARRAY['created'::"text", 'authorized'::"text"]));

CREATE UNIQUE INDEX "uq_subscription_billing_order" ON "public"."subscription_billing_records" USING "btree" ("provider", "provider_order_ref") WHERE ("provider_order_ref" IS NOT NULL);

CREATE UNIQUE INDEX "uq_subscription_billing_payment" ON "public"."subscription_billing_records" USING "btree" ("provider", "provider_payment_ref") WHERE ("provider_payment_ref" IS NOT NULL);

CREATE UNIQUE INDEX "uq_subscription_events_provider_ref" ON "public"."subscription_events" USING "btree" ("provider_name", "provider_event_reference") WHERE (("provider_name" IS NOT NULL) AND ("provider_event_reference" IS NOT NULL));

CREATE OR REPLACE TRIGGER "booking_audit_append" AFTER INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."booking_append_audit"();

CREATE OR REPLACE TRIGGER "booking_audit_immutable" BEFORE DELETE OR UPDATE ON "public"."booking_audit_events" FOR EACH ROW EXECUTE FUNCTION "public"."guard_audit_immutable"();

CREATE OR REPLACE TRIGGER "booking_checkout_guard" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_checkout"();

CREATE OR REPLACE TRIGGER "booking_email_outbox" AFTER INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."enqueue_booking_email"();

CREATE OR REPLACE TRIGGER "bookings_guard_salon_approval" BEFORE INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_salon_approval"();

CREATE OR REPLACE TRIGGER "checkout_policy_stamp" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_checkout_policy"();

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('avatar_url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('qr_image_url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('image_url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('image_url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('photo_url');

CREATE OR REPLACE TRIGGER "media_reference_guard" BEFORE INSERT OR UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."guard_media_reference"('photo_url');

CREATE OR REPLACE TRIGGER "payment_audit_append" AFTER INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."payment_append_audit"();

CREATE OR REPLACE TRIGGER "payment_collection_snapshot" BEFORE INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."guard_collection_snapshot"();

CREATE OR REPLACE TRIGGER "salon_subscriptions_guard_admin" BEFORE INSERT OR DELETE OR UPDATE ON "public"."salon_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."guard_subscription_admin"();

CREATE OR REPLACE TRIGGER "salons_guard_approval" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_approval"();

CREATE OR REPLACE TRIGGER "salons_guard_discovery_placement" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_discovery_placement"();

CREATE OR REPLACE TRIGGER "salons_guard_display_priority" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."guard_salon_display_priority"();

CREATE OR REPLACE TRIGGER "subscription_billing_guard" BEFORE UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."tg_subscription_billing_guard"();

CREATE OR REPLACE TRIGGER "subscription_plans_guard_admin" BEFORE INSERT OR DELETE OR UPDATE ON "public"."subscription_plans" FOR EACH ROW EXECUTE FUNCTION "public"."guard_subscription_admin"();

CREATE OR REPLACE TRIGGER "t_blocked_audit" BEFORE INSERT OR UPDATE ON "public"."blocked_slots" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_blocked_updated" BEFORE UPDATE ON "public"."blocked_slots" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_booking_action_requests_audit" BEFORE INSERT OR UPDATE ON "public"."booking_action_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_booking_action_requests_updated" BEFORE UPDATE ON "public"."booking_action_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_booking_payments_audit" BEFORE INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_booking_payments_guard" BEFORE UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."tg_booking_payments_guard"();

CREATE OR REPLACE TRIGGER "t_booking_payments_recompute" AFTER INSERT OR DELETE OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."tg_booking_payments_recompute"();

CREATE OR REPLACE TRIGGER "t_booking_payments_updated" BEFORE UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_booking_services_audit" BEFORE INSERT OR UPDATE ON "public"."booking_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_bookings_audit" BEFORE INSERT OR UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_bookings_closure_guard" BEFORE INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_against_closure"();

CREATE OR REPLACE TRIGGER "t_bookings_lifecycle" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_booking_lifecycle"();

CREATE OR REPLACE TRIGGER "t_bookings_payment_guard" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."guard_booking_payment_columns"();

CREATE OR REPLACE TRIGGER "t_bookings_trial_insert" AFTER INSERT ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."tg_bookings_recompute_trial"();

CREATE OR REPLACE TRIGGER "t_bookings_updated" BEFORE UPDATE ON "public"."bookings" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_categories_audit" BEFORE INSERT OR UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_categories_updated" BEFORE UPDATE ON "public"."service_categories" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_notification_outbox_updated" BEFORE UPDATE ON "public"."notification_outbox" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_payment_provider_accounts_audit" BEFORE INSERT OR UPDATE ON "public"."payment_provider_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_payment_provider_accounts_updated" BEFORE UPDATE ON "public"."payment_provider_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_payment_refunds_audit" BEFORE INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_payment_refunds_guard" BEFORE INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."tg_payment_refunds_guard"();

CREATE OR REPLACE TRIGGER "t_payment_refunds_recompute" AFTER INSERT OR UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."tg_payment_refunds_recompute"();

CREATE OR REPLACE TRIGGER "t_payment_refunds_updated" BEFORE UPDATE ON "public"."payment_refunds" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_profiles_audit" BEFORE INSERT OR UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_profiles_updated" BEFORE UPDATE ON "public"."profiles" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_salon_holidays_audit" BEFORE INSERT OR UPDATE ON "public"."salon_holidays" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_salon_holidays_updated" BEFORE UPDATE ON "public"."salon_holidays" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_salon_images_audit" BEFORE INSERT OR UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_salon_images_updated" BEFORE UPDATE ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_salon_main_image" BEFORE INSERT OR UPDATE OF "is_main" ON "public"."salon_images" FOR EACH ROW EXECUTE FUNCTION "public"."demote_other_main_images"();

CREATE OR REPLACE TRIGGER "t_salon_payout_accounts_audit" BEFORE INSERT OR UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_salon_payout_accounts_history" AFTER INSERT OR UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."tg_salon_payout_account_history"();

CREATE OR REPLACE TRIGGER "t_salon_payout_accounts_updated" BEFORE UPDATE ON "public"."salon_payout_accounts" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_salon_subscriptions_audit" BEFORE INSERT OR UPDATE ON "public"."salon_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_salons_access_approved" AFTER UPDATE OF "approval_status" ON "public"."salons" FOR EACH ROW WHEN ((("new"."approval_status" = 'approved'::"public"."salon_approval_status") AND ("old"."approval_status" IS DISTINCT FROM "new"."approval_status"))) EXECUTE FUNCTION "public"."tg_salons_access_row"();

CREATE OR REPLACE TRIGGER "t_salons_access_insert" AFTER INSERT ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."tg_salons_access_row"();

CREATE OR REPLACE TRIGGER "t_salons_audit" BEFORE INSERT OR UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_salons_updated" BEFORE UPDATE ON "public"."salons" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_services_audit" BEFORE INSERT OR UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_services_updated" BEFORE UPDATE ON "public"."services" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_staff_audit" BEFORE INSERT OR UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_staff_services_audit" BEFORE INSERT OR UPDATE ON "public"."staff_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_staff_services_updated" BEFORE UPDATE ON "public"."staff_services" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_staff_updated" BEFORE UPDATE ON "public"."staff" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_subcategories_audit" BEFORE INSERT OR UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_subcategories_updated" BEFORE UPDATE ON "public"."service_subcategories" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_subscription_billing_records_audit" BEFORE INSERT OR UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "t_subscription_billing_records_updated" BEFORE UPDATE ON "public"."subscription_billing_records" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();

CREATE OR REPLACE TRIGGER "t_subscription_plans_audit" BEFORE INSERT OR UPDATE ON "public"."subscription_plans" FOR EACH ROW EXECUTE FUNCTION "public"."set_audit_actor"();

CREATE OR REPLACE TRIGGER "trg_notification_read_at" BEFORE UPDATE ON "public"."notifications" FOR EACH ROW EXECUTE FUNCTION "public"."stamp_notification_read_at"();

CREATE OR REPLACE TRIGGER "verified_payment_email" AFTER INSERT OR UPDATE ON "public"."booking_payments" FOR EACH ROW EXECUTE FUNCTION "public"."enqueue_verified_payment_receipt"();

ALTER TABLE ONLY "public"."account_deletion_challenges"
    ADD CONSTRAINT "account_deletion_challenges_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."blocked_slots"
    ADD CONSTRAINT "blocked_slots_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_requested_by_fkey" FOREIGN KEY ("requested_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_action_requests"
    ADD CONSTRAINT "booking_action_requests_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "public"."profiles"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "public"."booking_audit_events"
    ADD CONSTRAINT "booking_audit_events_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_payer_id_fkey" FOREIGN KEY ("payer_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_recorded_by_fkey" FOREIGN KEY ("recorded_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."booking_payments"
    ADD CONSTRAINT "booking_payments_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_service_id_fkey" FOREIGN KEY ("service_id") REFERENCES "public"."services"("id");

ALTER TABLE ONLY "public"."booking_services"
    ADD CONSTRAINT "booking_services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_approved_by_fkey" FOREIGN KEY ("approved_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_cancelled_by_fkey" FOREIGN KEY ("cancelled_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_completed_by_fkey" FOREIGN KEY ("completed_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_payment_recorded_by_fkey" FOREIGN KEY ("payment_recorded_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_rejected_by_fkey" FOREIGN KEY ("rejected_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id");

ALTER TABLE ONLY "public"."bookings"
    ADD CONSTRAINT "bookings_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."customer_booking_restrictions"
    ADD CONSTRAINT "customer_booking_restrictions_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."device_tokens"
    ADD CONSTRAINT "device_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."email_events"
    ADD CONSTRAINT "email_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_device_token_id_fkey" FOREIGN KEY ("device_token_id") REFERENCES "public"."device_tokens"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notification_deliveries"
    ADD CONSTRAINT "notification_deliveries_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "public"."notifications"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_notification_id_fkey" FOREIGN KEY ("notification_id") REFERENCES "public"."notifications"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notification_outbox"
    ADD CONSTRAINT "notification_outbox_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "public"."booking_payments"("id");

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_anomalies"
    ADD CONSTRAINT "payment_anomalies_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_provider_account_audit"
    ADD CONSTRAINT "payment_provider_account_audit_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."payment_provider_accounts"
    ADD CONSTRAINT "payment_provider_accounts_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_booking_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "public"."bookings"("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_payment_id_fkey" FOREIGN KEY ("payment_id") REFERENCES "public"."booking_payments"("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_requested_by_fkey" FOREIGN KEY ("requested_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."payment_refunds"
    ADD CONSTRAINT "payment_refunds_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_access"
    ADD CONSTRAINT "salon_access_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."salon_holidays"
    ADD CONSTRAINT "salon_holidays_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."salon_images"
    ADD CONSTRAINT "salon_images_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_changed_by_fkey" FOREIGN KEY ("changed_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_payout_account_history"
    ADD CONSTRAINT "salon_payout_account_history_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."salon_payout_accounts"
    ADD CONSTRAINT "salon_payout_accounts_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_reporter_id_fkey" FOREIGN KEY ("reporter_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_reports"
    ADD CONSTRAINT "salon_reports_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "public"."subscription_plans"("id");

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."salon_subscriptions"
    ADD CONSTRAINT "salon_subscriptions_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_approved_by_fkey" FOREIGN KEY ("approved_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."salons"
    ADD CONSTRAINT "salons_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."service_categories"
    ADD CONSTRAINT "service_categories_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "public"."service_categories"("id");

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."service_subcategories"
    ADD CONSTRAINT "service_subcategories_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_subcategory_id_fkey" FOREIGN KEY ("subcategory_id") REFERENCES "public"."service_subcategories"("id");

ALTER TABLE ONLY "public"."services"
    ADD CONSTRAINT "services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_profile_id_fkey" FOREIGN KEY ("profile_id") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_language_code_fkey" FOREIGN KEY ("language_code") REFERENCES "public"."languages"("code");

ALTER TABLE ONLY "public"."staff_service_languages"
    ADD CONSTRAINT "staff_service_languages_staff_service_id_fkey" FOREIGN KEY ("staff_service_id") REFERENCES "public"."staff_services"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_service_id_fkey" FOREIGN KEY ("service_id") REFERENCES "public"."services"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_staff_id_fkey" FOREIGN KEY ("staff_id") REFERENCES "public"."staff"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."staff_services"
    ADD CONSTRAINT "staff_services_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."staff"
    ADD CONSTRAINT "staff_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "public"."subscription_plans"("id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "public"."salon_subscriptions"("id");

ALTER TABLE ONLY "public"."subscription_billing_records"
    ADD CONSTRAINT "subscription_billing_records_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."subscription_events"
    ADD CONSTRAINT "subscription_events_salon_subscription_id_fkey" FOREIGN KEY ("salon_subscription_id") REFERENCES "public"."salon_subscriptions"("id");

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_updated_by_fkey" FOREIGN KEY ("updated_by") REFERENCES "public"."profiles"("id");

ALTER TABLE ONLY "public"."subscription_provider_accounts"
    ADD CONSTRAINT "subscription_provider_accounts_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "public"."profiles"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "public"."support_messages"
    ADD CONSTRAINT "support_messages_ticket_id_fkey" FOREIGN KEY ("ticket_id") REFERENCES "public"."support_tickets"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_customer_id_fkey" FOREIGN KEY ("customer_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "public"."support_tickets"
    ADD CONSTRAINT "support_tickets_salon_id_fkey" FOREIGN KEY ("salon_id") REFERENCES "public"."salons"("id");

ALTER TABLE "public"."account_deletion_challenges" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."account_deletion_requests" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."alembic_version" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."api_rate_limits" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "blocked_owner_write" ON "public"."blocked_slots" USING (((("staff_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "blocked_slots"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) OR (("salon_id" IS NOT NULL) AND "public"."owns_salon"("salon_id")))) WITH CHECK (((("staff_id" IS NOT NULL) AND (EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "blocked_slots"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) OR (("salon_id" IS NOT NULL) AND "public"."owns_salon"("salon_id"))));

CREATE POLICY "blocked_read" ON "public"."blocked_slots" FOR SELECT USING (true);

ALTER TABLE "public"."blocked_slots" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."booking_action_requests" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "booking_action_requests_read" ON "public"."booking_action_requests" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM ("public"."bookings" "b"
     JOIN "public"."salons" "s" ON (("s"."id" = "b"."salon_id")))
  WHERE (("b"."id" = "booking_action_requests"."booking_id") AND (("b"."customer_id" = "auth"."uid"()) OR ("s"."owner_id" = "auth"."uid"()) OR (EXISTS ( SELECT 1
           FROM "public"."staff" "access_staff"
          WHERE (("access_staff"."salon_id" = "b"."salon_id") AND ("access_staff"."profile_id" = "auth"."uid"()) AND "access_staff"."is_active"))) OR "public"."is_super_admin"())))));

ALTER TABLE "public"."booking_audit_events" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."booking_payments" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "booking_payments_parties_read" ON "public"."booking_payments" FOR SELECT USING ((("payer_id" = "auth"."uid"()) OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

ALTER TABLE "public"."booking_services" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "booking_services_read" ON "public"."booking_services" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."bookings" "b"
  WHERE (("b"."id" = "booking_services"."booking_id") AND (("b"."customer_id" = "auth"."uid"()) OR "public"."owns_salon"("b"."salon_id") OR "public"."is_super_admin"())))));

ALTER TABLE "public"."bookings" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "bookings_customer_cancel" ON "public"."bookings" FOR UPDATE USING (("customer_id" = "auth"."uid"())) WITH CHECK (("customer_id" = "auth"."uid"()));

CREATE POLICY "bookings_owner_update" ON "public"."bookings" FOR UPDATE USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "bookings_read" ON "public"."bookings" FOR SELECT USING ((("customer_id" = "auth"."uid"()) OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

CREATE POLICY "bookings_staff_read" ON "public"."bookings" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM "public"."staff" "access_staff"
  WHERE (("access_staff"."salon_id" = "bookings"."salon_id") AND ("access_staff"."profile_id" = "auth"."uid"()) AND "access_staff"."is_active"))));

CREATE POLICY "categories_admin_write" ON "public"."service_categories" USING ("public"."is_super_admin"()) WITH CHECK ("public"."is_super_admin"());

CREATE POLICY "categories_read" ON "public"."service_categories" FOR SELECT USING (("is_active" OR "public"."is_super_admin"()));

ALTER TABLE "public"."customer_booking_restrictions" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "deliveries_own" ON "public"."notification_deliveries" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."notifications" "n"
  WHERE (("n"."id" = "notification_deliveries"."notification_id") AND ("n"."user_id" = "auth"."uid"())))));

ALTER TABLE "public"."device_tokens" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "device_tokens_own" ON "public"."device_tokens" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));

ALTER TABLE "public"."email_events" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."languages" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "languages_read" ON "public"."languages" FOR SELECT USING (true);

ALTER TABLE "public"."notification_deliveries" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."notification_outbox" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."notifications" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notifications_own" ON "public"."notifications" USING (("user_id" = "auth"."uid"())) WITH CHECK (("user_id" = "auth"."uid"()));

ALTER TABLE "public"."payment_anomalies" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."payment_idempotency_keys" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."payment_provider_account_audit" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "payment_provider_account_audit_owner_read" ON "public"."payment_provider_account_audit" FOR SELECT USING (("public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

ALTER TABLE "public"."payment_provider_accounts" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "payment_provider_accounts_owner_read" ON "public"."payment_provider_accounts" FOR SELECT USING (("public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

ALTER TABLE "public"."payment_refunds" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "payment_refunds_parties_read" ON "public"."payment_refunds" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."booking_payments" "p"
  WHERE (("p"."id" = "payment_refunds"."payment_id") AND (("p"."payer_id" = "auth"."uid"()) OR "public"."owns_salon"("p"."salon_id") OR "public"."is_super_admin"())))));

ALTER TABLE "public"."payment_webhook_events" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."profiles" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_self_read" ON "public"."profiles" FOR SELECT USING ((("id" = "auth"."uid"()) OR "public"."is_super_admin"()));

CREATE POLICY "profiles_self_update" ON "public"."profiles" FOR UPDATE USING (("id" = "auth"."uid"()));

ALTER TABLE "public"."salon_access" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."salon_holidays" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "salon_holidays_approval_read" ON "public"."salon_holidays" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "salon_holidays"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));

CREATE POLICY "salon_holidays_owner_write" ON "public"."salon_holidays" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "salon_holidays_read" ON "public"."salon_holidays" FOR SELECT USING (true);

ALTER TABLE "public"."salon_images" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "salon_images_approval_read" ON "public"."salon_images" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "salon_images"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));

CREATE POLICY "salon_images_owner_write" ON "public"."salon_images" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "salon_images_read" ON "public"."salon_images" FOR SELECT USING (true);

ALTER TABLE "public"."salon_payout_account_history" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."salon_payout_accounts" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "salon_payout_accounts_owner" ON "public"."salon_payout_accounts" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "salon_payout_history_owner_read" ON "public"."salon_payout_account_history" FOR SELECT USING ("public"."owns_salon"("salon_id"));

ALTER TABLE "public"."salon_reports" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "salon_reports_self_read" ON "public"."salon_reports" FOR SELECT TO "authenticated" USING ((("reporter_id" = "auth"."uid"()) AND "is_active"));

ALTER TABLE "public"."salon_subscriptions" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."salons" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "salons_owner_update" ON "public"."salons" FOR UPDATE USING (("owner_id" = "auth"."uid"())) WITH CHECK ((("owner_id" = "auth"."uid"()) AND ("is_active" = ( SELECT "s"."is_active"
   FROM "public"."salons" "s"
  WHERE ("s"."id" = "salons"."id")))));

CREATE POLICY "salons_public_read" ON "public"."salons" FOR SELECT USING ((("is_active" AND "profile_completed" AND ("approval_status" = 'approved'::"public"."salon_approval_status")) OR ("owner_id" = "auth"."uid"()) OR "public"."is_super_admin"()));

ALTER TABLE "public"."service_categories" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."service_subcategories" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."services" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "services_approval_read" ON "public"."services" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "services"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));

CREATE POLICY "services_owner_write" ON "public"."services" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "services_public_read" ON "public"."services" FOR SELECT USING (("is_active" OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

CREATE POLICY "ssl_owner_write" ON "public"."staff_service_languages" USING ((EXISTS ( SELECT 1
   FROM ("public"."staff_services" "ss"
     JOIN "public"."staff" "st" ON (("st"."id" = "ss"."staff_id")))
  WHERE (("ss"."id" = "staff_service_languages"."staff_service_id") AND "public"."owns_salon"("st"."salon_id"))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."staff_services" "ss"
     JOIN "public"."staff" "st" ON (("st"."id" = "ss"."staff_id")))
  WHERE (("ss"."id" = "staff_service_languages"."staff_service_id") AND "public"."owns_salon"("st"."salon_id")))));

CREATE POLICY "ssl_read" ON "public"."staff_service_languages" FOR SELECT USING (true);

ALTER TABLE "public"."staff" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "staff_approval_read" ON "public"."staff" AS RESTRICTIVE FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."salons" "sl"
  WHERE (("sl"."id" = "staff"."salon_id") AND (("sl"."is_active" AND "sl"."profile_completed" AND ("sl"."approval_status" = 'approved'::"public"."salon_approval_status")) OR ("sl"."owner_id" = "auth"."uid"()) OR "public"."is_super_admin"())))));

CREATE POLICY "staff_owner_write" ON "public"."staff" USING ("public"."owns_salon"("salon_id")) WITH CHECK ("public"."owns_salon"("salon_id"));

CREATE POLICY "staff_public_read" ON "public"."staff" FOR SELECT USING (("is_active" OR "public"."owns_salon"("salon_id") OR "public"."is_super_admin"()));

ALTER TABLE "public"."staff_service_languages" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."staff_services" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "staff_services_owner_write" ON "public"."staff_services" USING ((EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "staff_services"."staff_id") AND "public"."owns_salon"("s"."salon_id"))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."staff" "s"
  WHERE (("s"."id" = "staff_services"."staff_id") AND "public"."owns_salon"("s"."salon_id")))));

CREATE POLICY "staff_services_read" ON "public"."staff_services" FOR SELECT USING (true);

CREATE POLICY "subcategories_admin_write" ON "public"."service_subcategories" USING ("public"."is_super_admin"()) WITH CHECK ("public"."is_super_admin"());

CREATE POLICY "subcategories_read" ON "public"."service_subcategories" FOR SELECT USING (("is_active" OR "public"."is_super_admin"()));

ALTER TABLE "public"."subscription_billing_records" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."subscription_events" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."subscription_plans" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."subscription_provider_accounts" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."support_messages" ENABLE ROW LEVEL SECURITY;

ALTER TABLE "public"."support_tickets" ENABLE ROW LEVEL SECURITY;

ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."blocked_slots";

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."booking_action_requests";

ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."bookings";

GRANT USAGE ON SCHEMA "public" TO "postgres";

GRANT USAGE ON SCHEMA "public" TO "anon";

GRANT USAGE ON SCHEMA "public" TO "authenticated";

GRANT USAGE ON SCHEMA "public" TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey16_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey16_out"("public"."gbtreekey16") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey2_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey2_out"("public"."gbtreekey2") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey32_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey32_out"("public"."gbtreekey32") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey4_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey4_out"("public"."gbtreekey4") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey8_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey8_out"("public"."gbtreekey8") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_in"("cstring") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "anon";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbtreekey_var_out"("public"."gbtreekey_var") TO "service_role";

GRANT ALL ON FUNCTION "public"."app_role"() TO "anon";

GRANT ALL ON FUNCTION "public"."app_role"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."app_role"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."apply_subscription_billing_record"("p_record_id" "uuid", "p_grace_days" integer) TO "service_role";

REVOKE ALL ON FUNCTION "public"."booking_append_audit"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."booking_append_audit"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."cancel_salon_subscription_renewal"("p_salon_id" "uuid") TO "service_role";

GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "postgres";

GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "anon";

GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "authenticated";

GRANT ALL ON FUNCTION "public"."cash_dist"("money", "money") TO "service_role";

REVOKE ALL ON FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."create_booking"("p_salon_id" "uuid", "p_staff_id" "uuid", "p_service_ids" "uuid"[], "p_start" timestamp with time zone, "p_customer_name" "text", "p_customer_phone" "text", "p_source" "public"."booking_source", "p_notes" "text") TO "service_role";

GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "postgres";

GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "anon";

GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "authenticated";

GRANT ALL ON FUNCTION "public"."date_dist"("date", "date") TO "service_role";

REVOKE ALL ON FUNCTION "public"."deactivate_device_token"("p_token" "text") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."deactivate_device_token"("p_token" "text") TO "authenticated";

GRANT ALL ON FUNCTION "public"."deactivate_device_token"("p_token" "text") TO "service_role";

GRANT ALL ON FUNCTION "public"."demote_other_main_images"() TO "anon";

GRANT ALL ON FUNCTION "public"."demote_other_main_images"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."demote_other_main_images"() TO "service_role";

GRANT ALL ON FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") TO "anon";

GRANT ALL ON FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") TO "authenticated";

GRANT ALL ON FUNCTION "public"."effective_duration"("p_staff_id" "uuid", "p_service_id" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."enqueue_booking_email"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."enqueue_booking_email"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."enqueue_verified_payment_receipt"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."enqueue_verified_payment_receipt"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."erase_profile_references"("p_user" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."erase_profile_references"("p_user" "uuid") TO "service_role";

GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "postgres";

GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "anon";

GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "authenticated";

GRANT ALL ON FUNCTION "public"."float4_dist"(real, real) TO "service_role";

GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "postgres";

GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "anon";

GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "authenticated";

GRANT ALL ON FUNCTION "public"."float8_dist"(double precision, double precision) TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_consistent"("internal", bit, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bit_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_consistent"("internal", boolean, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_same"("public"."gbtreekey2", "public"."gbtreekey2", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bool_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bpchar_consistent"("internal", character, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_consistent"("internal", "bytea", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_bytea_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_consistent"("internal", "money", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_distance"("internal", "money", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_cash_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_consistent"("internal", "date", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_distance"("internal", "date", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_date_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_decompress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_consistent"("internal", "anyenum", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_enum_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_consistent"("internal", real, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_distance"("internal", real, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float4_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_consistent"("internal", double precision, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_distance"("internal", double precision, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_float8_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_consistent"("internal", "inet", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_inet_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_consistent"("internal", smallint, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_distance"("internal", smallint, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_same"("public"."gbtreekey4", "public"."gbtreekey4", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int2_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_consistent"("internal", integer, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_distance"("internal", integer, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int4_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_consistent"("internal", bigint, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_distance"("internal", bigint, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_int8_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_consistent"("internal", interval, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_decompress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_distance"("internal", interval, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_intv_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_consistent"("internal", "macaddr8", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad8_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_consistent"("internal", "macaddr", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_macad_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_consistent"("internal", numeric, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_numeric_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_consistent"("internal", "oid", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_distance"("internal", "oid", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_same"("public"."gbtreekey8", "public"."gbtreekey8", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_oid_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_consistent"("internal", "text", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_same"("public"."gbtreekey_var", "public"."gbtreekey_var", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_text_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_consistent"("internal", time without time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_distance"("internal", time without time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_time_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_timetz_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_timetz_consistent"("internal", time with time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_consistent"("internal", timestamp without time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_distance"("internal", timestamp without time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_same"("public"."gbtreekey16", "public"."gbtreekey16", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_ts_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_tstz_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_tstz_consistent"("internal", timestamp with time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_tstz_distance"("internal", timestamp with time zone, smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_compress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_consistent"("internal", "uuid", smallint, "oid", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_fetch"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_penalty"("internal", "internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_picksplit"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_same"("public"."gbtreekey32", "public"."gbtreekey32", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_uuid_union"("internal", "internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_var_decompress"("internal") TO "service_role";

GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "postgres";

GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "anon";

GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "authenticated";

GRANT ALL ON FUNCTION "public"."gbt_var_fetch"("internal") TO "service_role";

REVOKE ALL ON FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."get_active_tokens"("p_user_id" "uuid") TO "service_role";

GRANT ALL ON FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) TO "anon";

GRANT ALL ON FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) TO "authenticated";

GRANT ALL ON FUNCTION "public"."get_available_slots"("p_staff_id" "uuid", "p_date" "date", "p_duration_minutes" integer) TO "service_role";

GRANT ALL ON FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") TO "anon";

GRANT ALL ON FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") TO "authenticated";

GRANT ALL ON FUNCTION "public"."get_salon_by_qr"("p_qr_token" "text") TO "service_role";

REVOKE ALL ON FUNCTION "public"."guard_audit_immutable"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."guard_audit_immutable"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_booking_against_closure"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_booking_against_closure"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_booking_against_closure"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."guard_booking_checkout"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."guard_booking_checkout"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_booking_payment_columns"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_booking_payment_columns"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_booking_payment_columns"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_booking_salon_approval"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_booking_salon_approval"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_booking_salon_approval"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."guard_collection_snapshot"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."guard_collection_snapshot"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_media_reference"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_media_reference"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_media_reference"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_salon_approval"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_salon_approval"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_salon_approval"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_salon_discovery_placement"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_salon_discovery_placement"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_salon_discovery_placement"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_salon_display_priority"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_salon_display_priority"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_salon_display_priority"() TO "service_role";

GRANT ALL ON FUNCTION "public"."guard_subscription_admin"() TO "anon";

GRANT ALL ON FUNCTION "public"."guard_subscription_admin"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."guard_subscription_admin"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."handle_new_user"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."handle_new_user"() TO "service_role";

GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "postgres";

GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "anon";

GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "authenticated";

GRANT ALL ON FUNCTION "public"."int2_dist"(smallint, smallint) TO "service_role";

GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "postgres";

GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "anon";

GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "authenticated";

GRANT ALL ON FUNCTION "public"."int4_dist"(integer, integer) TO "service_role";

GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "postgres";

GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "anon";

GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "authenticated";

GRANT ALL ON FUNCTION "public"."int8_dist"(bigint, bigint) TO "service_role";

GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "postgres";

GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "anon";

GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "authenticated";

GRANT ALL ON FUNCTION "public"."interval_dist"(interval, interval) TO "service_role";

GRANT ALL ON FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) TO "anon";

GRANT ALL ON FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) TO "authenticated";

GRANT ALL ON FUNCTION "public"."is_subscription_promotion_active"("p_status" "public"."subscription_status", "p_current_start" timestamp with time zone, "p_current_end" timestamp with time zone, "p_grace_end" timestamp with time zone, "p_now" timestamp with time zone) TO "service_role";

GRANT ALL ON FUNCTION "public"."is_super_admin"() TO "anon";

GRANT ALL ON FUNCTION "public"."is_super_admin"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."is_super_admin"() TO "service_role";

GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "postgres";

GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "anon";

GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "authenticated";

GRANT ALL ON FUNCTION "public"."oid_dist"("oid", "oid") TO "service_role";

GRANT ALL ON FUNCTION "public"."owns_salon"("p_salon_id" "uuid") TO "anon";

GRANT ALL ON FUNCTION "public"."owns_salon"("p_salon_id" "uuid") TO "authenticated";

GRANT ALL ON FUNCTION "public"."owns_salon"("p_salon_id" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."payment_append_audit"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."payment_append_audit"() TO "service_role";

GRANT ALL ON TABLE "public"."salon_payout_accounts" TO "service_role";

GRANT ALL ON FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") TO "anon";

GRANT ALL ON FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") TO "authenticated";

GRANT ALL ON FUNCTION "public"."payout_account_snapshot"("r" "public"."salon_payout_accounts") TO "service_role";

REVOKE ALL ON FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."recompute_booking_payment_state"("p_booking_id" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."recompute_salon_trial"("p_salon_id" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") TO "authenticated";

GRANT ALL ON FUNCTION "public"."register_device_token"("p_token" "text", "p_platform" "text", "p_device_name" "text") TO "service_role";

REVOKE ALL ON FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."salon_booking_eligible"("p_salon" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."salon_payout_account_masked"("p_salon_id" "uuid") TO "service_role";

REVOKE ALL ON FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."salon_trial_setting"("p_name" "text", "p_default" integer, "p_min" integer, "p_max" integer) TO "service_role";

GRANT ALL ON FUNCTION "public"."set_audit_actor"() TO "anon";

GRANT ALL ON FUNCTION "public"."set_audit_actor"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."set_audit_actor"() TO "service_role";

GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";

GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";

GRANT ALL ON FUNCTION "public"."stamp_booking_lifecycle"() TO "anon";

GRANT ALL ON FUNCTION "public"."stamp_booking_lifecycle"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."stamp_booking_lifecycle"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."stamp_checkout_policy"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."stamp_checkout_policy"() TO "service_role";

GRANT ALL ON FUNCTION "public"."stamp_notification_read_at"() TO "anon";

GRANT ALL ON FUNCTION "public"."stamp_notification_read_at"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."stamp_notification_read_at"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone) FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."start_salon_trial"("p_salon_id" "uuid", "p_at" timestamp with time zone) TO "service_role";

REVOKE ALL ON FUNCTION "public"."sweep_lapsed_subscriptions"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."sweep_lapsed_subscriptions"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_guard"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_guard"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_guard"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_recompute"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_recompute"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_booking_payments_recompute"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."tg_bookings_recompute_trial"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."tg_bookings_recompute_trial"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_guard"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_guard"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_guard"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_recompute"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_recompute"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_payment_refunds_recompute"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_salon_payout_account_history"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_salon_payout_account_history"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_salon_payout_account_history"() TO "service_role";

REVOKE ALL ON FUNCTION "public"."tg_salons_access_row"() FROM PUBLIC;

GRANT ALL ON FUNCTION "public"."tg_salons_access_row"() TO "service_role";

GRANT ALL ON FUNCTION "public"."tg_subscription_billing_guard"() TO "anon";

GRANT ALL ON FUNCTION "public"."tg_subscription_billing_guard"() TO "authenticated";

GRANT ALL ON FUNCTION "public"."tg_subscription_billing_guard"() TO "service_role";

GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "postgres";

GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "anon";

GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "authenticated";

GRANT ALL ON FUNCTION "public"."time_dist"(time without time zone, time without time zone) TO "service_role";

GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "postgres";

GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "anon";

GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "authenticated";

GRANT ALL ON FUNCTION "public"."ts_dist"(timestamp without time zone, timestamp without time zone) TO "service_role";

GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "postgres";

GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "anon";

GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "authenticated";

GRANT ALL ON FUNCTION "public"."tstz_dist"(timestamp with time zone, timestamp with time zone) TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."account_deletion_challenges" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."account_deletion_challenges" TO "authenticated";

GRANT ALL ON TABLE "public"."account_deletion_challenges" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."account_deletion_requests" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."account_deletion_requests" TO "authenticated";

GRANT ALL ON TABLE "public"."account_deletion_requests" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."alembic_version" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."alembic_version" TO "authenticated";

GRANT ALL ON TABLE "public"."alembic_version" TO "service_role";

GRANT ALL ON TABLE "public"."api_rate_limits" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."blocked_slots" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."blocked_slots" TO "authenticated";

GRANT ALL ON TABLE "public"."blocked_slots" TO "service_role";

GRANT ALL ON TABLE "public"."booking_action_requests" TO "service_role";

GRANT SELECT ON TABLE "public"."booking_action_requests" TO "authenticated";

GRANT ALL ON TABLE "public"."booking_audit_events" TO "service_role";

GRANT ALL ON TABLE "public"."booking_payments" TO "service_role";

REVOKE ALL ON TABLE "public"."booking_services" FROM "anon";

GRANT SELECT ON TABLE "public"."booking_services" TO "authenticated";

GRANT ALL ON TABLE "public"."booking_services" TO "service_role";

REVOKE ALL ON TABLE "public"."bookings" FROM "anon";

GRANT SELECT ON TABLE "public"."bookings" TO "authenticated";

GRANT ALL ON TABLE "public"."bookings" TO "service_role";

GRANT ALL ON TABLE "public"."customer_booking_restrictions" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."device_tokens" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."device_tokens" TO "authenticated";

GRANT ALL ON TABLE "public"."device_tokens" TO "service_role";

GRANT ALL ON TABLE "public"."email_events" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."languages" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."languages" TO "authenticated";

GRANT ALL ON TABLE "public"."languages" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."notification_deliveries" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."notification_deliveries" TO "authenticated";

GRANT ALL ON TABLE "public"."notification_deliveries" TO "service_role";

GRANT ALL ON TABLE "public"."notification_outbox" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."notifications" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."notifications" TO "authenticated";

GRANT ALL ON TABLE "public"."notifications" TO "service_role";

GRANT ALL ON TABLE "public"."payment_anomalies" TO "service_role";

GRANT ALL ON TABLE "public"."payment_idempotency_keys" TO "service_role";

GRANT ALL ON TABLE "public"."payment_provider_account_audit" TO "service_role";

GRANT ALL ON TABLE "public"."payment_provider_accounts" TO "service_role";

GRANT ALL ON TABLE "public"."payment_refunds" TO "service_role";

GRANT ALL ON TABLE "public"."payment_webhook_events" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."profiles" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."profiles" TO "authenticated";

GRANT ALL ON TABLE "public"."profiles" TO "service_role";

GRANT ALL ON TABLE "public"."salon_access" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_holidays" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_holidays" TO "authenticated";

GRANT ALL ON TABLE "public"."salon_holidays" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_images" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_images" TO "authenticated";

GRANT ALL ON TABLE "public"."salon_images" TO "service_role";

GRANT ALL ON TABLE "public"."salon_payout_account_history" TO "service_role";

GRANT ALL ON TABLE "public"."salon_reports" TO "service_role";

GRANT SELECT ON TABLE "public"."salon_reports" TO "authenticated";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_subscriptions" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salon_subscriptions" TO "authenticated";

GRANT ALL ON TABLE "public"."salon_subscriptions" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salons" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."salons" TO "authenticated";

GRANT ALL ON TABLE "public"."salons" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."service_categories" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."service_categories" TO "authenticated";

GRANT ALL ON TABLE "public"."service_categories" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."service_subcategories" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."service_subcategories" TO "authenticated";

GRANT ALL ON TABLE "public"."service_subcategories" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."services" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."services" TO "authenticated";

GRANT ALL ON TABLE "public"."services" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff" TO "authenticated";

GRANT ALL ON TABLE "public"."staff" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff_service_languages" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff_service_languages" TO "authenticated";

GRANT ALL ON TABLE "public"."staff_service_languages" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff_services" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."staff_services" TO "authenticated";

GRANT ALL ON TABLE "public"."staff_services" TO "service_role";

GRANT ALL ON TABLE "public"."subscription_billing_records" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_events" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_events" TO "authenticated";

GRANT ALL ON TABLE "public"."subscription_events" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_plans" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_plans" TO "authenticated";

GRANT ALL ON TABLE "public"."subscription_plans" TO "service_role";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_provider_accounts" TO "anon";

GRANT SELECT,INSERT,UPDATE,DELETE ON TABLE "public"."subscription_provider_accounts" TO "authenticated";

GRANT ALL ON TABLE "public"."subscription_provider_accounts" TO "service_role";

GRANT ALL ON TABLE "public"."support_messages" TO "service_role";

GRANT ALL ON TABLE "public"."support_tickets" TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON FUNCTIONS FROM "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON FUNCTIONS FROM "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON TABLES FROM "anon";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE ALL ON TABLES FROM "authenticated";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

