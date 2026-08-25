"use client";

import { BookOpen, Lightbulb } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/ui/cn";
import type { ProductFactView } from "@/lib/api/types";

/**
 * One technical item, with the two affordances
 * `docs/01_PRODUCT_SPEC.md` section 2.8 requires: **Explain with example** and
 * **View source wording**.
 *
 * Both are disclosures rather than links, so the reader never loses their
 * place. The source disclosure always opens — even when there is no document —
 * because "we have nothing to show you here" is the honest answer for a demo
 * product, and hiding the control would hide that fact too.
 */
export function PolicyFact({ fact }: { fact: ProductFactView }) {
  const [showExample, setShowExample] = useState(false);
  const [showSource, setShowSource] = useState(false);

  const exampleId = `example-${fact.key}`;
  const sourceId = `source-${fact.key}`;

  return (
    <div className="flex flex-col gap-2 border-t border-border py-4 first:border-t-0 first:pt-0">
      <div className="flex flex-col gap-1">
        <h3 className="text-support font-semibold text-primary">{fact.label}</h3>
        <p className="text-body text-primary">{fact.value}</p>
      </div>

      <div className="flex flex-wrap gap-4">
        {fact.example ? (
          <button
            type="button"
            onClick={() => setShowExample((value) => !value)}
            aria-expanded={showExample}
            aria-controls={exampleId}
            className="flex min-h-touch items-center gap-1.5 text-support font-medium text-accent hover:underline"
          >
            <Lightbulb className="size-4" aria-hidden="true" />
            Explain with example
          </button>
        ) : null}

        <button
          type="button"
          onClick={() => setShowSource((value) => !value)}
          aria-expanded={showSource}
          aria-controls={sourceId}
          className={cn(
            "flex min-h-touch items-center gap-1.5 text-support font-medium hover:underline",
            fact.hasSource ? "text-accent" : "text-secondary",
          )}
        >
          <BookOpen className="size-4" aria-hidden="true" />
          View source wording
        </button>
      </div>

      {showExample && fact.example ? (
        <div id={exampleId} className="rounded-card bg-accent-soft p-4">
          {/* Labelled as an example, every time: docs/12_BETA_CHECKLIST.md. */}
          <p className="text-meta font-semibold text-primary">
            Example — explains how this works, not this policy&apos;s terms
          </p>
          <p className="mt-1 text-support text-primary">{fact.example}</p>
        </div>
      ) : null}

      {showSource ? (
        <div id={sourceId} className="rounded-card bg-bg p-4">
          {fact.hasSource ? null : (
            <p className="text-meta font-semibold text-primary">No source wording available</p>
          )}
          <p className="mt-1 text-support text-secondary">{fact.sourceNote}</p>
        </div>
      ) : null}
    </div>
  );
}
