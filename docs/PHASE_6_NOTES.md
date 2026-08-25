# Phase 6 — Comparison

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 6.

## Definition of done

Phase 6 has **no "Done when" section** — the fourth in a row (issues 11, 15,
16 in `docs/SPEC_ISSUES.md`). Held to the build list plus `CLAUDE.md`'s
definition of done:

| Requirement | Status | Evidence |
|---|---|---|
| Compare 2 | ✅ | Verified in the browser |
| Compare 3 | ✅ | Verified in the browser; a fourth stays blocked |
| Biggest differences | ✅ | Ranked by how far apart the labels are, capped at 4 |
| User-priority sorting | ✅ | A priority breaks ties, and gets its own section |
| Mobile stacked layout | ✅ | One column at 375px, confirmed from computed style |
| Types / tests / a11y | ✅ | 152 backend, 159 frontend, 21 browser checks |

## Decisions taken

### The section order is the design

`docs/02_UX_UI_SPEC.md` section 10 is unusually prescriptive: **Biggest
differences → Your priorities → All details**. That order is what stops a
comparison becoming the "giant feature matrix" the same section warns against.
Leading with what actually separates the options is the difference between a
comparison that helps and a spreadsheet that doesn't.

"All details" sits behind a disclosure for the same reason. It is available in
full — nothing is hidden — but it does not greet the reader as a wall of cells.

### Difference size decides the order, and never appears on screen

Dimensions are ranked by how far apart their fit labels are, with a dimension
the user said mattered breaking ties (`docs/01_PRODUCT_SPEC.md` section 2.7
puts priorities second after the differences themselves). Catalogue order
breaks remaining ties, so the result is stable between requests.

The numeric spread that produces that order is **never serialised**. A
"difference size" on screen would be a score by another name, and
`docs/01_PRODUCT_SPEC.md` section 2.5 rules scores out. A test asserts the
response contains no "spread", "score", "rank", "rating", "winner" or
"better".

### Priorities are shown even when the options agree

"All three are strong here" is a real answer to "does my priority separate
these?". Hiding matching dimensions would leave the reader wondering whether
the product had simply failed to check.

### Unknown data counts as a real difference

`UNVERIFIED` sits below `NEEDS_ATTENTION` rather than mid-scale, so an option
with unrecorded data reads as a genuine gap between the options rather than
being quietly averaged away — `docs/06_RECOMMENDATION_ENGINE.md` section 8,
and `docs/12_BETA_CHECKLIST.md`'s "Unknown critical data is not hidden".

### The 2–3 limit is enforced by the API, not the UI

The checkboxes disable at three and the action stays inert below two, but the
server rejects anything outside 2–3 independently, deduplicating first so
`[a, a]` cannot pass as two. `docs/12_BETA_CHECKLIST.md` lists "Compare max 3"
as a release-blocking property, and a client is not the place to guarantee
one. A browser check calls the endpoint directly with four options and
confirms a 422.

An option that is not part of the run is rejected too — otherwise a crafted
request could pull arbitrary products into someone's comparison.

### One layout, not two

`docs/01_PRODUCT_SPEC.md` section 2.7 requires stacked differences on mobile
rather than a wide horizontal table. Rather than maintaining two layouts, each
dimension renders as a stack of option entries that widens into columns from
`sm`. Every entry repeats its option's name, so the reader never has to
remember which column is which — the exact failure mode of a feature matrix.

### The comparison lives in the URL

`/app/recommendations/{runId}/compare?options=a,b` — so it survives a reload,
can be shared, and the back button works. The comparison itself is still
computed by the API (`POST /api/v1/comparisons`, per
`docs/08_API_CONTRACTS.md` section 6); only the selection is in the URL.

A URL with fewer than two options redirects back to the results rather than
rendering an error, since that is a navigation mistake rather than a failure.

### Nothing declares a winner

There is no total, no ranking within the comparison, and no "best". The header
says so explicitly: *"There is no overall winner here — each option trades
something off."* Tests assert the absence of winner/recommend/should-choose
wording.

## Corrections during verification

Three items, all caught before commit:

1. **The fit badge stretched to full width** inside the comparison's column
   layout — it read as a filled bar rather than a chip. Added `w-fit` and
   `self-start`. Visible in the first desktop screenshot; fixed and re-checked.
2. **A check of mine was too blunt** again: it flagged "winner" without
   noticing the page only ever says "no overall winner". Made the assertion
   precise rather than loosening it.
3. **A harness bug**: I extracted the run id from the wrong URL segment, so
   the mobile check loaded a comparison for a non-existent run and reported a
   layout failure that did not exist.

## Deliberately not done

| Not built | Why |
|---|---|
| Product detail links from the comparison | Phase 7 builds that screen. |
| Real product data | Phase 8. |
| `comparisons` persistence | `docs/08_API_CONTRACTS.md` defines the endpoint but `docs/05_DATA_MODEL.md` defines no table, and a comparison is derived from a run plus a selection — both already stored. Recorded in `docs/SPEC_ISSUES.md`. |
| `compare_added` / `comparison_viewed` analytics | Phase 15, per issue 12. |

## Open questions for the founder

1. **Four differences is my choice, not the specification's.** Enough to be
   useful, few enough not to be a matrix. Say if you want more or fewer.
2. **Should the comparison be limited to options from one run?** It is today,
   which keeps "compare what you were shown" honest — but it means a user
   cannot compare across two sessions. Probably right for the beta; flagging
   it because it is a product boundary rather than a technical one.
3. Still open from earlier phases: synthetic prices on demo products,
   question wording (open item 6), session lifetimes, invite issuance, the
   unthrottled magic-link endpoint, `/design-system` being public, and
   analytics timing (issue 12).

## Verification performed

152 backend tests, 159 frontend tests, and **21 browser checks** in Chromium:

- one option is not enough; two enable the comparison; a fourth stays blocked;
- the comparison has a shareable URL and the back link returns to the results;
- sections appear in the specified order; the screen is labelled as demo;
- no winner, no score, priorities marked, every option's watch-out shown;
- all details hidden until requested, then complete;
- three options lay out as three columns from `sm`;
- **the API rejects four options even when called directly**;
- a one-option URL redirects rather than erroring;
- 375×812: no horizontal scroll, differences confirmed to compute to a single
  column, every control ≥44px.

## Next phase

Phase 7 — Product Detail: fit summary, why match, watch-outs, policy sections,
examples, source links, save and a contextual CTA, still on fixture data.
