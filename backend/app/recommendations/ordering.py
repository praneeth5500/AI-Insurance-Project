"""Prototype ordering.

**This is not the matching engine.** docs/06_RECOMMENDATION_ENGINE.md
describes hard eligibility, fit evaluators, versioned weighting and an
internal relevance value; all of that is Phase 9. What lives here is the
smallest deterministic ordering that lets the results UX be reviewed on
synthetic products, and it is labelled as such everywhere it surfaces.

Two properties are real, and are the ones Phase 9 will inherit:

* **Deterministic.** The same answers and priorities always produce the same
  order — docs/10_TESTING_AND_EVALS.md section 3 requires it, and a
  recommendation that reshuffles on refresh is not one anyone can trust.
* **No overall score.** Nothing here produces a 0–100 number, and none of the
  intermediate values reach the screen
  (docs/01_PRODUCT_SPEC.md section 2.5).

An LLM is not involved at any point. CLAUDE.md is explicit: the model never
generates the ranking.
"""

from __future__ import annotations

from app.products.catalogue import PRIORITY_TO_FACTOR, SyntheticProduct

ORDERING_VERSION = "prototype-ordering-001"

#: How well an authored fit label serves a priority the user chose. These are
#: presentation weights for a demo, not insurance judgements, which is why
#: they live in one small table rather than being scattered through the code.
_LABEL_RANK: dict[str, int] = {
    "STRONG": 3,
    "GOOD": 2,
    "TRADE_OFF": 1,
    "NEEDS_ATTENTION": 0,
    # Unknown data is never quietly treated as average
    # (docs/06_RECOMMENDATION_ENGINE.md section 8).
    "UNVERIFIED": 0,
}


def priority_alignment(product: SyntheticProduct, priorities: list[str]) -> int:
    """How many of the user's chosen priorities this product serves well.

    Deliberately crude: a sum over the priorities the user actually picked.
    Nothing is inferred about priorities they did not choose.
    """
    total = 0
    for priority in priorities:
        factor = PRIORITY_TO_FACTOR.get(priority)
        if factor is None:
            continue
        fit = product.fit(factor)
        if fit is not None:
            total += _LABEL_RANK.get(fit.label, 0)
    return total


def order_products(
    products: tuple[SyntheticProduct, ...], priorities: list[str]
) -> list[SyntheticProduct]:
    """Order for presentation. Stable, so ties never shuffle between requests."""
    return sorted(
        products,
        key=lambda product: (-priority_alignment(product, priorities), product.id),
    )


def strongest_fits(product: SyntheticProduct, priorities: list[str], limit: int = 3) -> list[str]:
    """The factors to highlight on the card.

    docs/01_PRODUCT_SPEC.md section 2.5 asks for the 3 strongest fit areas.
    Factors the user said mattered come first, so the highlights answer *their*
    question rather than showing the product's best angle.
    """
    chosen_factors = [
        factor
        for priority in priorities
        if (factor := PRIORITY_TO_FACTOR.get(priority)) is not None
    ]

    def sort_key(factor_and_rank: tuple[str, int]) -> tuple[int, int, str]:
        factor, rank = factor_and_rank
        return (0 if factor in chosen_factors else 1, -rank, factor)

    ranked = [
        (fit.factor, _LABEL_RANK.get(fit.label, 0))
        for fit in product.fits
        # Only genuine strengths are ever called a strength.
        if fit.label in ("STRONG", "GOOD")
    ]
    ranked.sort(key=sort_key)
    return [factor for factor, _ in ranked[:limit]]
