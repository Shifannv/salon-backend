"""Date of birth and guardian approval for 13 to 17 year old customers.

Revision ID: 0065_age_and_guardian_consent
Revises: 0064_payout_proof_redaction
Create Date: 2026-11-08

Prepared only. Review and approve the migration chain before deployment.
"""

from pathlib import Path

from alembic import op

revision = "0065_age_and_guardian_consent"
down_revision = "0064_payout_proof_redaction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = (Path(__file__).resolve().parents[1] / "sql" / "0065_age_and_guardian_consent.sql").read_text(encoding="utf-8")
    for statement in sql.split("\n-- statement --\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Dates of birth and guardian approvals are consent evidence; removal needs a reviewed operation.
    raise RuntimeError("0065 is irreversible: retain age and guardian consent evidence")
