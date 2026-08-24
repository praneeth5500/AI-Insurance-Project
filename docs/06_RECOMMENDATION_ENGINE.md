# Recommendation Engine Specification

## 1. Purpose

The recommendation engine is a **prototype decision-support matcher**.

It is not an actuarial model.
It is not a medical diagnosis system.
It is not an LLM ranking system.

The goal is:

> Given structured user requirements and structured insurance-product facts, identify eligible options and explain meaningful fit/trade-offs.

---

# 2. Core architecture

```text
User facts
+
User priorities
+
Verified product facts
↓
Hard eligibility
↓
Fit evaluators
↓
Priority weighting
↓
Internal relevance value
↓
Matched option set
↓
Plain-language explanation
```

The LLM only participates after structured matching.

---

# 3. Data modes

Every product record must be labeled:

```text
SYNTHETIC
MANUALLY_VERIFIED
PARTNER_API
```

### Synthetic

Safe for:

- frontend development;
- demo;
- recommendation-engine tests;
- user-flow testing if clearly labeled.

### Manually verified

Can be used in controlled beta only if the product facts were checked against source documents and versioned.

### Partner API

Preferred later for current catalogue/quotes.

---

# 4. Hard eligibility

Rule behavior:

### Hard failure

Normally remove the product.

Examples:

- age outside supported eligibility;
- required family composition unsupported;
- product inactive;
- critical matching data unavailable/stale;
- required cover type unsupported.

### Preference mismatch

Do not remove.

Lower the relevant fit.

Examples:

- higher co-pay than desired;
- longer waiting period;
- budget above preference;
- less flexible room rule.

---

# 5. Health fit dimensions

Engine may evaluate:

- eligibility;
- coverage adequacy;
- co-pay;
- deductible;
- waiting periods;
- room/hospital flexibility;
- hospital network usefulness;
- disease/treatment sub-limits;
- important exclusions;
- restoration/refill;
- pre/post hospitalization;
- modern/day-care treatment where relevant;
- renewal/no-claim features where relevant;
- premium/budget;
- explicit user priorities.

Do not show all dimensions by default.

Show the ones that meaningfully affect the user's decision.

---

# 6. Prototype weighting strategy

Do not invent domain authority by assigning unexplained permanent weights.

For beta prototype:

1. hard constraints are pass/fail;
2. user's chosen Top 3 priorities receive stronger weight;
3. other verified fit dimensions receive baseline weight;
4. all weights live in versioned configuration;
5. changes require a new scoring version.

Example prototype configuration concept:

```json
{
  "version": "health-beta-001",
  "base_weight": 1.0,
  "top_priority_multiplier": 3.0,
  "must_have_multiplier": 5.0
}
```

These numbers are product-test parameters, **not insurance truth**.

They must be validated through user testing and expert review before broader use.

---

# 7. Normalized fit

Internal evaluator output:

```ts
type FitResult = {
  factorKey: string;
  eligible: boolean | null;
  normalizedScore: number | null; // 0..1 internal
  label:
    | "STRONG"
    | "GOOD"
    | "TRADE_OFF"
    | "NEEDS_ATTENTION"
    | "UNVERIFIED";
  explanationEvidence: Evidence[];
};
```

Consumer UI does not expose the raw normalized score.

---

# 8. Internal relevance

Possible prototype formula:

```text
sum(factor_score × factor_weight)
/
sum(applicable_factor_weights)
```

Only use factors with verified data.

If a critical factor is unknown:

- exclude product from new matching, or
- mark unavailable according to configured rule.

Never convert unknown into a neutral score silently.

---

# 9. Result presentation

Prototype UX target:

- 5 primary matched options
- see 5 more
- category fit
- no visible overall numeric score

Recommended wording:

> Policy X matches several of the priorities you selected.

Avoid:

> Policy X is objectively the best policy.

---

# 10. User priority changes

When user changes priority:

```text
Update structured priority
↓
Re-run deterministic matching
↓
Persist new or updated draft calculation
↓
UI reorders
↓
AI may explain what changed
```

Do not ask AI to "rethink" ranking.

---

# 11. Historical integrity

A completed recommendation run is immutable.

Persist:

- answers;
- priorities;
- questionnaire version;
- scoring version;
- product versions;
- price state;
- fit components;
- internal ordering;
- explanation version;
- timestamp.

If product data changes:

create a new run.

---

# 12. Motor engine

Architecture should support motor factors but implementation can follow health.

Candidate motor factors:

- cover structure;
- IDV adequacy;
- deductible;
- own-damage cover;
- relevant add-ons;
- garage-network usefulness;
- premium for equivalent protection;
- NCB;
- service/claims information when reliable;
- vehicle age;
- vehicle use;
- city/risk context.

Do not use vague claim-settlement metrics without a clearly comparable, sourced definition.
