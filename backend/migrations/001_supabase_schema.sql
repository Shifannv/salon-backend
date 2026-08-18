-- =====================================================================
-- SALON PLATFORM — COMPLETE SCHEMA (v3)
-- Consolidated. This is 001 + 002 + 003 flattened into one fresh-install script.
-- Run top to bottom on an EMPTY Supabase project.
--
-- Already have an earlier version applied with data? Run the incremental
-- migrations (002_schema_v2.sql, 003_audit_columns.sql) instead — this file
-- will not run against a populated database.
--
-- Shared by: Super Admin Panel, Customer App, Owner App, Walk-in QR Web App
-- =====================================================================

create extension if not exists "pgcrypto";
create extension if not exists "btree_gist";   -- required for the overlap constraint


-- =====================================================================
-- 1. ENUMS
-- =====================================================================

create type user_role      as enum ('super_admin', 'owner', 'staff', 'customer');
create type approval_mode  as enum ('auto', 'manual');
create type booking_status as enum ('pending', 'confirmed', 'rejected', 'completed', 'cancelled');
create type payment_status as enum ('unpaid', 'paid');
create type payment_method as enum ('cash', 'online');
create type booking_source as enum ('app', 'manual_walkin', 'qr_walkin');


-- =====================================================================
-- 2. SHARED TRIGGER FUNCTIONS
-- =====================================================================

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

create or replace function set_audit_actor()
returns trigger language plpgsql as $$
begin
  if tg_op = 'INSERT' then
    new.created_by := coalesce(new.created_by, auth.uid());
    new.updated_by := coalesce(new.updated_by, auth.uid());
  else
    new.updated_by := coalesce(auth.uid(), old.updated_by);
    new.created_by := old.created_by;          -- immutable
  end if;
  return new;
end $$;


-- =====================================================================
-- 3. PROFILES — one row per authenticated user, all roles
-- =====================================================================

create table profiles (
  id             uuid primary key references auth.users(id) on delete cascade,
  role           user_role   not null default 'customer',
  full_name      text,
  email          text unique,      -- owners & super admin sign in with this
  phone          text,             -- contact number; only OTP-verified via the QR web app
  phone_verified boolean     not null default false,
  avatar_url     text,
  is_active      boolean     not null default true,
  created_by     uuid references profiles(id),
  updated_by     uuid references profiles(id),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index idx_profiles_role       on profiles(role);
create index idx_profiles_phone      on profiles(phone);
create index idx_profiles_created_by on profiles(created_by);

create trigger t_profiles_updated before update on profiles
  for each row execute function set_updated_at();
create trigger t_profiles_audit before insert or update on profiles
  for each row execute function set_audit_actor();

-- AUTH MODEL (Phase 1)
--   super_admin / owner   -> email + password
--   customer (app)        -> NO OTP for now; phone is an unverified contact field
--   customer (QR web app) -> phone + OTP, the ONLY channel that yields a verified number
--
-- `phone` is deliberately NOT unique. A person may book once as a QR walk-in
-- (verified) and later sign up in the customer app with the same number. A unique
-- constraint would hard-fail that second signup. Deduplicate deliberately later —
-- see the identity-merge note at the bottom of this file.


-- Auto-create a profile whenever an auth user is created (by the Super Admin
-- panel for owners, or by phone-OTP signup for QR walk-in customers).
create or replace function handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, phone, full_name, role)
  values (
    new.id,
    new.email,
    new.phone,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    coalesce((new.raw_user_meta_data ->> 'role')::user_role, 'customer')
  )
  on conflict (id) do nothing;
  return new;
end $$;

create trigger t_on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();


-- =====================================================================
-- 4. SALONS — created by the Super Admin, completed by the owner
-- =====================================================================

