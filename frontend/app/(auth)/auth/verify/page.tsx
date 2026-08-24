import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import Link from "next/link";
import { buttonClassName } from "@/components/ui/button";
import { VerifyClient } from "@/app/(auth)/auth/verify/verify-client";

export const metadata = {
  title: "Signing you in — AI Insurance Decision Platform",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function VerifyPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;

  return (
    <PageContainer width="reading">
      <div className="mx-auto flex max-w-md flex-col gap-6 py-8">
        <h1 className="text-h2 font-semibold text-primary">Signing you in</h1>

        {token ? (
          <VerifyClient token={token} />
        ) : (
          <ErrorState
            title="This link is incomplete"
            description="The sign-in link is missing its token. Links can be truncated by some email clients — requesting a new one usually fixes it."
            action={
              <Link href="/sign-in" className={buttonClassName()}>
                Request a new link
              </Link>
            }
          />
        )}
      </div>
    </PageContainer>
  );
}
