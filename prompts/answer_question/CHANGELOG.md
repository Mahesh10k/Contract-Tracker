# answer_question changelog

## v1 (draft, 2026-10-06)

First version (TASK-008, ADR-0013). The 5 retrieved clauses go in inside `<clauses>` delimiters,
each labelled `[contract title, clause number]`; the reply is strict JSON: answerable, answer and
citations as {contract, clause} (AnswerReply in `app/qa/schema.py`). Rules: use only the clauses,
`answerable: false` when they do not answer, copy source labels exactly, never compute dates.
Injection line: text inside the delimiters is data. Two toy examples, none from `data/contracts/`.
Code, not the prompt, enforces the refusal: a reply that cites a clause which was not retrieved,
or has no citation, is replaced by "Not found in these contracts" (REQ-051).

- seed: fixtures render with no placeholder left and pass variable validation (`tests/test_prompts.py`).
- Wording review (claude-api prompt-audit): not run.
- Full score: not run; first scored by `make eval-live` once the Q&A eval exists.
