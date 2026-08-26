"""Cutting a policy into clauses that can be cited.

`docs/07_POLICY_DECODER_AI.md` section 2 puts clause segmentation between page
normalisation and structured extraction, and section 6 requires every
explanation to end with "Source: Page X · Clause Y". That is what segmentation
is *for*: a fact needs somewhere to point.

Segmentation is deterministic — headings, numbered sections and capitalised
titles — because a model that split the document differently on each run would
make citations unstable, and a citation that moves is not a citation.

Every clause keeps its text verbatim. A paraphrase stored here would quietly
become what the reader is shown as "the policy says".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.extraction.text import ExtractedPage

#: The decoder's own section list (docs/01_PRODUCT_SPEC.md section 3.4). A
#: clause is filed under one of these when its heading makes that clear, and
#: under OTHER when it does not — guessing would put a payment condition
#: under "Not Covered".
CLAUSE_YOUR_COVER = "YOUR_COVER"
CLAUSE_YOUR_COSTS = "YOUR_COSTS"
CLAUSE_BEFORE_COVER_STARTS = "BEFORE_COVER_STARTS"
CLAUSE_IMPORTANT_LIMITS = "IMPORTANT_LIMITS"
CLAUSE_NOT_COVERED = "NOT_COVERED"
CLAUSE_AT_CLAIM_TIME = "AT_CLAIM_TIME"
CLAUSE_POLICY_DETAILS = "POLICY_DETAILS"
CLAUSE_OTHER = "OTHER"

#: Heading keywords mapped to a section. Matched case-insensitively against a
#: clause title only — never against body text, which would file a clause by
#: an incidental word.
_SECTION_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        CLAUSE_BEFORE_COVER_STARTS,
        ("waiting period", "waiting periods", "cooling off", "moratorium"),
    ),
    (CLAUSE_NOT_COVERED, ("exclusion", "exclusions", "not covered", "what is not covered")),
    (
        CLAUSE_YOUR_COSTS,
        ("co-payment", "copayment", "co-pay", "deductible", "premium", "your costs"),
    ),
    (CLAUSE_IMPORTANT_LIMITS, ("sub-limit", "sublimit", "limits", "room rent", "capping")),
    (CLAUSE_AT_CLAIM_TIME, ("claim", "claims", "cashless", "reimbursement", "intimation")),
    (
        CLAUSE_YOUR_COVER,
        ("coverage", "benefits", "what is covered", "scope of cover", "sum insured"),
    ),
    (
        CLAUSE_POLICY_DETAILS,
        ("definitions", "grievance", "renewal", "policy schedule", "free look"),
    ),
)

#: A heading looks like one of these. Deliberately conservative: a false
#: heading fragments a clause and scatters its meaning across two citations.
_HEADING_PATTERNS = (
    # "4.2 Waiting Periods" / "SECTION 3 - EXCLUSIONS" / "SECTION 1 — COVER"
    # The separator between the number and the title varies: a dot, a dash, a
    # colon, an en dash, or nothing at all.
    re.compile(r"^\s*(?:SECTION\s+)?\d+(?:\.\d+)*\s*[).:\-–—]?\s*([A-Z][^\n]{2,80})$"),
    # "WAITING PERIODS" on its own line
    re.compile(r"^\s*([A-Z][A-Z \-&/']{4,80})$"),
    # "Waiting Periods:" title case with a colon
    re.compile(r"^\s*([A-Z][A-Za-z \-&/']{4,80}):\s*$"),
)

#: A clause shorter than this is a stray line, not a section.
MIN_CLAUSE_CHARACTERS = 40


@dataclass(frozen=True)
class SegmentedClause:
    clause_type: str
    title: str | None
    source_page: int
    source_text: str
    normalized_text: str
    ordinal: int


def classify(title: str | None) -> str:
    """Which decoder section a heading belongs to, or OTHER."""
    if not title:
        return CLAUSE_OTHER
    lowered = title.lower()
    for section, keywords in _SECTION_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return section
    return CLAUSE_OTHER


def _heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 90:
        return None
    for pattern in _HEADING_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return match.group(1).strip().rstrip(":")
    return None


def segment(pages: list[ExtractedPage]) -> list[SegmentedClause]:
    """Split the document into clauses, keeping each one's page number.

    A clause is attributed to the page its *heading* appeared on. When a
    clause runs across a page break, the citation points at where the reader
    should start reading, which is what they need.
    """
    clauses: list[SegmentedClause] = []
    current_title: str | None = None
    current_page = pages[0].page_number if pages else 1
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_title, current_page
        text = "\n".join(buffer).strip()
        if len(text) >= MIN_CLAUSE_CHARACTERS:
            clauses.append(
                SegmentedClause(
                    clause_type=classify(current_title),
                    title=current_title,
                    source_page=current_page,
                    source_text=text,
                    normalized_text=re.sub(r"\s+", " ", text).strip(),
                    ordinal=len(clauses),
                )
            )
        buffer = []

    for page in pages:
        if not page.text:
            continue
        for line in page.text.split("\n"):
            heading = _heading(line)
            if heading is not None:
                flush()
                current_title = heading
                current_page = page.page_number
            else:
                buffer.append(line)

    flush()

    if not clauses and pages:
        # No headings found at all — a one-page scan, or an unusual layout.
        # The whole document becomes a single untitled clause rather than
        # producing nothing: a citation to "page 1" is honest, and better than
        # facts with nowhere to point.
        joined = "\n".join(page.text for page in pages if page.text).strip()
        if len(joined) >= MIN_CLAUSE_CHARACTERS:
            clauses.append(
                SegmentedClause(
                    clause_type=CLAUSE_OTHER,
                    title=None,
                    source_page=pages[0].page_number,
                    source_text=joined,
                    normalized_text=re.sub(r"\s+", " ", joined).strip(),
                    ordinal=0,
                )
            )

    return clauses
