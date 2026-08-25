"""Policy sections for the product detail screen.

`docs/01_PRODUCT_SPEC.md` section 2.8 fixes the section list, and says every
technical item should support **Explain with example** and **View source
wording**.

Sections are derived from the fit data the catalogue already holds rather than
authored a second time. That keeps one source of truth: a product cannot say
one thing on its match card and another on its detail page.

Two rules shape the content:

* **No invented figures.** Where a real policy would state a number, the fact
  says so instead of making one up. Consistent with the catalogue, which
  carries no premium — see `docs/PHASE_5_NOTES.md`.
* **Examples explain the mechanism, never the product.** They are generic,
  clearly labelled, and phrased hypothetically, so an illustrative number can
  never be read as this product's terms
  (`docs/12_BETA_CHECKLIST.md`: "Examples clearly labeled as examples").
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.products.catalogue import FACTOR_LABELS, SyntheticProduct

#: Section keys and labels, verbatim from docs/01_PRODUCT_SPEC.md section 2.8.
#: "Why this matches you" and "What to watch out for" are rendered above these
#: from the fit data, so they are not repeated here.
SECTION_DEFINITIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("your-cover", "Your Cover", ("coverage",)),
    ("your-costs", "Your Costs", ("copay", "budget")),
    ("waiting-periods", "Waiting Periods", ("waiting_periods",)),
    ("important-limits", "Important Limits", ("sublimits",)),
    ("not-covered", "Not Covered", ("exclusions",)),
    ("claims", "Claims", ("hospital_flexibility", "network")),
)

#: "Explain with example" copy, one per dimension.
#:
#: Each is written as a hypothetical about policies in general. The figures
#: exist to make a mechanism concrete and are never attributed to a product —
#: that distinction is what makes an example safe.
FACTOR_EXAMPLES: dict[str, str] = {
    "coverage": (
        "If your cover is ₹5 lakh and a hospital stay comes to ₹7 lakh, the policy pays "
        "up to ₹5 lakh and the remaining ₹2 lakh is yours to pay."
    ),
    "copay": (
        "If a policy has a 10% co-pay and a bill comes to ₹1 lakh, you pay ₹10,000 and "
        "the insurer pays the rest — on every claim, not just the first."
    ),
    "budget": (
        "Two policies with the same cover can differ a lot in price. A lower premium "
        "usually means something else gives: a co-pay, a lower limit, or a longer wait."
    ),
    "waiting_periods": (
        "If a policy waits 3 years before covering an existing condition, a claim for "
        "that condition in year 2 would not be paid, even though the policy is active."
    ),
    "sublimits": (
        "A sub-limit caps one type of treatment separately. If cataract surgery is "
        "capped at ₹40,000 and the procedure costs ₹60,000, you pay the difference even "
        "though your overall cover is much larger."
    ),
    "exclusions": (
        "An exclusion is something the policy never pays for. A condition is something "
        "it pays for only if certain requirements are met first."
    ),
    "hospital_flexibility": (
        "Cashless means the insurer settles directly with the hospital. Without it you "
        "pay the bill yourself and claim the money back afterwards, which can mean "
        "finding a large sum at short notice."
    ),
    "network": (
        "A network hospital has an arrangement with the insurer. Going outside it "
        "usually still works, but often without cashless treatment."
    ),
}


class PolicyFactView(BaseModel):
    """One technical item on the detail screen."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    value: str
    #: "Explain with example". Always about the mechanism, never the product.
    example: str | None = None
    #: Whether source wording exists for this fact. False for every synthetic
    #: product — inventing a citation is release-blocking
    #: (docs/10_TESTING_AND_EVALS.md section 8).
    has_source: bool = False
    source_note: str | None = None


class PolicySectionView(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    facts: tuple[PolicyFactView, ...]


SYNTHETIC_SOURCE_NOTE = (
    "This is a demo product, so there is no policy document to quote. Real products "
    "show the exact wording their facts come from."
)


def build_policy_sections(product: SyntheticProduct) -> list[PolicySectionView]:
    """The policy sections for one product, derived from its fit data."""
    sections: list[PolicySectionView] = []

    for key, label, factors in SECTION_DEFINITIONS:
        facts: list[PolicyFactView] = []
        for factor in factors:
            fit = product.fit(factor)
            if fit is None:
                continue
            facts.append(
                PolicyFactView(
                    key=factor,
                    label=FACTOR_LABELS.get(factor, factor),
                    value=fit.note,
                    example=FACTOR_EXAMPLES.get(factor),
                    has_source=False,
                    source_note=SYNTHETIC_SOURCE_NOTE,
                )
            )
        if facts:
            sections.append(PolicySectionView(key=key, label=label, facts=tuple(facts)))

    return sections
