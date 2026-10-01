# ADR-0003: Use Postgres 16 with pgvector for all stored data and vectors

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief
- Area: database
- Reversibility: awkward: every table, migration, the vector index and the full-text queries would move

## Context

- From the request: "Postgres 16 + pgvector and MailHog, both in Docker Compose."
- Data volume: 15 to 20 contracts, a few hundred clauses, 384-dimension vectors (ADR-0004). Far below any limit of a single Postgres instance.
- Hybrid search (ADR-0005) needs vectors and full-text in the same query.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Postgres 16 with pgvector, in Docker Compose (chosen) | one more container to run locally; pgvector index tuning is manual | relational data plus vectors at up to a few million rows |
| Postgres plus a separate vector store (Qdrant) | no alternative was weighed: the brief fixed pgvector; listed as the revisit path | many millions of vectors or heavy filtered vector search |

## Decision

We will keep contracts, clauses, extractions, obligations, reminders and clause embeddings in one Postgres 16 database with the pgvector extension, run from Docker Compose, because the brief fixes it and one store lets a single SQL query combine vector and full-text ranking.

## Consequences

- Migrations own the schema, including `CREATE EXTENSION vector` and `clauses.embedding vector(384)`.
- Tests need the Compose database running, or a disposable Postgres in CI.
- Revisit if clause count passes about one million or vector queries exceed 200 ms at p95.

## Commits us to

PostgreSQL 16, pgvector, Docker Compose
