# Bearing skills used on ContractTracker

Source: the Skill calls made in the build conversation (2026-10-01 to 2026-10-12), written from the
conversation record and its summary, not from a tool log. Where a skill ran only partly, the row says so.

## Skills invoked

| Skill | Why it was used | Where it shows in the repository |
| --- | --- | --- |
| `prd` | Turn the brief into numbered, testable requirements, and re-scope it to the one-day brief | `docs/product/PRD.md`, REQ-045 to REQ-057 |
| `backlog` | Break requirements into stories with Given-When-Then criteria and a coverage table | `docs/product/backlog.md`, `coverage.md`, `tasks.md` |
| `adr` | Record each technology decision as a numbered ADR | `docs/adr/0012` to `0016`, `decisions.md` |
| `doctor` | Check the machine and repository for the workflow | start of the one-day plan |
| `start-task` | Create the task branch with the task id and restate the criteria | TASK-001 onward |
| `test-cases` | Write TC-numbered manual test cases and risks from the acceptance criteria | `docs/testing/` |
| `bearing-backend:python` | Load the Python house rules before writing Python | extraction, reminders, Q&A, login |
| `bearing-apps:react` | Load the React rules before changing the frontend | `web/` |
| `prompt-registry` | Keep prompts in a versioned folder with scores | `prompts/` |
| `llm-eval` | Golden sets and code graders so accuracy is measured | `evals/`, `EVALS.md` |
| `rag` | Retrieval design: embeddings, similarity floor, citation check | `app/retrieval/`, `app/qa/` |
| `design-directions` | Three visual directions, scored, with the choice recorded | `docs/design/variants/react-ui/` |
| `design-system` | Tokens, contrast measurement, generated CSS, component page, colour lint | `docs/design/`, `make design-lint` |
| `architecture-diagram` | Sequence diagram of Browser, API, Redis and PostgreSQL (drawn from the description, no files written) | conversation only |
| `health-checks` | Invoked with no scope; only inventoried what exists and asked | no files |
| `definition-of-done` | Check a branch against the done list with evidence | before the TASK-008 review |
| `branch-review` | Independent review with verifier agents confirming each serious finding | TASK-008 review fixes |
| `traceability` | Check requirement, story, case, test and commit links | after the review |
| `merge-request` | Pull request description, commit audit and push commands | TASK-008 |

## Scripts used from other skills (the skill itself was not invoked)

- `prose-lint`'s checker: no em dashes, filler or praise in documents.
- The `backlog` coverage gate and the `traceability` gate: documents stay consistent.
- The `design-system` scripts: contrast, CSS generation, the component page.
- `session-handoff`'s progress script: marked TASK-008 "in review".

## Skills that applied and were not invoked

- `auth`, for the login (TASK-013): designed from the agreed plan instead.
- `db-migration`, for migration 0004: written by hand in the repository's header style.
- `tech-decision`, for the login choice: questions were asked directly and ADR-0017 written afterwards.
- `runbook`, for `docs/runbooks/deploy.md`: written by hand.

A later review of the login against the `auth` skill would close the first gap.
