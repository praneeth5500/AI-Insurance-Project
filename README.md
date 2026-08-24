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
[`docs/SPEC_ISSUES.md`](docs/SPEC_ISSUES.md)

## Build status

Built phase by phase from `docs/11_BUILD_PLAN.md`.

| Phase | Status |
|---|---|
| 0 — Repository foundation | ✅ Complete |
| 1 — Design system | ✅ Complete |
| 2–17 | ⬜ Not started |

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
make migrate              # no migrations exist yet; this is a no-op
```

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

```bash
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
