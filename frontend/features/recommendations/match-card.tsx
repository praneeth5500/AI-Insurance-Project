"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { FitBadge, FitDimension } from "@/features/recommendations/fit-dimension";
import { PriceDisplay } from "@/features/recommendations/price-display";
import { WatchOut } from "@/features/recommendations/watch-out";
import type { MatchView } from "@/lib/api/types";
import { cn } from "@/lib/ui/cn";

/**
 * One matched option (docs/01_PRODUCT_SPEC.md section 2.5,
 * docs/02_UX_UI_SPEC.md section 8).
 *
 * Card contract: insurer + product, 3 strongest fit areas, 1 watch-out, price
 * state, "Why this matches", compare, view details. No overall score appears
 * anywhere — the specification forbids a 0–100 consumer number.
 *
 * "View details" opens the product detail screen, carrying the reader's
 * priorities so it leads with the same strengths this card shows.
 */
export function MatchCard({
  match,
  position,
  selected,
  onToggleCompare,
  compareDisabled,
  moved,
  detailHref,
  onOpenDetail = () => {},
}: {
  match: MatchView;
  position: number;
  selected: boolean;
  onToggleCompare: () => void;
  compareDisabled: boolean;
  /** Highlighted after a priority change, so a reordering is visible. */
  moved: boolean;
  detailHref: string;
  /** Fired when the reader opens the option in full. */
  onOpenDetail?: () => void;
}) {
  const [showWhy, setShowWhy] = useState(false);
  const whyId = `why-${match.id}`;

  return (
    <Card
      className={cn("flex flex-col gap-4", moved && "border-accent")}
      emphasis={moved ? "raised" : "flat"}
    >
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-meta text-secondary">Option {position}</span>
          {match.sourceType === "SYNTHETIC" ? (
            <span className="rounded-control bg-attention-soft px-2 py-0.5 text-meta font-medium text-primary">
              Demo product
            </span>
          ) : null}
          {moved ? (
            <span className="rounded-control bg-accent-soft px-2 py-0.5 text-meta font-medium text-accent">
              Moved
            </span>
          ) : null}
        </div>
        <h3 className="text-h3 font-medium text-primary">
          {match.insurerName} · {match.productName}
        </h3>
      </div>

      {/* The 3 strongest fit areas. */}
      <ul className="flex flex-col gap-1.5">
        {match.highlights.map((highlight) => (
          <li key={highlight.factor} className="flex flex-wrap items-center gap-2">
            <span className="text-support text-primary">{highlight.label}</span>
            <FitBadge fit={highlight.fit} />
          </li>
        ))}
      </ul>

      <WatchOut text={match.watchOut} />

      <PriceDisplay price={match.price} />

      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <button
          type="button"
          onClick={() => setShowWhy((value) => !value)}
          aria-expanded={showWhy}
          aria-controls={whyId}
          className="flex min-h-touch items-center gap-1.5 self-start text-support font-medium text-accent hover:underline"
        >
          Why this matches
          <ChevronDown
            className={cn("size-4 transition-transform duration-fast", showWhy && "rotate-180")}
            aria-hidden="true"
          />
        </button>

        {showWhy ? (
          <div id={whyId} className="flex flex-col gap-3">
            {match.fits.map((fit) => (
              <FitDimension key={fit.factor} dimension={fit} />
            ))}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex min-h-touch cursor-pointer items-center gap-2 text-support text-primary">
            <input
              type="checkbox"
              checked={selected}
              disabled={compareDisabled && !selected}
              onChange={onToggleCompare}
              className="size-5 accent-accent"
            />
            Compare
            <span className="sr-only">
              {" "}
              {match.insurerName} {match.productName}
            </span>
          </label>

          <Link
            href={detailHref}
            onClick={onOpenDetail}
            className="flex min-h-touch items-center text-support font-medium text-accent underline"
          >
            View details
            <span className="sr-only">
              {" "}
              for {match.insurerName} {match.productName}
            </span>
          </Link>
        </div>
      </div>
    </Card>
  );
}
