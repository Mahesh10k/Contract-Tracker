# Coverage: PRD statements to stories

PRD: docs/product/PRD.md   Backlog: docs/product/backlog.md   Built: 2026-10-01

## Matrix

| REQ | Statement (short) | Judgement | Why | Covered by | AC ids |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Reads contract PDFs and stores text | story | loading a contract is the first thing a user can do on its own | US-00-001 | AC-US-00-001-1, AC-US-00-001-4, AC-US-00-001-5, AC-US-00-001-6 |
| REQ-002 | Splits contracts into citable clauses | criterion-of US-00-001 | splitting is part of loading, not something the user asks for separately | US-00-001 | AC-US-00-001-2, AC-US-00-001-3 |
| REQ-003 | Extracts obligations | criterion-of US-00-003 | obligations are the dated duties computed from fields (Q-009) | US-00-003 | AC-US-00-003-7 |
| REQ-004 | Extracts key dates | criterion-of US-00-003 | key dates are the computed dates plus effective date (Q-012) | US-00-003 | AC-US-00-003-1, AC-US-00-003-7 |
| REQ-005 | Extracts 10 fields | story | the user gets something new: the fields of each contract | US-00-002 | AC-US-00-002-1, AC-US-00-002-5, AC-US-00-002-6, AC-US-00-002-7 |
| REQ-006 | Field returned as value and quote | criterion-of US-00-002 | the shape of each extracted field | US-00-002 | AC-US-00-002-2 |
| REQ-007 | Dates computed in code, never by the LLM | criterion-of US-00-003 | a rule on how dates are produced | US-00-003 | AC-US-00-003-1 |
| REQ-008 | Computes expiry | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-1 |
| REQ-009 | Computes notice deadline | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-2 |
| REQ-010 | Computes renewal date | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-3 |
| REQ-011 | Computes escalation dates | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-4 |
| REQ-012 | Computes payment dates | criterion-of US-00-003 | one of the dates the story computes | US-00-003 | AC-US-00-003-5 |
| REQ-013 | Unparseable value goes to needs_review | criterion-of US-00-003 | the failure path of date computation; correction seeded US-00-008 via Q-005 | US-00-003, US-00-008 | AC-US-00-003-6, AC-US-00-008-1, AC-US-00-008-2, AC-US-00-008-4 |
| REQ-014 | Quote checked against source clause | criterion-of US-00-002 | a check on each extracted field | US-00-002 | AC-US-00-002-3 |
| REQ-015 | Ungrounded field goes to needs_review | criterion-of US-00-002 | the failure path of the quote check | US-00-002, US-00-008 | AC-US-00-002-4, AC-US-00-008-1, AC-US-00-008-3 |
| REQ-016 | Emails reminders before deadlines | story | a new thing the user receives | US-00-006 | AC-US-00-006-1, AC-US-00-006-2, AC-US-00-006-3, AC-US-00-006-4, AC-US-00-006-5, AC-US-00-006-6 |
| REQ-017 | Answers questions across all contracts | story | a new thing the user can do | US-00-004 | AC-US-00-004-1 |
| REQ-018 | Hybrid retrieval | criterion-of US-00-004 | how answers find clauses, not a user action | US-00-004 | AC-US-00-004-2, AC-US-00-004-3 |
| REQ-019 | Cites [contract, clause] | criterion-of US-00-004 | the form of every answer | US-00-004 | AC-US-00-004-4, AC-US-00-004-5 |
| REQ-020 | Exact refusal text | story | the user gets a distinct, testable outcome when the answer is absent | US-00-005 | AC-US-00-005-1, AC-US-00-005-2 |
| REQ-021 | Guardrails on Q&A | criterion-of US-00-005 | guardrails exist to force a cite-or-refuse outcome (Q-010) | US-00-005 | AC-US-00-005-3, AC-US-00-005-4 |
| REQ-022 | Web UI | story | the browser is how the owner reaches every function (Q-004); review screen split into US-00-008 | US-00-007, US-00-008 | AC-US-00-007-1, AC-US-00-007-2, AC-US-00-007-3, AC-US-00-007-4, AC-US-00-008-1 |
| REQ-023 | Extraction accuracy per field | story | the developer gets a new report | US-02-001 | AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-4 |
| REQ-024 | Quote grounding metric | criterion-of US-02-001 | one more line of the same report | US-02-001 | AC-US-02-001-3 |
| REQ-025 | recall@5 | story | the developer gets a new Q&A report | US-02-002 | AC-US-02-002-1, AC-US-02-002-4 |
| REQ-026 | Answer accuracy | criterion-of US-02-002 | one more line of the same report | US-02-002 | AC-US-02-002-2, AC-US-02-002-4 |
| REQ-027 | Refusal accuracy | criterion-of US-02-002 | one more line of the same report | US-02-002 | AC-US-02-002-3, AC-US-02-002-4 |
| REQ-028 | Evals run under make check | story | turns two reports into a gate on every change | US-02-003 | AC-US-02-003-1, AC-US-02-003-2, AC-US-02-003-3 |
| REQ-029 | README takes a fresh clone to a demo | story | the developer can show the product to someone else | US-02-004 | AC-US-02-004-1 |
| REQ-030 | Traceability table REQ to tests | criterion-of US-02-004 | the evidence that goes with the demo | US-02-004 | AC-US-02-004-2 |

## Gaps

| REQ | Why uncovered | Proposed action |
| --- | --- | --- |
| none | | |

## Orphan stories

| Story | Reason it exists | Action |
| --- | --- | --- |
| none | US-02-004 now covers REQ-029 and REQ-030 | |

## Counts

stories-coverage: 30 REQ from docs/product/PRD.md (0 withdrawn), 30 covered, 0 out of scope, 0 gaps, 12 stories, 56 AC, 0 orphans, 0 problems
Verdict: covered
