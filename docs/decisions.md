# Decision log

One row per technology decision. The ADR holds the full reasoning; this
table is the index. `tech-decision` maintains it.

| Date | Key | Choice | Recommended | Why it was chosen | ADR | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-01 | frontend | FastAPI with Jinja | FastAPI with Jinja | one stack and process; pages tested in make check | ADR-0011 | Accepted |
| 2026-10-01 | llm provider and models (model) | anthropic/claude-haiku-4.5, pinned | anthropic/claude-haiku-4.5 | the Haiku the brief names; about 25 live runs fit USD 9; exact quoting | ADR-0002 | Accepted |
