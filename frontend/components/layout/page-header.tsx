import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

/**
 * The title block at the top of a page.
 *
 * Renders the page's single `h1`. Anything above it — progress, breadcrumbs —
 * goes in `above` so the heading order stays correct.
 */
export type PageHeaderProps = {
  title: string;
  description?: string;
  /** Content rendered before the heading, e.g. a ProgressStage. */
  above?: ReactNode;
  /** Actions aligned with the heading on wider screens. */
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({ title, description, above, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {above}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-h2 font-semibold text-primary sm:text-h1">{title}</h1>
          {description ? (
            <p className="max-w-prose text-body text-secondary">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
