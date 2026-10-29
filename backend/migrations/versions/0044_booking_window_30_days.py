"""Enforce the rolling 30-day customer booking window.

Revision ID: 0044_booking_window_30_days
Revises: 0043_no_show_attendance_guards
Create Date: 2026-10-29

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op


revision = "0044_booking_window_30_days"
down_revision = "0043_no_show_attendance_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Install the reviewed booking-window function replacements."""

    sql = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "0044_booking_window_30_days.sql"
    ).read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    """Require an explicit reviewed function rollback."""

    raise RuntimeError("Keep the booking window; use a reviewed forward repair")
