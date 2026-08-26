"use client";

import { FileText, Send } from "lucide-react";
import { useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiBaseUrl } from "@/lib/api/client";
import type { QaAnswer, QaCitation, QaConversation, QaMessage } from "@/lib/api/types";

/**
 * Ask about this policy (`docs/01_PRODUCT_SPEC.md` section 3.5,
 * `docs/02_UX_UI_SPEC.md` section 12).
 *
 * Two things this panel does that an ordinary chat box does not:
 *
 * * **It says up front what kind of answer it can give.** While no model is
 *   configured the assistant quotes the policy rather than explaining it, and
 *   the reader is told that before they type — not after they read an answer
 *   and wonder why it sounds like a photocopier.
 * * **Every answer shows its citations.** An answer with no wording behind it
 *   would be the assistant's opinion about someone's insurance, which is the
 *   thing this product exists not to produce.
 *
 * Suggested questions are offered because "ask me anything about your policy"
 * is a hard prompt to start from, and because the specific questions are the
 * ones retrieval can actually answer well.
 */

const SUGGESTIONS = [
  "How long is the waiting period for pre-existing conditions?",
  "What is the co-payment on a claim?",
  "What is the room rent limit?",
  "What is excluded from this policy?",
];

function CitationList({ citations }: { citations: QaCitation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 border-t border-control-border pt-3">
      <p className="text-meta font-medium text-secondary">
        Based on {citations.length === 1 ? "this part" : "these parts"} of your policy
      </p>
      {citations.map((citation) => (
        <details key={citation.ordinal} className="flex flex-col gap-1">
          <summary className="inline-flex min-h-touch cursor-pointer items-center gap-1 text-support text-accent">
            <FileText className="size-4" aria-hidden="true" />
            Page {citation.page}
            {citation.clauseTitle ? ` · ${citation.clauseTitle}` : ""}
          </summary>
          <blockquote className="mt-2 whitespace-pre-wrap border-l-2 border-accent bg-bg p-3 text-meta text-secondary">
            {citation.clauseText}
          </blockquote>
        </details>
      ))}
    </div>
  );
}

function MessageBubble({ message }: { message: QaMessage }) {
  const isReader = message.role === "USER";
  return (
    <li className={isReader ? "flex justify-end" : "flex"}>
      <div
        className={
          isReader
            ? "max-w-[85%] rounded-card bg-accent-soft p-3 text-support text-primary"
            : "flex w-full flex-col gap-3 rounded-card border border-control-border bg-surface p-4"
        }
      >
        <p className="sr-only">{isReader ? "You asked" : "The assistant answered"}</p>
        <p className="whitespace-pre-wrap text-support text-primary">{message.content}</p>
        {!isReader ? <CitationList citations={message.citations} /> : null}
      </div>
    </li>
  );
}

export function AskPanel({ conversation }: { conversation: QaConversation }) {
  const [messages, setMessages] = useState<QaMessage[]>(conversation.messages);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || asking) return;

    setAsking(true);
    setError(undefined);
    setQuestion("");
    // Shown immediately so the reader sees their own words while they wait.
    const pending: QaMessage = {
      id: `pending-${Date.now()}`,
      role: "USER",
      content: trimmed,
      answerState: null,
      citations: [],
      createdAt: new Date().toISOString(),
    };
    setMessages((current) => [...current, pending]);

    try {
      const response = await fetch(
        `${apiBaseUrl()}/api/v1/policies/${conversation.policyId}/questions`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed }),
        },
      );
      const payload: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const envelope = (payload as { error?: { message?: string } } | null)?.error;
        setError(envelope?.message ?? "We couldn't answer that. Please try again.");
        setMessages((current) => current.filter((item) => item.id !== pending.id));
      } else {
        const answer = payload as QaAnswer;
        setMessages((current) => [...current, answer.message]);
      }
    } catch {
      setError("We couldn't reach the service. Please check your connection and try again.");
      setMessages((current) => current.filter((item) => item.id !== pending.id));
    }
    setAsking(false);
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-h2 font-semibold text-primary">Ask about this policy</h2>
        <p className="text-support text-secondary">
          Answers come only from the document you uploaded, and every one shows the wording it came
          from.
        </p>
      </div>

      {!conversation.explanationAvailable ? (
        <InlineAlert tone="info" title="What this assistant can do right now">
          It can find and show you the parts of your policy that address your question. It
          can&apos;t yet explain them in its own words — so you&apos;ll get the wording, not a
          summary of it.
        </InlineAlert>
      ) : null}

      {messages.length > 0 ? (
        <ul aria-live="polite" className="flex flex-col gap-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </ul>
      ) : (
        <Card className="flex flex-col gap-3">
          <p className="text-support text-secondary">Try one of these to start:</p>
          <ul className="flex flex-col gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onClick={() => send(suggestion)}
                  disabled={asking}
                  className="inline-flex min-h-touch items-center text-left text-support text-accent underline disabled:opacity-50"
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {error ? (
        <InlineAlert tone="critical" title="We couldn't answer that">
          {error}
        </InlineAlert>
      ) : null}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send(question);
        }}
        className="flex flex-col gap-2"
      >
        <label htmlFor="policy-question" className="text-support font-medium text-primary">
          Your question
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="policy-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={500}
            placeholder="e.g. What is the room rent limit?"
            className="min-h-touch flex-1 rounded-control border border-control-border bg-surface px-3 text-body text-primary placeholder:text-secondary"
          />
          <Button type="submit" disabled={asking || question.trim().length === 0}>
            <Send className="size-4" aria-hidden="true" />
            {asking ? "Asking…" : "Ask"}
          </Button>
        </div>
        <p className="text-meta text-secondary">
          This isn&apos;t advice, and it can be wrong. For anything that matters, read the wording
          it quotes and check with your insurer.
        </p>
      </form>
    </section>
  );
}
