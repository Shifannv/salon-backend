"""Backend-only support messages, durable email outbox and rate-limit counters.

Revision ID: 0036_support_email_outbox
Revises: 0035_booking_checkout_safety
"""

from alembic import op

revision = "0036_support_email_outbox"
down_revision = "0035_booking_checkout_safety"
branch_labels = None
depends_on = None


def upgrade():
    for sql in (
        """create table public.support_tickets (
            id uuid primary key default gen_random_uuid(),
            customer_id uuid not null references public.profiles(id) on delete cascade,
            salon_id uuid references public.salons(id),
            subject text not null check (char_length(subject) between 1 and 200),
            status text not null default 'open' check (status in ('open','replied','closed')),
            created_at timestamptz not null default now(), updated_at timestamptz not null default now())""",
        """create table public.support_messages (
            id uuid primary key default gen_random_uuid(),
            ticket_id uuid not null references public.support_tickets(id) on delete cascade,
            author_id uuid references public.profiles(id) on delete set null,
            body text not null check (char_length(body) between 1 and 5000),
            created_at timestamptz not null default now())""",
        """create table public.email_events (
            id uuid primary key default gen_random_uuid(),
            user_id uuid references public.profiles(id) on delete cascade,
            event_key text not null unique, event_type text not null,
            recipient text not null, subject text not null, body text not null,
            status text not null default 'pending' check (status in ('pending','processing','sent','failed')),
            attempts integer not null default 0, provider_message_id text,
            last_error_code text, next_attempt_at timestamptz not null default now(),
            locked_at timestamptz, created_at timestamptz not null default now(), sent_at timestamptz)""",
        """create table public.api_rate_limits (
            bucket_hash text primary key, window_start timestamptz not null default now(),
            attempts integer not null default 1)""",
        "create index idx_support_customer_history on public.support_tickets(customer_id, created_at desc)",
        "create index idx_support_message_thread on public.support_messages(ticket_id, created_at)",
        "create index idx_email_pending on public.email_events(next_attempt_at) where status in ('pending','processing')",
        "create index idx_email_user_status on public.email_events(user_id, created_at desc)",
        """create or replace function public.enqueue_booking_email() returns trigger
            language plpgsql security definer set search_path = public as $$
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
            end $$""",
        "create trigger booking_email_outbox after insert or update on public.bookings for each row execute function public.enqueue_booking_email()",
        """create or replace function public.enqueue_verified_payment_receipt() returns trigger
            language plpgsql security definer set search_path = public as $$
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
            end $$""",
        "create trigger verified_payment_email after insert or update on public.booking_payments for each row execute function public.enqueue_verified_payment_receipt()",
        "revoke all on function public.enqueue_booking_email(), public.enqueue_verified_payment_receipt() from public, anon, authenticated",
    ):
        op.execute(sql)
    for table in ("support_tickets", "support_messages", "email_events", "api_rate_limits"):
        op.execute(f"alter table public.{table} enable row level security")
        op.execute(f"revoke all on public.{table} from public, anon, authenticated")
        op.execute(f"grant all on public.{table} to service_role")


def downgrade():
    op.execute("""do $$ begin
      if exists(select 1 from public.email_events) or exists(select 1 from public.support_tickets) then
        raise exception 'Support/email history exists; use a reviewed forward migration';
      end if;
    end $$""")
    for sql in (
        "drop trigger booking_email_outbox on public.bookings",
        "drop trigger verified_payment_email on public.booking_payments",
        "drop function public.enqueue_booking_email()",
        "drop function public.enqueue_verified_payment_receipt()",
        "drop table public.support_messages",
        "drop table public.support_tickets",
        "drop table public.email_events",
        "drop table public.api_rate_limits",
    ):
        op.execute(sql)
