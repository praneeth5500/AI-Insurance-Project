import type { Question, QuestionnaireSession } from "@/lib/api/types";

/** The visible questions in one stage, in definition order. */
export function questionsInStage(session: QuestionnaireSession, stageKey: string): Question[] {
  return session.questions.filter((question) => question.stage === stageKey);
}

/** The stored answer for a question, or undefined when unanswered. */
export function answerFor(session: QuestionnaireSession, questionId: string): unknown {
  return session.answers.find((answer) => answer.questionId === questionId)?.value;
}

/**
 * How an answer reads back to the person who gave it.
 *
 * Option *labels*, never raw stored values — a review that showed
 * `me_spouse` would not be a review.
 */
export function displayAnswer(question: Question, value: unknown): string {
  if (value === undefined || value === null || value === "") return "Not answered";

  if (question.inputType === "BOOLEAN") return value === true ? "Yes" : "No";

  if (question.inputType === "SINGLE_CHOICE") {
    return question.options.find((option) => option.value === value)?.label ?? "Not answered";
  }

  if (question.inputType === "MULTI_CHOICE") {
    if (!Array.isArray(value) || value.length === 0) return "Not answered";
    return value
      .map(
        (item) => question.options.find((option) => option.value === item)?.label ?? String(item),
      )
      .join(", ");
  }

  if (question.inputType === "MONEY") return `₹${Number(value).toLocaleString("en-IN")}`;

  if (question.inputType === "NUMBER") {
    return question.unit ? `${value} ${question.unit}` : String(value);
  }

  return String(value);
}
