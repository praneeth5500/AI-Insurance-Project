"""The fit dimensions the engine reasons about.

These were in the product catalogue while the catalogue was the only thing
that had an opinion about fit. They belong here now: a factor is a matching
concept, and the catalogue's job is to state facts, not to judge them.

docs/01_PRODUCT_SPEC.md section 2.6 fixes the visible list, and
docs/06_RECOMMENDATION_ENGINE.md section 5 adds "show the ones that
meaningfully affect the user's decision" — which is why the order here is the
order a reader meets them, not alphabetical.
"""

from __future__ import annotations

from typing import Literal

#: docs/01_PRODUCT_SPEC.md section 2.6. UNVERIFIED renders as "Not enough
#: verified data" and is a real outcome, not a placeholder.
FitLabel = Literal["STRONG", "GOOD", "TRADE_OFF", "NEEDS_ATTENTION", "UNVERIFIED"]

COVERAGE = "coverage"
COPAY = "copay"
WAITING_PERIODS = "waiting_periods"
HOSPITAL_FLEXIBILITY = "hospital_flexibility"
NETWORK = "network"
SUBLIMITS = "sublimits"
EXCLUSIONS = "exclusions"
BUDGET = "budget"

#: Presentation order and copy.
FACTOR_LABELS: dict[str, str] = {
    COVERAGE: "Coverage",
    COPAY: "Co-pay",
    WAITING_PERIODS: "Waiting periods",
    HOSPITAL_FLEXIBILITY: "Hospital flexibility",
    NETWORK: "Network usefulness",
    SUBLIMITS: "Sub-limits",
    EXCLUSIONS: "Exclusions and conditions",
    BUDGET: "Budget",
}

FACTOR_ORDER: tuple[str, ...] = tuple(FACTOR_LABELS)

#: Which questionnaire priority refers to which dimension.
#: docs/01_PRODUCT_SPEC.md section 2.3 priorities -> section 2.6 dimensions.
PRIORITY_TO_FACTOR: dict[str, str] = {
    "lower_premium": BUDGET,
    "low_copay": COPAY,
    "short_waiting_periods": WAITING_PERIODS,
    "hospital_flexibility": HOSPITAL_FLEXIBILITY,
    "broad_coverage": COVERAGE,
    "fewer_sublimits": SUBLIMITS,
}
