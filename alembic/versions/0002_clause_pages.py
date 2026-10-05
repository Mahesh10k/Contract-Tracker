"""clause pages

Migration: 0002_clause_pages                   Task: TASK-007
Store: postgres (pgvector/pgvector:pg16)       Phase: expand (1 of 1)
Purpose: record the first and last page each clause is printed on (US-00-009, REQ-037).
Locks: ADD COLUMN with no default and an ADD CONSTRAINT ... NOT VALID are metadata-only
  in Postgres 16; VALIDATE takes SHARE UPDATE EXCLUSIVE, which allows reads and writes.
Rows: about 10^3 clauses; existing rows keep their text and get NULL pages, never a
  guess (AC-US-00-009-3).
Index: none; pages are only displayed, never filtered on.
Retention / PII: no personal data.
Down: drops the check and both columns; Down loses: page numbers only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_clause_pages"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECK = "chk_clauses_pages_ordered"


def upgrade() -> None:
    """Add nullable page columns and a check that they come together and in order."""
    op.add_column("clauses", sa.Column("first_page", sa.Integer(), nullable=True))
    op.add_column("clauses", sa.Column("last_page", sa.Integer(), nullable=True))
    op.execute(
        f"ALTER TABLE clauses ADD CONSTRAINT {CHECK} CHECK ("
        "(first_page IS NULL AND last_page IS NULL) "
        "OR (first_page >= 1 AND last_page >= first_page)) NOT VALID"
    )
    op.execute(f"ALTER TABLE clauses VALIDATE CONSTRAINT {CHECK}")
    op.execute(
        "COMMENT ON COLUMN clauses.first_page IS "
        "'Page the clause heading is printed on, from 1; NULL for clauses loaded before 0002.'"
    )
    op.execute(
        "COMMENT ON COLUMN clauses.last_page IS "
        "'Page of the last line of the clause body; equals first_page unless it crosses a page.'"
    )


def downgrade() -> None:
    """Remove the check and the two columns."""
    op.execute(f"ALTER TABLE clauses DROP CONSTRAINT {CHECK}")
    op.drop_column("clauses", "last_page")
    op.drop_column("clauses", "first_page")
