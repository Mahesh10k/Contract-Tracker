# ADR-0008: Extract all 10 fields in one LLM call per contract and verify each quote in code

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), in office hours (D2) on 2026-10-01
- Area: llm extraction
- Reversibility: cheap: extraction is one service behind the prompt registry; per-field extraction can replace it field by field

## Context

- From the request: 10 fields "each returned as {value, quote}"; "Every quote must be found in the source clause, or the field goes to review."
- Budget USD 10 (ADR-0001); 18 contracts (ADR-0006).
- Contracts are sent with numbered clauses, so the model can name the clause each quote comes from.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| One call per contract returning value, quote and clause_id per field (chosen) | a long contract may lower accuracy on some fields | small contracts, tight budget, 4 days |
| Retrieve candidate clauses, then one call per field | about 10 times the calls; extraction would wait on TASK-004 search | fields the eval shows are weak; the upgrade path |
| Rules first, LLM for the rest | overfits the templates, so evals overstate quality | fixed-wording fields in a real corpus with known forms |

## Decision

We will make one structured-output call per contract that returns `{value, quote, clause_id}` for each of the 10 fields, and verify in code that each normalised quote is a substring of the cited clause, routing failures to needs_review, because it is about 20 calls per run, clause_id makes the check exact, and it gives the citation for free.

## Consequences

- Grounding is measured over every quote the model returns, before routing (Q-015).
- The extraction prompt treats contract text as data, never instructions (Q-010).
- Revisit if any field misses more than its allowed count in the eval: move that field to retrieve-then-extract.

## Commits us to

OpenRouter structured outputs (JSON schema), a project prompt registry
