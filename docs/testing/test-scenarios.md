# Test scenarios

Source: `docs/product/backlog.md` as of 2026-10-01. One block per story. Written by
`test-cases`; change the backlog, not this file, to change a scenario.
Each row names the cases in `test-cases.md` that cover it.

## US-00-001: Load a contract PDF and get numbered clauses

Requirements: REQ-001, REQ-002
Acceptance criteria: AC-US-00-001-1, AC-US-00-001-2, AC-US-00-001-3, AC-US-00-001-4, AC-US-00-001-5, AC-US-00-001-6

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-001-1 | Happy | A generated lease is loaded and split into its numbered clauses | every contract becomes clauses that answers can later cite exactly | AC-US-00-001-1, AC-US-00-001-2 | TC-0001, TC-0004 |
| TS-US-00-001-2 | Alternate | A one-page, one-clause contract is loaded with an explicit type | short contracts load as well as long ones | AC-US-00-001-1 | TC-0003, TC-0013 |
| TS-US-00-001-3 | Error | Scanned, whitespace-only, non-PDF, truncated or empty files are refused with a message | a bad file never becomes a contract with missing text | AC-US-00-001-4, AC-US-00-001-6 | TC-0002, TC-0011, TC-0012, TC-0017, TC-0018, TC-0019, TC-0029, TC-0030, TC-0031, TC-0034 |
| TS-US-00-001-4 | Edge | Cross-references, decimals and hyphenated headings sit where pypdf breaks lines | clause boundaries follow the contract's own numbering, not stray numbers in its text | AC-US-00-001-2 | TC-0005, TC-0006, TC-0007, TC-0025, TC-0026, TC-0027, TC-0028, TC-0032, TC-0033 |
| TS-US-00-001-5 | Edge | Clause 7.2, the first, the last and a missing number are requested | a citation always resolves to exactly one clause's text, or says it does not exist | AC-US-00-001-3 | TC-0008, TC-0009, TC-0010 |
| TS-US-00-001-6 | Edge | The same bytes are loaded twice, under the same or another name, and a one-byte change is loaded | one file is one contract, so reminders are never doubled | AC-US-00-001-5 | TC-0014, TC-0015, TC-0016 |
| TS-US-00-001-7 | Security | Untrusted file bytes are parsed by the command | a malformed file ends in a message, never a traceback or a partial write | AC-US-00-001-6 | TC-0017, TC-0018, TC-0024 |
| TS-US-00-001-8 | Edge | The first migration upgrades, downgrades and upgrades again, and tests roll back | the schema every later task builds on is exactly docs/design/schema.sql, and tests do not leak rows | review T3, T4 | TC-0020, TC-0021, TC-0022, TC-0023 |

Not applicable: Performance: 18 small PDFs, no SLO in the PRD; Accessibility: no screen in this task (the upload page is US-00-007).
Invariants: a contract is stored with all its clauses or not at all (TC-0024).

## US-00-002: Extract the 10 fields with a checked quote each

Requirements: REQ-005, REQ-006, REQ-014, REQ-015, REQ-038
Acceptance criteria: AC-US-00-002-1, AC-US-00-002-2, AC-US-00-002-3, AC-US-00-002-4, AC-US-00-002-5, AC-US-00-002-6, AC-US-00-002-7

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-002-1 | Happy | One call extracts the 10 fields with value, quote and clause | every contract gets all 10 fields, each traceable to a clause | AC-US-00-002-1, AC-US-00-002-2 | TC-0035, TC-0038 |
| TS-US-00-002-2 | Alternate | A bad reply is retried once, or a cached reply is reused | a single bad reply or a repeat run costs no extra correctness | AC-US-00-002-5, AC-US-00-002-7 | TC-0036, TC-0046, TC-0054 |
| TS-US-00-002-3 | Error | The model times out, returns 5xx or fails the schema twice | a failed extraction stores nothing and says why | AC-US-00-002-7 | TC-0052, TC-0053, TC-0055, TC-0056 |
| TS-US-00-002-4 | Edge | Quotes differ by layout only, are made up, or cite the wrong or a missing clause | only a quote really in its cited clause is accepted | AC-US-00-002-2, AC-US-00-002-3, AC-US-00-002-4 | TC-0037, TC-0039, TC-0043, TC-0044, TC-0045 |
| TS-US-00-002-5 | Edge | Normalisation of line breaks, hyphens and quotes | layout noise is ignored and real wording differences are not | AC-US-00-002-3 | TC-0040, TC-0041, TC-0042 |
| TS-US-00-002-6 | Edge | Spend at, just under and across USD 9 | no call is made once recorded spend reaches USD 9 | AC-US-00-002-6 | TC-0049, TC-0050, TC-0051 |
| TS-US-00-002-7 | Security | Prompt or model change against the reply cache | a cached answer is never reused for a different prompt or model | AC-US-00-002-5 | TC-0047, TC-0048 |

