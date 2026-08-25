import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HelpDisclosure } from "@/features/questionnaire/help-disclosure";
import { QuestionInput } from "@/features/questionnaire/question-input";
import { QuestionnaireShell } from "@/features/questionnaire/questionnaire-shell";
import { ReviewClient } from "@/features/questionnaire/review-client";
import { displayAnswer } from "@/features/questionnaire/session";
import type { Question, QuestionnaireSession } from "@/lib/api/types";

const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh, replace: vi.fn() }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockClear();
  refresh.mockClear();
});

function question(overrides: Partial<Question> = {}): Question {
  return {
    id: "cover_for",
    stage: "current-cover",
    title: "Who are you looking to protect?",
    description: null,
    inputType: "SINGLE_CHOICE",
    options: [
      { value: "just_me", label: "Just me", description: null },
      { value: "me_spouse", label: "Me + spouse", description: null },
    ],
    required: true,
    dataField: "cover_for",
    helpText: null,
    maxSelections: null,
    unit: null,
    minValue: null,
    maxValue: null,
    sensitive: false,
    ...overrides,
  };
}

function session(overrides: Partial<QuestionnaireSession> = {}): QuestionnaireSession {
  return {
    id: "qs_1",
    domain: "HEALTH",
    questionnaireVersion: "health-beta-draft-001",
    status: "IN_PROGRESS",
    startedAt: "2026-08-01T00:00:00Z",
    completedAt: null,
    definitionStatus: "DRAFT",
    stages: [
      { key: "about-you", label: "About you", questionIds: [], complete: false },
      { key: "current-cover", label: "Your cover", questionIds: ["cover_for"], complete: false },
      { key: "priorities", label: "What matters", questionIds: [], complete: false },
    ],
    questions: [question()],
    answers: [],
    currentStage: "current-cover",
    nextQuestionId: "cover_for",
    isComplete: false,
    ...overrides,
  };
}

