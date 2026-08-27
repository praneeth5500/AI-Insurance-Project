# Phase 14 — Claims Readiness

## What this phase changed

A reader can turn their decoded policy into a checklist: what their own
document asks of them at claim time, what insurers generally want, and what
only their insurer can answer.

`docs/01_PRODUCT_SPEC.md` section 3.6 draws the boundary in one sentence —
*it does not predict guaranteed claim approval* — and that is the constraint
every decision below serves.

## The three groups, and why they are three

`docs/07_POLICY_DECODER_AI.md` section 10 permits checklist items from exactly
three sources and says: **do not blend them.**

| Group | Comes from | Carries a citation |
|---|---|---|
| Your policy asks for this | clauses in the reader's own document | always |
| Generally worth having | approved templates, identical for everyone | never |
| Ask your insurer | nothing — these are questions | never |

Blending is not a presentation slip, it is a factual error in both directions:
a general suggestion shown as a policy requirement is an **invented policy
term**, and an unknown shown as a suggestion **hides that we do not know**.

So the separation is structural rather than a label on a flat list:

* `origin` is a column, and `source_clause_id` is set only on the first group —
  a test asserts every policy-specific item has a clause and no other item has
  one;
* the API returns three *groups*, not one list with a field. A flat list
  invites one careless `.map()` in a client and the distinction is gone;
* each group states what it is, and the general one states what it is **not**:
  "Not from your policy — these are things insurers commonly ask for. Your
  policy may not require them, and it may require things not listed here."

## Decisions and why

### An empty group beats a plausible one

If the document says nothing about claims, the policy-specific group is
absent. That tells the reader something true and actionable about their own
policy. Filling it with likely-sounding requirements would be the exact
invention the separation exists to prevent.

### Requirements are read narrowly

Only clauses already filed under "At Claim Time" are considered, and only a
short list of markers — intimation, documents, originals, pre-authorisation,
cashless — counts. A clause that merely mentions claims is not a requirement.
A false positive here is an obligation the reader does not actually have.

### The templates are procedural, never predictive

Nothing in the general group says a claim will be paid, or is more likely to
be, if the reader does these things. "Do this and you'll be fine" is a claim
prediction wearing a checklist, and a test greps the templates for exactly
that vocabulary.

### The checklist is built once and kept

Ticking things off is the point. Regenerating on each visit would throw that
away, so the session and its items persist and only the completion state
moves.

## A defect this phase caught

The checkbox did not move until the server replied. Browser verification
caught it as "clicking the checkbox did not change its state" — Playwright
asserting what a person would also notice.

It matters more here than in most places: someone working through this list is
plausibly standing at a hospital admission desk on a bad connection. The tick
is now applied immediately, reconciled with the server's response, and **rolled
back with a visible message if the save fails** — an optimistic update that
silently diverges from the server would be worse than a slow one.

## Verification

Backend: 15 new tests (373 total) — the three groups kept apart, every
policy-specific item carrying its clause and no other item carrying one, a
claims-silent policy producing no invented requirements, no outcome prediction
anywhere including in the templates themselves, ticking persisting, notes
bounded, and an item id from another user's checklist refused.

Frontend: 9 new tests (220 total), including the optimistic tick and its
rollback.

Browser: 14 checks against the real stack. A policy with a claims section
uploaded through the UI, processed by the worker, decoded, then its checklist
opened: three separate sections, 5 of 5 policy-read items citing their wording
and neither other group citing anything, the claims clause shown verbatim, and
a tick surviving a reload.

## Open questions

1. **The requirement markers are keyword-based.** They find what they find. A
   policy phrasing its notification requirement unusually will produce no
   policy-specific item — which the empty group states honestly, but the
   reader is not told *why* it is empty.
2. **The general templates are unreviewed.** They are written to be cautious
   and procedural, but nobody with claims experience has read them. They
   should be reviewed before real users see them.
3. **No reminder or expiry.** A checklist prepared today is still there in two
   years with a stale network-hospital note. Out of scope, worth knowing.

## Definition of done

| Item | Status |
|---|---|
| Claims clause extraction | ✅ narrow, from At Claim Time clauses only |
| Checklist | ✅ three groups, never blended |
| Source links | ✅ on every policy-read item, and only those |
| Mark complete | ✅ optimistic, persisted, rolled back on failure |
| No claim-approval prediction | ✅ stated on the page and enforced by tests |
