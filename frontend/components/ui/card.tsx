import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

export type CardProps = {
  /** Raises the card slightly. Used for the one thing a screen is about. */
  emphasis?: "flat" | "raised";
  padding?: "none" | "compact" | "comfortable";
  className?: string;
  children: ReactNode;
} & Omit<HTMLAttributes<HTMLDivElement>, "className">;

const PADDING = {
  none: "",
  compact: "p-4",
  comfortable: "p-5 sm:p-6",
} as const;

export function Card({
  emphasis = "flat",
  padding = "comfortable",
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        // --border is decorative here, so its low contrast is intentional.
        "rounded-card border border-border bg-surface",
        emphasis === "raised" ? "shadow-raised" : "shadow-card",
        PADDING[padding],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
