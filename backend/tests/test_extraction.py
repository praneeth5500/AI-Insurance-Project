"""Document extraction (docs/11_BUILD_PLAN.md Phase 11).

The rule the whole phase turns on is one sentence from
`docs/07_POLICY_DECODER_AI.md` section 4: **never guess.** So these tests are
mostly about the cases where guessing would be tempting — a fact that is not
in the document, two clauses that disagree, a scan we cannot read — and what
must happen instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.extraction.clauses import (
    CLAUSE_BEFORE_COVER_STARTS,
    CLAUSE_NOT_COVERED,
    CLAUSE_OTHER,
    CLAUSE_YOUR_COSTS,
    SegmentedClause,
    classify,
    segment,
)
from app.extraction.facts import (
    FACT_COPAY_PERCENT,
    FACT_PED_WAITING_MONTHS,
    FACT_ROOM_RENT_PERCENT,
    FACT_SUM_INSURED_INR,
    KNOWN_FACT_KEYS,
    RuleBasedFactExtractor,
)
from app.extraction.models import (
    CONFIDENCE_CONFLICTING,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_NOT_FOUND,
    METHOD_NATIVE,
    RUN_FAILED,
    RUN_SUCCEEDED,
    ExtractionRun,
    PolicyClause,
    PolicyFact,
    PolicyPage,
)
from app.extraction.ocr import OcrPage, OcrUnavailableError, UnavailableOcrProvider
from app.extraction.pipeline import FAILURE_MESSAGES, is_permanent, process_document
from app.extraction.text import ExtractedPage, ExtractionFailed, extract_pages, normalize
from app.jobs.queue import DatabaseJobQueue
from app.policies.models import STATUS_FAILED, STATUS_READY
from app.policies.storage import LocalFileStorage
from tests.test_policy_upload import PNG_BYTES, pdf_bytes
from tests.test_questionnaire import make_user

POLICY_TEXT = """
SECTION 1 - COVERAGE
The sum insured under this policy is Rs. 5 lakh per policy year and is
available to all insured persons named in the schedule of this contract.

SECTION 2 - YOUR COSTS
A co-payment of 20% applies to each and every claim made under this policy
regardless of the age of the insured person at the time of the claim.

SECTION 3 - WAITING PERIODS
Pre-existing diseases are covered after a waiting period of 36 months of
continuous coverage under this policy without any break in cover.
There is an initial waiting period of 30 days from the policy commencement
date, except in the case of an accident requiring hospitalisation.

SECTION 4 - LIMITS
Room rent is limited to 1% of the sum insured per day for any single stay in
a hospital under the terms of this contract of insurance.

