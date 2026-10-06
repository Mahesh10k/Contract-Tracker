// Sample data for design review and tests: the real golden contracts' wording, no network.
import { type Api, type Contract, type Deadline, type Field, type HeldField } from "./api";

export const CONTRACTS: Contract[] = [
  { id: "lease-01", title: "Lease Agreement 01", contract_type: "lease", source_filename: "lease-01.pdf" },
  { id: "vendor-07", title: "Supply Agreement 07", contract_type: "vendor", source_filename: "vendor-07.pdf" },
  { id: "vendor-08", title: "Supply Agreement 08", contract_type: "vendor", source_filename: "vendor-08.pdf" },
];

const FIELDS: Record<string, Field[]> = {
  "lease-01": [
    { field: "parties", value: "Northgate Realty Inc and Delta Foods Inc", quote: "This Lease is made between Northgate Realty Inc and Delta Foods Inc.", clause: "1", status: "accepted", review_reason: null },
    { field: "effective_date", value: "1 January 2025", quote: "The term commences on 1 January 2025.", clause: "2.1", status: "accepted", review_reason: null },
    { field: "term", value: "two (2) years", quote: "The term is two (2) years from the commencement date.", clause: "2.2", status: "accepted", review_reason: null },
    { field: "auto_renewal", value: "does not renew automatically", quote: "This Lease does not renew automatically.", clause: "2.3", status: "accepted", review_reason: null },
    { field: "notice_period", value: "not less than thirty days", quote: "Either party may end this Lease at expiry by giving not less than thirty days written notice before the end of the term.", clause: "7", status: "accepted", review_reason: null },
  ],
  "vendor-08": [
    { field: "parties", value: "Meridian Parts LLC and Beta Logistics LLC", quote: "This Agreement is made between Meridian Parts LLC and Beta Logistics LLC.", clause: "1", status: "accepted", review_reason: null },
    { field: "auto_renewal", value: null, quote: null, clause: null, status: "needs_review", review_reason: "value_missing" },
  ],
};

const DEADLINES: Deadline[] = [
  { contract: "Lease Agreement 01", kind: "notice_deadline", due: "2026-12-01", days_left: 57, clause: "7" },
  { contract: "Lease Agreement 01", kind: "expiry", due: "2026-12-31", days_left: 87, clause: "2.2" },
  { contract: "Supply Agreement 07", kind: "notice_deadline", due: "2027-05-31", days_left: 238, clause: "2.3" },
  { contract: "Supply Agreement 07", kind: "expiry", due: "2027-08-31", days_left: 330, clause: "2.2" },
];

const HELD: HeldField[] = [
  { contract: "Supply Agreement 08", field: "auto_renewal", value: null, quote: null, reason: "value_missing" },
  { contract: "Services Agreement 02", field: "notice_period", value: "upon completion of phase two of the works", quote: "Notice must be given upon completion of phase two of the works.", reason: "could_not_parse" },
];

const wait = <T,>(value: T): Promise<T> => Promise.resolve(value);

export const mockApi: Api = {
  contracts: () => wait(CONTRACTS),
  upload: (file) => wait(`Loaded ${file.name}`),
  loadGolden: () => wait(["Lease Agreement 01", "Supply Agreement 07 (already loaded)"]),
  fields: (id) => wait(FIELDS[id] ?? []),
  extract: () => wait("5 accepted, 0 need review"),
  deadlines: () => wait(DEADLINES),
  review: () => wait(HELD),
  ask: () =>
    Promise.resolve({
      text: "Supply Agreement 08 is governed by the laws of the State of California.",
      refused: false,
      citations: [
        {
          contract: "Supply Agreement 08",
          clause: "8",
          text: "This Agreement is governed by the laws of the State of California.",
        },
      ],
    }),
  sendReminders: () => wait("1 reminder sent, 2 skipped (older or expired)"),
};