function mockApi(body: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({ ok, status, json: async () => body });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

// ------------------------------------------------------------ input types --

describe("QuestionInput", () => {
  it("renders a single choice as radios", () => {
    render(<QuestionInput question={question()} value={null} onChange={vi.fn()} />);

    expect(screen.getAllByRole("radio")).toHaveLength(2);
  });

  it("renders yes/no for a boolean question", () => {
    render(
      <QuestionInput
        question={question({ id: "has_personal_cover", inputType: "BOOLEAN", options: [] })}
        value={null}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("radio", { name: "Yes" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "No" })).toBeDefined();
  });

  it("reports true and false, not strings, for a boolean question", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <QuestionInput
        question={question({ id: "has_personal_cover", inputType: "BOOLEAN", options: [] })}
        value={null}
        onChange={onChange}
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Yes" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("caps a multi-choice question at its limit", async () => {
    const user = userEvent.setup();
    const multi = question({
      id: "priorities",
      inputType: "MULTI_CHOICE",
      maxSelections: 2,
      options: [
        { value: "a", label: "A", description: null },
        { value: "b", label: "B", description: null },
        { value: "c", label: "C", description: null },
      ],
    });

    render(<QuestionInput question={multi} value={["a", "b"]} onChange={vi.fn()} />);

    // Already-chosen options stay operable so a choice can be swapped.
    expect((screen.getByRole("checkbox", { name: "A" }) as HTMLInputElement).disabled).toBe(false);
    expect((screen.getByRole("checkbox", { name: "C" }) as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(/Choose up to 2\. 2 chosen\./)).toBeDefined();

    await user.click(screen.getByText("C"));
    // The disabled option cannot be added past the cap.
    expect(screen.getByRole("checkbox", { name: "C" })).toBeDefined();
  });

  it("strips non-digits from a pincode", async () => {
    const user = userEvent.setup();
    // A controlled input needs its value fed back, or every keystroke is
    // applied to an empty string and the assertion tests nothing.
    function Fixture() {
      const [value, setValue] = useState<unknown>("");
      return (
        <QuestionInput
          question={question({ id: "pincode", inputType: "PINCODE", options: [] })}
          value={value}
          onChange={setValue}
        />
      );
    }

    render(<Fixture />);
    const field = screen.getByLabelText(/Who are you looking to protect/);

    await user.type(field, "5a6b0");
    expect((field as HTMLInputElement).value).toBe("560");
  });

  it("shows a currency prefix for a money question", () => {
    render(
      <QuestionInput
        question={question({ id: "budget", inputType: "MONEY", options: [] })}
        value={null}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText("₹")).toBeDefined();
  });
});

// ------------------------------------------------------------------- help --

describe("HelpDisclosure", () => {
  it("is collapsed until asked, and reports its state", async () => {
    const user = userEvent.setup();
    render(<HelpDisclosure helpText="Age affects eligibility." />);

    const trigger = screen.getByRole("button", { name: /Why we're asking this/ });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByText("Age affects eligibility.")).toBeNull();

    await user.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Age affects eligibility.")).toBeDefined();
  });
});

// ------------------------------------------------------------------ shell --

describe("QuestionnaireShell", () => {
  it("shows one question, as the page heading", () => {
    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Who are you looking to protect?" }),
    ).toBeDefined();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("blocks Continue until a required question is answered", async () => {
    const user = userEvent.setup();
    mockApi(session());
    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    const submit = screen.getByRole("button", { name: "Continue" });
    expect((submit as HTMLButtonElement).disabled).toBe(true);

    await user.click(screen.getByRole("radio", { name: "Just me" }));
    expect((screen.getByRole("button", { name: "Continue" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it("saves the answer and moves on when the stage is finished", async () => {
    const user = userEvent.setup();
    const fetchMock = mockApi(session());
    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Just me" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/questionnaire-sessions/qs_1/answers/cover_for");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ value: "just_me" });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/next"));
  });

  it("uses the server's recomputed session, so branching stays server-side", async () => {
    const user = userEvent.setup();
    const revealed = session({
      questions: [
        question(),
        question({
          id: "spouse_age",
          title: "How old is your spouse?",
          inputType: "NUMBER",
          options: [],
          dataField: "spouse_age",
        }),
      ],
      answers: [{ questionId: "cover_for", value: "me_spouse" }],
    });
    mockApi(revealed);

    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Me + spouse" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));

    // The newly revealed question appears; the client did not decide that.
    expect(
      await screen.findByRole("heading", { level: 1, name: "How old is your spouse?" }),
    ).toBeDefined();
    expect(push).not.toHaveBeenCalled();
  });

  it("surfaces a save failure without losing the answer", async () => {
    const user = userEvent.setup();
    mockApi(
      {
        error: {
          code: "INVALID_ANSWER",
          message: "Choose one of the options shown.",
          retryable: false,
          requestId: "req_1",
        },
      },
      false,
      422,
    );

    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    await user.click(screen.getByRole("radio", { name: "Just me" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Choose one of the options shown.",
    );
    expect(push).not.toHaveBeenCalled();
    expect((screen.getByRole("radio", { name: "Just me" }) as HTMLInputElement).checked).toBe(true);
  });

  it("lets an optional question be skipped", () => {
    const optional = session({
      questions: [question({ required: false })],
    });

    render(
      <QuestionnaireShell
        initialSession={optional}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    expect((screen.getByRole("button", { name: "Continue" }) as HTMLButtonElement).disabled).toBe(
      false,
    );
    expect(screen.getByText("You can skip this question.")).toBeDefined();
  });

  it("tells the user their answers are saved as they go", () => {
    render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    expect(screen.getByText(/saved as you go/)).toBeDefined();
  });

  it("shows stage progress without a percentage", () => {
    const { container } = render(
      <QuestionnaireShell
        initialSession={session()}
        stageKey="current-cover"
        nextHref="/next"
        previousHref="/prev"
      />,
    );

    expect(screen.getByText(/Step 2 of 4\. Current stage: Your cover\./)).toBeDefined();
    expect(container.textContent).not.toMatch(/%/);
  });
});

// ----------------------------------------------------------------- review --

describe("displayAnswer", () => {
  it("shows the chosen label, never the stored value", () => {
    expect(displayAnswer(question(), "me_spouse")).toBe("Me + spouse");
  });

  it("lists every choice for a multi-select", () => {
    const multi = question({
      inputType: "MULTI_CHOICE",
      options: [
        { value: "a", label: "Low co-pay", description: null },
        { value: "b", label: "Broad coverage", description: null },
      ],
    });

    expect(displayAnswer(multi, ["b", "a"])).toBe("Broad coverage, Low co-pay");
  });

  it("says so plainly when nothing was answered", () => {
    expect(displayAnswer(question(), null)).toBe("Not answered");
  });
});

describe("ReviewClient", () => {
  const answered = session({
    answers: [{ questionId: "cover_for", value: "just_me" }],
    isComplete: true,
  });

  it("shows each section with a link to edit it", () => {
    render(<ReviewClient initialSession={answered} matchingAvailable={false} />);

    const link = screen.getByRole("link", { name: /Edit Your cover/ });
    expect(link.getAttribute("href")).toBe("/app/recommend/health/current-cover");
    expect(screen.getByText("Just me")).toBeDefined();
  });

  it("does not promise matches while matching is not built", () => {
    render(<ReviewClient initialSession={answered} matchingAvailable={false} />);

    expect(screen.getByRole("button", { name: "Save my answers" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Find my matches" })).toBeNull();
  });

  it("uses the specified wording once matching exists", () => {
    render(<ReviewClient initialSession={answered} matchingAvailable />);

    expect(screen.getByRole("button", { name: "Find my matches" })).toBeDefined();
  });

  it("blocks submission while answers are missing", () => {
    render(
      <ReviewClient initialSession={session({ isComplete: false })} matchingAvailable={false} />,
    );

    expect(
      (screen.getByRole("button", { name: "Save my answers" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(screen.getByText(/Some answers are still needed/)).toBeDefined();
  });

  it("confirms submission without claiming anything was shared", async () => {
    const user = userEvent.setup();
    mockApi({ ...answered, status: "COMPLETED" });
    render(<ReviewClient initialSession={answered} matchingAvailable={false} />);

    await user.click(screen.getByRole("button", { name: "Save my answers" }));

    const confirmation = await screen.findByRole("status");
    expect(confirmation.textContent).toContain("Your answers are saved");
    expect(confirmation.textContent).toContain("Nothing has been shared with any insurer");
  });

  it("makes no unsupported insurance claim", () => {
    const { container } = render(
      <ReviewClient initialSession={answered} matchingAvailable={false} />,
    );

    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of ["guarantee", "best policy", "premium is", "approved"]) {
      expect(text).not.toContain(forbidden);
    }
  });
});

describe("review sections", () => {
  it("groups answers under their stage heading", () => {
    const answered = session({ answers: [{ questionId: "cover_for", value: "just_me" }] });
    render(<ReviewClient initialSession={answered} matchingAvailable={false} />);

    const heading = screen.getByRole("heading", { name: "Your cover" });
    const card = heading.closest("[class*='rounded-card']") as HTMLElement;
    expect(within(card).getByText("Just me")).toBeDefined();
  });
});
