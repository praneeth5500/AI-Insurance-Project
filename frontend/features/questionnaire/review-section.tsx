import Link from "next/link";
import { Card } from "@/components/ui/card";
import { displayAnswer, questionsInStage } from "@/features/questionnaire/session";
import type { QuestionnaireSession, QuestionnaireStage } from "@/lib/api/types";

/**
 * One stage's answers on the review screen.
 *
 * docs/01_PRODUCT_SPEC.md section 2.4: "User can edit each section." The edit
 * link goes back to that stage, which is why the flow has a route per stage.
 *
 * Answers are shown as the labels the person chose, never as stored values.
 */
export function ReviewSection({
  session,
  stage,
}: {
  session: QuestionnaireSession;
  stage: QuestionnaireStage;
}) {
  const questions = questionsInStage(session, stage.key);
  if (questions.length === 0) return null;

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-h3 font-medium text-primary">{stage.label}</h2>
        <Link
          href={`/app/recommend/health/${stage.key}`}
          className="flex min-h-touch items-center text-support font-medium text-accent underline"
        >
          {/* The whole name lives in one string so it cannot be reflowed into
              "EditYour cover"; the visible word is the aria-hidden one. */}
          <span aria-hidden="true">Edit</span>
          <span className="sr-only">Edit {stage.label}</span>
        </Link>
      </div>

      <dl className="flex flex-col gap-3">
        {questions.map((question) => {
          const answer = session.answers.find((a) => a.questionId === question.id)?.value;
          return (
            <div key={question.id} className="flex flex-col gap-0.5">
              <dt className="text-support text-secondary">{question.title}</dt>
              <dd className="text-body text-primary">{displayAnswer(question, answer)}</dd>
            </div>
          );
        })}
      </dl>
    </Card>
  );
}
