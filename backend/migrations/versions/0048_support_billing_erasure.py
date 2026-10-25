"""Prepared versioned support retention and subscription-benefit privacy."""

from pathlib import Path

from alembic import op

revision = "0048_support_billing_erasure"
down_revision = "0047_booking_audit_erasure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0048_support_billing_erasure.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Erased support and benefit text cannot be recovered; repair forward")
