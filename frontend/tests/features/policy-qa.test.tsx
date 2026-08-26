import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AskPanel } from "@/features/policy/ask-panel";
import type { QaAnswer, QaConversation, QaMessage } from "@/lib/api/types";

afterEach(() => vi.unstubAllGlobals());

function assistant(overrides: Partial<QaMessage> = {}): QaMessage {
  return {
    id: "msg_2",
    role: "ASSISTANT",
    content: "I can't explain this in my own words yet…",
    answerState: "UNAVAILABLE",
    citations: [
      {
        ordinal: 0,
        page: 14,
        clauseTitle: "WAITING PERIODS",
        clauseText: "Pre-existing diseases are covered after a waiting period of 36 months.",
      },
    ],
    createdAt: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

function conversation(overrides: Partial<QaConversation> = {}): QaConversation {
  return { policyId: "pol_1", messages: [], explanationAvailable: false, ...overrides };
}

function mockApi(body: unknown, ok = true) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue({ ok, status: ok ? 200 : 422, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("AskPanel", () => {
  it("says what kind of answer it can give before the reader types", () => {
    // Told up front, not discovered after reading an answer that sounds like
    // a photocopier.
    render(<AskPanel conversation={conversation()} />);

    const notice = screen.getByRole("status");
    expect(notice.textContent).toContain("can't yet explain them in its own words");
    expect(notice.textContent).toContain("you'll get the wording");
  });

  it("does not show that notice once explanation is available", () => {
    render(<AskPanel conversation={conversation({ explanationAvailable: true })} />);

    expect(screen.queryByRole("status")).toBeNull();
  });

  it("says answers come only from the uploaded document", () => {
    render(<AskPanel conversation={conversation()} />);

    expect(screen.getByText(/only from the document you uploaded/)).toBeDefined();
  });

  it("warns that it can be wrong and is not advice", () => {
    render(<AskPanel conversation={conversation()} />);

    const caveat = screen.getByText(/isn't advice, and it can be wrong/);
    expect(caveat.textContent).toContain("check with your insurer");
  });

  it("offers a starting point rather than a blank box", async () => {
    const fetchMock = mockApi({ message: assistant(), quotedNotExplained: true } as QaAnswer);
    const user = userEvent.setup();
    render(<AskPanel conversation={conversation()} />);

    await user.click(
      screen.getByRole("button", { name: /waiting period for pre-existing conditions/ }),
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const [, init] = fetchMock.mock.calls[0]!;
    expect(JSON.parse(init.body as string).question).toContain("waiting period");
  });

  it("shows the wording an answer was based on", async () => {
    mockApi({ message: assistant(), quotedNotExplained: true } as QaAnswer);
    const user = userEvent.setup();
    render(<AskPanel conversation={conversation()} />);

    await user.type(screen.getByLabelText("Your question"), "waiting period?");
    await user.click(screen.getByRole("button", { name: /^Ask$/ }));

    await waitFor(() =>
      expect(screen.getByText(/Based on this part of your policy/)).toBeDefined(),
    );
    expect(screen.getByText(/Page 14 · WAITING PERIODS/)).toBeDefined();
    expect(
      screen.getByText("Pre-existing diseases are covered after a waiting period of 36 months."),
    ).toBeDefined();
  });

  it("shows a refusal as its own answer, with nothing cited", async () => {
    mockApi({
      message: assistant({
        content: "I couldn't determine that from the policy you uploaded.",
        answerState: "INSUFFICIENT_EVIDENCE",
        citations: [],
      }),
      quotedNotExplained: false,
    } as QaAnswer);
    const user = userEvent.setup();
    render(<AskPanel conversation={conversation()} />);

    await user.type(screen.getByLabelText("Your question"), "which dentist?");
    await user.click(screen.getByRole("button", { name: /^Ask$/ }));

    await waitFor(() =>
      expect(screen.getByText(/couldn't determine that from the policy/)).toBeDefined(),
    );
    expect(screen.queryByText(/Based on/)).toBeNull();
  });

  it("keeps the reader's own question visible while it waits", async () => {
    mockApi({ message: assistant(), quotedNotExplained: true } as QaAnswer);
    const user = userEvent.setup();
    render(<AskPanel conversation={conversation()} />);

    await user.type(screen.getByLabelText("Your question"), "room rent limit?");
    await user.click(screen.getByRole("button", { name: /^Ask$/ }));

    expect(screen.getByText("room rent limit?")).toBeDefined();
  });

  it("removes the pending question and explains when the request fails", async () => {
    mockApi(
      { error: { code: "QUESTION_REJECTED", message: "We couldn't use that question." } },
      false,
    );
    const user = userEvent.setup();
    render(<AskPanel conversation={conversation()} />);

    await user.type(screen.getByLabelText("Your question"), "x".repeat(20));
    await user.click(screen.getByRole("button", { name: /^Ask$/ }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
    expect(screen.getByRole("alert").textContent).toContain("couldn't use that question");
  });

  it("labels who said what for a screen reader", () => {
    render(
      <AskPanel
        conversation={conversation({
          messages: [
            {
              ...assistant({
                id: "m1",
                role: "USER",
                content: "hi",
                citations: [],
                answerState: null,
              }),
            },
            assistant(),
          ],
        })}
      />,
    );

    expect(screen.getByText("You asked")).toBeDefined();
    expect(screen.getByText("The assistant answered")).toBeDefined();
  });
});
