"""invalid reply reason

Migration: 0003_invalid_reply_reason           Task: TASK-008
Store: postgres (pgvector/pgvector:pg16)       Phase: expand (1 of 1)
Purpose: a review reason for fields held because the model reply was still not valid
  JSON after one retry (US-00-010, REQ-046, ADR-0015).
Locks: ALTER TYPE ... ADD VALUE takes a brief lock on the type only; no table rewrite.
Rows: none changed on upgrade.
Index: none; the review queue index filters on status, not reason. The ledger now filters
  llm_calls on created_at >= LLM_BUDGET_SINCE (ADR-0014): no index, about 10^2 rows a day.
Retention / PII: no personal data.
Down: rows with invalid_reply become value_missing (still needs_review), then the type
  is rebuilt without the value; Down loses: the distinction between the two reasons.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_invalid_reply_reason"
down_revision: str | None = "0002_clause_pages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_VALUES = "'quote_not_found', 'clause_not_found', 'could_not_parse', 'value_missing'"


def upgrade() -> None:
    """Add invalid_reply to review_reason."""
    op.execute("ALTER TYPE review_reason ADD VALUE IF NOT EXISTS 'invalid_reply'")


def downgrade() -> None:
    """Map invalid_reply rows to value_missing and rebuild the type without it."""
    op.execute(
        "UPDATE extractions SET review_reason = 'value_missing' "
        "WHERE review_reason = 'invalid_reply'"
    )
    op.execute("ALTER TYPE review_reason RENAME TO review_reason_0003")
    op.execute(f"CREATE TYPE review_reason AS ENUM ({OLD_VALUES})")
    op.execute(
        "ALTER TABLE extractions ALTER COLUMN review_reason TYPE review_reason "
        "USING review_reason::text::review_reason"
    )
    op.execute("DROP TYPE review_reason_0003")
