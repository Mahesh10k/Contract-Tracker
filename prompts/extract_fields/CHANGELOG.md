# extract_fields changelog

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
