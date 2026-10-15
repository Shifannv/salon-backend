"""Adopt legacy cancellation text columns; never erase values or drop columns.

Prepared only. Erasure is implemented by the reviewed account-deletion adapter,
which clears both fields BEFORE erase_profile_references detaches customer IDs.
"""

from pathlib import Path

from alembic import op

revision = "0038_cancellation_compatibility"
down_revision = "0037_customer_processing_charge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0038_cancellation_compatibility.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Irreversible compatibility adoption: preserve columns/values; use a reviewed forward revision")
