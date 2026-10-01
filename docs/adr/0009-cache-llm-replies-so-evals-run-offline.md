# ADR-0009: Cache LLM replies on disk so make check runs evals offline

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), in office hours (D1.2) on 2026-10-01
- Area: evaluation
- Reversibility: cheap: the cache is a folder; deleting it forces one live run

## Context

- From the request: "Evals run under make check." and "hard budget USD 10".
- A live full eval run costs about USD 0.36 (estimate, ADR-0002); running it on every `make check` would spend the budget within about 25 runs and make results vary between runs.
- Q-016: Q&A prompts contain retrieved clauses, so any change to splitting, embeddings or top-k changes the prompt and misses the cache.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Disk cache keyed by hash(prompt version, model, full input); `make check` replays, `make eval-live` refreshes (chosen) | cached replies go stale silently if the key misses an input | deterministic, free evals on every change |
| Live calls in every `make check` | slow, non-deterministic, spends budget | a funded project with a nightly eval job |
| Mocked replies written by hand | tests the code paths, not the model | unit tests of parsing and routing (also used) |

## Decision

We will store every LLM reply on disk keyed by a hash of prompt version, model id and the full request body; `make check` reads only from this cache and fails on a miss with the list of missing keys, and `make eval-live` is the only target that calls OpenRouter, because evals must be free, repeatable and still reflect the real model.

## Consequences

- The cache folder is committed so a fresh clone can run `make check` offline.
- The embedding model is fetched by `make setup`, not at test time (ADR-0004).
- Revisit if the cache passes 50 MB or reviewers cannot tell stale replies from current ones.

## Commits us to

a project reply cache (JSON files), make targets `check`, `eval-live`, `setup`
