"""Add booking action requests, payment preference, and notification outbox.

Revision ID: 0013_booking_action_requests
Revises: 0012_booking_delay
"""

from alembic import op

revision = "0013_booking_action_requests"
down_revision = "0012_booking_delay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        alter table bookings
          add column if not exists payment_preference text;

        alter table salon_holidays
          add column if not exists reason text;

        alter table bookings
          add constraint bookings_payment_preference_check
          check (payment_preference is null or payment_preference = 'pay_at_salon');

        create or replace function guard_booking_against_closure()
        returns trigger language plpgsql set search_path = public as $$
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

        create trigger t_bookings_closure_guard
          before insert on bookings
          for each row execute function guard_booking_against_closure();

        create table booking_action_requests (
          id uuid primary key default gen_random_uuid(),
          booking_id uuid not null references bookings(id) on delete cascade,
          kind text not null check (kind in ('payment_confirmation', 'cancellation')),
          status text not null default 'pending'
            check (status in ('pending', 'resolved')),
          reason text check (reason is null or length(reason) <= 500),
          decision text check (
            decision is null or decision in (
              'received', 'not_received', 'approve', 'decline', 'invalidated'
            )
          ),
          decision_reason text check (
            decision_reason is null or length(decision_reason) <= 500
          ),
          requested_by uuid not null references profiles(id),
          resolved_by uuid references profiles(id),
          resolved_at timestamptz,
          created_by uuid references profiles(id),
          updated_by uuid references profiles(id),
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          check (
            (status = 'pending' and decision is null and resolved_by is null and resolved_at is null)
            or
            (status = 'resolved' and decision is not null and resolved_at is not null)
          ),
          check (
            decision is null
            or decision = 'invalidated'
            or (kind = 'payment_confirmation' and decision in ('received', 'not_received'))
            or (kind = 'cancellation' and decision in ('approve', 'decline'))
          ),
          check (
            decision is distinct from 'decline'
            or (decision_reason is not null and length(trim(decision_reason)) > 0)
          )
        );

        create unique index uq_booking_action_requests_pending
          on booking_action_requests (booking_id, kind)
          where status = 'pending';
        create index idx_booking_action_requests_booking
          on booking_action_requests (booking_id, kind, created_at desc);
        create index idx_booking_action_requests_pending
          on booking_action_requests (status, created_at);

        create trigger t_booking_action_requests_updated
          before update on booking_action_requests
          for each row execute function set_updated_at();
        create trigger t_booking_action_requests_audit
          before insert or update on booking_action_requests
          for each row execute function set_audit_actor();

        create table notification_outbox (
          id uuid primary key default gen_random_uuid(),
          notification_id uuid not null unique
            references notifications(id) on delete cascade,
          user_id uuid not null references profiles(id) on delete cascade,
          status text not null default 'pending'
            check (status in ('pending', 'processed')),
          attempts integer not null default 0 check (attempts >= 0),
          next_attempt_at timestamptz not null default now(),
          last_error text,
          processed_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        );

        create index idx_notification_outbox_pending
          on notification_outbox (next_attempt_at, created_at)
          where status = 'pending';
        create trigger t_notification_outbox_updated
          before update on notification_outbox
          for each row execute function set_updated_at();

        alter table booking_action_requests enable row level security;
        alter table notification_outbox enable row level security;

        create policy bookings_staff_read on bookings for select to authenticated
          using (
            exists (
              select 1 from staff access_staff
              where access_staff.salon_id = bookings.salon_id
                and access_staff.profile_id = auth.uid()
                and access_staff.is_active
            )
          );

        create policy booking_action_requests_read
          on booking_action_requests for select to authenticated
          using (
            exists (
              select 1
              from bookings b
              join salons s on s.id = b.salon_id
              where b.id = booking_action_requests.booking_id
                and (
                  b.customer_id = auth.uid()
                  or s.owner_id = auth.uid()
                  or exists (
                    select 1 from staff access_staff
                    where access_staff.salon_id = b.salon_id
                      and access_staff.profile_id = auth.uid()
                      and access_staff.is_active
                  )
                  or is_super_admin()
                )
            )
          );

        revoke all on booking_action_requests from anon, authenticated;
        grant select on booking_action_requests to authenticated;
        grant all on booking_action_requests to service_role;
        revoke all on notification_outbox from anon, authenticated;
        grant all on notification_outbox to service_role;

        alter table booking_action_requests replica identity full;
        alter publication supabase_realtime add table booking_action_requests;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        alter publication supabase_realtime drop table booking_action_requests;
        drop policy if exists bookings_staff_read on bookings;
        drop trigger if exists t_bookings_closure_guard on bookings;
        drop function if exists guard_booking_against_closure();
        drop table notification_outbox;
        drop table booking_action_requests;
        alter table bookings drop constraint if exists bookings_payment_preference_check;
        alter table bookings drop column if exists payment_preference;
        alter table salon_holidays drop column if exists reason;
        """
    )
