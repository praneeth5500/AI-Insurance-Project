import { SignOutButton } from "@/components/auth/sign-out-button";
import { ErrorState } from "@/components/feedback/error-state";
import { PageContainer } from "@/components/layout/page-container";
import { DemoDataNotice } from "@/features/home/demo-data-notice";
import { NewUserHome } from "@/features/home/new-user-home";
import { ReturningHome } from "@/features/home/returning-home";
import { getHomeSummary } from "@/lib/auth/home";

export const metadata = {
  title: "Home — AI Insurance Decision Platform",
};

export const dynamic = "force-dynamic";

/**
 * The signed-in home.
 *
 * A user with no activity sees the new-user home; a user with activity sees
 * their own. Which one is decided by the API summary, not guessed at here.
 */
export default async function HomePage() {
  const result = await getHomeSummary();

  if (result.status === "error") {
    return (
      <PageContainer width="reading">
        <ErrorState
          title="We couldn't load your home screen"
          description={result.error.message}
          code={result.error.code}
          {...(result.error.requestId !== null ? { requestId: result.error.requestId } : {})}
        />
      </PageContainer>
    );
  }

  const summary = result.data;

  return (
    <PageContainer>
      <div className="flex flex-col gap-8">
        {summary.dataMode === "DEMO" ? <DemoDataNotice /> : null}

        {summary.isNewUser ? (
          <NewUserHome features={summary.features} />
        ) : (
          <ReturningHome summary={summary} />
        )}

        <footer className="flex items-center justify-between gap-4 border-t border-border pt-6">
          <p className="text-meta text-secondary">
            Invite-only beta. No insurance data is shown that the product cannot support.
          </p>
          <SignOutButton />
        </footer>
      </div>
    </PageContainer>
  );
}
