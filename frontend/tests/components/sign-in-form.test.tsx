import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SignInForm } from "@/app/(auth)/sign-in/sign-in-form";

function mockPost(response: { ok: boolean; status: number; body: unknown }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: async () => response.body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SignInForm", () => {
  it("labels the email field and marks it required", () => {
    render(<SignInForm />);

    const field = screen.getByLabelText(/Email address/);
    expect(field.getAttribute("type")).toBe("email");
    expect(field.hasAttribute("required")).toBe(true);
    expect(field.getAttribute("autocomplete")).toBe("email");
  });

  it("posts the trimmed address to the magic-link endpoint", async () => {
    const user = userEvent.setup();
    const fetchMock = mockPost({ ok: true, status: 200, body: { status: "SENT_IF_ELIGIBLE" } });
    render(<SignInForm />);

    await user.type(screen.getByLabelText(/Email address/), "  invited@example.com  ");
    await user.click(screen.getByRole("button", { name: /Send my sign-in link/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/v1/auth/request-magic-link");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ email: "invited@example.com" });
    // The session cookie is httpOnly, so credentials must be sent.
    expect(init.credentials).toBe("include");
  });

  it("does not reveal whether the address was on the allowlist", async () => {
    const user = userEvent.setup();
    mockPost({ ok: true, status: 200, body: { status: "SENT_IF_ELIGIBLE" } });
    render(<SignInForm />);

    await user.type(screen.getByLabelText(/Email address/), "someone@example.com");
    await user.click(screen.getByRole("button", { name: /Send my sign-in link/ }));

    const confirmation = await screen.findByRole("status");
    // Conditional wording: it must not claim an email was actually sent.
    expect(confirmation.textContent).toContain("If");
    expect(confirmation.textContent).toContain("is on the beta invite list");
    expect(confirmation.textContent).not.toMatch(/we have sent|your account/i);
  });

  it("announces a failure without losing the entered address", async () => {
    const user = userEvent.setup();
    mockPost({
      ok: false,
      status: 503,
      body: {
        error: {
          code: "SERVICE_UNAVAILABLE",
          message: "The service is temporarily unavailable. Please try again shortly.",
          retryable: true,
          requestId: "req_abc",
        },
      },
    });
    render(<SignInForm />);

    await user.type(screen.getByLabelText(/Email address/), "invited@example.com");
    await user.click(screen.getByRole("button", { name: /Send my sign-in link/ }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("temporarily unavailable");
    expect(alert.textContent).toContain("req_abc");
    expect((screen.getByLabelText(/Email address/) as HTMLInputElement).value).toBe(
      "invited@example.com",
    );
  });

  it("reports a network failure rather than appearing to succeed", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED")));
    render(<SignInForm />);

    await user.type(screen.getByLabelText(/Email address/), "invited@example.com");
    await user.click(screen.getByRole("button", { name: /Send my sign-in link/ }));

    expect((await screen.findByRole("alert")).textContent).toContain("could not reach");
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("lets the user go back and correct their address", async () => {
    const user = userEvent.setup();
    mockPost({ ok: true, status: 200, body: { status: "SENT_IF_ELIGIBLE" } });
    render(<SignInForm />);

    await user.type(screen.getByLabelText(/Email address/), "typo@example.com");
    await user.click(screen.getByRole("button", { name: /Send my sign-in link/ }));
    await screen.findByRole("status");

    await user.click(screen.getByRole("button", { name: /Use a different email/ }));
    expect(screen.getByLabelText(/Email address/)).toBeDefined();
  });
});
