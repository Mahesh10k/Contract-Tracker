# ADR-0005: Retrieve clauses with hybrid search (pgvector plus Postgres full-text) and a cosine floor for refusal

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief; floor approach from the critic (Q-017)
- Area: search
- Reversibility: cheap: retrieval is one function; changing the fusion changes the Q&A cache keys, so one live eval run follows

## Context

- From the request: "Q&A: hybrid search (pgvector + Postgres full-text), answers cite [contract, clause], refuse with \"Not found in these contracts\"."
- Contract questions mix exact terms ("governing law", "Delaware") with paraphrase ("can I get out early?"); AC-US-00-004-2 and AC-US-00-004-3 test both halves.
- Q-017: fused scores from vector and full-text ranking are not on a calibrated scale, so the refusal floor uses top-1 cosine similarity, set by a spike of 10 answerable and 10 unanswerable questions.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Hybrid: pgvector cosine plus Postgres full-text, fused by rank, top 5 (chosen) | two rankings to fuse and tune | mixed exact-term and paraphrase questions |
| Vector search only | misses exact terms such as party names and statute names | paraphrase-heavy questions with no named entities |
| Full-text only | misses paraphrase | keyword lookups only |

## Decision

We will retrieve the top 5 clauses by fusing pgvector cosine ranking with Postgres full-text ranking, and refuse without an LLM call when the top-1 cosine similarity is below a floor set by the TASK-004 spike, because the brief fixes hybrid search and cosine is the only score with a stable scale.

## Consequences

- recall@5 (REQ-025) measures this function directly.
- If the spike shows answerable and unanswerable ranges overlap, the floor is dropped and refusal relies on the prompt and the citation check (Q-010).
- Revisit if recall@5 is below 0.90.

## Commits us to

pgvector, PostgreSQL full-text search (tsvector, ts_rank)
