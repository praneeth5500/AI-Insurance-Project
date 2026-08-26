import { PageContainer } from "@/components/layout/page-container";
import { UploadZone } from "@/features/policy/upload-zone";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Understand your policy — AI Insurance Decision Platform",
};

/**
 * Upload entry point (docs/01_PRODUCT_SPEC.md section 3.1, home CTA
 * "Understand my existing policy").
 *
 * Reachable only when the decoder feature flag is on: the home card renders
 * as "Coming soon" otherwise, and the API refuses the request regardless, so
 * a stale link cannot start an upload the product cannot finish.
 */
export default function PolicyUploadPage() {
  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-h2 font-semibold text-primary sm:text-h1">
            Understand the policy you already have
          </h1>
          <p className="text-body text-secondary">
            Upload your policy document and we&apos;ll set out what it covers, what it costs you at
            claim time, and what it leaves out — in plain language, with the wording it came from.
          </p>
        </div>

        <UploadZone />
      </div>
    </PageContainer>
  );
}
