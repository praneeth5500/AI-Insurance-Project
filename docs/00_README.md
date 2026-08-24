# AI Insurance Decision Platform — Claude Code Project Kit

## What this kit is

This folder is the current source of truth for the web app we have designed through founder interviews.

The product is an **invite-only beta** for friends/family and selected real users. It is **not a public production launch yet**.

The purpose of the beta is to learn:

1. Can users complete the guided insurance-needs flow?
2. Do the resulting matched options make sense to them?
3. Do they understand *why* an option matches their needs?
4. Does the policy decoder explain difficult insurance language clearly?
5. Do users trust the explanations when source clauses are shown?
6. Which parts confuse them or fail?
7. What should be changed before a broader launch?

## Core product

Two modules:

### Module 1 — Find Insurance That Fits Me

- Adaptive questionnaire
- Health first; motor supported by the architecture and introduced incrementally
- User chooses top priorities
- Matching engine filters unsuitable options
- Show **5 primary matched options**
- Allow **See all 10**
- No public overall numerical "92/100" score
- Show category-level fit instead
- Let users change priorities and recalculate
- Explain why each policy matches
- Explain trade-offs
- Decode technical policy terms
- Show source wording when available
- Beta can hand off to an official insurer/approved partner destination later

### Module 2 — Understand My Existing Policy

- PDF / scanned policy upload
- Extract policy facts
- Plain-language decoder
- Source-linked explanations
- Policy Q&A
- Claims-readiness checklist
- Never guarantee claim approval

## First beta access

- Invite-only
- Email allowlist
- Passwordless magic-link sign-in
- New user → product home
- Returning user → personalized home

## Technical direction

- Frontend: Next.js + React + TypeScript
- Styling: Tailwind CSS + accessible primitives + custom design system
- Backend: Python + FastAPI + Pydantic
- Database: PostgreSQL
- File storage: private S3
- Async jobs: queue + Python worker
- AI providers behind an internal interface
- OCR behind an internal interface
- Modular monolith; no microservices yet

## How Claude Code should use this kit

Read in this order:

1. `CLAUDE.md`
2. `01_PRODUCT_SPEC.md`
3. `02_UX_UI_SPEC.md`
4. `03_FRONTEND_ARCHITECTURE.md`
5. `04_BACKEND_ARCHITECTURE.md`
6. `05_DATA_MODEL.md`
7. `06_RECOMMENDATION_ENGINE.md`
8. `07_POLICY_DECODER_AI.md`
9. `08_API_CONTRACTS.md`
10. `09_AWS_DEPLOYMENT.md`
11. `10_TESTING_AND_EVALS.md`
12. `11_BUILD_PLAN.md`
13. `12_BETA_CHECKLIST.md`
14. `13_DECISIONS_AND_OPEN_ITEMS.md`

## Important build rule

Do **not** build the whole product in one prompt.

Work phase-by-phase from `11_BUILD_PLAN.md`.

At the end of every phase:

- run tests;
- verify mobile;
- verify error states;
- update documentation;
- commit;
- only then begin the next phase.

## Prototype truth rule

A UI can be polished while the data is still prototype data.

Never make prototype data look like verified real insurance facts.

Data records must carry provenance such as:

- `SYNTHETIC`
- `MANUALLY_VERIFIED`
- `PARTNER_API`

For friends/family UX testing, synthetic products are acceptable if clearly labeled as demo data.

Real-product facts should only be displayed when they were manually verified against source material or received from an approved API/integration.

---

## Suggested repo shape

```text
insurance-app/
├── CLAUDE.md
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── UX_UI_SPEC.md
│   ├── FRONTEND_ARCHITECTURE.md
│   ├── BACKEND_ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── RECOMMENDATION_ENGINE.md
│   ├── POLICY_DECODER_AI.md
│   ├── API_CONTRACTS.md
│   ├── AWS_DEPLOYMENT.md
│   ├── TESTING_AND_EVALS.md
│   ├── BUILD_PLAN.md
│   ├── BETA_CHECKLIST.md
│   └── DECISIONS_AND_OPEN_ITEMS.md
├── frontend/
├── backend/
├── worker/
├── evals/
├── scripts/
└── infra/
```
