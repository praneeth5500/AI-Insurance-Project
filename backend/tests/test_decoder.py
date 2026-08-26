"""The decoder report (docs/11_BUILD_PLAN.md Phase 12).

The report is the point in this product where a machine's reading of someone's
policy is presented back to them as fact. So the tests concentrate on the
places that could mislead: a value we are not sure about, two clauses that
disagree, a fact we never found, and whether the reader can always get back to
the wording the claim came from.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.decoder import service
from app.decoder.content import CONTENT, SECTION_ORDER, describe_value
from app.decoder.schemas import DecoderView
from app.extraction.facts import (
    FACT_COPAY_PERCENT,
    FACT_PED_WAITING_MONTHS,
    FACT_SUM_INSURED_INR,
    KNOWN_FACT_KEYS,
)
from app.extraction.models import (
    CONFIDENCE_CONFLICTING,
    CONFIDENCE_NOT_FOUND,
    PolicyFact,
)
from app.extraction.pipeline import process_document
from app.jobs.queue import DatabaseJobQueue
from app.policies import service as policy_service
from app.policies.errors import PolicyNotFoundError
from app.policies.storage import LocalFileStorage
from app.users.models import User
from tests.test_extraction import POLICY_TEXT
from tests.test_policy_upload import pdf_bytes
from tests.test_questionnaire import make_user


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


async def decoded_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings, *, email: str = "r@example.com"
) -> tuple[User, service.DecodedPolicy]:
    user = await make_user(db, email)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="wording.pdf",
        data=pdf_bytes(text=POLICY_TEXT.strip()),
    )
    await process_document(
        db,
        policy_id=uploaded.policy.id,
        document_id=uploaded.documents[0].id,
        storage=storage,
    )
    return user, await service.decode(db, user=user, policy_id=uploaded.policy.id)


# ---------------------------------------------------------------- content ---


def test_the_sections_are_the_ones_the_specification_names() -> None:
    """docs/01_PRODUCT_SPEC.md section 3.4."""
    assert [label for _, label in SECTION_ORDER] == [
        "Your Cover",
        "Your Costs",
        "Before Cover Starts",
        "Important Limits",
        "Not Covered",
        "At Claim Time",
        "Policy Details",
    ]


def test_every_extractable_fact_has_authored_content() -> None:
    """A fact with no explanation is not shown, so a gap here silently
    removes information from the report."""
    assert set(CONTENT) == set(KNOWN_FACT_KEYS)


def test_the_technical_term_is_kept_not_replaced() -> None:
    """docs/07_POLICY_DECODER_AI.md section 6: explain the term without
    hiding it. A reader who learns "co-payment" can use it on their
    insurer's website; one shown a friendlier invented word cannot."""
    for content in CONTENT.values():
        assert content.technical_term
        assert content.title.lower() != content.technical_term.lower()


def test_every_card_says_what_still_needs_checking() -> None:
    """A card with nothing to watch for invites more trust than an extracted
    number has earned."""
    for key, content in CONTENT.items():
        assert len(content.conditions) > 40, key


def test_examples_are_hypothetical_not_claims_about_this_policy() -> None:
    for key, content in CONTENT.items():
        lowered = content.example.lower()
        assert lowered.startswith(("if ", "a policy", "with a")), key
        assert "your policy pays" not in lowered
        assert "you will be paid" not in lowered


def test_a_value_becomes_a_sentence_a_reader_can_act_on() -> None:
    assert describe_value(FACT_SUM_INSURED_INR, {"amount": 500_000}) == (
        "This policy covers up to ₹5 lakh."
    )
    assert "36 months" in (describe_value(FACT_PED_WAITING_MONTHS, {"months": 36}) or "")
    assert "3 years" in (describe_value(FACT_PED_WAITING_MONTHS, {"months": 36}) or "")


def test_a_zero_copay_is_stated_as_good_news_not_as_zero_percent() -> None:
    statement = describe_value(FACT_COPAY_PERCENT, {"percent": 0})

    assert statement is not None
    assert "no share" in statement


def test_an_absent_value_produces_no_sentence() -> None:
    """A sentence built around a blank is how a report claims something it
    does not know."""
    assert describe_value(FACT_PED_WAITING_MONTHS, None) is None


# ----------------------------------------------------------------- report ---


