"""Salon menu categories and atomic, consecutive staff visits. Prepared only."""
from pathlib import Path

from alembic import op

revision = "0061_staff_service_visits"
down_revision = "0060_user_consents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0061_staff_service_visits.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("0061 retains booked itineraries; use a reviewed forward migration")
