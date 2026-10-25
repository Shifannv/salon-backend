"""Prepared privacy treatment for retained booking-change and finance audits."""

from pathlib import Path

from alembic import op

revision = "0047_booking_audit_erasure"
down_revision = "0046_u08_financial_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0047_booking_audit_erasure.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Erased personal data cannot be restored; repair forward")
