# Architecture decisions: ContractTracker

One row per decision, and every contradiction settled once so it is not
settled again, differently, in each file that runs into it.

## Decisions

| Id | Title | Area | Status | Reversibility |
| --- | --- | --- | --- | --- |
| ADR-0001 | Use OpenRouter as the only LLM provider, capped at USD 10 | llm provider and models | Accepted; cap superseded by ADR-0014 when accepted | cheap: one gateway module; reply cache refreshed |
| ADR-0002 | Use anthropic/claude-haiku-4.5, pinned by exact id | llm provider and models | Accepted | cheap: one setting; one live eval run to refill the cache |
| ADR-0003 | Use Postgres 16 with pgvector for all stored data and vectors | database | Accepted | awkward: every table, migration and query would move |
| ADR-0004 | Embed clauses locally with BAAI/bge-small-en-v1.5 on CPU | vector store and embeddings | Accepted | cheap at this size: re-embed a few hundred clauses |
| ADR-0005 | Retrieve clauses with hybrid search and a cosine floor for refusal | search | Superseded by ADR-0013 | cheap: one function; one live eval run |
| ADR-0006 | Read text PDFs with pypdf, from synthetic contracts with answer keys | document ingestion | Accepted | cheap: one module; set regenerated |
| ADR-0007 | Compute every date in code with python-dateutil and a duration parser | date computation | Accepted | cheap: one module |
| ADR-0008 | Extract all 10 fields in one call per contract and verify quotes in code | llm extraction | Accepted; field count superseded by ADR-0015 when accepted | cheap: per-field extraction can replace it field by field |
| ADR-0009 | Cache LLM replies on disk so make check runs evals offline | evaluation | Accepted | cheap: delete the folder and run live once |
| ADR-0010 | Send reminder email over SMTP to MailHog | email, sms, push, payments | Accepted | cheap: SMTP settings |
| ADR-0011 | Use FastAPI with Jinja templates for the web UI | frontend | Superseded by ADR-0012 | cheap: five pages over the same services |
| ADR-0012 | Use one Streamlit page with five tabs for the UI | frontend | Accepted | cheap: the page calls the same services as the CLI |
| ADR-0013 | Retrieve the top 5 clauses by vector similarity, refuse below a cosine floor | search | Accepted | cheap: one function; one live eval run |
| ADR-0014 | Cap LLM spend at USD 2 for the one-day build | llm provider and models | Proposed | cheap: two settings |
| ADR-0015 | Extract 5 fields with a new prompt version, keeping v1 | llm extraction | Proposed | cheap: one prompt file and one schema |

## Conflicts that were settled

### Whether effective_date may come from the LLM when REQ-007 says no date does

**Between:** REQ-005, REQ-007, US-00-002, US-00-003, ADR-0007
**Decision.** The LLM returns the date text exactly as written with its quote; code parses it.
**Why.** Only reading consistent with "The LLM never computes dates" (Q-021).
**Settled by:** Developer, in planning on 2026-10-01 (Q-021, inferred)
**What now has to change to match:**
- none; US-00-002 and US-00-003 criteria already follow it.
