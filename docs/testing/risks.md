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
| R-001 | US-00-001 | A cross-reference ("as set out in clause 7.2") or a decimal ("3.5 percent") in clause text is taken for a heading, so answers later cite the wrong text | AC-US-00-001-2, AC-US-00-001-3, new code, TASK-001 review findings 3 to 5 | M | M | Medium | TC-0005, TC-0006, TC-0008, TC-0025, TC-0026, TC-0027, TC-0028 |
| R-002 | US-00-001 | pypdf breaks lines or hyphenates differently from the source, so stored clause text drifts from truth.json and quotes later fail | AC-US-00-001-2, ADR-0006, new integration | M | M | Medium | TC-0004, TC-0007 |
| R-003 | US-00-001 | Loading the same file twice creates two contracts, so every reminder is sent twice | AC-US-00-001-5 | L | M | Low | TC-0014 |
| R-004 | US-00-001 | A scanned, corrupt or non-PDF file is half stored or crashes the command, leaving a contract with no clauses | AC-US-00-001-4, AC-US-00-001-6, external input, TASK-001 review finding 2 | M | M | Medium | TC-0011, TC-0017, TC-0018, TC-0024, TC-0029, TC-0030, TC-0031 |
| R-005 | US-00-001 | Migration 0001 fails on the vector extension or its downgrade leaves objects behind, blocking every later task and CI | review T3, T1, change size | M | M | Medium | TC-0020, TC-0021 |
| R-006 | US-00-001 | Integration tests stop rolling back, so rows leak between tests and failures become random | review T4 | L | M | Low | TC-0023 |
