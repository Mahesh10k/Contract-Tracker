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
