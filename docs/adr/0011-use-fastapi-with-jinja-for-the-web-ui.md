# ADR-0011: Use FastAPI with Jinja templates for the web UI

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), in tech-decision on 2026-10-01
- Area: frontend
- Reversibility: cheap: five server-rendered pages over the same services; a different UI can call the same service functions

## Context

- REQ-022 and Q-004 (confirmed) need five screens: upload, contract view, deadlines, review queue with a correction form, ask.
- The Bearing python-api stack is FastAPI. US-00-007-T1 and US-00-008-T1 need page tests that run in `make check`.
- About one day of TASK-005 is available for UI; one developer, 4 days in total.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| FastAPI with Jinja templates (chosen) | HTML forms and CSS are written by hand; about half a day more than Streamlit | simple forms and tables served by the same app, tested with TestClient |
| Streamlit | a second app with its own rerun model; UI tests need AppTest or manual checks; logic leaks into UI scripts | a data dashboard where UI speed matters more than tests |
| FastAPI, Jinja and HTMX | one more library to learn in 4 days | partial page updates, such as an inline review-queue correction |
| React with Vite (catalogue default) | a separate build and a JSON API for five simple pages | a larger, interactive authenticated app |

## Decision

We will render the five screens with Jinja templates from the FastAPI app, because it keeps one stack and one process, pages are tested in `make check` with the same tools as the API, and each screen is a plain form or table.

## Consequences

- Page handlers call the same service functions as the CLI; no business logic in templates.
- No JavaScript build step; minimal CSS.
- Revisit if a screen needs live updates without reload: add HTMX to that screen.

## Commits us to

FastAPI, Jinja2 (outside the standard stack), Starlette TestClient
