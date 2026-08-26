"""Policy sections for the product detail screen.

`docs/01_PRODUCT_SPEC.md` section 2.8 fixes the section list, and says every
technical item should support **Explain with example** and **View source
wording**.

Sections state the policy's **facts** — what the co-pay is, how long the wait
runs, whether room charges are capped. That is different from the "Why this
matches you" block above them, which says what those facts mean *for this
reader*. Keeping them apart matters: a fact is true for everyone, a fit is
true for one person, and blurring the two is how a prototype starts sounding
more certain than it is.

Both come from the same recorded facts, so a card and the page behind it
cannot disagree.

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

from app.matching.factors import FACTOR_LABELS
from app.products.facts import HealthFacts

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


def fact_statements(facts: HealthFacts) -> dict[str, str]:
    """One plain statement per dimension, straight from the recorded facts.

    Where a fact was never recorded the statement says so. That is the whole
    point of the "no invented figures" rule: a blank is more useful than a
    plausible number.
    """
    return {
        "coverage": _coverage_statement(facts),
        "copay": _copay_statement(facts),
        "waiting_periods": _waiting_statement(facts),
        "hospital_flexibility": _room_statement(facts),
        "network": _network_statement(facts),
        "sublimits": _sublimit_statement(facts),
        "exclusions": _exclusion_statement(facts),
        # No price exists for any product yet, and CLAUDE.md forbids inventing
        # one. The detail page says so rather than leaving a gap.
        "budget": (
            "No price is recorded for this option. Premiums come from the insurer, never from us."
        ),
    }


def _lakh(amount: int) -> str:
    value = amount / 100_000
    return f"₹{int(value)} lakh" if value.is_integer() else f"₹{value:.1f} lakh"


def _coverage_statement(facts: HealthFacts) -> str:
    options = ", ".join(_lakh(amount) for amount in sorted(facts.sum_insured_options_inr))
    restoration = {
        True: " Cover is restored after a claim.",
        False: " Cover is not restored after a claim.",
        None: "",
    }[facts.restoration]
    return f"Cover available at {options}.{restoration}"


def _copay_statement(facts: HealthFacts) -> str:
    if facts.copay_percent is None:
        return "No verified co-pay figure is recorded."
    if facts.copay_percent == 0:
        return "No co-pay: the policy pays the full covered amount on a standard claim."
    if facts.copay_applies_above_age is not None:
        return (
            f"A {facts.copay_percent}% co-pay applies to each claim from age "
            f"{facts.copay_applies_above_age}."
        )
    return f"A {facts.copay_percent}% co-pay applies to each claim."


def _waiting_statement(facts: HealthFacts) -> str:
    parts: list[str] = []
    if facts.ped_waiting_months is not None:
        parts.append(f"Existing conditions are covered after {facts.ped_waiting_months} months.")
    if facts.specific_treatment_waiting_months is not None:
        parts.append(
            f"Certain named treatments wait {facts.specific_treatment_waiting_months} months."
        )
    if facts.initial_waiting_days is not None:
        parts.append(f"There is an initial {facts.initial_waiting_days}-day wait, accidents aside.")
    return " ".join(parts) if parts else "No verified waiting periods are recorded."


def _room_statement(facts: HealthFacts) -> str:
    if facts.room_rule is None:
        return "No verified room rules are recorded."
    if facts.room_rule == "ANY_ROOM":
        return "Any room category is covered, with no separate cap on room charges."
    if facts.room_rule == "SINGLE_PRIVATE":
        return "Room charges are covered up to a single private room."
    if facts.room_rule == "CAPPED_PERCENT" and facts.room_cap_percent is not None:
        return (
            f"Room charges are capped at {facts.room_cap_percent}% of the cover amount per day. "
            "Going above the cap can reduce what is paid on the rest of the bill."
        )
    return (
        "Room charges are capped. Going above the cap can reduce what is paid on the rest "
        "of the bill."
    )


def _network_statement(facts: HealthFacts) -> str:
    if facts.cashless_scope is None:
        return "No verified network detail is recorded."
    if facts.cashless_scope == "ANY_HOSPITAL":
        return "Cashless treatment is not restricted to a network of hospitals."
    if facts.network_hospital_count is None:
        return "Cashless treatment is limited to a network; its size is not recorded."
    return (
        f"Cashless treatment works at around {facts.network_hospital_count:,} network hospitals "
        "nationally. We have not checked the network against your area."
    )


def _sublimit_statement(facts: HealthFacts) -> str:
    if facts.sublimit_count is None:
        return "No verified list of treatment caps is recorded."
    if facts.sublimit_count == 0:
        return "No individual treatment carries its own separate cap."
    named = ", ".join(facts.sublimit_treatments)
    detail = f" Capped treatments include {named}." if named else ""
    return f"{facts.sublimit_count} treatments carry their own separate cap.{detail}"


def _exclusion_statement(facts: HealthFacts) -> str:
    if facts.notable_exclusion_count is None:
        return "No verified exclusions list is recorded for this option."
    return f"{facts.notable_exclusion_count} notable exclusions are recorded."


def build_policy_sections(facts: HealthFacts) -> list[PolicySectionView]:
    """The policy sections for one product, stated from its recorded facts."""
    statements = fact_statements(facts)
    sections: list[PolicySectionView] = []

    for key, label, section_factors in SECTION_DEFINITIONS:
        entries = [
            PolicyFactView(
                key=factor,
                label=FACTOR_LABELS.get(factor, factor),
                value=statements[factor],
                example=FACTOR_EXAMPLES.get(factor),
                has_source=False,
                source_note=SYNTHETIC_SOURCE_NOTE,
            )
            for factor in section_factors
            if factor in statements
        ]
        if entries:
            sections.append(PolicySectionView(key=key, label=label, facts=tuple(entries)))

    return sections
