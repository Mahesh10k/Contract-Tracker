# Runbook: deploy ContractTracker for free

Written for: the project owner, doing the first deploy by hand. Every step that needs an account,
a secret or a push is yours; nothing here is run by an agent.

## What gets deployed

| Part | Where | Source |
|---|---|---|
| Database (Postgres + pgvector) | Supabase, session pooler | migrations in `alembic/` |
| Backend (FastAPI, embedding model, prompts) | Hugging Face Space (Docker) | `Dockerfile` at the repository root |
| Frontend (React) | Netlify | `web/`, build `npm run build`, publish `web/dist` |

The browser calls `/api` on the Netlify address. Netlify forwards those calls to the Space
(`web/public/_redirects`), so the backend needs no CORS settings.

## Before you start

1. The repository on GitHub holds the Dockerfile and `web/public/_redirects` (merge their pull request).
2. Rotate any key or password that was ever pasted into a chat, an issue or a screenshot.
3. Create the OpenRouter key for this deploy and set a credit limit on it in the OpenRouter dashboard.
   The app has no login: anyone who finds the URL can trigger paid model calls.

## Secrets (set in the host's settings, never in git)

| Name | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?ssl=require` |
| `OPENROUTER_API_KEY` | the new key |
| `LLM_BUDGET_STOP_USD` | `1.80` |
| `LLM_BUDGET_SINCE` | the day the budget starts, for example `2026-10-05` |
| `LLM_MODEL` | `anthropic/claude-haiku-4.5` |
| `ENV` | `production` |
| `REMINDER_TO`, `REMINDER_FROM` | the addresses for reminders (email is not sent anywhere real yet) |

Do not set `PRETEND_TODAY` in production. `SMTP_HOST` stays unset until a mail provider and an SMTP login
setting exist (see Known limits).

## 1. Database (Supabase)

1. Create a project and a database password of letters and digits.
2. SQL Editor: `create extension if not exists vector with schema public;`
3. Project Settings, Database, Connection string: choose **Session pooler** (it is IPv4 and supports
   prepared statements). The user is `postgres.<project-ref>`.
4. Project Settings, API: turn the **Data API off**. The tables live in `public`, which Supabase
   otherwise publishes to anyone with the project's public key.
5. From your machine, with the URL in `.env` (form above):
   ```
   set -a; . ./.env; set +a
   make migrate
   ```
   Expected: `Running upgrade` for 0001, 0002 and 0003.

## 2. Backend (Hugging Face Space)

1. Create a Space, SDK **Docker**, visibility as you prefer.
2. Settings, Variables and secrets: add every name in the table above as a secret.
3. A Space reads its settings from a `README.md` with front matter at the root of its own repository,
   so deploy from a throwaway branch that carries `deploy/hf-space-README.md` as the README.
   From the repository root:
   ```
   git remote add space https://huggingface.co/spaces/<user>/<space>
   git switch -c chore/TASK-011-SpaceDeploy main
   cp deploy/hf-space-README.md README.md
   git add README.md
   git commit -m "chore(deploy): space readme [TASK-011]"
   git push space chore/TASK-011-SpaceDeploy:main
   git switch main
   ```
   When Hugging Face asks for a password, use an access token with write permission
   (huggingface.co, Settings, Access Tokens). Do not put the token in the remote URL.
4. Watch the build log in the Space. The build downloads the CPU torch wheel and the embedding model
   and takes several minutes.
5. Check `https://<user>-<space>.hf.space/api/contracts`. A `[]` or a list of contracts means the
   backend reaches the database.

To redeploy after a change: merge to `main`, then repeat step 3 (the throwaway branch is rebuilt from `main`).

## 2b. Backend on Render (instead of a Hugging Face Space)

Use this when a Docker Space is not available to you. `render.yaml` at the repository root describes the service.

1. Merge the branch that holds `render.yaml` and the Dockerfile into `main`, so GitHub has them.
2. Render dashboard, New, **Blueprint**, connect the GitHub repository, choose `main`. Render reads `render.yaml`.
   (Without a blueprint: New, Web Service, runtime Docker, instance type Free, region Singapore,
   health check path `/api/contracts`, and add the same variables by hand.)
