# PRD: ContractTracker

Source: project brief pasted on 2026-10-01 (45 lines), plus the user's decisions D1 and D2 in /office-hours the same day (design note: docs/designs/contracttracker.md)   Normalised: 2026-10-01
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
| REQ-005 | The system extracts 10 fields from each contract: parties, effective_date, term, auto_renewal, notice_period, payment_terms, escalation, liability_cap, termination_rights, governing_law. | Contract owner | "Extraction: 10 fields (...)" | none |
| REQ-006 | The system returns each extracted field as a value together with the quote it was taken from. | Contract owner | "each returned as {value, quote}" | none |
| REQ-007 | The system computes every date in code; no date value is produced by the LLM. | Contract owner | "The LLM never computes dates." | none |
| REQ-008 | The system computes each contract's expiry date. | Contract owner | "Code computes expiry" | none |
| REQ-009 | The system computes each contract's notice deadline. | Contract owner | "notice deadline" | none |
| REQ-010 | The system computes each contract's renewal date. | Contract owner | "renewal" | none |
| REQ-011 | The system computes each contract's escalation dates. | Contract owner | "escalation" | none |
| REQ-012 | The system computes each contract's payment dates. | Contract owner | "and payment dates" | none |
| REQ-013 | The system places a field whose value cannot be parsed into the needs_review queue. | Contract owner | "Unparseable values go to a needs_review queue." | none |
| REQ-014 | The system checks that each extracted quote appears in the source clause. | Contract owner | "Every quote must be found in the source clause" | none |
| REQ-015 | The system places a field whose quote is not found in the source clause into the needs_review queue. | Contract owner | "or the field goes to review" | none |
| REQ-016 | The system emails a reminder before each deadline. | Contract owner | "emails reminders before deadlines" | ambiguous: Q-001 |
| REQ-017 | The system answers a question using all loaded contracts. | Contract owner | "answers questions across all contracts" | none |
| REQ-018 | The system retrieves clauses for a question by combining vector similarity and full-text search. | Contract owner | "Q&A: hybrid search (pgvector + Postgres full-text)" | none |
| REQ-019 | The system cites every answer as [contract, clause]. | Contract owner | "answers cite [contract, clause]" | none |
| REQ-020 | The system replies exactly "Not found in these contracts" when the answer is not in the contracts. | Contract owner | "refuse with \"Not found in these contracts\"" | none |
| REQ-021 | The system applies guardrails to question answering. | Contract owner | "TASK-004 ... guardrails" | ambiguous: Q-010 |
| REQ-022 | The system provides a web UI for the product's functions. | Contract owner | "TASK-005 reminders + UI"; "tech-decision for: web UI" | ambiguous: Q-004 |
| REQ-023 | The evaluation reports extraction accuracy for each of the 10 fields. | Contract owner | "Evals: extraction accuracy per field" | none |
| REQ-024 | The evaluation reports quote grounding: the share of quotes found in their source clause. | Contract owner | "quote grounding" | none |
| REQ-025 | The evaluation reports retrieval recall@5. | Contract owner | "recall@5" | none |
| REQ-026 | The evaluation reports answer accuracy. | Contract owner | "answer accuracy" | none |
| REQ-027 | The evaluation reports refusal accuracy. | Contract owner | "refusal accuracy" | none |
| REQ-028 | The evaluations run as part of `make check`. | Contract owner | "Evals run under make check." | none |
| REQ-029 | The project README takes a fresh clone to a working demo. | inferred: Developer | "TASK-006 final evals + traceability + README + demo" (added 2026-10-01, missed in the first pass) | none |
| REQ-030 | The project keeps a traceability table from each REQ to the stories and tests that cover it. | inferred: Developer | "TASK-006 ... traceability" (added 2026-10-01, missed in the first pass) | none |

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

## 7. Open questions

25 entries in docs/product/questions.md: 14 open, 0 need your confirmation. Q-001 to Q-009, Q-018 and Q-019 confirmed on 2026-10-01; Q-015 to Q-023 come from the critic; Q-024 and Q-025 from the backlog.

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
