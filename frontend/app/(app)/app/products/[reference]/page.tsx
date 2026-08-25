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
 * `from` and `priorities` are optional context from the results screen, so the
 * page opens on the same three strengths the match card showed and can offer a
 * way back. Without them the page still works — it is a real, linkable URL.
 */
export default async function ProductDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ reference: string }>;
  searchParams: Promise<{ from?: string; priorities?: string }>;
}) {
  const { reference } = await params;
  const { from, priorities } = await searchParams;

  const chosen = (priorities ?? "").split(",").filter(Boolean);
  const result = await getProductDetail(reference, chosen);

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
