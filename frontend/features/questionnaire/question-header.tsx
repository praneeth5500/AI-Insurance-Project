/**
 * The single primary question on a screen.
 *
 * Renders the page's `h1`: docs/02_UX_UI_SPEC.md rule 2 is one primary
 * question per onboarding screen, so the question *is* the heading.
 */
export function QuestionHeader({
  title,
  description,
  optional,
}: {
  title: string;
  description?: string | null;
  optional: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-h2 font-semibold text-primary">{title}</h1>
      {description ? <p className="max-w-prose text-body text-secondary">{description}</p> : null}
      {optional ? <p className="text-support text-secondary">You can skip this question.</p> : null}
    </div>
  );
}
