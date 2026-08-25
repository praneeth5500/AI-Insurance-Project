import { notFound, redirect } from "next/navigation";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { QuestionnaireShell } from "@/features/questionnaire/questionnaire-shell";
import { startOrResumeServerSide } from "@/lib/auth/questionnaire";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Health cover questions — AI Insurance Decision Platform",
};

/**
 * One stage of the health flow.
 *
 * Routes come from docs/03_FRONTEND_ARCHITECTURE.md section 2
 * (`/about-you`, `/current-cover`, `/priorities`, `/review`). A route per
 * stage is what lets the review screen link back to a single section to edit.
 */
export default async function HealthStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage } = await params;
  const result = await startOrResumeServerSide();

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load your questions"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  const session = result.data;
  if (session.status === "COMPLETED") redirect("/app/recommend/health/review");

  const index = session.stages.findIndex((candidate) => candidate.key === stage);
  if (index === -1) notFound();

  const next = session.stages[index + 1];
  const previous = session.stages[index - 1];

  return (
    <QuestionnaireShell
      initialSession={session}
      stageKey={stage}
      nextHref={next ? `/app/recommend/health/${next.key}` : "/app/recommend/health/review"}
      previousHref={previous ? `/app/recommend/health/${previous.key}` : "/app/home"}
    />
  );
}
