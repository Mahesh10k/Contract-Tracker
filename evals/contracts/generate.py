"""Generate the synthetic contracts and their truth.json answer keys (ADR-0006).

Every expected answer is fixed by construction: the generator chooses the
terms (start date, term, notice, renewal, payments) and writes the contract
text from them, so the answer key is the input, never output of the code it
will grade. Dates come from evals.contracts.dates (standard library only),
not from the product's dateutil code.

Run: `make contracts` (writes data/contracts/). Output is byte-identical
for a given seed, so files can be committed and cache keys stay stable.
"""

import calendar
import hashlib
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fpdf import FPDF

from evals.contracts.dates import end_of_term, months_after, months_before
from evals.contracts.truth import TRUTH, Truth, TruthClause, TruthDates, TruthField

FIELDS = (
    "parties",
    "effective_date",
    "term",
    "auto_renewal",
    "notice_period",
    "payment_terms",
    "escalation",
    "liability_cap",
    "termination_rights",
    "governing_law",
)
SEED = 2026
TERMINATION = "either party may terminate for material breach on thirty (30) days written notice"
TYPES = ("lease", "vendor", "service")
# Never used while tuning prompts: the honest score (design note, holdout split).
HOLDOUT = frozenset({"lease-03", "lease-06", "vendor-03", "vendor-06", "service-06"})
# Deliberately unparseable notice periods: they must land in needs_review (AC-US-00-003-6).
UNPARSEABLE_NOTICE = frozenset({"vendor-04", "service-02"})
FIXED_PDF_DATE = datetime(2026, 1, 1, tzinfo=UTC)

TITLES = {"lease": "Lease Agreement", "vendor": "Supply Agreement", "service": "Services Agreement"}
FIRST_PARTY = {
    "lease": ["Harbor Properties LLC", "Oakline Estates Ltd", "Northgate Realty Inc"],
    "vendor": ["Brightpath Supplies Inc", "Copperleaf Trading Ltd", "Meridian Parts LLC"],
    "service": ["Clearwater Cleaning Ltd", "Summit IT Services LLC", "Bluebell Security Inc"],
}
SECOND_PARTY = ["Acme Analytics Inc", "Beta Logistics LLC", "Cedar Health Ltd", "Delta Foods Inc"]
YEARS_TEXT = {1: "one (1) year", 2: "two (2) years", 3: "three (3) years", 5: "five (5) years"}
# (phrase as written, amount, unit); several wordings per field so a prompt cannot overfit one.
NOTICE = [
    ("ninety (90) days", 90, "days"),
    ("sixty (60) days", 60, "days"),
    ("not less than thirty days", 30, "days"),
    ("three (3) months", 3, "months"),
]
UNPARSEABLE_PHRASE = "upon completion of phase two of the works"
LAWS = [
    "the State of Delaware",
    "the State of New York",
    "England and Wales",
    "the State of California",
]
CAPS = [
    "the fees paid in the twelve (12) months before the claim",
    "USD 50,000",
    "two times the annual fees",
]
PAYMENT = {
    "lease": ("monthly in advance on the first day of each month", 1, 1),
    "vendor": ("monthly on the fifteenth day of each month", 15, 1),
    "service": ("quarterly in advance on the first day of each quarter", 1, 3),
}
ESCALATION = {
    "lease": "3.5 percent on each anniversary of the commencement date",
    "vendor": "fixed for the term",
    "service": "2 percent on each anniversary of the commencement date",
}


@dataclass(frozen=True)
class Terms:
    """The chosen terms of one contract; every expected answer derives from these."""

    contract_id: str
    contract_type: str
    party_a: str
    party_b: str
    start: date
    years: int
    notice: tuple[str, int, str] | None
    auto_renewal: bool
    law: str
    cap: str


def _long_date(d: date) -> str:
    return f"{d.day} {calendar.month_name[d.month]} {d.year}"


