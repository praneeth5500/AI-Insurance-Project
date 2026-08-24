import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { apiBaseUrl } from "@/lib/api/client";
import type { CurrentUser } from "@/lib/api/types";

/**
 * Server-side session resolution.
 *
 * The session is an httpOnly cookie set by the API, so the browser holds it
 * but no page script can read it. On the server we forward the cookie header
 * explicitly rather than relying on `credentials: "include"`, which has no
 * meaning outside a browser.
 *
 * The cookie's *presence* is never treated as proof of a session: the API is
 * the only thing that knows whether it is valid, unexpired, unrevoked and
 * still allowlisted.
 */
export const SESSION_COOKIE_NAME = "insurance_session";

export async function getCurrentUser(): Promise<CurrentUser | null> {
  const cookieStore = await cookies();
  const session = cookieStore.get(SESSION_COOKIE_NAME);
  if (!session) return null;

  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/me`, {
      headers: {
        Accept: "application/json",
        Cookie: `${SESSION_COOKIE_NAME}=${session.value}`,
      },
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as CurrentUser;
  } catch {
    // API unreachable. Treated as "not signed in" so a protected page fails
    // closed rather than rendering as though the user were authenticated.
    return null;
  }
}

/** Require a session, or send the visitor to sign in. */
export async function requireUser(): Promise<CurrentUser> {
  const user = await getCurrentUser();
  if (user === null) redirect("/sign-in");
  return user;
}
