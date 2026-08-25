import { AlertTriangle, Check, CircleHelp, Minus, TriangleAlert } from "lucide-react";
import type { FitLabel, FitView } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * One category-fit judgement (docs/01_PRODUCT_SPEC.md section 2.6).
 *
 * The wording carries the meaning and the icon reinforces it; colour is never
 * the only signal (docs/02_UX_UI_SPEC.md section 16). "Not enough verified
 * data" is a first-class outcome, not a gap to hide — the beta checklist
 * requires unknown data to stay visible.
 */
const FIT = {
  STRONG: { label: "Strong", icon: Check, tone: "text-positive", surface: "bg-positive-soft" },
  GOOD: { label: "Good", icon: Check, tone: "text-positive", surface: "bg-positive-soft" },
  TRADE_OFF: {
    label: "Trade-off",
    icon: Minus,
    tone: "text-attention",
    surface: "bg-attention-soft",
  },
  NEEDS_ATTENTION: {
    label: "Needs attention",
    icon: TriangleAlert,
    tone: "text-critical",
    surface: "bg-critical-soft",
  },
  UNVERIFIED: {
    label: "Not enough verified data",
    icon: CircleHelp,
    tone: "text-secondary",
    surface: "bg-bg",
  },
} as const satisfies Record<FitLabel, unknown>;

export function FitBadge({ fit }: { fit: FitLabel }) {
  const { label, icon: Icon, tone, surface } = FIT[fit];
  return (
    <span
      className={cn(
        // self-start keeps the badge hugging its text inside a column layout;
        // without it a flex parent stretches it into a full-width bar.
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

/** A named dimension with its fit and the note explaining it. */
export function FitDimension({ dimension }: { dimension: FitView }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-support font-medium text-primary">{dimension.label}</span>
        <FitBadge fit={dimension.fit} />
      </div>
      <p className="text-support text-secondary">{dimension.note}</p>
    </div>
  );
}

export { AlertTriangle };
