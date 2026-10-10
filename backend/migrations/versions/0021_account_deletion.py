"""Account deletion: verification challenges, durable erasure ledger, erasure helper.

Reviewed deploy step only; never run from API startup. Requires 0020 first.

Downgrade restores the audit trigger and drops the new objects. Re-adding NOT NULL
to salons.owner_id / booking_action_requests.requested_by fails if any erased
account left NULL rows behind; that is intentional (erased data cannot be restored).
"""

from alembic import op

revision = "0021_account_deletion"
down_revision = "0020_media_reference_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        create table account_deletion_challenges (
          id uuid primary key default gen_random_uuid(),
          user_id uuid not null references profiles(id) on delete cascade,
          purpose text not null default 'account_deletion'
            check (purpose = 'account_deletion'),
          channel text not null check (channel in ('email', 'phone')),
          contact_hash text not null,
          status text not null default 'sent'
            check (status in ('sent', 'verified', 'consumed', 'expired')),
          attempts integer not null default 0 check (attempts >= 0),
          max_attempts integer not null default 5 check (max_attempts > 0),
          resend_count integer not null default 0 check (resend_count >= 0),
          last_sent_at timestamptz not null default now(),
          expires_at timestamptz not null,
          verified_at timestamptz,
          confirmation_hash text,
          confirmation_expires_at timestamptz,
          consumed_at timestamptz,
          created_at timestamptz not null default now()
        );
        create unique index uq_account_deletion_challenge_live
          on account_deletion_challenges (user_id)
          where status in ('sent', 'verified');
        alter table account_deletion_challenges enable row level security;

        create table account_deletion_requests (
          id uuid primary key default gen_random_uuid(),
          user_id uuid,
          role text not null,
          salon_id uuid,
          salon_name text,
          salon_city text,
          status text not null default 'pending'
            check (status in ('pending', 'processing', 'completed', 'failed')),
          step_state jsonb not null default '{}'::jsonb,
          media_keys jsonb not null default '[]'::jsonb,
          attempts integer not null default 0 check (attempts >= 0),
          next_attempt_at timestamptz not null default now(),
          last_error_code text,
          requested_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          completed_at timestamptz
        );
        create unique index uq_account_deletion_request_open
          on account_deletion_requests (user_id)
          where status <> 'completed';
        create index idx_account_deletion_requests_due
          on account_deletion_requests (status, next_attempt_at)
          where status in ('pending', 'processing', 'failed');
        create index idx_account_deletion_requests_requested
          on account_deletion_requests (requested_at desc);
        alter table account_deletion_requests enable row level security;

        alter table salons alter column owner_id drop not null;
        alter table booking_action_requests alter column requested_by drop not null;
    """)
    op.execute("""
        do $$
        declare c record;
        begin
          for c in
            select conname from pg_constraint
            where conrelid = 'public.bookings'::regclass and contype = 'c'
              and pg_get_constraintdef(oid) like '%customer_id IS NOT NULL%manual_walkin%'
          loop
            execute format('alter table bookings drop constraint %I', c.conname);
          end loop;
        end $$;
        alter table bookings add constraint bookings_customer_or_walkin_check
          check (customer_id is not null or source = 'manual_walkin'
                 or customer_name = 'Deleted customer');
    """)
    op.execute("""
        create or replace function set_audit_actor()
        returns trigger language plpgsql as $$
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
    """)
    op.execute("""
        create function erase_profile_references(p_user uuid) returns integer
        language plpgsql security invoker set search_path = public, pg_catalog as $$
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
              and c.confdeltype = 'a'
              and array_length(c.conkey, 1) = 1
          loop
            execute format('update %s set %I = null where %I = $1', fk.tbl, fk.col, fk.col)
              using p_user;
            get diagnostics n = row_count;
            touched := touched + n;
          end loop;
          return touched;
        end $$;
    """)
    op.execute("""
        revoke execute on function erase_profile_references(uuid)
          from public, anon, authenticated;
    """)


def downgrade() -> None:
    op.execute("""
        alter table bookings drop constraint if exists bookings_customer_or_walkin_check;
        alter table bookings add check (customer_id is not null or source = 'manual_walkin');
    """)
    op.execute("drop function if exists erase_profile_references(uuid);")
    op.execute("""
        create or replace function set_audit_actor()
        returns trigger language plpgsql as $$
        begin
          if tg_op = 'INSERT' then
            new.created_by := coalesce(new.created_by, auth.uid());
            new.updated_by := coalesce(new.updated_by, auth.uid());
          else
            new.updated_by := coalesce(auth.uid(), old.updated_by);
            new.created_by := old.created_by;
          end if;
          return new;
        end $$;
    """)
    op.execute("""
        alter table booking_action_requests alter column requested_by set not null;
        alter table salons alter column owner_id set not null;
        drop table if exists account_deletion_requests;
        drop table if exists account_deletion_challenges;
    """)
