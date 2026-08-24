/**
 * Join class names, dropping falsy values.
 *
 * Deliberately dependency-free. Consumer classes are always passed last so
 * they win on equal specificity; components do not accept arbitrary
 * conflicting overrides beyond that.
 */
export type ClassValue = string | false | null | undefined;

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(" ");
}
