# PRD: ContractTracker

Source: project brief pasted on 2026-10-01 (45 lines), plus the user's decisions D1 and D2 in /office-hours the same day (design note: docs/designs/contracttracker.md); revised task list pasted by the developer on 2026-10-05 (6 lines, TASK-001 to TASK-006), adopted from TASK-002 on; one-day re-scope brief pasted 2026-10-05 (52 lines), applied as "re-scope, keep code" by the developer the same day   Normalised: 2026-10-05
Owner: unconfirmed:   Tracker epic: unconfirmed:

## 1. Problem

Not in the input. The brief describes the product, not the pain it removes.
The office-hours design note gives an inferred problem statement (missed notice
deadlines and auto-renewals buried in clauses); it is not used as a source here.

## 2. Business objectives

| Id | Objective | Target (measurable) | Source |
| --- | --- | --- | --- |
| B1 | The developer learns to build a grounded LLM application end to end: ingestion, extraction, retrieval, evals. | target: unconfirmed | "a learning project, and I'm new to AI projects" |
| B2 | inferred: No contract deadline passes without a reminder being sent first. | target: unconfirmed | "emails reminders before deadlines" |
| B3 | inferred: Every answer about the contracts can be checked against its source, or is refused. | target: unconfirmed | "answers questions ... with clause citations, refusing when the answer is not in the contracts" |

## 3. Non-goals

- OCR of scanned PDFs (brief, "Out of scope").
- Login or user accounts (brief, "Out of scope").
- Real email delivery; MailHog only (brief, "Out of scope").
- Multi-turn chat; each question is answered on its own (brief, "Out of scope").
- Real contract data; synthetic contracts only (brief, "no real data").

## 4. Personas

| Persona | Group | Who they are | What they need | Source |
| --- | --- | --- | --- | --- |
| inferred: Contract owner | 00 end user | The person who loads contracts, receives reminders, asks questions and clears the review queue | Know every obligation and deadline across their contracts and trust each answer | derived from "reads", "emails reminders", "answers questions" |

## 5. Requirement statements

One testable statement per id. Ids are never reused or renumbered.

