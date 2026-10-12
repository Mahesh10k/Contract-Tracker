"""users for login

Migration: 0004_users                          Task: TASK-013
Store: postgres (pgvector/pgvector:pg16)       Phase: expand (1 of 1)
Purpose: accounts for the login page (ADR-0017). Users are created from the command line,
  there is no sign-up.
Locks: CREATE TABLE takes no lock on existing tables.
Rows: none created; the first user comes from `make user`.
Index: the unique constraint on email is the lookup index (login reads by email).
Retention / PII: email addresses (personal data) and a salted scrypt password hash. A disabled
  account keeps its row. Remove a person's data by deleting the row.
Down: drops the table; Down loses: every account and its password hash.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_users"
down_revision: str | None = "0003_invalid_reply_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the users table."""
    op.execute(
        """
        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text NOT NULL,
            password_hash text NOT NULL,
            failed_attempts integer NOT NULL DEFAULT 0,
            locked_until timestamptz,
            disabled_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_users_email UNIQUE (email),
            CONSTRAINT ck_users_email_lower CHECK (email = lower(email)),
            CONSTRAINT ck_users_failed_attempts CHECK (failed_attempts >= 0)
        )
        """
    )


def downgrade() -> None:
    """Drop the users table."""
    op.execute("DROP TABLE users")
