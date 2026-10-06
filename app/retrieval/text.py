"""The text that gets embedded: a clause with its context, and a question in query form.

A clause alone loses its meaning: "governed by the laws of England and Wales" reads the same
in three contracts. Prefixing the contract title and the clause heading is what lets the
embedding tell them apart (REQ-040, AC-US-00-004-6).
"""

# BAAI/bge-small-en-v1.5 is trained to see questions with this instruction and passages without it.
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def embedding_text(title: str, number: str, heading: str, body: str) -> str:
    """ "<title> | <number> <heading> | <body>" for one clause."""
    return f"{title} | {number} {heading} | {body}"


def query_text(question: str) -> str:
    """A question as the embedding model expects to be asked."""
    return f"{QUERY_INSTRUCTION}{question}"
