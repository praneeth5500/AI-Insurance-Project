# Frontend

Next.js (App Router) + React + TypeScript strict + Tailwind CSS.

## Phase 1 status

The design system exists and is browsable at **`/design-system`**. There is
still no domain logic: every component is presentational. `app/page.tsx`
remains a **developer status page**, not the product home — the real home
screen is Phase 3.

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

## Structure so far

```text
app/                       route tree (App Router)
app/globals.css            design tokens + base typography
app/design-system/         component showcase
components/ui/             Button, Card, Input, ChoiceCard, Sheet, Modal
components/feedback/       InlineAlert, Skeleton, EmptyState, ErrorState,
                           ProgressStage
components/layout/         AppShell, TopNavigation, MobileNavigation,
                           PageContainer, PageHeader
lib/api/                   typed API client + AsyncState
lib/ui/                    cn(), useReturnFocus()
tests/                     vitest unit tests (jsdom)
```

## Design system

Tokens live in `app/globals.css`, not in a Tailwind config file: the
specification's own variable names in `:root`, re-exported to Tailwind through
`@theme inline`. `docs/02_UX_UI_SPEC.md` stays the readable source of truth.

Contrast was validated against WCAG 2.1 AA and is enforced by
`tests/tokens-contrast.test.ts`. Two usages are constrained as a result — see
`docs/PHASE_1_NOTES.md`:

- text inside a soft-tinted container always uses `--text-primary`; tone
  colours are for icons and rules;
- interactive boundaries use `--control-border`, never the decorative
  `--border`.

Rules that components follow:

- **Tone is never colour alone.** Alerts carry an icon and a wording label;
  choice cards show a check mark as well as a tint.
- **Every field is labelled**, and errors are linked with `aria-describedby`
  and announced.
- **Every tap target clears ~44px.**
- **Loading placeholders are hidden from screen readers**; a status message is
  announced instead.
- **Overlays trap focus and return it to the trigger** when they close.
- **No percentages for staged progress** — position only.

## Structure that later phases create

These are **not** scaffolded as empty folders on purpose — `CLAUDE.md` asks us
to avoid premature abstraction, so each arrives with the phase that fills it
(target shape from `docs/03_FRONTEND_ARCHITECTURE.md` section 1):

```text
app/(public)/  app/(auth)/  app/(app)/     route groups        Phases 2-3
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
- **Dark mode is deferred** (`docs/13_DECISIONS_AND_OPEN_ITEMS.md`), so there
  is deliberately no dark palette.
