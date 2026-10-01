# ADR-0001: Use OpenRouter as the only LLM provider, capped at USD 10

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief
- Area: llm provider and models
- Reversibility: cheap: every call goes through one gateway module; a provider swap changes its client and base URL, and the reply cache must be refreshed

## Context

- From the request: "LLM: OpenRouter only, a Haiku-class model, hard budget USD 10. Key in .env."
- Learning project, 4 days, one developer; about 20 extraction calls and 30 Q&A eval calls per full live run (docs/designs/contracttracker.md).
- Q-007 (confirmed): the gateway refuses calls once recorded spend reaches USD 9; the OpenRouter key also carries a USD 10 limit.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| OpenRouter, one key with a credit limit (chosen) | adds a middle layer: its prices and latency sit on top of the vendor's; requests go through a third party | prototypes and model comparisons where one capped key beats several accounts |
| Anthropic API directly (catalogue default) | no alternative was weighed: the brief fixed OpenRouter; listed as the revisit path | a production build on Claude only, or prompt-caching features OpenRouter does not pass through |

## Decision

We will send every LLM call through OpenRouter with one API key read from `.env`, because the brief fixes it, one key with a credit limit makes the USD 10 budget enforceable outside our code, and switching models for a comparison is a one-line change.

## Consequences

- The gateway (TASK-002) is the only module that knows the base URL, the key and the price table; nothing else imports an HTTP client for LLM calls.
- Spend is recorded per call from OpenRouter's reported usage; `make eval-live` prints it.
- `.env` is never committed; `.env.example` carries the variable names only.
- Revisit if the project moves beyond learning use or needs a vendor feature OpenRouter does not expose.

## Commits us to

OpenRouter API (OpenAI-compatible chat completions), an OpenRouter API key with a USD 10 credit limit
