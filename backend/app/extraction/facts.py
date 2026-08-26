"""Pulling structured facts out of clause text.

`docs/07_POLICY_DECODER_AI.md` section 4 sets the contract: schema-constrained
output, every value carrying its source page, clause title and the text it
came from, a `NOT_FOUND` status when a fact is absent, and — the sentence that
governs everything here — **never guess**.

## Why this is deterministic

The specification anticipates a model doing this work. No model provider is
chosen (`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 2), and the build plan
is explicit that AI comes *after* structured output is correct. So extraction
is pattern-based today, behind the same `FactExtractor` interface a model will
implement.

That is not a compromise for these particular facts. "How many months before
pre-existing conditions are covered" is a number printed in the document; a
regular expression that finds it and quotes the sentence it came from cannot
hallucinate, and every value it produces is checkable against the quote shown
beside it. A model earns its place on the harder half — reading a clause whose
meaning is not carried by a number — and it will inherit the same rule: a
value must arrive with the clause that supports it, or it is NOT_FOUND.

## Confidence

`docs/SPEC_ISSUES.md` issue 2 records that the specification shows confidence
both as a number and as an enum. Both are produced here: the number is the
extractor's own, the state is derived from it plus what the surrounding clause
was about. A value found inside a clause titled "Waiting Periods" is worth
more than the same number found in a marketing paragraph, and the state says
so.

`CONFLICTING` is a first-class result. When two clauses give different answers
we report the disagreement rather than picking one — section 5 requires
conflicting facts to be highlighted, and choosing a winner silently is exactly
the failure that rule exists to prevent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.extraction.clauses import (
    CLAUSE_BEFORE_COVER_STARTS,
    CLAUSE_IMPORTANT_LIMITS,
    CLAUSE_YOUR_COSTS,
    CLAUSE_YOUR_COVER,
    SegmentedClause,
)
from app.extraction.models import (
    CONFIDENCE_CONFLICTING,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_NOT_FOUND,
)

#: Bumped whenever a pattern changes, so a stored run says which rules
#: produced it and an old run is never confused for a current one.
EXTRACTION_SCHEMA_VERSION = "policy-extraction-001"

FACT_PED_WAITING_MONTHS = "ped_waiting_period_months"
FACT_INITIAL_WAITING_DAYS = "initial_waiting_period_days"
FACT_SPECIFIC_WAITING_MONTHS = "specific_disease_waiting_period_months"
FACT_COPAY_PERCENT = "copay_percentage"
FACT_ROOM_RENT_PERCENT = "room_rent_limit_percentage"
FACT_SUM_INSURED_INR = "sum_insured_inr"

#: Every fact the extractor looks for. A fact absent from a document is
#: recorded as NOT_FOUND rather than omitted — "we looked and it is not
#: there" is information the reader needs.
KNOWN_FACT_KEYS: tuple[str, ...] = (
    FACT_SUM_INSURED_INR,
    FACT_COPAY_PERCENT,
    FACT_ROOM_RENT_PERCENT,
    FACT_PED_WAITING_MONTHS,
    FACT_INITIAL_WAITING_DAYS,
    FACT_SPECIFIC_WAITING_MONTHS,
)

FACT_LABELS: dict[str, str] = {
    FACT_SUM_INSURED_INR: "Sum insured",
    FACT_COPAY_PERCENT: "Co-payment",
    FACT_ROOM_RENT_PERCENT: "Room rent limit",
    FACT_PED_WAITING_MONTHS: "Waiting period for pre-existing conditions",
    FACT_INITIAL_WAITING_DAYS: "Initial waiting period",
    FACT_SPECIFIC_WAITING_MONTHS: "Waiting period for specific treatments",
}

#: Which clause section each fact is expected in. A match inside the expected
#: section is HIGH; the same match elsewhere is MEDIUM.
EXPECTED_SECTION: dict[str, str] = {
    FACT_SUM_INSURED_INR: CLAUSE_YOUR_COVER,
    FACT_COPAY_PERCENT: CLAUSE_YOUR_COSTS,
    FACT_ROOM_RENT_PERCENT: CLAUSE_IMPORTANT_LIMITS,
    FACT_PED_WAITING_MONTHS: CLAUSE_BEFORE_COVER_STARTS,
    FACT_INITIAL_WAITING_DAYS: CLAUSE_BEFORE_COVER_STARTS,
    FACT_SPECIFIC_WAITING_MONTHS: CLAUSE_BEFORE_COVER_STARTS,
}


@dataclass(frozen=True)
class FactCandidate:
    """One reading of one fact, with where it came from."""

    fact_key: str
    value: dict[str, Any]
    clause_ordinal: int
    source_page: int
    source_quote: str
    confidence: float


@dataclass(frozen=True)
class ExtractedFact:
    """The contract from section 4, including the not-found case."""

    fact_key: str
    value: dict[str, Any] | None
    confidence: float | None
    confidence_state: str
    clause_ordinal: int | None = None
    source_page: int | None = None
    source_quote: str | None = None
    alternatives: list[dict[str, Any]] = field(default_factory=list)


class FactExtractor(Protocol):
    """The seam a model will implement.

    Whatever sits behind it, the contract is the same: a value arrives with
    the clause that supports it, or it does not arrive.
    """

    name: str
    schema_version: str

    def extract(self, clauses: list[SegmentedClause]) -> list[ExtractedFact]: ...


# ------------------------------------------------------------- the patterns --
#
# Each pattern captures the number and enough surrounding words that the match
# is unambiguous. Loose patterns are worse than no pattern: a bare "36" in a
# policy could be anything, and a wrong fact shown with a confident citation
# is the most damaging output this system can produce.

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twelve": 12,
    "twenty-four": 24,
    "thirty-six": 36,
    "forty-eight": 48,
}

_MONTHS_OR_YEARS = r"(\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s*(month|year)s?"

_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    FACT_PED_WAITING_MONTHS: (
        re.compile(
            r"pre[\s-]*existing[^.]{0,80}?" + _MONTHS_OR_YEARS,
            re.IGNORECASE,
        ),
        re.compile(
            _MONTHS_OR_YEARS + r"[^.]{0,80}?pre[\s-]*existing",
            re.IGNORECASE,
        ),
    ),
    FACT_SPECIFIC_WAITING_MONTHS: (
        re.compile(
            r"specifi(?:c|ed)\s+(?:disease|illness|treatment)s?[^.]{0,80}?" + _MONTHS_OR_YEARS,
            re.IGNORECASE,
        ),
    ),
    FACT_INITIAL_WAITING_DAYS: (
        re.compile(
            r"(?:initial|first)\s+(?:waiting\s+period\s+of\s+)?(\d{1,3})\s*days?",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d{1,3})\s*days?[^.]{0,40}?(?:from|of)\s+(?:the\s+)?(?:policy\s+)?(?:commencement|inception)",
            re.IGNORECASE,
        ),
    ),
    FACT_COPAY_PERCENT: (
        re.compile(r"co[\s-]*pay(?:ment)?[^.]{0,60}?(\d{1,2}(?:\.\d)?)\s*%", re.IGNORECASE),
        re.compile(r"(\d{1,2}(?:\.\d)?)\s*%[^.]{0,60}?co[\s-]*pay(?:ment)?", re.IGNORECASE),
    ),
    FACT_ROOM_RENT_PERCENT: (
        re.compile(
            r"room\s+rent[^.]{0,80}?(\d{1,2}(?:\.\d)?)\s*%",
            re.IGNORECASE,
        ),
        re.compile(
            r"(\d{1,2}(?:\.\d)?)\s*%\s*of\s+(?:the\s+)?sum\s+insured[^.]{0,40}?room",
            re.IGNORECASE,
        ),
    ),
    FACT_SUM_INSURED_INR: (
        re.compile(
            r"sum\s+insured[^.]{0,60}?(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)?",
            re.IGNORECASE,
        ),
    ),
}


def _sentence_around(text: str, match: re.Match[str]) -> str:
    """The sentence the value sits in, for the citation.

    Bounded: a citation the reader has to hunt through is not a citation, and
    an unbounded slice of a policy is a place document text ends up where it
    should not.
    """
    start = text.rfind(".", 0, match.start()) + 1
    end = text.find(".", match.end())
    if end == -1:
        end = len(text)
    return text[start : end + 1].strip()[:400]


def _to_months(amount: str, unit: str) -> int | None:
    number = _NUMBER_WORDS.get(amount.lower()) if not amount.isdigit() else int(amount)
    if number is None:
        return None
    months = number * 12 if unit.lower().startswith("year") else number
    # A waiting period longer than a decade is a misread, not a policy term.
    return months if 0 < months <= 120 else None


def _to_rupees(amount: str, scale: str | None) -> int | None:
    try:
        base = float(amount.replace(",", ""))
    except ValueError:
        return None
    if scale:
        lowered = scale.lower()
        if lowered in ("lakh", "lac"):
            base *= 100_000
        elif lowered in ("crore", "cr"):
            base *= 10_000_000
    value = int(base)
    # Below a lakh is not a sum insured; above a hundred crore is a misread.
    return value if 100_000 <= value <= 1_000_000_000 else None


class RuleBasedFactExtractor:
    """Deterministic extraction over clause text.

    Reads only what the document literally states, and cites the sentence it
    read it from. Nothing here infers, averages or fills in.
    """

    name = "rule-based"
    schema_version = EXTRACTION_SCHEMA_VERSION

    def extract(self, clauses: list[SegmentedClause]) -> list[ExtractedFact]:
        candidates: dict[str, list[FactCandidate]] = {key: [] for key in KNOWN_FACT_KEYS}

        for clause in clauses:
            for fact_key, patterns in _PATTERNS.items():
                for pattern in patterns:
                    for match in pattern.finditer(clause.normalized_text):
                        value = self._value_for(fact_key, match)
                        if value is None:
                            continue
                        in_expected_section = clause.clause_type == EXPECTED_SECTION[fact_key]
                        candidates[fact_key].append(
                            FactCandidate(
                                fact_key=fact_key,
                                value=value,
                                clause_ordinal=clause.ordinal,
                                source_page=clause.source_page,
                                source_quote=_sentence_around(clause.normalized_text, match),
                                confidence=0.9 if in_expected_section else 0.6,
                            )
                        )

        return [self._resolve(key, candidates[key]) for key in KNOWN_FACT_KEYS]

    @staticmethod
    def _value_for(fact_key: str, match: re.Match[str]) -> dict[str, Any] | None:
        if fact_key in (
            FACT_PED_WAITING_MONTHS,
            FACT_SPECIFIC_WAITING_MONTHS,
        ):
            months = _to_months(match.group(1), match.group(2))
            return {"months": months} if months is not None else None
        if fact_key == FACT_INITIAL_WAITING_DAYS:
            days = int(match.group(1))
            return {"days": days} if 0 < days <= 365 else None
        if fact_key in (FACT_COPAY_PERCENT, FACT_ROOM_RENT_PERCENT):
            percent = float(match.group(1))
            return {"percent": percent} if 0 <= percent <= 100 else None
        if fact_key == FACT_SUM_INSURED_INR:
            scale = match.group(2) if match.lastindex and match.lastindex >= 2 else None
            rupees = _to_rupees(match.group(1), scale)
            return {"amount": rupees, "currency": "INR"} if rupees is not None else None
        return None

    @staticmethod
    def _resolve(fact_key: str, found: list[FactCandidate]) -> ExtractedFact:
        """Turn every reading of one fact into a single reported result."""
        if not found:
            # Section 4: a fact that is not there is reported, not omitted.
            return ExtractedFact(
                fact_key=fact_key,
                value=None,
                confidence=None,
                confidence_state=CONFIDENCE_NOT_FOUND,
            )

        distinct = {tuple(sorted(candidate.value.items())) for candidate in found}
        best = max(found, key=lambda candidate: candidate.confidence)

        if len(distinct) > 1:
            # Section 5: highlight the disagreement rather than picking a
            # winner. The reader is shown every reading and where each came
            # from, and nothing automated relies on it.
            return ExtractedFact(
                fact_key=fact_key,
                value=None,
                confidence=None,
                confidence_state=CONFIDENCE_CONFLICTING,
                alternatives=[
                    {
                        "value": candidate.value,
                        "page": candidate.source_page,
                        "quote": candidate.source_quote,
                    }
                    for candidate in found
                ],
            )

        if best.confidence >= 0.85:
            state = CONFIDENCE_HIGH
        elif best.confidence >= 0.5:
            state = CONFIDENCE_MEDIUM
        else:
            state = CONFIDENCE_LOW

        return ExtractedFact(
            fact_key=fact_key,
            value=best.value,
            confidence=best.confidence,
            confidence_state=state,
            clause_ordinal=best.clause_ordinal,
            source_page=best.source_page,
            source_quote=best.source_quote,
        )


def build_fact_extractor() -> FactExtractor:
    """Select the extractor.

    One function to change when a model provider is chosen. A model
    implementation must satisfy the same contract — a value arrives with its
    clause, or it is NOT_FOUND — and the extraction run records which
    extractor produced it either way.
    """
    return RuleBasedFactExtractor()
