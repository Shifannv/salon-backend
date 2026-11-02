"""Payout proof: payment details, private proof files, corrections and an audit trail.

Revision ID: 0057_payout_proof
Revises: 0056_platform_payment_settings
Create Date: 2026-11-02

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0057_payout_proof"
down_revision = "0056_platform_payment_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0057_payout_proof.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Payment proof is financial evidence: fix forward, or restore from a backup.
    raise RuntimeError(
        "0057 is forward-only: payout payments, proofs, corrections and the audit trail are "
        "financial records and cannot be removed by a downgrade"
    )
