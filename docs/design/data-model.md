# Data model: ContractTracker

**Store:** PostgreSQL 16 with pgvector · **Tables:** 6 · **Columns:** 62 · **Indexes:** 17 · **Personal-data columns:** 1

This database holds the loaded contracts, their numbered clauses with search
vectors, the 10 extracted fields per contract, the dated obligations computed
from them, the reminder emails planned and sent, and a ledger of model calls
for the budget stop. The CLI, the FastAPI pages (ADR-0011), `make remind` and
the eval targets read and write it; one Postgres holds everything because
vectors and full-text must meet in one query (ADR-0005).

- Task: none (planning, before TASK-001)
- Serves: US-00-001 to US-00-008, US-02-001, US-02-003; REQ-001 to REQ-022, REQ-028
- ADRs: ADR-0003 (store choice), ADR-0004 (embeddings), ADR-0005 (hybrid search), ADR-0007 (dates), ADR-0009 (reply cache)
- Stores: postgres
- Companion files: `docs/design/schema.sql`, `docs/design/data-dictionary.csv`, `docs/design/erd.md`
- Author: Mahesh Pikki (git config user.name), 2026-10-01, status Draft, version v1

## 1. Why these stores

### PostgreSQL

**Holds:** contracts, clauses with their vectors and full-text fields, extractions, obligations, reminders and the model-call ledger.

Every criterion is relational: a quote must point at a clause of the same
contract, an obligation at the field it came from, a reminder at one
obligation. Hybrid search needs vector distance and full-text rank over the
same clause rows in one query. Volumes are tiny (10^2 to 10^3 rows a table).

| Considered | Why not |
| --- | --- |
| A separate vector store (Qdrant) | Splits clauses across two stores, so hybrid search becomes two queries and a merge in code; a few hundred vectors need no dedicated engine (ADR-0003). |
| SQLite with a vector extension | The brief fixes Postgres 16 with pgvector in Docker Compose. |

## 2. Entities: ownership and lifecycle

| Entity | Owner | Created by | Changed by | Ended by | Stories | PII | Retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| contract | ingestion module | upload page with a required type picker (Q-026), `ingest` CLI with type from truth.json (US-00-001) | none | no story deletes; a demo reset drops the database | US-00-001, US-00-007 | no | UNDEFINED |
| clause | ingestion module | clause splitter during ingestion (US-00-001) | embedding job (US-00-004) | cascade from contract | US-00-001, US-00-004 | no | with its contract |
| extraction | extraction module | extraction service (US-00-002) | quote check (US-00-002), date parser (US-00-003), review correction (US-00-008), re-extraction upsert | cascade from contract | US-00-002, US-00-003, US-00-008, US-02-001 | no | with its contract |
| obligation | dates module | date computation (US-00-003) | recompute of the whole contract after any extraction or correction (US-00-003, US-00-008) | cascade from contract or field; the contract-wide recompute deletes dates not in the new set and upserts the rest in one transaction | US-00-003, US-00-006, US-00-007 | no | with its contract |
| reminder | reminders module | `make remind` planning step (US-00-006) | `make remind` send step | cascade from obligation | US-00-006 | yes (recipient) | UNDEFINED |
| llm_call | LLM gateway | every gateway call, live or cached (US-00-002, US-00-004) | none (append only) | never deleted in this project | US-00-002, US-02-003 | no | UNDEFINED |

Not modelled: users and sessions, because login is a PRD non-goal; prompts, because the registry keeps them as versioned files in the repository (ADR-0008); the reply cache, because it is JSON files on disk (ADR-0009); golden Q&A questions, because they are an eval fixture file (US-02-002).

## 3. Relationships

| From | To | Cardinality | FK column | On delete | Why |
| --- | --- | --- | --- | --- | --- |
| contracts | clauses | one-to-many | clauses.contract_id | CASCADE | A clause has no meaning without its contract. |
| contracts | extractions | one-to-many | extractions.contract_id | CASCADE | Fields belong to one contract and die with it. |
| clauses | extractions | one-to-many, optional | extractions.(contract_id, clause_id) | CASCADE | The composite key makes a cited clause belong to the same contract; null when the model cited a clause number that does not exist. |
| contracts | obligations | one-to-many | obligations.contract_id | CASCADE | Dates die with their contract. |
| extractions | obligations | one-to-many | obligations.(contract_id, source_extraction_id) | CASCADE | The composite key keeps the source field in the same contract; a date without the field it is cited to cannot be shown. |
| obligations | reminders | one-to-many | reminders.obligation_id | CASCADE | A reminder for a date that no longer exists must never be sent. |

## 4. PostgreSQL tables

### `contracts`: Contracts (hot: no)

One loaded contract PDF and its extracted text.

