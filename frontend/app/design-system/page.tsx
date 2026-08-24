import { ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import type { NavItem } from "@/components/layout/nav-items";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { SkeletonBlock } from "@/components/feedback/skeleton";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  ChoiceCardDemo,
  InputDemo,
  OverlayDemo,
  ProgressStageDemo,
} from "@/app/design-system/showcase-demos";

export const metadata = {
  title: "Design system — AI Insurance Decision Platform",
};

// Navigation labels come from docs/02_UX_UI_SPEC.md section 4; the routes come
// from docs/03_FRONTEND_ARCHITECTURE.md section 2. Those routes are built in
// Phases 2-3, which the notice at the top of the page states plainly.
const DESKTOP_ITEMS = [
  { href: "/app/recommend", label: "Find Insurance" },
  { href: "/app/recommendations", label: "My Recommendations" },
  { href: "/app/policies", label: "My Policies" },
  { href: "/help", label: "Help" },
] as const;

const DESKTOP_END_ITEMS = [{ href: "/app/profile", label: "Profile" }] as const;

const MOBILE_ITEMS = [
  { href: "/app/home", label: "Home", icon: "home" },
  { href: "/app/recommend", label: "Recommend", icon: "recommend" },
  { href: "/app/policies", label: "Policies", icon: "policies" },
  { href: "/app/profile", label: "Profile", icon: "profile" },
] as const satisfies readonly NavItem[];

