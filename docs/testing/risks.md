# Test risks

Source: `docs/product/backlog.md` as of 2026-10-01; threat models: none.
Ids are permanent; a risk that no longer applies keeps its row with level
`Low` and "closed: <reason>" in the risk text.

## How the level is set

Likelihood (L, M, H) is how probable the failure is, from the evidence named
in the row: the size of the change, branching or concurrency in it, a new
integration or dependency, defects in the same files (`git log --grep=fix`
over the paths), and how settled the requirement is.
Impact (L, M, H) is what it costs when it happens: H for money, auth, data
loss, PII or a legal duty; M for a core flow; L for cosmetics.

| Likelihood / Impact | L | M | H |
| --- | --- | --- | --- |
| L | Low | Low | Medium |
| M | Low | Medium | High |
| H | Medium | High | High |

Depth by level, counted in live cases: High needs three, one with a `not:`
oracle and one of type integration or e2e; Medium needs two, one with a
`not:` oracle; Low needs one.

## Register

No git history touches these paths yet (one commit, no fixes), so likelihood comes from the change and the requirement.

| Risk | Story | What could go wrong | Source | Likelihood | Impact | Level | Cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | US-00-001 | A cross-reference ("as set out in clause 7.2") or a decimal ("3.5 percent") in clause text is taken for a heading, so answers later cite the wrong text | AC-US-00-001-2, AC-US-00-001-3, new code, TASK-001 review findings 3 to 5 | M | M | Medium | TC-0005, TC-0006, TC-0008, TC-0025, TC-0026, TC-0027, TC-0028, TC-0032, TC-0033 |
| R-002 | US-00-001 | pypdf breaks lines or hyphenates differently from the source, so stored clause text drifts from truth.json and quotes later fail | AC-US-00-001-2, ADR-0006, new integration | M | M | Medium | TC-0004, TC-0007 |
| R-003 | US-00-001 | Loading the same file twice creates two contracts, so every reminder is sent twice | AC-US-00-001-5 | L | M | Low | TC-0014 |
| R-004 | US-00-001 | A scanned, corrupt or non-PDF file is half stored or crashes the command, leaving a contract with no clauses | AC-US-00-001-4, AC-US-00-001-6, external input, TASK-001 review finding 2 | M | M | Medium | TC-0011, TC-0017, TC-0018, TC-0024, TC-0029, TC-0030, TC-0031, TC-0034 |
| R-005 | US-00-001 | Migration 0001 fails on the vector extension or its downgrade leaves objects behind, blocking every later task and CI | review T3, T1, change size | M | M | Medium | TC-0020, TC-0021 |
| R-006 | US-00-001 | Integration tests stop rolling back, so rows leak between tests and failures become random | review T4 | L | M | Low | TC-0023 |
| R-007 | US-00-002 | A quote the model made up, or took from another clause, is accepted as grounded, so a wrong deadline drives a missed notice | AC-US-00-002-4, B3, new LLM integration | M | H | High | TC-0044, TC-0045, TC-0042 |
| R-008 | US-00-002 | Spend escapes the USD 9 stop because a retry or a failed attempt is not logged, or the stop is checked after the call | AC-US-00-002-6, AC-US-00-002-7, Q-007 | M | H | High | TC-0049, TC-0051, TC-0055 |
| R-009 | US-00-002 | A cached reply survives a prompt or model change, so extraction and the eval keep using the old prompt's answers | AC-US-00-002-5, Q-028, ADR-0009 | M | M | Medium | TC-0047, TC-0048 |
| R-010 | US-00-002 | A failed extraction leaves some field rows behind, so a contract looks half extracted | AC-US-00-002-7 | M | M | Medium | TC-0052, TC-0056 |
| R-011 | US-00-002 | The shared normaliser is too lax (drops digits or words), so "90 days" matches "30 days" | review task T5, AC-US-00-002-3 | L | H | Medium | TC-0042, TC-0040 |
| R-012 | US-02-005 | Regenerating the set changes an existing contract, so every cached reply and earlier score silently stops matching | AC-US-02-005-7, change size | M | H | High | TC-0063, TC-0061, TC-0068 |
| R-013 | US-02-005 | A planted case does not actually contain its trap (the clause fits on one page, the quote sits in the notice clause), so the eval overstates hard-case coverage | AC-US-02-005-3, AC-US-02-005-5 | M | M | Medium | TC-0059, TC-0061 |
| R-014 | US-00-009 | A clause crossing a page is split in two or given the wrong page, so a citation sends the owner to the wrong page | AC-US-00-009-2, new migration | L | M | Low | TC-0067 |
| R-015 | US-02-006 | The golden set leaves out a hard case or a type, so the eval reports a score that never exercised the trap the brief asked for | AC-US-02-006-1, AC-US-02-006-2, change size | M | M | Medium | TC-0072, TC-0073, TC-0074, TC-0075 |
| R-016 | US-02-006 | The answer key drifts from truth.json (a hand edit, a missing field, a non-deterministic write), so the extraction eval scores against wrong values | AC-US-02-006-3, AC-US-02-006-4 | L | H | Medium | TC-0076, TC-0077, TC-0078, TC-0079 |
| R-017 | US-00-010 | A reply that is still invalid after the retry leaves the contract with no field rows, so it silently drops out of deadlines and review | AC-US-00-010-2, REQ-046, changes a done behaviour (AC-US-00-002-7) | M | H | High | TC-0083, TC-0084, TC-0085, TC-0089 |
| R-018 | US-00-010 | Prompt v2 and its schema disagree on the field set, so every reply fails validation or a field is never asked for | AC-US-00-010-1, new prompt version | L | M | Low | TC-0080, TC-0081, TC-0082 |
| R-019 | US-00-010 | In the notice-elsewhere contract the quote is checked against the notice clause instead of the clause it was taken from, so a correct field is held or a wrong one accepted | AC-US-00-010-4, hard case vendor-07 | M | H | High | TC-0087, TC-0088, TC-0086, TC-0103 |
| R-020 | US-00-003 | Date arithmetic is off by a day or mishandles a month end, so the notice deadline shown is after the real one and notice is missed | AC-US-00-003-1 to AC-US-00-003-4, REQ-007, new code | M | H | High | TC-0091, TC-0092, TC-0094, TC-0096, TC-0097, TC-0102, TC-0104 |
| R-021 | US-00-003 | Text no parser understands is turned into a guessed date instead of being held for review | AC-US-00-003-6, Q-022 | L | H | Medium | TC-0093, TC-0098, TC-0099 |
| R-022 | US-00-003 | An obligation is stored without the clause it came from, or twice, so the deadline cannot be checked or is reminded twice | AC-US-00-003-7 | L | M | Low | TC-0100, TC-0101 |
| R-023 | US-02-001 | A grader too lenient (any text matches) or too strict (wording differences count as misses) makes the accuracy number meaningless | AC-US-02-001-1, AC-US-02-001-4, new graders | M | H | High | TC-0105, TC-0106, TC-0107, TC-0111, TC-0113 |
| R-024 | US-02-001 | The eval passes with nothing measured (zero cases, a cache miss skipped) or fails to stop on a field over its limit | AC-US-02-001-2, gate-audit concern | L | H | Medium | TC-0108, TC-0109, TC-0112 |
| R-025 | US-02-001 | Grounding is counted only over accepted fields, so it reads 100 percent by construction (Q-015) | AC-US-02-001-3, Q-015 | M | M | Medium | TC-0110, TC-0114 |
