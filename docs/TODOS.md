# TODOs

Deferred work agreed in planning. Each item says what, why, and when to pick it up.

## Remove unused scaffold dependencies (after TASK-006)

- **What:** remove opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http,
  opentelemetry-instrumentation-fastapi and gunicorn from pyproject.toml, with
  app/core/telemetry.py, its test and the Dockerfile CMD that uses gunicorn.
- **Why:** none of them is asked for by the brief or an ADR (AGENTS.md rule 7).
- **Pros:** smaller install, less template code to learn.
- **Cons:** about an hour; touches template tests.
- **Context:** tracing is off unless OTEL_EXPORTER_OTLP_ENDPOINT is set; gunicorn
  runs only in the Docker image, which the plan never builds. Start at
  pyproject.toml dependencies and app/core/telemetry.py.
- **Depends on:** TASK-006 done, so nothing new depends on them.
- **Source:** /plan-eng-review 2026-10-01, decision D10.

## TASK-001 review leftovers (low severity)

- **What:** four low findings from the TASK-001 branch review, kept for a later task.
  - Two concurrent loads of the same file: the second gets "Contract could not be
    stored (uq_contracts_file_sha256)" instead of "Already loaded as"; map that
    unique violation to the already-loaded result (app/ingestion/service.py).
  - `get_clause` for an unknown contract id says "Clause 1 not found in " with a
    blank name; raise "Contract not found" instead.
  - Readiness returns 500, not 503, when the database refuses the password
    (asyncpg InvalidPasswordError is outside the caught types in
    app/api/health/router.py). Scaffold defect, seen in the TASK-001 smoke run.
  - Only integrity refusals are logged; unreadable, no-text and type-required
    refusals leave no log line.
- **Why:** none blocks TASK-002; each is a clearer message or log, not wrong data.
- **Depends on:** nothing. **Source:** TASK-001 branch review, 2026-10-01.
