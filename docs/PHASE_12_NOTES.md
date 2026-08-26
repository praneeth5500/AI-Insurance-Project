# Phase 12 — Decoder UI

## What this phase changed

The facts Phase 11 extracted become a report a person can read. This is the
point in the product where a machine's reading of someone's policy is
presented back to them as fact, so most of the decisions below are about
making the report's limits as visible as its findings.

## Decisions and why

### The report opens with what it could *not* determine

Before any finding, the reader sees how many things we looked for and did not
find, how many points the policy states inconsistently, and how many sections
of their document this report does not cover at all. A decoder that leads with
its findings and buries its gaps reads as more complete than it is — and
someone deciding whether they are covered deserves the limits first.

### An unknown is a card, not an omission

`docs/12_BETA_CHECKLIST.md` requires a visible not-found state. A missing
waiting-period card would tell the reader their policy has no waiting period,
which is the opposite of what we know. So the card is rendered, says we could
not find it, says plainly that this does not mean it is absent — only that it
is not worded in a way we recognise — and still explains what the thing *is*,
with its example and its conditions. An unknown that teaches you what to look
for is worth more than a blank.

### A contradiction is shown, never resolved

When the policy states something twice with different answers, the card says
so, shows both readings with their page numbers, and states outright that we
have not picked one. `docs/07_POLICY_DECODER_AI.md` section 5 requires
conflicts to be highlighted; silently choosing a winner is precisely what that
rule exists to prevent.

### The technical term is kept

Section 6: explain technical language *without hiding the technical term*.
Every card carries both — "The share of each claim you pay" and "Co-payment".
A reader who learns the real term can use it on their insurer's website; one
given a friendlier invented word cannot.

### Ordinary confidence gets no badge

A HIGH-confidence fact is unbadged. Labelling the normal case "high
confidence" would turn the report into a set of scores rather than a reading
of a policy, and would make the genuinely uncertain cards harder to pick out.
No numeric confidence reaches the screen at all.

### The explanation layer is composed, never stored

`docs/07_POLICY_DECODER_AI.md` section 3: explanation must never become the
source of truth. The plain-language wording is authored once in
`app/decoder/content.py` and composed at render time from the fact and its
clause. It cannot vary between readers, drift between runs, or outlive the
fact it explains — because it is never written down against a policy.

### Examples are hypothetical, and labelled

The same rule the product detail screen follows. An example that used this
policy's own numbers would become an unverified claim about what the reader
will actually be paid.

### The report says whether a model was involved

"Read by: no AI model" is on the page, with the reader version beside it.
Today that is always true. When a model does participate, the same line will
say so — the reader should never have to wonder.

### Q&A's column is not reserved

`docs/02_UX_UI_SPEC.md` section 12 describes a 65/35 split with policy Q&A on
the right. Q&A is Phase 13. The report runs full width rather than holding
space for something that does not exist — `CLAUDE.md` rule 8.

## A defect this phase caught

The worker failed on its first real run with
`NoReferencedTableError: … 'uploaded_policies.user_id' could not find table
'users'`. A SQLAlchemy mapper is only configured once its module is imported;
the API got a complete registry for free because its routers pull in every
domain, but the worker imports only what it directly uses, and the failure
surfaced at runtime on the first query rather than at import.

Fixed structurally rather than by adding one import: `app/db/registry.py`
imports every model module, and the API, the worker and `migrations/env.py`
all use it. There is now one list to keep current instead of three, and the
next model cannot half-exist in one process.

## Verification

Backend: 17 new tests (327 total) — section order, authored content coverage,
the technical term never replacing the title, examples that are hypothetical,
a zero co-pay stated as good news rather than "0%", every stated value tracing
to its wording, unknowns visible, conflicts showing both readings, no claim
outcome anywhere, and cross-user access refused.

Frontend: 12 new tests (201 total).

Browser: 19 checks against the real stack — API, worker and frontend together.
A PDF uploaded through the UI, processed by the worker, and read back as a
report with five cited facts, one visible unknown, verbatim source wording,
and no numeric score.

## Open questions

1. **Only six facts are decoded.** The sections the specification names —
   "At Claim Time", "Not Covered", "Policy Details" — have no cards yet
   because no fact keys map to them. They appear once extraction covers them,
   which is either more patterns or a model.
2. **`unreadClauseCount` is honest but blunt.** It tells the reader we did not
   summarise N sections without saying which. Letting them browse the clauses
   we did read would be better, and is not in the specification.
3. **The authored explanations are unreviewed.** They are written to be
   accurate and cautious, but nobody with insurance expertise has read them.
   They should be reviewed before real users see them.

## Definition of done

| Item | Status |
|---|---|
| Sections | ✅ the seven from section 3.4, rendered when they have content |
| Fact cards | ✅ all six parts of the section 6 shape |
| Examples | ✅ hypothetical and labelled |
| Source viewer | ✅ quote plus the whole clause, verbatim |
| Confidence/unknown states | ✅ visible, in words, no numeric score |