SECTION 5 - EXCLUSIONS
Cosmetic treatment is excluded from this policy unless it is required as a
direct result of an accident covered under the terms of this contract.
"""


def clause(
    clause_type: str, title: str, text: str, page: int = 1, ordinal: int = 0
) -> SegmentedClause:
    return SegmentedClause(
        clause_type=clause_type,
        title=title,
        source_page=page,
        source_text=text,
        normalized_text=" ".join(text.split()),
        ordinal=ordinal,
    )


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


# ---------------------------------------------------------------- reading ---


async def test_a_text_pdf_is_read_without_touching_ocr() -> None:
    """docs/07_POLICY_DECODER_AI.md section 11: do not run OCR unnecessarily.

    The provider raises, so if OCR were consulted at all this would fail —
    which is exactly the assertion worth making.
    """
    pages, ocr_used = await extract_pages(
        pdf_bytes(text=POLICY_TEXT.replace("\n", " ")),
        mime_type="application/pdf",
        ocr=UnavailableOcrProvider(),
    )

    assert ocr_used is None
    assert pages[0].method == METHOD_NATIVE
    assert "sum insured" in pages[0].text.lower()


async def test_a_scan_fails_clearly_rather_than_producing_an_empty_policy() -> None:
    """No OCR provider is configured (open item 3).

    Returning empty pages would give the reader a policy whose every section
    is blank, which they would reasonably read as "this covers nothing".
    """
    with pytest.raises(ExtractionFailed) as raised:
        await extract_pages(PNG_BYTES, mime_type="image/png", ocr=UnavailableOcrProvider())

    assert raised.value.reason == "SCAN_NEEDS_OCR"


async def test_ocr_is_used_when_a_provider_exists() -> None:
    """The fallback is real code, not a branch that has never run."""

    class StubOcr:
        name = "stub"

        async def read(self, *, data: bytes, page_numbers: list[int]) -> list[OcrPage]:
            return [OcrPage(number, "Recovered text from a scan", 0.8) for number in page_numbers]

    pages, ocr_used = await extract_pages(PNG_BYTES, mime_type="image/png", ocr=StubOcr())

    assert ocr_used == "stub"
    assert pages[0].text == "Recovered text from a scan"


async def test_an_encrypted_pdf_is_reported_as_such() -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    from io import BytesIO

    buffer = BytesIO()
    writer.write(buffer)

    with pytest.raises(ExtractionFailed) as raised:
        await extract_pages(
            buffer.getvalue(), mime_type="application/pdf", ocr=UnavailableOcrProvider()
        )

    assert raised.value.reason == "ENCRYPTED_PDF"


def test_normalisation_rejoins_hyphenated_line_breaks() -> None:
    """A PDF breaks words across lines; a fact pattern must still match."""
    assert "hospitalisation" in normalize("hospital-\nisation expenses")


def test_the_unavailable_ocr_provider_raises_rather_than_returning_nothing() -> None:
    with pytest.raises(OcrUnavailableError):
        import asyncio

        asyncio.get_event_loop_policy()
        asyncio.run(UnavailableOcrProvider().read(data=b"", page_numbers=[1]))


# ------------------------------------------------------------- segmentation ---


def test_clauses_are_split_on_headings_and_keep_their_page() -> None:
    pages = [ExtractedPage(1, POLICY_TEXT.strip(), METHOD_NATIVE, 1.0)]

    clauses = segment(pages)

    titles = [item.title for item in clauses]
    assert "COVERAGE" in titles
    assert "WAITING PERIODS" in titles
    assert all(item.source_page == 1 for item in clauses)


def test_a_clause_keeps_its_wording_verbatim() -> None:
    """A stored paraphrase would become what the reader is shown as the
    policy's own words."""
    pages = [ExtractedPage(1, POLICY_TEXT.strip(), METHOD_NATIVE, 1.0)]

    clauses = segment(pages)
    waiting = next(item for item in clauses if item.title == "WAITING PERIODS")

    assert "36 months of" in waiting.source_text


def test_headings_are_filed_under_the_decoder_s_own_sections() -> None:
    assert classify("WAITING PERIODS") == CLAUSE_BEFORE_COVER_STARTS
    assert classify("Exclusions") == CLAUSE_NOT_COVERED
    assert classify("Co-payment") == CLAUSE_YOUR_COSTS


def test_an_unrecognised_heading_is_not_forced_into_a_section() -> None:
    """Guessing would file a payment condition under "Not Covered"."""
    assert classify("MISCELLANEOUS PROVISIONS") == CLAUSE_OTHER
    assert classify(None) == CLAUSE_OTHER


def test_a_document_with_no_headings_still_produces_something_citable() -> None:
    pages = [ExtractedPage(1, "A policy with no headings at all. " * 5, METHOD_NATIVE, 1.0)]

    clauses = segment(pages)

    assert len(clauses) == 1
    assert clauses[0].source_page == 1


# ---------------------------------------------------------------- the facts ---


def test_facts_are_extracted_with_the_sentence_they_came_from() -> None:
    """docs/07_POLICY_DECODER_AI.md section 4: value plus source."""
    pages = [ExtractedPage(14, POLICY_TEXT.strip(), METHOD_NATIVE, 1.0)]

    facts = {fact.fact_key: fact for fact in RuleBasedFactExtractor().extract(segment(pages))}

    ped = facts[FACT_PED_WAITING_MONTHS]
    assert ped.value == {"months": 36}
    assert ped.source_page == 14
    assert ped.source_quote is not None and "36 months" in ped.source_quote
    assert facts[FACT_COPAY_PERCENT].value == {"percent": 20.0}
    assert facts[FACT_ROOM_RENT_PERCENT].value == {"percent": 1.0}
    assert facts[FACT_SUM_INSURED_INR].value == {"amount": 500_000, "currency": "INR"}


