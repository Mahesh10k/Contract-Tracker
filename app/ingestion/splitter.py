"""Split contract text into numbered clauses.

A clause is the unit every quote and citation points at, so a wrong boundary
here means a wrong citation everywhere downstream.
"""

import re

from app.domain.contracts import Clause

__all__ = ["Clause", "split_clauses", "successors"]

# "7.2 Renewal" or "1. Services": a number, an optional dot, then a capitalised word.
HEADING = re.compile(r"^(?P<number>\d+(?:\.\d+)*)(?P<dot>\.?)\s+(?P<heading>[A-Z].*)$")
# A word the PDF layout broke at a line end: "Limit-\nation" becomes "Limitation".
# A real hyphen at a line end ("self-\nemployed") is joined too; the quote
# check normalises the same way, so both sides agree.
BROKEN_WORD = re.compile(r"(\w)-\n(?=[a-z])")


def successors(number: str) -> set[str]:
    """Clause numbers that may follow `number`: its first child or the next at any level.

    "7.2" may be followed by "7.2.1", "7.3" or "8". A number outside this set,
    such as "90" in "90 Days notice", is text that happens to start a line.
    """
    parts = [int(p) for p in number.split(".")]
    following = {f"{number}.1"}
    for depth in range(len(parts)):
        following.add(".".join(str(p) for p in [*parts[:depth], parts[depth] + 1]))
    return following


def split_clauses(text: str) -> list[Clause]:
    """Return the clauses of `text` in document order.

    Preamble: until the first clause closes, a heading numbered "1" restarts
    the sequence when the current candidate is not a "1" ("100 Main Street")
    or is a "1" that has no body yet ("1 March 2026" directly above
    "1 Parties"). A "1 ..." line inside clause 1's body never restarts it.
    Style: every heading keeps the numbering style ("1" or "1.") of the
    heading that opened the sequence, so a "1." list inside undotted clauses
    stays body text. A heading-only parent ("2 Term" followed directly by
    "2.1 ...") takes its heading as its body, so no clause is empty.
    """
    clauses: list[Clause] = []
    number = heading = style = ""
    body: list[str] = []
    for line in BROKEN_WORD.sub(r"\1", text).splitlines():
        match = HEADING.match(line)
        if match and _restarts(match, clauses, number, body):
            number, heading, style, body = match["number"], match["heading"], match["dot"], []
        elif (
            match
            and (not number or match["number"] in successors(number))
            and (not number or match["dot"] == style)
        ):
            if number:
                clauses.append(_clause(number, heading, body))
            else:
                style = match["dot"]
            number, heading, body = match["number"], match["heading"], []
        else:
            body.append(line)
    if number:
        clauses.append(_clause(number, heading, body))
    return clauses


def _restarts(match: re.Match[str], clauses: list[Clause], number: str, body: list[str]) -> bool:
    """True when a "1" heading should replace a preamble candidate (see split_clauses)."""
    if clauses or match["number"] != "1":
        return False
    return number != "1" or not any(line.strip() for line in body)


def _clause(number: str, heading: str, body: list[str]) -> Clause:
    text = "\n".join(body).strip()
    return Clause(number, heading, text or heading)
