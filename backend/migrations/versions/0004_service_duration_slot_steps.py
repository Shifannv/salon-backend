"""Generate availability slots by service duration.

Revision ID: 0004_service_duration_slot_steps
Revises: 0003_google_oauth_metadata
Create Date: 2026-08-10
"""

from alembic import op

revision = "0004_service_duration_slot_steps"
down_revision = "0003_google_oauth_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make slot starts advance by selected service duration."""

    op.execute(
        """
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
          v_hours    jsonb;
          v_dow      text;
          v_open     time;
          v_close    time;
          v_cursor   timestamptz;
          v_day_end  timestamptz;
          v_try_end  timestamptz;
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

          if exists (select 1 from salon_holidays
                     where salon_id = v_salon and holiday_date = p_date) then
            return;
          end if;

          v_dow := lower(to_char(p_date, 'dy'));
          if v_hours -> v_dow ->> 'open' is null then return; end if;

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
              slot_end   := v_try_end;
              return next;
            end if;

            v_cursor := v_cursor + make_interval(mins => p_duration_minutes);
          end loop;
        end $$;
        """
    )


def downgrade() -> None:
    """Restore baseline slot-interval stepping."""

    op.execute(
        """
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

          if v_tz is null then return; end if;

          if exists (select 1 from salon_holidays
                     where salon_id = v_salon and holiday_date = p_date) then
            return;
          end if;

          v_dow := lower(to_char(p_date, 'dy'));
          if v_hours -> v_dow ->> 'open' is null then return; end if;

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
              slot_end   := v_try_end;
              return next;
            end if;

            v_cursor := v_cursor + make_interval(mins => v_interval);
          end loop;
        end $$;
        """
    )
