"""Prepared customer booking changes; explicit review and deployment required."""

from pathlib import Path

from alembic import op

revision = "0045_customer_booking_changes"
down_revision = "0044_versioned_checkout_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0045_customer_booking_changes.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Booking change history and financial obligations must be preserved; repair forward")
