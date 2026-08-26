"""Versioned scoring configuration.

docs/06_RECOMMENDATION_ENGINE.md section 6 is blunt about what these numbers
are and are not:

> Do not invent domain authority by assigning unexplained permanent weights.
> These numbers are product-test parameters, **not insurance truth**.
> They must be validated through user testing and expert review before
> broader use.

So they live in one versioned object rather than being spread through the
evaluators, and the version is persisted on every run. Changing a number means
a new version; it does not mean rewriting what past runs said
(CLAUDE.md rule 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

#: How strongly a dimension counts for this reader.
#:
#: MUST_HAVE exists because section 6 names it. Nothing produces it yet: the
#: health questionnaire asks for up to three priorities and has no way to say
#: "this one is non-negotiable". Rather than invent that product decision, the
#: level is defined, unreachable, and raised in docs/SPEC_ISSUES.md.
PriorityLevel = Literal["BASELINE", "TOP", "MUST_HAVE"]

BASELINE: PriorityLevel = "BASELINE"
TOP: PriorityLevel = "TOP"
MUST_HAVE: PriorityLevel = "MUST_HAVE"


@dataclass(frozen=True)
class ScoringConfig:
    """One frozen set of matching parameters."""

    version: str
    base_weight: float
    top_priority_multiplier: float
    must_have_multiplier: float
    #: What to do when a product's critical matching data is missing or stale.
    #: docs/06_RECOMMENDATION_ENGINE.md section 8 allows either excluding the
    #: product or marking it unavailable "according to configured rule".
    #: docs/13_DECISIONS_AND_OPEN_ITEMS.md already decided: excluded.
    unknown_critical_rule: Literal["EXCLUDE", "MARK_UNAVAILABLE"] = "EXCLUDE"

    def weight_for(self, level: PriorityLevel) -> float:
        if level == MUST_HAVE:
            return self.base_weight * self.must_have_multiplier
        if level == TOP:
            return self.base_weight * self.top_priority_multiplier
        return self.base_weight


#: The prototype configuration, with the values named in
#: docs/06_RECOMMENDATION_ENGINE.md section 6's example.
HEALTH_BETA_001 = ScoringConfig(
    version="health-beta-001",
    base_weight=1.0,
    top_priority_multiplier=3.0,
    must_have_multiplier=5.0,
)

SCORING_VERSION = HEALTH_BETA_001.version

#: Bumped whenever the wording the engine generates changes, so a stored run
#: records which phrasing its reader actually saw. No LLM is involved yet:
#: docs/11_BUILD_PLAN.md Phase 9 says "Add AI explanation only after
#: structured output is correct".
EXPLANATION_VERSION = "deterministic-001"