def pick[T](options: list[T], seed: int, *key: str) -> T:
    """Choose one option from a hash of (seed, key), the same choice on every run.

    A hash rather than a seeded random generator: the choice is reproducible
    without a pseudo-random generator, so no security lint needs silencing.
    """
    digest = hashlib.sha256(":".join([str(seed), *key]).encode()).digest()
    return options[int.from_bytes(digest[:8], "big") % len(options)]


def choose_terms(seed: int, contract_type: str, n: int) -> Terms:
    """Choose one contract's terms; each field is picked independently by name."""
    contract_id = f"{contract_type}-{n:02d}"
    return Terms(
        contract_id=contract_id,
        contract_type=contract_type,
        party_a=pick(FIRST_PARTY[contract_type], seed, contract_id, "party_a"),
        party_b=pick(SECOND_PARTY, seed, contract_id, "party_b"),
        start=date(
            pick([2024, 2025, 2026], seed, contract_id, "year"),
            pick(list(range(1, 13)), seed, contract_id, "month"),
            1,
        ),
        years=pick(sorted(YEARS_TEXT), seed, contract_id, "years"),
        notice=None
        if contract_id in UNPARSEABLE_NOTICE
        else pick(NOTICE, seed, contract_id, "notice"),
        auto_renewal=pick([True, False], seed, contract_id, "auto_renewal"),
        law=pick(LAWS, seed, contract_id, "law"),
        cap=pick(CAPS, seed, contract_id, "cap"),
    )


def clauses_and_fields(t: Terms) -> tuple[list[TruthClause], dict[str, TruthField]]:
    """Write the clause text and record, per field, its value, exact quote and clause."""
    doc = {"lease": "Lease", "vendor": "Agreement", "service": "Agreement"}[t.contract_type]
    payment_text, _, _ = PAYMENT[t.contract_type]
    notice_text = t.notice[0] if t.notice else UNPARSEABLE_PHRASE
    if t.auto_renewal:
        renewal_value = "renews automatically for successive one-year terms"
        renewal_sentence = (
            f"This {doc} {renewal_value} unless either party gives notice under clause 7."
        )
    else:
        renewal_value = "does not renew automatically"
        renewal_sentence = f"This {doc} {renewal_value}."
    escalation = ESCALATION[t.contract_type]
    escalation_sentence = (
        f"Prices are {escalation} and do not increase."
        if escalation == "fixed for the term"
        else f"Charges increase by {escalation}."
    )
    notice_sentence = (
        f"Either party may end this {doc} at expiry by giving {notice_text} written notice "
        "before the end of the term."
        if t.notice
        else f"Either party may end this {doc} at expiry by giving written notice {notice_text}."
    )
    rows: list[tuple[str, str, list[tuple[str | None, str, str]]]] = [
        (
            "1",
            "Parties",
            [
                (
                    "parties",
                    f"{t.party_a} and {t.party_b}",
                    f"This {doc} is made between {t.party_a} and {t.party_b}.",
                )
            ],
        ),
        ("2", "Term", [(None, "", "The term is set out in clause 2.1 to clause 2.3 below.")]),
        (
            "2.1",
            "Commencement",
            [
                (
                    "effective_date",
                    _long_date(t.start),
                    f"The term commences on {_long_date(t.start)}.",
                )
            ],
        ),
        (
            "2.2",
            "Duration",
            [
                (
                    "term",
                    YEARS_TEXT[t.years],
                    f"The term is {YEARS_TEXT[t.years]} from the commencement date.",
                )
            ],
        ),
        ("2.3", "Renewal", [("auto_renewal", renewal_value, renewal_sentence)]),
        ("3", "Payment", [("payment_terms", payment_text, f"Charges are payable {payment_text}.")]),
        ("3.1", "Price Changes", [("escalation", escalation, escalation_sentence)]),
        (
            "4",
            "Limitation of Liability",
            [("liability_cap", t.cap, f"The liability of either party is capped at {t.cap}.")],
        ),
        (
            "5",
            "Termination",
            [
                (
                    "termination_rights",
                    TERMINATION,
                    f"{TERMINATION.capitalize()}.",
                )
            ],
        ),
        (
            "6",
            "Confidentiality",
            [(None, "", "Each party keeps the other party's information confidential.")],
        ),
        ("7", "Notice of Non-Renewal", [("notice_period", notice_text, notice_sentence)]),
        (
            "8",
            "Governing Law",
            [("governing_law", t.law, f"This {doc} is governed by the laws of {t.law}.")],
        ),
    ]
    clauses: list[TruthClause] = []
    fields: dict[str, TruthField] = {}
    for number, heading, sentences in rows:
        clauses.append(
            {"number": number, "heading": heading, "body": " ".join(s for _, _, s in sentences)}
        )
        for name, value, sentence in sentences:
            if name:
                fields[name] = {"value": value, "quote": sentence, "clause": number}
    return clauses, fields