3. Render asks for the two secret values: `DATABASE_URL` (the Supabase session pooler form from step 1)
   and `OPENROUTER_API_KEY` (the new key). Do not set `PORT`: Render sets it and the container reads it.
4. Create. The first build downloads the CPU torch wheel and the embedding model and takes several minutes.
5. Open `https://contracttracker-api.onrender.com/api/contracts` (use the address Render shows).
   A list or `[]` means the backend reaches the database.
6. In the service's **Metrics** tab, watch memory while you press "Load the 6 golden contracts" and ask one
   question. The free instance has 512 MB. A log line "Ran out of memory" means the embedding model does
   not fit: move to the Starter instance, or use another host.
7. In `web/public/_redirects` use `https://contracttracker-api.onrender.com/api/:splat`.

Render-specific notes:
- A free service sleeps after about 15 minutes without traffic and needs about a minute to wake. Netlify
  cuts a proxied request after about 26 seconds, so open the backend address once to wake it before using
  the Netlify page.
- `autoDeploy` is off: deploy by hand (Manual Deploy) after you merge, so a push cannot ship by surprise.

## 3. Frontend (Netlify)

1. Open `web/public/_redirects` and replace `YOUR-USER-YOUR-SPACE.hf.space` with your Space host.
   Commit that change and merge it.
2. Netlify, Add new site, Import from Git, pick the repository.
   Base directory `web`, build command `npm run build`, publish directory `web/dist`.
3. Deploy, then open the Netlify address.

## Verify (about five minutes)

1. Upload tab: press "Load the 6 golden contracts". Expect the six contract titles.
2. Contracts tab: pick "Lease Agreement 01", press "Extract fields". It replays from `llm_cache`
   and costs nothing.
3. Deadlines tab: rows appear. Press "Send due reminders" and expect a message, not an error.
4. Ask tab: "Which law governs Supply Agreement 08?" gives California with a citation, and
   "Does any contract include a non-compete?" gives "Not found in these contracts".
5. In the OpenRouter dashboard check the key's usage: it should still be near zero.

## Operating notes

- **Sleep.** A free Space sleeps when idle and a free Supabase project pauses after about a week
  without activity. Wake the Space by opening it. Restore the project in the Supabase dashboard.
- **Cost.** The gateway stops live calls at `LLM_BUDGET_STOP_USD` counted since `LLM_BUDGET_SINCE`.
  The credit limit on the OpenRouter key is the backstop if that setting is wrong.
- **Rotating a secret.** Create the new value, update the host's secret, restart the Space, then
  delete the old value. For the database password also update your local `.env`.
- **Proxy timeout.** Netlify cuts a proxied request after about 26 seconds. A live extraction that
  takes longer shows an error in the page even though the backend finishes. Replays are fast.

## Rollback

- Frontend: Netlify, Deploys, publish an earlier deploy.
- Backend: push the previous commit to the Space (`git push space <earlier-commit>:main --force` is a
  history rewrite on the Space remote only, and it is yours to decide), or set the Space to private.
- Database: `make migrate-down` goes back one migration. Take a Supabase backup first if the data matters.

## Known limits

- There is no login. Keep the URLs private or put basic auth in front before sharing.
- Reminder email is not delivered: the mailer has no SMTP login setting, and free mail providers need one.
- The Dockerfile runs as uid 10001. If the Space logs a permission error when the app writes
  `llm_cache` (a live model call), the container user needs write access to that folder.
- One worker by default (`WEB_CONCURRENCY=1`) because each worker loads its own copy of the model.

## If something fails

| Symptom | Cause | Fix |
|---|---|---|
| Space shows "Building" for a long time | first build downloads torch and the model | wait, read the build log |
| `/api/contracts` returns `internal error` | the log line names it, usually the database | open the Space logs, find the `request_id` |
| `connection refused` in the log | wrong host in `DATABASE_URL` | use the Supabase session pooler host |
| `password authentication failed` | wrong password or user | user is `postgres.<project-ref>`; reset the password |
| `type "vector" does not exist` | extension missing | run the `create extension` line in step 1 |
| Page loads but every panel errors | `_redirects` still has the placeholder host | step 3.1 |
| 404 on `/api/...` from Netlify | `_redirects` not in `web/dist` | confirm `web/public/_redirects` is committed and rebuild |
