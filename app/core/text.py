"""One text normaliser for every "is this quote in that clause?" check (review decision D5).

The quote check (TASK-002), the grounding eval (TASK-003) and the citation
check (TASK-004) all call this, so the eval's grounding number describes
exactly what the product accepts. It removes layout noise only: line breaks,
runs of spaces, words broken at a line end, soft hyphens, typographic quotes
and non-breaking spaces. It never removes digits, words or a hyphen inside a
line, so "90 days" can never match "30 days".
"""

import re

_BROKEN_WORD = re.compile(r"(\w)-\n(?=[a-z])")  # same rule as the clause splitter
_SPACES = re.compile(r"\s+")
_UNIFY = str.maketrans(
    {
        "\u00ad": None,  # soft hyphen
        "\u00a0": " ",  # non-breaking space
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)


def normalise_for_match(text: str) -> str:
    """`text` with layout noise removed, for substring comparison."""
    joined = _BROKEN_WORD.sub(r"\1", text.translate(_UNIFY))
    return _SPACES.sub(" ", joined).strip()
