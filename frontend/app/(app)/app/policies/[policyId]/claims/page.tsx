import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { ClaimsChecklistView } from "@/features/policy/claims-checklist";
import { getClaimsChecklist } from "@/lib/auth/policies";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Getting ready to claim — AI Insurance Decision Platform",
};

export default async function ClaimsChecklistPage({
  params,
}: {
  params: Promise<{ policyId: string }>;
}) {
  const { policyId } = await params;
  const result = await getClaimsChecklist(policyId);

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load that checklist"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer width="reading">
      <ClaimsChecklistView initial={result.data} />
    </PageContainer>
  );
}