Not applicable: Performance: about 18 calls per full run, no SLO in the PRD; Accessibility: no screen in this task (the retry button is US-00-007).
Invariants: a contract has 10 extraction rows or none (TC-0056); every live call is recorded with its cost (TC-0051, TC-0055).

## US-02-005: Plant hard cases in the golden set

Requirements: REQ-031, REQ-032, REQ-033, REQ-034, REQ-035, REQ-036
Acceptance criteria: AC-US-02-005-1, AC-US-02-005-2, AC-US-02-005-3, AC-US-02-005-4, AC-US-02-005-5, AC-US-02-005-6, AC-US-02-005-7

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-005-1 | Happy | The set is regenerated with five planted contracts | the eval holds relative dates, notice elsewhere, an amendment, a page break and no renewal | AC-US-02-005-1, AC-US-02-005-2, AC-US-02-005-3, AC-US-02-005-4, AC-US-02-005-6 | TC-0057, TC-0058, TC-0059, TC-0060, TC-0062, TC-0064 |
| TS-US-02-005-2 | Edge | A clause crosses the page break | splitting does not cut a clause at a page boundary | AC-US-02-005-5 | TC-0061, TC-0065 |
| TS-US-02-005-3 | Error | Regeneration touches an existing contract | earlier answers and cached replies stay valid | AC-US-02-005-7 | TC-0063 |

Not applicable: Security, Performance, Accessibility: generated test data only, no input, screen or SLO.
Invariants: the 18 original contracts never change bytes (TC-0063).

## US-00-009: See which page a clause is on

Requirements: REQ-037
Acceptance criteria: AC-US-00-009-1, AC-US-00-009-2, AC-US-00-009-3

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-009-1 | Happy | A clause on one page gets that page | a citation points at the page the clause is printed on | AC-US-00-009-1 | TC-0066 |
| TS-US-00-009-2 | Edge | A clause or its heading crosses a page | a crossing clause is one clause with both pages | AC-US-00-009-2 | TC-0067, TC-0068, TC-0070 |
| TS-US-00-009-3 | Alternate | Rows stored before migration 0002, or text with no pages | no page is guessed | AC-US-00-009-3 | TC-0069, TC-0071 |

Not applicable: Security: no new input path; Performance: two integer columns; Accessibility: no screen (pages appear in the UI in TASK-005).
Invariants: first_page <= last_page or both NULL (chk_clauses_pages_ordered).

## US-02-006: Pick the 6-contract golden set and its answer key

Requirements: REQ-054, REQ-055
Acceptance criteria: AC-US-02-006-1, AC-US-02-006-2, AC-US-02-006-3, AC-US-02-006-4

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-006-1 | Happy | `make contracts` writes the answer key for 2 leases, 2 vendor and 2 service contracts | every eval and the demo run on the same six files | AC-US-02-006-1 | TC-0072 |
| TS-US-02-006-2 | Error | A golden id the generator did not write | a typo in the golden list fails loudly instead of shrinking the set | AC-US-02-006-1 | TC-0073 |
| TS-US-02-006-3 | Edge | Holdout contracts and the two hard cases | the set holds the traps and none of the held-out contracts | AC-US-02-006-1, AC-US-02-006-2 | TC-0074, TC-0075 |
| TS-US-02-006-4 | Happy | Key values equal truth.json, 5 fields only | the eval scores against the generator's own truth | AC-US-02-006-3 | TC-0076, TC-0077 |
| TS-US-02-006-5 | Edge | The no-renewal contract has no auto_renewal quote | a missing clause is expected as null, not as an empty string | AC-US-02-006-3 | TC-0078 |
| TS-US-02-006-6 | Alternate | The generator runs twice | the key is byte-identical, so cached replies and scores stay comparable | AC-US-02-006-4 | TC-0079 |

Not applicable: Security: no input from users; Performance: six records; Accessibility: no screen.
Invariants: every golden id has a truth.json; the key lists exactly the 5 fields of REQ-045 per contract.

## US-00-010: Extract the 5 one-day fields; unreadable replies go to review

