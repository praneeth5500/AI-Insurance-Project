# Claude Code Build Plan

Build in phases. Do not skip ahead.

---

# Phase 0 — Repository Foundation

## Build

- monorepo/folder structure;
- frontend;
- backend;
- worker placeholder;
- docs;
- env files/templates;
- lint/format;
- strict TypeScript;
- Python tooling;
- test runners;
- Docker local dependencies if desired.

## Done when

- frontend runs;
- backend runs;
- DB connects;
- health endpoint works;
- CI/test command exists.

---

# Phase 1 — Design System

## Build

- tokens;
- typography;
- Button;
- Card;
- Input;
- Choice Card;
- Sheet;
- Modal;
- Alert;
- Skeleton;
- Empty State;
- Error State;
- Progress Stage;
- responsive shell.

## Do not build domain logic.

## Done when

- component showcase exists;
- desktop/mobile checked;
- keyboard/focus works.

---

# Phase 2 — Beta Auth

## Build

- email entry;
- allowlist check;
- magic-link flow;
- session;
- protected routes;
- sign out.

Use a provider adapter.

## Done when

- allowlisted user can sign in;
- non-allowlisted user cannot access app;
- expired token handled;
- session protected.

---

# Phase 3 — Home

## Build

New-user home:

- Health card
- Motor card
- Existing Policy card

Returning home:

- Continue
- Recommendations
- Policies
- conditional claims/profile/vehicle modules

Use mock data first.

---

# Phase 4 — Questionnaire Engine

## Build

Reusable renderer:

- question schema;
- cards/buttons;
- branching;
- progress stage;
- back/continue;
- draft persistence;
- short review.

Seed health-beta questions.

Do not implement final matching yet.

---

# Phase 5 — Mock Recommendation Experience

Use synthetic products.

Build:

- What we learned;
- 5 primary matched options;
- see 5 more;
- category fit;
- watch-out;
- priority editor;
- comparison select.

Goal:

validate UX before real insurance data integration.

---

# Phase 6 — Comparison

Build:

- compare 2;
- compare 3;
- biggest differences;
- user-priority sorting;
- mobile stacked layout.

---

# Phase 7 — Product Detail

Build:

- fit summary;
- why match;
- watch-outs;
- policy sections;
- examples;
- source links;
- save;
- contextual CTA.

Still synthetic/fixture data acceptable.

---

# Phase 8 — Real Data Domain Layer

Build:

- canonical product model;
- product versioning;
- provenance;
- price state;
- manual verified-data importer;
- partner adapter interface.

Do not scrape random websites into production data.

---

# Phase 9 — Matching Engine

Build:

- hard eligibility;
- fit evaluators;
- priority weighting;
- scoring version;
- immutable recommendation runs;
- explanation evidence object.

Start with synthetic + manually verified fixtures.

Add AI explanation only after structured output is correct.

---

# Phase 10 — Policy Upload

Build:

- private upload;
- file validation;
- DB record;
- queue job;
- processing UI;
- failure handling.

---

# Phase 11 — Document Extraction

Build worker:

- native PDF extraction;
- OCR adapter fallback;
- page model;
- clause segmentation;
- structured fact extraction;
- validation;
- citations.

---

# Phase 12 — Decoder UI

Build:

- sections;
- fact cards;
- examples;
- source viewer;
- confidence/unknown states.

---

# Phase 13 — Policy Q&A

Build:

- retrieval;
- grounded answer;
- citations;
- insufficient-evidence response;
- AI unavailability handling.

---

# Phase 14 — Claims Readiness

Build:

- claims clause extraction;
- checklist;
- source links;
- mark complete.

No claim-approval prediction.

---

# Phase 15 — Analytics & Feedback

Add:

- funnel events;
- beta feedback;
- helpfulness;
- error telemetry.

Do not send sensitive answer values to analytics.

---

# Phase 16 — Security / Beta Hardening

Review:

- authz;
- S3 access;
- logs;
- rate limits;
- upload attacks;
- deletion;
- backups;
- error handling;
- accessibility;
- responsive behavior.

---

# Phase 17 — Friends & Family Beta

Start small.

Suggested:

```text
3–5 internal/family users
↓
fix major confusion
↓
10–20 invited users
↓
fix trust/accuracy problems
↓
expand gradually
```

Do not optimize growth before the product is understandable and reliable.

---

# Claude prompt pattern per phase

Use:

```text
Read CLAUDE.md and the relevant docs.
We are implementing Phase X only.

Before coding:
1. Summarize the requirements you will implement.
2. List files you plan to create/change.
3. Call out any ambiguity instead of inventing product behavior.

Then implement the smallest complete version.
Add tests.
Run tests.
Report what remains.
Do not implement later phases.
```
