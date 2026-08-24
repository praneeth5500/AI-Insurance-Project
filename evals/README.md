# Evals

Empty until Phase 9.

This directory will hold the evaluation assets from
`docs/10_TESTING_AND_EVALS.md`:

- **Recommendation personas** (section 3) — synthetic user profiles with the
  expected structured outcome: which products are excluded by hard eligibility,
  which are penalised, and how a priority change must reorder results.
  Determinism is the property under test: identical structured input must
  produce an identical structured result, and an LLM outage must not change a
  score.
- **Policy decoder golden set** (section 4) — manually verified policies with
  expected clause, expected fact, expected page and allowed variants.
- **Q&A evals** (section 5) — simple factual, multi-clause, ambiguous, missing
  information, adversarial, misleading premise, claim-guarantee requests and
  medical/legal overreach. Expected behaviour includes *refusing* to conclude.

Fixtures must be synthetic or explicitly licensed. Do not commit a real
customer policy document.
