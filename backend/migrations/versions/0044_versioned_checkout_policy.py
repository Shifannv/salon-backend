"""Prepare explicit immutable checkout policy selection; activation is a separate release.

Existing booking values and historical payment snapshots are never rewritten.
"""

from pathlib import Path

from alembic import op

revision = "0044_versioned_checkout_policy"
down_revision = "0043_no_show_attendance_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = (Path(__file__).parents[1] / "sql/0044_versioned_checkout_policy.sql").read_text(encoding="utf-8")
    for statement in source.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Preserve policy snapshots; repair forward or select the legacy policy only for future bookings")
