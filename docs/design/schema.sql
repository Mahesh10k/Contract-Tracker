-- ContractTracker: database schema (PostgreSQL 16 with pgvector)
-- Written by data-model beside docs/design/data-model.md, which gives the
-- reason for every table, column, index and constraint below.
--
-- Applies in one transaction to an empty database: the extension and enum
-- types first, then tables in foreign-key order, each followed by its
-- comments and indexes. Use it as the first migration; every change after the
-- first release is its own migration (db-migration), never an edit to this
-- file.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE contract_type AS ENUM ('lease', 'vendor', 'service');
CREATE TYPE extraction_field AS ENUM (
    'parties', 'effective_date', 'term', 'auto_renewal', 'notice_period',
    'payment_terms', 'escalation', 'liability_cap', 'termination_rights', 'governing_law'
);
CREATE TYPE extraction_status AS ENUM ('accepted', 'needs_review', 'corrected');
CREATE TYPE review_reason AS ENUM ('quote_not_found', 'clause_not_found', 'could_not_parse', 'value_missing');
CREATE TYPE obligation_kind AS ENUM ('expiry', 'notice_deadline', 'renewal', 'escalation', 'payment');
CREATE TYPE reminder_status AS ENUM ('pending', 'sending', 'sent', 'skipped');

-- contracts: one loaded contract PDF and its extracted text.
-- Serves US-00-001, US-00-002, US-00-003, US-00-007
CREATE TABLE contracts (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    title text NOT NULL,
    contract_type contract_type NOT NULL,
    source_filename text NOT NULL,
    file_sha256 char(64) NOT NULL,
    full_text text NOT NULL,
    page_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT contracts_pkey PRIMARY KEY (id),
    CONSTRAINT chk_contracts_title_not_blank CHECK (btrim(title) <> '' AND length(title) <= 300),
    CONSTRAINT chk_contracts_file_sha256_hex CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_contracts_full_text_not_blank CHECK (btrim(full_text) <> ''),
    CONSTRAINT chk_contracts_page_count_positive CHECK (page_count > 0)
);
COMMENT ON TABLE contracts IS 'One loaded contract PDF and its extracted text. Serves US-00-001, US-00-002, US-00-003, US-00-007.';
COMMENT ON COLUMN contracts.id IS 'Surrogate key; the id in the contract page URL and in every child row.';
COMMENT ON COLUMN contracts.title IS 'Contract title shown in the list and cited in answers as the contract name.';
COMMENT ON COLUMN contracts.contract_type IS 'lease, vendor or service; from truth.json for generated contracts, from the required type picker on the upload form (Q-026).';
COMMENT ON COLUMN contracts.source_filename IS 'File name as uploaded, shown to the owner.';
COMMENT ON COLUMN contracts.file_sha256 IS 'SHA-256 of the PDF bytes, lowercase hex; detects a second load of the same file.';
COMMENT ON COLUMN contracts.full_text IS 'All text pypdf read from the PDF, before clause splitting.';
COMMENT ON COLUMN contracts.page_count IS 'Pages in the PDF.';
COMMENT ON COLUMN contracts.created_at IS 'When the contract was loaded.';
COMMENT ON COLUMN contracts.updated_at IS 'Last change to this row.';
-- A second load of the same file is refused (AC-US-00-001-5).
CREATE UNIQUE INDEX uq_contracts_file_sha256 ON contracts (file_sha256);

