"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { postJson } from "@/lib/api/client";

/**
 * Ends the session.
 *
 * The API revokes the session row and clears the cookie; `router.refresh()`
 * then discards the cached server render so no signed-in content survives the
 * sign-out on screen.
 */
export function SignOutButton() {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function onSignOut() {
    setSigningOut(true);
    // Sign-out is idempotent server-side, so a failed response still means the
    // safest thing to do is send the user to the sign-in screen.
    await postJson("/api/v1/auth/sign-out", {});
    router.replace("/sign-in");
    router.refresh();
  }

  return (
    <Button variant="secondary" onClick={onSignOut} loading={signingOut}>
      Sign out
    </Button>
  );
}
