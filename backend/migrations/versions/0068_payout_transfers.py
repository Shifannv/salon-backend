"""Automatic payout through Cashfree Payouts: transfers table and the money-safety guards."""

from pathlib import Path

from alembic import op

revision = "0068_payout_transfers"
down_revision = "0067_working_hours_breaks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).resolve().parents[1] / "sql" / "0068_payout_transfers.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade not supported: payout transfers are money records. Restore the previous "
        "guard_payout_request() from 0057_payout_proof.sql by hand if ever needed."
    )
