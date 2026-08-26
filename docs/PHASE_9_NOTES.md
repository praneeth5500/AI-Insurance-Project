# Phase 9 — Matching Engine

## What this phase changed

Before Phase 9 the "recommendation" was an ordering over hand-written labels.
Every demo product carried an authored judgement — `copay: STRONG` — and the
ordering counted how many of those judgements lined up with the reader's
priorities. It was honest about being a prototype, and it was labelled as such
everywhere, but it was not an engine: nothing was evaluated, and the same
product told every reader the same thing.

Phase 9 replaces that with the pipeline `docs/06_RECOMMENDATION_ENGINE.md`
section 2 describes:

```text
user facts + priorities + product facts
  -> hard eligibility
  -> fit evaluators
  -> priority weighting
  -> internal relevance value
  -> matched option set
```

The visible consequence is that a match is now *about the reader*. A 10%
co-pay is a trade-off for someone who said they would rather not share a
claim, and unremarkable for someone who said a small share is fine. The same
product legitimately gets different labels for different people.

## The pieces

| Concern | Where |
|---|---|
| Structured product facts | `backend/app/products/facts.py` |
| Fit dimensions | `backend/app/matching/factors.py` |
| The reader, typed | `backend/app/matching/profile.py` |
| Hard eligibility | `backend/app/matching/eligibility.py` |
| Fit evaluators | `backend/app/matching/evaluators.py` |
| Versioned weighting | `backend/app/matching/weights.py` |
| Explanation evidence | `backend/app/matching/evidence.py` |
| The pipeline | `backend/app/matching/engine.py` |
| Persistence and the API boundary | `backend/app/recommendations/` |

## Decisions and why

### The synthetic catalogue now states facts, not opinions

`backend/app/products/catalogue.py` holds entry ages, supported family
compositions, sum insured options, co-pay percentages, waiting periods in
months, room rules, network sizes, sub-limit counts and exclusion counts.
Everything there is still invented and still labelled `SYNTHETIC`; every
insurer name still ends in "(demo)". What changed is that the invented data is
now the *kind* of thing a real policy has, so the evaluators exercise the same
code path they will over verified data.

There is still no premium anywhere. That is not an oversight — see below.

### Unknown is never average

`docs/06_RECOMMENDATION_ENGINE.md` section 8: *never convert unknown into a
neutral score silently.* Every evaluator returns `UNVERIFIED` with a
`DATA_GAP` evidence entry and a null score when the fact it needs is missing,
and a null score is excluded from **both halves** of the relevance fraction.
Scoring it 0 would punish a product for our missing data; scoring it 0.5 would
invent a judgement.

One demo product (`sp_lantern_starter`) has its exclusions count deliberately
absent so this path is always live on screen.

### The budget dimension reports a gap, for everyone

No product has a price: the synthetic catalogue has none and no partner is
integrated. So budget evaluates to "not enough verified data" for every reader,
however much budget they gave, and drops out of the weighting. The branch that
compares a real annual price against a stated budget is written and tested —
`backend/app/recommendations/pricing_lookup.py` finds one if it exists, through
the Phase 8 price-state rules — it simply has nothing to read.

### Hard failure versus preference mismatch

Section 4 draws a line this build now holds:

* **Hard failure removes the product.** Age outside the entry range, an
  unsupported family composition, more children than the policy covers,
  unreadable facts, missing or stale critical data, or no verified fit data at
  all.
* **A preference mismatch does not.** A higher co-pay than someone wanted, a
  longer wait, a capped room — these lower the fit and are explained.

For the fixture persona (34, insuring only themselves) two of the ten demo
products are excluded: one that can only be bought for a family, and one that
starts at age 55. The results screen says so — the count and the *rules*, never
the products, because an excluded product was not assessed for fit and naming
it would imply a judgement we did not make.

### Runs are immutable

`CLAUDE.md` rule 10 and section 11. Changing a priority now creates a **new**
run with `previous_run_id` pointing at the old one; the results screen moves
the URL to it. The earlier run keeps its own candidates, its own priorities and
its own recorded fit. A mapper-level guard raises `ImmutableRunError` if
anything tries to edit a stored candidate, run or fit component in place — an
application-level guarantee, not a database one, but it catches the realistic
mistake, which is code that loads a result and adjusts it.

Because a run is immutable, the product detail page now reads its fit *from the
run* the reader arrived from rather than recomputing it. A card and the page
behind it cannot disagree, and reopening an old result set shows what it said
at the time.

### Evidence

Every fit judgement carries the product facts, the reader's answers, the
threshold rule and any data gaps that produced it, persisted in
`fit_components.evidence_json`. This is what makes the AI explanation safe when
it arrives: the model will be handed these objects, not the product, so it
cannot introduce a fact that is not there. `docs/11_BUILD_PLAN.md` is explicit
that AI explanation comes *after* the structured output is correct, and no
model participates in this phase.

## What a reader sees that is new

* Options they cannot buy are no longer shown. Fewer than ten options is now
  normal, and the screen says how many were not a match and under which rules.
* An empty result set has its own state, which says the small demo catalogue is
  the limit rather than implying nothing exists.
* The product detail page states the policy's facts ("A 20% co-pay applies to
  each claim", "Existing conditions are covered after 24 months") instead of
  repeating the fit note.
* Opened outside a set of matches, the detail page says there is no personal
  assessment rather than showing a fit that belongs to nobody.

## Verification

Backend: 249 tests (37 new in `tests/test_matching.py`), including the two
personas from `docs/10_TESTING_AND_EVALS.md` section 3 and its four required
properties — same input/same result, no LLM in the path, stale critical data
excludes, unknown never treated as average.

Browser: 22 checks in real Chromium against the running app, driving the whole
flow from sign-in through the questionnaire to results, a priority change, both
product-detail modes, and mobile/desktop layout and keyboard basics.

## Open questions

New this phase, all recorded in `docs/SPEC_ISSUES.md` as issues 21–24:

1. **`MUST_HAVE` weighting is unreachable.** The specification names it; the
   questionnaire has no way to mark a priority non-negotiable. Defined,
   unused, and covered by a test that fails the day that changes.
2. **The weighting numbers are unvalidated.** 1.0 / 3.0 / 5.0 come from the
   specification's own example and it says outright they need user testing and
   expert review. A visible consequence: the option strongest on the reader's
   top priority is not always first.
3. **Every fit threshold is authored.** How many months is a "short" wait, how
   many hospitals is a "wide" network. Consistent and recorded as evidence, but
   not sourced. These should not be shown over verified products without expert
   review.
4. **No children's age rule.** The questionnaire does not ask, so family
   eligibility checks the adults and the child count only.

Carried forward: the freshness windows, `verified_by`, and everything listed in
`docs/PHASE_8_NOTES.md` that has not been answered.

## Definition of done

| Item | Status |
|---|---|
| Hard eligibility | ✅ |
| Fit evaluators | ✅ (8 dimensions) |
| Priority weighting | ✅ versioned configuration |
| Scoring version | ✅ `health-beta-001`, persisted per run |
| Immutable recommendation runs | ✅ new run per change, guard against edits |
| Explanation evidence object | ✅ persisted per fit component |
| Synthetic + manually verified fixtures | ✅ both reach the engine through one provider interface |
| AI explanation | Deliberately not started — Phase 9 says "only after structured output is correct" |
