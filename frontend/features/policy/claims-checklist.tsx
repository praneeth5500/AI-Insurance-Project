"use client";

import { FileText } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Card } from "@/components/ui/card";
import { apiBaseUrl } from "@/lib/api/client";
import type { ChecklistItem, ClaimsChecklist } from "@/lib/api/types";

/**
 * Claims readiness (`docs/01_PRODUCT_SPEC.md` section 3.6).
 *
 * The product boundary is stated on the page, not just in the code: this
 * prepares documents and questions, and **does not predict whether a claim
 * will be paid**.
 *
 * The three groups are rendered as three separate sections with their own
 * headings and their own explanation of what they are — and, for the general
 * group, what they are *not*. `docs/07_POLICY_DECODER_AI.md` section 10 says
 * not to blend them, and a single list with small labels is blending with
 * extra steps.
 */

function ItemRow({
  item,
  policyId,
  onChange,
  onOptimisticToggle,
}: {
  item: ChecklistItem;
  policyId: string;
  onChange: (next: ClaimsChecklist) => void;
  onOptimisticToggle: (itemId: string, completed: boolean) => void;
}) {
  const [note, setNote] = useState(item.userNote ?? "");
  const [showSource, setShowSource] = useState(false);
  const [failed, setFailed] = useState(false);

  async function patch(body: Record<string, unknown>) {
    setFailed(false);
    try {
      const response = await fetch(
        `${apiBaseUrl()}/api/v1/policies/${policyId}/claims-checklist/${item.id}`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (response.ok) {
        onChange((await response.json()) as ClaimsChecklist);
        return true;
      }
    } catch {
      // fall through to the failure path
    }
    setFailed(true);
    return false;
  }

  async function toggle(completed: boolean) {
    // Ticked immediately. A checkbox that waits for a round trip before it
    // moves feels broken, and someone working through this at a hospital
    // admission desk is not on a good connection.
    onOptimisticToggle(item.id, completed);
    const ok = await patch({ completed });
    if (!ok) onOptimisticToggle(item.id, !completed);
  }

  return (
    <li className="flex flex-col gap-2 border-b border-control-border py-4 last:border-b-0">
      <label className="flex min-h-touch cursor-pointer items-start gap-3">
        <input
          type="checkbox"
          checked={item.completed}
          onChange={(event) => void toggle(event.target.checked)}
          className="mt-1 size-5 shrink-0 rounded border-control-border accent-accent"
        />
        <span className="flex flex-col gap-1">
          <span
            className={
              item.completed
                ? "text-support font-medium text-secondary line-through"
                : "text-support font-medium text-primary"
            }
          >
            {item.label}
          </span>
          <span className="text-support text-secondary">{item.description}</span>
        </span>
      </label>

      {item.source ? (
        <div className="flex flex-col gap-2 pl-8">
          <button
            type="button"
            onClick={() => setShowSource((open) => !open)}
            aria-expanded={showSource}
            className="inline-flex min-h-touch items-center gap-1 self-start text-support text-accent underline"
          >
            <FileText className="size-4" aria-hidden="true" />
            View source wording · Page {item.source.page}
            {item.source.clauseTitle ? ` · ${item.source.clauseTitle}` : ""}
          </button>
          {showSource ? (
            <blockquote className="whitespace-pre-wrap border-l-2 border-accent bg-bg p-3 text-meta text-secondary">
              {item.source.clauseText}
            </blockquote>
          ) : null}
        </div>
      ) : null}

      {failed ? (
        <p role="alert" className="pl-8 text-meta text-critical">
          We couldn&apos;t save that. Your change has been undone — please try again.
        </p>
      ) : null}

      <div className="flex flex-col gap-1 pl-8">
        <label htmlFor={`note-${item.id}`} className="text-meta text-secondary">
          Your note
        </label>
        <input
          id={`note-${item.id}`}
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
          onBlur={() => {
            if (note !== (item.userNote ?? "")) void patch({ note });
          }}
          placeholder="e.g. policy number, who you spoke to"
          className="min-h-touch rounded-control border border-control-border bg-surface px-3 text-support text-primary placeholder:text-secondary"
        />
      </div>
    </li>
  );
}

export function ClaimsChecklistView({ initial }: { initial: ClaimsChecklist }) {
  const [checklist, setChecklist] = useState(initial);

  /** Move one item locally, and keep the counter honest while it saves. */
  function toggleLocally(itemId: string, completed: boolean) {
    setChecklist((current) => {
      let delta = 0;
      const groups = current.groups.map((group) => ({
        ...group,
        items: group.items.map((item) => {
          if (item.id !== itemId || item.completed === completed) return item;
          delta += completed ? 1 : -1;
          return { ...item, completed };
        }),
      }));
      return { ...current, groups, completedCount: current.completedCount + delta };
    });
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-h2 font-semibold text-primary sm:text-h1">Getting ready to claim</h1>
        <p className="text-body text-secondary">
          For {checklist.displayName}. {checklist.completedCount} of {checklist.totalCount} done.
        </p>
      </div>

      <InlineAlert tone="info" title="What this is">
        {checklist.disclaimer}
      </InlineAlert>

      {checklist.groups.map((group) => (
        <section key={group.origin} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h2 className="text-h2 font-semibold text-primary">{group.label}</h2>
            {/* The explanation is what keeps the groups from blending: it says
                what this group is, and for the general one, what it isn't. */}
            <p className="text-support text-secondary">{group.explanation}</p>
          </div>
          <Card>
            <ul className="flex flex-col">
              {group.items.map((item) => (
                <ItemRow
                  key={item.id}
                  item={item}
                  policyId={checklist.policyId}
                  onChange={setChecklist}
                  onOptimisticToggle={toggleLocally}
                />
              ))}
            </ul>
          </Card>
        </section>
      ))}

      <Link
        href={`/app/policies/${checklist.policyId}/decoded`}
        className="inline-flex min-h-touch items-center self-start text-support text-accent underline"
      >
        Back to your policy summary
      </Link>
    </div>
  );
}
