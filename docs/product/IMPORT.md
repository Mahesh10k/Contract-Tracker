# Importing the backlog: ContractTracker

6 epics, 14 stories, 70 tasks, from 44 statements in the PRD.
Gate: stories-coverage: 44 REQ from docs/product/PRD.md (0 withdrawn), 44 covered, 0 out of scope, 0 gaps, 14 stories, 72 AC, 0 orphans, 0 problems

## The files

| File | What it holds | How it imports |
| --- | --- | --- |
| PRD.md | the normalised requirements, REQ-001 to REQ-030 | attach to the project as the source document |
| backlog.md | story index, delivery tasks TASK-001 to TASK-006, epics and stories with criteria | tracker-sync sync (epics, then stories; writes Ticket: back), or read only for this solo project |
| tasks.md | development and test tasks, hours TBD | CSV import of the exported table, parent = story key, or read only |
| coverage.md | what became of every REQ, and why | read only |
| questions.md | open points, the decision taken, what it rests on | read only |
| user-flows.md | six journeys with alternate and failure paths | read only; the UI work in TASK-005 follows it |

## Steps

1. Commit docs/product/ so the ids are versioned (step 7 creates the repository).
2. No tracker is named for this project; if one is added, run `tracker-sync sync` for epics and stories, then import tasks with the story as parent.
3. Work the delivery tasks in order TASK-001 to TASK-006; owners and dates are yours to set.

## Before you commit

- None. Every assumption was confirmed on 2026-10-01.

## Still open

- Q-013 web UI framework and Q-014 exact model: closed in step 4 (tech-decision).
- Q-023 how many live eval refreshes USD 10 covers: closed in step 5 (genai-design).
- Q-017 refusal score floor: closed by the spike in US-00-005-D1.
- Q-010, Q-011, Q-012, Q-015, Q-016, Q-020, Q-021, Q-022, Q-024, Q-025: team conventions recorded as decisions; the developer can overturn any of them.

## Out of scope

- OCR of scanned PDFs (PRD non-goal).
- Login or user accounts (PRD non-goal).
- Real email delivery (PRD non-goal).
- Multi-turn chat (PRD non-goal).
- Real contract data (PRD non-goal).
- Obligations without a date (Q-009).
