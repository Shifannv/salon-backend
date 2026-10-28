"""Optional end date for admin-set salon plan offers."""

from pathlib import Path

from alembic import op

revision = "0050_plan_price_valid_until"
down_revision = "0049_trial_salon_plan_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0050_plan_price_valid_until.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    op.execute("alter table public.salon_plan_prices drop column if exists valid_until")
