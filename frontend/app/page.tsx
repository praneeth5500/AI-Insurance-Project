import Link from "next/link";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { apiBaseUrl, getReadiness } from "@/lib/api/client";

// Developer status page. This is NOT the product home screen — the new-user and
// returning-user home in docs/02_UX_UI_SPEC.md sections 5 and 6 is Phase 3
// work. This page deliberately makes no product or insurance claim.
export const dynamic = "force-dynamic";

export default async function DeveloperStatusPage() {
  const readiness = await getReadiness();

  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-6">
        <PageHeader
          title="AI Insurance Decision Platform"
          description="Phase 1 — design system. No product features are implemented yet."
        />

        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-h3 font-medium text-primary">Backend connection</h2>
            <p className="text-support text-secondary">
              API base URL: <code className="text-primary">{apiBaseUrl()}</code>
            </p>

            {readiness.status === "success" ? (
              <InlineAlert tone="positive" title="API ready">
                Database: {readiness.data.dependencies.database}
              </InlineAlert>
            ) : (
              <InlineAlert tone="critical" title="API unavailable">
                <p>{readiness.error.message}</p>
                <p className="mt-1 text-meta">
                  Error code: <code>{readiness.error.code}</code>
                  {readiness.error.requestId !== null ? (
                    <>
                      {" · Reference: "}
                      <code>{readiness.error.requestId}</code>
                    </>
                  ) : null}
                </p>
              </InlineAlert>
            )}
          </div>
        </Card>

        <p className="text-support text-secondary">
          <Link href="/design-system" className="font-medium text-accent underline">
            View the design system
          </Link>
        </p>
      </div>
    </PageContainer>
  );
}