-- clauses: one numbered clause of a contract, with its search vectors.
-- Serves US-00-001, US-00-002, US-00-004, US-00-005
CREATE TABLE clauses (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    contract_id uuid NOT NULL REFERENCES contracts (id) ON DELETE CASCADE,
    clause_number text NOT NULL,
    heading text NOT NULL,
    body text NOT NULL,
    position integer NOT NULL,
    first_page integer,
    last_page integer,
    embedding vector(384),
    embedding_model text,
    search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', heading || ' ' || body)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT clauses_pkey PRIMARY KEY (id),
    CONSTRAINT chk_clauses_number_shape CHECK (clause_number ~ '^[0-9]+(\.[0-9]+)*$'),
    CONSTRAINT chk_clauses_body_not_blank CHECK (btrim(body) <> ''),
    CONSTRAINT chk_clauses_position_positive CHECK (position > 0),
    CONSTRAINT chk_clauses_pages_ordered CHECK (
        (first_page IS NULL AND last_page IS NULL) OR (first_page >= 1 AND last_page >= first_page)
    ),
    CONSTRAINT chk_clauses_embedding_with_model CHECK ((embedding IS NULL) = (embedding_model IS NULL))
);
COMMENT ON TABLE clauses IS 'One numbered clause of a contract, with its vector and full-text search fields. Serves US-00-001, US-00-002, US-00-004, US-00-005.';
COMMENT ON COLUMN clauses.id IS 'Surrogate key; the clause an extraction quote or an answer citation points to.';
COMMENT ON COLUMN clauses.contract_id IS 'The contract this clause belongs to.';
COMMENT ON COLUMN clauses.clause_number IS 'Number as printed in the contract, such as 7.2; the clause part of a [contract, clause] citation.';
COMMENT ON COLUMN clauses.first_page IS 'Page the clause heading is printed on, from 1; NULL for clauses loaded before migration 0002 (US-00-009).';
COMMENT ON COLUMN clauses.last_page IS 'Page of the last line of the clause body; equals first_page unless it crosses a page.';
COMMENT ON COLUMN clauses.heading IS 'Heading printed after the number, such as Termination; may be empty when the contract prints none.';
COMMENT ON COLUMN clauses.body IS 'Clause text; quotes are checked against it after normalisation.';
COMMENT ON COLUMN clauses.position IS 'Order of the clause in the contract, from 1.';
COMMENT ON COLUMN clauses.embedding IS 'bge-small-en-v1.5 vector of heading and body; null until the clause is embedded.';
COMMENT ON COLUMN clauses.embedding_model IS 'Model name and version that produced embedding; null exactly when embedding is null.';
COMMENT ON COLUMN clauses.search_tsv IS 'English full-text vector of heading and body, generated by Postgres.';
COMMENT ON COLUMN clauses.created_at IS 'When the clause was stored.';
COMMENT ON COLUMN clauses.updated_at IS 'Last change to this row, such as embedding.';
-- One clause per number in a contract; serves "give me clause 7.2" (AC-US-00-001-3) and the contract_id FK.
CREATE UNIQUE INDEX uq_clauses_contract_number ON clauses (contract_id, clause_number);
-- Clauses in reading order for the contract view.
CREATE UNIQUE INDEX uq_clauses_contract_position ON clauses (contract_id, position);
-- Target of the composite FK from extractions, so a cited clause must belong to the same contract.
CREATE UNIQUE INDEX uq_clauses_contract_id_id ON clauses (contract_id, id);
-- Vector half of hybrid search: nearest clauses by cosine distance (AC-US-00-004-3).
CREATE INDEX idx_clauses_embedding_hnsw ON clauses USING hnsw (embedding vector_cosine_ops);
-- Full-text half of hybrid search (AC-US-00-004-2).
CREATE INDEX idx_clauses_search_tsv ON clauses USING gin (search_tsv);

-- extractions: one extracted field of one contract, with its quote and review state.
-- Serves US-00-002, US-00-003, US-00-007, US-00-008, US-02-001
CREATE TABLE extractions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    contract_id uuid NOT NULL REFERENCES contracts (id) ON DELETE CASCADE,
    field_name extraction_field NOT NULL,
    value_text text,
    quote text,
    cited_clause_number text,
    clause_id uuid,
    status extraction_status NOT NULL,
    review_reason review_reason,
    corrected_value text,
    corrected_at timestamptz,
    prompt_version text NOT NULL,
    model_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT extractions_pkey PRIMARY KEY (id),
    CONSTRAINT fk_extractions_contract_clause FOREIGN KEY (contract_id, clause_id)
        REFERENCES clauses (contract_id, id) ON DELETE CASCADE,
    CONSTRAINT chk_extractions_review_reason_matches CHECK ((status = 'needs_review') = (review_reason IS NOT NULL)),
    CONSTRAINT chk_extractions_correction_complete CHECK (
        (status = 'corrected') = (corrected_value IS NOT NULL AND corrected_at IS NOT NULL)
    ),
    CONSTRAINT chk_extractions_accepted_grounded CHECK (
        status <> 'accepted' OR (value_text IS NOT NULL AND quote IS NOT NULL AND clause_id IS NOT NULL)
    )
);
COMMENT ON TABLE extractions IS 'One extracted field of one contract, with its quote, cited clause and review state. Serves US-00-002, US-00-003, US-00-007, US-00-008, US-02-001.';
COMMENT ON COLUMN extractions.id IS 'Surrogate key; the id the review page posts a correction to.';
COMMENT ON COLUMN extractions.contract_id IS 'The contract the field was extracted from.';
COMMENT ON COLUMN extractions.field_name IS 'Which of the 10 fields this row holds.';
COMMENT ON COLUMN extractions.value_text IS 'Value as the model returned it, text as written in the contract; dates and durations are not normalised here.';
COMMENT ON COLUMN extractions.quote IS 'Exact contract text the model gave as the source of value_text.';
COMMENT ON COLUMN extractions.cited_clause_number IS 'Clause number exactly as the model cited it, kept even when no such clause exists.';
COMMENT ON COLUMN extractions.clause_id IS 'Clause the model cited for the quote; null when the cited number does not exist in this contract.';
COMMENT ON COLUMN extractions.status IS 'accepted, needs_review or corrected.';
COMMENT ON COLUMN extractions.review_reason IS 'Why the field is held; set exactly when status is needs_review.';
COMMENT ON COLUMN extractions.corrected_value IS 'Value the owner entered in the review queue; wins over value_text and survives re-extraction.';
COMMENT ON COLUMN extractions.corrected_at IS 'When the owner saved corrected_value.';
COMMENT ON COLUMN extractions.prompt_version IS 'Prompt registry version that produced this row.';
COMMENT ON COLUMN extractions.model_id IS 'Exact model id that produced this row, such as anthropic/claude-haiku-4.5.';
COMMENT ON COLUMN extractions.created_at IS 'When the field was first extracted.';
COMMENT ON COLUMN extractions.updated_at IS 'Last change to this row.';
-- One row per field per contract; re-extraction upserts on it; also the contract_id FK index.
CREATE UNIQUE INDEX uq_extractions_contract_field ON extractions (contract_id, field_name);
-- Target of the composite FK from obligations, so a date's source field belongs to the same contract.
CREATE UNIQUE INDEX uq_extractions_contract_id_id ON extractions (contract_id, id);
-- FK index for the composite clause reference.
CREATE INDEX idx_extractions_contract_clause ON extractions (contract_id, clause_id);
-- The review queue page: held fields, oldest first (AC-US-00-008-1).
CREATE INDEX idx_extractions_needs_review ON extractions (created_at) WHERE status = 'needs_review';

