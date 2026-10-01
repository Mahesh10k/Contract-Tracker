# GenAI solution: ContractTracker extraction and cited Q&A

Serves: REQ-003 to REQ-030; US-00-002, US-00-003, US-00-004, US-00-005, US-02-001, US-02-002, US-02-003
Status: Draft
Owner: Developer (project owner)
ADR: docs/adr/0008-extract-with-one-call-per-contract-and-check-quotes.md and docs/adr/0005-use-hybrid-search-for-retrieval.md (both Accepted; no new approach ADR needed)
HLD: docs/design/contracttracker-hld.md (to write)

## 1. Problem

Obligations and deadlines are buried in contract clauses, so the owner cannot see what is due when, or get a checkable answer about a contract, without reading every page.

## 2. Success metric

Primary: on the extraction golden set (18 contracts by 10 fields), every field is wrong in at most 2 of 18 contracts, graded by code against `truth.json` after normalisation (Q-006, Q-015).

Secondary gates, all in `make check` (REQ-023 to REQ-028):

| Metric | Threshold | Graded by |
| --- | --- | --- |
| quote grounding over every returned quote, before routing | >= 95% | normalised substring match in the cited clause |
| recall@5 | >= 0.90 | expected clause id in top 5 |
| answer accuracy | >= 0.80 | expected value present and expected clause cited |
| refusal accuracy | >= 0.90 | exact refusal text on unanswerable, none on answerable |

## 3. Task class

Two components, each classified alone:
- Field extraction (US-00-002): extract.
- Question answering (US-00-004, US-00-005): retrieve and answer.

Date computation (US-00-003) is not a model task: code only (ADR-0007).

## 4. Approach

**Extraction.** Chosen: prompt only plus structured output (one call per contract, ADR-0008).

Reasons, in order of weight:
1. A whole contract (assumption: about 4,500 tokens) fits in one request, so retrieval adds nothing for extraction.
2. Code must read 10 fields as `{value, quote, clause_id}`, so the output is schema-constrained.
3. About 18 calls per full run keeps the budget trivial.

Rejected: no model (regex rules over the templates), because the same field is phrased many ways ("ninety (90) days", "three months prior"), and rules tuned to our own templates overstate the eval (design note, Approach C).

**Question answering.** Chosen: prompt plus retrieval plus structured output (answer text and a list of `[contract, clause]` citations).

Reasons, in order of weight:
1. Answers must cite clauses, which needs clause-level retrieval (REQ-018, REQ-019).
2. Citations as structured output let code check every citation against the retrieved set and refuse otherwise (REQ-020, REQ-021).

Rejected: prompt only with every contract in context, because 18 contracts make about 81,000 input tokens per question: assumption: USD 0.08 per question, so a 100-question eval run costs about USD 8 and breaks the USD 10 budget (ADR-0001). It also abandons the hybrid search the brief fixes.

## 5. Model and budget

Prices are OpenRouter's public list fetched on 2026-10-01 for `anthropic/claude-haiku-4.5`: USD 1.00 per million input tokens, USD 5.00 per million output, USD 0.10 per million cache reads. The project pays OpenRouter, so these prices are used instead of Anthropic's direct list.

| Item | Extraction | Q&A |
| --- | --- | --- |
| Model | `anthropic/claude-haiku-4.5` (ADR-0002) | `anthropic/claude-haiku-4.5` |
| Effort | no extended thinking | no extended thinking |
| Tokens in per request | assumption: 6,000 (system and schema 1,500, contract 4,500) | assumption: 2,150 (system 600, 5 clauses 1,500, question 50) |
| Tokens out per request | assumption: 1,500 | assumption: 250 |
| Calls per user action | 1 per contract loaded | 1 per question (0 when the cosine floor refuses) |
| Cost per request | USD 0.0135 | USD 0.0034 |
| Cost per 1,000 requests | USD 13.50 | USD 3.40 |
| p95 latency | assumption: 32 s (2 s first token, 1,500 tokens at 50 per second) | assumption: 7 s (2 s plus 250 tokens at 50 per second, plus under 0.1 s CPU embedding) |
| Cache strategy | stable system prompt and schema first; disk reply cache (ADR-0009) | same; retrieved clauses after the stable prefix |

Cost of one full live eval run (`make eval-live`), all assumptions:

