"""Reading a page that has no text layer.

`docs/07_POLICY_DECODER_AI.md` section 11: native text first, OCR only as a
fallback, the provider replaceable, and *do not run OCR unnecessarily on
already extractable pages*. `docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 3
leaves the provider undecided.

So this is an interface and a deliberate refusal. `UnavailableOcrProvider`
fails with a named reason that the reader sees as "we can't read scans yet" —
which is true, and far better than the alternatives: silently producing
nothing (a policy that looks empty), or guessing at the content of a document
we cannot read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class OcrUnavailableError(RuntimeError):
    """No OCR provider is configured, so a scan cannot be read."""


@dataclass(frozen=True)
class OcrPage:
    page_number: int
    text: str
    #: 0..1, the provider's own confidence in the recognition.
    confidence: float


class OcrProvider(Protocol):
    """docs/07_POLICY_DECODER_AI.md section 11. Replaceable by design."""

    name: str

    async def read(self, *, data: bytes, page_numbers: list[int]) -> list[OcrPage]: ...


class UnavailableOcrProvider:
    """The honest default until a provider is chosen.

    Raising is the point. A provider that returned empty pages would produce a
    policy whose decoder sections are all blank, and a reader would reasonably
    conclude their policy covers nothing — which is a far worse failure than
    being told we cannot read scans yet.
    """

    name = "none"

    async def read(self, *, data: bytes, page_numbers: list[int]) -> list[OcrPage]:
        raise OcrUnavailableError(
            "No OCR provider is configured, so pages without a text layer cannot be read. "
            "See open item 3 in docs/13_DECISIONS_AND_OPEN_ITEMS.md."
        )


def build_ocr_provider() -> OcrProvider:
    """Select the OCR adapter.

    One function to change when a provider is chosen. Everything upstream
    already handles the unavailable case, so adding a real adapter turns a
    failure into a success without touching the pipeline.
    """
    return UnavailableOcrProvider()
