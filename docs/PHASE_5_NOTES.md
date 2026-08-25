# Phase 5 — Mock Recommendation Experience

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 5.

## Definition of done

Phase 5 has **no "Done when" section** — the third phase in a row (issues 11
and 15 in `docs/SPEC_ISSUES.md`). Held to the build list plus `CLAUDE.md`'s
definition of done:

| Requirement | Status | Evidence |
|---|---|---|
| Use synthetic products | ✅ | 10 fictional products, `SYNTHETIC` provenance, labelled on every card |
| What we learned | ✅ | A synthesis built deterministically from stored answers |
| 5 primary matched options | ✅ | Verified in the browser |
| See 5 more | ✅ | Reveals the remaining 5 |
| Category fit | ✅ | 8 dimensions, five labels, stated in words |
| Watch-out | ✅ | Exactly one on every card, never collapsed |
| Priority editor | ✅ | Re-picks priorities, server reorders, change explained |
| Comparison select | ✅ | Up to 3, tray, removable |
| Types / tests / mobile / a11y | ✅ | 134 backend, 144 frontend, 28 browser checks |

## The honesty problem this phase creates, and how it was handled

Phase 5 asks for a recommendation experience *before* the recommendation
engine exists. That is the most dangerous thing this product could ship
carelessly: a screen that looks like advice but is not.

Five constraints, each enforced by a test:

1. **Every product is obviously fictional.** Every insurer name ends in
   "(demo)". A screenshot of this build cannot be mistaken for a real
   comparison.
2. **No premium anywhere.** `CLAUDE.md` is unconditional. The catalogue has no
   price field, and `PriceDisplay` renders "No price available — these are
   demo products… Real prices come from the insurer, never from us." A test
   asserts no product prose contains a digit or a currency symbol.
3. **The screen says what it is.** A persistent notice: *"These options are
   invented for testing this screen. The insurers and products are not real,
   no prices are shown, and nothing here is a recommendation to buy."*
4. **No overall score.** No 0–100 number exists, and the ordering's internal
   value never leaves the server. A test asserts the API response contains no
   "score", "rank", "rating" or "relevance".
5. **The ordering is labelled as a prototype**, not an engine. The run records
   `scoringVersion: "prototype-ordering-001"` and `catalogueVersion`, so any
   result set can be explained by what produced it.

## Decisions taken

### The ordering is deliberately crude, and deliberately deterministic

`docs/06_RECOMMENDATION_ENGINE.md` describes hard eligibility, fit evaluators
and versioned weighting — all Phase 9. What Phase 5 has is the smallest thing
that lets the UX be reviewed: a sum over the priorities the user actually
chose, using the authored fit labels, tie-broken by product id.

Two properties are real and Phase 9 inherits them:

* **Determinism.** Same answers, same order, every time — including after a
  reload, which the browser check confirms.
* **Unknown is never average.** `UNVERIFIED` ranks with `NEEDS_ATTENTION`, not
  in the middle (`docs/06_RECOMMENDATION_ENGINE.md` section 8).

No LLM participates at any point.

### The fit labels are authored content, not computed judgements

Each demo product carries a hand-written fit label and note per dimension.
They are fixture data for a demo, which is why they are not stored as
`fit_components` rows: that table is for the evidence a real evaluator
produces, and filling it with authored prose would misrepresent what it holds.
They live in `reason_summary_json` until Phase 9.

### "What we learned about you" is templated, not generated

`docs/01_PRODUCT_SPEC.md` section 2.5 asks for "a synthesis, not a raw form
dump". It is built deterministically from the stored answers — every line
derives from something the person actually answered, a missing answer produces
no line, and nothing is inferred.

Deliberately not an LLM: `docs/11_BUILD_PLAN.md` Phase 9 says AI explanation
comes only after the structured output is correct, and a hallucinated detail
about someone's *own answers* would damage trust faster than anything else on
the screen. The health-condition line, when it appears, restates only that one
exists — never what it is.

### The priority editor keeps the top-3 model

