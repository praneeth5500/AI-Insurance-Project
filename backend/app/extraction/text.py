"""Getting text out of a document, and deciding whether we actually did.

`docs/07_POLICY_DECODER_AI.md` section 2 puts native extraction before OCR and
section 11 says not to run OCR on pages that are already extractable. That is
a per-page decision, not a per-document one: a born-digital wording with a
scanned endorsement stapled on the end is a real and common shape.

The `confidence` recorded against a page is not a claim about accuracy — it is
a measure of how much text was recovered relative to what a page of a policy
usually holds. It exists so a page that yielded three characters is visibly
different from one that yielded three thousand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.extraction.models import METHOD_NATIVE, METHOD_NONE, METHOD_OCR
from app.extraction.ocr import OcrProvider, OcrUnavailableError

#: Below this many characters a page is treated as having no usable text
#: layer. A scanned page typically yields nothing or a few stray ligatures; a
#: real page of policy wording yields hundreds.
MIN_NATIVE_CHARACTERS = 80

#: What a full page of policy text roughly holds, used only to scale the
#: recovered-text measure into 0..1.
TYPICAL_PAGE_CHARACTERS = 1800


class ExtractionFailed(Exception):
    """The document could not be read, with a reason the reader can act on."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    method: str
    confidence: float | None


def normalize(text: str) -> str:
    """Collapse the whitespace a PDF extractor leaves behind.

    Used for matching only. The verbatim text is what gets stored as the
    source, because a normalised quote is no longer the wording.
    """
    without_hyphenation = re.sub(r"-\n(?=\w)", "", text)
    return re.sub(r"[ \t ]+", " ", without_hyphenation).strip()


def _coverage(text: str) -> float:
    return min(len(text) / TYPICAL_PAGE_CHARACTERS, 1.0)


async def extract_pages(
    data: bytes, *, mime_type: str, ocr: OcrProvider
) -> tuple[list[ExtractedPage], str | None]:
    """Read every page, using OCR only where native extraction found nothing.

    Returns the pages and the name of the OCR provider if one was used, so the
    extraction run can record whether OCR participated at all.
    """
    if mime_type != "application/pdf":
        # A photo or scan has no text layer by definition.
        return await _ocr_pages(data, [1], ocr), ocr.name

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionFailed("ENCRYPTED_PDF")
        raw = [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
    except ExtractionFailed:
        raise
    except (PdfReadError, ValueError, OSError, KeyError, TypeError) as exc:
        raise ExtractionFailed("CORRUPT_PDF") from exc

    if not raw:
        raise ExtractionFailed("NO_PAGES")

    pages: list[ExtractedPage] = []
    needs_ocr: list[int] = []
    for page_number, text in raw:
        cleaned = normalize(text)
        if len(cleaned) >= MIN_NATIVE_CHARACTERS:
            pages.append(ExtractedPage(page_number, cleaned, METHOD_NATIVE, _coverage(cleaned)))
        else:
            needs_ocr.append(page_number)

    ocr_used: str | None = None
    if needs_ocr:
        if len(needs_ocr) == len(raw):
            # Nothing at all was extractable: this is a scan.
            recovered = await _ocr_pages(data, needs_ocr, ocr)
            pages.extend(recovered)
            ocr_used = ocr.name
        else:
            try:
                pages.extend(await _ocr_pages(data, needs_ocr, ocr))
                ocr_used = ocr.name
            except ExtractionFailed:
                # Some pages are readable and some are not. Keeping the
                # readable ones is right, but the unreadable pages are
                # recorded as empty with method NONE rather than omitted —
                # a missing page number would make the citations lie.
                pages.extend(ExtractedPage(number, "", METHOD_NONE, 0.0) for number in needs_ocr)

    pages.sort(key=lambda page: page.page_number)
    return pages, ocr_used


async def _ocr_pages(data: bytes, page_numbers: list[int], ocr: OcrProvider) -> list[ExtractedPage]:
    try:
        results = await ocr.read(data=data, page_numbers=page_numbers)
    except OcrUnavailableError as exc:
        raise ExtractionFailed("SCAN_NEEDS_OCR") from exc
    return [
        ExtractedPage(page.page_number, normalize(page.text), METHOD_OCR, page.confidence)
        for page in results
    ]
