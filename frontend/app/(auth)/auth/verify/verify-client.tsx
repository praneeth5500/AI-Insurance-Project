"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorState } from "@/components/feedback/error-state";
import { SkeletonBlock } from "@/components/feedback/skeleton";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { postJson } from "@/lib/api/client";
import type { AppError, CurrentUser } from "@/lib/api/types";

type VerifyState = { status: "verifying" } | { status: "error"; error: AppError };

/**
 * Exchanges the magic-link token for a session.
 *
 * This runs in the browser on purpose: the API sets an httpOnly session cookie
 * on the response, and that cookie has to reach the user's browser. On success
 * we replace the history entry so the token is not left in the address bar or
 * in back-button history.
 */
export function VerifyClient({ token }: { token: string }) {
  const router = useRouter();
  const [state, setState] = useState<VerifyState>({ status: "verifying" });
  const attempted = useRef(false);

  useEffect(() => {
    // A magic link is single-use; React's development double-effect must not
    // burn the token twice and turn a valid link into an error.
    if (attempted.current) return;
    attempted.current = true;

    void (async () => {
      const result = await postJson<CurrentUser>("/api/v1/auth/verify", { token });
      if (result.status === "success") {
        router.replace("/app/home");
      } else {
        setState({ status: "error", error: result.error });
      }
    })();
  }, [token, router]);

  if (state.status === "error") {
    return (
      <ErrorState
        title="This sign-in link didn't work"
        description={state.error.message}
        code={state.error.code}
        {...(state.error.requestId !== null ? { requestId: state.error.requestId } : {})}
        action={<Button onClick={() => router.push("/sign-in")}>Request a new link</Button>}
      />
    );
  }

  return (
    <Card>
      <SkeletonBlock label="Signing you in" lines={2} />
    </Card>
  );
}
