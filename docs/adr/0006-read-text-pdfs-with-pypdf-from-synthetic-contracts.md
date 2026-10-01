# ADR-0006: Read text PDFs with pypdf, from synthetic contracts generated with answer keys

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief; generator approach decided in office hours (D1.1, D1.3)
- Area: document ingestion
- Reversibility: cheap: the reader is one module; the generated set can be regenerated at any time

## Context

- From the request: "PDFs: text PDFs only, read with pypdf. 15-20 synthetic contracts, no real data." OCR is out of scope.
- Evals need answer keys (REQ-023 to REQ-027). D1.1: contracts are generated from templates, each PDF written together with `truth.json`; fpdf2 writes the PDFs.
- D1.3: templates use numbered clause headings so the splitter is deterministic; pypdf output breaks lines mid-sentence, so the quote check normalises whitespace and hyphenation.

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| Template generator with fpdf2, read back with pypdf (chosen) | templates are cleaner than real contracts, so scores may overstate real-world quality | a learning project that needs exact answer keys |
| Contracts written by the LLM, labelled by hand | spends budget and leaves answer keys unverified | a larger, more varied corpus when time allows |
| pdfplumber or PyMuPDF for reading | no alternative was weighed: the brief fixed pypdf | layout-heavy PDFs with tables pypdf flattens badly |

## Decision

We will generate 18 contracts (leases, vendor and service agreements) from templates with fpdf2, write a `truth.json` beside each, and read every PDF with pypdf, rejecting any file with no text layer, because answer keys must be exact and the brief fixes pypdf and text-only input.

## Consequences

- Ingestion is tested on real PDF bytes, not template text.
- Template variety (wording of durations, renewal and escalation clauses) decides how honest the eval is; the generator varies phrasing deliberately.
- Revisit if the project ever loads real contracts: add a held-out set not generated from these templates.

## Commits us to

pypdf, fpdf2 (outside the standard stack)