def test_a_fact_that_is_not_in_the_document_is_reported_as_not_found() -> None:
    """Silence would let the reader assume there is no waiting period."""
    facts = {
        fact.fact_key: fact
        for fact in RuleBasedFactExtractor().extract(
            [clause(CLAUSE_YOUR_COSTS, "Your Costs", "A co-payment of 10% applies.")]
        )
    }

    assert facts[FACT_PED_WAITING_MONTHS].confidence_state == CONFIDENCE_NOT_FOUND
    assert facts[FACT_PED_WAITING_MONTHS].value is None
    # Every known fact is accounted for, found or not.
    assert set(facts) == set(KNOWN_FACT_KEYS)


def test_two_clauses_that_disagree_produce_a_conflict_not_a_winner() -> None:
    """docs/07_POLICY_DECODER_AI.md section 5.

    Picking one silently is exactly the failure the CONFLICTING state exists
    to prevent.
    """
    facts = {
        fact.fact_key: fact
        for fact in RuleBasedFactExtractor().extract(
            [
                clause(
                    CLAUSE_BEFORE_COVER_STARTS,
                    "Waiting Periods",
                    "Pre-existing diseases are covered after 36 months of cover.",
                    page=14,
                    ordinal=0,
                ),
                clause(
                    CLAUSE_BEFORE_COVER_STARTS,
                    "Waiting Periods",
                    "Pre-existing diseases are covered after 48 months of cover.",
                    page=22,
                    ordinal=1,
                ),
            ]
        )
    }

    conflicting = facts[FACT_PED_WAITING_MONTHS]
    assert conflicting.confidence_state == CONFIDENCE_CONFLICTING
    assert conflicting.value is None
    # The reader has to be able to see *what* disagrees, and where.
    assert {alternative["page"] for alternative in conflicting.alternatives} == {14, 22}


def test_the_same_value_stated_twice_is_not_a_conflict() -> None:
    facts = {
        fact.fact_key: fact
        for fact in RuleBasedFactExtractor().extract(
            [
                clause(
                    CLAUSE_BEFORE_COVER_STARTS, "Waiting", "Pre-existing after 36 months.", 1, 0
                ),
                clause(CLAUSE_OTHER, "Summary", "Pre-existing conditions: 36 months.", 2, 1),
            ]
        )
    }

    assert facts[FACT_PED_WAITING_MONTHS].confidence_state == CONFIDENCE_HIGH


def test_a_value_found_outside_its_expected_section_is_less_confident() -> None:
    """A number in a marketing paragraph is worth less than the same number
    under the heading it belongs to."""
    in_place = RuleBasedFactExtractor().extract(
        [clause(CLAUSE_BEFORE_COVER_STARTS, "Waiting Periods", "Pre-existing after 36 months.")]
    )
    out_of_place = RuleBasedFactExtractor().extract(
        [clause(CLAUSE_OTHER, "Introduction", "Pre-existing after 36 months.")]
    )

    assert {f.fact_key: f for f in in_place}[FACT_PED_WAITING_MONTHS].confidence_state == (
        CONFIDENCE_HIGH
    )
    assert {f.fact_key: f for f in out_of_place}[FACT_PED_WAITING_MONTHS].confidence_state == (
        CONFIDENCE_MEDIUM
    )


def test_years_are_normalised_to_months() -> None:
    facts = {
        fact.fact_key: fact
        for fact in RuleBasedFactExtractor().extract(
            [clause(CLAUSE_BEFORE_COVER_STARTS, "Waiting", "Pre-existing diseases: 3 years.")]
        )
    }

    assert facts[FACT_PED_WAITING_MONTHS].value == {"months": 36}


def test_an_implausible_reading_is_discarded_rather_than_reported() -> None:
    """A 600-month waiting period is a misread, not a policy term."""
    facts = {
        fact.fact_key: fact
        for fact in RuleBasedFactExtractor().extract(
            [clause(CLAUSE_BEFORE_COVER_STARTS, "Waiting", "Pre-existing diseases: 600 months.")]
        )
    }

    assert facts[FACT_PED_WAITING_MONTHS].confidence_state == CONFIDENCE_NOT_FOUND


def test_extraction_is_deterministic() -> None:
    pages = [ExtractedPage(1, POLICY_TEXT.strip(), METHOD_NATIVE, 1.0)]
    clauses = segment(pages)

    first = RuleBasedFactExtractor().extract(clauses)
    second = RuleBasedFactExtractor().extract(clauses)

    assert [(f.fact_key, f.value, f.confidence_state) for f in first] == [
        (f.fact_key, f.value, f.confidence_state) for f in second
    ]


