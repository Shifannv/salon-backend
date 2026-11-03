"""Consent records: terms, privacy, "13 or older" and marketing, per user, newest row wins.

Revision ID: 0060_user_consents
Revises: 0059_payout_account_encryption
Create Date: 2026-11-03

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0060_user_consents"
down_revision = "0059_payout_account_encryption"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0060_user_consents.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Consent records are evidence; removal needs a separate reviewed operation.
    raise RuntimeError("0060 is irreversible: retain consent evidence and use a reviewed forward migration")
