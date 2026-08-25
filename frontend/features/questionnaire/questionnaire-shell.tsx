"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ProgressStage } from "@/components/feedback/progress-stage";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { PageContainer } from "@/components/layout/page-container";
import { BackContinueBar } from "@/features/questionnaire/back-continue-bar";
import { HelpDisclosure } from "@/features/questionnaire/help-disclosure";
import { QuestionHeader } from "@/features/questionnaire/question-header";
import { QuestionInput } from "@/features/questionnaire/question-input";
import { saveAnswer } from "@/features/questionnaire/questionnaire-client";
import { answerFor, questionsInStage } from "@/features/questionnaire/session";
import type { QuestionnaireSession } from "@/lib/api/types";

/** The final stage in the progress indicator; it has no questions. */
export const REVIEW_STAGE_LABEL = "Review";

/**
 * Walks one stage, one question per screen
 * (docs/02_UX_UI_SPEC.md rule 2).
 *
 * The server owns branching and validation. This component only tracks which
 * question is on screen; every Continue saves the answer and takes the
 * recomputed session back, so a changed answer reshapes the flow immediately
 * without any client-side branching logic.
 */
export function QuestionnaireShell({
  initialSession,
  stageKey,
  nextHref,
  previousHref,
}: {
  initialSession: QuestionnaireSession;
  stageKey: string;
  /** Where Continue goes after the last question in this stage. */
  nextHref: string;
  /** Where Back goes from the first question. Null on the first stage. */
  previousHref: string | null;
}) {
  const router = useRouter();
  const [session, setSession] = useState(initialSession);
  const [index, setIndex] = useState(0);
  const [draft, setDraft] = useState<unknown>(undefined);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  const questions = useMemo(() => questionsInStage(session, stageKey), [session, stageKey]);
  // docs/02_UX_UI_SPEC.md section 7 shows four stages in the progress
  // indicator. Review has no questions of its own, so it is appended here
  // rather than living in the question set — otherwise progress would read
  // "Step 3 of 3" during the questions and "Step 4 of 4" on review.
  const stageLabels = useMemo(
    () => [...session.stages.map((stage) => stage.label), REVIEW_STAGE_LABEL],
    [session.stages],
  );
  const stageIndex = session.stages.findIndex((s) => s.key === stageKey);

  const question = questions[Math.min(index, Math.max(questions.length - 1, 0))];

  if (!question) {
    // A stage can become empty when an earlier answer changes.
    return (
      <PageContainer width="reading">
        <InlineAlert tone="info" title="Nothing to answer here">
          Your earlier answers mean this section doesn&apos;t apply.
        </InlineAlert>
      </PageContainer>
    );
  }

  // Bound after the guard above: narrowing does not reach hoisted closures.
  const activeQuestion = question;
  const stored = answerFor(session, activeQuestion.id);
  const value = draft === undefined ? stored : draft;
  const answered =
    value !== undefined &&
    value !== null &&
    value !== "" &&
    !(Array.isArray(value) && value.length === 0);
  const canContinue = activeQuestion.required ? answered : true;

  async function onContinue() {
    setSaving(true);
    setError(undefined);

    const result = await saveAnswer(session.id, activeQuestion.id, value ?? null);
    setSaving(false);

    if (result.status === "error") {
      setError(result.error.message);
      return;
    }

    setSession(result.data);
    setDraft(undefined);

    // Re-read the stage from the *updated* session: answering may have
    // revealed or hidden questions in this very stage.
    const updated = questionsInStage(result.data, stageKey);
    if (index + 1 < updated.length) {
      setIndex(index + 1);
    } else {
      router.push(nextHref);
    }
  }

  function onBack() {
    setError(undefined);
    setDraft(undefined);
    if (index > 0) {
      setIndex(index - 1);
    } else if (previousHref) {
      router.push(previousHref);
    }
  }

  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-8">
        <ProgressStage stages={stageLabels} currentIndex={Math.max(stageIndex, 0)} />

        <div className="flex flex-col gap-6">
          <QuestionHeader
            title={activeQuestion.title}
            description={activeQuestion.description}
            optional={!activeQuestion.required}
          />

          <QuestionInput
            question={activeQuestion}
            value={value ?? null}
            onChange={(next) => {
              setDraft(next);
              setError(undefined);
            }}
            {...(error ? { error } : {})}
          />

          {activeQuestion.helpText ? <HelpDisclosure helpText={activeQuestion.helpText} /> : null}
        </div>

        <BackContinueBar
          onBack={onBack}
          onContinue={onContinue}
          backDisabled={index === 0 && previousHref === null}
          continueDisabled={!canContinue || saving}
          saving={saving}
        />

        <p className="text-meta text-secondary">
          Your answers are saved as you go. You can leave and come back.
        </p>
      </div>
    </PageContainer>
  );
}
