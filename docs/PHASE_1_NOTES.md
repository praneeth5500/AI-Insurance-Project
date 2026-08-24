# Phase 1 — Design System

Implementation notes for `docs/11_BUILD_PLAN.md` Phase 1.

## Definition of done

| Requirement | Status | Evidence |
|---|---|---|
| Component showcase exists | ✅ | `/design-system` renders every Phase 1 component |
| Desktop checked | ✅ | 1280×900 in Chromium: top nav visible, bottom nav hidden, no horizontal scroll |
| Mobile checked | ✅ | 375×812 in Chromium: bottom nav visible, desktop nav hidden, no horizontal scroll, all tap targets ≥ 44px |
| Keyboard/focus works | ✅ | Skip link is first tab stop; focus ring renders; focus trapped in overlays; focus returns to trigger on close; radio arrow keys work |
| No domain logic | ✅ | Every component is presentational; nothing imports the API layer |

## Contrast validation

`docs/02_UX_UI_SPEC.md` says "Validate contrast before finalizing". Measured
against WCAG 2.1 (AA text 4.5:1, large text and non-text 3:1). The check is a
test — `frontend/tests/tokens-contrast.test.ts` — so a future token change
cannot quietly regress it.

| Pair | Ratio | Verdict |
|---|---|---|
| `--text-primary` on `--bg` | 16.70:1 | Pass |
| `--text-primary` on `--surface` | 17.93:1 | Pass |
| `--text-secondary` on `--bg` | 5.27:1 | Pass |
| `--text-secondary` on `--surface` | 5.66:1 | Pass |
| `--surface` on `--accent` (primary button) | 5.87:1 | Pass |
| `--accent` on `--surface` | 5.87:1 | Pass |
| `--accent` on `--bg` (focus ring) | 5.47:1 | Pass |
| `--positive` on `--surface` | 5.34:1 | Pass |
| `--attention` on `--surface` | 4.71:1 | Pass |
| `--critical` on `--surface` | 6.57:1 | Pass |
| `--text-primary` on any `*-soft` | 15.79–16.53:1 | Pass |
| **`--attention` on `--attention-soft`** | **4.34:1** | **Below AA for text** |
| **`--border` on `--surface`** | **1.24:1** | **Below 3:1 for control boundaries** |

### Finding 1 — `--attention` on `--attention-soft` is 4.34:1

Short of the 4.5:1 needed for body text, but comfortably over the 3:1 needed
for icons and rules.

**Handled by constraining usage, not by changing the palette.** Text inside a
soft-tinted container always uses `--text-primary`; the tone colour is used
only for the icon and the left rule. This is applied uniformly across all four
alert tones, so the treatment is consistent rather than one-off.

No specification file was edited. **If you would rather the attention colour be
usable as text on its own tint, it needs to darken slightly — that is a palette
decision for you, not one I should make.**

### Finding 2 — `--border` is 1.24:1 on `--surface`

This is correct for the "subtle border" the spec asks for: WCAG does not
require 3:1 for decorative edges such as card outlines and dividers. It *is*
too low when a boundary is the only thing identifying an interactive control.

**Handled by adding one derived token, not a new colour.**
`--control-border: var(--text-secondary)` (5.66:1) is used for input and choice
card boundaries; `--border` stays decorative. The alias is asserted in the
contrast test.

**If a lighter control border is wanted visually, the palette needs a genuinely
new token — that is a design decision I have left to you.**

## Decisions taken

### Three dependencies, each mapped to a specification line

| Dependency | Why | Specification |
|---|---|---|
| `geist` | Typography. Self-hosted, so no third-party font request at runtime and no network dependency at build. | 02 section 2: "Geist / Inter-like" |
| `@radix-ui/react-dialog` | Focus trapping, escape handling, scroll lock and dialog semantics for Sheet *and* Modal — one primitive covers both. Hand-rolling a focus trap would be worse. | 03 stack: "Accessible headless primitives" |
| `lucide-react` | Status icons, so tone is never carried by colour alone. | 03 stack: "One icon library" |

Class merging is a six-line local helper (`lib/ui/cn.ts`) rather than a
dependency. No state-management library was added.

### Tailwind v4, CSS-first

Tokens live in `app/globals.css`: the spec's own variable names in `:root`, and
a `@theme inline` block that re-exports them as Tailwind utilities. The spec
remains the readable source of truth and there is no `tailwind.config.ts` to
drift from it.

### Progress shows stages, never a percentage

`ProgressStage` renders "Your cover · Step 2 of 4". The onboarding flow has no
fixed question count (`docs/13_DECISIONS_AND_OPEN_ITEMS.md`), so a percentage
would be a number the product cannot honestly support — the same rule the
decoder's processing UI follows ("No fake percentages", 02 section 14).

### Choice cards are real radios and checkboxes

A visually hidden native input inside its `<label>`, styled through
`group-has-[:checked]`. Arrow-key navigation, roving focus, form participation
and screen-reader semantics come from the browser rather than from hand-written
ARIA. Selection is shown by a check mark as well as by colour.

### Navigation items are serialisable data

`NavItem.icon` is a *name* (`"home"`), resolved to a component by a registry
inside the client navigation component. Navigation lists are declared in server
components, and a component reference cannot cross that boundary. This surfaced
as a real build failure and is now the API.

### Overlays return focus themselves

The dialog primitive restores focus only when its own `Trigger` opened it.
Sheet and Modal are controlled through `open`/`onOpenChange`, so without help a
keyboard user was dropped onto `<body>` — verified as a genuine defect during
testing. `lib/ui/use-return-focus.ts` captures the previously focused element
during the render in which `open` flips true (by the time effects run, focus has
already moved) and restores it on close.

## What Phase 1 deliberately does NOT do

| Not built | Why |
|---|---|
| `Toast` | Listed in `docs/03_FRONTEND_ARCHITECTURE.md` section 4 but **not** in the Phase 1 build list. Logged as issue 8 in `docs/SPEC_ISSUES.md`; it should arrive with the first feature that needs a transient message. |
| Any domain component | Phase 1 says "Do not build domain logic". Questionnaire, recommendation, product-detail and decoder components belong to Phases 4–13. |
| The product home screen | Phase 3. `/` is still a developer status page. |
| Dark mode | Deferred in `docs/13_DECISIONS_AND_OPEN_ITEMS.md`. There is deliberately no dark palette. |
| Playwright as a project dependency | Browser verification was run out-of-tree. An in-repo E2E suite belongs to the phase with a user flow worth testing end to end. |

## Verification performed

66 unit tests (`pnpm test`), plus 18 browser checks in Chromium at 375×812 and
1280×900 covering: horizontal overflow, navigation swap, 44px tap targets,
sheet placement (bottom on mobile, right panel on desktop), skip-link tab
order and visibility, focus-ring rendering, focus trapping, focus return,
radio arrow keys, and `prefers-reduced-motion` suppression. All 18 passed.

## Open question for the founder

The showcase at `/design-system` is currently reachable by anyone who has the
URL. It contains no data and no product claims, but it should sit behind the
beta auth added in Phase 2, or be disabled outside `local`. Flagging it now so
it is not forgotten at Phase 16 hardening.

## Next phase

Phase 2 — Beta Auth: email entry, allowlist check, magic-link flow, session,
protected routes, sign out, behind a provider adapter.
