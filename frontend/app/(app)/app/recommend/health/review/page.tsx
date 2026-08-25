import Link from "next/link";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { ProgressStage } from "@/components/feedback/progress-stage";
import { ReviewClient } from "@/features/questionnaire/review-client";
import { REVIEW_STAGE_LABEL } from "@/features/questionnaire/questionnaire-shell";
import { startOrResumeServerSide } from "@/lib/auth/questionnaire";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Review your answers — AI Insurance Decision Platform",
};

/**
 * The short review before submitting (docs/01_PRODUCT_SPEC.md section 2.4).
 *
 * `Review` is the fourth stage in docs/02_UX_UI_SPEC.md section 7's progress
 * indicator but has no questions of its own, so it is appended here rather
 * than living in the question set.
 */
export default async function HealthReviewPage() {
  const result = await startOrResumeServerSide();

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load your answers"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  const session = result.data;
  const stageLabels = [...session.stages.map((stage) => stage.label), REVIEW_STAGE_LABEL];

  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-8">
        <ProgressStage stages={stageLabels} currentIndex={stageLabels.length - 1} />

        <PageHeader
          title="Review your answers"
          description="Check anything that looks wrong before you finish. You can edit each section."
        />

        {/* Matching is Phase 9. Until it exists the review says so rather than
            promising results the product cannot produce. */}
        <ReviewClient initialSession={session} matchingAvailable={false} />

        <p className="text-meta text-secondary">
          <Link href="/app/home" className="text-accent underline">
            Back to home
          </Link>
        </p>
      </div>
    </PageContainer>
  );
}
