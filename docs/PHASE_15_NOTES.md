# Phase 15 — Analytics & Feedback

## What this phase changed

The product can now be measured: a funnel from first screen to answered
question, a helpfulness signal on the screens where being wrong costs the
reader something, and error telemetry.

`docs/11_BUILD_PLAN.md` attaches one instruction to this phase — **do not send
sensitive answer values to analytics** — and `docs/03_FRONTEND_ARCHITECTURE.md`
section 7 ends with the same rule. Everything below follows from taking it as
a property to enforce rather than a habit to maintain.

## The allow-list, and why it is the whole design

A rule written in a comment is one that gets broken by the next call site. So
analytics works the way logging already does in this codebase
(`ALLOWED_LOG_FIELDS`): **an allow-list applied centrally**, with exactly one
function able to write an event.

* An event name nobody declared is refused. A typo is a silent hole in a
  funnel; an undeclared event from a client is an unbounded write.
* A property key not declared **for that event** is dropped. There is no
  free-form property bag anywhere.
* Values must be primitives. A dict is how an answer payload travels, and no
  event needs one.
* Strings are truncated to 64 characters, so a property cannot become a
  smuggling channel for free text.

The failure mode of a careless call site is therefore a *missing property*,
never a leaked answer. `sanitize()` is exported separately so the rule can be
tested directly, and one test walks the registry itself asserting no event
declares a property that could hold an answer — that test is what would have
to be edited to introduce a leak, which makes it a deliberate act with a
visible diff.

What events may carry is deliberately dull: which screen, which question id,
how many, which stable identifier. Never what someone answered.

## Decisions and why

### Client events are declared, server events are not client-emittable

A browser may post only events marked `client_emittable`. Questionnaire
completion, match generation and priority changes are recorded where they
actually happen, so a browser cannot fabricate a funnel.

### Priorities count, they do not name

`priority_changed` records `priority_count`. Which priorities someone chose is
something they told us about themselves; the number is what the funnel needs.

### Feedback is the one place free text lives — and it stays there

The comment goes to the `feedback` table. The `feedback_submitted` event
carries only the context and the rating. Verified end to end: a comment
mentioning a policy number and a health condition appears in the feedback row
and in **zero** analytics events.

### "Was this helpful?" asks for a reason only on "no"

A rating alone is enough — requiring a comment gets far fewer responses, and
the count is the signal that generalises. What went wrong is worth the extra
step; what went right rarely says anything actionable. The comment box warns
that a person will read it.

### Error telemetry lives inside `ErrorState`

Rather than at each call site, so an error screen cannot be added without
being counted. The error *code* is recorded; the description, which can carry
specifics, is not.

### Measurement can never break the thing it measures

`record_safely` swallows everything. A questionnaire submission must not fail
because an event could not be written, and `track()` on the client is
fire-and-forget with `keepalive` so an event on a link click survives the
navigation.

## Spec issues resolved

* **Issue 3** — `questionnaire_reviewed` vs `questionnaire_completed`. These
  are two genuinely different things, so both exist: reviewed fires on
  reaching the review screen, completed on submitting. The beta checklist's
  event is present and the frontend spec's event is too.
* **Issue 12** — `CLAUDE.md` wants an analytics event per feature while the
  build plan sequences analytics at Phase 15. Resolved by Phase 15 going back
  and wiring every earlier screen, which is what the build plan's ordering
  implied all along.

## Verification

Backend: 21 new tests (394 total). The ones that matter most try to *get*
sensitive data into an event: every field the health questionnaire collects
offered to the closest event, structured values on a declared key, oversized
strings, and a Q&A question containing a health condition. All are dropped.

Frontend: 8 new tests (228 total).

Real stack: drove the app and read the database afterwards. Eight distinct
events recorded with clean properties — `{"section": "your-cover"}`,
`{"outcome": "READY", "facts_found": 5, "facts_not_found": 1}`,
`{"rating": -1, "context_type": "DECODER"}` — and a feedback comment stored
for a human with zero occurrences anywhere in `analytics_events`.

## Open questions

1. **No analytics vendor.** Events go to our own table behind a sink
   interface. That is fine for a small beta and avoids a vendor decision, but
   there is no dashboard — reading the funnel means writing SQL.
2. **`analytics_events` is not in the data model.** Added deliberately;
   recorded in `docs/SPEC_ISSUES.md`.
3. **No retention policy.** Events accumulate forever. A beta should decide
   how long it keeps them, and `feedback` in particular contains free text
   someone wrote.

## Definition of done

| Item | Status |
|---|---|
| Funnel events | ✅ all 11 the beta checklist names, plus the frontend spec's list |
| Beta feedback | ✅ with a bounded comment and a known context |
| Helpfulness | ✅ on results, comparison and the decoded report |
| Error telemetry | ✅ emitted from `ErrorState`, so it cannot be forgotten |
| No sensitive values in analytics | ✅ enforced centrally, tested adversarially |
