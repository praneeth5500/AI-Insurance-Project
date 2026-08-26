import { AlertTriangle, Check, CircleHelp, TriangleAlert } from "lucide-react";
import type { ConfidenceState } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * How much a fact card can be trusted
 * (`docs/07_POLICY_DECODER_AI.md` section 5).
 *
 * The wording carries the meaning and the icon reinforces it; colour is never
 * the only signal (`docs/02_UX_UI_SPEC.md` section 16).
 *
 * A HIGH-confidence fact deliberately gets no badge. Labelling the ordinary
 * case "high confidence" would make the whole report read as a set of
 * confidence scores rather than a reading of a policy — and would make the
 * genuinely uncertain cards harder to pick out, which is the opposite of what
 * this is for.
 */
const STATE = {
  HIGH: null,
  MEDIUM: {
    label: "Worth double-checking",
    icon: CircleHelp,
    tone: "text-attention",
    surface: "bg-attention-soft",
  },
  LOW: {
    label: "We're not confident about this",
    icon: TriangleAlert,
    tone: "text-critical",
    surface: "bg-critical-soft",
  },
  NOT_FOUND: {
    label: "We couldn't find this in your policy",
    icon: CircleHelp,
    tone: "text-secondary",
    surface: "bg-bg",
  },
  CONFLICTING: {
    label: "Your policy says two different things",
    icon: AlertTriangle,
    tone: "text-critical",
    surface: "bg-critical-soft",
  },
} as const satisfies Record<ConfidenceState, unknown>;

export function ConfidenceBadge({ state }: { state: ConfidenceState }) {
  const config = STATE[state];
  if (config === null) return null;

  const { label, icon: Icon, tone, surface } = config;
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-1 self-start rounded-control px-2 py-0.5",
        "text-meta font-medium",
        surface,
        tone,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}

export { Check };
