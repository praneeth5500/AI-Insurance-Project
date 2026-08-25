"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { completeSession } from "@/features/questionnaire/questionnaire-client";
import { ReviewSection } from "@/features/questionnaire/review-section";
import type { QuestionnaireSession } from "@/lib/api/types";

/**
 * The short review before submitting (docs/01_PRODUCT_SPEC.md section 2.4).
 *
 * The specification's button here is "Find my matches". Matching is built in
 * Phase 9, so until then the action says what it actually does. Promising
 * matches that do not exist would be exactly the kind of unsupported UI claim
 * CLAUDE.md forbids.
 */
export function ReviewClient({
  initialSession,
  matchingAvailable,
}: {
  initialSession: QuestionnaireSession;
  matchingAvailable: boolean;
}) {
  const router = useRouter();
  const [session, setSession] = useState(initialSession);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  const submitted = session.status === "COMPLETED";

  async function onSubmit() {
    setSubmitting(true);
    setError(undefined);

    const result = await completeSession(session.id);
    setSubmitting(false);

    if (result.status === "error") {
      setError(result.error.message);
      return;
    }
    setSession(result.data);
    router.refresh();
  }

  if (submitted) {
    return (
      <div className="flex flex-col gap-6">
        <InlineAlert tone="positive" title="Your answers are saved">
          {matchingAvailable
            ? "We're putting your matched options together."
            : "Matched options are being built. Nothing has been shared with any insurer."}
        </InlineAlert>
        {session.stages.map((stage) => (
          <ReviewSection key={stage.key} session={session} stage={stage} />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {session.stages.map((stage) => (
        <ReviewSection key={stage.key} session={session} stage={stage} />
      ))}

      {!session.isComplete ? (
        <InlineAlert tone="attention" title="Some answers are still needed">
          Use the Edit links above to finish the sections that are incomplete.
        </InlineAlert>
      ) : null}

      {error ? (
        <InlineAlert tone="critical" title="We couldn't save your answers">
          {error}
        </InlineAlert>
      ) : null}

      <Card>
        <div className="flex flex-col gap-3">
          <p className="text-support text-secondary">
            {matchingAvailable
              ? "We'll use these answers to find options that fit what matters to you."
              : "Your answers are stored privately. Matched options are being built, so nothing is recommended yet."}
          </p>
          <Button
            size="lg"
            onClick={onSubmit}
            disabled={!session.isComplete || submitting}
            loading={submitting}
          >
            {matchingAvailable ? "Find my matches" : "Save my answers"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
