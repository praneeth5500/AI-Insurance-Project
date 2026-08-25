import { redirect } from "next/navigation";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { startOrResumeServerSide } from "@/lib/auth/questionnaire";

export const dynamic = "force-dynamic";

/**
 * Entry point for the health flow.
 *
 * Resumes the user's draft and sends them to the stage they left off in, so
 * "continue where you left off" lands on the right screen rather than
 * restarting the questionnaire.
 */
export default async function HealthQuestionnaireEntry() {
  const result = await startOrResumeServerSide();

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't start your questions"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  const session = result.data;
  if (session.isComplete || session.currentStage === null) {
    redirect("/app/recommend/health/review");
  }
  redirect(`/app/recommend/health/${session.currentStage}`);
}
