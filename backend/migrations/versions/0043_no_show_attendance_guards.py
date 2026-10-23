"""Enforce explicit no-show reasons and the ten-minute grace period.

Prepared only. This revision does not enable the U08 financial policy or reconcile
remote migration history. Review the complete release chain before any deployment.
"""

from pathlib import Path

from alembic import op

revision = "0043_no_show_attendance_guards"
down_revision = "0042_remove_business_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0043_no_show_attendance_guards.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Keep no-show reason/grace protections; use a reviewed forward repair")
