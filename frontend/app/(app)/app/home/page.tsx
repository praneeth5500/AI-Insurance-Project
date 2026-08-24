import { SignOutButton } from "@/components/auth/sign-out-button";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { requireUser } from "@/lib/auth/session";

export const metadata = {
  title: "Home — AI Insurance Decision Platform",
};

export const dynamic = "force-dynamic";

/**
 * Placeholder home.
 *
 * The real new-user and returning-user home screens in
 * docs/02_UX_UI_SPEC.md sections 5 and 6 are Phase 3. This page exists so that
 * Phase 2 has a protected destination to protect, and deliberately makes no
 * product claim and offers no feature that does not exist.
 */
export default async function HomePage() {
  const user = await requireUser();

  return (
    <PageContainer width="reading">
      <div className="flex flex-col gap-6">
        <PageHeader
          title="You're signed in"
          description="Your session is active. The product home screen is built in the next phase."
          actions={<SignOutButton />}
        />

        <Card>
          <div className="flex flex-col gap-2">
            <h2 className="text-h3 font-medium text-primary">Account</h2>
            <p className="text-support text-secondary">
              Signed in as <span className="text-primary">{user.email}</span>
            </p>
            <p className="text-support text-secondary">
              Beta access: {user.betaAccess ? "active" : "inactive"}
            </p>
          </div>
        </Card>

        <InlineAlert tone="info" title="Nothing to do here yet">
          Finding insurance and understanding an existing policy are built in later phases. No
          insurance data exists in this build.
        </InlineAlert>
      </div>
    </PageContainer>
  );
}
