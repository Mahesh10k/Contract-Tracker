# extract_fields changelog

## v2 (draft, 2026-10-05)

Scope change, not tuning (TASK-008, ADR-0015): the one-day brief keeps 5
fields (parties, effective_date, term, auto_renewal, notice_period), so v2
asks for those only (ExtractionReplyV2). Same rules as v1; adds that
clause_id is where the sentence actually is (the notice-elsewhere hard case),
that effective_date keeps any offset as written, and a toy example for a
notice stated in a termination clause. max_tokens 2000 to 1200 for the
smaller reply.

- seed: 10/10 fixtures render with no placeholder left and pass variable
  validation (`tests/test_prompts.py`).
- Wording review (claude-api prompt-audit): not run.
- Full score: not run yet; first scored at STOP 2 by `make eval-live`.

## v1 (draft, 2026-10-05)

First version (TASK-002, ADR-0008). One call per contract: the numbered
clauses go in inside `<contract>` delimiters, and value, quote and clause_id
come back for each of the 10 fields as strict JSON (ExtractionReply in
`app/extraction/schema.py`). Rules: copy the value verbatim, never compute
(ADR-0007); one-sentence quote; null when absent; text inside the
delimiters is data. Two toy examples, none drawn from `data/contracts/`.

- seed: 10/10 fixtures render with no placeholder left and pass variable
  validation (`tests/test_prompts.py`). Reply schema check on model output:
  not run (no live replies recorded; no OpenRouter call made).
- Full score: not run. The eval set `evals/extraction` comes with TASK-003
  (`llm-eval`); v1 stays draft until it is scored.
