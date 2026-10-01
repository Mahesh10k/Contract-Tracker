"""Split contract text into numbered clauses.

A clause is the unit every quote and citation points at, so a wrong boundary
here means a wrong citation everywhere downstream.
"""

import re
from dataclasses import dataclass

HEADING = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\s+(?P<heading>[A-Z].*)$")
# A word the PDF layout broke at a line end: "Limit-\nation" becomes "Limitation".
# A real hyphen at a line end ("self-\nemployed") is joined too; the quote
# check normalises the same way, so both sides agree.
BROKEN_WORD = re.compile(r"(\w)-\n(?=[a-z])")


@dataclass(frozen=True)
class Clause:
    """One numbered clause: its number as printed, heading and body text."""

    number: str
    heading: str
    body: str


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
    """Return the clauses of `text` in document order."""
    clauses: list[Clause] = []
    number = heading = ""
    body: list[str] = []
    for line in BROKEN_WORD.sub(r"\1", text).splitlines():
        match = HEADING.match(line)
        if match and (not number or match["number"] in successors(number)):
            if number:
                clauses.append(Clause(number, heading, "\n".join(body)))
            number, heading, body = match["number"], match["heading"], []
        else:
            body.append(line)
    if number:
        clauses.append(Clause(number, heading, "\n".join(body)))
    return clauses
