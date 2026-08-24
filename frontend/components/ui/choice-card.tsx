"use client";

import { Check } from "lucide-react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

/**
 * The large tappable option cards the onboarding flow is built from
 * (docs/02_UX_UI_SPEC.md section 7).
 *
 * Implemented as a real `<input type="radio">` / `<input type="checkbox">`
 * inside its `<label>`, so arrow-key navigation, roving focus, form
 * participation and screen-reader semantics come from the browser rather than
 * from hand-written ARIA.
 */
export type ChoiceCardProps = {
  label: string;
  description?: string;
  /** "radio" for one-of-many, "checkbox" for many-of-many. */
  type?: "radio" | "checkbox";
} & Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "type">;

export function ChoiceCard({
  label,
  description,
  type = "radio",
  disabled,
  ...props
}: ChoiceCardProps) {
  return (
    <label
      className={cn(
        "group relative flex min-h-touch cursor-pointer items-start gap-3 rounded-card",
        "border border-control-border bg-surface p-4",
        "transition-[border-color,background-color] duration-fast ease-standard",
        "hover:bg-accent-soft/40",
        "has-[:checked]:border-accent has-[:checked]:bg-accent-soft",
        "has-[:focus-visible]:outline has-[:focus-visible]:outline-2",
        "has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <input type={type} disabled={disabled} className="sr-only" {...props} />

      {/* Selection is shown by a mark as well as by colour, never colour alone. */}
      <span
        aria-hidden="true"
        className={cn(
          "mt-0.5 flex size-5 shrink-0 items-center justify-center border border-control-border",
          "bg-surface text-surface transition-colors duration-fast ease-standard",
          "group-has-[:checked]:border-accent group-has-[:checked]:bg-accent",
          type === "radio" ? "rounded-full" : "rounded-[6px]",
        )}
      >
        <Check className="size-3.5 opacity-0 group-has-[:checked]:opacity-100" strokeWidth={3} />
      </span>

      <span className="flex flex-col gap-0.5">
        <span className="text-body font-medium text-primary">{label}</span>
        {description ? <span className="text-support text-secondary">{description}</span> : null}
      </span>
    </label>
  );
}

export type ChoiceCardGroupProps = {
  /** The question the options answer. Rendered as the group's legend. */
  legend: string;
  /** Hide the legend visually while keeping it for screen readers. */
  hideLegend?: boolean;
  description?: string;
  error?: string;
  columns?: 1 | 2;
  children: ReactNode;
};

export function ChoiceCardGroup({
  legend,
  hideLegend = false,
  description,
  error,
  columns = 1,
  children,
}: ChoiceCardGroupProps) {
  return (
    <fieldset className="flex flex-col gap-3 border-0 p-0">
      <legend className={cn("text-h3 font-medium text-primary", hideLegend && "sr-only")}>
        {legend}
      </legend>
      {description ? <p className="text-support text-secondary">{description}</p> : null}
      <div className={cn("grid gap-3", columns === 2 ? "sm:grid-cols-2" : "grid-cols-1")}>
        {children}
      </div>
      {error ? (
        <p role="alert" className="text-support text-critical">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
