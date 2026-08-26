"""Deciding whether a file may be accepted at all.

`docs/09_AWS_DEPLOYMENT.md` section 5 requires MIME validation *before*
processing, and `docs/12_BETA_CHECKLIST.md` names the cases that must be
handled: PDF works, scanned PDF works or fails clearly, images as designed,
the file limit enforced, an invalid type rejected, and a password-protected
PDF handled.

The governing rule is that **nothing the client says about the file is
trusted**. A browser's `Content-Type` header is a claim, and a filename
extension is a claim; both are attacker-controlled. The type is determined
from the bytes.

Every rejection returns a named reason with wording the reader can act on. A
generic "upload failed" tells someone with a password-protected PDF nothing
about what to do next.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIME_PDF = "application/pdf"
MIME_PNG = "image/png"
MIME_JPEG = "image/jpeg"

#: docs/01_PRODUCT_SPEC.md section 3.2: PDF, scanned PDF, supported images.
ACCEPTED_MIME_TYPES: frozenset[str] = frozenset({MIME_PDF, MIME_PNG, MIME_JPEG})

EXTENSIONS: dict[str, str] = {MIME_PDF: "pdf", MIME_PNG: "png", MIME_JPEG: "jpg"}

RejectionReason = Literal[
    "EMPTY_FILE",
    "TOO_LARGE",
    "UNSUPPORTED_TYPE",
    "ENCRYPTED_PDF",
    "CORRUPT_PDF",
]

#: What the reader is told. Each one says what happened *and* what they can do.
REJECTION_MESSAGES: dict[str, str] = {
    "EMPTY_FILE": "That file is empty. Please choose the policy document again.",
    "TOO_LARGE": (
        "That file is larger than we can accept. If it is a scan, try exporting it at a "
        "lower resolution, or upload the policy wording on its own."
    ),
    "UNSUPPORTED_TYPE": (
        "We can read PDFs and photos or scans in PNG or JPEG. That file is a different "
        "type, so we haven't stored it."
    ),
    "ENCRYPTED_PDF": (
        "That PDF is password-protected, so we can't open it. Please save an unlocked "
        "copy — most PDF readers can do this — and upload that instead."
    ),
    "CORRUPT_PDF": (
        "We couldn't open that PDF. It may not have downloaded fully. Please try "
        "downloading it from your insurer again and re-uploading."
    ),
}


class UploadRejected(Exception):
    """The file cannot be accepted, with a reason the reader can act on."""

    def __init__(self, reason: RejectionReason) -> None:
        self.reason: RejectionReason = reason
        self.message = REJECTION_MESSAGES[reason]
        super().__init__(self.message)


@dataclass(frozen=True)
class ValidatedUpload:
    mime_type: str
    extension: str
    size_bytes: int
    sha256: str
    page_count: int | None
    #: True only for a PDF we could open and that carries selectable text.
    #: False for a scan, which is not a problem — it means OCR is needed, and
    #: the worker needs to know which path to take.
    has_text_layer: bool
    metadata: dict[str, Any]


def _sniff_mime(data: bytes) -> str | None:
    """Determine the type from the bytes themselves.

    Short, explicit signature checks rather than a magic-number library: the
    accepted set is three types, and a dependency that guesses among hundreds
    would be a larger surface for no benefit.
    """
    if data.startswith(b"%PDF-"):
        return MIME_PDF
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return MIME_PNG
    if data.startswith(b"\xff\xd8\xff"):
        return MIME_JPEG
    return None


def _inspect_pdf(data: bytes) -> tuple[int | None, bool, dict[str, Any]]:
    """Page count and whether there is text to extract, without storing text.

    Only the first few pages are sampled. Enough to tell a born-digital
    document from a scan, without walking a 200-page booklet at upload time —
    and the sampled text is measured and discarded, never returned or logged.
    """
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise UploadRejected("ENCRYPTED_PDF")
        page_count = len(reader.pages)
        sample = min(page_count, 3)
        characters = 0
        for index in range(sample):
            characters += len((reader.pages[index].extract_text() or "").strip())
    except UploadRejected:
        raise
    except (PdfReadError, ValueError, OSError, KeyError, TypeError) as exc:
        # pypdf raises a wide range of types on a malformed file. The reader
        # gets one clear message; the exception type is not useful to them and
        # its text could echo document content.
        raise UploadRejected("CORRUPT_PDF") from exc

    # A born-digital policy has hundreds of characters per page. A scan
    # typically yields nothing, occasionally a stray ligature.
    has_text = characters >= 50 * max(sample, 1)
    return page_count, has_text, {"sampledPages": sample, "hasTextLayer": has_text}


def validate_upload(data: bytes, *, max_bytes: int) -> ValidatedUpload:
    """Accept or reject a file, deciding its type from its contents."""
    if not data:
        raise UploadRejected("EMPTY_FILE")
    if len(data) > max_bytes:
        raise UploadRejected("TOO_LARGE")

    mime_type = _sniff_mime(data)
    if mime_type is None or mime_type not in ACCEPTED_MIME_TYPES:
        raise UploadRejected("UNSUPPORTED_TYPE")

    page_count: int | None = None
    has_text_layer = False
    metadata: dict[str, Any] = {}

    if mime_type == MIME_PDF:
        page_count, has_text_layer, metadata = _inspect_pdf(data)
    else:
        # A photo of a policy is one page and always needs OCR.
        page_count = 1
        metadata = {"hasTextLayer": False}

    return ValidatedUpload(
        mime_type=mime_type,
        extension=EXTENSIONS[mime_type],
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
        has_text_layer=has_text_layer,
        metadata=metadata,
    )
