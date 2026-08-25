"""The product detail screen (docs/11_BUILD_PLAN.md Phase 7)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.products import service
from app.products.catalogue import all_products
from app.products.errors import ProductNotFoundError
from app.products.schemas import ProductDetailView
from app.products.sections import (
    FACTOR_EXAMPLES,
    SECTION_DEFINITIONS,
    build_policy_sections,
)
from app.recommendations.ordering import strongest_fits
from tests.test_questionnaire import make_user

REFERENCE = "sp_meridian_core"


async def detail_view(db: AsyncSession, reference: str = REFERENCE) -> ProductDetailView:
    user = await make_user(db)
    detail = await service.get_detail(db, user=user, product_reference=reference)
    return ProductDetailView.of(
        detail, highlight_factors=strongest_fits(detail.product, ["low_copay"])
    )


# --------------------------------------------------------------- sections ---


def test_sections_match_the_specification() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.8."""
    labels = [label for _, label, _ in SECTION_DEFINITIONS]

    assert labels == [
        "Your Cover",
        "Your Costs",
        "Waiting Periods",
        "Important Limits",
        "Not Covered",
        "Claims",
    ]


def test_every_product_produces_every_section() -> None:
    for product in all_products():
        sections = build_policy_sections(product)
        assert [section.label for section in sections] == [
            label for _, label, _ in SECTION_DEFINITIONS
        ]


def test_sections_reuse_the_fit_notes_rather_than_restating_them() -> None:
    """One source of truth: a card and its detail page cannot disagree."""
    product = next(p for p in all_products() if p.id == REFERENCE)
    sections = build_policy_sections(product)

    values = {fact.value for section in sections for fact in section.facts}
    notes = {fit.note for fit in product.fits}

    assert values <= notes


def test_every_fact_offers_an_example() -> None:
    """docs/01_PRODUCT_SPEC.md section 2.8: "Explain with example"."""
    for product in all_products():
        for section in build_policy_sections(product):
            for fact in section.facts:
                assert fact.example, f"{product.id}/{fact.key}"


def test_examples_are_hypothetical_not_claims_about_the_product() -> None:
    """docs/12_BETA_CHECKLIST.md: examples clearly labeled as examples."""
    for example in FACTOR_EXAMPLES.values():
        assert any(
            marker in example.lower()
            for marker in ("if ", "usually", "can ", "means", "two policies")
        ), example
        # Never asserted of this policy.
        assert "this policy pays" not in example.lower()


# ----------------------------------------------------------------- sources --


def test_no_synthetic_fact_claims_to_have_a_source() -> None:
    """A fabricated citation is release-blocking
    (docs/10_TESTING_AND_EVALS.md section 8)."""
    for product in all_products():
        for section in build_policy_sections(product):
            for fact in section.facts:
                assert fact.has_source is False
                assert fact.source_note


async def test_the_source_documents_section_explains_its_emptiness(
    db: AsyncSession,
) -> None:
    view = await detail_view(db)

    assert view.source_documents == []
    assert "demo product" in view.source_documents_note


async def test_provenance_travels_with_the_response(db: AsyncSession) -> None:
    """docs/08_API_CONTRACTS.md section 5: include source/provenance metadata."""
    view = await detail_view(db)

    assert view.provenance.source_type == "SYNTHETIC"
    assert view.provenance.verified_at is None
    assert "synthetic" in view.provenance.explanation.lower()


# ------------------------------------------------------------------- hero ---


async def test_the_hero_carries_three_strengths_and_one_trade_off(
    db: AsyncSession,
) -> None:
    """docs/02_UX_UI_SPEC.md section 11."""
    view = await detail_view(db)

    assert 1 <= len(view.highlights) <= 3
    assert view.watch_out.strip()


async def test_highlights_follow_the_reader_s_priorities(db: AsyncSession) -> None:
    user = await make_user(db)
    detail = await service.get_detail(db, user=user, product_reference=REFERENCE)

    copay_first = ProductDetailView.of(
        detail, highlight_factors=strongest_fits(detail.product, ["low_copay"])
    )
    sublimits_first = ProductDetailView.of(
        detail, highlight_factors=strongest_fits(detail.product, ["fewer_sublimits"])
    )

    assert copay_first.highlights[0].factor == "copay"
    assert sublimits_first.highlights[0].factor == "sublimits"


async def test_no_overall_score_appears(db: AsyncSession) -> None:
    view = await detail_view(db)
    serialized = view.model_dump_json().lower()

    for forbidden in ("score", "rank", "rating", "best policy", "guarantee"):
        assert forbidden not in serialized


async def test_no_premium_appears(db: AsyncSession) -> None:
    """CLAUDE.md: never invent a premium."""
    view = await detail_view(db)

    # Figures appear only inside examples, never as a product fact.
    for section in view.sections:
        for fact in section.facts:
            assert "₹" not in fact.value


# ------------------------------------------------------------------ saving --


async def test_saving_is_idempotent(db: AsyncSession) -> None:
    user = await make_user(db)

    await service.save(db, user=user, product_reference=REFERENCE)
    await service.save(db, user=user, product_reference=REFERENCE)

    assert await service.list_saved(db, user=user) == [REFERENCE]


async def test_saving_survives_a_reload(db: AsyncSession) -> None:
    user = await make_user(db)
    await service.save(db, user=user, product_reference=REFERENCE)

    detail = await service.get_detail(db, user=user, product_reference=REFERENCE)

    assert detail.saved is True


async def test_unsaving_what_was_never_saved_is_not_an_error(db: AsyncSession) -> None:
    user = await make_user(db)

    assert await service.unsave(db, user=user, product_reference=REFERENCE) is False


async def test_saves_are_private_to_the_user(db: AsyncSession) -> None:
    owner = await make_user(db, "owner@example.com")
    other = await make_user(db, "other@example.com")
    await service.save(db, user=owner, product_reference=REFERENCE)

    assert await service.list_saved(db, user=other) == []
    other_detail = await service.get_detail(db, user=other, product_reference=REFERENCE)
    assert other_detail.saved is False


async def test_an_unknown_product_cannot_be_saved(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(ProductNotFoundError):
        await service.save(db, user=user, product_reference="sp_not_real")


async def test_an_unknown_product_has_no_detail(db: AsyncSession) -> None:
    user = await make_user(db)

    with pytest.raises(ProductNotFoundError):
        await service.get_detail(db, user=user, product_reference="sp_not_real")


# ------------------------------------------------------------ authorization --


async def test_the_endpoints_require_a_session(api: AsyncClient) -> None:
    assert (await api.get(f"/api/v1/products/{REFERENCE}")).status_code == 401
    assert (await api.put(f"/api/v1/products/{REFERENCE}/saved")).status_code == 401
    assert (await api.delete(f"/api/v1/products/{REFERENCE}/saved")).status_code == 401
