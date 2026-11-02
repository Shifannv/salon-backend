"""Super-admin payment settings: commission rate and base, minimum payout, per-salon commission.

Revision ID: 0056_platform_payment_settings
Revises: 0055_feature_access
Create Date: 2026-11-02

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0056_platform_payment_settings"
down_revision = "0055_feature_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0056_platform_payment_settings.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Commission policy is what payment snapshots refer to: fix forward, or restore from a backup.
    raise RuntimeError(
        "0056 is forward-only: platform_payment_settings and salon_commission_overrides hold the "
        "commission policy and cannot be removed by a downgrade"
    )
