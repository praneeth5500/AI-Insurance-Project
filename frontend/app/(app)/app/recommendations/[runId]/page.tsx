import Link from "next/link";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { ResultsClient } from "@/features/recommendations/results-client";
import { getRecommendationRun } from "@/lib/auth/recommendations";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Your matched options — AI Insurance Decision Platform",
};

export default async function RecommendationRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const result = await getRecommendationRun(runId);

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load your matched options"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-8">
        <PageHeader
          title="Your matched options"
          description="Based on the answers you gave. You can change what matters and see the order update."
        />

        <ResultsClient initialRun={result.data} />

        <Link
          href="/app/home"
          className="inline-flex min-h-touch items-center self-start text-support text-accent underline"
        >
          Back to home
        </Link>
      </div>
    </PageContainer>
  );
}
