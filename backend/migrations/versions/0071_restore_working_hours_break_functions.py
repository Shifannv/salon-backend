"""Restore the 0067 working-hours break functions on drifted databases."""

from pathlib import Path

from alembic import op

revision = "0071_restore_working_hours_break_functions"
down_revision = "0070_booking_no_show_warnings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0071_restore_working_hours_break_functions.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is not supported: restoring drifted function bodies would reintroduce broken break checks."
    )