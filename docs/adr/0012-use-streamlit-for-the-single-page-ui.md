# ADR-0012: Use one Streamlit page with five tabs for the UI

- Status: Superseded by ADR-0016 on 2026-10-05
- Date: 2026-10-05
- Task: TASK-008
- Deciders: Developer (project owner), fixed in the one-day brief of 2026-10-05
- Supersedes: ADR-0011
- Area: frontend
- Reversibility: cheap: the page calls the same service functions as the CLI; a different UI can replace it without touching services

## Context

- From the request: "Streamlit single-page UI" and "Streamlit page with tabs: Upload, Contracts (fields + quotes), Deadlines, Ask, Needs review; a \"send due reminders\" button that emails MailHog."
- The scope shrank to one day (2026-10-05). ADR-0011 chose FastAPI with Jinja for five screens with a correction form; the brief drops corrections from today's scope (US-00-008 AC-1 only).
- Services are async (SQLAlchemy 2 async). Streamlit reruns a synchronous script on every interaction.
- Page tests must run in `make check` without a browser.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Streamlit, one page, five tabs (chosen) | a second process beside the API; its rerun model means each action calls services through `asyncio.run` | a one-day demo where UI speed matters more than a polished app |
| FastAPI with Jinja (ADR-0011) | about half a day more for forms and CSS, which the day does not have | the multi-day plan with a correction form |

## Decision

We will build the UI as one Streamlit page with the tabs Upload, Contracts, Deadlines, Ask and Needs review, because the brief fixes it, it fits in the day, and its AppTest harness lets the page be tested in `make check`.

## Consequences

- No business logic in the page: each tab calls one service function through a small sync adapter that runs the coroutine.
- Page tests use `streamlit.testing.v1.AppTest` with services faked.
- The FastAPI app stays for health checks; it serves no pages.
- Revisit if corrections (US-00-008 AC-2 to 4) come back into scope: a form per held field fits Streamlit too.

## Commits us to

Streamlit (outside the standard stack)
