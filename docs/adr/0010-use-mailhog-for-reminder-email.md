# ADR-0010: Send reminder email over SMTP to MailHog

- Status: Accepted
- Date: 2026-10-01
- Task: none
- Deciders: Developer (project owner), fixed in the brief
- Area: email, sms, push, payments
- Reversibility: cheap: SMTP host and port are settings; a real provider is a configuration change plus deliverability work

## Context

- From the request: "Postgres 16 + pgvector and MailHog, both in Docker Compose." Real email is out of scope.
- Q-002, Q-003, Q-019 (confirmed): one recipient in `.env`; sent by `make remind`; missed reminders caught up once.
- MailHog exposes an HTTP API listing received messages, which tests use (US-00-006-T1).

## What else was considered

| Option | Why not | Would suit |
| --- | --- | --- |
| MailHog in Docker Compose over plain SMTP (chosen) | nothing reaches a real inbox; MailHog is no longer actively developed | local demos and tests of email content |
| Mailpit (maintained MailHog replacement) | no alternative was weighed: the brief fixed MailHog | if the MailHog image stops working on the developer's machine |
| A real provider (Resend, Postmark, SES) | out of scope in the brief | a real deployment with real recipients |

## Decision

We will send reminders with Python's standard `smtplib` to MailHog from Docker Compose and read them back through its HTTP API in tests, because the brief fixes MailHog and real email is out of scope.

## Consequences

- The sender has no provider SDK; switching to a provider later means SMTP credentials and TLS, nothing else in the code.
- Revisit if the MailHog image fails to run: switch to Mailpit, which offers the same SMTP port and an equivalent API.

## Commits us to

MailHog (outside the standard stack), Python smtplib, Docker Compose