Serves US-00-001, US-00-002, US-00-003, US-00-007. Expected volume: 18 generated contracts plus a few uploads (10^1), driven by the synthetic set (ADR-0006).

Column reasons are in `data-dictionary.csv` (Why column), one per column; the DDL is in `schema.sql`.

**Indexes**

- `uq_contracts_file_sha256`: unique on (file_sha256). Serves the duplicate check on load (AC-US-00-001-5).

**Constraints**

- `chk_contracts_title_not_blank`: refuses a blank or over-300-character title, which would leave a citation with no contract name.
- `chk_contracts_file_sha256_hex`: refuses a hash that is not 64 lowercase hex characters, which would defeat the duplicate check.
- `chk_contracts_full_text_not_blank`: refuses a contract with no text; the scanned-PDF case is rejected before insert (AC-US-00-001-4) and this is the backstop.
- `chk_contracts_page_count_positive`: refuses a zero-page record.

### `clauses`: Clauses (hot: no)

One numbered clause of a contract, with its vector and full-text search fields.

Serves US-00-001, US-00-002, US-00-004, US-00-005, US-00-009. Since migration 0002 each clause carries first_page and last_page (NULL for rows loaded before it); no index, since pages are only displayed. Expected volume: about 25 clauses per contract, about 450 rows (10^2 to 10^3).

**Indexes**

- `uq_clauses_contract_number`: unique on (contract_id, clause_number). Fetches clause 7.2 of a contract (AC-US-00-001-3) and covers the contract_id FK.
- `uq_clauses_contract_position`: unique on (contract_id, position). Reading order in the contract view (AC-US-00-007-2).
- `uq_clauses_contract_id_id`: unique on (contract_id, id). The target of the composite FK from extractions, so a quote cannot cite another contract's clause.
- `idx_clauses_embedding_hnsw`: HNSW on embedding with cosine distance. The vector half of hybrid search (AC-US-00-004-3) and the top-1 cosine floor (AC-US-00-005-1).
- `idx_clauses_search_tsv`: GIN on search_tsv. The full-text half of hybrid search (AC-US-00-004-2).

**Constraints**

- `chk_clauses_number_shape`: refuses a clause number that is not digits separated by dots, so citations always read like "7.2".
- `chk_clauses_body_not_blank`: refuses an empty clause, which retrieval could return with nothing to quote.
- `chk_clauses_position_positive`: refuses a zero or negative position.
- `chk_clauses_embedding_with_model`: refuses a vector without the model that made it, or the reverse (ADR-0004).
- `chk_clauses_pages_ordered`: pages come together and in order (first_page from 1, last_page not before it), or both are NULL (migration 0002).

### `extractions`: Extracted fields (hot: no)

One extracted field of one contract, with its quote, cited clause and review state.

Serves US-00-002, US-00-003, US-00-007, US-00-008, US-02-001. Expected volume: 10 per contract, about 180 rows (10^2).

**Indexes**

- `uq_extractions_contract_id_id`: unique on (contract_id, id). The target of the composite FK from obligations.
- `uq_extractions_contract_field`: unique on (contract_id, field_name). Re-extraction upserts on it, with `WHERE status <> 'corrected'` on the update so a correction survives (AC-US-00-008-3); covers the contract_id FK.
- `idx_extractions_contract_clause`: on (contract_id, clause_id). FK index for the composite clause reference.
- `idx_extractions_needs_review`: on (created_at) where status = 'needs_review'. The review queue (AC-US-00-008-1); the predicate must be repeated in the query.

**Constraints**

- `fk_extractions_contract_clause`: composite FK to clauses (contract_id, id); refuses a quote that cites a clause of another contract.
- `chk_extractions_accepted_grounded` and `fk_extractions_contract_clause` together mean an accepted field always cites a clause of its own contract.
- `chk_extractions_review_reason_matches`: refuses a held field without a reason, or a reason on a field that is not held (AC-US-00-008-1).
- `chk_extractions_correction_complete`: refuses status corrected without a corrected value and time, or a corrected value on another status.
- `chk_extractions_accepted_grounded`: refuses an accepted field with no value, quote or clause; an ungrounded field can only be needs_review (REQ-015).

### `obligations`: Obligations (hot: no)

One dated duty computed in code from an extracted field.

Serves US-00-003, US-00-006, US-00-007. Expected volume: monthly payments to term end dominate: about 36 per contract for a 3-year term, about 700 rows (10^2 to 10^3).

**Indexes**

