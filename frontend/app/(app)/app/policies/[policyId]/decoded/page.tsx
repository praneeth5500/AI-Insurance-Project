import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { DecoderView } from "@/features/policy/decoder-view";
import { getDecodedPolicy } from "@/lib/auth/policies";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Your policy, decoded — AI Insurance Decision Platform",
};

export default async function DecodedPolicyPage({
  params,
}: {
  params: Promise<{ policyId: string }>;
}) {
  const { policyId } = await params;
  const result = await getDecodedPolicy(policyId);

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load that report"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer width="reading">
      <DecoderView decoded={result.data} />
    </PageContainer>
  );
}
