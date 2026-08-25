import { FitBadge } from "@/features/recommendations/fit-dimension";
import { cn } from "@/lib/ui/cn";
import type { ComparisonOptionView, DimensionView } from "@/lib/api/types";

/**
 * One fit dimension across the compared options.
 *
 * Laid out as a stack of option entries, not a table row.
 * docs/01_PRODUCT_SPEC.md section 2.7: "Mobile uses stacked differences, not a
 * wide horizontal table." The same structure widens into columns from `sm`,
 * so there is one layout to reason about rather than two.
 *
 * Every option's name is repeated on each entry so a reader never has to
 * remember which column is which — the failure mode of a feature matrix.
 */
export function ComparisonRow({
  dimension,
  options,
}: {
  dimension: DimensionView;
  options: readonly ComparisonOptionView[];
}) {
  return (
    <div className="flex flex-col gap-2 border-t border-border py-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-support font-semibold text-primary">{dimension.label}</h3>
        {dimension.isPriority ? (
          <span className="rounded-control bg-accent-soft px-2 py-0.5 text-meta font-medium text-accent">
            Your priority
          </span>
        ) : null}
        {!dimension.differs ? (
          <span className="text-meta text-secondary">These options are the same here</span>
        ) : null}
      </div>

      {/* One column on mobile — the specification is explicit that a phone
          must show stacked differences, never a wide horizontal table. */}
      <div className={cn("grid gap-3", options.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2")}>
        {options.map((option) => {
          const value = dimension.values[option.productReference];
          const note = dimension.notes[option.productReference];
          return (
            <div key={option.productReference} className="flex flex-col gap-1">
              <p className="text-meta text-secondary">
                {option.insurerName} · {option.productName}
              </p>
              {value ? <FitBadge fit={value} /> : null}
              {note ? <p className="text-support text-primary">{note}</p> : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
