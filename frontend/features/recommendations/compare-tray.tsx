"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MatchView } from "@/lib/api/types";

/**
 * The options picked for comparison (docs/01_PRODUCT_SPEC.md section 2.7).
 *
 * Up to 3, which the checkboxes enforce by disabling the rest at the limit.
 * The side-by-side comparison itself is Phase 6, so the action states that
 * plainly instead of leading nowhere.
 */
export const MAX_COMPARE = 3;

export function CompareTray({
  selected,
  onRemove,
  onClear,
}: {
  selected: readonly MatchView[];
  onRemove: (productReference: string) => void;
  onClear: () => void;
}) {
  if (selected.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Selected for comparison"
      className="sticky bottom-20 z-20 mt-6 rounded-card border border-border bg-surface p-4 shadow-raised md:bottom-4"
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-support font-medium text-primary">
            {selected.length} of {MAX_COMPARE} selected to compare
          </p>
          <button
            type="button"
            onClick={onClear}
            className="min-h-touch text-support text-accent underline"
          >
            Clear
          </button>
        </div>

        <ul className="flex flex-wrap gap-2">
          {selected.map((match) => (
            <li key={match.productReference}>
              <button
                type="button"
                onClick={() => onRemove(match.productReference)}
                className="flex min-h-touch items-center gap-1.5 rounded-control bg-bg px-3 text-support text-primary"
              >
                {match.insurerName} · {match.productName}
                <X className="size-4" aria-hidden="true" />
                <span className="sr-only">
                  Remove {match.insurerName} {match.productName} from comparison
                </span>
              </button>
            </li>
          ))}
        </ul>

        <div className="flex flex-col gap-1">
          <Button disabled>Compare side by side</Button>
          <p className="text-meta text-secondary">
            Side-by-side comparison is being built. Your selection is kept while you browse.
          </p>
        </div>
      </div>
    </div>
  );
}
