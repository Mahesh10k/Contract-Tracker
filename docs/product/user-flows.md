# User flows

Backlog: docs/product/backlog.md   Built: 2026-10-01
Flows: 6   Screens named: 6

## Flow F1: Load a new contract (EP-01)

Persona: Contract owner, group 00   Platforms: desktop web
Trigger: the owner signs a new lease and has its PDF.
Exercises: US-00-001, US-00-007

### Before it starts

- Docker Compose is up (Postgres, MailHog) and the web app is running.

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Upload | chooses the lease PDF and submits | stores the contract and its numbered clauses | US-00-001 |
| 2 | Contract list | sees the new lease | lists it with its type "lease" | US-00-007 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | the owner loads contracts from the command line instead | `ingest <file>` stores it the same way | US-00-001 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 1 | the PDF is scanned, with no text layer | "No text found; scanned PDFs are not supported" | upload a text PDF | US-00-001 |
| 1 | the same file was loaded before | told the contract already exists; no duplicate | open the existing contract | US-00-001 |

### Afterwards

The contract and its clauses are stored and listed; extraction can run.

## Flow F2: See what a contract obliges me to do (EP-02)

Persona: Contract owner, group 00   Platforms: desktop web
Trigger: a contract has just been loaded.
Exercises: US-00-002, US-00-003, US-00-007, US-00-008

### Before it starts

- The contract is loaded (F1).

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Contract view | opens the contract | shows 10 fields, each with value, quote and clause number | US-00-002, US-00-007 |
| 2 | Contract view | reads the obligations | lists expiry, notice, renewal, escalation and payment dates with their clauses | US-00-003 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | a field is marked "needs review" | the owner opens the review queue, enters the right value, and the dates are recomputed | US-00-008 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 1 | the LLM budget is reached | "LLM budget reached"; no fields extracted | raise the cap or replay from cache | US-00-002 |
| 1 | a quote is not in its clause | field marked "needs review" with "quote not found in clause" | correct it in the review queue | US-00-008 |
| 2 | a duration cannot be parsed | field marked "needs review" with "could not parse"; no date shown | correct it in the review queue | US-00-008 |

### Afterwards

Every field is either grounded with a quote or in the review queue; every parseable dated duty is an obligation.

## Flow F3: Get reminded before a notice deadline (EP-03)

Persona: Contract owner, group 00   Platforms: email (MailHog)
Trigger: a notice deadline is 30 days away.
Exercises: US-00-006

### Before it starts

- Obligations with dates exist (F2); `REMINDER_TO` is set in `.env`.

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Terminal | runs `make remind` | sends the 30-day reminder for each due obligation and records it as sent | US-00-006 |
| 2 | MailHog inbox | opens the email | shows contract, obligation, date and clause | US-00-006 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | `make remind` was not run for a while | every unsent reminder due on or before today is sent once | US-00-006 |
| 1 | it is run twice the same day | the second run sends nothing | US-00-006 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 1 | MailHog is not running | the command fails with the SMTP error; nothing is marked sent | start MailHog and run again | US-00-006 |

### Afterwards

Each due reminder is in MailHog exactly once and recorded as sent.

## Flow F4: Ask a question across contracts (EP-04)

Persona: Contract owner, group 00   Platforms: desktop web
Trigger: the owner wants to know which contracts can be ended early.
Exercises: US-00-004, US-00-005, US-00-007

### Before it starts

- Contracts are loaded and their clauses embedded.

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Ask | types the question and submits | retrieves the top 5 clauses by hybrid search | US-00-004 |
| 2 | Ask | reads the answer | shows the answer with [contract, clause] citations linking to clause text | US-00-004, US-00-007 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | the contracts do not hold the answer | the reply is exactly "Not found in these contracts" | US-00-005 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 2 | the model reply has no valid citation | "Not found in these contracts" | rephrase the question | US-00-005 |
| 1 | the LLM budget is reached | "LLM budget reached" | raise the cap | US-00-004 |

### Afterwards

The owner has a cited answer or the refusal; nothing uncited is shown.

## Flow F5: Check upcoming deadlines (EP-05)

Persona: Contract owner, group 00   Platforms: desktop web
Trigger: the owner starts the week and wants to see what is due.
Exercises: US-00-007

### Before it starts

- Obligations exist (F2).

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Deadlines | opens the page | lists every upcoming date soonest first with contract and clause | US-00-007 |
| 2 | Contract view | clicks a deadline | opens the contract at the clause the date comes from | US-00-007 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | no obligations exist yet | the page says there are no upcoming deadlines | US-00-007 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 1 | the database is down | an error page naming the database | start Docker Compose | US-00-007 |

### Afterwards

The owner knows the next deadlines and where each comes from.

## Flow F6: Check quality before a change lands (EP-06)

Persona: Developer (inferred:), group 02   Platforms: terminal
Trigger: the developer changed a prompt or the search settings.
Exercises: US-02-001, US-02-002, US-02-003, US-02-004

### Before it starts

- The reply cache and the embedding model are present (`make setup`).

### Steps

| Step | Screen | The user | The system | Story |
| --- | --- | --- | --- | --- |
| 1 | Terminal | runs `make check` | prints per-field extraction counts and grounding | US-02-001, US-02-003 |
| 2 | Terminal | reads the Q&A lines | prints recall@5, answer accuracy and refusal accuracy against thresholds | US-02-002, US-02-003 |

### Alternate paths

| At step | Condition | What happens | Story |
| --- | --- | --- | --- |
| 1 | the change altered prompts | the developer runs `make eval-live` to refresh the cache, sees USD spent, then reruns `make check` | US-02-003 |
| 2 | preparing a demo | follows the README on a fresh clone | US-02-004 |

### When it fails

| At step | Condition | What the user sees | Recovery | Story |
| --- | --- | --- | --- | --- |
| 1 | cache keys are missing | `make check` fails listing the missing keys; no network call | run `make eval-live` | US-02-003 |
| 2 | a metric is below threshold | non-zero exit naming the metric | fix the change or revert it | US-02-002 |

### Afterwards

The change either passes every threshold offline or is blocked with the failing metric named.

## Counts

Flows: 6   Steps: 12   Alternate paths: 8   Failure paths: 11   Unhandled failures: 0
