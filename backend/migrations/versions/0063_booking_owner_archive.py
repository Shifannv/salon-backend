"""Let salon staff hide finished bookings from their list. Prepared only."""
from pathlib import Path

from alembic import op

revision = "0063_booking_owner_archive"
down_revision = "0062_booking_management"
branch_labels = None
depends_on = None

def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0063_booking_owner_archive.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)

def downgrade() -> None:
    raise RuntimeError("Archive markers are retained; use a reviewed forward migration")
