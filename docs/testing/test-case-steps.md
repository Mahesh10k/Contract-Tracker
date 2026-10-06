# Test case steps

Cases: docs/testing/test-cases.md as of 2026-10-01. Step ids are permanent;
a retired case keeps its steps.

## Steps

TASK-001 had no manual or e2e case. TASK-008 adds the Streamlit page cases below; AppTest runs them in make check and a person can follow the same steps with `make ui`.

| Step | Case | Action | Expected |
| --- | --- | --- | --- |
| TC-0115.1 | TC-0115 | Open the page with `make ui` | The tabs Upload, Contracts, Deadlines, Ask and Needs review show, in that order |
| TC-0116.1 | TC-0116 | On Upload, choose type "lease" | "lease" is selected |
| TC-0116.2 | TC-0116 | Choose data/contracts/lease-01.pdf | The file name lease-01.pdf shows under the uploader |
| TC-0116.3 | TC-0116 | Press "Load contract" | Success "Loaded Lease Agreement 01" shows |
| TC-0117.1 | TC-0117 | On Upload, choose a scanned PDF and press "Load contract" | Error "No text found; scanned PDFs are not supported" shows and no success message |
| TC-0118.1 | TC-0118 | On Contracts, pick "Lease Agreement 01" | A table of 5 fields shows with value, quote, clause and status |
| TC-0118.2 | TC-0118 | Read the notice_period row | Value "not less than thirty days", clause 7, its quote |
| TC-0119.1 | TC-0119 | On Contracts, pick "Supply Agreement 08" and read auto_renewal | Status "needs review (value_missing)" |
| TC-0122.1 | TC-0122 | On Ask, type "What notice does lease 01 need?" | The question shows in the box |
| TC-0122.2 | TC-0122 | Press "Ask" | The answer shows, then "Lease Agreement 01, clause 7" followed by the clause text |
| TC-0123.1 | TC-0123 | Open Needs review | Two rows: Supply Agreement 08 auto_renewal value_missing, Service Agreement 02 notice_period could_not_parse, each with value and quote |
| TC-0124.1 | TC-0124 | Open Needs review with no held fields | Info "Nothing is waiting for review." |
| TC-0173.1 | TC-0173 | Start MailHog with make mail and open http://localhost:8025 | The inbox is empty |
| TC-0173.2 | TC-0173 | In the terminal run PRETEND_TODAY=2026-10-31 make remind | The command prints how many reminders were sent and exits 0 |
| TC-0173.3 | TC-0173 | Reload http://localhost:8025 | A message per due reminder appears, subject naming the contract and the obligation |
| TC-0173.4 | TC-0173 | Open one message | The body shows the contract, the obligation, the date and "clause 7" |
| TC-0173.5 | TC-0173 | Run PRETEND_TODAY=2026-10-31 make remind again and reload MailHog | No new message appears |
| TC-0181.1 | TC-0181 | On Deadlines press Send due reminders twice quickly while the request is slow | The button shows busy and is disabled after the first press |
| TC-0181.2 | TC-0181 | Wait for the result | One success message shows and the button is enabled again |
