"""Build small PDFs for tests with fpdf2, so no binary fixture is committed."""

from fpdf import FPDF


def text_pdf(*pages: str) -> bytes:
    """A PDF with one page per string; an empty string makes a page with no text."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    for page in pages:
        pdf.add_page()
        if page:
            pdf.multi_cell(0, 6, page)
    return bytes(pdf.output())


def image_only_pdf(page_count: int = 2) -> bytes:
    """Pages with drawn shapes and no text layer, like a scanned document."""
    pdf = FPDF()
    for _ in range(page_count):
        pdf.add_page()
        pdf.rect(20, 20, 100, 60, style="F")
    return bytes(pdf.output())