-- obligations: one dated duty computed in code from an extracted field.
-- Serves US-00-003, US-00-006, US-00-007
CREATE TABLE obligations (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    contract_id uuid NOT NULL REFERENCES contracts (id) ON DELETE CASCADE,
    source_extraction_id uuid NOT NULL,
    kind obligation_kind NOT NULL,
    due_on date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT obligations_pkey PRIMARY KEY (id),
    CONSTRAINT fk_obligations_contract_extraction FOREIGN KEY (contract_id, source_extraction_id)
        REFERENCES extractions (contract_id, id) ON DELETE CASCADE
);
COMMENT ON TABLE obligations IS 'One dated duty computed in code from an extracted field. Serves US-00-003, US-00-006, US-00-007.';
COMMENT ON COLUMN obligations.id IS 'Surrogate key; the obligation a reminder is sent for.';
COMMENT ON COLUMN obligations.contract_id IS 'The contract the duty comes from.';
COMMENT ON COLUMN obligations.source_extraction_id IS 'The extracted field the date is cited to (for expiry: term; notice: notice_period); its clause is the citation. Any correction recomputes every obligation of the contract.';
COMMENT ON COLUMN obligations.kind IS 'expiry, notice_deadline, renewal, escalation or payment.';
COMMENT ON COLUMN obligations.due_on IS 'Calendar date of the duty, computed by python-dateutil, never by the model.';
COMMENT ON COLUMN obligations.created_at IS 'When the date was first computed.';
COMMENT ON COLUMN obligations.updated_at IS 'Last change to this row.';
-- Recompute upserts on it so unchanged dates keep their reminders; also the contract_id FK index.
CREATE UNIQUE INDEX uq_obligations_contract_kind_due ON obligations (contract_id, kind, due_on);
-- At most one expiry, notice deadline and renewal per contract, even if a recompute misses a delete.
CREATE UNIQUE INDEX uq_obligations_contract_single_kind ON obligations (contract_id, kind) WHERE kind IN ('expiry', 'notice_deadline', 'renewal');
-- FK index for the composite reference to the source field.
CREATE INDEX idx_obligations_contract_source ON obligations (contract_id, source_extraction_id);
-- The deadlines page: upcoming dates soonest first (AC-US-00-007-3).
CREATE INDEX idx_obligations_due_on ON obligations (due_on);

