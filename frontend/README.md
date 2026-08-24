# Frontend

Next.js (App Router) + React + TypeScript strict + Tailwind CSS.

## Phase 0 status

Only the shell exists. `app/page.tsx` is a **developer status page**, not the
product home — it shows whether the API is reachable and makes no product or
insurance claim. The real home screen is Phase 3.

## Commands

```bash
pnpm dev         # dev server on :3000
pnpm build       # production build (fails on type or lint errors)
pnpm lint
pnpm typecheck
pnpm test        # vitest
pnpm format
```

`NEXT_PUBLIC_API_BASE_URL` points at the API (default `http://localhost:8000`).

## Structure that Phase 0 created

```text
app/            route tree (App Router)
lib/api/        typed API client + AsyncState
tests/          vitest unit tests
```

## Structure that later phases create

These are **not** scaffolded as empty folders on purpose — `CLAUDE.md` asks us
to avoid premature abstraction, so each arrives with the phase that fills it
(target shape from `docs/03_FRONTEND_ARCHITECTURE.md` section 1):

```text
app/(public)/  app/(auth)/  app/(app)/     route groups        Phases 2-3
components/ui/ layout/ feedback/           design system       Phase 1
features/auth/                             beta auth           Phase 2
features/home/                             home screens        Phase 3
features/questionnaire/                    question renderer   Phase 4
features/recommendations/                  matched options     Phase 5
features/comparison/                       compare up to 3     Phase 6
features/product-detail/                   policy detail       Phase 7
features/policy-upload/ policy-decoder/ policy-chat/           Phases 10-13
features/account/                          profile/settings    later
lib/analytics/ auth/ formatting/ validation/
styles/
```

## Conventions

- **TypeScript strict**, plus `noUncheckedIndexedAccess` and
  `exactOptionalPropertyTypes`. No `any`.
- **Every request state is explicit.** `AsyncState<T>` in `lib/api/types.ts`
  has `idle | loading | success | error`; screens render all four. Never a
  blank screen while loading (`docs/03_FRONTEND_ARCHITECTURE.md` section 5).
- **The API client returns errors, it does not throw them**, so the error
  branch cannot be forgotten.
- **camelCase on the wire.** The backend translates to snake_case internally.
- **No design tokens yet.** The colour system in `docs/02_UX_UI_SPEC.md` needs
  contrast validation first; that is Phase 1.
