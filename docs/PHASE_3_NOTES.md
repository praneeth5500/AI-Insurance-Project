# Phase 3 — Home

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 3.

## A note on the Definition of Done

Phase 3 is the first phase in the build plan with **no "Done when" section**.
Recorded as issue 11 in `docs/SPEC_ISSUES.md`. In its absence the phase was
held to `CLAUDE.md`'s own definition of done, and to the two home sections of
the specification:

| Requirement | Status | Evidence |
|---|---|---|
| New-user home: Health, Motor, Existing Policy cards | ✅ | All three render with the specification's copy verbatim |
| Returning home: Continue, Recommendations, Policies, conditional modules | ✅ | All six modules render in the specified order |
| Use mock data first | ✅ | `HOME_DEMO_DATA` serves labelled synthetic modules; local/preview only |
| Types pass | ✅ | mypy strict, tsc strict |
| Tests pass | ✅ | 58 backend, 94 frontend |
| Mobile works | ✅ | 375×812 in Chromium: no horizontal scroll, all actions ≥44px |
| Keyboard / accessibility | ✅ | Skip link first, one `h1`, status spelled out not colour-coded |
| Loading / empty / error states | ✅ | Empty modules are absent by design; API failure renders `ErrorState` |
| No sensitive-data logging | ✅ | The home endpoint logs nothing beyond the standard request line |
| Documentation updated | ✅ | This file, `SPEC_ISSUES.md`, `README.md`, `.env.example` |

Analytics (`home_viewed`) is **not** implemented — see "Deliberately not done".

## The central decision: nothing is advertised that does not work

Three specifications pull in different directions here:

* `docs/02_UX_UI_SPEC.md` section 5 says the new-user home shows a Health card,
  a Motor card and an Existing Policy card.
* `docs/12_BETA_CHECKLIST.md` requires **no dead buttons**, and lists Health as
  the only recommendation domain enabled initially.
* `docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 8 says motor must not be
  enabled until the health engine and motor data are ready.

And in Phase 3 none of the three destinations exist yet: the questionnaire is
Phase 4, the matching engine Phase 9, the decoder Phases 10–13.

**Resolution:** all three cards are rendered exactly as specified, but each
card's action appears only when its flow actually works. Until then the card
shows a plain "Coming soon" with one line saying what is being built — not a
button, not a link, nothing that goes nowhere. `CLAUDE.md` is explicit that the
UI must never make a claim the backend cannot support.

Availability is configuration, not code:

```text
FEATURE_HEALTH_RECOMMENDATION   false   -> true in Phase 4
FEATURE_MOTOR_RECOMMENDATION    false   -> only when motor is genuinely ready
FEATURE_POLICY_DECODER          false   -> true in Phase 10
```

Phase 4 flips one flag and the Health card becomes a real entry point. No home
code changes.

## Mock data, and how it is kept honest

Phase 3 says "Use mock data first", and the returning-user home cannot be
reviewed before recommendation runs and uploaded policies exist. So
`HOME_DEMO_DATA=true` serves a fully populated summary.

Three constraints keep that from becoming a lie:

1. **The response is marked `dataMode: "DEMO"`**, and the UI renders a visible
   "Demo content" notice above it saying the activity is not the user's
   information and does not describe a real policy.
2. **Configuration refuses to start** with demo data enabled outside `local`
   and `preview`. A beta user cannot be shown synthetic activity by accident.
3. **The demo content contains no insurance facts.** No insurer, no product
   name, no premium, no claim outcome — only counts, dates and obviously
   demo identifiers (`rr_demo_1`, `pol_demo_1`). A test asserts this.

With the flag off — the default, and how the beta will run — the summary is
computed from real tables. Every module is genuinely empty today, and the home
says so by rendering the new-user screen rather than inventing activity.

## Other decisions

### Empty modules are absent, not empty

`docs/02_UX_UI_SPEC.md` section 6: "Do not render empty irrelevant modules."
There is deliberately no empty state for a home module — the API returns
`null` and nothing is drawn. Empty states belong on screens the user navigated
to on purpose.

### New vs returning is derived, not guessed

The API decides, from whether the user has any activity. The frontend renders
whichever the summary reports; it does not infer.

### The API reports state, the frontend owns copy

`GET /api/v1/home` returns availability, counts and identifiers. Every string
the user reads lives in the frontend, so wording can change without an API
change. The hero and card copy are taken from the specification verbatim.

### Claims progress never implies a claim outcome

The claims module shows "2 of 6 steps prepared" and carries the line "A
checklist helps you prepare. It does not decide whether a claim is accepted."
`docs/07_POLICY_DECODER_AI.md` section 9 forbids promising claim approval, and
a progress bar on a home screen is exactly where that could be implied.

### Recent Q&A is deliberately absent

`docs/01_PRODUCT_SPEC.md` section 5: "Do not place isolated recent Q&A on the
home screen. Q&A stays inside policy context." A test asserts the home never
renders it.

### Navigation still lists only Home

`docs/02_UX_UI_SPEC.md` section 4 specifies five destinations, but four of them
do not exist yet. They are added by the phases that build them, for the same
"no dead buttons" reason.

## Deliberately not done

| Not built | Why |
|---|---|
| `home_viewed` analytics | `docs/11_BUILD_PLAN.md` sequences analytics at Phase 15. `CLAUDE.md`'s definition of done asks for the event "where specified", which is a genuine tension — flagged as issue 12 rather than resolved by building an analytics pipeline three phases early. |
| Real recommendation / policy / household data | Phases 5–14 create those tables. The home reads them the moment they exist. |
| Privacy/settings entry | `docs/01_PRODUCT_SPEC.md` section 5 lists it among returning-home modules, but `/app/settings` is not built. Added with those routes. |
| Full activity history | Explicitly deferred by the specification. |

## Open questions for the founder

1. **Should the Motor card appear at all before motor works?** It is specified
   for the new-user home, so it renders as "Coming soon". The alternative is
   hiding it until motor is ready. Showing it sets an expectation; hiding it
   makes the home look thinner. Your call.
2. **Analytics timing** (issue 12): confirm that `home_viewed` and the rest can
   wait for Phase 15, or say the word and they come sooner.
3. Still open from earlier phases: session lifetimes, how invites are issued,
   the unthrottled magic-link endpoint, and `/design-system` being public.

## Verification performed

58 backend tests and 94 frontend tests, plus **26 browser checks** in Chromium
across both home states at 1280×900 and 375×812:

- new-user home: hero and card copy match the specification; three cards
  present; **no link points at an unbuilt destination**; all three show
  "Coming soon"; no premium, insurer or guarantee wording anywhere; one `h1`;
  skip link first in tab order; no horizontal scroll; every action ≥44px;
- returning home: demo content labelled; modules render in the specified order
  (Continue → Recommendations → Policies → Claims → Household → Vehicles); the
  claims module carries its no-outcome line; no Q&A module; no unsupported
  claim; no horizontal scroll; every action ≥44px.

## Next phase

Phase 4 — Questionnaire Engine: the reusable question renderer, branching,
stage progress, draft persistence and a short review, seeded with health-beta
questions. Matching is not implemented there.
