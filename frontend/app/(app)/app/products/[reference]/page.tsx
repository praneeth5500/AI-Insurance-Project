import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { ProductDetailView } from "@/features/product/product-detail-view";
import { getProductDetail } from "@/lib/auth/recommendations";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Option details — AI Insurance Decision Platform",
};

/**
 * Route from `docs/03_FRONTEND_ARCHITECTURE.md` section 2, which names it
 * `/app/products/:productVersionId`. Product versions arrive in Phase 8, so
 * the segment currently carries a synthetic product reference — recorded in
 * `docs/SPEC_ISSUES.md`.
 *
 * `from` names the result set the reader came from. It is what makes the fit
 * block possible: the page renders the judgement that run recorded, so a card
 * and the page behind it can never disagree, and reopening an old result set
 * shows what it said at the time. Without it the page still works — it is a
 * real, linkable URL — and shows the policy's facts alone.
 */
export default async function ProductDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ reference: string }>;
  searchParams: Promise<{ from?: string }>;
}) {
  const { reference } = await params;
  const { from } = await searchParams;

  const result = await getProductDetail(reference, from ?? null);

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load that option"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer width="reading">
      <ProductDetailView product={result.data} runId={from ?? null} />
    </PageContainer>
  );
}