`docs/02_UX_UI_SPEC.md` section 9 also suggests a four-level control (Less
important / Normal / More important / Must have). That maps onto weights, and
weights belong in the versioned scoring configuration that arrives in Phase 9.
Phase 5 keeps onboarding's "choose up to 3", re-runs the ordering server-side,
and reports what moved — the section's actual requirement, that a changed
priority *visibly explains why results changed*. Raw weights are never
exposed; a test asserts it.

### Two card actions are not offered, because they do not exist

The card contract lists Compare and View details. **Compare selection works**
(it is in this phase's build list) — up to 3, with a tray. The side-by-side
view is Phase 6 and the detail screen is Phase 7, so those read "Side-by-side
comparison is being built" and "Full details coming soon" rather than linking
nowhere. A test asserts the card renders no links at all.

### "Find my matches" is now honest

Phase 4 shipped the review button as "Save my answers" because matching did
not exist. It now produces a match set, so the specification's wording from
section 2.4 is live, and submitting takes the user straight to the results.

### The run is persisted; immutability waits for Phase 9

Runs and candidates are stored so a result set has a stable URL and can appear
on the home screen. `docs/06_RECOMMENDATION_ENGINE.md` section 11 freezes a
*completed* run; a Phase 5 run is an exploratory draft that the priority editor
reorders in place, which section 10 explicitly permits.

## Corrections made during verification

Five browser checks failed on the first run. Four were **my checks being
wrong**: `textContent` includes Next.js's serialised RSC payload inside
`<script>` tags, so option values, help text and framework CSS looked like
visible page content. Switched to `innerText`.

The fifth was **real**: the "Back to home" link was a 17px tap target, below
the 44px minimum, on both the results and review screens. Fixed.

## Open questions for the founder

1. **Should demo products carry a labelled synthetic price?** Right now they
   carry none, because `CLAUDE.md` forbids inventing a premium — but that
   leaves the price component barely exercised, and price is a large part of
   how people read a results screen. A clearly-labelled synthetic indicative
   figure would let you test that. Your call; I did not want to make it.
2. **Are the fit labels plausible enough to test with?** They are invented to
   exercise the UI. If any read as misleading rather than obviously fictional,
   say so and I will flatten them further.
3. **The four-level priority control** (section 9) is not built — see above.
   Confirm the top-3 model is fine until Phase 9, or say if you want the finer
   control sooner.
4. Still open from earlier phases: question wording (open item 6), session
   lifetimes, how invites are issued, the unthrottled magic-link endpoint,
   `/design-system` being public, and analytics timing (issue 12).

## Deliberately not done

| Not built | Why |
|---|---|
| Side-by-side comparison | Phase 6. Selection is built; the view is not. |
| Product detail screen | Phase 7. |
| Real product data, versioning, provenance pipeline | Phase 8. |
| Hard eligibility, fit evaluators, scoring versions, immutable runs, `fit_components` | Phase 9. |
| AI explanation of a match | Phase 9, and only after the structured output is correct. |
| Analytics (`recommendation_generated`, `match_opened`, `priority_changed`) | Phase 15, per issue 12. |

## Verification performed

134 backend tests, 144 frontend tests, and **28 browser checks** in Chromium
driving the flow from sign-in through the questionnaire to results:

- submitting the review lands on the results screen;
- the screen is labelled as demo content and no price is invented;
- "What we learned about you" comes first, reflects the answers given, and is
  not a form dump;
- five options, each with a watch-out; "see 5 more" reveals the rest;
- no overall score and no unsupported claim anywhere;
- "Why this matches" expands the full category fit, stated in words;
- comparison caps at three, the fourth is disabled, the view is not offered;
- a priority change reorders, explains what moved, marks the moved options,
  loses nothing and exposes no weights;
- the same run renders the same order after a reload;
- 375×812: no horizontal scroll, every control ≥44px, skip link first.

## Next phase

Phase 6 — Comparison: compare 2 and 3, biggest differences first, then the
user's priorities, then all details, with a stacked layout on mobile.