| Id | Statement | Persona | Source | Flags |
| --- | --- | --- | --- | --- |
| REQ-001 | The system reads contract PDFs (leases, vendor agreements, service agreements) and stores their text. | Contract owner | "reads contracts (leases, vendor and service agreements)" | none |
| REQ-002 | The system splits each contract into clauses that can be cited individually. | Contract owner | "TASK-001 ... clause splitter" | none |
| REQ-003 | The system extracts the obligations in each contract. | Contract owner | "extracts obligations" | ambiguous: Q-009 |
| REQ-004 | The system extracts the key dates in each contract. | Contract owner | "and key dates" | ambiguous: Q-012 |
| REQ-005 | The system extracts 10 fields from each contract: parties, effective_date, term, auto_renewal, notice_period, payment_terms, escalation, liability_cap, termination_rights, governing_law. | Contract owner | "Extraction: 10 fields (...)" | withdrawn: replaced by REQ-045 (2026-10-05 one-day brief: "5 fields per contract") |
| REQ-006 | The system returns each extracted field as a value together with the quote it was taken from. | Contract owner | "each returned as {value, quote}" | none |
| REQ-007 | The system computes every date in code; no date value is produced by the LLM. | Contract owner | "The LLM never computes dates." | none |
| REQ-008 | The system computes each contract's expiry date. | Contract owner | "Code computes expiry" | none |
| REQ-009 | The system computes each contract's notice deadline. | Contract owner | "notice deadline" | none |
| REQ-010 | The system computes each contract's renewal date. | Contract owner | "renewal" | withdrawn: removed 2026-10-05 (one-day brief: "code computes expiry and notice deadline" only) |
| REQ-011 | The system computes each contract's escalation dates. | Contract owner | "escalation" | withdrawn: removed 2026-10-05 (one-day brief: field list has no escalation) |
| REQ-012 | The system computes each contract's payment dates. | Contract owner | "and payment dates" | withdrawn: removed 2026-10-05 (one-day brief: field list has no payment terms) |
| REQ-013 | The system places a field whose value cannot be parsed into the needs_review queue. | Contract owner | "Unparseable values go to a needs_review queue." | none |
| REQ-014 | The system checks that each extracted quote appears in the source clause. | Contract owner | "Every quote must be found in the source clause" | none |
| REQ-015 | The system places a field whose quote is not found in the source clause into the needs_review queue. | Contract owner | "or the field goes to review" | none |
| REQ-016 | The system emails a reminder before each deadline. | Contract owner | "emails reminders before deadlines" | ambiguous: Q-001 |
| REQ-017 | The system answers a question using all loaded contracts. | Contract owner | "answers questions across all contracts" | none |
| REQ-018 | The system retrieves clauses for a question by combining vector similarity and full-text search. | Contract owner | "Q&A: hybrid search (pgvector + Postgres full-text)" | withdrawn: replaced by REQ-047 (2026-10-05: "vector search top 5"; "Out of scope: ... hybrid search") |
| REQ-019 | The system cites every answer as [contract, clause]. | Contract owner | "answers cite [contract, clause]" | none |
| REQ-020 | The system replies exactly "Not found in these contracts" when the answer is not in the contracts. | Contract owner | "refuse with \"Not found in these contracts\"" | none |
| REQ-021 | The system applies guardrails to question answering. | Contract owner | "TASK-004 ... guardrails" | ambiguous: Q-010; withdrawn: replaced by REQ-051 (2026-10-05: "a check that every citation was retrieved") |
| REQ-022 | The system provides a web UI for the product's functions. | Contract owner | "TASK-005 reminders + UI"; "tech-decision for: web UI" | ambiguous: Q-004; withdrawn: replaced by REQ-052 (2026-10-05: "Streamlit page with tabs") |
| REQ-023 | The evaluation reports extraction accuracy for each of the 10 fields. | Contract owner | "Evals: extraction accuracy per field" | withdrawn: replaced by REQ-057 (2026-10-05: 5 fields) |
| REQ-024 | The evaluation reports quote grounding: the share of quotes found in their source clause. | Contract owner | "quote grounding" | none |
| REQ-025 | The evaluation reports retrieval recall@5. | Contract owner | "recall@5" | none |
| REQ-026 | The evaluation reports answer accuracy. | Contract owner | "answer accuracy" | none |
| REQ-027 | The evaluation reports refusal accuracy. | Contract owner | "refusal accuracy" | none |
| REQ-028 | The evaluations run as part of `make check`. | Contract owner | "Evals run under make check." | none |
| REQ-029 | The project README takes a fresh clone to a working demo. | inferred: Developer | "TASK-006 final evals + traceability + README + demo" (added 2026-10-01, missed in the first pass) | none |
| REQ-030 | The project keeps a traceability table from each REQ to the stories and tests that cover it. | inferred: Developer | "TASK-006 ... traceability" (added 2026-10-01, missed in the first pass) | none |
| REQ-031 | The synthetic contracts state dates both as absolute dates and as dates relative to another stated date. | inferred: Developer | 2026-10-05 list, TASK-001: "varied wording (absolute and relative dates" | ambiguous: Q-031; withdrawn: removed 2026-10-05 (one-day brief keeps 2 hard cases: REQ-033, REQ-036) |
| REQ-032 | The synthetic contracts include notice periods in days and in months, and contracts with and without renewal. | inferred: Developer | 2026-10-05 list, TASK-001: "notice in days and months, renewal present and absent" | none |
| REQ-033 | The synthetic contracts include a contract whose notice period is stated in a clause other than the notice clause. | inferred: Developer | 2026-10-05 list, TASK-001: "notice in a different clause" | none |
| REQ-034 | The synthetic contracts include a contract with an amendment that changes an earlier term. | inferred: Developer | 2026-10-05 list, TASK-001: "an amendment" | ambiguous: Q-030; withdrawn: removed 2026-10-05 (one-day brief keeps 2 hard cases) |
| REQ-035 | The synthetic contracts include a contract with a clause that continues across a page break. | inferred: Developer | 2026-10-05 list, TASK-001: "a clause across a page break" | withdrawn: removed 2026-10-05 (one-day brief keeps 2 hard cases) |
| REQ-036 | The synthetic contracts include a contract with no renewal clause. | inferred: Developer | 2026-10-05 list, TASK-001: "no renewal clause" | none |
| REQ-037 | The system records the page or pages each clause appears on. | Contract owner | 2026-10-05 list, TASK-001: "numbered-clause splitter that keeps page numbers" | none |
| REQ-038 | The system retries an extraction once when the model reply fails validation. | Contract owner | 2026-10-05 list, TASK-002: "Validate with Pydantic, retry once on failure" | none |
| REQ-039 | The evaluation reports extraction results for prompt v1 and prompt v2 side by side. | inferred: Developer | 2026-10-05 list, TASK-003: "Compare prompt v1 and v2" | withdrawn: removed 2026-10-05 ("Out of scope: ... prompt comparisons") |
| REQ-040 | The system embeds each clause with its contract title and clause heading prefixed to the clause text. | Contract owner | 2026-10-05 list, TASK-004: "Embed clauses with the contract title and heading prefixed" | none |
| REQ-041 | The evaluation reports recall@5 for vector-only retrieval and for hybrid retrieval. | inferred: Developer | 2026-10-05 list, TASK-004: "Measure recall@5, then add hybrid search" | withdrawn: removed 2026-10-05 ("Out of scope: ... hybrid search") |
| REQ-042 | The system lets the owner set the date it treats as today for reminders and deadlines. | Contract owner | 2026-10-05 list, TASK-005: "with a \"pretend today is\" setting" | ambiguous: Q-032 |
| REQ-043 | The project records the latest results of every evaluation in EVALS.md. | inferred: Developer | 2026-10-05 list, TASK-006: "Rerun all evals into EVALS.md" | none |
| REQ-044 | The project has a security review of API key handling and file uploads before the demo. | inferred: Developer | 2026-10-05 list, TASK-006: "/cso for a security review of key handling and uploads" | none |
| REQ-045 | The system extracts 5 fields from each contract: parties, effective_date, term, auto_renewal, notice_period. | Contract owner | 2026-10-05 one-day brief: "5 fields per contract, each {value, quote}" | none |
| REQ-046 | The system places every field of a contract in the needs_review queue when the model reply is still not valid JSON after one retry. | Contract owner | 2026-10-05: "Invalid JSON: one retry, then needs_review." | none |
| REQ-047 | The system retrieves the 5 clauses most similar to a question by vector search. | Contract owner | 2026-10-05: "Q&A: vector search top 5" | none |
| REQ-048 | The system answers a question only from the retrieved clauses. | Contract owner | 2026-10-05: "answer only from retrieved clauses" | none |
| REQ-049 | The system replies "Not found in these contracts" without an LLM call when the best retrieved clause scores below a similarity threshold. | Contract owner | 2026-10-05: "reply \"Not found in these contracts\" below a similarity threshold" | none |
| REQ-050 | The system replies "Not found in these contracts" when the retrieved clauses do not answer the question. | Contract owner | 2026-10-05: "or when the clauses don't answer it" | none |
| REQ-051 | The system checks that every clause an answer cites is one of the retrieved clauses. | Contract owner | 2026-10-05: "a check that every citation was retrieved" | none |
| REQ-052 | The system provides a single-page web app (React since 2026-10-05, ADR-0016; Streamlit before) with the tabs Upload, Contracts (fields and quotes), Deadlines, Ask and Needs review. | Contract owner | 2026-10-05: "Streamlit page with tabs: Upload, Contracts (fields + quotes), Deadlines, Ask, Needs review" | none |
| REQ-053 | The Streamlit page has a "send due reminders" button that emails every due reminder to MailHog. | Contract owner | 2026-10-05: "a \"send due reminders\" button that emails MailHog" | none |
| REQ-054 | The golden contract set has 6 synthetic contracts: 2 leases, 2 vendor and 2 service agreements, including the hard cases of REQ-033 and REQ-036. | inferred: Developer | 2026-10-05: "6 synthetic contracts (2 leases, 2 vendor, 2 service), 2 hard cases" | none |
| REQ-055 | data/answer_key.json holds the expected value of each of the 5 fields for every golden contract. | inferred: Developer | 2026-10-05: "Golden sets: data/answer_key.json for extraction" | none |
| REQ-056 | The Q&A golden set holds 10 questions: 7 answerable and 3 not answerable from the contracts. | inferred: Developer | 2026-10-05: "10 questions (7 answerable, 3 not) for Q&A" | none |
| REQ-057 | The evaluation reports extraction accuracy for each of the 5 fields. | inferred: Developer | 2026-10-05: "extraction accuracy per field" | none |

