"use client";

import { useMemo, useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { CompareTray, MAX_COMPARE } from "@/features/recommendations/compare-tray";
import { DecisionProfileSummary } from "@/features/recommendations/decision-profile-summary";
import { MatchCard } from "@/features/recommendations/match-card";
import { PriorityEditor, PRIORITY_OPTIONS } from "@/features/recommendations/priority-editor";
import { requestJson } from "@/lib/api/client";
import type { MatchView, RecommendationRun } from "@/lib/api/types";

/**
 * The results screen (docs/02_UX_UI_SPEC.md section 8).
 *
 * Order: what we learned → matched options (5) → see 5 more → priority
 * editor. No overall score is shown anywhere; every card carries its own
 * strengths and one watch-out.
 */
export function ResultsClient({ initialRun }: { initialRun: RecommendationRun }) {
  const [run, setRun] = useState(initialRun);
  const [showMore, setShowMore] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [reorderNote, setReorderNote] = useState<string | undefined>(undefined);

  const visible = useMemo(
    () => (showMore ? [...run.matches, ...run.additionalMatches] : run.matches),
    [run, showMore],
  );

  const allMatches = useMemo(() => [...run.matches, ...run.additionalMatches], [run]);

  const selectedMatches = useMemo(
    () =>
      selected
        .map((reference) => allMatches.find((m) => m.productReference === reference))
        .filter((m): m is MatchView => m !== undefined),
    [selected, allMatches],
  );

  function toggleCompare(productReference: string) {
    setSelected((current) =>
      current.includes(productReference)
        ? current.filter((item) => item !== productReference)
        : current.length >= MAX_COMPARE
          ? current
          : [...current, productReference],
    );
  }

  async function applyPriorities(next: string[]) {
    setSaving(true);
    setError(undefined);

    const result = await requestJson<RecommendationRun>(
      `/api/v1/recommendation-runs/${run.id}/priorities`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ priorities: next }),
      },
    );
    setSaving(false);

    if (result.status === "error") {
      setError(result.error.message);
      return;
    }

    setRun(result.data);
    // docs/02_UX_UI_SPEC.md section 9: a changed priority must visibly
    // explain why the results changed.
    const labels = next
      .map((value) => PRIORITY_OPTIONS.find((option) => option.value === value)?.label)
      .filter(Boolean)
      .join(", ");
    setReorderNote(
      result.data.reordered.length === 0
        ? `Your priorities are now ${labels}. The order didn't change.`
        : `Reordered for ${labels}. ${result.data.reordered.length} option${
            result.data.reordered.length === 1 ? "" : "s"
          } moved.`,
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {run.sourceType === "SYNTHETIC" ? (
        <InlineAlert tone="attention" title="Demo products">
          These options are invented for testing this screen. The insurers and products are not
          real, no prices are shown, and nothing here is a recommendation to buy.
        </InlineAlert>
      ) : null}

      <DecisionProfileSummary lines={run.decisionProfile} />

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-h2 font-semibold text-primary">Matched options</h2>
          <p className="text-support text-secondary">
            Ordered by what you said matters. There is no single best option — each one trades
            something off.
          </p>
        </div>

        {reorderNote ? (
          <InlineAlert tone="info" title="Your results updated">
            {reorderNote}
          </InlineAlert>
        ) : null}

        <ul className="flex flex-col gap-4">
          {visible.map((match, index) => (
            <li key={match.id}>
              <MatchCard
                match={match}
                position={index + 1}
                selected={selected.includes(match.productReference)}
                onToggleCompare={() => toggleCompare(match.productReference)}
                compareDisabled={selected.length >= MAX_COMPARE}
                moved={run.reordered.includes(match.productReference)}
                detailHref={`/app/products/${match.productReference}?from=${run.id}&priorities=${run.priorities.join(",")}`}
              />
            </li>
          ))}
        </ul>

        {run.canShowMore && !showMore ? (
          <Button variant="secondary" onClick={() => setShowMore(true)}>
            See {run.additionalMatches.length} more matches
          </Button>
        ) : null}
      </section>

      {error ? (
        <InlineAlert tone="critical" title="We couldn't update your matches">
          {error}
        </InlineAlert>
      ) : null}

      <PriorityEditor priorities={run.priorities} onApply={applyPriorities} saving={saving} />

      <CompareTray
        selected={selectedMatches}
        onRemove={(reference) =>
          setSelected((current) => current.filter((item) => item !== reference))
        }
        onClear={() => setSelected([])}
        runId={run.id}
      />
    </div>
  );
}