def test_no_model_participates_in_extraction() -> None:
    """CLAUDE.md, and docs/11_BUILD_PLAN.md: AI explanation comes after the
    structured output is correct."""
    import pathlib

    import app.extraction

    for path in pathlib.Path(app.extraction.__path__[0]).glob("*.py"):
        source = path.read_text().lower()
        for banned in ("import openai", "import anthropic", "import httpx", "import requests"):
            assert banned not in source, path.name


# -------------------------------------------------------------- pipeline ---


async def upload_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings, text: str
) -> tuple[str, str]:
    from app.policies import service as policy_service

    user = await make_user(db)
    result = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="policy.pdf",
        data=pdf_bytes(text=text),
    )
    return result.policy.id, result.documents[0].id


async def test_processing_a_policy_stores_pages_clauses_and_facts(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    policy_id, document_id = await upload_policy(
        db, storage, settings, POLICY_TEXT.replace("\n", " ")
    )

    result = await process_document(
        db, policy_id=policy_id, document_id=document_id, storage=storage
    )

    assert result.pages == 1
    assert result.facts_found >= 3
    assert (await db.execute(select(PolicyPage))).scalars().all()
    assert (await db.execute(select(PolicyClause))).scalars().all()

    run = (await db.execute(select(ExtractionRun))).scalar_one()
    assert run.status == RUN_SUCCEEDED
    # No OCR ran, and no model participated: both recorded as null rather
    # than left ambiguous.
    assert run.ocr_provider is None
    assert run.ai_provider is None


async def test_a_processed_policy_becomes_ready(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    policy_id, document_id = await upload_policy(
        db, storage, settings, POLICY_TEXT.replace("\n", " ")
    )

    await process_document(db, policy_id=policy_id, document_id=document_id, storage=storage)

    from app.policies.models import UploadedPolicy

    policy = (
        await db.execute(select(UploadedPolicy).where(UploadedPolicy.id == policy_id))
    ).scalar_one()
    assert policy.status == STATUS_READY
    assert policy.ready_at is not None


async def test_every_stored_fact_with_a_value_points_at_a_clause(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A fact without a clause is a guess. Only NOT_FOUND may be clause-less."""
    policy_id, document_id = await upload_policy(
        db, storage, settings, POLICY_TEXT.replace("\n", " ")
    )
    await process_document(db, policy_id=policy_id, document_id=document_id, storage=storage)

    facts = list((await db.execute(select(PolicyFact))).scalars().all())

    assert facts
    for fact in facts:
        if fact.value_json is not None:
            assert fact.clause_id is not None, fact.fact_key
            assert fact.source_page is not None
            assert fact.source_quote


async def test_a_scan_leaves_the_policy_visibly_failed(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """CLAUDE.md: a failed extraction must remain visibly failed."""
    from app.policies import service as policy_service
    from app.policies.models import UploadedPolicy

    user = await make_user(db)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="scan.png",
        data=PNG_BYTES,
    )

    with pytest.raises(ExtractionFailed):
        await process_document(
            db,
            policy_id=uploaded.policy.id,
            document_id=uploaded.documents[0].id,
            storage=storage,
        )

    policy = (
        await db.execute(select(UploadedPolicy).where(UploadedPolicy.id == uploaded.policy.id))
    ).scalar_one()
    assert policy.status == STATUS_FAILED
    assert policy.failure_reason == "SCAN_NEEDS_OCR"

    run = (await db.execute(select(ExtractionRun))).scalar_one()
    assert run.status == RUN_FAILED


def test_a_permanent_failure_is_not_retried() -> None:
    """Retrying an encrypted PDF three times only delays telling the reader."""
    assert is_permanent("ENCRYPTED_PDF")
    assert is_permanent("SCAN_NEEDS_OCR")
    assert not is_permanent("UNEXPECTED_ERROR")


def test_every_failure_reason_has_wording_the_reader_can_act_on() -> None:
    for reason, message in FAILURE_MESSAGES.items():
        assert len(message) > 40, reason
        assert message.endswith(".")
        # No internal vocabulary reaches the reader.
        assert "OCR" not in message or "scans" in message
        assert reason not in message
