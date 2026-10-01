# ADR-0004: Embed clauses locally with BAAI/bge-small-en-v1.5 on CPU

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief
- Area: vector store and embeddings
- Reversibility: cheap at this size: changing the model means re-embedding a few hundred clauses and changing the column dimension

## Context

- From the request: "Embeddings: BAAI/bge-small-en-v1.5 locally on CPU via sentence-transformers."
- The model outputs 384-dimension vectors, so `clauses.embedding` is `vector(384)`.
- Embeddings cost nothing against the USD 10 LLM budget (ADR-0001).
- Q-016: `make check` must run offline, so the model is downloaded once by `make setup` into a local folder, never at test time.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| bge-small-en-v1.5 via sentence-transformers, CPU (chosen) | pulls in PyTorch (a large install); weaker than larger embedding models on long or subtle clauses | small English corpora, offline evals, zero per-call cost |
| A hosted embedding API through OpenRouter or a vendor | no alternative was weighed: the brief fixed local embeddings; listed as the revisit path | recall@5 below its threshold with tuning exhausted, if budget allows |

## Decision

We will embed every clause with BAAI/bge-small-en-v1.5 through sentence-transformers on CPU and store the vectors in pgvector, because the brief fixes it, it costs nothing per call and it keeps evals offline.

## Consequences

- The embedding model name and version are recorded with the vectors; changing it requires re-embedding.
- First setup downloads the model (about 130 MB) and PyTorch.
- Revisit if recall@5 stays below 0.90 after hybrid search and chunking are tuned.

## Commits us to

BAAI/bge-small-en-v1.5, sentence-transformers, PyTorch (CPU)
