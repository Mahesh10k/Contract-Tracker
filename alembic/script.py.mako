"""${message}

Migration: ${up_revision}_<name>               Task: <TASK-ID>
Store: postgres                                Phase: expand | migrate | contract (n of m)
Purpose: <one sentence: what changes and why>
Locks: <lock taken, on which table, how long; lock_timeout>
Rows: <table size and backfill plan, or "none">
Index: <one entry per new WHERE or ORDER BY shape, or "none: no new shape">
Retention / PII: <window or none>; <personal-data fields or "no PII">
Down: <what it reverts>; Down loses: <DATA LOST, or "nothing">; tested in: make migrate-verify

Revises: ${down_revision | comma,n}    Created: ${create_date}
Hand-written (decision D4): write upgrade and downgrade below; never autogenerate.
"""

from collections.abc import Sequence

from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this migration."""
    ${upgrades if upgrades else "op.execute(\"SELECT 1\")  # replace with the real change"}


def downgrade() -> None:
    """Undo this migration. It must work; `make migrate-down` proves it."""
    ${downgrades if downgrades else "op.execute(\"SELECT 1\")  # replace with the real undo"}
