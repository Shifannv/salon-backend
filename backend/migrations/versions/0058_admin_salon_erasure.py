"""Admin salon erasure: a tombstone table and the erase_salon(uuid) function.

Revision ID: 0058_admin_salon_erasure
Revises: 0057_payout_proof
Create Date: 2026-11-02

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0058_admin_salon_erasure"
down_revision = "0057_payout_proof"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0058_admin_salon_erasure.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.erase_salon(uuid)")
    # The tombstone table is kept: it is the only proof that an erased salon was erased.
