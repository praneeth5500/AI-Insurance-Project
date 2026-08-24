import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session";

/**
 * A cheap first gate on `/app/*`.
 *
 * This only checks that a session cookie *exists*, which is not proof that it
 * is valid — it saves an unauthenticated visitor a pointless round trip and
 * nothing more. The real check is `requireUser()` in the protected layout,
 * which asks the API on every request. Never rely on this alone for access
 * control.
 */
export function middleware(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE_NAME)) return NextResponse.next();

  const signIn = new URL("/sign-in", request.url);
  // Remember where they were headed so sign-in can return them there.
  signIn.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(signIn);
}

export const config = {
  matcher: ["/app/:path*"],
};
