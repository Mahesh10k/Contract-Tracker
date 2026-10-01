# Open questions: ContractTracker

PRD: docs/product/PRD.md   Updated: 2026-10-01
Entries: 26   Open: 12   Needs your confirmation: 0

Basis, for every entry:
- stated: the input answers it elsewhere; the passage that wins is named.
- inferred: only one reading is consistent with the rest of the input.
- convention: the input is silent and the team's standards settle it.
- assumption: nothing settles it; a choice was made so the team is not blocked.

## Needs your confirmation

None open.

## Confirmed by the developer

Confirmed on 2026-10-01 in the planning session: questions 1 to 9, 18 and 19 in
the register below (reminder timing, recipient and trigger; UI screens; review
corrections; eval thresholds; budget stop; scanned PDFs; meaning of obligation;
corrections win over re-extraction; reminder catch-up).

## Register

| Q | Status | Kind | Where | Basis | Question | Readings | Decision | Why | Affects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | confirmed | gap | REQ-016 | assumption | How long before a deadline is the reminder sent? | (a) fixed 30 and 7 days; (b) one fixed lead time; (c) set per contract | (a) 30 and 7 days before, configurable in settings | common practice for notice periods; two reminders give a second chance | US-00-006 |
| Q-002 | confirmed | gap | REQ-016 | assumption | Who receives reminders when there is no login? | (a) one address in `.env`; (b) an address per contract | (a) one address in `.env` | no users exist; one developer demo | US-00-006 |
| Q-003 | confirmed | gap | REQ-016 | assumption | What triggers reminders to be sent? | (a) a command run on demand; (b) an in-process scheduler; (c) a cron container | (a) `make remind` with an optional "today" date; each reminder sent once | demoable without waiting for real dates; no scheduler to run | US-00-006 |
| Q-004 | confirmed | gap | REQ-022 | assumption | What must the web UI let the user do? | (a) upload, contract view with fields and quotes, deadlines, review queue, ask; (b) read-only views plus ask | (a) | every REQ with a user-visible result needs a screen | US-00-007, US-00-008 |
| Q-005 | confirmed | gap | REQ-013, REQ-015 | assumption | What can the user do with a needs_review item? | (a) view only; (b) enter a corrected value that feeds date computation | (b) | without a correction path, unparsed contracts never get reminders | US-00-008 |
| Q-006 | confirmed | gap | REQ-023, REQ-024, REQ-025, REQ-026, REQ-027, REQ-028 | assumption | What eval scores count as passing? | (a) thresholds per metric; (b) report only, no pass or fail | (a) extraction 85% per field, grounding 100% of accepted fields, recall@5 0.90, answer 80%, refusal 90%; extraction and grounding restated by Q-015 | "Evals run under make check" needs a pass rule | US-02-001, US-02-002, US-02-003 |
| Q-007 | confirmed | gap | Constraints | assumption | How is the USD 10 budget enforced? | (a) gateway hard stop below the limit; (b) OpenRouter account limit only; (c) both | (c) gateway refuses calls once spend reaches USD 9, plus a USD 10 limit on the OpenRouter key | a hard budget needs a stop that code can test | US-00-002, US-00-004 |
| Q-008 | confirmed | gap | REQ-001 | assumption | What happens with a PDF that has no text layer? | (a) reject with a message; (b) ingest an empty contract | (a) reject with "No text found; scanned PDFs are not supported" | OCR is out of scope | US-00-001 |
| Q-009 | confirmed | gap | REQ-003 | assumption | What counts as an obligation? | (a) each dated duty derived from the fields; (b) every duty of each party in free text | (a) | the brief stores obligations alongside reminders, which need dates | US-00-003 |
| Q-010 | open | gap | REQ-021 | convention | What do the Q&A guardrails cover? | (a) refusal and citation check only; (b) plus treating contract text as data, not instructions | (b) an answer without a valid citation becomes the refusal; contract text is passed as quoted data | team convention for retrieval over uploaded documents | US-00-005 |
| Q-011 | open | gap | REQ-023, REQ-024, REQ-025, REQ-026, REQ-027 | stated | What are the evals judged against? | (a) `truth.json` per contract and a golden Q&A file; (b) LLM judge | (a) | D1.1 answer keys from templates | US-00-001, US-02-001, US-02-002 |
| Q-012 | open | gap | REQ-004 | inferred | Which dates are the key dates? | (a) effective date plus the five computed dates; (b) any date in the text | (a) | the brief lists exactly the dates code computes | US-00-003 |
| Q-013 | confirmed | open-question | REQ-022 | convention | Which web UI framework? | (a) FastAPI with Jinja; (b) Streamlit; (c) FastAPI, Jinja and HTMX | (a), chosen by the developer on 2026-10-01 (ADR-0011) | the brief asks for this decision | US-00-007, US-00-008 |
| Q-014 | confirmed | open-question | Constraints | convention | Which exact OpenRouter model? | (a) claude-haiku-4.5; (b) gpt-5.4-mini; (c) gemini-3.1-flash-lite; (d) gpt-5-mini | (a) pinned by exact id, chosen by the developer on 2026-10-01 (ADR-0002) | the brief asks for this decision | US-00-002, US-00-004 |
| Q-015 | open | gap | REQ-024 | convention | Critic: does the grounding gate test anything, and is 85% per field meaningful with about 17 samples? | (a) keep as written; (b) measure grounding over every LLM-returned quote before routing to review, and state extraction thresholds as maximum misses per field; experiment: flip 1 or 2 truth values in 17 rows and print the per-field score | (b) | grounding of accepted fields is 100% by construction; one miss moves a 17-sample score by 6 points | US-02-001 |
| Q-016 | open | gap | REQ-028 | convention | Critic: what does `make check` do on a cache miss, and how is the embedding model available offline? | (a) call live on a miss; (b) fail and list the missing keys, never call live; model fetched once by `make setup` into a local folder; experiment: change top-k from 5 to 6 and run `make check` with the network off | (b) | any change to splitting, embeddings or top-k changes the Q&A prompt hash | US-02-003 |
| Q-017 | open | gap | REQ-020 | convention | Critic: can one score floor separate answerable from unanswerable questions when fused scores are uncalibrated? | (a) floor on the fused score; (b) floor on top-1 cosine similarity, value set from a spike; if ranges overlap, rely on the prompt refusal plus citation check; experiment: top-1 scores for 10 answerable and 10 unanswerable questions over 20 contracts | (b), spike in TASK-004 | cosine has a fixed scale; rank fusion does not | US-00-005, US-02-002 |
| Q-018 | confirmed | gap | REQ-013 | assumption | Critic: does re-extraction overwrite a value the user corrected? | (a) re-extraction overwrites; (b) a user correction always wins and is kept | (b) | losing a manual correction silently would break trust in the dates | US-00-008 |
| Q-019 | confirmed | gap | REQ-016 | assumption | Critic: what happens to reminders when `make remind` is not run for a while, or a deadline is already within 7 days at upload? | (a) only reminders due exactly today are sent; (b) every unsent reminder due on or before today is sent once (catch-up) | (b) | B2 says no deadline passes without a reminder | US-00-006 |
| Q-020 | confirmed | gap | REQ-026, REQ-027 | convention | Critic: how big is the Q&A eval set and who writes it? | (a) 30 questions: 20 answerable generated from template truth, 10 unanswerable written by hand, budgeted in TASK-004; (b) 100 questions, the genai-design minimum | (a), kept by the developer on 2026-10-01 against the recommendation of (b); accepted that one question moves a score by about 3 points | fits 4 days; a third unanswerable per D1.4 | US-02-002 |
| Q-021 | open | contradiction | REQ-005, REQ-007 | inferred | Critic: effective_date is extracted by the LLM, but REQ-007 says no date comes from the LLM. | (a) the LLM returns the date text exactly as written plus its quote; code parses it into a date; (b) the LLM returns an ISO date | (a) | only reading consistent with "The LLM never computes dates" | US-00-002, US-00-003 |
| Q-022 | open | gap | REQ-008, REQ-009, REQ-010, REQ-011, REQ-012 | convention | Critic: python-dateutil does not parse durations such as "ninety (90) days prior to expiry"; who parses them? | (a) a small project parser for number words, digits and units, unit-tested, with failures sent to needs_review; (b) ask the LLM to normalise durations | (a) | (b) would break REQ-007 | US-00-003 |
| Q-023 | open | gap | Constraints | convention | Critic: how many `make eval-live` refreshes does USD 10 cover? | computed in the genai-design cost estimate | about 26 full runs at about USD 0.34 each (assumption until the first live run; docs/genai/contracttracker-solution.md) | decides whether prompt iteration is cheap | US-02-003 |
| Q-024 | open | gap | REQ-011, REQ-012 | convention | How far ahead are recurring escalation and payment dates computed? | (a) to the end of the current term; (b) a fixed horizon such as 24 months; (c) including renewal terms | (a); renewal terms get dates once the renewal date passes | bounded and testable; matches the term the contract states | US-00-003, US-00-006 |
| Q-025 | open | gap | Personas | convention | Who triggers the eval stories? The PRD names only the contract owner. | (a) a developer persona, group 02, inferred; (b) fold evals into owner stories | (a) | evals are run by whoever builds the product, not by the contract owner | US-02-001, US-02-002, US-02-003, US-02-004 |
| Q-026 | open | gap | REQ-001, REQ-022 | convention | Where does an uploaded contract's type (lease, vendor, service) come from? Raised by the data-model review. | (a) a required type picker on the upload form; (b) the model classifies it during extraction; (c) the type column is optional | (a) | no LLM call for something the owner knows; the column stays required for the contract list | US-00-001, US-00-007 |
