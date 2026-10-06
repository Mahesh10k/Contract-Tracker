# ADR-0014: Cap LLM spend at USD 2 for the one-day build

- Status: Proposed
- Date: 2026-10-05
- Task: TASK-008
- Deciders: Developer (project owner) set the budget in the one-day brief; the enforcement is an assumption awaiting confirmation (Q-033)
- Supersedes: ADR-0001, for the budget cap only (OpenRouter stays the only provider)
- Area: llm provider and models
- Reversibility: cheap: two settings

## Context

- From the request: "OpenRouter, a Haiku-class model, budget USD 2 for today. Key in .env."
- ADR-0001 capped spend at USD 10 with a gateway stop at USD 9 (Q-007). The gateway sums every row of the `llm_calls` ledger, so spend from earlier tasks counts against any new cap.
- One extraction call per contract (ADR-0008) costs about USD 0.01 to 0.02 with claude-haiku-4.5; 6 golden contracts plus 10 Q&A questions is well under USD 1 per live run.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Gateway stop at USD 1.80 counted over ledger rows since LLM_BUDGET_SINCE (default 2026-10-05), plus a USD 2 limit on the OpenRouter key (chosen) | one more setting to explain | a budget that is per day or per phase while the ledger keeps history |
| Raise the all-time stop to earlier spend plus USD 2 | needs the earlier spend known and written into config; wrong as soon as it drifts | a ledger that is reset at each phase |
| OpenRouter key limit only | nothing in code stops a loop before the provider does; not testable | a team that trusts the provider's limit alone |

## Decision

We will refuse LLM calls once ledger spend since LLM_BUDGET_SINCE reaches USD 1.80, and the developer sets a USD 2 limit on the OpenRouter key, because the brief sets USD 2 for the day and a stop in code is testable while the key limit is the backstop.

## Consequences

- New settings LLM_BUDGET_SINCE (date) and LLM_BUDGET_STOP_USD (default 1.80); `.env.example` documents both.
- `make eval-live` prints the spend of its own run and the total since LLM_BUDGET_SINCE.
- Revisit when the next phase starts: move LLM_BUDGET_SINCE and set its cap.

## Commits us to

OpenRouter
