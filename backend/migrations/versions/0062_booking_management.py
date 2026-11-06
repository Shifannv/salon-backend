"""Pay at Salon quotas, immediate cancellation and complete visit changes. Prepared only."""
from pathlib import Path

from alembic import op

revision = "0062_booking_management"
down_revision = "0061_staff_service_visits"
branch_labels = None
depends_on = None

def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0062_booking_management.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)

def downgrade() -> None:
    raise RuntimeError("Booking history and quota decisions are retained; use a reviewed forward migration")
