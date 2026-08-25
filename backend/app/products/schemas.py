"""Product detail payloads.

`docs/08_API_CONTRACTS.md` section 5: "Return only verified fields. Include
source/provenance metadata." Nothing here is verified — every product is
synthetic — so the provenance travels with the response and the source state
says plainly that no document exists.
"""

from __future__ import annotations

from app.core.schema import ApiModel
from app.products.catalogue import FACTOR_LABELS, FitLabel
from app.products.sections import PolicySectionView
from app.products.service import ProductDetail


class ProductFitView(ApiModel):
    factor: str
    label: str
    fit: FitLabel
    note: str


class ProductFactView(ApiModel):
    key: str
    label: str
    value: str
    #: "Explain with example" — about the mechanism, never this product.
    example: str | None = None
    #: False for every synthetic product. A fabricated citation is
    #: release-blocking (docs/10_TESTING_AND_EVALS.md section 8).
    has_source: bool
    source_note: str | None = None


class ProductSectionView(ApiModel):
    key: str
    label: str
    facts: list[ProductFactView]


class ProvenanceView(ApiModel):
    """docs/06_RECOMMENDATION_ENGINE.md section 3 and the beta checklist."""

    source_type: str
    catalogue_version: str
    #: Null for synthetic data: there is nothing to have verified.
    verified_at: str | None = None
    explanation: str


class ProductDetailView(ApiModel):
    reference: str
    insurer_name: str
    product_name: str
    source_type: str
    #: The 3 strongest areas, for the hero (docs/02_UX_UI_SPEC.md section 11).
    highlights: list[ProductFitView]
    #: Exactly one trade-off, alongside the highlights rather than below them.
    watch_out: str
    fits: list[ProductFitView]
    sections: list[ProductSectionView]
    #: docs/01_PRODUCT_SPEC.md section 2.8 lists Source Documents as a section.
    #: Empty for synthetic products, with the reason stated.
    source_documents: list[str]
    source_documents_note: str
    provenance: ProvenanceView
    saved: bool

    @classmethod
    def of(cls, detail: ProductDetail, *, highlight_factors: list[str]) -> ProductDetailView:
        product = detail.product

        def fit_view(factor: str, label: FitLabel, note: str) -> ProductFitView:
            return ProductFitView(
                factor=factor,
                label=FACTOR_LABELS.get(factor, factor),
                fit=label,
                note=note,
            )

        fits = [fit_view(fit.factor, fit.label, fit.note) for fit in product.fits]

        def section_view(section: PolicySectionView) -> ProductSectionView:
            return ProductSectionView(
                key=section.key,
                label=section.label,
                facts=[
                    ProductFactView(
                        key=fact.key,
                        label=fact.label,
                        value=fact.value,
                        example=fact.example,
                        has_source=fact.has_source,
                        source_note=fact.source_note,
                    )
                    for fact in section.facts
                ],
            )

        by_factor = {fit.factor: fit for fit in fits}

        return cls(
            reference=product.id,
            insurer_name=product.insurer_name,
            product_name=product.product_name,
            source_type=product.source_type,
            # Ordered by highlight_factors, not catalogue order: the caller
            # sorted these so the reader's own priority leads.
            highlights=[by_factor[factor] for factor in highlight_factors if factor in by_factor],
            watch_out=product.watch_out,
            fits=fits,
            sections=[section_view(section) for section in detail.sections],
            source_documents=[],
            source_documents_note=(
                "No policy document exists for a demo product. For a real product this "
                "is where the wording behind each fact would be linked."
            ),
            provenance=ProvenanceView(
                source_type=product.source_type,
                catalogue_version=product.catalogue_version,
                verified_at=None,
                explanation=(
                    "This product is synthetic: it was invented to test this screen. "
                    "Nothing here has been checked against a real policy document."
                ),
            ),
            saved=detail.saved,
        )


class SaveResponse(ApiModel):
    reference: str
    saved: bool
