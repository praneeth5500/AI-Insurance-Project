import { redirect } from "next/navigation";
import { SignInForm } from "@/app/(auth)/sign-in/sign-in-form";
import { PageContainer } from "@/components/layout/page-container";
import { Card } from "@/components/ui/card";
import { getCurrentUser } from "@/lib/auth/session";

export const metadata = {
  title: "Sign in — AI Insurance Decision Platform",
};

export const dynamic = "force-dynamic";

export default async function SignInPage() {
  // Someone already signed in has no reason to see this screen.
  if (await getCurrentUser()) redirect("/app/home");

  return (
    <PageContainer width="reading">
      <div className="mx-auto flex max-w-md flex-col gap-6 py-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-h2 font-semibold text-primary">Sign in</h1>
          <p className="text-body text-secondary">
            This beta is invite-only. Enter the email address your invite was sent to.
          </p>
        </div>

        <Card>
          <SignInForm />
        </Card>

        <p className="text-support text-secondary">
          Signing in confirms you are using an invited account. We only use your email address to
          identify you.
        </p>
      </div>
    </PageContainer>
  );
}
