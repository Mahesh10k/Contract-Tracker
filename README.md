# ContractTracker

A learning project. It reads synthetic contracts (leases, vendor and service agreements),
extracts five key terms with the sentence each came from, computes notice deadlines in code,
emails reminders to a local mail catcher, and answers questions across all contracts with clause
citations, refusing with "Not found in these contracts" when the contracts do not say.
`make help` lists every command; `make check` is the gate.

## How it works

1. **Ingest.** `pypdf` reads text PDFs and a splitter cuts them into numbered clauses with page numbers.
2. **Extract.** One LLM call per contract returns `{value, quote, clause}` for parties, effective date,
   term, auto-renewal and notice period. Code checks that every quote is in the clause it cites;
   anything else goes to the Needs review tab. An unreadable reply is retried once, then held.
3. **Compute.** Expiry and notice deadline are worked out in code with python-dateutil. The model
   never computes a date.
4. **Remind.** Reminders at 60, 30 and 7 days go to MailHog. Each is sent once; a missed one is
   caught up; an expired deadline is skipped.
5. **Ask.** Clauses are embedded locally (`BAAI/bge-small-en-v1.5`, CPU). A question retrieves the
   5 closest clauses; below a similarity floor it is refused without calling the model. Otherwise the
   model answers only from those clauses and code checks every citation was one of them.

## Run it

Needs Python 3.12 with `uv`, Node 20 or later, and Docker.

```bash
cp .env.example .env           # then set OPENROUTER_API_KEY, LLM_BUDGET_STOP_USD=1.80 and LLM_BUDGET_SINCE
make setup                     # Python deps, git hooks and the embedding model (about 130 MB, once)
make web-install               # React deps
# If port 5432 is taken: export POSTGRES_PORT=5433 and set the same port in DATABASE_URL in .env
make db && make migrate        # Postgres 16 with pgvector
make mail                      # MailHog, the local mail catcher (web UI http://localhost:8025)
make contracts                 # only to regenerate the committed PDFs and answer key
make ui                        # API on :8080 and the page on http://localhost:5173
make check                     # the gate; make test-integration needs make db
```

The reply cache `llm_cache/` is committed, so extraction and the evals replay for free and need no
key. A live call needs `OPENROUTER_API_KEY`, is logged in `llm_calls`, and stops once spend since
`LLM_BUDGET_SINCE` reaches `LLM_BUDGET_STOP_USD`. Only `make eval-live` and a new question or
extraction on an uncached input spend money.

Other commands: `make extract NAMES="lease-01"`, `make embed`, `make ask Q="Which law governs
Supply Agreement 08?"`, `make remind TODAY=2026-10-31` (a date ahead of today is a preview that records nothing), `make eval-extraction`, `make eval-qa`,
`make eval-live`. Add `?mock=1` to the page URL (development) to view it with sample data and no API.

## Demo in five steps

1. **Start.** `make db && make migrate && make mail`, then `make ui`, and open http://localhost:5173.
2. **Load and read.** Upload tab, "Load the 6 golden contracts". Run `make extract` once (it replays
   the cache). On Contracts, pick Lease Agreement 01: five fields, each with its quote and clause.
3. **See what is held.** Needs review tab: Supply Agreement 08's auto renewal is held because that
   contract has no renewal clause. The system does not guess.
4. **Deadlines and reminders.** Deadlines tab: leave "Treat today as" on today's date and press "Send due
   reminders". Open http://localhost:8025 and read the email: contract, obligation, date, clause.
   Press again: "No reminders are due." (a reminder is sent once). Set the date box ahead of today
   to preview a later date: the emails go to MailHog but nothing is recorded, so pressing again
   sends them again, and your real reminders are left untouched.
5. **Ask and be refused.** Ask tab: "Which law governs Supply Agreement 08?" answers California with
   the clause text under it. Then "Does any contract include a non-compete?" answers "Not found in
   these contracts".

## Evals

See [EVALS.md](EVALS.md): extraction 6/6 on every field with 29/29 quotes grounded; Q&A recall@5 7/7,
answer accuracy 7/7, refusal accuracy 10/10. Both run in `make check` offline.

## Known limits

- **Small, template-shaped test set.** 6 contracts, 30 labelled fields, 10 questions. The scores are a
  regression floor, not proof of accuracy on real contracts.
- **Text PDFs only.** Scanned PDFs are refused (no OCR). English only.
- **Five fields.** Payment terms, escalation, liability cap, termination rights and governing law are
  not extracted (the one-day scope); renewal, escalation and payment dates are not computed.
- **No correction form.** The Needs review tab lists held fields with the reason; fixing one is not built.
- **Vector search only.** An exact term with little meaning (a code, a name) can rank low; hybrid
  search was left out of scope.
- **The refusal floor (0.70) was tuned on the 10 golden questions.** A real question worded unusually
  can score under it and be refused although the contracts hold the answer.
- **One user, local only.** No login, no scheduler (reminders go out when you press the button or run
  `make remind`), mail goes to MailHog and never to a real inbox, uploads are limited to 5 MB.
- **Torch is the default build.** `uv.lock` holds the CUDA build of PyTorch (about 5 GB); run
  `uv add torch` once on a machine that can reach download.pytorch.org to switch the lock to CPU.
- **A crash between emailing and recording** leaves that one reminder unsent, never sent twice.

## Documents

- `docs/product/`: PRD, open questions, backlog, tasks, coverage, user flows
- `docs/adr/`: decisions ADR-0001 to ADR-0016; index in `docs/architecture/decisions.md`
- `docs/genai/contracttracker-solution.md`: approach, cost, risks, eval plan
- `docs/design/`: data model, schema, data dictionary, ERD; `docs/design/variants/react-ui/`: the chosen look
- `docs/testing/`: risks, scenarios, cases and steps; `docs/progress/`: task progress

## Facts and where they come from

- Python 3.12: the brief asks for 3.11+, this machine has 3.12 (decided 2026-10-01).
- The one-day brief of 2026-10-05 narrowed the scope (5 fields, vector search, USD 2, 6 golden
  contracts); the original plan is kept in the PRD with withdrawn statements marked.
- PDFs are written with fpdf2, not reportlab: kept as built under Q-027 and ADR-0006.
- Git host GitHub; CODEOWNERS has no owner yet.
- Commits: `type(scope): subject [TASK-008]`, checked by `.githooks/commit-msg`.
