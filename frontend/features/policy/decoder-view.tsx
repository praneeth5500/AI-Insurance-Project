import Link from "next/link";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Card } from "@/components/ui/card";
import { AskPanel } from "@/features/policy/ask-panel";
import { FactCard } from "@/features/policy/fact-card";
import type { DecodedPolicy, QaConversation } from "@/lib/api/types";

/**
 * The decoder report (`docs/02_UX_UI_SPEC.md` section 12,
 * `docs/01_PRODUCT_SPEC.md` section 3.4).
 *
 * `docs/02_UX_UI_SPEC.md` section 12 asks for a 65/35 split on desktop —
 * report on the left, assistant on the right — and a full-width report on
 * mobile with the assistant opening separately. That is what this does, and
 * the assistant only appears when a conversation was actually loaded.
 *
 * The report opens by saying what it could *not* determine. A decoder that
 * leads with its findings and buries its gaps reads as more complete than it
 * is, and someone deciding whether their policy covers them deserves the
 * limits up front.
 */
export function DecoderView({
  decoded,
  conversation,
}: {
  decoded: DecodedPolicy;
  /** Null when the conversation could not be loaded; the report still reads. */
  conversation: QaConversation | null;
}) {
  const hasGaps = decoded.unknownCount > 0 || decoded.conflictingCount > 0;

  return (
    <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:gap-10">
      <div className="flex min-w-0 flex-col gap-8 lg:w-[65%]">
        <div className="flex flex-col gap-2">
          <h1 className="text-h2 font-semibold text-primary sm:text-h1">{decoded.displayName}</h1>
          <p className="text-body text-secondary">
            What we could read from the document you uploaded, in plain language, with the wording
            each point came from.
          </p>
        </div>

        <InlineAlert tone="info" title="What this is, and isn't">
          This is our reading of your document, not advice and not a substitute for it. Every point
          below links to the wording it came from — if something matters to you, read the wording
          and check with your insurer.
        </InlineAlert>

        {hasGaps ? (
          <InlineAlert tone="attention" title="What we couldn't determine">
            <ul className="flex list-disc flex-col gap-1 pl-4">
              {decoded.unknownCount > 0 ? (
                <li>
                  {decoded.unknownCount === 1
                    ? "1 thing we looked for isn't stated in a way we recognised."
                    : `${decoded.unknownCount} things we looked for aren't stated in a way we recognised.`}
                </li>
              ) : null}
              {decoded.conflictingCount > 0 ? (
                <li>
                  {decoded.conflictingCount === 1
                    ? "1 point is stated more than once with different answers."
                    : `${decoded.conflictingCount} points are stated more than once with different answers.`}
                </li>
              ) : null}
              {decoded.unreadClauseCount > 0 ? (
                <li>
                  This report covers the points we know how to read. Your policy has{" "}
                  {decoded.unreadClauseCount} other{" "}
                  {decoded.unreadClauseCount === 1 ? "section" : "sections"} we haven&apos;t
                  summarised.
                </li>
              ) : null}
            </ul>
          </InlineAlert>
        ) : null}

        {decoded.sections.map((section) => (
          <section key={section.key} className="flex flex-col gap-4">
            <h2 className="text-h2 font-semibold text-primary">{section.label}</h2>
            <div className="flex flex-col gap-4">
              {section.facts.map((fact) => (
                <FactCard key={fact.factKey} fact={fact} />
              ))}
            </div>
          </section>
        ))}

        <section className="flex flex-col gap-3">
          <h2 className="text-h2 font-semibold text-primary">How this was produced</h2>
          <Card className="flex flex-col gap-2">
            <p className="text-support text-secondary">
              Read by: <span className="text-primary">{decoded.aiProvider ?? "no AI model"}</span>
            </p>
            <p className="text-support text-secondary">
              Reader version: <span className="text-primary">{decoded.schemaVersion ?? "—"}</span>
            </p>
            <p className="text-meta text-secondary">
              {decoded.aiProvider === null
                ? "This report was produced by fixed rules reading your document — no AI model was involved, and every point above quotes the wording it came from."
                : "An AI model helped produce this report. Every point above still quotes the wording it came from."}
            </p>
          </Card>
        </section>

        <Link
          href={`/app/policies/${decoded.policyId}`}
          className="inline-flex min-h-touch items-center self-start text-support text-accent underline"
        >
          Back to this policy
        </Link>
      </div>

      {conversation ? (
        <aside className="flex min-w-0 flex-col lg:sticky lg:top-6 lg:w-[35%]">
          <AskPanel conversation={conversation} />
        </aside>
      ) : null}
    </div>
  );
}
