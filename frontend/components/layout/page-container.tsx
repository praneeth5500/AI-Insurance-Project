import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

/**
 * Horizontal rhythm for page content.
 *
 * `reading` is for a single column of prose or a questionnaire step — one
 * primary decision per screen (docs/02_UX_UI_SPEC.md rule 2). `wide` is for
 * lists and comparisons.
 */
export type PageContainerProps = {
  width?: "reading" | "wide";
  className?: string;
  children: ReactNode;
};

export function PageContainer({ width = "wide", className, children }: PageContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 py-6 sm:px-6 sm:py-8",
        width === "reading" ? "max-w-2xl" : "max-w-6xl",
        className,
      )}
    >
      {children}
    </div>
  );
}
