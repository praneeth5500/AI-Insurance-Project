import { cn } from "@/lib/ui/cn";

/**
 * A loading placeholder.
 *
 * Purely decorative and hidden from assistive technology — use
 * `SkeletonBlock`'s `label` so screen readers hear a status message instead of
 * silence (docs/02_UX_UI_SPEC.md section 16).
 *
 * The pulse is suppressed under prefers-reduced-motion by the global rule in
 * app/globals.css.
 */
export type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={cn("block animate-pulse rounded-control bg-border", className)}
    />
  );
}

export type SkeletonTextProps = {
  lines?: number;
  className?: string;
};

export function SkeletonText({ lines = 3, className }: SkeletonTextProps) {
  return (
    <span className={cn("flex flex-col gap-2", className)}>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton
          key={index}
          // A ragged last line reads as text rather than as a solid block.
          className={cn("h-4", index === lines - 1 ? "w-2/3" : "w-full")}
        />
      ))}
    </span>
  );
}

export type SkeletonBlockProps = {
  /** Announced while content loads, e.g. "Loading your matched options". */
  label: string;
  lines?: number;
  className?: string;
};

export function SkeletonBlock({ label, lines = 3, className }: SkeletonBlockProps) {
  return (
    <div role="status" aria-live="polite" className={className}>
      <span className="sr-only">{label}</span>
      <SkeletonText lines={lines} />
    </div>
  );
}
