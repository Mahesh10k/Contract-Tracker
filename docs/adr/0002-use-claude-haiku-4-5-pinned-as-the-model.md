# ADR-0002: Use anthropic/claude-haiku-4.5, pinned by exact id, for extraction and Q&A

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), in tech-decision on 2026-10-01
- Area: llm provider and models
- Reversibility: cheap: one config value; changing it invalidates every cached reply, so one `make eval-live` run (about USD 0.36, estimate) must follow

## Context

- From the request: "a Haiku-class model, hard budget USD 10".
- OpenRouter prices fetched 2026-10-01 from its public models list, per million tokens in / out: claude-haiku-4.5 $1.00 / $5.00; gpt-5.4-mini $0.75 / $4.50; gemini-3.1-flash-lite $0.25 / $1.50; gpt-5-mini $0.25 / $2.00 (reasoning tokens billed as output). All four list structured output support.
- Estimated workload per full live eval run: 18 extraction calls at about 6k tokens in and 1.5k out, plus 30 Q&A calls at about 2.5k in and 300 out. These are estimates, not measurements; genai-design (step 5) refines them.
- The reply cache key includes the model id (ADR-0009), so an alias such as `~anthropic/claude-haiku-latest` could change models silently and empty the cache.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| anthropic/claude-haiku-4.5 (chosen) | highest price of the four: about USD 0.36 per full live run, about 25 runs inside the USD 9 stop | quote-exact extraction where a miss sends a field to review |
| openai/gpt-5.4-mini | about USD 0.30 per run; not the family the brief names, so its guidance does not transfer directly | a comparison run, or if Haiku misses quotes the eval shows this model gets |
| google/gemini-3.1-flash-lite | lighter model; more risk on exact quotes and the 10-field schema | prompt iteration needing more than about 25 live runs (about 90 fit) |
| openai/gpt-5-mini | reasoning tokens make cost and latency per call unpredictable against a hard budget | tasks that need multi-step reasoning, which extraction does not |

## Decision

We will use `anthropic/claude-haiku-4.5` by that exact id for both extraction and Q&A, because it is the model the brief names, about 25 full live runs fit the cap while `make check` costs nothing, and exact quoting is where a stronger small model pays for itself.

## Consequences

- The model id lives in one setting; prompts in the registry are versioned against it.
- Revisit if genai-design's estimate or the first live run shows more than USD 0.40 per full run, or if prompt iteration needs more than 20 live runs: switch to gemini-3.1-flash-lite and compare on the same eval.

## Commits us to

anthropic/claude-haiku-4.5 via OpenRouter
