# Phase 4 — Questionnaire Engine

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 4.

## Definition of done

Phase 4, like Phase 3, has **no "Done when" section** (issue 11 in
`docs/SPEC_ISSUES.md`). Held to the build list plus `CLAUDE.md`'s own
definition of done:

| Requirement | Status | Evidence |
|---|---|---|
| Question schema | ✅ | `QuestionDefinition` per `docs/03_FRONTEND_ARCHITECTURE.md` §3, plus two documented additions |
| Cards / buttons | ✅ | One renderer covers all six input types, from Phase 1 components |
| Branching | ✅ | Deterministic, server-side; verified live in the browser |
| Progress stage | ✅ | Four stages, position not percentage |
| Back / continue | ✅ | Per the example screen in `docs/02_UX_UI_SPEC.md` §7 |
| Draft persistence | ✅ | Saved server-side on every answer; resuming lands where you left off |
| Short review | ✅ | Per stage, each editable |
| Seed health-beta questions | ✅ | 15 questions, drawn only from the specification's candidate lists |
| Do not implement final matching | ✅ | No matching exists; the review says so |
| Types / tests / mobile / keyboard / a11y | ✅ | 104 backend, 119 frontend, 31 browser checks |

## The seeded question set is marked DRAFT

`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 6: *"The structure is decided.
Exact question wording/data fields still need a dedicated pass."*

So `health-beta-draft-001` carries `status: "DRAFT"`, surfaced through the API
as `definitionStatus`, and every question is drawn from a list the
specification already provides:

* fields **only** from the candidate inputs in `docs/01_PRODUCT_SPEC.md` §2.2;
* priorities **only** from §2.3;
* stage names from §2.2;
* "Who are you looking to protect?" and its four options **verbatim** from the
  example screen in `docs/02_UX_UI_SPEC.md` §7.

Nothing asks for detailed medical history — the specification forbids it by
default — and no question states an insurance fact. A test asserts the copy
contains no guarantee, no "claim approved", no "cheapest"; "best" is allowed
only inside *"there is no single best policy"*, which is the framing the
product is built on rather than a claim.

**This still needs your wording pass.** Changing a question means a new
version, never an edit: a completed session records the version it was
answered against.

## Decisions taken

### Branching lives on the server, and answers are the only source of truth

Which questions apply is recomputed from the stored answers on every read.
Change an earlier answer and the branch it opened closes immediately — the
orphaned answer stays in the database (the user did give it) but is excluded
from the working set, so it cannot influence branching or completeness. The
client never decides what to show; it renders what the server returns.

A condition is a small inspectable structure (`field`, `operator`, `value`,
or `allOf`) rather than an expression language, so which questions a person
saw can be reconstructed exactly.

### Two additions to the question schema

Both recorded in `docs/SPEC_ISSUES.md`:

* **`maxSelections`** — §2.3 says "choose up to 3" but the schema in §3 has no
  way to express a limit.
* **`sensitive`** — `docs/05_DATA_MODEL.md` §2 requires sensitive fields to be
  flagged in metadata. It is mirrored onto the stored answer, so anything
  reading answers knows what must never be logged or sent to analytics without
  consulting the definition.

### A route per stage

`docs/03_FRONTEND_ARCHITECTURE.md` §2 lists `/about-you`, `/current-cover`,
`/priorities`, `/review`. Kept exactly, with one question per screen inside a
stage (`docs/02_UX_UI_SPEC.md` rule 2). The stage route is what makes the
review screen's per-section **Edit** links possible.

### The review button does not promise matches

`docs/01_PRODUCT_SPEC.md` §2.4 specifies **"Find my matches"**. Matching is
Phase 9, so until it exists the button reads **"Save my answers"** and the
confirmation says *"Matched options are being built. Nothing has been shared
with any insurer."* Promising matches that cannot be produced is exactly the
unsupported UI claim `CLAUDE.md` forbids. The specified wording is already
wired behind `matchingAvailable` and appears the moment Phase 9 lands.

### The health entry point is now live

`FEATURE_HEALTH_RECOMMENDATION` now defaults to **true**: the questionnaire
genuinely works, so the home card links to it instead of saying "Coming soon".
Motor and the policy decoder stay off. "Find Insurance" joins the navigation
for the same reason — the destination exists.

### Answers are validated server-side, and errors never echo them

Every answer is checked against its definition before storage, so a draft can
never hold a value the questionnaire could not have produced. Error messages
never repeat the submitted value — answers can be sensitive. Answering a
question hidden by branching is rejected rather than silently accepted.

### A completed session is frozen

Once submitted, answers cannot be changed and the session cannot be
re-completed; starting again creates a new draft. This is what will let a
recommendation run stay reproducible when Phase 9 arrives.

## Defect found while building

**The review screen's Edit link announced "EditYour cover".** The visible word
and the screen-reader-only stage name were separate JSX children, and the
space between them was lost to formatting. Caught by a test asserting the
accessible name, not the text content. Fixed by putting the whole name in one
string and hiding the visible word from assistive technology.

Also corrected during verification: progress read "Step 3 of 3" during the
questions but "Step 4 of 4" on review. `docs/02_UX_UI_SPEC.md` §7 shows four
stages throughout, so Review is now in the indicator from the first question.

## Deliberately not done

| Not built | Why |
|---|---|
| `AIHelpSheet` ("Ask a question") | Listed under questionnaire components in `docs/03_FRONTEND_ARCHITECTURE.md` §4, but contextual AI help needs an LLM, and the provider is open item 2. `HelpDisclosure` — the static "Why we're asking this" — is built. |
| Matching, results, priority fine-tuning | Phases 5–9. Phase 4 says explicitly: do not implement final matching. |
| Motor questions | No question set exists; motor stays off (open item 8). |
| `question_answered` / `questionnaire_reviewed` analytics | Phase 15, per issue 12. Note the design already supports it safely: `analyticsKey` is on every question and `sensitive` marks the one answer whose value must never be sent. |

## Open questions for the founder

1. **The question wording needs your pass** (open item 6). Fifteen questions,
   all from the specification's candidate lists — but the phrasing, the order,
   and whether every field earns its place are yours to decide. In particular:
   *is 15 questions too long for one sitting?*
2. **The sum-insured brackets** ("Up to ₹5 lakh", "₹5–10 lakh", …) are the
   user's own target, not a product's terms — but they are the one place I
   chose numbers the specification does not list. Say the word and they change.
3. **Should the ongoing-health-condition question exist at all in the beta?**
   It is optional, flagged sensitive, offers "I'd rather not say", and asks
   only yes/no. It is also the only sensitive question in the flow, so
   dropping it would remove that whole category of risk.
4. Still open from earlier phases: session lifetimes, how invites are issued,
   the unthrottled magic-link endpoint, `/design-system` being public, and
   analytics timing (issue 12).

## Verification performed

104 backend tests, 119 frontend tests, and **31 browser checks** in Chromium
driving the real flow end to end:

- home card links to the questionnaire; entry redirects to the first stage;
- one `h1` per screen; stage progress with no percentage; Continue blocked
  until a required question is answered;
- "Why we're asking this" collapsed by default, expands, reports its state;
- **branching live**: choosing "Me + spouse" reveals the spouse question;
  going back and choosing "Just me" removes it;
- optional questions skippable; priorities capped at three with the fourth
  option disabled and the count shown;
- review shows chosen **labels** not stored values, offers an Edit link per
  section that returns to that stage, and does not promise matches;
- resuming mid-flow lands on the right screen, not back at question one;
- submission confirmed without claiming anything was shared;
- 375×812: no horizontal scroll, every control ≥44px, skip link first.

## Next phase

Phase 5 — Mock Recommendation Experience: "What we learned about you",
5 primary matched options with "see 5 more", category fit, watch-outs, the
priority editor and comparison selection, on synthetic products.