- `uq_obligations_contract_kind_due`: unique on (contract_id, kind, due_on). Recompute upserts on it, so a date that did not change keeps its reminders and is not emailed twice; covers the contract_id FK.
- `uq_obligations_contract_single_kind`: unique on (contract_id, kind) where kind is expiry, notice_deadline or renewal. One of each per contract, even if a recompute misses a delete; the predicate is a constant list, so it is immutable.
- `idx_obligations_contract_source`: on (contract_id, source_extraction_id). FK index for the composite reference to the source field.
- `idx_obligations_due_on`: on (due_on). The deadlines page, soonest first (AC-US-00-007-3).

**Constraints**

- `fk_obligations_contract_extraction`: composite FK to extractions (contract_id, id); refuses a date whose source field belongs to another contract.
- No CHECK: dates are validated by the parser tests (ADR-0007).

Recompute rule: expiry depends on effective_date and term, the notice deadline on expiry and notice_period, payment and escalation dates on effective_date and expiry. So any extraction or correction recomputes every obligation of that contract in one transaction: delete the obligations not in the new set, then insert the new set with `ON CONFLICT DO NOTHING` on `uq_obligations_contract_kind_due`, so unchanged dates keep their reminders.

### `reminders`: Reminders (hot: no)

One planned email for one obligation at one lead time.

Serves US-00-006. Expected volume: 3 per obligation, about 2,100 rows (10^3).

**Indexes**

- `uq_reminders_obligation_lead`: unique on (obligation_id, lead_days). One email per obligation per lead time (AC-US-00-006-3); covers the FK.
- `idx_reminders_pending_send_on`: on (send_on) where status = 'pending'. `make remind` reads pending reminders with send_on on or before today (AC-US-00-006-4); the predicate must be repeated.

**Constraints**

- `chk_reminders_lead_days_positive`: refuses a zero or negative lead time.
- `chk_reminders_sent_complete`: refuses status sent without sent_at, or sent_at on another status.
- `chk_reminders_recipient_when_sending`: refuses a sending or sent row with no recipient.
- `chk_reminders_recipient_shape`: refuses a recipient that is not an email address.

Crash rule: the row is set to sending, and committed, before the SMTP call, then to sent after it; an SMTP error sets it back to pending. A row left in sending after a crash is never picked up again (the partial index reads pending only), so a crash can lose one email but never send one twice; `make remind` lists sending rows so the owner sees them.

Send rule: in one run, for one obligation, only the pending reminder with the smallest lead_days among those due is sent; the earlier ones become skipped. This makes AC-US-00-006-5 (one email for a deadline 3 days away at upload) and AC-US-00-006-4 (a missed 30-day reminder is still sent when the 7-day one is not yet due) both hold.

### `llm_calls`: Model call ledger (hot: no)

One model call or cache replay, with tokens and cost; the gateway sums it for the USD 9 stop.

Serves US-00-002, US-00-004, US-02-003. Expected volume: about 50 rows a live eval run, a few thousand rows over the project (10^3).

**Indexes**

- `idx_llm_calls_run_id`: on (run_id). The spend of one eval-live run (AC-US-02-003-3). The overall USD 9 check sums the whole table, at most a few thousand rows, with no index.

**Constraints**

- `chk_llm_calls_tokens_non_negative`: refuses negative token counts.
- `chk_llm_calls_cost_non_negative`: refuses a negative cost, which would hide spend from the stop.
- `chk_llm_calls_cache_hit_free`: refuses a cost on a cache hit.
- `chk_llm_calls_live_call_costed`: refuses a live call recorded at 0; when OpenRouter omits the cost the gateway computes it from tokens and the price table, so the stop never undercounts.
- `chk_llm_calls_cache_key_hex`: refuses a cache key that is not a SHA-256 hex string.

## 5. Enumerations

| Name | Values | Why |
| --- | --- | --- |
| `contract_type` | lease, vendor, service | The brief names these three; a new type is a migration and a template. |
| `extraction_field` | the 10 fields of REQ-005 | REQ-005 fixes the list; a new field changes the prompt schema and the eval. |
| `extraction_status` | accepted, needs_review, corrected | AC-US-00-002-4, AC-US-00-008-2 name these states. |
| `review_reason` | quote_not_found, clause_not_found, could_not_parse, value_missing | The four ways a field fails grounding or parsing (AC-US-00-002-4, AC-US-00-003-6). |
| `obligation_kind` | expiry, notice_deadline, renewal, escalation, payment | Q-009: the five dated duties. |
| `reminder_status` | pending, sending, sent, skipped | AC-US-00-006-3, AC-US-00-006-5, and the crash rule in section 4. |

## 6. Retention and personal data

Rules marked **UNDEFINED** are decisions owed by a person before the first
release; this document does not make them.

