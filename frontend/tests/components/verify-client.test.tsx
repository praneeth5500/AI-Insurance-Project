import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VerifyClient } from "@/app/(auth)/auth/verify/verify-client";

const replace = vi.fn();
const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  replace.mockClear();
  push.mockClear();
});

function mockVerify(response: { ok: boolean; status: number; body: unknown }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: async () => response.body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("VerifyClient", () => {
  it("exchanges the token and sends the user to the app", async () => {
    const fetchMock = mockVerify({
      ok: true,
      status: 200,
      body: { id: "usr_1", email: "a@b.com", hasProfile: false, betaAccess: true },
    });

    render(<VerifyClient token="tok_123" />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app/home"));
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/v1/auth/verify");
    expect(JSON.parse(init.body as string)).toEqual({ token: "tok_123" });
  });

  it("exchanges the token only once, so a single-use link is not burned twice", async () => {
    const fetchMock = mockVerify({
      ok: true,
      status: 200,
      body: { id: "usr_1", email: "a@b.com", hasProfile: false, betaAccess: true },
    });

    const { rerender } = render(<VerifyClient token="tok_123" />);
    rerender(<VerifyClient token="tok_123" />);

    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows a recoverable error for an expired or used link", async () => {
    mockVerify({
      ok: false,
      status: 400,
      body: {
        error: {
          code: "SIGN_IN_LINK_INVALID",
          message: "This sign-in link is no longer valid. Request a new one to continue.",
          retryable: false,
          requestId: "req_xyz",
        },
      },
    });

    render(<VerifyClient token="expired" />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("no longer valid");
    expect(alert.textContent).toContain("SIGN_IN_LINK_INVALID");
    expect(replace).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Request a new link" })).toBeDefined();
  });

  it("announces that it is working rather than showing a blank screen", () => {
    mockVerify({ ok: true, status: 200, body: {} });

    render(<VerifyClient token="tok" />);

    expect(screen.getByRole("status").textContent).toContain("Signing you in");
  });
});
