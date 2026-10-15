"""Codify FastAPI-only business access on explicitly named application objects.

Existing managed extension ACLs, server rights and future-object defaults remain.
No positive grants, role creation or signup-trigger DDL.
"""

from pathlib import Path

from alembic import op

revision = "0040_fastapi_only_access"
down_revision = "0039_promotion_search_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).parents[1] / "sql" / "0040_fastapi_only_access.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Irreversible client-access restriction: never restore broad grants; use a reviewed forward revision")
