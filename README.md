# AI Insurance Decision & Policy Intelligence Platform

Invite-only beta of a web app that helps people **understand insurance before
they choose it**.

> Understand first. Choose confidently.

Two modules:

1. **Find insurance that fits me** — an adaptive questionnaire, deterministic
   matching, and plain-language explanations of *why* an option fits.
2. **Understand my existing policy** — upload a policy, get source-linked
   explanations, grounded Q&A, and a claims-readiness checklist.

This is a product-learning beta, not a marketplace and not a public launch.

## ⚠️ Prototype data

Insurance data in this repository is **synthetic** unless a record explicitly
carries `MANUALLY_VERIFIED` or `PARTNER_API` provenance. Synthetic data is
labelled as demo data in the UI and must never be presented as verified
insurance fact. Premiums are never invented, and no claim outcome is ever
predicted. See `docs/06_RECOMMENDATION_ENGINE.md` section 3.

## Documentation

`CLAUDE.md` is the engineering authority. The full specification lives in
[`docs/`](docs/) and is the product source of truth — read it in order:

| # | Document |
|---|---|
| 00 | [Project kit overview](docs/00_README.md) |
| 01 | [Product spec](docs/01_PRODUCT_SPEC.md) |
| 02 | [UX / UI spec](docs/02_UX_UI_SPEC.md) |
| 03 | [Frontend architecture](docs/03_FRONTEND_ARCHITECTURE.md) |
| 04 | [Backend architecture](docs/04_BACKEND_ARCHITECTURE.md) |
| 05 | [Data model](docs/05_DATA_MODEL.md) |
| 06 | [Recommendation engine](docs/06_RECOMMENDATION_ENGINE.md) |
| 07 | [Policy decoder & AI](docs/07_POLICY_DECODER_AI.md) |
| 08 | [API contracts](docs/08_API_CONTRACTS.md) |
| 09 | [AWS / deployment](docs/09_AWS_DEPLOYMENT.md) |
| 10 | [Testing & evals](docs/10_TESTING_AND_EVALS.md) |
| 11 | [Build plan](docs/11_BUILD_PLAN.md) |
| 12 | [Beta checklist](docs/12_BETA_CHECKLIST.md) |
| 13 | [Decisions & open items](docs/13_DECISIONS_AND_OPEN_ITEMS.md) |

Implementation notes: [`docs/PHASE_0_NOTES.md`](docs/PHASE_0_NOTES.md) ·
[`docs/PHASE_1_NOTES.md`](docs/PHASE_1_NOTES.md) ·
[`docs/PHASE_2_NOTES.md`](docs/PHASE_2_NOTES.md) ·
[`docs/PHASE_3_NOTES.md`](docs/PHASE_3_NOTES.md) ·
[`docs/PHASE_4_NOTES.md`](docs/PHASE_4_NOTES.md) ·
[`docs/PHASE_5_NOTES.md`](docs/PHASE_5_NOTES.md) ·
[`docs/PHASE_6_NOTES.md`](docs/PHASE_6_NOTES.md) ·
[`docs/PHASE_7_NOTES.md`](docs/PHASE_7_NOTES.md) ·
[`docs/PHASE_8_NOTES.md`](docs/PHASE_8_NOTES.md) ·
[`docs/SPEC_ISSUES.md`](docs/SPEC_ISSUES.md)

## Build status

Built phase by phase from `docs/11_BUILD_PLAN.md`.

| Phase | Status |
|---|---|
| 0 — Repository foundation | ✅ Complete |
| 1 — Design system | ✅ Complete |
| 2 — Beta auth | ✅ Complete |
| 3 — Home | ✅ Complete |
| 4 — Questionnaire engine | ✅ Complete |
| 5 — Mock recommendation experience | ✅ Complete |
| 6 — Comparison | ✅ Complete |
| 7 — Product detail | ✅ Complete |
| 8 — Real data domain layer | ✅ Complete |
| 9 — Matching engine | ✅ Complete |
| 10 — Policy upload | ✅ Complete (behind `FEATURE_POLICY_DECODER`) |
| 11 — Document extraction | ✅ Complete (behind `FEATURE_POLICY_DECODER`) |
| 12 — Decoder UI | ✅ Complete (behind `FEATURE_POLICY_DECODER`) |
| 13 — Policy Q&A | ✅ Complete (behind `FEATURE_POLICY_DECODER`) |
| 14 — Claims readiness | ✅ Complete (behind `FEATURE_POLICY_DECODER`) |
| 15 — Analytics & feedback | ✅ Complete |
| 16–17 | ⬜ Not started |

## Repository layout

```text
backend/    FastAPI modular monolith (Python)
worker/     async document-processing worker (placeholder until Phase 10)
frontend/   Next.js + React + TypeScript
docs/       product and engineering specification
evals/      policy-decoder golden set (Phases 9/11)
infra/      deployment artefacts (Phase 16)
```

## Requirements

- Node 20+ and pnpm 9+
- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Docker (for local PostgreSQL)

## Local setup

```bash
cp .env.example .env      # then fill in locally — never commit .env
make install              # backend, worker and frontend dependencies
make db-up                # PostgreSQL 16 on :5432
make migrate              # apply database migrations
```