function Section({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4 border-t border-border pt-8">
      <div className="flex flex-col gap-1">
        <h2 className="text-h3 font-semibold text-primary">{title}</h2>
        {note ? <p className="max-w-prose text-support text-secondary">{note}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Swatch({ name, variable, ratio }: { name: string; variable: string; ratio?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className="size-10 shrink-0 rounded-control border border-border"
        style={{ backgroundColor: `var(${variable})` }}
      />
      <span className="flex flex-col">
        <span className="text-support font-medium text-primary">{name}</span>
        <span className="text-meta text-secondary">{variable}</span>
        {ratio ? <span className="text-meta text-secondary">{ratio}</span> : null}
      </span>
    </div>
  );
}

export default function DesignSystemPage() {
  return (
    <AppShell
      desktopItems={DESKTOP_ITEMS}
      desktopEndItems={DESKTOP_END_ITEMS}
      mobileItems={MOBILE_ITEMS}
    >
      <PageContainer>
        <div className="flex flex-col gap-8">
          <PageHeader
            title="Design system"
            description="Phase 1 component showcase. Every component here is presentational — no product or insurance logic is implemented yet."
          />

          <InlineAlert tone="info" title="Internal reference page">
            The navigation above is live so the responsive shell can be checked, but the routes it
            points to are built in Phases 2–3 and will not resolve yet. Nothing on this page shows
            real insurance data.
          </InlineAlert>

          <Section
            title="Colour"
            note="Tokens from docs/02_UX_UI_SPEC.md section 2, validated against WCAG 2.1 AA. Two constrained usages are documented in docs/PHASE_1_NOTES.md and enforced by tests."
          >
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Swatch name="Background" variable="--bg" />
              <Swatch name="Surface" variable="--surface" />
              <Swatch name="Text primary" variable="--text-primary" ratio="16.70:1 on background" />
              <Swatch
                name="Text secondary"
                variable="--text-secondary"
                ratio="5.27:1 on background"
              />
              <Swatch name="Border (decorative)" variable="--border" />
              <Swatch name="Control border" variable="--control-border" ratio="5.66:1 on surface" />
              <Swatch name="Accent" variable="--accent" ratio="5.87:1 on surface" />
              <Swatch name="Accent soft" variable="--accent-soft" />
              <Swatch name="Positive" variable="--positive" ratio="5.34:1 on surface" />
              <Swatch name="Positive soft" variable="--positive-soft" />
              <Swatch name="Attention" variable="--attention" ratio="4.71:1 on surface" />
              <Swatch name="Attention soft" variable="--attention-soft" />
              <Swatch name="Critical" variable="--critical" ratio="6.57:1 on surface" />
              <Swatch name="Critical soft" variable="--critical-soft" />
            </div>
          </Section>

          <Section
            title="Typography"
            note="Geist, self-hosted. Tabular numerals are on by default."
          >
            <div className="flex flex-col gap-3">
              <p className="text-hero-mobile font-semibold sm:text-hero">Hero</p>
              <p className="text-h1 font-semibold">Heading 1</p>
              <p className="text-h2 font-semibold">Heading 2</p>
              <p className="text-h3 font-medium">Heading 3</p>
              <p className="text-body-lg">Body large — 18px</p>
              <p className="text-body">Body — 16px, the default reading size</p>
              <p className="text-support text-secondary">Support — 14px</p>
              <p className="text-meta text-secondary">Metadata — 13px · 1234567890</p>
            </div>
          </Section>

          <Section title="Buttons" note="Every size clears the ~44px minimum touch target.">
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <Button>Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="ghost">Ghost</Button>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="lg">Large primary</Button>
                <Button loading>Loading</Button>
                <Button disabled>Disabled</Button>
              </div>
              <div className="max-w-sm">
                <Button fullWidth size="lg">
                  Full width
                </Button>
              </div>
            </div>
          </Section>

          <Section title="Cards">
            <div className="grid gap-4 sm:grid-cols-2">
              <Card>
                <h3 className="text-h3 font-medium text-primary">Flat card</h3>
                <p className="mt-1 text-support text-secondary">
                  The default surface for grouped content.
                </p>
              </Card>
              <Card emphasis="raised">
                <h3 className="text-h3 font-medium text-primary">Raised card</h3>
                <p className="mt-1 text-support text-secondary">
                  For the single thing a screen is about.
                </p>
              </Card>
            </div>
          </Section>

          <Section
            title="Inputs"
            note="Labels are required. Errors are linked with aria-describedby and announced."
          >
            <InputDemo />
          </Section>

          <Section
            title="Choice cards"
            note="Real radio and checkbox inputs, so arrow keys, focus and form semantics come from the browser."
          >
            <ChoiceCardDemo />
          </Section>

          <Section
            title="Progress stage"
            note="Stage position, never a percentage — the flow has no fixed question count."
          >
            <ProgressStageDemo />
          </Section>

          <Section title="Alerts" note="Tone is carried by icon and wording as well as colour.">
            <div className="flex flex-col gap-3">
              <InlineAlert tone="info">Contextual information about this step.</InlineAlert>
              <InlineAlert tone="positive" title="Saved">
                Your answers are stored and you can return to them.
              </InlineAlert>
              <InlineAlert tone="attention" title="Worth checking">
                Some details could not be verified from the source document.
              </InlineAlert>
              <InlineAlert tone="critical" title="We couldn't read this file">
                The file appears to be password protected.
              </InlineAlert>
            </div>
          </Section>

          <Section
            title="Overlays"
            note="Focus is trapped, Escape closes, and focus returns to the trigger."
          >
            <OverlayDemo />
          </Section>

          <Section
            title="Loading"
            note="Placeholders are hidden from screen readers; a status message is announced instead."
          >
            <Card>
              <SkeletonBlock label="Loading example content" lines={3} />
            </Card>
          </Section>

          <Section title="Empty state">
            <EmptyState
              icon={ShieldCheck}
              title="No saved policies yet"
              description="When you upload a policy, it will appear here so you can return to it."
              action={<Button variant="secondary">Upload a policy</Button>}
            />
          </Section>

          <Section
            title="Error state"
            note="Shows the API error code and request reference when available."
          >
            <ErrorState
              title="We couldn't load this"
              description="The service is temporarily unavailable. Your answers have been saved."
              code="SERVICE_UNAVAILABLE"
              requestId="req_0a1b2c3d4e5f6789"
              action={<Button variant="secondary">Try again</Button>}
            />
          </Section>
        </div>
      </PageContainer>
    </AppShell>
  );
}
