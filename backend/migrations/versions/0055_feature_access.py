"""Super-admin feature access: catalogue, Trial/Growth/Premium matrix, salon overrides, plan content.

Revision ID: 0055_feature_access
Revises: 0054_staff_earnings
Create Date: 2026-11-01

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0055_feature_access"
down_revision = "0054_staff_earnings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0055_feature_access.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for table in ("plan_tier_content", "salon_feature_overrides", "feature_plan_access", "feature_catalog"):
        op.execute(f"DROP TABLE IF EXISTS public.{table}")
