# Evals

Latest results of every evaluation, with how to reproduce them (REQ-043). Numbers below were
printed by the commands shown, on 2026-10-05 and 2026-10-06, with `anthropic/claude-haiku-4.5`.
Both evals run in `make check`, offline, from the committed reply cache `llm_cache/` (ADR-0009): a
cache miss fails the gate and names the missing items; it never calls the network.

## Extraction (`make eval-extraction`)

Prompt `extract_fields` v2, 6 golden contracts, answer key `data/answer_key.json` (5 fields each).

| Metric | Result | Limit |
| --- | --- | --- |
| parties | 6/6 | at most 1 miss |
| effective_date | 6/6 | at most 1 miss |
| term | 6/6 | at most 1 miss |
| auto_renewal | 6/6 | at most 1 miss |
| notice_period | 6/6 | at most 1 miss |
| quote grounding | 29/29 returned quotes found in their cited clause | at least 95% |
| deadlines (expiry and notice deadline computed in code from the model's text) | 12/12 | informational |

Cost: USD 0.0203 for the 6 calls (about USD 0.0034 each). The two hard cases pass: vendor-07 (notice
stated in clause 2.3, not the notice clause) and vendor-08 (no renewal clause, auto_renewal null).
Limits live in `evals/extraction/thresholds.toml`; the latest report is `evals/extraction/last-run.md`.

## Question answering (`make eval-qa`)

Prompt `answer_question` v1, 10 golden questions in `data/golden_questions.json` (7 answerable,
3 not), retrieval by cosine top-5 over `BAAI/bge-small-en-v1.5` vectors, refusal floor 0.70.

| Metric | Result | Limit |
| --- | --- | --- |
| recall@5 (expected contract and clause in the 5 retrieved) | 7/7 | at most 1 miss |
| answer accuracy (expected value stated and expected clause cited) | 7/7 | at most 1 miss |
| refusal accuracy (answerable answered, unanswerable refused, over all 10) | 10/10 | at most 1 miss |

Cost: USD 0.0148 for the 10 answers (about USD 0.0015 each). Limits live in
`evals/qa/thresholds.toml`; the floor and the scores it was chosen from are in
`evals/qa/floor-spike.md`.

## How far to trust these numbers

- **Small and close to the templates.** 30 labelled fields and 10 questions, all on contracts the
  generator wrote from the same templates the prompts' examples resemble. The scores show the
  pipeline works end to end and give a floor for catching regressions. They do not show accuracy on
  real contracts. One miss moves a field score by 17 points and a Q&A score by 10 to 14.
- **Graded by code, not by a judge model**, so the same inputs always score the same.
- **The floor is tuned on the same 10 questions it is scored on.** It sits in a clear gap (answerable
  0.763 to 0.868, unanswerable 0.598 to 0.635), but a real question worded unusually can score under
  0.70 and be refused although the answer exists.
- **Retrieval is checked by pgvector too**: `tests/integration/test_qa.py` pins the database
  ranking to the in-memory ranking the eval uses.

## Reproduce

```bash
make fetch-model       # once: saves the embedding model into models/
make eval-extraction   # offline, USD 0
make eval-qa           # offline, USD 0
make eval-live         # refreshes llm_cache/ from OpenRouter for both evals; the only target that spends
```
After any change to a prompt, the retrieval text or top-k, the affected cache keys change: run
`make eval-live` once, review the numbers, and commit the new `llm_cache/` files.
