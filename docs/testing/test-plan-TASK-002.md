# Test plan: ContractTracker TASK-002 Extraction

Backlog: `docs/product/backlog.md` as of 2026-10-05   Cases: docs/testing/test-cases.md
Version: v1   Author: unattributed

## 1. Headline

Scenarios: 15 (7 new for US-00-002, 8 carried from US-00-001)
test-cases: 7 ACs, 7 with cases, 56 live cases, 56 with oracles, 5 risks (high 2, medium 3, low 0), 0 threats traced from 0 threat models, 0 problems
test-types: unit 15, integration 41, e2e 0, manual 0; by machine 56 (automated 56, planned 0), by hand 0

The counts lines cover the whole table (TASK-001's 34 automated cases plus TASK-002's 22 planned ones, TC-0035 to TC-0056); the 7 ACs and 5 risks are US-00-002's.

## 2. Risk summary

| Risk | Story | What could go wrong | Level | Cases |
| --- | --- | --- | --- | --- |
| R-007 | US-00-002 | A quote the model made up, or took from another clause, is accepted as grounded | High | TC-0044, TC-0045, TC-0042 |
| R-008 | US-00-002 | Spend escapes the USD 9 stop | High | TC-0049, TC-0051, TC-0055 |

Medium: 3 (R-009, R-010, R-011; US-00-002)   Low: 0

## 3. Scenarios

US-00-001 rows are carried unchanged from docs/testing/test-plan.md (TASK-001, merged); they keep running in every gate.

| Scenario | Story | Title | Proves that | Cases | Run by |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-002-1 | US-00-002 | One call, 10 fields | every contract gets all 10 fields, each traceable to a clause | TC-0035, TC-0038 | machine |
| TS-US-00-002-2 | US-00-002 | Retry and cache | a single bad reply or a repeat run costs no extra correctness | TC-0036, TC-0046, TC-0054 | machine |
| TS-US-00-002-3 | US-00-002 | Failed extraction | a failed extraction stores nothing and says why | TC-0052, TC-0053, TC-0055, TC-0056 | machine |
| TS-US-00-002-4 | US-00-002 | Quote check | only a quote really in its cited clause is accepted | TC-0037, TC-0039, TC-0043, TC-0044, TC-0045 | machine |
| TS-US-00-002-5 | US-00-002 | Normaliser | layout noise is ignored and real wording differences are not | TC-0040, TC-0041, TC-0042 | machine |
| TS-US-00-002-6 | US-00-002 | Budget stop | no call is made once recorded spend reaches USD 9 | TC-0049, TC-0050, TC-0051 | machine |
| TS-US-00-002-7 | US-00-002 | Cache key | a cached answer is never reused for a different prompt or model | TC-0047, TC-0048 | machine |
| TS-US-00-001-1 | US-00-001 | Generated lease loaded | every contract becomes clauses that answers can later cite exactly | TC-0001, TC-0004 | machine |
| TS-US-00-001-2 | US-00-001 | Short contract with explicit type | short contracts load as well as long ones | TC-0003, TC-0013 | machine |
| TS-US-00-001-3 | US-00-001 | Bad files refused | a bad file never becomes a contract with missing text | TC-0002, TC-0011, TC-0012, TC-0017, TC-0018, TC-0019, TC-0029, TC-0030, TC-0031, TC-0034 | machine |
| TS-US-00-001-4 | US-00-001 | Stray numbers in clause text | clause boundaries follow the contract's own numbering, not stray numbers in its text | TC-0005, TC-0006, TC-0007, TC-0025, TC-0026, TC-0027, TC-0028, TC-0032, TC-0033 | machine |
| TS-US-00-001-5 | US-00-001 | Clause lookup | a citation always resolves to exactly one clause's text, or says it does not exist | TC-0008, TC-0009, TC-0010 | machine |
| TS-US-00-001-6 | US-00-001 | Duplicate files | one file is one contract, so reminders are never doubled | TC-0014, TC-0015, TC-0016 | machine |
| TS-US-00-001-7 | US-00-001 | Untrusted file bytes | a malformed file ends in a message, never a traceback or a partial write | TC-0017, TC-0018, TC-0024 | machine |
| TS-US-00-001-8 | US-00-001 | First migration and test isolation | the schema every later task builds on is exactly docs/design/schema.sql, and tests do not leak rows | TC-0020, TC-0021, TC-0022, TC-0023 | machine |

## 4. Entry criteria

- `make db POSTGRES_PORT=55432 && make migrate POSTGRES_PORT=55432` succeed (developer).
- Recorded replies for the extraction prompt v1 exist under the test fixtures; no test reaches the network (developer).

## 5. Exit criteria

- Every case above passes under `make check` and `make test-integration`; the gate prints 0 problems.
- No live OpenRouter call happened without the developer's OK; spend for the task is reported.

## 6. Environments

Local: Python 3.12 (uv), Docker Compose pgvector/pgvector:pg16 on port 55432. CI: GitHub Actions unit and integration jobs. No browser matrix: no screen in this task.

## 7. What QA raised

- [assumption] The retry button in AC-US-00-002-7 belongs to the web UI (US-00-007, TASK-005); TASK-002 delivers the message and a re-runnable extract command.
- [assumption] A timed-out attempt reports no usage, so its cost is estimated from the request size and the price table; the data model refuses a live call recorded at 0 (chk_llm_calls_live_call_costed).
- [risk] Recorded replies are written by us; a real model reply can differ in shape. One live run (with the developer's OK) refreshes them before the eval in TASK-003.
- [undefined] The exact failure message wording ("model timed out", "model unavailable (503)", "reply did not match the schema") is this plan's; the backlog fixes only "Extraction failed: <reason>".
