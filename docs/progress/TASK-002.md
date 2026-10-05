# Progress: TASK-002 Extraction

- Task: TASK-002
- Title: Extraction
- Branch: feature/TASK-002-Extraction
- Status: in review
- Owner: Mahesh Pikki
- Started: 2026-10-05
- Updated: 2026-10-05
- Acceptance criteria: 7

## Next
- address review comments

## Done
- LLM gateway (app/llm): timeout, one retry, disk cache, llm_calls ledger, USD 9 stop
- Prompt registry and extract_fields v1 (draft, seed 10/10 render)
- Extraction service and make extract; quote check with normalise_for_match
- 56 cases automated; make check passed, coverage 81.31%

## Blockers
- none

## Decisions
- TOML frontmatter for prompts (no new YAML dependency)
- httpx moved to runtime dependencies (approved)
- Spend recorded in its own session so a failed extraction still counts
- Retry button deferred to TASK-005; re-run make extract retries

## Links
- MR: none
- Ticket: none
