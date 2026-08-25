"use client";

import { ChoiceCard, ChoiceCardGroup } from "@/components/ui/choice-card";
import { Input } from "@/components/ui/input";
import type { Question } from "@/lib/api/types";

/**
 * Renders any question from its definition.
 *
 * docs/03_FRONTEND_ARCHITECTURE.md section 3: "Do not hard-code every question
 * as a separate unique component." Adding a question to the seeded set
 * requires no change here — only a new `inputType` would.
 */
export type QuestionInputProps = {
  question: Question;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string;
};

export function QuestionInput({ question, value, onChange, error }: QuestionInputProps) {
  const { inputType, options, maxSelections } = question;

  if (inputType === "SINGLE_CHOICE") {
    return (
      <ChoiceCardGroup
        legend={question.title}
        hideLegend
        columns={options.length > 3 ? 2 : 1}
        {...(error ? { error } : {})}
      >
        {options.map((option) => (
          <ChoiceCard
            key={option.value}
            name={question.id}
            value={option.value}
            label={option.label}
            {...(option.description ? { description: option.description } : {})}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
        ))}
      </ChoiceCardGroup>
    );
  }

  if (inputType === "MULTI_CHOICE") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    // At the limit, unchosen options are disabled rather than silently
    // ignored, so the cap is visible before it is hit.
    const atLimit = maxSelections !== null && selected.length >= maxSelections;

    return (
      <ChoiceCardGroup
        legend={question.title}
        hideLegend
        columns={2}
        {...(maxSelections !== null
          ? { description: `Choose up to ${maxSelections}. ${selected.length} chosen.` }
          : {})}
        {...(error ? { error } : {})}
      >
        {options.map((option) => {
          const checked = selected.includes(option.value);
          return (
            <ChoiceCard
              key={option.value}
              type="checkbox"
              name={question.id}
              value={option.value}
              label={option.label}
              {...(option.description ? { description: option.description } : {})}
              checked={checked}
              disabled={!checked && atLimit}
              onChange={() =>
                onChange(
                  checked
                    ? selected.filter((item) => item !== option.value)
                    : [...selected, option.value],
                )
              }
            />
          );
        })}
      </ChoiceCardGroup>
    );
  }

  if (inputType === "BOOLEAN") {
    return (
      <ChoiceCardGroup legend={question.title} hideLegend {...(error ? { error } : {})}>
        {[
          { value: "yes", label: "Yes", boolValue: true },
          { value: "no", label: "No", boolValue: false },
        ].map((option) => (
          <ChoiceCard
            key={option.value}
            name={question.id}
            value={option.value}
            label={option.label}
            checked={value === option.boolValue}
            onChange={() => onChange(option.boolValue)}
          />
        ))}
      </ChoiceCardGroup>
    );
  }

  if (inputType === "PINCODE") {
    return (
      <div className="max-w-xs">
        <Input
          label={question.title}
          inputMode="numeric"
          autoComplete="postal-code"
          maxLength={6}
          placeholder="560001"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
          required={question.required}
          {...(error ? { error } : {})}
        />
      </div>
    );
  }

  // NUMBER and MONEY
  const numeric = typeof value === "number" ? String(value) : "";
  return (
    <div className="max-w-xs">
      <Input
        label={question.title}
        inputMode="numeric"
        value={numeric}
        onChange={(event) => {
          const digits = event.target.value.replace(/\D/g, "");
          onChange(digits === "" ? null : Number(digits));
        }}
        required={question.required}
        {...(inputType === "MONEY" ? { prefix: "₹" } : {})}
        {...(question.unit ? { description: `In ${question.unit}` } : {})}
        {...(error ? { error } : {})}
      />
    </div>
  );
}
