"""Staff earnings: per-service staff, commission rule versions and append-only earnings (S1a).

Revision ID: 0054_staff_earnings
Revises: 0053_salon_payout_requests
Create Date: 2026-11-01

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0054_staff_earnings"
down_revision = "0053_salon_payout_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0054_staff_earnings.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Earnings are financial records: fix forward, or restore from a backup.
    raise RuntimeError(
        "0054 is forward-only: staff_earnings and staff_commission_rule_versions hold financial records "
        "and cannot be removed by a downgrade"
    )
