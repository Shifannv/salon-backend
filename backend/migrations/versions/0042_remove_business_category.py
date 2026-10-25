"""Remove only the obsolete salon business-profile category.

Prepared for review; not authorized for remote execution. Service catalog taxonomy
and service category/subcategory display fields are deliberately unchanged.
"""

from pathlib import Path

from alembic import op

revision = "0042_remove_business_category"
down_revision = "0041_salon_photo_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0042_remove_business_category.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Business category values were permanently removed; use a reviewed forward repair")
