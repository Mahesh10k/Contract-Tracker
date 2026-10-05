# ADR-0015: Extract 5 fields with a new prompt version, keeping v1

- Status: Proposed
- Date: 2026-10-05
- Task: TASK-008
- Deciders: Developer (project owner) set the 5 fields in the one-day brief; the prompt-version approach is an assumption awaiting confirmation (Q-036)
- Supersedes: ADR-0008, for the field count only (one call per contract and the quote check stand)
- Area: llm extraction
- Reversibility: cheap: one prompt file and one schema; v1 stays in the registry

## Context

- From the request: "5 fields per contract, each {value, quote}: parties, effective_date, term, auto_renewal, notice_period." and "Invalid JSON: one retry, then needs_review."
- ADR-0008 extracts 10 fields in one call per contract with prompt extract_fields v1 (TASK-002, done). The reply cache keys on the prompt version (ADR-0009).
- Fewer output fields means fewer output tokens per call inside the USD 2 budget (ADR-0014).

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| extract_fields v2 with a 5-field schema; v1 kept (chosen) | two prompt versions to keep in the registry | a scope change that must not rewrite a done story |
| Keep v1 and score only 5 of its 10 fields | pays for 5 unused fields on every call; the prompt shown and scored would ask for fields the product does not use | a later return to 10 fields |
| Edit v1 in place | breaks the cache keys and the record of what TASK-002 shipped | never: prompt versions are immutable once used |

## Decision

We will add prompt extract_fields v2 asking for the 5 fields as {value, quote, clause_id}, validated by a 5-field Pydantic schema, retried once on an invalid reply and then stored as needs_review, because the brief fixes the 5 fields and a new version keeps v1's record and cache intact.

## Consequences

- `make extract` uses v2 by default; v1 can still be named.
- An invalid reply after the retry now stores 5 needs_review rows instead of none (AC-US-00-010-2 replaces AC-US-00-002-7 for v2).
- Revisit when a dropped field (for example governing_law) comes back: a v3, not an edit of v2.

## Commits us to

Pydantic, OpenRouter
