"""Owner wallet payout requests: ask for a payout, admin pays it by hand (forward-only)."""

from pathlib import Path

from alembic import op

revision = "0053_salon_payout_requests"
down_revision = "0052_booking_window_30_days"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0053_salon_payout_requests.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Money records are never dropped by a rollback: fix forward, or restore from a backup.
    raise RuntimeError(
        "0053 is forward-only: salon_payout_requests holds financial records and cannot be "
        "removed by a downgrade"
    )