def expected_dates(t: Terms) -> TruthDates:
    """The dates the product must compute, from the chosen terms alone."""
    expiry = end_of_term(t.start, years=t.years)
    if t.notice is None:
        notice_deadline = None
    elif t.notice[2] == "days":
        notice_deadline = (expiry - timedelta(days=t.notice[1])).isoformat()
    else:
        notice_deadline = months_before(expiry, months=t.notice[1]).isoformat()
    _, pay_day, step = PAYMENT[t.contract_type]
    first_payment = t.start.replace(day=pay_day)
    payments = [months_after(first_payment, months=k * step) for k in range(t.years * 12 // step)]
    escalates = ESCALATION[t.contract_type] != "fixed for the term"
    return {
        "expiry": expiry.isoformat(),
        "notice_deadline": notice_deadline,
        "renewal": (expiry + timedelta(days=1)).isoformat() if t.auto_renewal else None,
        "escalation_dates": [
            t.start.replace(year=t.start.year + k).isoformat() for k in range(1, t.years)
        ]
        if escalates
        else [],
        "payment_dates": [d.isoformat() for d in payments],
    }


def render_pdf(title: str, clauses: list[TruthClause]) -> bytes:
    """One heading line per clause, then its body, in a core font (latin-1 only)."""
    pdf = FPDF()
    pdf.set_creation_date(FIXED_PDF_DATE)
    pdf.set_title(title)
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.multi_cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for clause in clauses:
        pdf.multi_cell(
            0, 6, f"{clause['number']} {clause['heading']}", new_x="LMARGIN", new_y="NEXT"
        )
        pdf.multi_cell(0, 6, clause["body"], new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def generate(out_dir: Path, seed: int = SEED) -> list[Path]:
    """Write 18 contract PDFs and their truth.json files to `out_dir`; return the truth paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for contract_type in TYPES:
        for n in range(1, 7):
            terms = choose_terms(seed, contract_type, n)
            title = f"{TITLES[contract_type]} {n:02d}"
            clauses, fields = clauses_and_fields(terms)
            truth: Truth = {
                "id": terms.contract_id,
                "title": title,
                "contract_type": contract_type,
                "start": terms.start.isoformat(),
                "term_years": terms.years,
                "holdout": terms.contract_id in HOLDOUT,
                "expected_review": ["notice_period"] if terms.notice is None else [],
                "clauses": clauses,
                "fields": fields,
                "expected": expected_dates(terms),
            }
            (out_dir / f"{terms.contract_id}.pdf").write_bytes(render_pdf(title, clauses))
            path = out_dir / f"{terms.contract_id}.truth.json"
            path.write_bytes(TRUTH.dump_json(truth, indent=2) + b"\n")
            written.append(path)
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "data/contracts")
    paths = generate(target)
    sys.stdout.write(f"contracts: {len(paths)} written to {target}\n")