Requirements: REQ-045, REQ-046
Acceptance criteria: AC-US-00-010-1, AC-US-00-010-2, AC-US-00-010-3, AC-US-00-010-4

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-010-1 | Happy | A valid v2 reply gives 5 rows | the owner sees exactly the 5 fields the brief asks for | AC-US-00-010-1 | TC-0080 |
| TS-US-00-010-2 | Error | A reply missing a field or adding one | a wrong shape never reaches storage | AC-US-00-010-1 | TC-0081, TC-0082 |
| TS-US-00-010-3 | Error | Two invalid replies in a row | the contract is held for review, never dropped | AC-US-00-010-2 | TC-0083, TC-0084, TC-0089 |
| TS-US-00-010-4 | Alternate | A timeout twice | only an unreadable reply goes to review; an outage stays an error to retry | AC-US-00-010-2 | TC-0085 |
| TS-US-00-010-5 | Alternate | Invalid first reply, valid retry | one bad reply costs a retry, not a review | AC-US-00-010-3 | TC-0086 |
| TS-US-00-010-6 | Edge | Notice period stated in clause 2.3 | the quote is checked where it was found | AC-US-00-010-4 | TC-0087, TC-0088, TC-0103 |

Not applicable: Performance: one call per contract; Accessibility: no screen.
Security: contract text is model input; v2 keeps v1's data-not-instructions rule and injection flag (Q-010).
Invariants: every extracted contract has exactly 5 field rows; an accepted row has a quote found in its cited clause.

## US-00-003: See the computed key dates and obligations

Requirements: REQ-003, REQ-004, REQ-007, REQ-008, REQ-009, REQ-013
Acceptance criteria: AC-US-00-003-1, AC-US-00-003-2, AC-US-00-003-3, AC-US-00-003-4, AC-US-00-003-6, AC-US-00-003-7

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-00-003-1 | Happy | Effective date plus term gives expiry | expiry is the last day of the term, computed in code | AC-US-00-003-1 | TC-0091, TC-0102 |
| TS-US-00-003-2 | Edge | Leap years and month ends | a deadline never lands after the real one | AC-US-00-003-1, AC-US-00-003-3 | TC-0092, TC-0096 |
| TS-US-00-003-3 | Happy | Notice in days and in months | days count days, months count calendar months | AC-US-00-003-2, AC-US-00-003-4 | TC-0094, TC-0095, TC-0097 |
| TS-US-00-003-4 | Error | Text no parser understands | nothing is guessed; the field waits for a person | AC-US-00-003-6 | TC-0093, TC-0098, TC-0099 |
| TS-US-00-003-5 | Happy | Each dated duty becomes one obligation with its clause | every deadline can be traced to the contract | AC-US-00-003-7 | TC-0100, TC-0101, TC-0104 |

Not applicable: Security: no new input path; Performance: two dates per contract; Accessibility: no screen.
Invariants: the LLM output is never a date; notice_deadline <= expiry.

## US-02-001: Measure extraction accuracy and quote grounding

Requirements: REQ-024, REQ-057
Acceptance criteria: AC-US-02-001-1, AC-US-02-001-2, AC-US-02-001-3, AC-US-02-001-4

| Scenario | Category | What happens | Proves that | ACs | Cases |
| --- | --- | --- | --- | --- | --- |
| TS-US-02-001-1 | Happy | Model output equal to the key scores full; empty output scores zero | the graders measure the field, not the wording | AC-US-02-001-1 | TC-0105, TC-0106, TC-0107 |
| TS-US-02-001-2 | Error | A field over its allowed misses, or no cases at all | the gate stops a regression and never passes on nothing | AC-US-02-001-2, AC-US-02-001-1 | TC-0108, TC-0109, TC-0112 |
| TS-US-02-001-3 | Happy | Grounding over every returned quote | a made-up quote lowers the number even when it is later held | AC-US-02-001-3 | TC-0110, TC-0114 |
| TS-US-02-001-4 | Alternate | One truth value changed | the score moves by exactly one, so the eval is sensitive | AC-US-02-001-4 | TC-0111 |
| TS-US-02-001-5 | Happy | The run over the 6 golden contracts from the cache | the number in EVALS.md comes from the real prompt and model | AC-US-02-001-1 | TC-0113 |

Not applicable: Security: no user input; Performance: 6 calls; Accessibility: no screen.
Invariants: the eval builds the same request as the app (same cache key); a cache miss offline fails, never calls live.

## Needs rewording

Criteria with no testable expected result. Each one counts as uncovered
until the backlog is fixed.

- none
