"""Read the text layer of a contract PDF with pypdf (ADR-0006).

Text PDFs only: a file with no text layer is refused rather than stored
empty, because OCR is out of scope (Q-008).
"""

import io
from dataclasses import dataclass

from pypdf import PdfReader

from app.core.errors import DomainError


class UnreadablePdfError(DomainError):
    """The bytes are not a PDF pypdf can open (AC-US-00-001-6)."""

    status_code = 422
    code = "unreadable_pdf"


class NoTextLayerError(DomainError):
    """The PDF opens but holds no text, as a scan does (AC-US-00-001-4)."""

    status_code = 422
    code = "no_text_layer"


@dataclass(frozen=True)
class PdfText:
    """The text of every page joined in order, each page's own text, and the page count."""

    text: str
    page_count: int
    pages: tuple[str, ...] = ()


def read_pdf(data: bytes) -> PdfText:
    """Return the text of `data`, or raise why it cannot be used."""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    # The bytes are untrusted, and pypdf raises far more than PdfReadError on
    # hostile input (AttributeError, KeyError, ValueError, NotImplementedError,
    # DependencyError for AES): every parser failure means "not readable".
    except Exception as exc:  # parser boundary; mapped to one domain error
        raise UnreadablePdfError("Not a readable PDF") from exc
    text = "\n".join(pages)
    if not text.strip():
        raise NoTextLayerError("No text found; scanned PDFs are not supported")
    return PdfText(text=text, page_count=len(pages), pages=tuple(pages))