| Table | Rule | Mechanism | Source |
| --- | --- | --- | --- |
| `contracts` and its children | UNDEFINED (asked: keep until the developer deletes the contract or resets the database? owner Developer) | none until decided | not stated |
| `reminders` | UNDEFINED (asked: same as its contract? owner Developer) | none until decided | not stated |
| `llm_calls` | UNDEFINED (asked: keep for the life of the project so spend stays auditable? owner Developer) | none until decided | not stated |

Personal-data columns (1): `reminders.recipient` (contact). Contract text is synthetic (PRD non-goal: real data), so party names are not personal data here.

## 7. Migration plan

| # | db-migration name | Phase (expand \| migrate \| contract) | Hot table | Lock risk and batch note |
| --- | --- | --- | --- | --- |
| 1 | initial_schema (schema.sql) | expand | no | empty database, none |

## 8. Rules and deviations

Rules checked: 14 against `database/references/postgres.md` (naming, ids, timestamps, NOT NULL default, enums, text limits, FK with ON DELETE and index, tenant_id first, composite order, partial indexes, concurrent index builds, money, soft delete, JSONB). Deviations: 3.

- deviation: ids use `gen_random_uuid()` (v4) instead of a time-ordered v7, because PostgreSQL 16 has no built-in v7 and tables stay under 10^4 rows; revisit 2027-01-01 or when a table passes 10^6 rows.
- deviation: no `tenant_id`, because there is one user and no login (PRD non-goal); revisit if multi-user is ever added.
- deviation: text columns other than title carry no length CHECK, because clause bodies and contract text have no natural limit; the PDF itself bounds them.

## 9. What the review found

Findings: BLOCKER 0, MAJOR 3, MINOR 4, NIT 1 (open 1).

### MAJOR: obligations did not follow their source fields (`obligations`)

Expiry depends on two fields and the notice deadline on three; a correction to effective_date left payment and notice dates stale, and the field cascade never fires on an upsert. **Fix:** contract-wide recompute rule in section 4, and `uq_obligations_contract_single_kind`. Status: fixed in this version.

### MAJOR: an obligation could name one contract and another contract's field (`obligations`)

**Fix:** `uq_extractions_contract_id_id` and the composite FK `fk_obligations_contract_extraction`. Status: fixed in this version.

### MAJOR: the upload path had no source for contract_type (`contracts`)

**Fix:** the upload form carries a required type picker (Q-026, a convention the developer can overturn). Status: fixed in this version.

### MINOR: the cited clause number was lost when no such clause exists (`extractions`)

**Fix:** `cited_clause_number`. Status: fixed in this version.

### MINOR: a crash after sending was not visible and could resend (`reminders`)

**Fix:** sending status and the crash rule in section 4. Status: fixed in this version.

### MINOR: spend could not be reported per run, and a missing cost could be recorded as 0 (`llm_calls`)

**Fix:** `run_id`, `idx_llm_calls_run_id`, `chk_llm_calls_live_call_costed`. Status: fixed in this version.

### MINOR: deleting a clause deletes a corrected field (`extractions`)

Suggested fix: ON DELETE SET NULL (clause_id). Not taken: it would violate `chk_extractions_accepted_grounded` for accepted fields, and no story deletes or re-splits clauses; a duplicate load is refused (AC-US-00-001-5), so clauses only die with their contract. Status: open, revisit if re-splitting is ever added.

### NIT: stale statements in schema.sql and section 11

**Fix:** the obligations comment and section 11 updated. Status: fixed in this version.

## 10. Open concerns

- **[gap]** Retention is not stated for any table. Modelled as kept until the database is reset. (`contracts`, `reminders`, `llm_calls`) Owner: Developer, by 2026-10-05. Blocks development: no.
- **[risk]** The contract-wide recompute deletes obligations whose date changed; their sent reminders cascade away, so if a later correction brings the same date back it could be emailed again. Rare in the synthetic set. (`obligations`, `reminders`) Owner: Developer, by TASK-005. Blocks development: no.
- **[scope]** A crash between marking a reminder sending and sending it loses that email (never doubles it). Accepted for a local demo. (`reminders`) Owner: Developer, by TASK-005. Blocks development: no.
- **[ambiguity]** Q-026: the upload form requires the owner to pick the contract type; the model does not classify it. (`contracts`) Owner: Developer, by TASK-005. Blocks development: no.

## 11. Applying this

`schema.sql` runs top to bottom in one transaction against an empty database:
the pgvector extension and enum types first, then tables in foreign-key
order. Use it as the first migration; every change after the first release is
its own migration, never an edit to this file.

- Gate: `data-model: 6 tables, 62 columns, 17 indexes, 20 checks, 6 enums, 1 personal-data columns, 0 problems`
- Applied to an empty Postgres: yes, `schema-apply: docs/design/schema.sql applied to pgvector/pgvector:pg16, 6 tables` (the stock postgres:16 image has no pgvector, so the pgvector build of the same version was used)
