# ADR-0016: Use a React single-page app (Vite, TypeScript, Tailwind) for the UI

- Status: Accepted
- Date: 2026-10-05
- Task: TASK-008
- Deciders: Developer (project owner), after asking for React on 2026-10-05
- Supersedes: ADR-0012
- Area: frontend
- Reversibility: awkward: the UI moves to its own `web/` app and a JSON API; going back to Streamlit means rewriting the page, not the services

## Context

- From the request: "update the UI with react and make it beautiful". ADR-0012 chose one Streamlit page because the one-day brief fixed it and time was short.
- The five tabs (Upload, Contracts, Deadlines, Ask, Needs review) and the reminders button stay (REQ-052, REQ-053). The services, read queries and `deadlines_from` already exist and are tested.
- Streamlit called services through a sync adapter; a browser app needs an HTTP JSON API, and FastAPI is already the stack.
- Node 24 and npm 11 are installed. The coverage gate sits at 80.28% against 80%, so new Python routes ship with tests.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Vite, React, TypeScript, Tailwind (chosen) | a second toolchain (Node) and about 9 JSON routes to build and test | a polished, interactive UI that can grow |
| Streamlit (ADR-0012) | limited control over layout and look; reruns the script on every click | a one-day demo where speed beats polish |
| Next.js | server rendering and routing a local one-page app does not need; heavier to run | a public, multi-page, SEO-facing site |
| Vite, React, plain CSS | more hand-written styling for the same result | a team with a design system already |

## Decision

We will build the UI as a React single-page app in `web/` that calls a FastAPI JSON API under `/api`, because the owner asked for React and a polished look, and the existing services already map one to one onto API routes.

## Consequences

- New `app/api/ui/` routers with Pydantic schemas call the same services; no logic in the browser beyond display.
- `make check` also runs eslint, tsc and vitest through `make web-check`; CI needs Node 20 or later.
- Vite proxies `/api` to the FastAPI app in development, so no CORS settings are needed.
- Streamlit, `app/ui/page.py`, its AppTest tests and the dependency are removed; `app/ui/views.py` stays.
- Revisit if the UI needs server rendering or auth: that is when Next.js or a session layer comes in.

## Commits us to

React, Vite, TypeScript, Tailwind CSS, Vitest, Testing Library, ESLint (all outside the standard stack)
