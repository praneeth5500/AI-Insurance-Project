import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Helpfulness } from "@/features/feedback/helpfulness";

afterEach(() => vi.unstubAllGlobals());

function mockFetch() {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Helpfulness", () => {
  it("records a positive rating without demanding an explanation", async () => {
    // Requiring a comment gets far fewer responses, and the count is the
    // signal that generalises.
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    render(<Helpfulness contextType="DECODER" contextId="pol_1" />);

    await user.click(screen.getByRole("button", { name: /Yes/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body as string)).toEqual({
      contextType: "DECODER",
      contextId: "pol_1",
      rating: 1,
    });
    expect(screen.getByRole("status").textContent).toContain("Thanks");
  });

  it("asks what went wrong only when the answer is no", async () => {
    mockFetch();
    const user = userEvent.setup();
    render(<Helpfulness contextType="DECODER" />);

    expect(screen.queryByLabelText(/What was missing/)).toBeNull();

    await user.click(screen.getByRole("button", { name: /No/ }));
    expect(screen.getByLabelText(/What was missing or wrong/)).toBeDefined();
  });

  it("warns that a comment is read by a person", async () => {
    mockFetch();
    const user = userEvent.setup();
    render(<Helpfulness contextType="DECODER" />);

    await user.click(screen.getByRole("button", { name: /No/ }));

    expect(screen.getByText(/this goes to a person/)).toBeDefined();
  });

  it("sends the comment with the negative rating", async () => {
    const fetchMock = mockFetch();
    const user = userEvent.setup();
    render(<Helpfulness contextType="QA_ANSWER" contextId="pol_2" />);

    await user.click(screen.getByRole("button", { name: /No/ }));
    await user.type(screen.getByLabelText(/What was missing or wrong/), "It quoted the wrong page");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body as string)).toEqual({
      contextType: "QA_ANSWER",
      contextId: "pol_2",
      rating: -1,
      comment: "It quoted the wrong page",
    });
  });

  it("never lets a failed submission become the reader's problem", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const user = userEvent.setup();
    render(<Helpfulness contextType="DECODER" />);

    await user.click(screen.getByRole("button", { name: /Yes/ }));

    expect(screen.getByRole("status").textContent).toContain("Thanks");
  });
});
