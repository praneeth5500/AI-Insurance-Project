"""The synthetic health product catalogue.

**Everything here is invented.** The insurers do not exist, the products do
not exist, and the fit labels are authored demo content — not judgements the
product computed about a real policy. docs/11_BUILD_PLAN.md Phase 5 says "Use
synthetic products", and docs/00_README.md's prototype truth rule requires
that such data is never allowed to look verified.

Three rules were followed while writing this file:

1. **No real insurer or product name.** Every name is obviously fictional, so
   a screenshot of this build cannot be mistaken for a real comparison.
2. **No premium.** CLAUDE.md is unconditional: never invent a premium. These
   products carry no price at all, and the UI says so rather than showing a
   made-up number.
3. **No claim outcomes, no network claims, no eligibility promises.** The
   watch-outs and fit notes describe policy *shapes* in the abstract.

Real products arrive in Phase 8 behind provenance and versioning. The
matching engine that produces genuine fit assessments arrives in Phase 9.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.products.provenance import SYNTHETIC, SourceType

CATALOGUE_VERSION = "synthetic-health-001"

#: Fit labels from docs/01_PRODUCT_SPEC.md section 2.6.
FitLabel = Literal["STRONG", "GOOD", "TRADE_OFF", "NEEDS_ATTENTION", "UNVERIFIED"]

#: Fit dimensions, also from section 2.6. The keys match the priority keys in
#: the questionnaire where the two overlap, so a user's priority can be lined
#: up with the dimension it refers to.
FACTOR_LABELS: dict[str, str] = {
    "coverage": "Coverage",
    "copay": "Co-pay",
    "waiting_periods": "Waiting periods",
    "hospital_flexibility": "Hospital flexibility",
    "network": "Network usefulness",
    "sublimits": "Sub-limits",
    "exclusions": "Exclusions and conditions",
    "budget": "Budget",
}

#: Which questionnaire priority maps onto which fit dimension.
#: docs/01_PRODUCT_SPEC.md section 2.3 priorities -> section 2.6 dimensions.
PRIORITY_TO_FACTOR: dict[str, str] = {
    "lower_premium": "budget",
    "low_copay": "copay",
    "short_waiting_periods": "waiting_periods",
    "hospital_flexibility": "hospital_flexibility",
    "broad_coverage": "coverage",
    "fewer_sublimits": "sublimits",
}


class ProductFit(BaseModel):
    """One authored fit judgement for a demo product."""

    model_config = ConfigDict(frozen=True)

    factor: str
    label: FitLabel
    #: Plain-language note shown under "Why this matches".
    note: str


class SyntheticProduct(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    insurer_name: str
    product_name: str
    source_type: SourceType = SYNTHETIC
    catalogue_version: str = CATALOGUE_VERSION
    fits: tuple[ProductFit, ...]
    #: The single most important thing to be aware of. Every product has one:
    #: docs/02_UX_UI_SPEC.md rule 4 — trust requires discussing disadvantages.
    watch_out: str

    def fit(self, factor: str) -> ProductFit | None:
        return next((entry for entry in self.fits if entry.factor == factor), None)


def _fits(**labels: tuple[FitLabel, str]) -> tuple[ProductFit, ...]:
    return tuple(
        ProductFit(factor=factor, label=label, note=note)
        for factor, (label, note) in labels.items()
    )


#: Ten demo products, so the "5 primary + see 5 more" result set is real
#: (docs/01_PRODUCT_SPEC.md section 2.5).
PRODUCTS: tuple[SyntheticProduct, ...] = (
    SyntheticProduct(
        id="sp_meridian_core",
        insurer_name="Meridian Mutual (demo)",
        product_name="Core Health",
        fits=_fits(
            coverage=("GOOD", "Covers hospitalisation with a broad set of day-care treatments."),
            copay=("STRONG", "No share of the bill is passed back to you on a standard claim."),
            waiting_periods=(
                "GOOD",
                "Shorter than average before existing conditions are covered.",
            ),
            hospital_flexibility=(
                "TRADE_OFF",
                "You can use any hospital, but paperwork differs outside the network.",
            ),
            network=("GOOD", "A wide network in larger cities."),
            sublimits=("STRONG", "No separate caps on individual treatments."),
            exclusions=("GOOD", "A short, clearly written exclusions list."),
            budget=("TRADE_OFF", "Sits above the middle of the range for this level of cover."),
        ),
        watch_out=(
            "Room charges are capped, so a more expensive room can reduce what is paid on the "
            "whole bill."
        ),
    ),
    SyntheticProduct(
        id="sp_northgate_value",
        insurer_name="Northgate Assurance (demo)",
        product_name="Value Shield",
        fits=_fits(
            coverage=("TRADE_OFF", "Covers the essentials; several add-ons are optional extras."),
            copay=("NEEDS_ATTENTION", "You pay a fixed share of every claim."),
            waiting_periods=(
                "TRADE_OFF",
                "Existing conditions wait longer than most policies here.",
            ),
            hospital_flexibility=("GOOD", "Cashless treatment across a reasonable network."),
            network=("TRADE_OFF", "Thinner outside major cities."),
            sublimits=("NEEDS_ATTENTION", "Several treatments have their own separate caps."),
            exclusions=("TRADE_OFF", "A longer exclusions list than average."),
            budget=("STRONG", "One of the lower-cost options at this level of cover."),
        ),
        watch_out=(
            "A co-pay applies to every claim, so a low premium can cost more when you actually "
            "claim."
        ),
    ),
    SyntheticProduct(
        id="sp_harbourline_family",
        insurer_name="Harbourline Health (demo)",
        product_name="Family First",
        fits=_fits(
            coverage=("STRONG", "One shared cover amount across everyone on the policy."),
            copay=("GOOD", "No co-pay below a set claim size."),
            waiting_periods=("TRADE_OFF", "Standard waiting periods for existing conditions."),
            hospital_flexibility=(
                "STRONG",
                "Any hospital, with cashless treatment widely available.",
            ),
            network=("STRONG", "Broad network including smaller towns."),
            sublimits=("GOOD", "Few separate caps."),
            exclusions=("GOOD", "Conditions are set out in plain language."),
            budget=("TRADE_OFF", "Costs more than single-person cover for obvious reasons."),
        ),
        watch_out=(
            "Cover is shared, so one large claim can leave less available for everyone else "
            "that year."
        ),
    ),
    SyntheticProduct(
        id="sp_alderwood_essential",
        insurer_name="Alderwood Cover (demo)",
        product_name="Essential Care",
        fits=_fits(
            coverage=("TRADE_OFF", "A lower cover amount than most options here."),
            copay=("STRONG", "No co-pay on standard claims."),
            waiting_periods=(
                "STRONG",
                "Among the shortest waits before existing conditions are covered.",
            ),
            hospital_flexibility=("GOOD", "Cashless treatment across a solid network."),
            network=("GOOD", "Reasonable coverage in most cities."),
            sublimits=("TRADE_OFF", "A few treatments carry their own caps."),
            exclusions=("GOOD", "Short exclusions list."),
            budget=("GOOD", "Below the middle of the range."),
        ),
        watch_out="The cover amount is lower, so a long hospital stay could use most of it.",
    ),
    SyntheticProduct(
        id="sp_beacon_wide",
        insurer_name="Beacon Life (demo)",
        product_name="Wide Cover",
        fits=_fits(
            coverage=("STRONG", "A high cover amount with restoration after a claim."),
            copay=("GOOD", "No co-pay under most circumstances."),
            waiting_periods=(
                "NEEDS_ATTENTION",
                "A longer wait before existing conditions are covered.",
            ),
            hospital_flexibility=("STRONG", "No restriction on which hospital you use."),
            network=("GOOD", "Wide network in cities."),
            sublimits=("STRONG", "No separate treatment caps."),
            exclusions=("TRADE_OFF", "Some conditions carry extra requirements."),
            budget=("NEEDS_ATTENTION", "One of the more expensive options at this level."),
        ),
        watch_out="Existing conditions wait longer here than on most of the other options shown.",
    ),
    SyntheticProduct(
        id="sp_stillwater_flex",
        insurer_name="Stillwater Mutual (demo)",
        product_name="Flexible Plan",
        fits=_fits(
            coverage=("GOOD", "Mid-range cover with optional top-ups."),
            copay=("TRADE_OFF", "A co-pay applies above a set age."),
            waiting_periods=("GOOD", "Shorter than average waits."),
            hospital_flexibility=("GOOD", "Any hospital, cashless within the network."),
            network=("TRADE_OFF", "Network is concentrated in a few regions."),
            sublimits=("GOOD", "Only one or two treatments are capped."),
            exclusions=("GOOD", "Clear and reasonably short."),
            budget=("GOOD", "Middle of the range."),
        ),
        watch_out=(
            "A co-pay starts applying above a set age, which can change what you pay later on."
        ),
    ),
    SyntheticProduct(
        id="sp_kestrel_secure",
        insurer_name="Kestrel Insurance (demo)",
        product_name="Secure Health",
        fits=_fits(
            coverage=("GOOD", "Solid mid-range cover."),
            copay=("STRONG", "No co-pay."),
            waiting_periods=("TRADE_OFF", "Standard waiting periods."),
            hospital_flexibility=("TRADE_OFF", "Cashless treatment only inside the network."),
            network=("NEEDS_ATTENTION", "A smaller network than most options here."),
            sublimits=("GOOD", "Few caps."),
            exclusions=("GOOD", "Straightforward."),
            budget=("GOOD", "Slightly below the middle of the range."),
        ),
        watch_out=(
            "Cashless treatment only works inside the network, so an out-of-network hospital "
            "means paying first and claiming later."
        ),
    ),
    SyntheticProduct(
        id="sp_orchard_senior",
        insurer_name="Orchard Assurance (demo)",
        product_name="Senior Care",
        fits=_fits(
            coverage=("GOOD", "Designed around cover for older adults."),
            copay=("NEEDS_ATTENTION", "A co-pay applies to every claim."),
            waiting_periods=(
                "GOOD",
                "Shorter waits for existing conditions than most options for this age group.",
            ),
            hospital_flexibility=("GOOD", "Cashless treatment across a wide network."),
            network=("STRONG", "Strong network coverage, including smaller towns."),
            sublimits=("TRADE_OFF", "Some treatments are capped."),
            exclusions=("TRADE_OFF", "More conditions attached than average."),
            budget=("TRADE_OFF", "Higher cost, which is typical for this age group."),
        ),
        watch_out="A co-pay applies to every claim, which adds up if claims are frequent.",
    ),
    SyntheticProduct(
        id="sp_verdant_balanced",
        insurer_name="Verdant Health (demo)",
        product_name="Balanced Cover",
        fits=_fits(
            coverage=("GOOD", "Balanced cover with no obvious gaps."),
            copay=("GOOD", "No co-pay on most claims."),
            waiting_periods=("GOOD", "Around average."),
            hospital_flexibility=("GOOD", "Any hospital, cashless in-network."),
            network=("GOOD", "Broad enough in most cities."),
            sublimits=("TRADE_OFF", "A handful of caps apply."),
            exclusions=("GOOD", "Nothing unusual."),
            budget=("GOOD", "Middle of the range."),
        ),
        watch_out="Nothing stands out as weak, but nothing stands out as especially strong either.",
    ),
    SyntheticProduct(
        id="sp_lantern_starter",
        insurer_name="Lantern Cover (demo)",
        product_name="Starter Health",
        fits=_fits(
            coverage=("NEEDS_ATTENTION", "The lowest cover amount of the options shown."),
            copay=("GOOD", "No co-pay."),
            waiting_periods=("TRADE_OFF", "Standard waits."),
            hospital_flexibility=("TRADE_OFF", "In-network cashless treatment only."),
            network=("TRADE_OFF", "Limited outside larger cities."),
            sublimits=("NEEDS_ATTENTION", "Several treatments carry caps."),
            exclusions=("UNVERIFIED", "Not enough detail recorded for this demo product."),
            budget=("STRONG", "The lowest-cost option shown."),
        ),
        watch_out=(
            "The cover amount is the lowest here, so it may not stretch far for a serious "
            "hospital stay."
        ),
    ),
)


def all_products() -> tuple[SyntheticProduct, ...]:
    return PRODUCTS


def get_product(product_id: str) -> SyntheticProduct | None:
    return next((product for product in PRODUCTS if product.id == product_id), None)
