"""Prepared 60 day / 500 booking trial for new salons and admin-set per-salon plan prices."""

from pathlib import Path

from alembic import op

revision = "0049_trial_salon_plan_prices"
down_revision = "0048_support_billing_erasure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    source = Path(__file__).parents[1] / "sql" / "0049_trial_salon_plan_prices.sql"
    for statement in source.read_text(encoding="utf-8").split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Per-salon plan prices would be lost and trials already granted cannot be recalled; repair forward")
