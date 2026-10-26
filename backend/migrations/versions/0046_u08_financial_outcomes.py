"""Prepared immutable terminal policy snapshots and manual finance controls."""

from pathlib import Path

from alembic import op

revision = "0046_u08_financial_outcomes"
down_revision = "0045_customer_booking_changes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0046_u08_financial_outcomes.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Financial obligations and audit history are retained; repair forward")
