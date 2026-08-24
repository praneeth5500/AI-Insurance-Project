/**
 * Dates on the home screen.
 *
 * Rendered on the server, so the locale is fixed rather than the visitor's —
 * a value that changes between server and client render causes a hydration
 * mismatch. `en-IN` matches the beta's market.
 */
const FORMATTER = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : FORMATTER.format(date);
}