-- reminders: one planned email for one obligation at one lead time.
-- Serves US-00-006
CREATE TABLE reminders (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    obligation_id uuid NOT NULL REFERENCES obligations (id) ON DELETE CASCADE,
    lead_days integer NOT NULL,
    send_on date NOT NULL,
    status reminder_status NOT NULL DEFAULT 'pending',
    sent_at timestamptz,
    recipient text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT reminders_pkey PRIMARY KEY (id),
    CONSTRAINT chk_reminders_lead_days_positive CHECK (lead_days > 0),
    CONSTRAINT chk_reminders_sent_complete CHECK ((status = 'sent') = (sent_at IS NOT NULL)),
    CONSTRAINT chk_reminders_recipient_when_sending CHECK (status NOT IN ('sending', 'sent') OR recipient IS NOT NULL),
    CONSTRAINT chk_reminders_recipient_shape CHECK (recipient IS NULL OR recipient ~ '^[^@[:space:]]+@[^@[:space:]]+$')
);
COMMENT ON TABLE reminders IS 'One planned email for one obligation at one lead time. Serves US-00-006.';
COMMENT ON COLUMN reminders.id IS 'Surrogate key.';
COMMENT ON COLUMN reminders.obligation_id IS 'The obligation this reminder is about.';
COMMENT ON COLUMN reminders.lead_days IS 'Days before due_on the email is due: 60, 30 or 7 by default (Q-029).';
COMMENT ON COLUMN reminders.send_on IS 'obligations.due_on minus lead_days.';
COMMENT ON COLUMN reminders.status IS 'pending, then sending just before the SMTP call, then sent; back to pending if SMTP fails; skipped when a closer reminder for the same obligation is due on the same run. A row left in sending after a crash is never resent automatically.';
COMMENT ON COLUMN reminders.sent_at IS 'When the email was handed to MailHog.';
COMMENT ON COLUMN reminders.recipient IS 'Address the email went to, copied from REMINDER_TO at send time. [personal data]';
COMMENT ON COLUMN reminders.created_at IS 'When the reminder was planned.';
COMMENT ON COLUMN reminders.updated_at IS 'Last change to this row.';
-- One reminder per obligation per lead time, so a second run sends nothing twice (AC-US-00-006-3); also the FK index.
CREATE UNIQUE INDEX uq_reminders_obligation_lead ON reminders (obligation_id, lead_days);
-- make remind: pending reminders due on or before today (catch-up, AC-US-00-006-4).
CREATE INDEX idx_reminders_pending_send_on ON reminders (send_on) WHERE status = 'pending';

-- llm_calls: one model call or cache replay, with tokens and cost, for the budget stop.
-- Serves US-00-002, US-00-004, US-02-003
CREATE TABLE llm_calls (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL,
    prompt_name text NOT NULL,
    prompt_version text NOT NULL,
    model_id text NOT NULL,
    cache_key char(64) NOT NULL,
    cache_hit boolean NOT NULL,
    input_tokens integer NOT NULL,
    output_tokens integer NOT NULL,
    cost_usd numeric(10,6) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT llm_calls_pkey PRIMARY KEY (id),
    CONSTRAINT chk_llm_calls_tokens_non_negative CHECK (input_tokens >= 0 AND output_tokens >= 0),
    CONSTRAINT chk_llm_calls_cost_non_negative CHECK (cost_usd >= 0),
    CONSTRAINT chk_llm_calls_cache_hit_free CHECK (NOT cache_hit OR cost_usd = 0),
    CONSTRAINT chk_llm_calls_live_call_costed CHECK (cache_hit OR cost_usd > 0),
    CONSTRAINT chk_llm_calls_cache_key_hex CHECK (cache_key ~ '^[0-9a-f]{64}$')
);
COMMENT ON TABLE llm_calls IS 'One model call or cache replay, with tokens and cost; the gateway sums it for the USD 9 stop. Serves US-00-002, US-00-004, US-02-003.';
COMMENT ON COLUMN llm_calls.id IS 'Surrogate key.';
COMMENT ON COLUMN llm_calls.run_id IS 'One id per command run (an eval-live run, an upload); groups the calls whose spend that run prints.';
COMMENT ON COLUMN llm_calls.prompt_name IS 'Registry name of the prompt, such as extract_fields or answer_question.';
COMMENT ON COLUMN llm_calls.prompt_version IS 'Registry version of the prompt.';
COMMENT ON COLUMN llm_calls.model_id IS 'Exact model id called.';
COMMENT ON COLUMN llm_calls.cache_key IS 'SHA-256 of prompt version, model and full request body, lowercase hex; the reply cache file name.';
COMMENT ON COLUMN llm_calls.cache_hit IS 'True when the reply came from the disk cache and no network call was made.';
COMMENT ON COLUMN llm_calls.input_tokens IS 'Input tokens reported by OpenRouter; 0 on a cache hit.';
COMMENT ON COLUMN llm_calls.output_tokens IS 'Output tokens reported by OpenRouter; 0 on a cache hit.';
COMMENT ON COLUMN llm_calls.cost_usd IS 'Cost in US dollars reported by OpenRouter, or computed from tokens and the price table when OpenRouter omits it; 0 only on a cache hit.';
COMMENT ON COLUMN llm_calls.created_at IS 'When the call was made.';
-- eval-live prints the spend of its own run (AC-US-02-003-3).
CREATE INDEX idx_llm_calls_run_id ON llm_calls (run_id);

COMMIT;
