# Entity relationship diagram: ContractTracker

PostgreSQL 16 with pgvector. 6 tables, 6 relationships. `llm_calls` has no relationship: it is an append-only ledger keyed by cache key, read only as a sum.

## Diagram

```mermaid
erDiagram
    contracts ||--o{ clauses : "is split into"
    contracts ||--o{ extractions : "has fields"
    clauses |o--o{ extractions : "is quoted by"
    contracts ||--o{ obligations : "creates"
    extractions ||--o{ obligations : "dates come from"
    obligations ||--o{ reminders : "is reminded by"
    contracts {
        uuid id PK
        text title
        contract_type contract_type "lease, vendor, service"
        text source_filename
        char file_sha256 UK "duplicate check"
        text full_text
        integer page_count
        timestamptz created_at
        timestamptz updated_at
    }
    clauses {
        uuid id PK
        uuid contract_id FK
        text clause_number "such as 7.2"
        text heading
        text body
        integer position
        vector embedding "384 dims, bge-small"
        text embedding_model
        tsvector search_tsv "generated"
        timestamptz created_at
        timestamptz updated_at
    }
    extractions {
        uuid id PK
        uuid contract_id FK
        extraction_field field_name "one of 10"
        text value_text "as written"
        text quote
        text cited_clause_number "as the model cited it"
        uuid clause_id FK "same contract"
        extraction_status status
        review_reason review_reason
        text corrected_value "wins over value_text"
        timestamptz corrected_at
        text prompt_version
        text model_id
        timestamptz created_at
        timestamptz updated_at
    }
    obligations {
        uuid id PK
        uuid contract_id FK
        uuid source_extraction_id FK
        obligation_kind kind
        date due_on "computed in code"
        timestamptz created_at
        timestamptz updated_at
    }
    reminders {
        uuid id PK
        uuid obligation_id FK
        integer lead_days "30 or 7"
        date send_on
        reminder_status status "pending, sending, sent, skipped"
        timestamptz sent_at
        text recipient "personal data"
        timestamptz created_at
        timestamptz updated_at
    }
    llm_calls {
        uuid id PK
        uuid run_id "one command run"
        text prompt_name
        text prompt_version
        text model_id
        char cache_key
        boolean cache_hit
        integer input_tokens
        integer output_tokens
        numeric cost_usd
        timestamptz created_at
    }
```

## Relationships

| From | | To | Meaning |
| --- | --- | --- | --- |
| contracts | one-to-many | clauses | A contract is split into numbered clauses; deleting the contract removes them (CASCADE). |
| contracts | one-to-many | extractions | Each contract has its 10 fields; they go with the contract (CASCADE). |
| clauses | zero-or-one to many | extractions | A field's quote cites one clause of the same contract, enforced by the composite key; null when the cited number does not exist. |
| contracts | one-to-many | obligations | A contract's dated duties; they go with the contract (CASCADE). |
| extractions | one-to-many | obligations | Each date is cited to one field of the same contract (composite key); any correction recomputes all of the contract's dates, and a removed field removes its dates (CASCADE). |
| obligations | one-to-many | reminders | Each obligation gets a 30-day and a 7-day reminder; a removed date must never be emailed (CASCADE). |
