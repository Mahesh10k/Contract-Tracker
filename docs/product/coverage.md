# Coverage: PRD statements to stories

PRD: docs/product/PRD.md   Backlog: docs/product/backlog.md   Built: 2026-10-01   Updated: 2026-10-05 (one-day brief)

## Matrix

| REQ | Statement (short) | Judgement | Why | Covered by | AC ids |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Reads contract PDFs and stores text | story | loading a contract is the first thing a user can do on its own | US-00-001 | AC-US-00-001-1, AC-US-00-001-4, AC-US-00-001-5, AC-US-00-001-6 |
| REQ-002 | Splits contracts into citable clauses | criterion-of US-00-001 | splitting is part of loading, not something the user asks for separately | US-00-001 | AC-US-00-001-2, AC-US-00-001-3 |
| REQ-003 | Extracts obligations | criterion-of US-00-003 | obligations are the dated duties computed from fields (Q-009) | US-00-003 | AC-US-00-003-7 |
| REQ-004 | Extracts key dates | criterion-of US-00-003 | key dates are the computed dates plus effective date (Q-012) | US-00-003 | AC-US-00-003-1, AC-US-00-003-7 |
| REQ-005 | Extracts 10 fields | story | withdrawn: replaced by REQ-045 2026-10-05; the user gets something new: the fields of each contract | none (withdrawn) | none |
| REQ-006 | Field returned as value and quote | criterion-of US-00-002 | the shape of each extracted field | US-00-002 | AC-US-00-002-2 |
| REQ-007 | Dates computed in code, never by the LLM | criterion-of US-00-003 | a rule on how dates are produced | US-00-003 | AC-US-00-003-1 |
| REQ-008 | Computes expiry | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-1 |
| REQ-009 | Computes notice deadline | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4 |
| REQ-010 | Computes renewal date | criterion-of US-00-003 | withdrawn: removed 2026-10-05; one of the dates the story computes | none (withdrawn) | none |
| REQ-011 | Computes escalation dates | criterion-of US-00-003 | withdrawn: removed 2026-10-05; one of the dates the story computes | none (withdrawn) | none |
| REQ-012 | Computes payment dates | criterion-of US-00-003 | withdrawn: removed 2026-10-05; one of the dates the story computes | none (withdrawn) | none |
| REQ-013 | Unparseable value goes to needs_review | criterion-of US-00-003 | the failure path of date computation; correction seeded US-00-011 via Q-005 | US-00-003, US-00-008, US-00-011 | AC-US-00-003-6, AC-US-00-008-1, AC-US-00-011-1, AC-US-00-011-3 |
| REQ-014 | Quote checked against source clause | criterion-of US-00-002 | a check on each extracted field | US-00-002 | AC-US-00-002-3 |
| REQ-015 | Ungrounded field goes to needs_review | criterion-of US-00-002 | the failure path of the quote check | US-00-002, US-00-008, US-00-011 | AC-US-00-002-4, AC-US-00-008-1, AC-US-00-011-2 |
| REQ-016 | Emails reminders before deadlines | story | a new thing the user receives; lead times 60, 30 and 7 days since Q-029 | US-00-006 | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3, AC-US-00-006-4, AC-US-00-006-5, AC-US-00-006-6 |
| REQ-017 | Answers questions across all contracts | story | a new thing the user can do | US-00-004 | AC-US-00-004-1 |
| REQ-018 | Hybrid retrieval | criterion-of US-00-004 | withdrawn: replaced by REQ-047 2026-10-05; how answers find clauses, not a user action | none (withdrawn) | none |
| REQ-019 | Cites [contract, clause] | criterion-of US-00-004 | the form of every answer | US-00-004 | AC-US-00-004-4, AC-US-00-004-5 |
| REQ-020 | Exact refusal text | story | the user gets a distinct, testable outcome when the answer is absent | US-00-005 | AC-US-00-005-1, AC-US-00-005-2 |
| REQ-021 | Guardrails on Q&A | criterion-of US-00-005 | withdrawn: replaced by REQ-051 2026-10-05; guardrails exist to force a cite-or-refuse outcome (Q-010) | none (withdrawn) | none |
| REQ-022 | Web UI | story | withdrawn: replaced by REQ-052 2026-10-05; the browser is how the owner reaches every function (Q-004); review screen split into US-00-008 | none (withdrawn) | none |
| REQ-023 | Extraction accuracy per field | story | withdrawn: replaced by REQ-057 2026-10-05; the developer gets a new report | none (withdrawn) | none |
| REQ-024 | Quote grounding metric | criterion-of US-02-001 | one more line of the same report as REQ-057 | US-02-001 | AC-US-02-001-3 |
| REQ-025 | recall@5 | story | the developer gets a new Q&A report | US-02-002 | AC-US-02-002-1, AC-US-02-002-4 |
| REQ-026 | Answer accuracy | criterion-of US-02-002 | one more line of the same report | US-02-002 | AC-US-02-002-2, AC-US-02-002-4 |
| REQ-027 | Refusal accuracy | criterion-of US-02-002 | one more line of the same report | US-02-002 | AC-US-02-002-3, AC-US-02-002-4 |
| REQ-028 | Evals run under make check | story | turns two reports into a gate on every change | US-02-003 | AC-US-02-003-1, AC-US-02-003-2, AC-US-02-003-3 |
| REQ-029 | README takes a fresh clone to a demo | story | the developer can show the product to someone else | US-02-004 | AC-US-02-004-1 |
| REQ-030 | Traceability table REQ to tests | criterion-of US-02-004 | the evidence that goes with the demo | US-02-004 | AC-US-02-004-2 |
| REQ-031 | Absolute and relative dates in the set | story | withdrawn: removed 2026-10-05 (Q-037); new golden-set data the developer can evaluate against; seeds US-02-005 | none (withdrawn) | none |
| REQ-032 | Notice in days and months; renewal present and absent | criterion-of US-02-005 | a property of the same planted set | US-02-005 | AC-US-02-005-2, AC-US-02-005-7 |
| REQ-033 | Notice stated outside the notice clause | criterion-of US-02-005 | one planted case of the same set | US-02-005 | AC-US-02-005-3 |
| REQ-034 | Amendment that changes an earlier term | criterion-of US-02-005 | withdrawn: removed 2026-10-05 (Q-037); one planted case of the same set (Q-030) | none (withdrawn) | none |
| REQ-035 | Clause across a page break | criterion-of US-02-005 | withdrawn: removed 2026-10-05 (Q-037); one planted case of the same set | none (withdrawn) | none |
| REQ-036 | Contract with no renewal clause | criterion-of US-02-005 | one planted case of the same set | US-02-005 | AC-US-02-005-6 |
| REQ-037 | Clause page numbers | story | the owner can do something new: find a cited clause by page; US-00-001 is Done, so a new story | US-00-009 | AC-US-00-009-1, AC-US-00-009-2, AC-US-00-009-3 |
| REQ-038 | Retry once on validation failure | criterion-of US-00-002 | a rule on the existing extraction, folded into AC-7 (To do, edited in place) | US-00-002 | AC-US-00-002-7 |
| REQ-039 | Prompt v1 and v2 side by side | criterion-of US-02-001 | withdrawn: removed 2026-10-05; one more view of the same extraction report | none (withdrawn) | none |
| REQ-040 | Title and heading prefixed to embeddings | criterion-of US-00-004 | how clauses are embedded for the existing Q&A | US-00-004 | AC-US-00-004-6 |
| REQ-041 | recall@5 vector-only and hybrid | criterion-of US-02-002 | withdrawn: removed 2026-10-05; one more line of the same Q&A report | none (withdrawn) | none |
| REQ-042 | Pretend-today setting | criterion-of US-00-006 | qualifies when reminders fire (Q-032) | US-00-006 | AC-US-00-006-7 |
| REQ-043 | EVALS.md with the latest results | criterion-of US-02-003 | an output of the same eval gate | US-02-003 | AC-US-02-003-4 |
| REQ-044 | Security review of key handling and uploads | criterion-of US-02-004 | part of making the demo ready for someone else | US-02-004 | AC-US-02-004-3 |
| REQ-045 | Extracts 5 fields | story | changes the Done US-00-002, so a new story (Q-036) | US-00-010 | AC-US-00-010-1, AC-US-00-010-4 |
| REQ-046 | Invalid JSON after one retry goes to needs_review | criterion-of US-00-010 | the failure path of the same extraction | US-00-010 | AC-US-00-010-2, AC-US-00-010-3 |
| REQ-047 | Vector top 5 | criterion-of US-00-004 | how answers find clauses, not a user action | US-00-004 | AC-US-00-004-2 |
| REQ-048 | Answers only from retrieved clauses | criterion-of US-00-004 | a rule on what the answer may use; also carries the injection case in US-00-005 | US-00-004, US-00-005 | AC-US-00-004-3, AC-US-00-005-3 |
| REQ-049 | Refuse below a similarity threshold, no LLM call | criterion-of US-00-005 | one trigger of the refusal | US-00-005 | AC-US-00-005-1 |
| REQ-050 | Refuse when the clauses do not answer | criterion-of US-00-005 | the other trigger of the refusal | US-00-005 | AC-US-00-005-2 |
| REQ-051 | Every citation was retrieved | criterion-of US-00-005 | the guardrail that forces cite-or-refuse | US-00-005 | AC-US-00-005-4 |
| REQ-052 | Streamlit page with five tabs | story | the page is how the owner reaches every function; Needs review tab in US-00-008 | US-00-007, US-00-008 | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-3, AC-US-00-007-4, AC-US-00-007-5, AC-US-00-008-1 |
| REQ-053 | Send due reminders button | criterion-of US-00-006 | another trigger of the same reminders | US-00-006 | AC-US-00-006-1 |
| REQ-054 | 6-contract golden set | story | new golden-set data the developer evaluates against | US-02-006 | AC-US-02-006-1, AC-US-02-006-2 |
| REQ-055 | data/answer_key.json | criterion-of US-02-006 | the file the golden set is written to | US-02-006 | AC-US-02-006-3, AC-US-02-006-4 |
| REQ-056 | 10 golden questions, 7 answerable, 3 not | criterion-of US-02-002 | the dataset of the same Q&A report | US-02-002 | AC-US-02-002-5 |
| REQ-057 | Extraction accuracy per 5 fields | story | the developer gets the extraction report | US-02-001 | AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-4 |

## Gaps

| REQ | Why uncovered | Proposed action |
| --- | --- | --- |
| none | | |

## Orphan stories

| Story | Reason it exists | Action |
| --- | --- | --- |
| none | US-02-004 now covers REQ-029 and REQ-030 | |

## Counts

stories-coverage: 44 REQ from docs/product/PRD.md (13 withdrawn), 44 covered, 0 out of scope, 0 gaps, 16 stories, 79 AC, 0 orphans, 0 problems
Verdict: covered