| Part | Calls | Cost |
| --- | --- | --- |
| extraction, 18 contracts | 18 | USD 0.24 |
| Q&A, 30 questions (Q-020, chosen) | 30 | USD 0.10 |
| full run | 48 | USD 0.34 |

`make eval-live` calls the model only on cache misses, so a Q&A prompt change re-runs only Q&A (USD 0.10) and an extraction prompt change only extraction (USD 0.24). Against the USD 9 gateway stop this allows about 26 full runs, or about 90 Q&A-only and 37 extraction-only refreshes. This settles Q-023.

Smaller model considered: `google/gemini-3.1-flash-lite` (USD 0.25 / 1.50); right for Q&A if Haiku passes with margin, but wrong to start extraction on, because exact quotes in a 10-field schema are where a lighter model fails first and a miss costs a review item.

Runtime: one OpenRouter key with a USD 10 credit limit, held in `.env`; the gateway stops at USD 9 (Q-007). One-off budget, not monthly. GPU: none (embeddings on CPU, ADR-0004). Claude Code builds the project; it does not pay for the product's calls.

## 6. Risks

| Risk | Likelihood | Impact | Mitigation | Skill |
| --- | --- | --- | --- | --- |
| hallucination: invented quote or answer | M | H | quote check against the cited clause; answer citations checked against retrieved clauses; refusal when either fails | `llm-guardrails`, `llm-eval` |
| prompt injection in contract text | L | M | contract text wrapped as delimited data; no tools; test clause "Ignore previous instructions" (AC-US-00-005-3) | `llm-guardrails`, `prompt-registry` |
| PII | L | L | synthetic contracts only (PRD non-goal); logs hold contract ids and token counts, not text | `llm-gateway` |
| cost blow-up | L | H | USD 9 stop in the gateway, USD 10 key limit, disk cache, live calls only on misses | `llm-gateway` |
| latency: 30 s extraction blocks the upload page | M | L | 60 s gateway timeout, one retry, a progress message on upload | `llm-gateway` |
| wrong computed date | M | H | dates in code only; month-end and leap-year tests; unparsed fields to review | `llm-eval` |
| small Q&A set (30) makes the 0.80 and 0.90 gates noisy | M | M | report counts as hits over total beside each score; treat a one-question swing as noise; grow the set if a gate flips on reruns | `llm-eval` |
| synthetic templates overstate scores | H | M | varied phrasing per field; 5 of 18 contracts held out and never used while tuning prompts | `llm-eval` |
| stale or silently missed cache | M | M | key includes prompt version, model and full body; a miss fails `make check` | `llm-gateway` |
| refusal floor cannot separate questions | M | M | spike in US-00-005-D1; fallback to prompt refusal plus citation check (ADR-0005) | `llm-eval` |
| model id withdrawn or changed on OpenRouter | L | M | id pinned; cache keyed by model; switch path in ADR-0002 | `llm-gateway` |

Risks: 11. Mitigated: 11.

## 7. Evaluation plan

| Item | Extraction | Q&A |
| --- | --- | --- |
| Golden set size | 180 field items (18 contracts by 10 fields) | 30 questions (20 answerable, 10 unanswerable), chosen by the developer on 2026-10-01 below this skill's minimum of 100; one question moves a score by about 3 points |
| Source of items | generated contracts with `truth.json` (ADR-0006); real contracts are out of scope by the brief, so the "real inputs" rule is waived and the holdout split stands in | answerable questions generated from `truth.json` field values; unanswerable written by hand about topics no template covers |
| Grading | exact match after normalisation, by code; schema check on every reply | code: expected clause in top 5; expected value present and expected clause cited; exact refusal text |
| Threshold | at most 2 misses per field; grounding >= 95% | recall@5 >= 0.90, answer >= 0.80, refusal >= 0.90 |
| Runs on | every `make check` (cached), every prompt version and model change (`make eval-live`) | same |

Built by `llm-eval` in TASK-003 (extraction) and TASK-004 (Q&A); wired into `make check` in TASK-006.

## 8. Open questions

| Question | Owner | Needed by |
| --- | --- | --- |
| Replace token and latency assumptions with the gateway's measured numbers after the first live extraction run | Developer | end of TASK-002, day 2 |
| Is >= 95% grounding over returned quotes the right gate, or should it be stricter? | Developer | first extraction eval, TASK-003 |
