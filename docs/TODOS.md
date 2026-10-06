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

## Branch review of TASK-008, findings not fixed (2026-10-06)

Source: `bearing:branch-review` of feature/TASK-008-OneDayScope. Fixed in the same task: 1, 2, 3, 4, 6,
9, 10, 11, 15. Left, each with the reviewer's evidence in `.scratch/review/TASK-008/`:

- **5** Fetch effects in `web/src/panels.tsx` have no stale-response guard (an older answer can
  overwrite a newer one); loading shows the empty state. Pick it up with the next UI change.
- **7** Citation check keys clauses by (contract title, clause number); two contracts with the same title
  collide. Key by contract id and make titles unique at ingest.
- **8** `clauses` is capped at 12000 characters in the answer prompt; real clause sets can exceed it
  and answer 422. Drop the lowest-ranked hits until the block fits.
- **12** Filenames `..` or over 255 bytes return 500; write uploads under a fixed temp name.
- **13** Migration 0003: add `SET lock_timeout`, drop the stale Streamlit line, note the index decision
  for `clauses WHERE embedding IS NULL`.
- **14** Docstrings in `app/llm/gateway.py` and `app/extraction/cli.py` still say USD 9 and 10 fields.
- **16** `web/src/api.ts` casts responses (`as T`) instead of validating them.
- **17** Tabs lack `aria-controls` and arrow-key handling; the answer has no `aria-live`.
- **18** `tests/api/fakes.py` still has an unused `NotAvailableError`; the reminders route has no test for
  its 502 envelope. Also `evals/qa/run.py` counts an unreadable reply as a refusal, which the app does
  not (the app returns 502).
- `make check` rewrites `evals/*/last-run.*` on every run; `web/tsconfig.tsbuildinfo` is committed.

