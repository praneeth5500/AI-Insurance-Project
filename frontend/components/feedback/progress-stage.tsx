import { cn } from "@/lib/ui/cn";

/**
 * The subtle top progress indicator for a staged flow
 * (docs/02_UX_UI_SPEC.md section 7): a thin bar plus the current stage name.
 *
 * Deliberately shows stage position, not a percentage. The onboarding flow has
 * no fixed question count (docs/13_DECISIONS_AND_OPEN_ITEMS.md), so a
 * percentage would be a number the product cannot honestly support.
 */
export type ProgressStageProps = {
  /** Ordered stage names, e.g. About you / Your cover / What matters / Review. */
  stages: readonly string[];
  /** Zero-based index of the stage the user is on. */
  currentIndex: number;
  className?: string;
};

export function ProgressStage({ stages, currentIndex, className }: ProgressStageProps) {
  const total = stages.length;
  const safeIndex = Math.min(Math.max(currentIndex, 0), Math.max(total - 1, 0));
  const current = stages[safeIndex];

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* The bar is decorative; the text below carries the same information. */}
      <div aria-hidden="true" className="flex gap-1.5">
        {stages.map((stage, index) => (
          <span
            key={stage}
            className={cn(
              "h-1 flex-1 rounded-full transition-colors duration-base ease-standard",
              index <= safeIndex ? "bg-accent" : "bg-border",
            )}
          />
        ))}
      </div>

      <p className="text-support text-secondary">
        {/* Announced as one sentence; the visible line below is the same
            information arranged for the eye, so it is hidden from readers. */}
        <span className="sr-only">
          {`Step ${safeIndex + 1} of ${total}. Current stage: ${current}.`}
        </span>
        <span aria-hidden="true">
          <span className="font-medium text-primary">{current}</span>
          {` · Step ${safeIndex + 1} of ${total}`}
        </span>
      </p>
    </div>
  );
}
