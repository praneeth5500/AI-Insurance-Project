import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { ProcessingStatus } from "@/features/policy/processing-status";
import { getPolicy } from "@/lib/auth/policies";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Your policy — AI Insurance Decision Platform",
};

/**
 * One uploaded policy.
 *
 * Rendered on the server on every request, so returning to this URL after
 * closing the tab shows the real current stage rather than whatever the
 * browser last held (docs/02_UX_UI_SPEC.md section 14: the reader may leave
 * and return).
 */
export default async function PolicyPage({ params }: { params: Promise<{ policyId: string }> }) {
  const { policyId } = await params;
  const result = await getPolicy(policyId);

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load that policy"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer width="reading">
      <ProcessingStatus policy={result.data} />
    </PageContainer>
  );
}
