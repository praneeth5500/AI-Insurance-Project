"use client";

import { useId } from "react";
import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

export type InputProps = {
  /** Always required: every field is labelled (accessibility requirement). */
  label: string;
  /** Helper text shown under the label and linked via aria-describedby. */
  description?: ReactNode;
  /** When set, the field is marked invalid and the message is linked to it. */
  error?: string;
  /** Text or symbol shown inside the field, e.g. a currency prefix. */
  prefix?: string;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "className" | "id">;

export function Input({ label, description, error, prefix, required, ...props }: InputProps) {
  const id = useId();
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;

  const describedBy =
    [description ? descriptionId : null, error ? errorId : null].filter(Boolean).join(" ") ||
    undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-support font-medium text-primary">
        {label}
        {required ? (
          <span className="text-critical">
            {" *"}
            <span className="sr-only">(required)</span>
          </span>
        ) : null}
      </label>

      {description ? (
        <p id={descriptionId} className="text-support text-secondary">
          {description}
        </p>
      ) : null}

      <div
        className={cn(
          "flex items-center gap-1 rounded-control border bg-surface",
          "focus-within:outline focus-within:outline-2 focus-within:outline-offset-2",
          "focus-within:outline-accent",
          // --control-border, not --border: a control boundary needs 3:1.
          error ? "border-critical" : "border-control-border",
        )}
      >
        {prefix ? (
          <span aria-hidden="true" className="pl-3 text-secondary">
            {prefix}
          </span>
        ) : null}
        <input
          id={id}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            "min-h-touch w-full rounded-control bg-transparent px-3 text-body text-primary",
            "placeholder:text-secondary focus:outline-none",
            "disabled:cursor-not-allowed disabled:opacity-50",
            prefix && "pl-1",
          )}
          {...props}
        />
      </div>

      {error ? (
        // role="alert" so the message is announced when it appears.
        <p id={errorId} role="alert" className="text-support text-critical">
          {error}
        </p>
      ) : null}
    </div>
  );
}