The beta is invite-only, so nobody can sign in until an address is invited.
Put your address in `BETA_ALLOWLIST_EMAILS` in `.env`, then:

```bash
make seed-allowlist
```

To load manually verified product data (the canonical catalogue ships empty):

```bash
cp backend/examples/products.template.json my-products.json
# fill in every REPLACE_ME — the importer refuses placeholders
make import-products FILE=my-products.json
```

In local development, magic links are written to
`backend/.dev-magic-links.log` instead of being emailed. Open the link from
there to sign in.

To review the returning-user home before real activity exists, set
`HOME_DEMO_DATA=true`. It serves clearly-labelled synthetic modules and is
refused outside `local` and `preview`.

`NEXT_PUBLIC_API_BASE_URL` is inlined into the frontend at **build** time, and
the API and app must be same-site for the session cookie to be sent.

Run the three processes:

```bash
make dev-backend          # http://localhost:8000
make dev-frontend         # http://localhost:3000
make dev-worker           # placeholder: starts, logs, exits
```

Verify:

```bash
curl http://localhost:8000/health/live     # {"status":"ok"}
curl http://localhost:8000/health/ready    # 200 with DB up, 503 with DB down
```

The component showcase is at
[localhost:3000/design-system](http://localhost:3000/design-system).

## Checks

Backend auth tests need a database:

```bash
make db-up         # required: auth tests run against real PostgreSQL
make check         # lint + typecheck + test (what CI runs)
make lint
make typecheck
make test
```

`make help` lists every command.

## Security ground rules

- **Never commit secrets.** `.env` is git-ignored; `.env.example` holds
  placeholders only.
- **Never log** policy text, health answers, raw documents or magic-link
  tokens. `backend/app/core/logging.py` enforces an allow-list.
- **Never expose uploaded files publicly.** Private storage and signed URLs
  only (Phase 10).
- **The LLM never ranks recommendations.** Matching is deterministic and
  testable (`docs/06_RECOMMENDATION_ENGINE.md`).
- **Sign-in tokens are stored only as digests**, are single-use, and expire.
  Sessions are revocable rows, not self-contained tokens.
- **Auth responses never reveal who is on the beta allowlist.**
- **Nothing is advertised that does not work.** Each destination is gated by a
  `FEATURE_*` flag and shows "Coming soon" until its flow exists.
- **Synthetic content is always labelled** and cannot be enabled outside local
  and preview.
- **The seeded questionnaire is DRAFT** and needs a wording pass; changing a
  question means a new version, never an edit.
- **Sensitive answers are flagged at the question and on the stored answer**,
  so nothing can send them to logs or analytics by accident.
- **Every insurance product in this build is invented** and labelled as such.
  No premium is shown anywhere, and no ranking is produced by an LLM.
- **No source citation is ever fabricated.** Where no policy document exists,
  the UI says so rather than hiding the control.
- **Examples explain a mechanism, never a product** — and are labelled as
  examples wherever they appear.
- **Nothing enters the verified catalogue without provenance**: source
  document, location within it, when it was checked and by whom. Synthetic
  data is refused outright.
- **Stale critical data excludes a product** rather than lowering its score.
- **A price is a state, never a bare number**, and no code path can produce
  one.
- **Matching is deterministic and versioned.** The same answers, priorities and
  product facts always produce the same result set, in the same order. The
  scoring version is stored on every run.
- **Unknown is never treated as average.** A dimension with no verified fact is
  reported as such and left out of the weighting entirely — it cannot drag a
  product down or prop one up.
- **A product a reader cannot buy is removed, not ranked low**, and the screen
  says how many were removed and under which rules — never which products.
- **A recommendation run is immutable.** Changing a priority creates a new run
  linked to the old one; a stored result is never rewritten, and the code
  raises rather than allowing an in-place edit.
- **An uploaded policy is never publicly reachable.** No public URL, no signed
  link — documents stream through an authenticated route that re-checks
  ownership on every request, and deletion is auditable.
- **Every extracted policy fact carries its citation** — the page and the
  exact sentence it came from. A fact without a clause behind it is not stored
  as a fact.
- **No answer value can reach analytics.** Events carry only declared
  property keys; anything else is dropped centrally, and free text lives only
  in the feedback table.
- **A claims checklist never blends what your policy requires with what
  insurers generally want**, and never predicts whether a claim will be paid.
- **Q&A answers come only from the uploaded document**, always with the
  wording they came from, and a question the policy does not answer gets a
  refusal rather than a plausible guess.
- **The decoder report opens with what it could not determine**, and an
  unknown is a visible card rather than a missing one.
- **Conflicting clauses are reported as conflicting**, never silently resolved,
  and nothing automated relies on a fact in that state.
- **A document we cannot read fails visibly** and says why. It never produces
  an empty policy that could be mistaken for one covering nothing.
- **A file's type is read from its bytes**, never from the filename or the
  `Content-Type` the browser claimed.
- **Every fit judgement stores its evidence** — the product facts, the reader's
  answers and the threshold that produced it — so a result can be explained
  months later without re-running anything.
