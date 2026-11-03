"""Bank account number encrypted at rest: last-four column, widened format check, masking functions.

Revision ID: 0059_payout_account_encryption
Revises: 0058_admin_salon_erasure
Create Date: 2026-11-03

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0059_payout_account_encryption"
down_revision = "0058_admin_salon_erasure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0059_payout_account_encryption.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Encrypted numbers cannot be turned back into digits here, so refuse rather than lose them.
    op.execute(
        """
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM public.salon_payout_accounts WHERE bank_account_number LIKE 'enc:%') THEN
            RAISE EXCEPTION 'Encrypted payout accounts exist; decrypt them with scripts/encrypt_payout_accounts.py --decrypt first';
          END IF;
        END $$
        """
    )
    # Put the 0027 masking functions back before the column they now read disappears.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.payout_account_snapshot(r public.salon_payout_accounts)
        RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path = public AS $$
          SELECT jsonb_build_object(
            'account_holder_name', r.account_holder_name, 'upi_id', r.upi_id,
            'bank_name', r.bank_name, 'ifsc', r.ifsc,
            'bank_account_last4', right(r.bank_account_number, 4))
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.salon_payout_account_masked(p_salon_id uuid)
        RETURNS TABLE (account_holder_name text, upi_id text, bank_name text, bank_account_last4 text,
                       ifsc text, created_at timestamptz, updated_at timestamptz)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
          SELECT p.account_holder_name, p.upi_id, p.bank_name, right(p.bank_account_number, 4),
                 p.ifsc, p.created_at, p.updated_at
          FROM public.salon_payout_accounts p WHERE p.salon_id = p_salon_id
        $$
        """
    )
    op.execute("ALTER TABLE public.salon_payout_accounts DROP CONSTRAINT IF EXISTS ck_payout_encrypted_has_last4")
    op.execute("ALTER TABLE public.salon_payout_accounts DROP CONSTRAINT IF EXISTS ck_payout_last4_format")
    op.execute("ALTER TABLE public.salon_payout_accounts DROP CONSTRAINT IF EXISTS ck_payout_account_format")
    op.execute(
        "ALTER TABLE public.salon_payout_accounts ADD CONSTRAINT ck_payout_account_format "
        "CHECK (bank_account_number IS NULL OR bank_account_number ~ '^[0-9]{9,18}$')"
    )
    op.execute("ALTER TABLE public.salon_payout_accounts DROP COLUMN IF EXISTS bank_account_last4")
