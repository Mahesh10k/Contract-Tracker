# Tasks

Backlog: docs/product/backlog.md   Built: 2026-10-01   Hours: TBD

## Task table

| Task | Story | Discipline | Title | Estimate (h) | Depends on | Done when | Verifies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-00-001-D1 | US-00-001 | backend | Contract templates and generator: 18 contracts (leases, vendor, service) with numbered clauses, written with fpdf2, each with truth.json | TBD | none | `make contracts` writes 18 PDFs and 18 truth.json files under data/contracts | none: enabler for every AC of US-00-001 and the evals |
| US-00-001-D2 | US-00-001 | backend | Schema and migration for contracts and clauses | TBD | none | migration applies and rolls back on a clean Postgres 16 | AC-US-00-001-1 |
| US-00-001-D3 | US-00-001 | backend | PDF reader with pypdf: text extraction, scanned-PDF rejection, duplicate detection by file hash | TBD | US-00-001-D2 | `ingest <file>` stores a contract or prints the rejection or duplicate message | AC-US-00-001-1, AC-US-00-001-4, AC-US-00-001-5 |
| US-00-001-D4 | US-00-001 | backend | Clause splitter on numbered headings | TBD | US-00-001-D3 | every generated contract stores its clauses with number, heading and text | AC-US-00-001-2, AC-US-00-001-3 |
| US-00-001-T1 | US-00-001 | qa | Ingestion tests: lease row, scanned PDF rejected, duplicate refused | TBD | US-00-001-D3 | tests pass in `make check` | AC-US-00-001-1, AC-US-00-001-4, AC-US-00-001-5 |
| US-00-001-T2 | US-00-001 | qa | Splitter tests against truth.json clause lists, and the clause 7.2 boundary case | TBD | US-00-001-D4 | tests pass for all 18 contracts | AC-US-00-001-2, AC-US-00-001-3 |
| US-00-001-T3 | US-00-001 | qa | Unreadable file tests: a .txt renamed to .pdf and a truncated PDF are refused with nothing stored | TBD | US-00-001-D3 | tests pass | AC-US-00-001-6 |
| US-00-009-D1 | US-00-009 | backend | Migration 0002: clauses.first_page and last_page (nullable integers, checked first <= last) | TBD | none | migrate-verify passes with 0002 | AC-US-00-009-3 |
| US-00-009-D2 | US-00-009 | backend | Reader keeps page boundaries; splitter and repository store first and last page per clause | TBD | US-00-009-D1, US-02-005-D3 | clauses carry their pages | AC-US-00-009-1, AC-US-00-009-2 |
| US-00-009-T1 | US-00-009 | qa | Page tests: single-page clause, the page-break clause, and a pre-0002 row left empty | TBD | US-00-009-D2 | tests pass | AC-US-00-009-1, AC-US-00-009-2, AC-US-00-009-3 |
| US-00-002-D1 | US-00-002 | backend | LLM gateway: OpenRouter client, timeout, retry, cost per call, USD 9 stop, disk reply cache keyed by prompt version, model and input | TBD | none | a cached call makes no network request; spend is recorded per call | AC-US-00-002-5, AC-US-00-002-6 |
| US-00-002-D2 | US-00-002 | backend | Prompt registry with a versioned extraction prompt and the output schema for 10 fields as value, quote, clause_id | TBD | none | the prompt loads by name and version; schema rejects a reply missing a field | AC-US-00-002-1, AC-US-00-002-2 |
| US-00-002-D3 | US-00-002 | backend | Extraction service and field storage, one call per contract | TBD | US-00-002-D1, US-00-002-D2, US-00-001-D4 | `extract <contract>` stores 10 field rows | AC-US-00-002-1, AC-US-00-002-2 |
| US-00-002-D4 | US-00-002 | backend | Quote check with whitespace, line-break and hyphenation normalisation; ungrounded fields to needs_review | TBD | US-00-002-D3 | ungrounded fields are queued with the reason | AC-US-00-002-3, AC-US-00-002-4 |
| US-00-002-T1 | US-00-002 | qa | Gateway tests: cache hit makes no call, budget stop message | TBD | US-00-002-D1 | tests pass with the network disabled | AC-US-00-002-5, AC-US-00-002-6 |
| US-00-002-T2 | US-00-002 | qa | Extraction and quote check tests from recorded replies, including a hyphenated quote and a fabricated quote | TBD | US-00-002-D4 | tests pass in `make check` | AC-US-00-002-1, AC-US-00-002-2, AC-US-00-002-3, AC-US-00-002-4 |
| US-00-002-T3 | US-00-002 | qa | Gateway failure tests with a fake transport: timeout twice, 5xx twice, schema-invalid reply twice (one retry each); no rows written, spend recorded | TBD | US-00-002-D3 | tests pass with the network disabled | AC-US-00-002-7 |
| US-00-003-D1 | US-00-003 | backend | Duration and date-text parser: number words, digits, units, "prior to expiry" | TBD | none | parser returns a typed duration or "could not parse" | AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-6 |
| US-00-003-D2 | US-00-003 | backend | Date computation with python-dateutil: expiry, notice, renewal, escalation, payment | TBD | US-00-003-D1, US-00-002-D3 | dates are stored per contract | AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-5 |
| US-00-003-D3 | US-00-003 | backend | Obligations table and needs_review routing for unparseable fields | TBD | US-00-003-D2 | each dated duty is one obligation row with its clause | AC-US-00-003-6, AC-US-00-003-7 |
| US-00-003-T1 | US-00-003 | qa | Parser and date tests with the worked examples in the criteria, leap years and month ends | TBD | US-00-003-D2 | tests pass | AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-5 |
| US-00-003-T2 | US-00-003 | qa | Obligation and needs_review tests | TBD | US-00-003-D3 | tests pass | AC-US-00-003-6, AC-US-00-003-7 |
| US-00-008-D1 | US-00-008 | frontend | Review queue page: list held fields with reason and quote | TBD | US-00-007-D1 | page lists every held field | AC-US-00-008-1 |
| US-00-008-D2 | US-00-008 | backend | Save a correction: parse, recompute dates, mark corrected so re-extraction keeps it | TBD | US-00-003-D3 | a corrected field leaves the queue and survives re-extraction | AC-US-00-008-2, AC-US-00-008-3, AC-US-00-008-4 |
| US-00-008-T1 | US-00-008 | qa | Review queue tests: list, correct, re-extract keeps value, unparseable correction refused | TBD | US-00-008-D2 | tests pass | AC-US-00-008-1, AC-US-00-008-2, AC-US-00-008-3, AC-US-00-008-4 |
| US-00-006-D1 | US-00-006 | backend | Reminder table and `make remind` with an optional today date: 30 and 7 days, catch-up, send once | TBD | US-00-003-D3 | due reminders are recorded as sent | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3, AC-US-00-006-4, AC-US-00-006-5 |
| US-00-006-D2 | US-00-006 | backend | SMTP sender to MailHog with the reminder email body | TBD | US-00-006-D1 | an email with contract, obligation, date and clause appears in MailHog | AC-US-00-006-1 |
| US-00-006-T1 | US-00-006 | qa | Reminder tests with fixed today dates against MailHog's API | TBD | US-00-006-D2 | tests pass | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3, AC-US-00-006-4, AC-US-00-006-5 |
| US-00-006-T2 | US-00-006 | qa | SMTP failure test: point SMTP_PORT at a closed port; reminders stay pending and the command exits non-zero | TBD | US-00-006-D2 | test passes | AC-US-00-006-6 |
| US-00-006-D3 | US-00-006 | backend | 60-day lead time beside 30 and 7; PRETEND_TODAY read by make remind and the deadlines page; migration for the lead_days comment | TBD | US-00-006-D1 | make remind sends 60, 30 and 7-day reminders and honours PRETEND_TODAY | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-7 |
| US-00-006-T3 | US-00-006 | qa | Lead-time and pretend-today tests: 2028-10-01, 2028-10-31, 2028-11-23 with and without PRETEND_TODAY | TBD | US-00-006-D3 | tests pass | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-7 |
| US-00-004-D1 | US-00-004 | backend | Embed clauses with bge-small-en-v1.5 into clauses.embedding vector(384) and add a full-text index | TBD | US-00-001-D4 | every clause has an embedding and a tsvector | AC-US-00-004-2, AC-US-00-004-3 |
| US-00-004-D2 | US-00-004 | backend | Hybrid retrieval: vector and full-text results fused, top 5 | TBD | US-00-004-D1 | `search <question>` returns 5 clauses with scores | AC-US-00-004-2, AC-US-00-004-3 |
| US-00-004-D3 | US-00-004 | backend | Answer service: versioned Q&A prompt, citations as [contract, clause], citation check against retrieved clauses | TBD | US-00-004-D2, US-00-002-D1 | `ask <question>` prints a cited answer | AC-US-00-004-1, AC-US-00-004-4, AC-US-00-004-5 |
| US-00-004-T1 | US-00-004 | qa | Retrieval tests: keyword-only and meaning-only questions both hit top 5 | TBD | US-00-004-D2 | tests pass | AC-US-00-004-2, AC-US-00-004-3 |
| US-00-004-T2 | US-00-004 | qa | Answer tests from recorded replies: governing-law question, citation format, uncited clause replaced | TBD | US-00-004-D3 | tests pass | AC-US-00-004-1, AC-US-00-004-4, AC-US-00-004-5 |
| US-00-004-D4 | US-00-004 | backend | Embedding text joins contract title, clause number with heading, and body, separated by vertical bars | TBD | US-00-004-D1 | stored embeddings use the prefixed text | AC-US-00-004-6 |
| US-00-004-T3 | US-00-004 | qa | Test the exact embedded text for clause 2.2 of Lease Agreement 01 | TBD | US-00-004-D4 | test passes | AC-US-00-004-6 |
| US-00-005-D1 | US-00-005 | backend | Score-floor spike (10 answerable, 10 unanswerable) and the floor check before the LLM call | TBD | US-00-004-D2 | floor value recorded with the spike output | AC-US-00-005-1 |
| US-00-005-D2 | US-00-005 | backend | Guardrails: contract text passed as quoted data, prompt refusal rule, no-citation reply replaced by the refusal | TBD | US-00-004-D3 | injection clause and no-citation replies are handled | AC-US-00-005-2, AC-US-00-005-3, AC-US-00-005-4 |
| US-00-005-T1 | US-00-005 | qa | Refusal and guardrail tests, including the injection clause | TBD | US-00-005-D2 | tests pass | AC-US-00-005-1, AC-US-00-005-2, AC-US-00-005-3, AC-US-00-005-4 |
| US-00-007-D1 | US-00-007 | frontend | Web app shell, upload page and contract list | TBD | US-00-001-D3 | upload stores a contract and lists it | AC-US-00-007-1 |
| US-00-007-D2 | US-00-007 | frontend | Contract view with fields, quotes and review markers; deadlines page | TBD | US-00-007-D1, US-00-003-D3 | both pages render from the database | AC-US-00-007-2, AC-US-00-007-3 |
| US-00-007-D3 | US-00-007 | frontend | Ask page with citations linking to clause text | TBD | US-00-007-D1, US-00-004-D3 | question returns a linked, cited answer | AC-US-00-007-4 |
| US-00-007-T1 | US-00-007 | qa | Page tests for upload, contract view, deadlines and ask | TBD | US-00-007-D3 | tests pass | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-3, AC-US-00-007-4 |
| US-02-001-D1 | US-02-001 | backend | Extraction eval: per-field correct over total against truth.json, allowed misses per field | TBD | US-00-003-D3 | `make eval-extraction` prints 10 field lines and exits non-zero on a miss over the limit | AC-US-02-001-1, AC-US-02-001-2 |
| US-02-001-D2 | US-02-001 | backend | Grounding metric over every LLM-returned quote before routing | TBD | US-02-001-D1 | the grounded over total line prints | AC-US-02-001-3 |
| US-02-001-T1 | US-02-001 | qa | Eval self-test: flip one truth value, count drops by one; threshold exit code | TBD | US-02-001-D2 | tests pass | AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-3, AC-US-02-001-4 |
| US-02-001-D3 | US-02-001 | backend | Extraction eval accepts two prompt versions and prints them side by side | TBD | US-02-001-D1 | `make eval-extraction PROMPTS=v1,v2` prints one comparison table | AC-US-02-001-5 |
| US-02-001-T2 | US-02-001 | qa | Comparison table test on cached v1 and v2 replies | TBD | US-02-001-D3 | test passes | AC-US-02-001-5 |
| US-02-002-D1 | US-02-002 | backend | Golden question file: 20 answerable from templates, 10 unanswerable by hand | TBD | US-00-001-D1 | 30 questions with expected clause, value or refusal | none: dataset for every AC of US-02-002 |
| US-02-002-D2 | US-02-002 | backend | Q&A eval: recall@5, answer accuracy, refusal accuracy, thresholds | TBD | US-02-002-D1, US-00-005-D2 | `make eval-qa` prints three metrics and exits non-zero below threshold | AC-US-02-002-1, AC-US-02-002-2, AC-US-02-002-3, AC-US-02-002-4 |
| US-02-002-D3 | US-02-002 | backend | Record the spike floor and threshold values in the eval config | TBD | US-00-005-D1 | thresholds live in one config file | AC-US-02-002-4 |
| US-02-002-T1 | US-02-002 | qa | Q&A eval self-tests on a tiny fixed set | TBD | US-02-002-D2 | tests pass | AC-US-02-002-1, AC-US-02-002-2, AC-US-02-002-3, AC-US-02-002-4 |
| US-02-002-D4 | US-02-002 | backend | Q&A eval runs retrieval vector-only and hybrid and prints both recall@5 lines | TBD | US-02-002-D2 | two recall@5 lines print | AC-US-02-002-5 |
| US-02-002-T2 | US-02-002 | qa | Test both recall lines on the tiny fixed set | TBD | US-02-002-D4 | test passes | AC-US-02-002-5 |
| US-02-003-D1 | US-02-003 | devops | Wire both evals into `make check`; cache miss fails with the missing keys; `make setup` fetches the embedding model | TBD | US-02-001-D2, US-02-002-D2 | `make check` runs offline end to end | AC-US-02-003-1, AC-US-02-003-2 |
| US-02-003-D2 | US-02-003 | devops | `make eval-live` refreshes the cache and prints USD spent | TBD | US-02-003-D1 | one live run prints spend | AC-US-02-003-3 |
| US-02-003-T1 | US-02-003 | qa | Run `make check` with the network off; change top-k and confirm the cache-miss failure | TBD | US-02-003-D2 | both outcomes observed and recorded | AC-US-02-003-1, AC-US-02-003-2, AC-US-02-003-3 |
| US-02-003-D3 | US-02-003 | devops | `make evals-report` writes EVALS.md with every metric, threshold, counts, prompt versions and date | TBD | US-02-003-D1 | EVALS.md rewritten from cached runs | AC-US-02-003-4 |
| US-02-003-T2 | US-02-003 | qa | Run make evals-report twice offline; the file is identical apart from the date | TBD | US-02-003-D3 | check recorded | AC-US-02-003-4 |
| US-02-004-D1 | US-02-004 | devops | README from fresh clone to demo, with `.env.example` | TBD | US-02-003-D1 | a fresh clone reaches the demo by following it | AC-US-02-004-1 |
| US-02-004-D2 | US-02-004 | backend | Traceability table REQ to story to test | TBD | US-02-003-D1 | every live REQ has a test file | AC-US-02-004-2 |
| US-02-004-T1 | US-02-004 | qa | Follow the README on a clean checkout and check the traceability table | TBD | US-02-004-D2 | demo works and table has no gap | AC-US-02-004-1, AC-US-02-004-2 |
| US-02-004-D3 | US-02-004 | devops | Run gstack /cso over key handling and uploads; save the report under docs/security/ | TBD | US-02-004-D1 | report saved, no open Critical or High | AC-US-02-004-3 |
| US-02-004-T2 | US-02-004 | qa | Check the saved security report for open Critical or High findings | TBD | US-02-004-D3 | none open | AC-US-02-004-3 |
| US-02-005-D1 | US-02-005 | backend | Generator: relative-date commencement (anchor in the same sentence) and the notice-elsewhere, amendment and no-renewal contracts, added beside the 18 existing ones | TBD | none | new contracts and truth.json written; the 18 existing files unchanged | AC-US-02-005-1, AC-US-02-005-2, AC-US-02-005-3, AC-US-02-005-4, AC-US-02-005-6, AC-US-02-005-7 |
| US-02-005-D2 | US-02-005 | backend | Generator: page-break contract whose clause body runs from page 1 onto page 2 | TBD | US-02-005-D1 | the PDF has the clause split across a page | AC-US-02-005-5 |
| US-02-005-D3 | US-02-005 | backend | Splitter rejoins a clause across a page boundary | TBD | US-02-005-D2 | split equals truth.json for the page-break contract | AC-US-02-005-5 |
| US-02-005-T1 | US-02-005 | qa | Generator and splitter tests for each planted case, and byte-identical output for the original 18 | TBD | US-02-005-D3 | tests pass | AC-US-02-005-1, AC-US-02-005-2, AC-US-02-005-3, AC-US-02-005-4, AC-US-02-005-5, AC-US-02-005-6, AC-US-02-005-7 |
