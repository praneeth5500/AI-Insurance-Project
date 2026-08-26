"use client";

import { ChevronDown, FileText } from "lucide-react";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { ConfidenceBadge } from "@/features/policy/confidence-badge";
import type { FactCard as FactCardData } from "@/lib/api/types";

/**
 * One decoded fact (`docs/07_POLICY_DECODER_AI.md` section 6).
 *
 * The section fixes the shape: a plain-language title, what it means, an
 * example, important conditions, the technical term, and the source. All six
 * are present on every card, including cards where the value is unknown —
 * an unknown that still explains what the thing *is* leaves the reader better
 * off than a blank.
 *
 * "View source wording" is always rendered when a clause exists, and the
 * quote is shown verbatim. This is the control that makes the rest of the
 * card checkable, so it is never hidden behind a hover or a tooltip.
 */
export function FactCard({ fact }: { fact: FactCardData }) {
  const [showSource, setShowSource] = useState(false);
  const [showExample, setShowExample] = useState(false);

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-h3 font-medium text-primary">{fact.title}</h3>
          <ConfidenceBadge state={fact.confidenceState} />
        </div>

        {fact.statement ? (
          <p className="text-body text-primary">{fact.statement}</p>
        ) : fact.confidenceState === "CONFLICTING" ? (
          <p className="text-body text-primary">
            Your policy states this more than once, and the statements don&apos;t agree. We
            haven&apos;t picked one — both are below, with where each appears.
          </p>
        ) : (
          <p className="text-body text-secondary">
            We couldn&apos;t find this in the document you uploaded. That doesn&apos;t mean it
            isn&apos;t there — it may be worded in a way we don&apos;t recognise yet. It is worth
            checking the wording or asking your insurer directly.
          </p>
        )}
      </div>

      {fact.alternatives.length > 0 ? (
        <ul className="flex flex-col gap-2 rounded-card bg-critical-soft p-3">
          {fact.alternatives.map((alternative, index) => (
            <li key={`${alternative.page}-${index}`} className="flex flex-col gap-1">
              <span className="text-meta font-medium text-primary">Page {alternative.page}</span>
              <q className="text-support text-secondary">{alternative.quote}</q>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => setShowExample((open) => !open)}
          aria-expanded={showExample}
          className="inline-flex min-h-touch items-center gap-1 self-start text-support text-accent underline"
        >
          Explain with an example
          <ChevronDown
            className={showExample ? "size-4 rotate-180" : "size-4"}
            aria-hidden="true"
          />
        </button>
        {showExample ? (
          <div className="flex flex-col gap-1 rounded-card bg-bg p-3">
            {/* Labelled as an example, and about policies in general — never
                a statement about the reader's own policy. */}
            <p className="text-meta font-medium text-secondary">
              Example — this explains how it works, not your policy&apos;s terms
            </p>
            <p className="text-support text-secondary">{fact.example}</p>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-1 border-t border-control-border pt-3">
        <p className="text-meta font-medium text-secondary">Worth checking</p>
        <p className="text-support text-secondary">{fact.conditions}</p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-meta text-secondary">
          Technical term: <span className="text-primary">{fact.technicalTerm}</span>
        </p>

        {fact.citation ? (
          <>
            <button
              type="button"
              onClick={() => setShowSource((open) => !open)}
              aria-expanded={showSource}
              className="inline-flex min-h-touch items-center gap-1 self-start text-support text-accent underline"
            >
              <FileText className="size-4" aria-hidden="true" />
              View source wording · Page {fact.citation.page}
              {fact.citation.clauseTitle ? ` · ${fact.citation.clauseTitle}` : ""}
            </button>
            {showSource ? (
              <blockquote className="flex flex-col gap-2 border-l-2 border-accent bg-bg p-3">
                <p className="text-support text-primary">{fact.citation.quote}</p>
                {fact.citation.clauseText && fact.citation.clauseText !== fact.citation.quote ? (
                  <details>
                    <summary className="min-h-touch cursor-pointer text-meta text-accent">
                      Show the whole clause
                    </summary>
                    <p className="whitespace-pre-wrap pt-2 text-meta text-secondary">
                      {fact.citation.clauseText}
                    </p>
                  </details>
                ) : null}
              </blockquote>
            ) : null}
          </>
        ) : (
          <p className="text-meta text-secondary">
            No source to show — we didn&apos;t find this stated in the document.
          </p>
        )}
      </div>
    </Card>
  );
}
