# ContractTracker

A learning project: read synthetic contracts, extract obligations and key
dates with quotes, email reminders before deadlines, and answer questions
across contracts with clause citations or the refusal "Not found in these
contracts". `make help` lists every command; `make check` is the gate.

## What exists today

The Bearing `python-api` skeleton only: a FastAPI app with `/healthz` and
`/readyz`, settings, structured logging, Alembic with a probe migration, and
their tests. No ContractTracker feature is built yet.

```
cp .env.example .env
make setup            # needs uv; installs Python 3.12 deps and git hooks
make db && make migrate
make dev              # http://localhost:8080 (/healthz, /readyz, /docs)
```

`docker compose up -d` starts Postgres 16 with pgvector on 5432 and MailHog
(SMTP 1025, web UI http://localhost:8025).

## Planned

Built task by task from `docs/product/backlog.md`:

| Task | Delivers |
| --- | --- |
| TASK-001 | synthetic contracts, ingestion, clause splitter |
| TASK-002 | extraction, prompt registry, LLM gateway, quote check |
| TASK-003 | date computation, extraction eval |
| TASK-004 | embeddings, hybrid search, cited Q&A, guardrails, Q&A eval |
| TASK-005 | reminders and web UI |
| TASK-006 | final evals, traceability, README demo |

The planned schema is `docs/design/schema.sql`; it replaces the probe
migration in TASK-001.

## Documents

- `docs/product/`: PRD, open questions, backlog, tasks, coverage, user flows
- `docs/adr/`: decisions ADR-0001 to ADR-0011; index in `docs/architecture/decisions.md`
- `docs/genai/contracttracker-solution.md`: approach, cost, risks, eval plan
- `docs/design/`: data model, schema, data dictionary, ERD
- `docs/designs/contracttracker.md`: the office-hours design note

## Facts and where they come from

- Python 3.12: the brief asks for 3.11+, this machine has 3.12 (decided 2026-10-01).
- Port 8080: the kit default; no port registry exists in this workspace.
- Git host GitHub; CODEOWNERS has no owner yet.
- Commits: `type(scope): subject [TASK-001]`, checked by `.githooks/commit-msg`.