## 6. Constraints

From the brief:
- Python 3.11 or later; Bearing stack python-api.
- 4 days total, one developer.
- LLM through OpenRouter only, a Haiku-class model; exact model chosen in tech-decision (Q-014).
- Hard LLM budget of USD 10 (enforcement: Q-007).
- OpenRouter key kept in `.env`.
- Postgres 16 with pgvector, and MailHog, both in Docker Compose.
- Embeddings: BAAI/bge-small-en-v1.5, run locally on CPU via sentence-transformers (384 dimensions).
- Text PDFs only, read with pypdf.
- 15 to 20 synthetic contracts.
- Dates computed with python-dateutil.
- Named components: prompt registry, LLM gateway, quote check (TASK-002).
- Delivery split into TASK-001 to TASK-006 as listed in the brief.

From the user's decisions in /office-hours (2026-10-01):
- D1.1: Synthetic contracts are generated from code templates; each PDF is written with a `truth.json` answer key; PDFs are written with fpdf2.
- D1.2: LLM replies are cached on disk keyed by hash(prompt version, model, input); `make check` replays the cache offline; a separate `make eval-live` refreshes it and is the only target that spends budget.
- D1.3: Templates use numbered clause headings; the quote check normalises whitespace, line breaks and hyphenation before matching.
- D1.4: Refusal has two layers: a retrieval-score floor in code and an instruction in the prompt; about a third of the Q&A eval set is unanswerable.
- D2: Extraction makes one LLM call per contract with numbered clauses in the input and returns `{value, quote, clause_id}` per field.

