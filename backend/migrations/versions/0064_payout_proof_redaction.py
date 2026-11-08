"""Payout proof redaction: remove proof files a set time after an owner deletes their account.

Revision ID: 0064_payout_proof_redaction
Revises: 0063_booking_owner_archive
Create Date: 2026-11-08

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0064_payout_proof_redaction"
down_revision = "0063_booking_owner_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0064_payout_proof_redaction.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Redacted files cannot be restored; removal needs a separate reviewed operation.
    raise RuntimeError("0064 is irreversible: redacted proof files cannot be restored")
