"use client";

import Link from "next/link";
import { X } from "lucide-react";
import { buttonClassName } from "@/components/ui/button";
import type { MatchView } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * The options picked for comparison (docs/01_PRODUCT_SPEC.md section 2.7).
 *
 * Up to 3, which the checkboxes enforce by disabling the rest at the limit —
 * and the API enforces again, since a client is not the place to guarantee a
 * product rule.
 *
 * Comparison needs at least two options, so the action stays inert until a
 * second is picked rather than leading to an empty screen.
 */
export const MAX_COMPARE = 3;

export const MIN_COMPARE = 2;

export function CompareTray({
  selected,
  onRemove,
  onClear,
  runId,
}: {
  selected: readonly MatchView[];
  onRemove: (productReference: string) => void;
  onClear: () => void;
  runId: string;
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
          {selected.length >= MIN_COMPARE ? (
            <Link
              href={`/app/recommendations/${runId}/compare?options=${selected
                .map((match) => encodeURIComponent(match.productReference))
                .join(",")}`}
              className={buttonClassName()}
            >
              Compare side by side
            </Link>
          ) : (
            <>
              <span className={cn(buttonClassName(), "cursor-not-allowed opacity-50")}>
                Compare side by side
              </span>
              <p className="text-meta text-secondary">Pick one more option to compare.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
