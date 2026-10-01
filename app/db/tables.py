"""SQLAlchemy Core tables that mirror migration 0001 (review decision D4).

The migration is the source of truth; these definitions only give queries
typed column references. Tables are added here as each task starts using
them; columns the code does not touch yet are left out.
"""

from sqlalchemy import Column, DateTime, Enum, Integer, MetaData, String, Table, Text, Uuid, func

metadata = MetaData()

contract_type = Enum("lease", "vendor", "service", name="contract_type", create_type=False)

contracts = Table(
    "contracts",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("title", Text, nullable=False),
    Column("contract_type", contract_type, nullable=False),
    Column("source_filename", Text, nullable=False),
    Column("file_sha256", String(64), nullable=False, unique=True),
    Column("full_text", Text, nullable=False),
    Column("page_count", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

clauses = Table(
    "clauses",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("contract_id", Uuid, nullable=False),
    Column("clause_number", Text, nullable=False),
    Column("heading", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("position", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
