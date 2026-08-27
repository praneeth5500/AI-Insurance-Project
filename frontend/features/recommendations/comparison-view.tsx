"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ComparisonRow } from "@/features/recommendations/comparison-row";
import { Helpfulness } from "@/features/feedback/helpfulness";
import { WatchOut } from "@/features/recommendations/watch-out";
import { track } from "@/lib/analytics/track";
import type { ComparisonView as Comparison } from "@/lib/api/types";

/**
 * Comparing 2 or 3 options (docs/02_UX_UI_SPEC.md section 10).
 *
 * The section order is the design: biggest differences first, then the
 * dimensions the reader said mattered, then everything else behind a
 * disclosure. Leading with what actually separates the options is what stops
 * this becoming the "giant feature matrix" the specification warns against.
 *
 * Nothing declares a winner. There is no total, no score and no "best"
 * anywhere — the reader decides, which is the entire premise of the product.
 */
export function ComparisonView({ comparison }: { comparison: Comparison }) {
  // How many options were compared, never which. Fired once per mount.
  useEffect(() => {
    track("comparison_viewed", { option_count: comparison.options.length });
  }, [comparison.options.length]);

  const [showAll, setShowAll] = useState(false);

  return (
    <div className="flex flex-col gap-8">
      {comparison.sourceType === "SYNTHETIC" ? (
        <InlineAlert tone="attention" title="Demo products">
          These options are invented for testing this screen. Nothing here describes a real policy.
        </InlineAlert>
      ) : null}

      <Card className="flex flex-col gap-3">
        <h2 className="text-h3 font-medium text-primary">Comparing</h2>
        <ul className="flex flex-col gap-1">
          {comparison.options.map((option) => (
            <li key={option.productReference} className="text-body text-primary">
              {option.insurerName} · {option.productName}
            </li>
          ))}
        </ul>
      </Card>

      <section className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-h2 font-semibold text-primary">Biggest differences</h2>
          <p className="text-support text-secondary">
            Where these options are least alike. Each one is a trade-off, not a verdict.
          </p>
        </div>
        <Card>
          {comparison.biggestDifferences.length === 0 ? (
            <p className="text-support text-secondary">
              These options are alike on every dimension we hold. The details below show what we
              have.
            </p>
          ) : (
            comparison.biggestDifferences.map((dimension) => (
              <ComparisonRow
                key={dimension.factor}
                dimension={dimension}
                options={comparison.options}
              />
            ))
          )}
        </Card>
      </section>

      {comparison.yourPriorities.length > 0 ? (
        <section className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-h2 font-semibold text-primary">Your priorities</h2>
            <p className="text-support text-secondary">
              The things you said matter most, whether or not these options differ on them.
            </p>
          </div>
          <Card>
            {comparison.yourPriorities.map((dimension) => (
              <ComparisonRow
                key={dimension.factor}
                dimension={dimension}
                options={comparison.options}
              />
            ))}
          </Card>
        </section>
      ) : null}

      <section className="flex flex-col gap-3">
        <h2 className="text-h2 font-semibold text-primary">What to watch out for</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {comparison.options.map((option) => (
            <div key={option.productReference} className="flex flex-col gap-1.5">
              <p className="text-support font-medium text-primary">
                {option.insurerName} · {option.productName}
              </p>
              <WatchOut text={option.watchOut} />
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-h2 font-semibold text-primary">All details</h2>
        {/* Progressive disclosure: the full set is available, but it does not
            greet the reader as a wall of cells. */}
        {showAll ? (
          <Card>
            {comparison.allDetails.map((dimension) => (
              <ComparisonRow
                key={dimension.factor}
                dimension={dimension}
                options={comparison.options}
              />
            ))}
          </Card>
        ) : (
          <Button variant="secondary" onClick={() => setShowAll(true)}>
            Show all {comparison.allDetails.length} details
          </Button>
        )}
      </section>

      <Helpfulness
        contextType="COMPARISON"
        contextId={comparison.runId}
        question="Did this comparison make the differences clear?"
      />

      <Link
        href={`/app/recommendations/${comparison.runId}`}
        className="inline-flex min-h-touch items-center self-start text-support text-accent underline"
      >
        Back to your matched options
      </Link>
    </div>
  );
}
