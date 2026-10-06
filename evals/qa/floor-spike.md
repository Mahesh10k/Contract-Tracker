# Refusal floor spike (Q-017, ADR-0013)

Run: `make eval-live`, 2026-10-06, bge-small-en-v1.5, 6 golden contracts (71 clauses), 10 golden questions.
Score is the top-1 cosine similarity of the retrieved clauses.

| Question | Answerable | Top-1 |
| --- | --- | --- |
| q01 Which law governs Supply Agreement 08? | yes | 0.825 |
| q02 Liability cap, Lease Agreement 01 | yes | 0.831 |
| q03 How often is rent paid, Lease Agreement 04 | yes | 0.781 |
| q04 Notice to prevent renewal, Supply Agreement 07 | yes | 0.868 |
| q05 Liability cap, Supply Agreement 07 | yes | 0.802 |
| q06 Payments due, Services Agreement 01 | yes | 0.763 |
| q07 Which law governs Services Agreement 04? | yes | 0.797 |
| q08 Tenant's parking allowance | no | 0.635 |
| q09 Any non-compete? | no | 0.598 |
| q10 CEO of Northgate Realty | no | 0.628 |

Answerable: 0.763 to 0.868. Unanswerable: 0.598 to 0.635. The two ranges do not overlap; the gap is
0.635 to 0.763, and its midpoint is 0.699. Floor chosen: **0.70** (0.063 under the lowest answerable
score, 0.065 over the highest unanswerable one).

Limits of this evidence: 10 questions, 3 of them unanswerable, all on template wording. A real
question phrased unusually can score under 0.70 and be refused although the contracts hold the
answer. The floor is a cheap first filter; the prompt's "not answerable" and the citation check
remain the real guard for questions that score above it. Recheck the floor when the contracts or
the embedding model change.

Result at the provisional floor 0.45 (no question reached the floor): recall@5 7/7, answer
accuracy 7/7, refusal accuracy 10/10; the three unanswerable questions were refused by the model
and the citation check. Spend: USD 0.0148 for the 10 answers.
