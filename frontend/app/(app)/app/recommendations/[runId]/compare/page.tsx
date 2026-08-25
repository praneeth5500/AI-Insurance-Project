import { redirect } from "next/navigation";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { ComparisonView } from "@/features/recommendations/comparison-view";
import { getComparison } from "@/lib/auth/recommendations";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Comparing your options — AI Insurance Decision Platform",
};

/**
 * Route from docs/03_FRONTEND_ARCHITECTURE.md section 2.
 *
 * The selected options are in the query string, so this page can be reloaded,
 * shared and reached with the back button — a comparison held only in client
 * state would be lost on refresh.
 */
export default async function ComparePage({
  params,
  searchParams,
}: {
  params: Promise<{ runId: string }>;
  searchParams: Promise<{ options?: string }>;
}) {
  const { runId } = await params;
  const { options } = await searchParams;

  const references = (options ?? "").split(",").filter(Boolean);
  if (references.length < 2) {
    // Nothing to compare: send the reader back to pick options.
    redirect(`/app/recommendations/${runId}`);
  }

  const result = await getComparison(runId, references);

  if (result.status === "error") {
    return (
      <PageContainer>
        <ErrorState
          title="We couldn't build that comparison"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="flex flex-col gap-8">
        <PageHeader
          title="Comparing your options"
          description="Differences first, then what you said matters. There is no overall winner here — each option trades something off."
        />
        <ComparisonView comparison={result.data} />
      </div>
    </PageContainer>
  );
}
