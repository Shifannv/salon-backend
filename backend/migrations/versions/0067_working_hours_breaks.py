"""Add breaks support to working_hours and enforce them in slot functions."""

from pathlib import Path

from alembic import op

revision = "0067_working_hours_breaks"
down_revision = "0066_notification_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0067_working_hours_breaks.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade not supported: recreate the previous function versions from "
        "0045_customer_booking_changes.sql, 0052_booking_window_30_days.sql, and "
        "0062_booking_management.sql manually."
    )
