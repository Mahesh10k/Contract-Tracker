# ADR-0017: Sign in with scrypt passwords and a signed session cookie

- Status: Accepted
- Date: 2026-10-12
- Task: TASK-013
- Deciders: Developer (project owner), after asking for a login page on 2026-10-12
- Supersedes: none (the brief's "login out of scope" is withdrawn in the PRD, Q-040)
- Area: backend, frontend
- Reversibility: easy: sessions are stateless and the users table stands alone

## Context

- The app is now reachable on public addresses (Render for the API, Netlify for the page) and every Ask or extraction can call a paid model through the owner's OpenRouter key. The PRD had login out of scope.
- The developer chose accounts with email and password, no sign-up page, and users created by the owner from the command line (Q-040).
- The page and the API are served from one origin (the Vite proxy in development, the Netlify rule in production), so the browser treats the session cookie as first-party.
- AGENTS.md rule 7: no dependency nobody asked for.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| scrypt from the standard library, signed cookie (chosen) | no server-side session list, so a copied cookie works until it expires | a small app with few users |
| argon2 or bcrypt library | a new dependency to pin and audit for no gain at this size | a team with a security baseline that names it |
| A sessions table | instant sign-out everywhere, but more code, a table and a query on every request | many users or a strict revocation requirement |
| One shared password | no per-person accounts or audit | a demo behind one secret |
| Google or GitHub sign-in | an OAuth app and redirect URLs on two hosts | a public product |

## Decision

We will store users in Postgres with a salted scrypt hash (standard library `hashlib.scrypt`, N=2^14, r=8, p=1), sign a session token with HMAC-SHA256 and send it as an HttpOnly, SameSite=Lax cookie (Secure in production) that lasts 12 hours, and require it on every `/api` route except login and the health checks. The owner creates users with `make user`; there is no sign-up.

## Consequences

- New `users` table (migration 0004), `app/auth/`, `app/api/auth/`, a `require_user` dependency on the UI router, and a Login page in `web/`.
- New settings: `SESSION_SECRET` (required, at least 32 characters, when ENV=production), `SESSION_TTL_HOURS`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCK_MINUTES`.
- Every failed sign-in gets the same message; an unknown email still pays for one hash check. Five wrong passwords lock the account for 15 minutes. The lock is per account, not per address, so someone who knows an email can lock its owner out for 15 minutes at a time.
- Logging out clears the cookie but cannot recall a copy of it; a stolen cookie works until it expires. Rotating `SESSION_SECRET` signs everyone out.
- Free hosting keeps a single worker, so no shared state is needed between workers.
- Revisit if there are many users, if instant revocation is required, or if the page moves to a different origin from the API (then CORS, a SameSite=None cookie and a CSRF token are needed).

## Commits us to

`hashlib.scrypt` (Python standard library) and no new package.
