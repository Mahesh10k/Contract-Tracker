"""SQLAlchemy Core tables that mirror migration 0001 (review decision D4).

The migration is the source of truth; these definitions only give queries
typed column references. Tables are added here as each task starts using
them; columns the code does not touch yet are left out.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    func,
)

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
    Column("first_page", Integer),
    Column("last_page", Integer),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

llm_calls = Table(
    "llm_calls",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("run_id", Uuid, nullable=False),
    Column("prompt_name", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("model_id", Text, nullable=False),
    Column("cache_key", String(64), nullable=False),
    Column("cache_hit", Boolean, nullable=False),
    Column("input_tokens", Integer, nullable=False),
    Column("output_tokens", Integer, nullable=False),
    Column("cost_usd", Numeric(10, 6), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

extraction_field = Enum(
    "parties",
    "effective_date",
    "term",
    "auto_renewal",
    "notice_period",
    "payment_terms",
    "escalation",
    "liability_cap",
    "termination_rights",
    "governing_law",
    name="extraction_field",
    create_type=False,
)
extraction_status = Enum(
    "accepted", "needs_review", "corrected", name="extraction_status", create_type=False
)
review_reason = Enum(
    "quote_not_found",
    "clause_not_found",
    "could_not_parse",
    "value_missing",
    "invalid_reply",
    name="review_reason",
    create_type=False,
)

extractions = Table(
    "extractions",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=func.gen_random_uuid()),
    Column("contract_id", Uuid, nullable=False),
    Column("field_name", extraction_field, nullable=False),
    Column("value_text", Text),
    Column("quote", Text),
    Column("cited_clause_number", Text),
    Column("clause_id", Uuid),
    Column("status", extraction_status, nullable=False),
    Column("review_reason", review_reason),
    Column("corrected_value", Text),
    Column("corrected_at", DateTime(timezone=True)),
    Column("prompt_version", Text, nullable=False),
    Column("model_id", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
