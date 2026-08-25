import { TriangleAlert } from "lucide-react";

/**
 * The one thing to be aware of about an option.
 *
 * docs/02_UX_UI_SPEC.md rule 4: every policy detail needs a "what to watch out
 * for", because trust requires discussing disadvantages. It is never
 * collapsed behind a disclosure — it sits on the card at the same level as
 * the strengths.
 */
export function WatchOut({ text }: { text: string }) {
  return (
    <div className="flex gap-2 rounded-card bg-attention-soft p-3">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-attention" aria-hidden="true" />
      <div className="flex flex-col gap-0.5">
        <p className="text-meta font-semibold text-primary">Watch out for</p>
        <p className="text-support text-primary">{text}</p>
      </div>
    </div>
  );
}