create table salons (
  id                     uuid primary key default gen_random_uuid(),
  owner_id               uuid not null references profiles(id),
  name                   text not null,
  description            text,
  category               text,                 -- 'mens' | 'womens' | 'unisex'
  address                text,
  city                   text,
  lat                    double precision,
  lng                    double precision,
  timezone               text not null default 'Asia/Kolkata',
  working_hours          jsonb not null default '{}'::jsonb,
  approval_mode          approval_mode not null default 'manual',
  slot_interval_minutes  int not null default 15 check (slot_interval_minutes > 0),
  qr_token               text unique not null default encode(gen_random_bytes(16), 'hex'),
  profile_completed      boolean not null default false,
  is_active              boolean not null default true,   -- soft delete lives here
  created_by             uuid references profiles(id),
  updated_by             uuid references profiles(id),
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create index idx_salons_owner      on salons(owner_id);
create index idx_salons_updated_by on salons(updated_by);
create index idx_salons_active on salons(is_active, profile_completed);
create index idx_salons_city   on salons(city);

create trigger t_salons_updated before update on salons
  for each row execute function set_updated_at();
create trigger t_salons_audit before insert or update on salons
  for each row execute function set_audit_actor();

-- working_hours shape (a missing/null day key means CLOSED that day):
--   {"mon": {"open":"09:00","close":"21:00"},
--    "tue": {"open":"09:00","close":"21:00"},
--    "sun": null}
--
-- qr_token is what the printed in-shop QR code encodes:
--   https://walkin.yoursite.com/s/{qr_token}
-- Using a token instead of the salon id means the URL leaks no internal ids
-- and can be rotated if a QR sticker is ever compromised.


create table salon_images (
  id         uuid primary key default gen_random_uuid(),
  salon_id   uuid not null references salons(id) on delete cascade,
  url        text not null,
  caption    text,
  is_main    boolean not null default false,
  sort_order int not null default 0,
  created_by uuid references profiles(id),
  updated_by uuid references profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Exactly one main image per salon, enforced by the database.
create unique index uq_salon_main_image on salon_images(salon_id) where is_main;
create index idx_salon_images_salon on salon_images(salon_id, sort_order);

-- Setting a new main image demotes the old one automatically, so clients
-- never have to do a two-step update.
create or replace function demote_other_main_images()
returns trigger language plpgsql as $$
begin
  if new.is_main then
    update salon_images set is_main = false
    where salon_id = new.salon_id and id <> new.id and is_main;
  end if;
  return new;
end $$;

create trigger t_salon_main_image before insert or update of is_main on salon_images
  for each row execute function demote_other_main_images();
create trigger t_salon_images_updated before update on salon_images
  for each row execute function set_updated_at();
create trigger t_salon_images_audit before insert or update on salon_images
  for each row execute function set_audit_actor();


create table salon_holidays (
  id           uuid primary key default gen_random_uuid(),
  salon_id     uuid not null references salons(id) on delete cascade,
  holiday_date date not null,
  title        text,
  is_recurring boolean not null default false,   -- annual, e.g. Onam
  created_by   uuid references profiles(id),
  updated_by   uuid references profiles(id),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (salon_id, holiday_date)
);

create index idx_salon_holidays on salon_holidays(salon_id, holiday_date);

create trigger t_salon_holidays_updated before update on salon_holidays
  for each row execute function set_updated_at();
create trigger t_salon_holidays_audit before insert or update on salon_holidays
  for each row execute function set_audit_actor();


-- =====================================================================
-- 5. SERVICE CATALOG — category > subcategory > service
-- =====================================================================
-- The catalog is GLOBAL and platform-curated (super admin owns it), so every
-- salon's services roll up into one taxonomy and cross-salon search works.
-- To make it per-salon instead, add a nullable salon_id to both tables and
-- widen the RLS write policies.

create table service_categories (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  slug        text not null unique,
  image_url   text,
  description text,
  sort_order  int not null default 0,
  is_active   boolean not null default true,
  created_by  uuid references profiles(id),
  updated_by  uuid references profiles(id),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table service_subcategories (
  id          uuid primary key default gen_random_uuid(),
  category_id uuid not null references service_categories(id),
  name        text not null,
  slug        text not null,
  image_url   text,
  description text,
  sort_order  int not null default 0,
  is_active   boolean not null default true,
  created_by  uuid references profiles(id),
  updated_by  uuid references profiles(id),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (category_id, slug)
);

create index idx_subcategories_category on service_subcategories(category_id, is_active);

create trigger t_categories_updated before update on service_categories
  for each row execute function set_updated_at();
create trigger t_subcategories_updated before update on service_subcategories
  for each row execute function set_updated_at();
create trigger t_categories_audit before insert or update on service_categories
  for each row execute function set_audit_actor();
create trigger t_subcategories_audit before insert or update on service_subcategories
  for each row execute function set_audit_actor();


create table services (
  id               uuid primary key default gen_random_uuid(),
  salon_id         uuid not null references salons(id),
  subcategory_id   uuid not null references service_subcategories(id),
  name             text not null,
  description      text,
  duration_minutes int  not null check (duration_minutes > 0),
  price            numeric(10,2) not null check (price >= 0),
  is_active        boolean not null default true,
  created_by       uuid references profiles(id),
  updated_by       uuid references profiles(id),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index idx_services_salon       on services(salon_id, is_active);
create index idx_services_subcategory on services(subcategory_id) where is_active;
create index idx_services_updated_by  on services(updated_by);

create trigger t_services_updated before update on services
  for each row execute function set_updated_at();
create trigger t_services_audit before insert or update on services
  for each row execute function set_audit_actor();


-- =====================================================================
-- 6. STAFF  (the barbers working under an owner)
-- =====================================================================

create table staff (
  id             uuid primary key default gen_random_uuid(),
  salon_id       uuid not null references salons(id),
  profile_id     uuid references profiles(id),   -- null in Phase 1: staff have no login yet
  name           text not null,
  photo_url      text,
  specialization text,
  experience     text,
  working_hours  jsonb,        -- null = inherit the salon's hours
  is_active      boolean not null default true,
  created_by     uuid references profiles(id),
  updated_by     uuid references profiles(id),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create index idx_staff_salon on staff(salon_id, is_active);

create trigger t_staff_updated before update on staff
  for each row execute function set_updated_at();
create trigger t_staff_audit before insert or update on staff
  for each row execute function set_audit_actor();


create table languages (
  code text primary key,          -- ISO 639-1: 'en', 'ml', 'hi', 'ar'
  name text not null
);

insert into languages (code, name) values
  ('en','English'), ('ml','Malayalam'), ('hi','Hindi'),
  ('ta','Tamil'), ('ar','Arabic'), ('kn','Kannada');


-- Per-staff overrides. A senior barber may take 45 min for a cut the salon
-- lists as 30 — duration_minutes/price_override capture that. NULL means
-- "use the service default".
create table staff_services (
  id               uuid primary key default gen_random_uuid(),
  staff_id         uuid not null references staff(id) on delete cascade,
  service_id       uuid not null references services(id) on delete cascade,
  duration_minutes int check (duration_minutes is null or duration_minutes > 0),
  price_override   numeric(10,2) check (price_override is null or price_override >= 0),
  specialization   text,
  is_active        boolean not null default true,
  created_by       uuid references profiles(id),
  updated_by       uuid references profiles(id),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (staff_id, service_id)
);

create index idx_staff_services_staff   on staff_services(staff_id) where is_active;
create index idx_staff_services_service on staff_services(service_id) where is_active;

create trigger t_staff_services_updated before update on staff_services
  for each row execute function set_updated_at();
create trigger t_staff_services_audit before insert or update on staff_services
  for each row execute function set_audit_actor();


create table staff_service_languages (
  staff_service_id uuid not null references staff_services(id) on delete cascade,
  language_code    text not null references languages(code),
  primary key (staff_service_id, language_code)
);

create index idx_ssl_language on staff_service_languages(language_code);


create or replace function effective_duration(p_staff_id uuid, p_service_id uuid)
returns int language sql stable set search_path = public as $$
  select coalesce(ss.duration_minutes, sv.duration_minutes)
  from services sv
  left join staff_services ss
    on ss.service_id = sv.id and ss.staff_id = p_staff_id and ss.is_active
  where sv.id = p_service_id;
$$;


-- =====================================================================
-- 7. BLOCKED SLOTS  (leave, lunch, ad-hoc unavailability)
-- staff_id NULL + salon_id set = the whole salon is blocked.
-- =====================================================================

create table blocked_slots (
  id              uuid primary key default gen_random_uuid(),
  staff_id        uuid references staff(id) on delete cascade,
  salon_id        uuid references salons(id) on delete cascade,
  start_datetime  timestamptz not null,
  end_datetime    timestamptz not null,
  block_type      text not null default 'other'
    check (block_type in ('leave','break','lunch','training','holiday','other')),
  reason          text,
  is_full_day     boolean not null default false,
  is_recurring    boolean not null default false,
  recurrence_rule text,        -- iCal RRULE; stored but NOT yet interpreted
  recurrence_end  date,
  created_by      uuid references profiles(id),
  updated_by      uuid references profiles(id),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (end_datetime > start_datetime),
  constraint blocked_scope_check check (staff_id is not null or salon_id is not null)
);

create index idx_blocked_staff_time on blocked_slots(staff_id, start_datetime, end_datetime);
create index idx_blocked_salon_time on blocked_slots(salon_id, start_datetime, end_datetime);

create trigger t_blocked_updated before update on blocked_slots
  for each row execute function set_updated_at();
create trigger t_blocked_audit before insert or update on blocked_slots
  for each row execute function set_audit_actor();


-- =====================================================================
-- 8. BOOKINGS  — the one table every app converges on
-- =====================================================================

create table bookings (
  id                     uuid primary key default gen_random_uuid(),
  salon_id               uuid not null references salons(id),
  staff_id               uuid not null references staff(id),

  -- customer_id is NULL only for walk-ins typed in by staff, who never log in
  customer_id            uuid references profiles(id),
  customer_name          text not null,
  customer_phone         text,          -- optional: a counter walk-in may decline
  -- Informational ONLY. TRUE for qr_walkin (the OTP channel). Never a
  -- precondition for creating a booking — do not validate against it.
  phone_verified         boolean not null default false,

  source                 booking_source not null default 'app',
  status                 booking_status not null default 'pending',

  start_datetime         timestamptz not null,
  end_datetime           timestamptz not null,
  total_duration_minutes int not null check (total_duration_minutes > 0),
  total_price            numeric(10,2) not null check (total_price >= 0),

  payment_status         payment_status not null default 'unpaid',
  payment_method         payment_method,

  rejection_reason       text,
  notes                  text,

  -- Lifecycle actors. A booking passes through several distinct decisions,
  -- potentially by different people. A single updated_by would only ever
  -- remember the most recent one, so each decision gets its own column.
  -- Stamped automatically by t_bookings_lifecycle below.
  approved_by            uuid references profiles(id),
  approved_at            timestamptz,
  rejected_by            uuid references profiles(id),
  rejected_at            timestamptz,
  completed_by           uuid references profiles(id),
  completed_at           timestamptz,
  cancelled_by           uuid references profiles(id),
  cancelled_at           timestamptz,
  payment_recorded_by    uuid references profiles(id),
  payment_recorded_at    timestamptz,

  created_by             uuid references profiles(id),
  updated_by             uuid references profiles(id),
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  check (end_datetime > start_datetime),
  check (customer_id is not null or source = 'manual_walkin'),
  check (status <> 'rejected' or rejection_reason is not null)
);

create index idx_bookings_salon_day   on bookings(salon_id, start_datetime);
create index idx_bookings_staff_day   on bookings(staff_id, start_datetime);
create index idx_bookings_customer    on bookings(customer_id);
create index idx_bookings_status_time on bookings(salon_id, status, start_datetime);
create index idx_bookings_pending     on bookings(salon_id) where status = 'pending';
create index idx_bookings_approved_by  on bookings(approved_by);
create index idx_bookings_completed_by on bookings(completed_by);

create trigger t_bookings_updated before update on bookings
  for each row execute function set_updated_at();
create trigger t_bookings_audit before insert or update on bookings
  for each row execute function set_audit_actor();


-- Stamp the lifecycle actor on each status transition, so no client can
-- forget to set it (or set someone else's id).
create or replace function stamp_booking_lifecycle()
returns trigger language plpgsql as $$
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

create trigger t_bookings_lifecycle before update on bookings
  for each row execute function stamp_booking_lifecycle();

-- ---------------------------------------------------------------------
-- THE DOUBLE-BOOKING GUARANTEE
-- Enforced by the database, not by app code. Any client — customer app,
-- owner app, QR web app — that tries to write an overlapping slot for the
-- same staff member gets rejected at the constraint level. This is what
-- makes "several apps, one slot engine" actually safe.
-- ---------------------------------------------------------------------
alter table bookings add constraint bookings_no_overlap
  exclude using gist (
    staff_id with =,
    tstzrange(start_datetime, end_datetime) with &&
  ) where (status in ('pending', 'confirmed'));


-- Line items. Name/duration/price are SNAPSHOTS: if the owner later edits or
-- deactivates a service, historical bookings must not silently change.
create table booking_services (
  booking_id       uuid not null references bookings(id) on delete cascade,
  service_id       uuid not null references services(id),
  service_name     text not null,
  duration_minutes int  not null,
  price            numeric(10,2) not null,
  -- Rows are immutable snapshots written by create_booking(), so updated_by
  -- stays null in practice. Present for schema consistency.
  created_by       uuid references profiles(id),
  updated_by       uuid references profiles(id),
  primary key (booking_id, service_id)
);

create trigger t_booking_services_audit before insert or update on booking_services
  for each row execute function set_audit_actor();


-- =====================================================================
-- 9. NOTIFICATIONS & MULTI-DEVICE PUSH
-- =====================================================================

create table notifications (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references profiles(id) on delete cascade,
  booking_id uuid references bookings(id) on delete cascade,
  type       text,
  title      text not null,
  body       text,
  read       boolean not null default false,
  created_at timestamptz not null default now()
);

create index idx_notifications_user on notifications(user_id, read, created_at desc);


-- One row per physical device. A user may hold many. Sign-out deactivates
-- one row; it never deletes and never touches the user's other devices.
create table device_tokens (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references profiles(id) on delete cascade,
  token        text not null unique,
  platform     text,
  device_name  text,
  is_active    boolean not null default true,
  last_seen_at timestamptz not null default now(),
  created_at   timestamptz not null default now()
);

create index idx_device_tokens_active on device_tokens(user_id) where is_active;


-- Per-device delivery ledger: one notification, N device rows.
create table notification_deliveries (
  id              uuid primary key default gen_random_uuid(),
  notification_id uuid not null references notifications(id) on delete cascade,
  device_token_id uuid not null references device_tokens(id) on delete cascade,
  delivered       boolean not null default false,
  error           text,
  attempted_at    timestamptz not null default now(),
  unique (notification_id, device_token_id)
);

create index idx_deliveries_notification on notification_deliveries(notification_id);


-- Register = upsert that REACTIVATES. Call on every app launch, not just
-- first login. Never overwrites another device's row.
create or replace function register_device_token(
  p_token       text,
  p_platform    text default null,
  p_device_name text default null
)
returns uuid language plpgsql security definer set search_path = public as $$
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


create or replace function deactivate_device_token(p_token text)
returns void language sql security definer set search_path = public as $$
  update device_tokens set is_active = false
  where token = p_token and user_id = auth.uid();
$$;


-- The ONLY query the push sender should use.
create or replace function get_active_tokens(p_user_id uuid)
returns table (token text, platform text)
language sql stable security definer set search_path = public as $$
  select d.token, d.platform
  from device_tokens d
  join profiles p on p.id = d.user_id
  where d.user_id = p_user_id and d.is_active and p.is_active;
$$;


-- =====================================================================
-- 10. RLS HELPER FUNCTIONS
-- (`current_role` is a reserved word in Postgres — hence `app_role`)
-- =====================================================================

create or replace function app_role()
returns user_role language sql stable security definer set search_path = public as $$
  select role from profiles where id = auth.uid();
$$;

create or replace function is_super_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((select role = 'super_admin' from profiles where id = auth.uid()), false);
$$;

create or replace function owns_salon(p_salon_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from salons
    where id = p_salon_id and owner_id = auth.uid() and is_active
  );
$$;


-- =====================================================================
-- 11. ROW LEVEL SECURITY
-- =====================================================================

alter table profiles                enable row level security;
alter table salons                  enable row level security;
alter table salon_images            enable row level security;
alter table salon_holidays          enable row level security;
alter table service_categories      enable row level security;
alter table service_subcategories   enable row level security;
alter table services                enable row level security;
alter table staff                   enable row level security;
alter table languages               enable row level security;
alter table staff_services          enable row level security;
alter table staff_service_languages enable row level security;
alter table blocked_slots           enable row level security;
alter table bookings                enable row level security;
alter table booking_services        enable row level security;
alter table notifications           enable row level security;
alter table device_tokens           enable row level security;
alter table notification_deliveries enable row level security;

-- ---- profiles ----
create policy profiles_self_read on profiles
  for select using (id = auth.uid() or is_super_admin());
create policy profiles_self_update on profiles
  for update using (id = auth.uid());

-- ---- salons ----
-- Anyone (incl. logged-out browsing) may see live, completed salons.
create policy salons_public_read on salons
  for select using ((is_active and profile_completed) or owner_id = auth.uid() or is_super_admin());
-- Owners edit their own salon but can NEVER flip is_active — only the Super
-- Admin deactivates a salon, and deactivation is the only form of deletion.
create policy salons_owner_update on salons
  for update using (owner_id = auth.uid())
  with check (owner_id = auth.uid() and is_active = (select is_active from salons s where s.id = salons.id));

create policy salon_images_read on salon_images for select using (true);
create policy salon_images_owner_write on salon_images
  for all using (owns_salon(salon_id)) with check (owns_salon(salon_id));

create policy salon_holidays_read on salon_holidays for select using (true);
create policy salon_holidays_owner_write on salon_holidays
  for all using (owns_salon(salon_id)) with check (owns_salon(salon_id));

-- ---- catalog (super-admin curated) ----
create policy categories_read on service_categories
  for select using (is_active or is_super_admin());
create policy categories_admin_write on service_categories
  for all using (is_super_admin()) with check (is_super_admin());

create policy subcategories_read on service_subcategories
  for select using (is_active or is_super_admin());
create policy subcategories_admin_write on service_subcategories
  for all using (is_super_admin()) with check (is_super_admin());

-- ---- services ----
create policy services_public_read on services
  for select using (is_active or owns_salon(salon_id) or is_super_admin());
create policy services_owner_write on services
  for all using (owns_salon(salon_id)) with check (owns_salon(salon_id));

-- ---- staff ----
create policy staff_public_read on staff
  for select using (is_active or owns_salon(salon_id) or is_super_admin());
create policy staff_owner_write on staff
  for all using (owns_salon(salon_id)) with check (owns_salon(salon_id));

create policy languages_read on languages for select using (true);

create policy staff_services_read on staff_services for select using (true);
create policy staff_services_owner_write on staff_services
  for all using (exists (select 1 from staff s where s.id = staff_id and owns_salon(s.salon_id)))
  with check (exists (select 1 from staff s where s.id = staff_id and owns_salon(s.salon_id)));

create policy ssl_read on staff_service_languages for select using (true);
create policy ssl_owner_write on staff_service_languages
  for all using (exists (
    select 1 from staff_services ss join staff st on st.id = ss.staff_id
    where ss.id = staff_service_id and owns_salon(st.salon_id)))
  with check (exists (
    select 1 from staff_services ss join staff st on st.id = ss.staff_id
    where ss.id = staff_service_id and owns_salon(st.salon_id)));

-- ---- blocked_slots ----
create policy blocked_read on blocked_slots
  for select using (true);   -- the slot engine needs this for all booking clients
create policy blocked_owner_write on blocked_slots
  for all using (
    (staff_id is not null and exists (select 1 from staff s where s.id = staff_id and owns_salon(s.salon_id)))
    or (salon_id is not null and owns_salon(salon_id)))
  with check (
    (staff_id is not null and exists (select 1 from staff s where s.id = staff_id and owns_salon(s.salon_id)))
    or (salon_id is not null and owns_salon(salon_id)));

-- ---- bookings ----
-- A customer sees only their own. An owner sees every booking in their salon,
-- regardless of which app or QR code created it.
create policy bookings_read on bookings
  for select using (customer_id = auth.uid() or owns_salon(salon_id) or is_super_admin());
create policy bookings_owner_update on bookings
  for update using (owns_salon(salon_id)) with check (owns_salon(salon_id));
create policy bookings_customer_cancel on bookings
  for update using (customer_id = auth.uid()) with check (customer_id = auth.uid());
-- NOTE: no INSERT policy, on purpose. All clients create bookings through
-- create_booking() below, which validates availability atomically.

create policy booking_services_read on booking_services
  for select using (exists (
    select 1 from bookings b where b.id = booking_id
      and (b.customer_id = auth.uid() or owns_salon(b.salon_id) or is_super_admin())
  ));

-- ---- notifications / devices ----
create policy notifications_own on notifications
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy device_tokens_own on device_tokens
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy deliveries_own on notification_deliveries
  for select using (exists (
    select 1 from notifications n where n.id = notification_id and n.user_id = auth.uid()
  ));


-- =====================================================================
-- 12. THE SHARED SLOT ENGINE
-- Every booking client calls this. Do not reimplement it per app.
--   supabase.rpc('get_available_slots', { p_staff_id, p_date, p_duration_minutes })
-- Honours: salon hours, staff hours, salon holidays, staff blocks,
-- salon-wide blocks, and existing bookings.
-- =====================================================================

create or replace function get_available_slots(
  p_staff_id         uuid,
  p_date             date,
  p_duration_minutes int
)
returns table (slot_start timestamptz, slot_end timestamptz)
language plpgsql stable security definer set search_path = public as $$
declare
  v_salon    uuid;
  v_tz       text;
  v_interval int;
  v_hours    jsonb;
  v_dow      text;
  v_open     time;
  v_close    time;
  v_cursor   timestamptz;
  v_day_end  timestamptz;
  v_try_end  timestamptz;
begin
  select sl.id, sl.timezone, sl.slot_interval_minutes,
         coalesce(st.working_hours, sl.working_hours)
    into v_salon, v_tz, v_interval, v_hours
  from staff st
  join salons sl on sl.id = st.salon_id
  where st.id = p_staff_id
    and st.is_active
    and sl.is_active
    and sl.profile_completed;

  if v_tz is null then return; end if;                      -- unknown/inactive staff

  if exists (select 1 from salon_holidays
             where salon_id = v_salon and holiday_date = p_date) then
    return;                                                 -- salon closed
  end if;

  v_dow := lower(to_char(p_date, 'dy'));                    -- mon, tue, wed...
  if v_hours -> v_dow ->> 'open' is null then return; end if;  -- closed that day

  v_open  := (v_hours -> v_dow ->> 'open')::time;
  v_close := (v_hours -> v_dow ->> 'close')::time;

  v_cursor  := (p_date + v_open)  at time zone v_tz;
  v_day_end := (p_date + v_close) at time zone v_tz;

  while v_cursor + make_interval(mins => p_duration_minutes) <= v_day_end loop
    v_try_end := v_cursor + make_interval(mins => p_duration_minutes);

    if v_cursor > now()
       and not exists (
         select 1 from bookings b
         where b.staff_id = p_staff_id
           and b.status in ('pending', 'confirmed')
           and tstzrange(b.start_datetime, b.end_datetime) && tstzrange(v_cursor, v_try_end)
       )
       and not exists (
         select 1 from blocked_slots bs
         where (bs.staff_id = p_staff_id
                or (bs.staff_id is null and bs.salon_id = v_salon))
           and tstzrange(bs.start_datetime, bs.end_datetime) && tstzrange(v_cursor, v_try_end)
       )
    then
      slot_start := v_cursor;
      slot_end   := v_try_end;
      return next;
    end if;

    v_cursor := v_cursor + make_interval(mins => v_interval);
  end loop;
end $$;


-- =====================================================================
-- 13. ATOMIC BOOKING CREATION
-- The single write path for every booking client.
--   supabase.rpc('create_booking', {...})
-- Phone is OPTIONAL and phone_verified is never a precondition.
-- =====================================================================

create or replace function create_booking(
  p_salon_id       uuid,
  p_staff_id       uuid,
  p_service_ids    uuid[],
  p_start          timestamptz,
  p_customer_name  text,
  p_customer_phone text default null,
  p_source         booking_source default 'app',
  p_notes          text default null
)
returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_duration int;
  v_price    numeric(10,2);
  v_end      timestamptz;
  v_mode     approval_mode;
  v_status   booking_status;
  v_customer uuid := auth.uid();
  v_tz       text;
  v_booking  uuid;
begin
  select timezone, approval_mode into v_tz, v_mode
  from salons where id = p_salon_id and is_active;

  if v_tz is null then
    raise exception 'Salon not found or inactive';
  end if;

  if exists (
    select 1 from salon_holidays
    where salon_id = p_salon_id
      and holiday_date = (p_start at time zone v_tz)::date
  ) then
    raise exception 'Salon is closed on this date';
  end if;

  -- staff must actually offer every requested service, in this salon
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

  -- Per-staff duration/price override wins over the service default.
  select sum(coalesce(ss.duration_minutes, sv.duration_minutes)),
         sum(coalesce(ss.price_override,   sv.price))
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
    select 1 from get_available_slots(p_staff_id, (p_start at time zone v_tz)::date, v_duration) g
    where g.slot_start = p_start
  ) then
    raise exception 'Selected slot is no longer available';
  end if;

  -- A customer physically in the shop needs no remote approval step.
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

  insert into booking_services (booking_id, service_id, service_name, duration_minutes, price)
  select v_booking, sv.id, sv.name,
         coalesce(ss.duration_minutes, sv.duration_minutes),
         coalesce(ss.price_override,   sv.price)
  from services sv
  left join staff_services ss
    on ss.service_id = sv.id and ss.staff_id = p_staff_id and ss.is_active
  where sv.id = any(p_service_ids);

  return v_booking;
exception
  when exclusion_violation then
    raise exception 'That slot was just taken. Please pick another time.';
end $$;


-- =====================================================================
-- 14. QR FAST-REGISTRATION (walk-in web app)
-- The in-shop QR encodes:  https://walkin.yoursite.com/s/{qr_token}
-- Flow: scan -> instant web page -> name + phone -> OTP -> book. No install,
-- no password. Supabase phone OTP creates a real auth user, which is what
-- makes this the platform's only trustworthy source of customer numbers.
-- =====================================================================

create or replace function get_salon_by_qr(p_qr_token text)
returns table (
  id uuid, name text, description text,
  city text, timezone text, approval_mode approval_mode
)
language sql stable security definer set search_path = public as $$
  select s.id, s.name, s.description, s.city, s.timezone, s.approval_mode
  from salons s
  where s.qr_token = p_qr_token
    and s.is_active
    and s.profile_completed;
$$;


-- =====================================================================
-- 15. SEED THE FIRST SUPER ADMIN
-- Create the user in Supabase Auth (Dashboard > Authentication > Add user),
-- then promote it here. There is no self-service path to this role.
-- =====================================================================
-- update profiles set role = 'super_admin' where email = 'you@example.com';


-- =====================================================================
-- 16. IDENTITY MERGE (deferred — do not build in Phase 1, just don't block it)
-- A walk-in verified by OTP and an app customer may be the same human. Because
-- `profiles.phone` is not unique, both rows can coexist safely today.
-- When you do merge, the verified row wins the phone number, and bookings are
-- repointed to the surviving profile id. Keeping this deliberate (rather than
-- enforced by a constraint) avoids hard-failing a signup at 2am in production.
-- =====================================================================
--
-- Find likely duplicates:
--   select phone, array_agg(id) from profiles
--   where phone is not null and role = 'customer'
--   group by phone having count(*) > 1;
