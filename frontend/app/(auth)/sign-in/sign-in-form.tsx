"use client";

import { useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { postJson } from "@/lib/api/client";
import type { AppError, MagicLinkResponse } from "@/lib/api/types";

type FormState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "sent" }
  | { status: "error"; error: AppError };

export function SignInForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<FormState>({ status: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ status: "loading" });

    const result = await postJson<MagicLinkResponse>("/api/v1/auth/request-magic-link", {
      email: email.trim(),
    });

    // Success here means "we processed your request", not "you are invited".
    // The API deliberately does not disclose allowlist membership, and neither
    // does this screen.
    setState(
      result.status === "success" ? { status: "sent" } : { status: "error", error: result.error },
    );
  }

  if (state.status === "sent") {
    return (
      <div className="flex flex-col gap-4">
        <InlineAlert tone="positive" title="Check your email">
          <p>
            If <strong>{email.trim()}</strong> is on the beta invite list, a sign-in link is on its
            way. The link works once and expires shortly.
          </p>
        </InlineAlert>
        <Button variant="secondary" onClick={() => setState({ status: "idle" })}>
          Use a different email
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
      <Input
        label="Email address"
        type="email"
        name="email"
        autoComplete="email"
        inputMode="email"
        required
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        description="We'll send a sign-in link. There is no password to remember."
      />

      {state.status === "error" ? (
        <InlineAlert tone="critical" title="We couldn't send your link">
          <p>{state.error.message}</p>
          {state.error.requestId !== null ? (
            <p className="mt-1 text-meta">Reference: {state.error.requestId}</p>
          ) : null}
        </InlineAlert>
      ) : null}

      <Button type="submit" size="lg" fullWidth loading={state.status === "loading"}>
        Send my sign-in link
      </Button>
    </form>
  );
}
