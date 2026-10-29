"""Owner finance cash book: expenses, cash adjustments and day closes (append-only)."""

from pathlib import Path

from alembic import op

revision = "0051_owner_finance_cashbook"
down_revision = "0050_plan_price_valid_until"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0051_owner_finance_cashbook.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Money records are never dropped by a rollback: fix forward, or restore from a backup.
    raise RuntimeError(
        "0051 is forward-only: salon_expenses, salon_cash_adjustments and salon_day_closes hold "
        "financial records and cannot be removed by a downgrade"
    )
