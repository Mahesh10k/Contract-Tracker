# ADR-0013: Retrieve the top 5 clauses by vector similarity, refuse below a cosine floor

- Status: Accepted
- Date: 2026-10-05
- Task: TASK-008
- Deciders: Developer (project owner), fixed in the one-day brief of 2026-10-05
- Supersedes: ADR-0005
- Area: search
- Reversibility: cheap: retrieval is one function; changing it changes the Q&A cache keys, so one live eval run follows

## Context

- From the request: "Q&A: vector search top 5, answer only from retrieved clauses, cite [contract, clause], reply \"Not found in these contracts\" below a similarity threshold or when the clauses don't answer it." and "Out of scope: ... hybrid search".
- Clauses are embedded with BAAI/bge-small-en-v1.5 (ADR-0004), 384 dimensions, normalised, stored in pgvector.
- The golden set is 6 contracts, about 60 clauses; a sequential scan is fast at this size.
- Q-017: cosine has a fixed scale, so a floor on top-1 cosine can be set from a spike; a fused rank score cannot.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Vector top 5 by cosine, floor on top-1 cosine (chosen) | misses a clause that matches only on an exact term with little meaning | a small corpus of plain-language clauses |
| Hybrid pgvector plus full-text (ADR-0005) | out of scope in the brief; a tsvector column and fusion code the day does not have | exact-term questions (names, numbers) that embeddings rank low |

## Decision

We will retrieve the 5 clauses with the highest cosine similarity to the question and reply "Not found in these contracts" without an LLM call when the top-1 similarity is below a floor set by a spike over the golden questions, because the brief fixes vector-only search and cosine gives a floor with a stable scale.

## Consequences

- No full-text index or tsvector column.
- The floor value lives in one setting with the spike output beside it; the refusal-accuracy eval guards it.
- Revisit when recall@5 misses a question whose answer turns on an exact term: that is the case hybrid search fixes.

## Commits us to

pgvector, sentence-transformers (outside the standard stack), BAAI/bge-small-en-v1.5
