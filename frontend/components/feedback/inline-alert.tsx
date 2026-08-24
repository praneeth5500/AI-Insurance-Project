import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

export type AlertTone = "info" | "positive" | "attention" | "critical";

/**
 * An in-page message.
 *
 * Tone is carried by an icon and a wording label as well as by colour, never
 * by colour alone (docs/02_UX_UI_SPEC.md section 16).
 *
 * Body text inside a soft-tinted container always uses --text-primary. The
 * tone colours are reserved for the icon and the rule: --attention on
 * --attention-soft is 4.34:1, below the 4.5:1 needed for body text. See
 * docs/PHASE_1_NOTES.md.
 */
const TONE = {
  info: {
    icon: Info,
    surface: "bg-accent-soft border-accent",
    iconColor: "text-accent",
    defaultLabel: "Information",
  },
  positive: {
    icon: CheckCircle2,
    surface: "bg-positive-soft border-positive",
    iconColor: "text-positive",
    defaultLabel: "Confirmed",
  },
  attention: {
    icon: AlertTriangle,
    surface: "bg-attention-soft border-attention",
    iconColor: "text-attention",
    defaultLabel: "Worth checking",
  },
  critical: {
    icon: XCircle,
    surface: "bg-critical-soft border-critical",
    iconColor: "text-critical",
    defaultLabel: "Problem",
  },
} as const;

export type InlineAlertProps = {
  tone?: AlertTone;
  /** Visible heading. When omitted, the tone's default wording is used. */
  title?: string;
  children?: ReactNode;
};

export function InlineAlert({ tone = "info", title, children }: InlineAlertProps) {
  const { icon: Icon, surface, iconColor, defaultLabel } = TONE[tone];
  const heading = title ?? defaultLabel;

  return (
    <div
      // Critical messages interrupt; the rest are polite.
      role={tone === "critical" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-card border-l-2 p-4", surface)}
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", iconColor)} aria-hidden="true" />
      <div className="flex flex-col gap-1 text-primary">
        <p className="text-support font-semibold">{heading}</p>
        {children ? <div className="text-support">{children}</div> : null}
      </div>
    </div>
  );
}
