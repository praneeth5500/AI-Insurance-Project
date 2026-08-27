"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { track } from "@/lib/analytics/track";
import { cn } from "@/lib/ui/cn";

/**
 * "Why we're asking this" (docs/02_UX_UI_SPEC.md rule 3).
 *
 * A native `<details>`-style disclosure built from a button and a region, so
 * the expanded/collapsed state is announced and keyboard operable. The answer
 * is static copy from the question definition — there is no AI here.
 */
export function HelpDisclosure({
  helpText,
  questionId,
}: {
  helpText: string;
  /** Which question needed explaining. Never the answer to it. */
  questionId?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => {
          // Which questions people need help understanding.
          if (!open && questionId) track("question_help_opened", { question_id: questionId });
          setOpen((value) => !value);
        }}
        aria-expanded={open}
        className={cn(
          "flex min-h-touch items-center gap-1.5 self-start rounded-control",
          "text-support font-medium text-accent",
          "transition-colors duration-fast hover:underline",
        )}
      >
        Why we&apos;re asking this
        <ChevronDown
          className={cn("size-4 transition-transform duration-fast", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      {open ? (
        <p className="max-w-prose rounded-card bg-accent-soft p-4 text-support text-primary">
          {helpText}
        </p>
      ) : null}
    </div>
  );
}
