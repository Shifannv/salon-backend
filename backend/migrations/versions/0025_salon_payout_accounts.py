"""Add owner-only salon payout accounts (UPI / bank) in a private table.

``salons`` is publicly readable by customers, so payout details live in their own
table with RLS and no browser-facing grants. Access is only through the backend,
which masks the account number in every response.

Revision ID: 0025_salon_payout_accounts
Revises: 0024_secure_new_user_role
Create Date: 2026-10-11 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025_salon_payout_accounts"
down_revision: str | Sequence[str] | None = "0024_secure_new_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the private payout table with RLS, an owner policy and format checks."""
    op.execute(
        """
        create table public.salon_payout_accounts (
          salon_id            uuid primary key references public.salons(id) on delete cascade,
          account_holder_name text not null check (char_length(account_holder_name) between 2 and 100),
          upi_id              text,
          bank_name           text check (bank_name is null or char_length(bank_name) <= 100),
          bank_account_number text,
          ifsc                text,
          created_at          timestamptz not null default now(),
          updated_at          timestamptz not null default now(),
          constraint ck_payout_has_destination check (
            upi_id is not null or (bank_account_number is not null and ifsc is not null)
          ),
          constraint ck_payout_upi_format check (
            upi_id is null or upi_id ~ '^[A-Za-z0-9._-]{2,255}@[A-Za-z]{2,64}$'
          ),
          constraint ck_payout_account_format check (
            bank_account_number is null or bank_account_number ~ '^[0-9]{9,18}$'
          ),
          constraint ck_payout_ifsc_format check (
            ifsc is null or ifsc ~ '^[A-Z]{4}0[A-Z0-9]{6}$'
          )
        )
        """
    )
    op.execute(
        "create trigger t_salon_payout_accounts_updated before update on public.salon_payout_accounts "
        "for each row execute function set_updated_at()"
    )
    op.execute("alter table public.salon_payout_accounts enable row level security")
    # Owner-only: no public read, unlike salons/services. owns_salon() checks
    # salons.owner_id = auth.uid() and is_active (see 001_supabase_schema.sql).
    op.execute(
        """
        create policy salon_payout_accounts_owner on public.salon_payout_accounts
          for all using (public.owns_salon(salon_id)) with check (public.owns_salon(salon_id))
        """
    )
    # Supabase auto-grants new tables to anon/authenticated. Payout data is reached
    # only through the backend, so withdraw every browser-facing privilege.
    op.execute("revoke all on public.salon_payout_accounts from public, anon, authenticated")
    op.execute("grant all on public.salon_payout_accounts to postgres, service_role")


def downgrade() -> None:
    """Drop the payout table (and its policy, trigger and constraints)."""
    op.execute("drop table if exists public.salon_payout_accounts")