async def test_the_report_arranges_facts_into_the_right_sections(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, decoded = await decoded_policy(db, storage, settings)

    sections = {section.key: section for section in decoded.sections}
    assert "your-cover" in sections
    assert "before-cover-starts" in sections
    keys = {fact.fact_key for fact in sections["before-cover-starts"].facts}
    assert FACT_PED_WAITING_MONTHS in keys


async def test_every_stated_value_can_be_traced_to_the_wording(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 6 ends every card with its source.

    A claim about someone's policy that they cannot check is the thing this
    product exists not to do.
    """
    _, decoded = await decoded_policy(db, storage, settings)

    stated = [fact for section in decoded.sections for fact in section.facts if fact.statement]
    assert stated
    for fact in stated:
        assert fact.citation is not None, fact.fact_key
        assert fact.citation.page >= 1
        assert fact.citation.quote
        # The whole clause travels too, so "view source wording" shows the
        # sentence in context rather than stranded.
        assert fact.citation.clause_text


async def test_a_fact_we_could_not_find_is_shown_as_unknown(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/12_BETA_CHECKLIST.md: not-found state visible.

    Omitting it would tell the reader their policy has no such waiting
    period, which is the opposite of what we know.
    """
    _, decoded = await decoded_policy(db, storage, settings)

    unknown = [
        fact
        for section in decoded.sections
        for fact in section.facts
        if fact.confidence_state == CONFIDENCE_NOT_FOUND
    ]
    assert unknown
    for fact in unknown:
        assert fact.statement is None
        assert fact.reliable is False
        # The card still explains what the thing *is*, so an unknown is
        # informative rather than blank.
        assert fact.example
        assert fact.conditions


async def test_a_conflicting_fact_shows_the_disagreement_not_a_winner(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 5."""
    user, decoded = await decoded_policy(db, storage, settings)

    # Force the conflict the way extraction would have recorded it.
    fact = next(
        item
        for item in (
            await db.execute(
                __import__("sqlalchemy")
                .select(PolicyFact)
                .where(
                    PolicyFact.policy_id == decoded.policy.id,
                    PolicyFact.fact_key == FACT_PED_WAITING_MONTHS,
                )
            )
        ).scalars()
    )
    fact.confidence_state = CONFIDENCE_CONFLICTING
    fact.value_json = None
    fact.alternatives_json = [
        {"value": {"months": 36}, "page": 14, "quote": "…after 36 months…"},
        {"value": {"months": 48}, "page": 22, "quote": "…after 48 months…"},
    ]
    await db.commit()

    rebuilt = await service.decode(db, user=user, policy_id=decoded.policy.id)
    conflicting = next(
        item
        for section in rebuilt.sections
        for item in section.facts
        if item.fact_key == FACT_PED_WAITING_MONTHS
    )

    assert conflicting.statement is None
    assert conflicting.reliable is False
    assert {citation.page for citation in conflicting.alternatives} == {14, 22}
    assert rebuilt.conflicting_count == 1


async def test_the_report_says_how_much_it_could_not_determine(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A report that looks complete when it is not is the failure this whole
    phase exists to avoid."""
    _, decoded = await decoded_policy(db, storage, settings)
    view = DecoderView.of(decoded)

    assert view.unknown_count >= 1
    # And the reader is told the report is not the whole document.
    assert view.unread_clause_count >= 1


async def test_the_report_records_whether_a_model_was_involved(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, decoded = await decoded_policy(db, storage, settings)
    view = DecoderView.of(decoded)

    assert view.ai_provider is None
    assert view.schema_version is not None


async def test_no_card_promises_a_claim_outcome(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 9."""
    _, decoded = await decoded_policy(db, storage, settings)
    text = DecoderView.of(decoded).model_dump_json().lower()

    for forbidden in (
        "will be approved",
        "guaranteed",
        "you will be paid",
        "claim approved",
        "we recommend you",
    ):
        assert forbidden not in text


# ---------------------------------------------------------- authorization ---


async def test_one_user_cannot_decode_another_users_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, decoded = await decoded_policy(db, storage, settings, email="owner@example.com")
    intruder = await make_user(db, "intruder@example.com")

    with pytest.raises(PolicyNotFoundError):
        await service.decode(db, user=intruder, policy_id=decoded.policy.id)


async def test_a_policy_that_is_still_processing_cannot_be_decoded(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A partial report would be indistinguishable from a complete one."""
    user = await make_user(db)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="wording.pdf",
        data=pdf_bytes(text=POLICY_TEXT.strip()),
    )

    with pytest.raises(service.PolicyNotReadyError):
        await service.decode(db, user=user, policy_id=uploaded.policy.id)
