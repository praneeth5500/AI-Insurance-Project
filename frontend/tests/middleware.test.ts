import { describe, expect, it, vi } from "vitest";

import { config, middleware } from "@/middleware";
import { SESSION_COOKIE_NAME } from "@/lib/auth/session";

vi.mock("next/server", () => ({
  NextResponse: {
    next: () => ({ kind: "next" }),
    redirect: (url: URL) => ({ kind: "redirect", url }),
  },
}));

/** Shape returned by the mocked NextResponse above. */
type Redirect = { kind: string; url: URL };

function request(path: string, hasCookie: boolean) {
  return {
    cookies: { has: (name: string) => hasCookie && name === SESSION_COOKIE_NAME },
    url: `http://localhost:3000${path}`,
    nextUrl: { pathname: path },
  } as unknown as Parameters<typeof middleware>[0];
}

describe("middleware", () => {
  it("guards the authenticated area only", () => {
    expect(config.matcher).toEqual(["/app/:path*"]);
  });

  it("lets a request with a session cookie through", () => {
    expect(middleware(request("/app/home", true))).toEqual({ kind: "next" });
  });

  it("redirects an anonymous visitor to sign in", () => {
    const result = middleware(request("/app/home", false)) as unknown as Redirect;

    expect(result.kind).toBe("redirect");
    expect(result.url.pathname).toBe("/sign-in");
  });

  it("remembers where the visitor was headed", () => {
    const result = middleware(request("/app/policies", false)) as unknown as Redirect;

    expect(result.url.searchParams.get("next")).toBe("/app/policies");
  });
});
