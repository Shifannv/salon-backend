"""Booking no-show warnings: barber warning, customer reply, timed auto no-show."""

from pathlib import Path

from alembic import op

revision = "0070_booking_no_show_warnings"
down_revision = "0069_notification_audience"
branch_labels = None
depends_on = None

_PRIOR_GUARD = Path(__file__).resolve().parents[1] / "sql" / "0043_no_show_attendance_guards.sql"


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0070_booking_no_show_warnings.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for statement in _PRIOR_GUARD.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if "guard_no_show_attendance()\nRETURNS trigger" in statement:
            op.execute(statement)
    op.execute("DROP TABLE IF EXISTS public.booking_no_show_warnings")