From the developer's revised task list (2026-10-05), named methods and tools:
- Reminders 60, 30 and 7 days before a deadline (reverses Q-001; see Q-029).
- TASK-001 named reportlab and data/answer_key.json; the developer kept TASK-001 as built
  (fpdf2, truth.json per contract, ADR-0006) on 2026-10-05 (Q-027).
- One OpenRouter wrapper with retries, caching by contract hash and a cost log (llm-gateway; Q-028).
- Versioned extraction prompts (prompt-registry); Pydantic validation of model replies.
- compute_obligations() with python-dateutil, unit tests for month-end, leap years, days vs months.
- Skills named per task: bearing:rag (TASK-007), bearing:llm-gateway and bearing:prompt-registry
  (TASK-002), bearing:llm-eval (TASK-003), bearing:llm-guardrails (TASK-004), gstack /qa (TASK-005),
  bearing:traceability with zero gaps, gstack /cso and bearing:task-report (TASK-006).

From the one-day re-scope brief (2026-10-05); these replace the matching lines above where they differ:
- One day, one session; checkpoints with two STOP points for the developer.
- Budget USD 2 for the day (replaces USD 10; see Q-033).
- Single-page UI: Streamlit per the brief (ADR-0012), then React from 2026-10-05 (ADR-0016).
- Vector-only retrieval (replaces hybrid, ADR-0005).
- reportlab named for PDF generation; the generator stays on fpdf2 under the "keep code" choice (Q-027).
- Out of scope: OCR, login, hybrid search, scheduler, prompt comparisons.
- Cut rule: a checkpoint 30 minutes over cuts contracts or fields, never the evals.

## 7. Open questions

37 entries in docs/product/questions.md: 14 open, 3 need your confirmation (Q-033, Q-034, Q-036). Q-033 to Q-037 come from the one-day brief of 2026-10-05; Q-007, Q-013 and Q-020 were reversed by it and Q-010, Q-012 and Q-017 answered by it.

## 8. Could not extract

- Problem: not in the input; the developer (product owner) can state the pain in one or two sentences.
- Business objective targets: no numbers in the input; the developer can set them, and eval thresholds are proposed in Q-006.
- Owner and tracker epic: not in the input.

## 9. Glossary

| Term | Meaning | Source |
| --- | --- | --- |
| needs_review queue | Fields that could not be parsed or whose quote was not found, held for a person to check | brief, Extraction |
| quote | The exact contract text an extracted value was taken from | brief, "{value, quote}" |
| quote grounding | Whether a quote is found in its source clause | brief, Evals |
| notice period | How long before expiry a party must give notice to end or not renew | brief, field list |
| auto_renewal | Whether the contract renews itself at the end of its term | brief, field list |
| escalation | A scheduled increase in price or rent | brief, field list |
| hybrid search | Retrieval combining pgvector similarity and Postgres full-text search | brief, Q&A |
| recall@5 | Share of questions whose correct clause is among the top 5 retrieved | brief, Evals |
| Haiku-class model | A small, low-cost LLM tier | brief, LLM |
| MailHog | A local SMTP server that captures email for viewing instead of delivering it | brief |
