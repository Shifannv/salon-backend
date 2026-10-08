"""Require super admin approval before salon publication or daily business.

Existing active, completed salons retain approval for compatibility. New salons
start pending. This revision has NOT been applied to the configured database.
Revision ID: 0015_salon_admin_approval
Revises: 0014_repair_cancel_reason
"""

from alembic import op

revision = "0015_salon_admin_approval"
down_revision = "0014_repair_cancel_reason"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
create type salon_approval_status as enum ('pending', 'approved', 'rejected');
        """
    )
    op.execute(
        """
alter table salons
  add column approval_status salon_approval_status not null default 'pending',
  add column approved_at timestamptz,
  add column approved_by uuid references profiles(id),
  add column rejection_reason text;
        """
    )
    op.execute(
        """
create index idx_salons_approval_status on salons(approval_status);
        """
    )
    op.execute(
        """
-- Compatibility backfill, not a human review. approved_by remains null.
update salons set approval_status = 'approved', approved_at = now()
where profile_completed and is_active;
        """
    )
    op.execute(
        """
drop policy salons_public_read on salons;
        """
    )
    op.execute(
        """
create policy salons_public_read on salons for select using (
  (is_active and profile_completed and approval_status = 'approved')
  or owner_id = auth.uid() or is_super_admin()
);
        """
    )
    op.execute(
        """
-- RLS permits owner profile edits, so protect privileged columns independently.
create function guard_salon_approval() returns trigger
language plpgsql set search_path = public as $$
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
        """
    )
    op.execute(
        """
create trigger salons_guard_approval before insert or update on salons
for each row execute function guard_salon_approval();
        """
    )
    op.execute(
        """
-- Serialize booking creation against review/deactivation and reject RPC bypasses.
create function guard_booking_salon_approval() returns trigger
language plpgsql set search_path = public as $$
begin
  perform 1 from salons where id = new.salon_id
    and is_active and profile_completed and approval_status = 'approved' for share;
  if not found then
    raise exception 'Salon is not approved for business' using errcode = '42501';
  end if;
  return new;
end $$;
        """
    )
    op.execute(
        """
create trigger bookings_guard_salon_approval before insert on bookings
for each row execute function guard_booking_salon_approval();
        """
    )
    op.execute(
        """
create policy services_approval_read on services as restrictive for select using (
  exists (select 1 from salons sl where sl.id = services.salon_id
    and ((sl.is_active and sl.profile_completed and sl.approval_status = 'approved')
         or sl.owner_id = auth.uid() or is_super_admin()))
);
        """
    )
    op.execute(
        """
create policy staff_approval_read on staff as restrictive for select using (
  exists (select 1 from salons sl where sl.id = staff.salon_id
    and ((sl.is_active and sl.profile_completed and sl.approval_status = 'approved')
         or sl.owner_id = auth.uid() or is_super_admin()))
);
        """
    )
    op.execute(
        """
create policy salon_images_approval_read on salon_images as restrictive for select using (
  exists (select 1 from salons sl where sl.id = salon_images.salon_id
    and ((sl.is_active and sl.profile_completed and sl.approval_status = 'approved')
         or sl.owner_id = auth.uid() or is_super_admin()))
);
        """
    )
    op.execute(
        """
create policy salon_holidays_approval_read on salon_holidays as restrictive for select using (
  exists (select 1 from salons sl where sl.id = salon_holidays.salon_id
    and ((sl.is_active and sl.profile_completed and sl.approval_status = 'approved')
         or sl.owner_id = auth.uid() or is_super_admin()))
);
        """
    )
    _replace_functions(approved=True)


def downgrade() -> None:
    _replace_functions(approved=False)
    op.execute(
        """
drop trigger bookings_guard_salon_approval on bookings;
        """
    )
    op.execute(
        """
drop function guard_booking_salon_approval();
        """
    )
    op.execute(
        """
drop trigger salons_guard_approval on salons;
        """
    )
    op.execute(
        """
drop function guard_salon_approval();
        """
    )
    op.execute(
        """
drop policy services_approval_read on services;
        """
    )
    op.execute(
        """
drop policy staff_approval_read on staff;
        """
    )
    op.execute(
        """
drop policy salon_images_approval_read on salon_images;
        """
    )
    op.execute(
        """
drop policy salon_holidays_approval_read on salon_holidays;
        """
    )
    op.execute(
        """
drop policy salons_public_read on salons;
        """
    )
    op.execute(
        """
create policy salons_public_read on salons for select using (
  (is_active and profile_completed) or owner_id = auth.uid() or is_super_admin()
);
        """
    )
    op.execute(
        """
drop index idx_salons_approval_status;
        """
    )
    op.execute(
        """
alter table salons drop column rejection_reason, drop column approved_by,
  drop column approved_at, drop column approval_status;
        """
    )
    op.execute(
        """
drop type salon_approval_status;
        """
    )


def _replace_functions(*, approved: bool) -> None:
    if approved:
        op.execute(
            """
create or replace function get_available_slots(
          p_staff_id uuid,
          p_date date,
          p_duration_minutes int
        )
        returns table (slot_start timestamptz, slot_end timestamptz)
        language plpgsql stable security definer set search_path = public as $$
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
            and sl.profile_completed and sl.approval_status = 'approved';

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
                   and b.status in ('pending', 'confirmed')
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
            """
        )
        op.execute(
            """
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
    and s.profile_completed and s.approval_status = 'approved';
$$;
            """
        )
    else:
        op.execute(
            """
create or replace function get_available_slots(
          p_staff_id uuid,
          p_date date,
          p_duration_minutes int
        )
        returns table (slot_start timestamptz, slot_end timestamptz)
        language plpgsql stable security definer set search_path = public as $$
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
            and sl.profile_completed;

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
                   and b.status in ('pending', 'confirmed')
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
            """
        )
        op.execute(
            """
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
            """
        )
