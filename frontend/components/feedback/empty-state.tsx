import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

/**
 * Shown when there is genuinely nothing to display yet.
 *
 * An empty state should say what would fill it and offer the action that
 * does so — the home screen rule is "do not render empty irrelevant modules"
 * (docs/02_UX_UI_SPEC.md section 6), so if there is no useful action here,
 * the module should not be rendered at all.
 */
export type EmptyStateProps = {
  icon?: LucideIcon;
  title: string;
  description?: string;
  /** The action that resolves the emptiness. */
  action?: ReactNode;
  className?: string;
};

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-card border border-border",
        "bg-surface px-6 py-10 text-center",
        className,
      )}
    >
      {Icon ? (
        <span className="flex size-11 items-center justify-center rounded-full bg-accent-soft">
          <Icon className="size-5 text-accent" aria-hidden="true" />
        </span>
      ) : null}
      <div className="flex flex-col gap-1">
        <p className="text-h3 font-medium text-primary">{title}</p>
        {description ? (
          <p className="mx-auto max-w-prose text-support text-secondary">{description}</p>
        ) : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
