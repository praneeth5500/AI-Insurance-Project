"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChoiceCard, ChoiceCardGroup } from "@/components/ui/choice-card";

/**
 * Fine-tuning priorities after results (docs/02_UX_UI_SPEC.md section 9).
 *
 * Raw weights are never exposed. The user re-picks what matters, in the same
 * words as onboarding, and the server re-runs the deterministic ordering —
 * the client never reorders anything itself.
 *
 * Kept to the same "up to 3" model as onboarding. The four-level control the
 * specification also suggests (Less important / Normal / More important /
 * Must have) needs the versioned scoring configuration it feeds, which is
 * Phase 9.
 */
export const PRIORITY_OPTIONS = [
  { value: "lower_premium", label: "Lower premium" },
  { value: "low_copay", label: "Low co-pay" },
  { value: "short_waiting_periods", label: "Short waiting periods" },
  { value: "hospital_flexibility", label: "Hospital flexibility" },
  { value: "broad_coverage", label: "Broad coverage" },
  { value: "fewer_sublimits", label: "Fewer sub-limits" },
] as const;

export const MAX_PRIORITIES = 3;

export function PriorityEditor({
  priorities,
  onApply,
  saving,
}: {
  priorities: readonly string[];
  onApply: (next: string[]) => void;
  saving: boolean;
}) {
  const [draft, setDraft] = useState<string[]>([...priorities]);

  const atLimit = draft.length >= MAX_PRIORITIES;
  const changed =
    draft.length !== priorities.length || draft.some((item, i) => item !== priorities[i]);

  function toggle(value: string) {
    setDraft((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-h3 font-medium text-primary">What matters most to you</h2>
        <p className="text-support text-secondary">
          Change these and the options reorder. Nothing is added or removed — only the order
          changes.
        </p>
      </div>

      <ChoiceCardGroup
        legend="Choose up to 3 things that matter most"
        hideLegend
        columns={2}
        description={`Choose up to ${MAX_PRIORITIES}. ${draft.length} chosen.`}
      >
        {PRIORITY_OPTIONS.map((option) => {
          const checked = draft.includes(option.value);
          return (
            <ChoiceCard
              key={option.value}
              type="checkbox"
              name="priority-editor"
              value={option.value}
              label={option.label}
              checked={checked}
              disabled={!checked && atLimit}
              onChange={() => toggle(option.value)}
            />
          );
        })}
      </ChoiceCardGroup>

      <Button
        onClick={() => onApply(draft)}
        disabled={!changed || draft.length === 0 || saving}
        loading={saving}
      >
        Update my matches
      </Button>
    </Card>
  );
}
