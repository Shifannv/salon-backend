"""Payout-account hardening: audit trail, SQL masking, bank-triple CHECK.

* ``created_by``/``updated_by`` plus the shared ``set_audit_actor`` trigger, so a changed
  payout destination is attributable.
* ``salon_payout_account_history``: append-only, written by trigger, stores the last four
  digits of an account number only, so history never duplicates the full value.
* ``salon_payout_account_masked`` (security definer) returns ``right(number, 4)`` so the
  full account number never has to leave Postgres on a read path.
* ``ck_payout_bank_triple``: account number and IFSC are all-or-nothing, and ``bank_name``
  may only accompany them.
* ``bank_account_fingerprint``: reserved for future duplicate detection. It is NOT
  populated yet; a bare hash of a 9-18 digit number is brute-forceable, so it needs a keyed
  HMAC with a key that lives outside the database. Plaintext-at-rest is a known, deferred gap.

Revision ID: 0027_payout_account_audit
Revises: 0026_booking_payments
Create Date: 2026-10-11 19:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027_payout_account_audit"
down_revision: str | Sequence[str] | None = "0026_booking_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _sql(*statements: str) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    """Add audit columns, history, masking function and the bank-triple CHECK."""

    _sql(
        """
        alter table public.salon_payout_accounts
          add column if not exists created_by uuid references public.profiles(id),
          add column if not exists updated_by uuid references public.profiles(id),
          add column if not exists bank_account_fingerprint text
        """,
        "drop trigger if exists t_salon_payout_accounts_audit on public.salon_payout_accounts",
        """
        create trigger t_salon_payout_accounts_audit
          before insert or update on public.salon_payout_accounts
          for each row execute function set_audit_actor()
        """,
        # Repair rows the new CHECK would reject: a stray IFSC/bank name without an account
        # number, or an account number without an IFSC, was never a usable bank destination
        # (ck_payout_has_destination guarantees such a row still has a UPI ID).
        """
        update public.salon_payout_accounts
        set ifsc = null, bank_name = null
        where bank_account_number is null and (ifsc is not null or bank_name is not null)
        """,
        """
        update public.salon_payout_accounts
        set bank_account_number = null, bank_name = null
        where ifsc is null and bank_account_number is not null
        """,
        "alter table public.salon_payout_accounts drop constraint if exists ck_payout_bank_triple",
        """
        alter table public.salon_payout_accounts add constraint ck_payout_bank_triple check (
          (bank_account_number is null and ifsc is null and bank_name is null)
          or (bank_account_number is not null and ifsc is not null)
        )
        """,
    )

    _sql(
        """
        create table if not exists public.salon_payout_account_history (
          id             uuid primary key default gen_random_uuid(),
          salon_id       uuid not null references public.salons(id) on delete cascade,
          changed_by     uuid references public.profiles(id),
          changed_at     timestamptz not null default now(),
          action         text not null check (action in ('created', 'updated')),
          changed_fields text[] not null default '{}',
          before_state   jsonb,
          after_state    jsonb not null
        )
        """,
        """
        create index if not exists idx_salon_payout_history_salon
          on public.salon_payout_account_history(salon_id, changed_at desc)
        """,
        # The only projection of a payout row that ever reaches history or the API.
        """
        create or replace function public.payout_account_snapshot(r public.salon_payout_accounts)
        returns jsonb language sql immutable set search_path = public as $$
          select jsonb_build_object(
            'account_holder_name', r.account_holder_name,
            'upi_id', r.upi_id,
            'bank_name', r.bank_name,
            'ifsc', r.ifsc,
            'bank_account_last4', right(r.bank_account_number, 4)
          )
        $$
        """,
        """
        create or replace function public.tg_salon_payout_account_history()
        returns trigger language plpgsql set search_path = public as $$
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
        end $$
        """,
        "drop trigger if exists t_salon_payout_accounts_history on public.salon_payout_accounts",
        """
        create trigger t_salon_payout_accounts_history
          after insert or update on public.salon_payout_accounts
          for each row execute function public.tg_salon_payout_account_history()
        """,
        # Masked read: the full number is projected to its last four digits inside Postgres.
        """
        create or replace function public.salon_payout_account_masked(p_salon_id uuid)
        returns table (
          account_holder_name text,
          upi_id              text,
          bank_name           text,
          bank_account_last4  text,
          ifsc                text,
          created_at          timestamptz,
          updated_at          timestamptz
        ) language sql stable security definer set search_path = public as $$
          select p.account_holder_name, p.upi_id, p.bank_name,
                 right(p.bank_account_number, 4), p.ifsc, p.created_at, p.updated_at
          from public.salon_payout_accounts p
          where p.salon_id = p_salon_id
        $$
        """,
        "revoke all on function public.salon_payout_account_masked(uuid) from public, anon, authenticated",
        "grant execute on function public.salon_payout_account_masked(uuid) to postgres, service_role",
        "alter table public.salon_payout_account_history enable row level security",
        "drop policy if exists salon_payout_history_owner_read on public.salon_payout_account_history",
        """
        create policy salon_payout_history_owner_read on public.salon_payout_account_history
          for select using (public.owns_salon(salon_id))
        """,
        "revoke all on public.salon_payout_account_history from public, anon, authenticated",
        "grant all on public.salon_payout_account_history to postgres, service_role",
    )


def downgrade() -> None:
    """Drop history, masking and audit additions. The audit history is lost."""

    _sql(
        "drop trigger if exists t_salon_payout_accounts_history on public.salon_payout_accounts",
        "drop table if exists public.salon_payout_account_history",
        "drop function if exists public.tg_salon_payout_account_history()",
        "drop function if exists public.payout_account_snapshot(public.salon_payout_accounts)",
        "drop function if exists public.salon_payout_account_masked(uuid)",
        "alter table public.salon_payout_accounts drop constraint if exists ck_payout_bank_triple",
        "drop trigger if exists t_salon_payout_accounts_audit on public.salon_payout_accounts",
        """
        alter table public.salon_payout_accounts
          drop column if exists bank_account_fingerprint,
          drop column if exists updated_by,
          drop column if exists created_by
        """,
    )
