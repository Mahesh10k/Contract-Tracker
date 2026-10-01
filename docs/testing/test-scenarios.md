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
| TS-US-00-001-3 | Error | Scanned, whitespace-only, non-PDF, truncated or empty files are refused with a message | a bad file never becomes a contract with missing text | AC-US-00-001-4, AC-US-00-001-6 | TC-0002, TC-0011, TC-0012, TC-0017, TC-0018, TC-0019, TC-0029, TC-0030, TC-0031 |
| TS-US-00-001-4 | Edge | Cross-references, decimals and hyphenated headings sit where pypdf breaks lines | clause boundaries follow the contract's own numbering, not stray numbers in its text | AC-US-00-001-2 | TC-0005, TC-0006, TC-0007, TC-0025, TC-0026, TC-0027, TC-0028 |
| TS-US-00-001-5 | Edge | Clause 7.2, the first, the last and a missing number are requested | a citation always resolves to exactly one clause's text, or says it does not exist | AC-US-00-001-3 | TC-0008, TC-0009, TC-0010 |
| TS-US-00-001-6 | Edge | The same bytes are loaded twice, under the same or another name, and a one-byte change is loaded | one file is one contract, so reminders are never doubled | AC-US-00-001-5 | TC-0014, TC-0015, TC-0016 |
| TS-US-00-001-7 | Security | Untrusted file bytes are parsed by the command | a malformed file ends in a message, never a traceback or a partial write | AC-US-00-001-6 | TC-0017, TC-0018, TC-0024 |
| TS-US-00-001-8 | Edge | The first migration upgrades, downgrades and upgrades again, and tests roll back | the schema every later task builds on is exactly docs/design/schema.sql, and tests do not leak rows | review T3, T4 | TC-0020, TC-0021, TC-0022, TC-0023 |

Not applicable: Performance: 18 small PDFs, no SLO in the PRD; Accessibility: no screen in this task (the upload page is US-00-007).
Invariants: a contract is stored with all its clauses or not at all (TC-0024).

## Needs rewording

Criteria with no testable expected result. Each one counts as uncovered
until the backlog is fixed.

- none
