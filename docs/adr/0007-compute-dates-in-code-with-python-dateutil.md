# ADR-0007: Compute every date in code with python-dateutil and a project duration parser

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief; parser approach from Q-021 and Q-022
- Area: date computation
- Reversibility: cheap: one module; swapping the parser changes no stored data shape

## Context

- From the request: "The LLM never computes dates. Code computes expiry, notice deadline, renewal, escalation and payment dates with python-dateutil. Unparseable values go to a needs_review queue."
- Q-021: the LLM returns date and duration text exactly as written, with its quote; code parses it.
- Q-022: python-dateutil parses dates ("1 March 2026") and does date arithmetic (relativedelta), but not durations such as "ninety (90) days prior to expiry".
- Q-024: recurring escalation and payment dates are computed to the end of the current term.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| python-dateutil plus a small project parser for durations (chosen) | the duration parser is our code to write and test | a fixed set of phrasings, as in template contracts |
| Ask the LLM to normalise durations to ISO 8601 | breaks REQ-007 and makes dates depend on the model | never, under this brief |
| A natural-language date library (dateparser) | adds a dependency that still does not handle "prior to expiry" relations | free-form date mentions in emails or notes |

## Decision

We will parse date text with python-dateutil, parse durations with a small unit-tested project parser (number words, digits, units, "prior to"), compute every date with relativedelta, and send anything unparsed to needs_review, because the brief forbids model-computed dates and a wrong date is worse than a held one.

## Consequences

- Month-end and leap-year cases are tested explicitly (AC-US-00-003-1: 1 March 2026 plus 3 years ends 2029-02-28).
- A user correction in the review queue is parsed by the same code and wins over re-extraction (Q-018).
- Revisit if more than 10% of fields in the synthetic set land in needs_review for parse failures.

## Commits us to

python-dateutil
