"""PDF reading: text out of good files, a clear refusal for bad ones (US-00-001)."""

import pytest

from app.ingestion.pdf import NoTextLayerError, UnreadablePdfError, read_pdf
from tests.pdf_fixtures import image_only_pdf, text_pdf


def test_text_and_page_count_are_read_from_a_text_pdf() -> None:
    data = text_pdf("1 Parties\nAcme Ltd and Beta LLC.", "2 Term\nThree years.")

    result = read_pdf(data)

    assert result.page_count == 2
    assert "Acme Ltd and Beta LLC." in result.text
    assert "2 Term" in result.text


# TC-0011
def test_tc0011_image_only_pdf_is_refused_as_scanned() -> None:
    with pytest.raises(NoTextLayerError) as raised:
        read_pdf(image_only_pdf(2))

    assert raised.value.message == "No text found; scanned PDFs are not supported"


# TC-0012
def test_tc0012_pdf_with_only_whitespace_is_refused_as_scanned() -> None:
    with pytest.raises(NoTextLayerError):
        read_pdf(text_pdf("   ", ""))


# TC-0013
def test_tc0013_text_page_followed_by_blank_page_is_accepted() -> None:
    result = read_pdf(text_pdf("1 Services\nCleaning.", ""))

    assert result.page_count == 2
    assert "Cleaning." in result.text


# TC-0017
def test_tc0017_text_file_renamed_to_pdf_is_unreadable() -> None:
    with pytest.raises(UnreadablePdfError) as raised:
        read_pdf(b"hello\n")

    assert raised.value.message == "Not a readable PDF"


# TC-0018
def test_tc0018_truncated_pdf_is_unreadable() -> None:
    data = text_pdf("1 Parties\nAcme Ltd.")

    with pytest.raises(UnreadablePdfError):
        read_pdf(data[: len(data) // 2])


# TC-0019
def test_tc0019_empty_file_is_unreadable() -> None:
    with pytest.raises(UnreadablePdfError):
        read_pdf(b"")


@pytest.mark.parametrize("offset", [143, 305, 403, 492])
def test_corrupt_byte_that_breaks_pypdf_internals_is_unreadable(offset: int) -> None:
    # TASK-001 review finding 2: these offsets raised AttributeError, NotImplementedError,
    # ValueError and KeyError out of pypdf instead of "Not a readable PDF".
    data = bytearray(text_pdf("1 Parties\nAcme and Beta.\n2 Term\nThree years."))
    data[offset] ^= 0xFF

    with pytest.raises(UnreadablePdfError):
        read_pdf(bytes(data))


def test_each_page_text_is_kept_in_order() -> None:
    # US-00-009: pages are needed to know which page a clause is on.
    data = text_pdf("1 Parties\nAcme Ltd and Beta LLC.", "2 Term\nThree years.")

    result = read_pdf(data)

    assert len(result.pages) == 2
    assert "Acme Ltd" in result.pages[0]
    assert "2 Term" in result.pages[1]
