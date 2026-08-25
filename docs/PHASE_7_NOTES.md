# Phase 7 — Product Detail

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 7.

## Definition of done

Phase 7 has **no "Done when" section** — the fifth in a row (issues 11, 15, 16
in `docs/SPEC_ISSUES.md`). Held to the build list plus `CLAUDE.md`'s
definition of done:

| Requirement | Status | Evidence |
|---|---|---|
| Fit summary | ✅ | Full category fit, plus 3 highlights in the hero |
| Why match | ✅ | Leads the page, ordered by the reader's own priorities |
| Watch-outs | ✅ | Beside the strengths, not below the fold |
| Policy sections | ✅ | All eight from `docs/01_PRODUCT_SPEC.md` §2.8 |
| Examples | ✅ | Per fact, labelled as examples every time |
| Source links | ✅ | Present on every fact, and honest that none exists |
| Save | ✅ | Persists, survives reload, private per user |
| Contextual CTA | ✅ | "Compare this policy". No checkout. |
| Types / tests / mobile / a11y | ✅ | 172 backend, 177 frontend, 26 browser checks |

## The two rules that shaped this screen

### Never fabricate a source

`docs/10_TESTING_AND_EVALS.md` section 8 lists a **fabricated source citation**
as release-blocking. Every synthetic fact therefore reports `hasSource: false`
and, when the reader opens "View source wording", says:

> **No source wording available.** This is a demo product, so there is no
> policy document to quote. Real products show the exact wording their facts
> come from.

The control is still rendered when there is nothing behind it. Hiding it would
hide the fact that nothing is verified — and that fact is exactly what a beta
tester needs to see.

### An example explains a mechanism; it never describes the product

`docs/12_BETA_CHECKLIST.md` requires examples to be clearly labelled as
examples. Each carries the heading *"Example — explains how this works, not
this policy's terms"* and is written hypothetically: *"If a policy has a 10%
co-pay and a bill comes to ₹1 lakh, you pay ₹10,000."*

That distinction is what makes the figures safe. A number inside a labelled
hypothetical teaches a mechanism; the same number attached to a product would
be an invented insurance fact. So the product facts themselves still carry no
figures, consistent with Phase 5, and a test asserts no `₹` appears in any
fact value.

## Decisions taken

### Sections are derived from the fit data, not authored twice

The eight sections in `docs/01_PRODUCT_SPEC.md` §2.8 are built by mapping the
fit dimensions the catalogue already holds. That keeps one source of truth: a
product cannot say one thing on its match card and something else on its
detail page. A test asserts every section value comes from a fit note.

### The trade-off sits beside the strengths

`docs/02_UX_UI_SPEC.md` §11 puts "1 trade-off" above the fold with the
highlights, and rule 4 says trust requires discussing disadvantages. "What to
watch out for" is therefore the second `h2` on the page, in a two-column block
with "Why this matches you" — not a footnote further down. A test asserts the
heading order.

### No checkout, and the page says so

`docs/01_PRODUCT_SPEC.md` §2.9 leaves outbound continuation disabled for the
early beta, and `docs/12_BETA_CHECKLIST.md` requires **no fake checkout**. The
primary action is "Compare this policy" (§11's evaluating-state CTA), and the
page states plainly:

> This beta doesn't sell insurance and doesn't pass your details to anyone.
> When you're ready, you would continue with the insurer directly.

A test asserts the absence of buy/quote/purchase/checkout/apply wording.

### The page is a real URL

`/app/products/{reference}` works standalone. `from` and `priorities` are
optional context from the results screen, so the detail page opens on the same
three strengths the card showed and can offer a way back — but without them
the page still renders, and simply omits the compare action rather than
linking nowhere.

### Saving is a row, not a copy

`saved_products` stores who saved what, and nothing else. Copying product
detail into it would let a saved option drift out of step with the catalogue.
Saving is idempotent server-side, so a double click cannot create two rows,
and a failed save returns the button to its previous state rather than
pretending it worked.

## Defect found while building

**The hero was not leading with the reader's priority.** `strongest_fits`
deliberately sorts so the factors a reader said mattered come first — and both
consumers then discarded that order by filtering the full fit list by
membership, which silently restored catalogue order. So a card could headline
a strength the reader never mentioned.

Present in Phase 5's match card too, and fixed in both.

Fixing it surfaced a second, smaller thing: among two equally strong
priorities, the tiebreak was alphabetical rather than the order the reader
ranked them in. `PriorityItem.rank_order` already preserves that order, so
`strongest_fits` now uses it. Choosing "fewer sub-limits" first now leads with
sub-limits, not co-pay.

## Deliberately not done

| Not built | Why |
|---|---|
| Outbound "Continue to insurer" link | `docs/01_PRODUCT_SPEC.md` §2.9 leaves it disabled for the early beta, and the learning loop must not depend on checkout. |
| A saved-options module on the home screen | `docs/01_PRODUCT_SPEC.md` §5 lists the home modules and saved products is not among them. Flagged below rather than invented. |
| Real source documents and verified facts | Phase 8 (product data) and Phases 10–13 (the decoder, which is where real source wording comes from). |
| `match_opened` analytics | Phase 15, per issue 12. |

## Open questions for the founder

1. **Should saved options appear on the home screen?** They persist and the
   detail page reflects them, but `docs/01_PRODUCT_SPEC.md` §5 does not list
   saved products among the returning-home modules, so I did not add one.
   Saving that the user cannot find again is half a feature.
2. **The examples are mine.** Eight of them, one per fit dimension, written to
   explain co-pay, sub-limits, waiting periods and so on. They are the most
   *educational* copy in the product so far and deserve your eye — especially
   whether the illustrative figures read clearly as hypothetical.
3. Still open: labelled synthetic prices on demo products (Phase 5), question
   wording (open item 6), session lifetimes, invite issuance, the unthrottled
   magic-link endpoint, `/design-system` being public, analytics timing
   (issue 12).

## Verification performed

172 backend tests, 177 frontend tests, and **26 browser checks** in Chromium,
all passing on the first run:

- match cards link through, carrying the reader's priorities;
- one `h1`; why-matches and the trade-off lead; compare is primary; save offered;
- all eight policy sections present;
- examples collapsed by default, then labelled as examples;
- source wording states plainly that none exists; provenance shows
  "Not verified — demo data";
- no checkout, no score, no unsupported claim;
- save → reload → still saved → unsave;
- the page works as a standalone URL, and an unknown option shows an error
  state rather than crashing;
- 375×812: no horizontal scroll, every control ≥44px, skip link first,
  highlights lead with the reader's first priority.

## Next phase

Phase 8 — Real Data Domain Layer: canonical product model, product versioning,
provenance, price state, a manual verified-data importer, and the partner
adapter interface.
